"""Standalone development adapter. Does not advance the production ESG engine."""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlparse

ADAPTER = Path(__file__).resolve().parents[1] / "adapters" / "esg"
SCHEMA = "esg-learning-report/1"
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


def digest(path):
    with Path(path).open("rb") as stream:
        hasher = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def hash_object(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, where):
    require(isinstance(value, str) and bool(value.strip()), f"{where}: nonblank text required")
    return value


def shape(value, required, optional, where):
    require(isinstance(value, dict), f"{where}: object required")
    require(not (set(required) - value.keys()), f"{where}: missing {sorted(set(required) - value.keys())}")
    require(not (value.keys() - set(required) - set(optional)), f"{where}: unknown fields {sorted(value.keys() - set(required) - set(optional))}")


def array(value, where, nonempty=False):
    require(isinstance(value, list), f"{where}: array required")
    require(not nonempty or bool(value), f"{where}: empty array")
    return value


def index(items, where):
    result = {}
    for item in array(items, where):
        require(isinstance(item, dict), f"{where}: object required")
        ident = item.get("id")
        require(isinstance(ident, str) and ID.fullmatch(ident), f"{where}: invalid id {ident!r}")
        require(ident not in result, f"{where}: duplicate id {ident}")
        result[ident] = item
    return result


def safe_relative(base, name):
    require(isinstance(name, str) and name.strip(), "source path: nonblank relative path required")
    relative = Path(name)
    require(not relative.is_absolute() and ".." not in relative.parts and "\\" not in name,
            f"unsafe relative path: {name}")
    resolved = (base / relative).resolve()
    require(resolved.is_relative_to(base.resolve()), f"source path escapes input parent: {name}")
    return resolved


def pdf_pages(path):
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise ValueError(f"pypdf missing; install {ADAPTER / 'requirements.txt'}") from error
    try:
        reader = PdfReader(str(path), strict=True)
        require(not reader.is_encrypted, f"encrypted PDF unsupported: {path}")
        return len(reader.pages)
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(f"invalid PDF {path}: {error}") from error


def localize_pdf_links(path, out):
    """Keep Chromium's local source hyperlinks portable with the delivery folder."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, TextStringObject
    reader = PdfReader(str(path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    for page in writer.pages:
        for annotation in page.get("/Annots", []):
            action = annotation.get_object().get("/A")
            if not action:
                continue
            action = action.get_object()
            uri = str(action.get("/URI", ""))
            parsed = urlparse(uri)
            if parsed.scheme == "file":
                target = Path(unquote(parsed.path)).resolve()
                require(target.is_relative_to(out.resolve()), "PDF hyperlink escapes delivery")
                relative = target.relative_to(out.resolve()).as_posix()
                require(relative.startswith("sources/") and parsed.fragment.startswith("page="), "unexpected PDF file hyperlink")
                action[NameObject("/URI")] = TextStringObject(relative + "#" + parsed.fragment)
    # Atomic replacement, retaining all pages, annotations and embedded font objects.
    temporary = path.with_suffix(".pdf.tmp")
    try:
        with temporary.open("wb") as stream:
            writer.write(stream)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def pdf_details(path):
    from pypdf import PdfReader
    reader = PdfReader(str(path), strict=True)
    details = []
    for number, page in enumerate(reader.pages, 1):
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        require(abs(width - 595.276) < 1 and abs(height - 841.89) < 1, f"PDF page {number} is not portrait A4")
        visible = page.extract_text() or ""
        require(bool(visible.strip()), f"blank rendered PDF page: {number}")
        details.append({"page": number, "width_pt": width, "height_pt": height, "text_characters": len(visible)})
    return details


def read_input(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"nonfinite JSON number: {value}")

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def validate(data, parent):
    shape(data, ["company", "title", "reporting_period", "information_cutoff", "status", "sources", "metrics", "claims", "pages", "framework"], ["schema", "contract"], "request")
    require(data.get("schema", data.get("contract")) == SCHEMA, f"schema must be {SCHEMA}")
    if "contract" in data and "schema" in data:
        require(data["contract"] == data["schema"], "conflicting schema and contract")
    for field in ["company", "title", "reporting_period", "information_cutoff"]:
        text(data[field], field)
    require(data["status"] == "비공식 학습용", 'status must be "비공식 학습용"')
    shape(data["framework"], ["basis", "qualification"], [], "framework")
    for field in ["basis", "qualification"]:
        text(data["framework"][field], f"framework.{field}")
    sources, metrics, claims, pages = [index(data[key], key) for key in ["sources", "metrics", "claims", "pages"]]
    require(bool(sources), "at least one original source PDF required")
    require(20 <= len(pages) <= 30, "20-30 explicitly authored pages required")
    source_files = {}
    for source in sources.values():
        shape(source, ["id", "title", "url", "path", "sha256", "pages"], [], "source")
        text(source["title"], "source.title")
        require(isinstance(source["url"], str) and urlparse(source["url"]).scheme in ("http", "https") and bool(urlparse(source["url"]).netloc), "source.url: http(s) URL required")
        require(isinstance(source["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", source["sha256"]), "source.sha256: lowercase SHA-256 required")
        path = safe_relative(parent, source["path"])
        require(path.is_file() and path.suffix.lower() == ".pdf", f"source PDF missing: {path}")
        require(digest(path) == source["sha256"], f"source hash mismatch: {source['id']}")
        require(type(source["pages"]) is int and source["pages"] > 0, "source.pages: positive integer required")
        require(pdf_pages(path) == source["pages"], f"source physical page count mismatch: {source['id']}")
        source_files[source["id"]] = path

    def ref(value):
        sid, page = value.get("source_id"), value.get("page")
        require(sid in sources, f"unknown source: {sid}")
        require(type(page) is int and 1 <= page <= sources[sid]["pages"], f"physical page out of range: {sid}:{page}")

    def refs(values):
        for value in array(values, "source_refs", True):
            shape(value, ["source_id", "page"], [], "source ref")
            ref(value)

    for claim in claims.values():
        shape(claim, ["id", "text", "source_id", "page"], [], "claim")
        text(claim["text"], "claim.text")
        ref(claim)
    for metric in metrics.values():
        shape(metric, ["id", "label", "unit", "boundary", "method", "values", "footnotes"], [], "metric")
        for field in ["label", "unit", "boundary", "method"]:
            text(metric[field], f"metric.{field}")
        for footnote in array(metric["footnotes"], "footnotes"):
            text(footnote, "footnote")
        years = set()
        for value in array(metric["values"], "metric.values", True):
            shape(value, ["year", "value"], ["source_id", "page"], "metric value")
            year = value["year"]
            require(type(year) is int and 1 <= year <= 9999, "metric.year: integer year required")
            require(year not in years, f"duplicate metric year: {metric['id']}:{year}")
            years.add(year)
            number = value["value"]
            require(number is None or (type(number) in (int, float) and (not isinstance(number, int) or number.bit_length() <= 1023) and math.isfinite(number)), "metric.value: finite renderable numeric value or null required")
            if number is not None or "source_id" in value or "page" in value:
                ref(value)
    used_claims, used_metrics = set(), set()

    def claim_ids(values):
        for ident in array(values, "claim_ids", True):
            require(isinstance(ident, str) and ident in claims, f"unknown claim: {ident}")
            used_claims.add(ident)

    def metric_ids(values):
        for ident in array(values, "metric_ids", True):
            require(isinstance(ident, str) and ident in metrics, f"unknown metric: {ident}")
            used_metrics.add(ident)

    for page in pages.values():
        shape(page, ["id", "title", "kicker", "lead", "blocks"], ["claim_ids", "classification", "non_company_assertion"], "page")
        for field in ["title", "kicker", "lead"]:
            text(page[field], f"page.{field}")
        # Leads and headings are author-controlled too; factual introductions need citations.
        if "claim_ids" in page:
            claim_ids(page["claim_ids"])
            require("classification" not in page and "non_company_assertion" not in page, "page: mixed factual/analysis classification")
        elif "classification" in page or "non_company_assertion" in page:
            require(page.get("classification") == "analysis" and page.get("non_company_assertion") is True, "page analysis requires explicit non_company_assertion:true")
        else:
            raise ValueError("page title/lead requires claim_ids or analysis with non_company_assertion:true")
        for block in array(page["blocks"], "page.blocks", True):
            require(isinstance(block, dict), "block: object required")
            kind = block.get("kind")
            if kind in ("paragraph", "finding"):
                shape(block, ["kind", "text"], ["claim_ids", "classification", "non_company_assertion"], kind)
                text(block["text"], f"{kind}.text")
                if block.get("classification") == "analysis":
                    require(block.get("non_company_assertion") is True and not block.get("claim_ids"), "analysis requires non_company_assertion:true and no claim_ids")
                    require(data["company"].casefold() not in block["text"].casefold(), "analysis text names the company; use claim_ids")
                else:
                    require("classification" not in block and "non_company_assertion" not in block, "invalid classification")
                    claim_ids(block.get("claim_ids"))
            elif kind == "metrics":
                shape(block, ["kind", "ids"], [], kind)
                metric_ids(block["ids"])
            elif kind == "chart":
                shape(block, ["kind", "metric_ids", "caption"], [], kind)
                text(block["caption"], "chart.caption")
                metric_ids(block["metric_ids"])
                # Render separate panels, never combine incomparable units/boundaries.
            elif kind == "table":
                shape(block, ["kind", "headers", "rows", "source_refs"], ["metric_ids"], kind)
                refs(block["source_refs"])
                if "metric_ids" in block:
                    metric_ids(block["metric_ids"])
                    bound_refs = {(value["source_id"], value["page"]) for ident in block["metric_ids"] for value in metrics[ident]["values"] if "source_id" in value}
                    supplied_refs = {(value.get("source_id"), value.get("page")) for value in block["source_refs"]}
                    require(bound_refs <= supplied_refs, "table metric citation coverage incomplete")
                headers = array(block["headers"], "table.headers", True)
                for header in headers:
                    text(header, "table.header")
                for row in array(block["rows"], "table.rows", True):
                    require(isinstance(row, list) and len(row) == len(headers), "table row width mismatch")
                    for cell in row:
                        text(cell, "table.cell")
                refs(block["source_refs"])
            elif kind == "source":
                shape(block, ["kind", "refs"], [], kind)
                refs(block["refs"])
            else:
                raise ValueError(f"unknown block kind: {kind}")
    require(used_claims == set(claims), f"orphan claims: {sorted(set(claims) - used_claims)}")
    require(used_metrics == set(metrics), f"orphan claimed metric values: {sorted(set(metrics) - used_metrics)}")
    return source_files


def normalized(data):
    result = copy.deepcopy(data)
    for source in result["sources"]:
        source["path"] = f"sources/{source['id']}.pdf"
    return result


def adapter_hashes():
    files = [Path(__file__), *sorted(path for path in ADAPTER.rglob("*") if path.is_file() and "node_modules" not in path.parts and "__pycache__" not in path.parts and path.name != "development-summary.md")]
    return {("pr/esg.py" if path == Path(__file__) else "adapters/esg/" + path.relative_to(ADAPTER).as_posix()): digest(path) for path in files}


def fingerprint(data):
    return hash_object({"content": normalized(data), "adapter": adapter_hashes()})


def value_text(value):
    return "자료 없음 (null)" if value is None else format(value, ",")


def citation(ref, sources):
    source = sources[ref["source_id"]]
    return f'<a href="sources/{html.escape(source["id"])}.pdf#page={ref["page"]}">{html.escape(source["title"])} · PDF p.{ref["page"]}</a>'


def unique_refs(refs):
    result = {}
    for ref in refs:
        if "source_id" in ref:
            result[(ref["source_id"], ref["page"])] = ref
    return list(result.values())


def citations(refs, sources):
    grouped = {}
    for ref in unique_refs(refs):
        grouped.setdefault(ref["source_id"], []).append(ref["page"])
    entries = []
    for ident, pages in grouped.items():
        source = sources[ident]
        links = ", ".join(f'<a href="sources/{html.escape(ident)}.pdf#page={page}">p.{page}</a>' for page in pages)
        entries.append(f'{html.escape(source["title"])} · PDF {links}')
    return '<div class="citations">출처: ' + " / ".join(entries) + "</div>"


def chart_svg(metric):
    """One sourced series per panel; nulls are gaps, with a zero baseline."""
    values = sorted(metric["values"], key=lambda value: value["year"])
    numbers = [value["value"] for value in values if value["value"] is not None]
    if not numbers:
        label = html.escape(metric["label"])
        unit = html.escape(metric["unit"])
        return f'<svg viewBox="0 0 700 120" role="img"><title>{label} ({unit}) 자료 없음</title><text x="20" y="25">{label} · 단위: {unit}</text><text x="20" y="60">자료 없음 (null) · 연도: ' + ", ".join(str(value["year"]) for value in values) + '</text></svg>'
    low, high = min([0, *numbers]), max([0, *numbers])
    if high == low:
        high = low + 1
    # Normalize before subtraction to avoid overflow for very large finite values.
    scale = max(abs(low), abs(high), 1)
    lower, upper = low / scale, high / scale
    def y(number):
        return 205 - (number / scale - lower) / (upper - lower) * 145
    def x(position):
        return 150 + position * 430 / max(len(values) - 1, 1)
    label = html.escape(metric["label"])
    unit = html.escape(metric["unit"])
    parts = [f'<svg viewBox="0 0 700 265" role="img" aria-labelledby="chart-{metric["id"]}-title"><title id="chart-{metric["id"]}-title">{label} ({unit}) 연도별 원자료; null은 자료 없음</title>',
             f'<text x="20" y="22">{label}</text><text x="20" y="43">단위: {unit}</text>',
             '<path d="M105 60 V205 H610" fill="none" stroke="#899c94"/>']
    for tick in range(4):
        fraction = tick / 3
        number = (lower * (1 - fraction) + upper * fraction) * scale
        pos = 205 - fraction * 145
        parts.append(f'<path d="M105 {pos:.3f} H610" stroke="#e1e9e4"/><text x="98" y="{pos + 4:.3f}" text-anchor="end">{html.escape(format(number, ".3g"))}</text>')
    previous = None
    for position, value in enumerate(values):
        px = x(position)
        parts.append(f'<text x="{px:.3f}" y="230" text-anchor="middle">{value["year"]}</text>')
        if value["value"] is None:
            previous = None
            parts.append(f'<text x="{px:.3f}" y="190" text-anchor="middle">자료 없음</text>')
            continue
        py = y(value["value"])
        if previous:
            parts.append(f'<path d="M{previous[0]:.3f} {previous[1]:.3f} L{px:.3f} {py:.3f}" stroke="#287466" stroke-width="2" fill="none"/>')
        label_y = py + 20 if py < 90 else py - 10
        parts.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="4" fill="#287466"/><text x="{px:.3f}" y="{label_y:.3f}" text-anchor="middle">{html.escape(value_text(value["value"]))}</text>')
        previous = px, py
    parts.append('<text x="645" y="230">연도</text></svg>')
    return "".join(parts)


def render_html(data):
    sources, metrics, claims = [index(data[key], key) for key in ["sources", "metrics", "claims"]]
    esc = html.escape
    def claim_evidence(ids):
        return '<div class="claim-evidence citations">' + " / ".join(f'[{esc(ident)}] ' + citation(claims[ident], sources) for ident in ids) + "</div>"
    def block_html(block):
        kind = block["kind"]
        if kind in ("paragraph", "finding"):
            tail = '<span class="classification">방법론 해설 · 기업에 대한 주장이 아님</span>' if block.get("classification") == "analysis" else claim_evidence(block["claim_ids"])
            return f'<div class="block {kind}"><p>{esc(block["text"])}</p>{tail}</div>'
        if kind == "source":
            return '<div class="block">' + citations(block["refs"], sources) + "</div>"
        if kind == "table":
            return '<div class="block"><table><thead><tr>' + "".join(f"<th>{esc(cell)}</th>" for cell in block["headers"]) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in block["rows"]) + "</tbody></table>" + citations(block["source_refs"], sources) + "</div>"
        if kind == "metrics" and len(block["ids"]) > 1:
            selected = [metrics[ident] for ident in block["ids"]]
            years = sorted({value["year"] for metric in selected for value in metric["values"]})
            rows, notes = [], []
            for metric in selected:
                by_year = {value["year"]: value for value in metric["values"]}
                cells = [f'<td>{esc(metric["label"])}</td>', f'<td>{esc(metric["unit"])}</td>']
                for year in years:
                    value = by_year.get(year)
                    if value is None or value["value"] is None:
                        display = '자료 없음 (null)'
                        if value and "source_id" in value:
                            display += f'<br><a class="cell-ref" href="sources/{esc(value["source_id"])}.pdf#page={value["page"]}">[{esc(value["source_id"])} p.{value["page"]}]</a>'
                    else:
                        display = esc(value_text(value["value"])) + f'<br><a class="cell-ref" title="{esc(sources[value["source_id"]]["title"])}" href="sources/{esc(value["source_id"])}.pdf#page={value["page"]}">[{esc(value["source_id"])} p.{value["page"]}]</a>'
                    cells.append(f'<td>{display}</td>')
                rows.append('<tr>' + ''.join(cells) + '</tr>')
                notes.append(f'<p class="footnotes"><strong>{esc(metric["label"])}</strong> · 경계: {esc(metric["boundary"])} · 방법: {esc(metric["method"])}' + ''.join(' · ' + esc(note) for note in metric["footnotes"]) + '</p>')
            return '<div class="block metric-comparison"><table><thead><tr><th>지표</th><th>단위</th>' + ''.join(f'<th>{year}</th>' for year in years) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table><div class="comparison-notes">' + ''.join(notes) + '</div></div>'
        panels = []
        for ident in block.get("ids", block.get("metric_ids", [])):
            metric = metrics[ident]
            meta = f'<div class="meta">단위: {esc(metric["unit"])} · 경계: {esc(metric["boundary"])} · 방법: {esc(metric["method"])}</div>'
            if kind == "metrics":
                visual = f'<h2>{esc(metric["label"])}</h2>' + meta + '<table><thead><tr><th>연도</th><th>값</th><th>근거 (물리 페이지)</th></tr></thead><tbody>' + "".join(f'<tr><td>{value["year"]}</td><td>{esc(value_text(value["value"]))}</td><td>{citation(value, sources) if "source_id" in value else "자료 없음"}</td></tr>' for value in sorted(metric["values"], key=lambda value: value["year"])) + "</tbody></table>"
            else:
                visual = '<figure>' + chart_svg(metric) + meta + f'<figcaption>{esc(block["caption"])}</figcaption>' + citations(metric["values"], sources) + "</figure>"
            panels.append('<div class="block metric">' + visual + "".join(f'<p class="footnotes">{esc(footnote)}</p>' for footnote in metric["footnotes"]) + "</div>")
        return "".join(panels)
    sheets = []
    for number, page in enumerate(data["pages"], 1):
        lead_citations = claim_evidence(page["claim_ids"]) if page.get("claim_ids") else ""
        sheets.append(f'<section class="report-page" id="{esc(page["id"])}"><header><div class="masthead"><span>{esc(data["company"])} · {esc(data["title"])}</span><span class="status">{esc(data["status"])}</span></div><div class="kicker">{esc(page["kicker"])}</div><h1>{esc(page["title"])}</h1><p class="lead">{esc(page["lead"])}</p>{lead_citations}</header><main class="page-body">' + "".join(block_html(block) for block in page["blocks"]) + f'</main><footer class="footer"><span class="qualification">{esc(data["framework"]["basis"])} · {esc(data["framework"]["qualification"])}<br>보고기간: {esc(data["reporting_period"])} · 정보 기준일: {esc(data["information_cutoff"])}</span><span>{number:02d} / {len(data["pages"]):02d}</span></footer></section>')
    return '<!doctype html>\n<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data: file:; font-src file:"><title>' + esc(data["title"]) + '</title><style>' + (ADAPTER / "report.css").read_text(encoding="utf-8") + '</style></head><body>' + "\n".join(sheets) + "</body></html>\n"


def render_markdown(data):
    lines = [f'# {data["title"]}', "", f'{data["company"]} · {data["status"]}', "", f'보고기간: {data["reporting_period"]} | 기준일: {data["information_cutoff"]}', "", data["framework"]["basis"], "", data["framework"]["qualification"], "", "<!-- Editable companion. JSON is the build source; synchronize edits into JSON. -->", ""]
    sources, metrics, claims = [index(data[key], key) for key in ["sources", "metrics", "claims"]]
    def refs(values):
        return " / ".join(f'[{sources[ref["source_id"]]["title"]} · PDF p.{ref["page"]}](sources/{ref["source_id"]}.pdf#page={ref["page"]})' for ref in unique_refs(values))
    def factual(ids):
        return [" / ".join(f'[{ident}] ' + refs([claims[ident]]) for ident in ids)]
    for page in data["pages"]:
        lines.extend(["---", "", f'## {page["title"]} {{#{page["id"]}}}', "", page["kicker"], "", page["lead"], ""])
        if page.get("claim_ids"):
            lines.extend(factual(page["claim_ids"]) + [""])
        for block in page["blocks"]:
            kind = block["kind"]
            if kind in ("paragraph", "finding"):
                lines.append(block["text"])
                lines.extend(["방법론 해설 · 기업에 대한 주장이 아님"] if block.get("classification") else factual(block["claim_ids"]))
            elif kind == "table":
                lines += ["| " + " | ".join(cell.replace("|", "\\|").replace("\n", "<br>") for cell in block["headers"]) + " |", "| " + " | ".join("---" for _ in block["headers"]) + " |"]
                lines.extend("| " + " | ".join(cell.replace("|", "\\|").replace("\n", "<br>") for cell in row) + " |" for row in block["rows"])
                lines.append(refs(block["source_refs"]))
            elif kind == "source":
                lines.append(refs(block["refs"]))
            else:
                if kind == "chart":
                    lines.append(block["caption"])
                if kind == "metrics" and len(block["ids"]) > 1:
                    selected = [metrics[ident] for ident in block["ids"]]
                    years = sorted({value["year"] for metric in selected for value in metric["values"]})
                    lines.append("| 지표 | 단위 | " + " | ".join(map(str, years)) + " |")
                    lines.append("| " + " | ".join("---" for _ in range(len(years) + 2)) + " |")
                    for metric in selected:
                        by_year = {value["year"]: value for value in metric["values"]}
                        cells = [metric["label"], metric["unit"]]
                        for year in years:
                            value = by_year.get(year)
                            cells.append(value_text(value["value"] if value else None) + (" " + refs([value]) if value and "source_id" in value else ""))
                        lines.append("| " + " | ".join(cell.replace("|", "\\|").replace("\n", "<br>") for cell in cells) + " |")
                    for metric in selected:
                        lines.append(f'{metric["label"]} · 경계: {metric["boundary"]} · 방법: {metric["method"]} ' + " / ".join(metric["footnotes"]))
                    lines.append("")
                    continue
                for ident in block.get("ids", block.get("metric_ids", [])):
                    metric = metrics[ident]
                    lines.extend([f'### {metric["label"]}', f'단위: {metric["unit"]} | 경계: {metric["boundary"]} | 방법: {metric["method"]}', "| 연도 | 값 | 근거 |", "| --- | --- | --- |"])
                    lines.extend(f'| {value["year"]} | {value_text(value["value"])} | {refs([value]) or "자료 없음"} |' for value in sorted(metric["values"], key=lambda value: value["year"]))
                    lines.extend(metric["footnotes"])
            lines.append("")
    lines.extend(["## 원본 자료", ""])
    lines.extend(f'- [{source["title"]}]({source["path"]}) · [원문 URL]({source["url"]}) · SHA-256 `{source["sha256"]}` · PDF {source["pages"]}쪽' for source in data["sources"])
    return "\n".join(lines) + "\n"


def guard_output(out, input_path, source_files):
    def writable_file(path):
        require(not path.is_symlink(), f"output symlink forbidden: {path.name}")
        require(not path.is_file() or path.stat().st_nlink == 1,
                f"output hardlink forbidden: {path.name}")
    require(not out.is_symlink(), "output directory cannot be a symlink")
    for source in source_files.values():
        require(source != out and not out.is_relative_to(source), "output conflicts with source PDF")
    require(input_path != out, "output conflicts with input")
    managed_names = {"input.json", "report.md", "report.html", "report.pdf", "manifest.json", "geometry.json", "render.json", "checks.json"}
    resolved_out = out.resolve()
    if input_path.is_relative_to(resolved_out):
        relative = input_path.relative_to(resolved_out)
        require(relative == Path("input.json") or (len(relative.parts) == 1 and relative.name not in managed_names), "output would overwrite input")
    for source in source_files.values():
        if source.is_relative_to(resolved_out):
            relative = source.relative_to(resolved_out)
            require(relative.parts[0] not in {"screenshots", "assets"} and relative.as_posix() not in managed_names, "output would overwrite original source")
    for name in ["input.json", "report.md", "report.html", "report.pdf", "manifest.json", "geometry.json", "render.json", "checks.json", "sources", "screenshots", "assets"]:
        writable_file(out / name)
    for asset in (ADAPTER / "assets").iterdir():
        writable_file(out / "assets" / asset.name)
    for sid, source in source_files.items():
        destination = out / "sources" / f"{sid}.pdf"
        writable_file(destination)
        require(destination.resolve() != input_path, "output source conflicts with input")
        require(destination.resolve() not in source_files.values() or destination.resolve() == source,
                "output source would overwrite another original source")


def prepare(input_path, out):
    input_path, out = Path(input_path).resolve(), Path(out).absolute()
    data = read_input(input_path)
    source_files = validate(data, input_path.parent)
    guard_output(out, input_path, source_files)
    out.mkdir(parents=True, exist_ok=True)
    # Invalidate a previous successful receipt before any mutations/rendering.
    (out / "manifest.json").unlink(missing_ok=True)
    (out / "sources").mkdir(exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    for asset in (ADAPTER / "assets").iterdir():
        shutil.copyfile(asset, out / "assets" / asset.name)
    frozen = normalized(data)
    for source in frozen["sources"]:
        dest = out / source["path"]
        if source_files[source["id"]].resolve() != dest.resolve():
            shutil.copyfile(source_files[source["id"]], dest)
        require(digest(dest) == source["sha256"], "source changed while copying")
    if input_path != (out / "input.json").resolve():
        write_json(out / "input.json", frozen)
    (out / "report.md").write_text(render_markdown(frozen), encoding="utf-8")
    manifest = {"schema": SCHEMA, "stage": "prepared", "pdf_success": False, "independent_review": "not_performed", "input_sha256": digest(input_path), "input_fingerprint": fingerprint(data), "content_sha256": hash_object(frozen), "authored_pages": len(data["pages"]), "adapter_sha256": adapter_hashes(), "files": {}}
    manifest["files"] = {name: digest(out / name) for name in ["input.json", "report.md", *[source["path"] for source in frozen["sources"]], *["assets/" + asset.name for asset in (ADAPTER / "assets").iterdir()]]}
    write_json(out / "manifest.json", manifest)
    return data, manifest


def build(input_path, out, html_only=False, chromium=None, node=None, playwright_module=None):
    out = Path(out).absolute()
    data, manifest = prepare(input_path, out)
    (out / "manifest.json").unlink(missing_ok=True)
    for name in ["report.pdf", "geometry.json", "render.json", "checks.json"]:
        (out / name).unlink(missing_ok=True)
    if (out / "screenshots").exists():
        shutil.rmtree(out / "screenshots")
    (out / "report.html").write_text(render_html(data), encoding="utf-8")
    manifest["files"]["report.html"] = digest(out / "report.html")
    manifest["stage"] = "html_only" if html_only else "pdf"
    if not html_only:
        executable = node or os.environ.get("ESG_NODE") or shutil.which("node")
        if not executable:
            bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
            executable = str(bundled) if bundled.is_file() else None
        require(executable, "Node >=20 missing; use --node or ESG_NODE")
        command = [str(executable), str(ADAPTER / "render.mjs"), "--out", str(out)]
        if chromium:
            command += ["--chromium", chromium]
        if playwright_module:
            command += ["--playwright-module", playwright_module]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
        require(completed.returncode == 0, f"Playwright rendering failed: {completed.stderr.strip() or completed.stdout.strip()}")
        localize_pdf_links(out / "report.pdf", out)
        geometry = read_input(out / "geometry.json")
        require(geometry["page_count"] == len(data["pages"]) and not geometry["overflows"], "page geometry overflow or count mismatch")
        require(pdf_pages(out / "report.pdf") == len(data["pages"]), "rendered PDF physical page count mismatch")
        manifest["pdf_pages"] = pdf_pages(out / "report.pdf")
        manifest["pdf_success"] = True
        for name in ["report.pdf", "geometry.json", "render.json", *[f"screenshots/page-{i:02d}.png" for i in range(1, len(data["pages"]) + 1)]]:
            manifest["files"][name] = digest(out / name)
    # Detect concurrent author/source edits during rendering.
    require(digest(input_path) == manifest["input_sha256"], "input changed during build")
    validate(read_input(input_path), Path(input_path).resolve().parent)
    require(fingerprint(data) == manifest["input_fingerprint"], "adapter changed during build")
    write_json(out / "manifest.json", manifest)
    return check(input_path, out, html_only=html_only)


def check(input_path, out, html_only=False):
    out = Path(out).absolute()
    result = {"ok": False, "pdf_success": False, "independent_review": "not_performed", "errors": [], "actual_sha256": {}}
    safe_to_write = False
    try:
        require(not (out / "checks.json").is_symlink(), "checks.json symlink forbidden")
        data = read_input(input_path)
        source_files = validate(data, Path(input_path).resolve().parent)
        guard_output(out, Path(input_path).resolve(), source_files)
        safe_to_write = True
        manifest = read_input(out / "manifest.json")
        result["actual_input_sha256"] = digest(input_path)
        result["actual_input_fingerprint"] = fingerprint(data)
        result["content_sha256"] = hash_object(normalized(data))
        require(manifest["schema"] == SCHEMA, "manifest schema mismatch")
        require(manifest["input_sha256"] == result["actual_input_sha256"], "stale output: input bytes changed")
        require(manifest["input_fingerprint"] == result["actual_input_fingerprint"], "stale output: input or adapter fingerprint changed")
        require(manifest["content_sha256"] == result["content_sha256"], "stale content hash")
        expected = {"input.json", "report.md", "report.html", *[f"sources/{source['id']}.pdf" for source in data["sources"]], *["assets/" + asset.name for asset in (ADAPTER / "assets").iterdir()]}
        require(manifest["stage"] in ("html_only", "pdf"), "output prepared but not built")
        if manifest["stage"] == "pdf":
            expected |= {"report.pdf", "geometry.json", "render.json", *[f"screenshots/page-{i:02d}.png" for i in range(1, len(data["pages"]) + 1)]}
        else:
            require(html_only, "HTML-only output is not PDF success; pass --html-only to check HTML")
        require(set(manifest["files"]) == expected, "manifest artifact inventory mismatch")
        for name in sorted(expected):
            path = safe_relative(out, name)
            require(path.is_file(), f"missing output: {name}")
            require(not (out / name).is_symlink(), f"output symlink forbidden: {name}")
            result["actual_sha256"][name] = digest(path)
        for name in sorted(expected):
            require(result["actual_sha256"][name] == manifest["files"][name], f"stale or modified output: {name}")
        frozen = read_input(out / "input.json")
        validate(frozen, out)
        require(normalized(frozen) == normalized(data), "frozen input mismatch")
        require((out / "report.html").read_text(encoding="utf-8") == render_html(data), "HTML does not match current authored input")
        require((out / "report.md").read_text(encoding="utf-8") == render_markdown(normalized(data)), "Markdown does not match input (synchronize author edits to JSON)")
        if manifest["stage"] == "pdf":
            result["pdf_pages"] = pdf_pages(out / "report.pdf")
            result["pdf_geometry"] = pdf_details(out / "report.pdf")
            require(result["pdf_pages"] == len(data["pages"]) == manifest["pdf_pages"], "PDF pages differ from authored pages")
            geometry = read_input(out / "geometry.json")
            require(geometry["page_count"] == len(data["pages"]) and not geometry["overflows"], "geometry overflow")
            require([page["id"] for page in geometry["pages"]] == [page["id"] for page in data["pages"]], "geometry page order mismatch")
            require(manifest["pdf_success"] is True, "manifest did not record PDF success")
            result["pdf_success"] = True
        result["ok"] = True
        result["stage"] = manifest["stage"]
    except (ValueError, OSError, KeyError, TypeError) as error:
        result["errors"].append(str(error))
    if safe_to_write and out.is_dir() and not (out / "checks.json").is_symlink():
        write_json(out / "checks.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Development ESG learning reports; no production or independent-review approval")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["prepare", "build", "check"]:
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True, help=f"{SCHEMA} request JSON; sources relative to its parent")
        command.add_argument("--out", type=Path, required=True)
        if name in ("build", "check"):
            command.add_argument("--html-only", action="store_true", help="explicitly permit HTML only; pdf_success stays false")
        if name == "build":
            command.add_argument("--chromium", help="Chromium executable; alternatively ESG_CHROMIUM_EXECUTABLE")
            command.add_argument("--node", help="Node executable; alternatively ESG_NODE")
            command.add_argument("--playwright-module", help="Playwright module/directory; alternatively ESG_PLAYWRIGHT_MODULE")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            _, receipt = prepare(args.input, args.out)
            result = {"ok": True, "stage": "prepared", "pdf_success": False, "content_sha256": receipt["content_sha256"]}
        elif args.command == "build":
            result = build(args.input, args.out, args.html_only, args.chromium, args.node, args.playwright_module)
        else:
            result = check(args.input, args.out, args.html_only)
    except (ValueError, OSError, subprocess.SubprocessError, TypeError) as error:
        result = {"ok": False, "pdf_success": False, "errors": [str(error)]}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
