"""Source development ESG corpus tools; never advance general ESG production gates.

The portable ledger is authoritative. DuckDB is a query projection, not evidence
of semantic correctness or an independent review. See docs/esg-system.md.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import http.client
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import tempfile
from contextlib import contextmanager
from urllib.parse import urljoin, urlsplit

SCHEMA = "esg-corpus/1"
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
SOURCE_PROVENANCE = ("report_release_date", "publication_date_basis", "pdf_created_at", "pdf_modified_at", "acquired_at", "first_distribution_of_hash_verified", "assurance_version_equivalence_verified", "source_date_note")
METRICS = {
    "scope1_ghg": ("Scope 1 온실가스", "직접 배출의 조직 경계와 포함 가스, CO₂ 환산 기준을 읽는다. 연결기업과 사업부의 배출량을 합치거나 배출 감축 성과로 해석하지 않는다."),
    "scope2_lb_ghg": ("Scope 2 온실가스 · LB", "지역기반(LB) 산정은 전력망의 평균 배출계수를 사용하는 후보이다. 시장기반(MB) 결과와 별도 계열로 유지하고 계약수단의 효과를 LB 수치에 부여하지 않는다."),
    "scope2_mb_ghg": ("Scope 2 온실가스 · MB", "시장기반(MB) 산정은 계약수단과 잔여믹스 등 적용 조건의 검토가 필요하다. 지역기반(LB)와 이름이나 단위가 같아도 서로 대체하지 않는다."),
    "scope3_ghg": ("Scope 3 온실가스", "가치사슬 배출의 포함 카테고리, 추정 방법 및 제외 항목을 확인한다. 카테고리 일부와 전체 합계를 비교하거나 미등록 카테고리를 영으로 취급하지 않는다."),
    "electricity_consumption": ("전력 사용량", "구매전력과 자가발전의 포함 여부, 전력 판매의 차감 및 사용 시설의 범위를 읽는다. 전력 사용량은 총에너지 사용량과 다른 개념이며 설비 규모 차이만으로 효율을 추정할 수 없다."),
    "energy_consumption": ("에너지 사용량", "연료와 전력의 합산 기준, 열량 환산계수와 내부 발전 중복 처리 여부를 확인한다. 같은 에너지 단위라도 최종에너지와 일차에너지의 산정 차이를 보존한다."),
    "renewable_electricity_share": ("재생전력 비중", "비중의 분모가 전력인지 전체 에너지인지 확인한다. 인증서, 구매계약 및 현장 발전의 포함 기준이 다르면 같은 백분율로 직접적인 환경 효과를 비교할 수 없다."),
    "water_withdrawal": ("취수량", "외부에서 유입되는 물의 공급원과 집계 경계를 확인한다. 취수량은 소비량과 구분하며 내부 순환수의 재계상을 원문 정의 없이 더하지 않는다."),
    "water_consumption": ("물 소비량", "취수에서 배출 등을 차감하는 정의와 추정 방식, 물 부족 지역의 포함 범위를 확인한다. 원문이 취수량만 제공하면 소비량을 임의 계산하지 않는다."),
    "water_reuse_share": ("용수 재이용 비중", "반복 사용, 재활용 및 회수의 구분과 분모를 확인한다. 공정 내부 순환 횟수나 재이용량을 서로 다른 비중 정의로 환산하지 않는다."),
    "waste_generated": ("폐기물 발생량", "일반·유해 폐기물 포함 범위와 사업장 집계 기준, 부산물 취급을 확인한다. 폐기물 총량의 차이가 생산량 또는 생산공정의 차이를 통제한 성과 차이를 뜻하지는 않는다."),
    "waste_recovery_share": ("폐기물 회수 비중", "회수에는 에너지 회수 등 재활용과 다른 처리가 포함될 수 있다. 원문의 recovery와 recycling을 구분하고 분모와 처리 경로를 그대로 보존한다."),
    "hazardous_waste": ("유해 폐기물", "관할 지역의 분류와 유해성 정의, 발생·처리·보관 시점을 읽는다. 국가별 법적 분류나 사업장 경계가 다르면 총량의 단순한 크기 비교에 의미를 부여할 수 없다."),
    "employees_total": ("종업원 수", "기말 인원과 연평균 인원, 직접 고용과 외주 인력, 정규직과 기간제 포함 범위를 구분한다. 그룹 인원과 특정 법인 인원을 같은 모집단으로 해석하지 않는다."),
    "women_workforce_share": ("여성 인력 비중", "성별 분류의 대상 인원과 근로 형태, 기준 시점 및 지역을 확인한다. 비중의 분모가 다르면 조직 규모나 기회 접근성의 차이를 이 숫자만으로 판단할 수 없다."),
    "women_management_share": ("여성 관리직 비중", "관리직 직급의 정의와 포함 조직, 분모의 직급 범위를 읽는다. 임원·관리자·전체 직원의 여성 비중은 구분하며 직급 정의가 다른 수치의 서열을 만들지 않는다."),
    "training_hours": ("교육 시간", "총시간인지 인당 평균인지, 대상 인력과 교육 종류의 포함 기준을 확인한다. 온라인 교육과 법정 교육, 수료와 참여 기준의 차이를 검토하기 전에는 교육 성과로 해석하지 않는다."),
    "ltir": ("휴업재해율 · LTIR", "분자의 재해 정의와 분모의 근로시간, 배수(예: 백만 시간), 임직원과 도급인 포함 범위를 읽는다. LTIR 명칭이 같아도 배수나 집계 경계가 다르면 직접 비교할 수 없다."),
    "work_fatalities": ("업무 관련 사망", "사망의 업무 관련성 판단, 보고 시점과 임직원·협력사 포함 범위를 확인한다. 미등록과 영 건을 분리하고 특정 지역 자료를 그룹 전체 결과로 확장하지 않는다."),
    "supplier_audits": ("공급업체 감사", "감사 대상 업체 수와 감사 건수, 현장·서면 평가 및 중복 업체 처리 기준을 확인한다. 숫자가 크다는 이유만으로 공급망 통제의 효과나 감사 품질이 우수하다고 판단하지 않는다."),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint(data):
    return hashlib.sha256(canonical(data).encode("utf-8")).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def no_links(path, regular=False):
    """Check lexical ancestors before resolve; reject aliases even if in-bounds."""
    path = Path(os.path.abspath(path))
    for part in reversed([path, *path.parents]):
        require(not part.is_symlink(), f"symlink forbidden: {part}")
    if path.exists() and path.is_file():
        require(path.stat().st_nlink == 1, f"hardlink forbidden: {path}")
    if regular:
        require(path.is_file(), f"regular file required: {path}")
    return path


def input_path(path):
    return no_links(path, regular=True)


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"nonfinite JSON number: {value}")

    return json.loads(input_path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def public_url(url):
    require(isinstance(url, str) and not any(ord(c) < 33 for c in url), "URL must be nonblank without whitespace/control characters")
    parsed = urlsplit(url)
    require(parsed.scheme in ("https", "http") and parsed.hostname, "only public http(s) URLs permitted")
    require(not parsed.username and not parsed.password and not parsed.fragment, "URL credentials/fragments forbidden")
    require(parsed.port in (None, 80 if parsed.scheme == "http" else 443), "nonstandard URL port forbidden")
    host = parsed.hostname.lower().rstrip(".")
    require("." in host or ":" in host, "private/local hostname forbidden")
    require(not host.endswith((".local", ".localhost", ".internal", ".test", ".invalid")), "private/local hostname forbidden")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    require(address is None or address.is_global, "private/nonpublic IP forbidden")
    return parsed


def download_pdf(url, destination, allowed_hosts, max_bytes=200 * 1024 * 1024):
    """Resolve/check/pin the public IP for every hop; do not use ambient proxies."""
    original = url
    for _ in range(6):
        parsed = public_url(url)
        require(parsed.hostname.lower().rstrip(".") in allowed_hosts, "redirect host not in declared official hosts")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
        require(bool(addresses), "DNS returned no addresses")
        require(all(ipaddress.ip_address(a[4][0]).is_global for a in addresses), "DNS resolved to private/nonpublic address")
        # Connection uses the checked address, with original hostname for TLS/Host.
        conn = http.client.HTTPConnection(parsed.hostname, port, timeout=60)
        raw = socket.create_connection((addresses[0][4][0], port), timeout=60)
        try:
            conn.sock = raw
            if parsed.scheme == "https":
                conn.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=parsed.hostname)
            target = parsed.path or "/"
            if parsed.query:
                target += "?" + parsed.query
            conn.request("GET", target, headers={"User-Agent": "professional-reports-esg-system/1", "Accept": "application/pdf", "Accept-Encoding": "identity"})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                require(location, "redirect without Location")
                redirected = urljoin(url, location)
                require(not (parsed.scheme == "https" and urlsplit(redirected).scheme == "http"), "HTTPS downgrade forbidden")
                url = redirected
                continue
            require(response.status == 200, f"PDF download HTTP {response.status}")
            require(response.getheader("Content-Encoding", "identity") == "identity", "encoded PDF response unsupported")
            size = 0
            with Path(destination).open("xb") as stream:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    require(size <= max_bytes, "PDF exceeds download size limit")
                    stream.write(chunk)
            require(size > 0, "empty PDF download")
            from datetime import datetime, timezone
            return {"url": original, "final_url": url, "bytes": size, "retrieved_at": datetime.now(timezone.utc).isoformat()}
        finally:
            conn.close()
    raise ValueError("too many PDF redirects")


def pdf_evidence(path):
    from pypdf import PdfReader
    path = input_path(path)
    require(path.suffix.lower() == ".pdf", "source must be a PDF path")
    with path.open("rb") as stream:
        require(stream.read(5) == b"%PDF-", "source lacks PDF header")
    try:
        reader = PdfReader(str(path), strict=True)
        require(not reader.is_encrypted, "encrypted PDF unsupported")
        require(len(reader.pages) > 0, "empty PDF")
        result = []
        for number, page in enumerate(reader.pages, 1):
            value = page.extract_text() or ""
            # Locator evidence may be image-only. A blank page is not evidence.
            xobjects = page.get("/Resources", {}).get("/XObject", {})
            xobjects = xobjects.get_object() if hasattr(xobjects, "get_object") else xobjects
            has_image = any(item.get_object().get("/Subtype") == "/Image" for item in xobjects.values())
            result.append({"page": number, "text": value, "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(), "has_image": has_image})
        return result
    except (ValueError, OSError):
        raise
    except Exception as error:
        raise ValueError(f"invalid/extraction-failed PDF: {path}: {error}") from error


def shape(data, required, optional, where):
    require(isinstance(data, dict), f"{where}: object required")
    require(set(required) <= data.keys(), f"{where}: missing fields {sorted(set(required) - data.keys())}")
    require(data.keys() <= set(required) | set(optional), f"{where}: unknown fields {sorted(data.keys() - set(required) - set(optional))}")


def nonblank(value, where):
    require(isinstance(value, str) and bool(value.strip()), f"{where}: nonblank string required")


def ident(value, where):
    require(isinstance(value, str) and ID.fullmatch(value), f"{where}: invalid ID")


def indexed(values, where):
    require(isinstance(values, list), f"{where}: array required")
    result = {}
    for item in values:
        require(isinstance(item, dict), f"{where}: object required")
        key = item.get("id")
        ident(key, where)
        require(key not in result, f"{where}: duplicate ID {key}")
        result[key] = item
    return result


def company_shape(data, stub=False):
    shape(data, ["company", "sources", "observations", "claims"], [], "company file")
    shape(data["company"], ["id", "name", "business_model"], [], "company")
    ident(data["company"]["id"], "company")
    for key in ("name", "business_model"):
        nonblank(data["company"][key], "company." + key)
    sources = indexed(data["sources"], "sources")
    require(bool(sources), "at least one source PDF required per company")
    for source in sources.values():
        shape(source, ["id", "title", "url", "path", "sha256", "pages", "reporting_period", "publication_date"], SOURCE_PROVENANCE, "source")
        for key in ("title", "reporting_period"):
            nonblank(source[key], "source." + key)
        if source["publication_date"] is not None:
            date_value(source["publication_date"])
        if source.get("report_release_date") is not None:
            date_value(source["report_release_date"])
        for key in ("publication_date_basis", "source_date_note"):
            if key in source:
                require(isinstance(source[key], str), f"source.{key}: string required")
        for key in ("pdf_created_at", "pdf_modified_at"):
            if key in source:
                require(source[key] is None or isinstance(source[key], str), f"source.{key}: original metadata string or null required")
        if source.get("acquired_at") is not None:
            from datetime import datetime
            require(isinstance(source["acquired_at"], str), "source.acquired_at: ISO timestamp or null required")
            stamp = datetime.fromisoformat(source["acquired_at"].replace("Z", "+00:00"))
            require("T" in source["acquired_at"] and stamp.tzinfo is not None, "source.acquired_at: ISO timestamp with timezone required")
        for key in ("first_distribution_of_hash_verified", "assurance_version_equivalence_verified"):
            if key in source:
                require(type(source[key]) is bool, f"source.{key}: boolean required")
        public_url(source["url"])
        require((stub and source["path"] is None) or isinstance(source["path"], str) and source["path"].strip(), "source.path required")
        require((stub and source["sha256"] is None) or isinstance(source["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", source["sha256"]), "source.sha256 required")
        require((stub and source["pages"] is None) or type(source["pages"]) is int and source["pages"] > 0, "source.pages: positive integer required")
    indexed(data["observations"], "observations")
    indexed(data["claims"], "claims")


def date_value(value):
    from datetime import date
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), "ISO date required")
    date.fromisoformat(value)


def load_corpus(path, information_cutoff=None, policy=None):
    path = input_path(path)
    data = read_json(path)
    if isinstance(data, dict) and "company" in data:
        data = {"schema": SCHEMA, "information_cutoff": information_cutoff, "companies": [data]}
    shape(data, ["schema", "information_cutoff", "companies"], ["comparison_policy", "report_notes", "source_status_notes"], "corpus")
    require(data["schema"] == SCHEMA, f"schema must be {SCHEMA}")
    if information_cutoff:
        require(data["information_cutoff"] in (None, information_cutoff), "conflicting information cutoff")
        data["information_cutoff"] = information_cutoff
    if data["information_cutoff"] is not None:
        date_value(data["information_cutoff"])
    require(isinstance(data["companies"], list) and data["companies"], "nonempty companies array required")
    if policy:
        supplied = read_json(policy)
        require("comparison_policy" not in data or data["comparison_policy"] == supplied, "conflicting comparison policy")
        data["comparison_policy"] = supplied
    if "comparison_policy" in data:
        supplied = data["comparison_policy"]
        require(isinstance(supplied, dict) and supplied.get("schema") == "esg-comparison-policy/1" and supplied.get("default") == "context_only", "policy must preserve context_only default")
        require(isinstance(supplied.get("rules"), list), "policy rules required")
        for rule in supplied["rules"]:
            require(isinstance(rule, dict) and isinstance(rule.get("metric_ids"), list) and rule["metric_ids"], "policy metric_ids required")
            require(all(isinstance(mid, str) and mid in METRICS for mid in rule["metric_ids"]), "policy unknown candidate metric")
        canonical(supplied)
    return data, path


def source_path(parent, name):
    require(isinstance(name, str) and name.strip() and "\\" not in name, "invalid source path")
    relative = Path(name)
    require(".." not in relative.parts, "source path traversal forbidden")
    return input_path(relative if relative.is_absolute() else parent / relative)


def validate_corpus(data, parent):
    """Validate physical evidence linkage; meaning remains subject to source review."""
    shape(data, ["schema", "information_cutoff", "companies"], ["comparison_policy", "report_notes", "source_status_notes"], "corpus")
    require(data["schema"] == SCHEMA, f"schema must be {SCHEMA}")
    require(isinstance(data["companies"], list) and data["companies"], "nonempty companies array required")
    if data["information_cutoff"] is not None:
        date_value(data["information_cutoff"])
    canonical(data)  # Reject nonfinite values even in fields not used arithmetically.
    company_ids, source_ids, observation_ids, claim_ids = set(), set(), set(), set()
    files, evidence = {}, {}
    for packet in data["companies"]:
        company_shape(packet)
        cid = packet["company"]["id"]
        require(cid not in company_ids, f"duplicate company ID: {cid}")
        company_ids.add(cid)
        own_sources = indexed(packet["sources"], "sources")
        for sid, source in own_sources.items():
            require(sid not in source_ids, f"globally duplicate source ID: {sid}")
            source_ids.add(sid)
            if data["information_cutoff"] and source["publication_date"] is not None:
                require(source["publication_date"] <= data["information_cutoff"], f"source published after cutoff: {sid}")
            path = source_path(parent, source["path"])
            before = digest(path)
            require(before == source["sha256"], f"source SHA mismatch: {sid}")
            pages = pdf_evidence(path)
            require(len(pages) == source["pages"], f"source physical page count mismatch: {sid}")
            require(digest(path) == before, f"source changed during extraction: {sid}")
            files[sid], evidence[sid] = path, pages

        def linkage(item):
            sid, number = item["source_id"], item["page"]
            require(isinstance(sid, str) and sid in own_sources, "source ref must belong to observation/claim company")
            require(type(number) is int and 1 <= number <= own_sources[sid]["pages"], "physical page ref out of bounds")
            page = evidence[sid][number - 1]
            require(page["text"].strip() or page["has_image"], "blank source page is not evidence")
            return page

        for observation in packet["observations"]:
            shape(observation, ["id", "company_id", "metric_id", "year", "value", "unit", "boundary", "method", "source_id", "page", "evidence_text", "note"], [], "observation")
            oid = observation["id"]
            require(oid not in observation_ids, f"globally duplicate observation ID: {oid}")
            observation_ids.add(oid)
            require(observation["company_id"] == cid, "observation company_id mismatch")
            require(isinstance(observation["metric_id"], str) and observation["metric_id"] in METRICS, "unknown candidate metric_id")
            require(type(observation["year"]) is int and 1 <= observation["year"] <= 9999, "year must be integer 1..9999")
            for key in ("unit", "boundary", "method"):
                nonblank(observation[key], "observation." + key)
            require(isinstance(observation["note"], str), "note must be string")
            require(observation["evidence_text"] is None or isinstance(observation["evidence_text"], str), "evidence_text must be string or null")
            number = observation["value"]
            require(number is None or type(number) in (int, float) and (not isinstance(number, int) or number.bit_length() <= 1023) and math.isfinite(number), "finite numeric value or null required")
            sid, page_number = observation["source_id"], observation["page"]
            if number is None:
                nonblank(observation["note"], "missing observation.note")
                require((sid is None) == (page_number is None), "missing reference must supply both source_id and page or neither")
                if sid is None:
                    require(not observation["evidence_text"], "unlinked missing observation cannot assert evidence text")
                    continue
            page = linkage(observation)
            # Text may originate in OCR rather than pypdf reading order. Physical
            # source SHA/page linkage is verified; quote presence is never a
            # semantic source-truth gate. Preserve the entire submitted text.
            if observation["evidence_text"] is not None:
                require(observation["evidence_text"] == "" or observation["evidence_text"].strip(), "evidence_text cannot be whitespace-only")
        for claim in packet["claims"]:
            shape(claim, ["id", "text", "source_id", "page"], [], "claim")
            require(claim["id"] not in claim_ids, f"globally duplicate claim ID: {claim['id']}")
            claim_ids.add(claim["id"])
            nonblank(claim["text"], "claim.text")
            linkage(claim)
    if "report_notes" in data:
        require(isinstance(data["report_notes"], list), "report_notes: array required")
        for note in data["report_notes"]:
            shape(note, ["metric_id", "text", "source_refs"], ["company_id"], "report note")
            if "company_id" in note:
                require(isinstance(note["company_id"], str) and note["company_id"] in company_ids, "report note: unknown company_id")
            require(isinstance(note["metric_id"], str) and note["metric_id"] in METRICS, "report note: unknown candidate metric")
            nonblank(note["text"], "report note.text")
            require(isinstance(note["source_refs"], list) and note["source_refs"], "report note must have actual source_refs")
            for ref in note["source_refs"]:
                shape(ref, ["source_id", "page"], [], "report note ref")
                sid, number = ref["source_id"], ref["page"]
                require(isinstance(sid, str) and sid in source_ids, "report note: unknown source")
                require(type(number) is int and 1 <= number <= len(evidence[sid]), "report note: physical page out of bounds")
                actual = evidence[sid][number - 1]
                require(actual["text"].strip() or actual["has_image"], "report note: blank page is not evidence")
            if "company_id" in note:
                own = {s["id"] for p in data["companies"] if p["company"]["id"] == note["company_id"] for s in p["sources"]}
                require(any(r["source_id"] in own for r in note["source_refs"]), "report note: scoped company needs at least one own source ref")
    if "source_status_notes" in data:
        require(isinstance(data["source_status_notes"], list), "source status notes: array required")
        seen_status_companies = set()
        for note in data["source_status_notes"]:
            shape(note, ["company_id", "text", "source_refs"], [], "source status note")
            cid = note["company_id"]
            require(isinstance(cid, str) and cid in company_ids, "source status note: unknown company")
            require(cid not in seen_status_companies, "source status note: duplicate company")
            seen_status_companies.add(cid)
            nonblank(note["text"], "source status note.text")
            require(isinstance(note["source_refs"], list) and note["source_refs"], "source status note: source refs required")
            own = {s["id"] for p in data["companies"] if p["company"]["id"] == cid for s in p["sources"]}
            for ref in note["source_refs"]:
                shape(ref, ["source_id", "page"], [], "source status ref")
                sid, number = ref["source_id"], ref["page"]
                require(isinstance(sid, str) and sid in own, "source status note: foreign or unknown source")
                require(type(number) is int and 1 <= number <= len(evidence[sid]), "source status note: physical page out of bounds")
                actual = evidence[sid][number - 1]
                require(actual["text"].strip() or actual["has_image"], "source status note: blank page is not evidence")
    return files, evidence


def portable(data):
    result = copy.deepcopy(data)
    result["companies"].sort(key=lambda packet: packet["company"]["id"])
    for packet in result["companies"]:
        for key in ("sources", "observations", "claims"):
            packet[key].sort(key=lambda item: item["id"])
        for source in packet["sources"]:
            source["path"] = f"sources/{source['sha256']}.pdf"
    return result


def logical_fingerprint(data):
    logical = portable(data)
    for packet in logical["companies"]:
        for source in packet["sources"]:
            source.pop("acquired_at", None)
    return fingerprint(logical)


def verify_tree(out):
    out = no_links(out)
    require(out.is_dir(), "output is not a directory")
    manifest = read_json(out / "system-manifest.json")
    require(manifest.get("schema") == "esg-system-artifacts/1", "unmanaged output directory")
    files = manifest.get("files")
    require(isinstance(files, dict), "manifest files required")
    actual = {path.relative_to(out).as_posix() for path in out.rglob("*") if path.is_file()}
    require(actual == set(files) | {"system-manifest.json"}, "output inventory changed")
    for path in out.rglob("*"):
        no_links(path)
    for name, expected in files.items():
        require(isinstance(name, str) and not Path(name).is_absolute() and ".." not in Path(name).parts, "unsafe artifact name")
        require(digest(input_path(out / name)) == expected, f"cached artifact hash mismatch: {name}")
    return manifest


def guard_out(out, protected):
    out = no_links(out)
    # No outputs in immutable installed releases, or in a directory containing
    # any input/original (even if that file would have a different output name).
    require(not any((p / "release.json").exists() for p in [out, *out.parents]), "cannot write inside an installed/release bundle")
    require(not any((p / "system-manifest.json").exists() for p in out.parents), "cannot write inside a managed artifact tree; choose a sibling output")
    for source in protected:
        source = input_path(source)
        require(source != out and not source.is_relative_to(out), "output would overwrite/contain input or original")
    return out


@contextmanager
def atomic_output(out, protected):
    out = guard_out(out, protected)
    require(not out.exists(), "output already exists; choose a new directory")
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".esg-system-", dir=out.parent))
    try:
        yield temporary
        guard_out(out, protected)
        require(not out.exists(), "output appeared during operation")
        # Rename directory only after all verified artifacts exist. An exclusive
        # sibling lock serializes cooperating publishers; no originals replaced.
        lock = out.parent / ("." + out.name + ".esg-system-lock")
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            require(not out.exists(), "output appeared during publication")
            os.rename(temporary, out)
        finally:
            os.close(fd)
            lock.unlink()
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def seal(out, operation, request_fingerprint, **details):
    files = {path.relative_to(out).as_posix(): digest(path) for path in sorted(out.rglob("*")) if path.is_file() and path.name != "system-manifest.json"}
    manifest = {"schema": "esg-system-artifacts/1", "operation": operation, "request_fingerprint": request_fingerprint,
                "files": files, "independent_review": "not_performed", "runtime_model_telemetry": "unknown", **details}
    write_json(out / "system-manifest.json", manifest)
    return manifest


def reuse(out, protected, operation, request_fingerprint):
    out = guard_out(out, protected)
    if not out.exists():
        return None
    manifest = verify_tree(out)
    require(manifest["operation"] == operation and manifest["request_fingerprint"] == request_fingerprint, "existing output belongs to different input/options; choose a new directory")
    # Manifest alone is insufficient: re-open every cached original PDF.
    for path in out.rglob("*.pdf"):
        pdf_evidence(path)
    return manifest


def extract_files(out, sources, evidence):
    records = []
    (out / "page-text").mkdir(exist_ok=True)
    for source in sources:
        for page in evidence[source["id"]]:
            name = f"page-text/{source['id']}-{page['page']:05d}.txt"
            (out / name).write_text(page["text"], encoding="utf-8")
            records.append({"source_id": source["id"], "source_sha256": source["sha256"], "page": page["page"], "path": name,
                            "sha256": page["sha256"], "has_image": page["has_image"]})
    write_json(out / "page-evidence.json", records)
    return records


def collect(config, out, official_hosts=(), local_snapshots=False):
    config = input_path(config)
    config_hash = digest(config)
    data = read_json(config)
    company_shape(data, stub=not local_snapshots)
    mode = "verified_local_snapshot" if local_snapshots else "http_download"
    local_files, local_evidence = {}, {}
    if local_snapshots:
        require(not official_hosts, "--official-host is a network option; omit it for --local-snapshots")
        for source in data["sources"]:
            title = source["title"]
            require(all(re.search(r"\b" + word + r"\b", title, re.I) for word in ("generated", "web", "snapshot")) and
                    re.search(r"\bnot\s+(?:an?\s+)?issuer(?:[\s-]+original)?[\s-]+pdf\b", title, re.I),
                    "local snapshot title must disclose GENERATED web snapshot and NOT issuer PDF")
        # Verify caller bytes as well as cached copies. No stale local original
        # may be hidden by a valid cache; no network fallback is attempted.
        local_files, local_evidence = validate_corpus({"schema": SCHEMA, "information_cutoff": None, "companies": [data]}, config.parent)
    declared = {public_url(source["url"]).hostname.lower().rstrip(".") for source in data["sources"]}
    for host in official_hosts:
        require(isinstance(host, str) and public_url("https://" + host).hostname == host, "invalid official host")
    allowed_hosts = declared | set(official_hosts)
    originals = [source_path(config.parent, source["path"]) for source in data["sources"] if source["path"] is not None]
    key = fingerprint({"company_file": portable({"schema": SCHEMA, "information_cutoff": None, "companies": [data]}) if all(s["sha256"] for s in data["sources"]) else {**data, "sources": [{**s, "path": None} for s in data["sources"]]}, "mode": mode, "official_hosts": sorted(allowed_hosts), "extractor": extractor_version(), "implementation": implementation()})
    cached = reuse(out, [config, *originals], "collect", key)
    if cached:
        frozen = read_json(Path(out) / "company.json")
        validate_corpus({"schema": SCHEMA, "information_cutoff": None, "companies": [frozen]}, Path(out))
        return cached
    with atomic_output(out, [config, *originals]) as staging:
        (staging / "sources").mkdir()
        frozen = copy.deepcopy(data)
        acquisitions, evidence = [], {}
        for source in frozen["sources"]:
            temporary = staging / (source["id"] + ".pdf")
            if local_snapshots:
                from datetime import datetime, timezone
                shutil.copyfile(local_files[source["id"]], temporary)
                receipt = {"mode": mode, "url": source["url"], "final_url": None,
                           "local_input_path": str(local_files[source["id"]]), "bytes": temporary.stat().st_size,
                           "verified_at": datetime.now(timezone.utc).isoformat(), "http_acquisition": False,
                           "issuer_original_acquired": False, "origin_qualification": source["title"]}
            else:
                receipt = {**download_pdf(source["url"], temporary, allowed_hosts), "mode": mode}
            sha = digest(temporary)
            pages = local_evidence[source["id"]] if local_snapshots else pdf_evidence(temporary)
            require(source["sha256"] is None or sha == source["sha256"], f"download SHA mismatch: {source['id']}")
            require(source["pages"] is None or len(pages) == source["pages"], f"download page count mismatch: {source['id']}")
            source.update(path=f"sources/{sha}.pdf", sha256=sha, pages=len(pages))
            destination = staging / source["path"]
            if destination.exists():
                require(digest(destination) == sha, "content path collision")
                temporary.unlink()
            else:
                temporary.rename(destination)
            acquisitions.append({"source_id": source["id"], **receipt, "sha256": sha, "pages": len(pages), "officiality": "registered_generated_snapshot; independent_source_review_pending" if local_snapshots else "config_declared; independent_source_review_pending"})
            evidence[source["id"]] = pages
        validate_corpus({"schema": SCHEMA, "information_cutoff": None, "companies": [frozen]}, staging)
        write_json(staging / "company.json", frozen)
        write_json(staging / "acquisition.json", acquisitions)
        extract_files(staging, frozen["sources"], evidence)
        require(digest(config) == config_hash, "config changed during collection")
        if local_snapshots:
            for source in data["sources"]:
                require(digest(local_files[source["id"]]) == source["sha256"], "local snapshot changed during collection")
        result = seal(staging, "collect", key, mode=mode, extractor=extractor_version(), sources=len(frozen["sources"]), implementation=implementation())
    return result


def extractor_version():
    from pypdf import __version__
    return "pypdf/" + __version__


def implementation():
    root = Path(__file__).resolve().parents[1]
    return {"pr/esg_system.py": digest(__file__), "schemas/esg-corpus.schema.json": digest(root / "schemas/esg-corpus.schema.json")}


def qualifications(data):
    return {"unknown_publication_date_source_ids": [s["id"] for p in data["companies"] for s in p["sources"] if s["publication_date"] is None],
            "information_cutoff_verified": False,
            "cutoff_scope": "known declared publication dates checked; unknown publication dates and declarations require independent source review",
            "evidence_linkage": "PDF bytes, physical page bounds and page contents verified; text may be OCR; meaning not independently verified"}


def duckdb_module():
    import duckdb
    require(duckdb.__version__ == "1.5.6", "duckdb==1.5.6 required; install adapters/esg-system/requirements.txt in an isolated venv")
    return duckdb


def comparison(data):
    rows, missing = [], []
    present_sources = {s["id"] for p in data["companies"] for s in p["sources"]}
    present_companies = {p["company"]["id"] for p in data["companies"]}
    for metric_id, (label, _) in METRICS.items():
        cells = []
        for packet in data["companies"]:
            cid = packet["company"]["id"]
            observations = sorted((copy.deepcopy(o) for o in packet["observations"] if o["metric_id"] == metric_id), key=lambda o: (o["year"], o["id"]))
            state = "not_registered" if not observations else "reported" if all(o["value"] is not None for o in observations) else "partial_missing" if any(o["value"] is not None for o in observations) else "explicit_missing"
            cells.append({"company_id": cid, "company_name": packet["company"]["name"], "state": state, "observations": observations})
            missing.append({"company_id": cid, "metric_id": metric_id, "state": state, "null_observation_ids": [o["id"] for o in observations if o["value"] is None], "notes": [o["note"] for o in observations if o["value"] is None],
                            "source_refs": [{"source_id": o["source_id"], "page": o["page"]} for o in observations if o["source_id"] is not None]})
        refs = sorted({(o["source_id"], o["page"]) for cell in cells for o in cell["observations"] if o["source_id"] is not None})
        rows.append({"metric_id": metric_id, "candidate_label_ko": label, "comparison_mode": "context_only", "ranking_authorized": False, "unit_compatibility": "not_approved",
                     "limitations": METRICS[metric_id][1], "cells": cells, "source_refs": [{"source_id": sid, "page": page} for sid, page in refs]})
    return {"schema": "esg-context-comparison/1", "information_cutoff": data["information_cutoff"], "comparison_policy": copy.deepcopy(data.get("comparison_policy")), "report_notes": [copy.deepcopy(n) for n in data.get("report_notes", []) if ("company_id" not in n or n["company_id"] in present_companies) and all(r["source_id"] in present_sources for r in n["source_refs"])], "comparison_mode": "context_only", "metrics": rows, "missingness": missing,
            "sources": [copy.deepcopy(s) for p in data["companies"] for s in p["sources"]], "claims": [copy.deepcopy(c) for p in data["companies"] for c in p["claims"]]}


def export_comparison(out, data):
    result = comparison(data)
    write_json(out / "comparison.json", result)
    write_json(out / "missingness.json", result["missingness"])
    fields = ["company_id", "metric_id", "id", "year", "value", "unit", "boundary", "method", "source_id", "page", "evidence_text", "note"]
    with (out / "observations.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for packet in data["companies"]:
            for observation in packet["observations"]:
                row = copy.deepcopy(observation)
                # CSV blanks are ambiguous; spell null explicitly. JSON authoritative.
                for key, value in row.items():
                    if value is None:
                        row[key] = "null"
                    elif isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
                        row[key] = "'" + value
                writer.writerow(row)
    return result


def create_db(path, data, pages, ledger_fingerprint):
    duckdb = duckdb_module()
    db = duckdb.connect(str(path))
    try:
        db.execute("BEGIN TRANSACTION")
        db.execute("CREATE TABLE metadata (key VARCHAR PRIMARY KEY, value VARCHAR NOT NULL)")
        db.execute("CREATE TABLE companies (id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL, business_model VARCHAR NOT NULL, raw_json VARCHAR NOT NULL)")
        db.execute('CREATE TABLE source (id VARCHAR PRIMARY KEY, company_id VARCHAR REFERENCES companies(id), title VARCHAR, url VARCHAR, path VARCHAR, sha256 VARCHAR, pages INTEGER, reporting_period VARCHAR, publication_date VARCHAR, raw_json VARCHAR NOT NULL)')
        db.execute("CREATE TABLE observations (id VARCHAR PRIMARY KEY, company_id VARCHAR REFERENCES companies(id), metric_id VARCHAR, year INTEGER, value DOUBLE, unit VARCHAR, boundary VARCHAR, method VARCHAR, source_id VARCHAR REFERENCES source(id), page INTEGER, evidence_text VARCHAR, note VARCHAR, raw_json VARCHAR NOT NULL)")
        db.execute("CREATE TABLE claims (id VARCHAR PRIMARY KEY, company_id VARCHAR REFERENCES companies(id), text VARCHAR, source_id VARCHAR REFERENCES source(id), page INTEGER, raw_json VARCHAR NOT NULL)")
        db.execute("CREATE TABLE page_evidence (source_id VARCHAR REFERENCES source(id), page INTEGER, source_sha256 VARCHAR, path VARCHAR, sha256 VARCHAR, text VARCHAR, has_image BOOLEAN, PRIMARY KEY(source_id,page))")
        db.executemany("INSERT INTO metadata VALUES (?,?)", [("schema", SCHEMA), ("ledger_fingerprint", ledger_fingerprint), ("duckdb_version", duckdb.__version__), ("extractor", extractor_version())])
        for packet in data["companies"]:
            company = packet["company"]
            db.execute("INSERT INTO companies VALUES (?,?,?,?)", [company["id"], company["name"], company["business_model"], canonical(company)])
        for packet in data["companies"]:
            cid = packet["company"]["id"]
            for source in packet["sources"]:
                db.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?,?,?,?)", [source["id"], cid, *[source[k] for k in ("title", "url", "path", "sha256", "pages", "reporting_period", "publication_date")], canonical(source)])
            for observation in packet["observations"]:
                db.execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", [observation[k] for k in ("id", "company_id", "metric_id", "year", "value", "unit", "boundary", "method", "source_id", "page", "evidence_text", "note")] + [canonical(observation)])
            for claim in packet["claims"]:
                db.execute("INSERT INTO claims VALUES (?,?,?,?,?,?)", [claim["id"], cid, claim["text"], claim["source_id"], claim["page"], canonical(claim)])
        for page in pages:
            db.execute("INSERT INTO page_evidence VALUES (?,?,?,?,?,?,?)", [page[k] for k in ("source_id", "page", "source_sha256", "path", "sha256")] + [(Path(path).parent / page["path"]).read_text(encoding="utf-8"), page["has_image"]])
        db.execute("COMMIT")
        db.execute("CHECKPOINT")
    except Exception:
        try:
            db.execute("ROLLBACK")
        except Exception:
            pass  # Preserve original error if CHECKPOINT failed after COMMIT.
        raise
    finally:
        db.close()


def copy_sources(out, data, files):
    (out / "sources").mkdir()
    for packet in data["companies"]:
        for source in packet["sources"]:
            destination = out / source["path"]
            if not destination.exists():
                shutil.copyfile(files[source["id"]], destination)
            require(digest(destination) == source["sha256"], "source changed during copy")


def ingest(input_file, out, information_cutoff=None, policy=None):
    data, path = load_corpus(input_file, information_cutoff, policy)
    original_hash = digest(path)
    files, evidence = validate_corpus(data, path.parent)
    frozen = portable(data)
    content_key = logical_fingerprint(frozen)
    key = fingerprint({"ledger": frozen, "extractor": extractor_version(), "duckdb": "1.5.6", "implementation": implementation()})
    protected = [path, *files.values(), *([input_path(policy)] if policy else [])]
    cached = reuse(out, protected, "ingest", key)
    if cached:
        validate_corpus(read_json(Path(out) / "ledger.json"), Path(out))
        return cached
    with atomic_output(out, protected) as staging:
        copy_sources(staging, frozen, files)
        pages = extract_files(staging, [s for p in frozen["companies"] for s in p["sources"]], evidence)
        write_json(staging / "ledger.json", frozen)
        create_db(staging / "corpus.duckdb", frozen, pages, content_key)
        export_comparison(staging, frozen)
        require(digest(path) == original_hash, "input changed during ingestion")
        validate_corpus(data, path.parent)
        result = seal(staging, "ingest", key, ledger_fingerprint=content_key, companies=len(frozen["companies"]), candidate_metrics=len(METRICS), duckdb_version="1.5.6", qualifications=qualifications(frozen), implementation=implementation())
    return result


def db_ledger(db_path):
    db_path = input_path(db_path)
    require(db_path.name == "corpus.duckdb", "managed corpus.duckdb required")
    manifest = verify_tree(db_path.parent)
    require(manifest["operation"] == "ingest", "database must belong to an ingested corpus")
    data = read_json(db_path.parent / "ledger.json")
    key = logical_fingerprint(data)
    require(key == manifest["ledger_fingerprint"], "ledger fingerprint mismatch")
    validate_corpus(data, db_path.parent)
    db = duckdb_module().connect(str(db_path), read_only=True, config={"enable_external_access": "false", "autoload_known_extensions": "false", "autoinstall_known_extensions": "false"})
    try:
        require(db.execute("SELECT value FROM metadata WHERE key='ledger_fingerprint'").fetchone() == (key,), "database fingerprint mismatch")
        for table, expected in [("companies", [p["company"] for p in data["companies"]]), ("source", [s for p in data["companies"] for s in p["sources"]]), ("observations", [o for p in data["companies"] for o in p["observations"]]), ("claims", [c for p in data["companies"] for c in p["claims"]])]:
            actual = [json.loads(row[0]) for row in db.execute(f'SELECT raw_json FROM "{table}" ORDER BY id').fetchall()]
            require(actual == sorted(expected, key=lambda x: x["id"]), f"database {table} diverges from authoritative ledger")
    finally:
        db.close()
    return data


def compare(db, out):
    data = db_ledger(db)
    protected = [input_path(db), input_path(Path(db).parent / "ledger.json"), *[source_path(Path(db).parent, s["path"]) for p in data["companies"] for s in p["sources"]]]
    key = fingerprint({"ledger": portable(data), "implementation": implementation()})
    cached = reuse(out, protected, "compare", key)
    if cached:
        return cached
    with atomic_output(out, protected) as staging:
        copy_sources(staging, data, {s["id"]: source_path(Path(db).parent, s["path"]) for p in data["companies"] for s in p["sources"]})
        export_comparison(staging, data)
        write_json(staging / "ledger.json", data)
        result = seal(staging, "compare", key, candidate_metrics=len(METRICS), comparison_mode="context_only")
    return result


def analysis(text):
    return {"kind": "paragraph", "text": "방법론 해설(기업에 대한 주장이 아님): " + text, "classification": "analysis", "non_company_assertion": True}


def display_company(company):
    # Extract an explicitly supplied Korean name/acronym; never invent one.
    korean = re.search(r"\(([^)]*[가-힣][^)]*)\)", company["name"])
    acronym = re.search(r"\(([A-Z][A-Z0-9._-]{1,11})\)", company["name"])
    return korean.group(1) if korean else acronym.group(1) if acronym else company["name"]


def display_scope(boundary, company=None, method=None):
    # This is an extractive navigation label. Complete original semantics remain
    # in metric metadata and explicitly linked companion records.
    if "DX+DS" in boundary:
        return "DX+DS"
    if "DX Division" in boundary:
        return "DX Division"
    if "DS Division" in boundary:
        return "DS Division"
    tier = re.search(r"\b(junior|senior|top)\s+management\b", boundary, re.I)
    if tier:
        return tier.group(0)
    # Extract the supplied measurement name so total and per-person mean do
    # not become identical navigation labels after boundary compaction.
    if method:
        training = re.search(r"\b(Total Training Hours|Average Training Hours)\b", method, re.I)
        if training:
            return training.group(0)
    first = boundary.split(";", 1)[0].strip()
    if company:
        # Remove a supplied repeated issuer prefix so region/workforce qualifiers
        # are visible, rather than truncating all rows to the same issuer name.
        supplied = company["name"].split(" (", 1)[0]
        supplied = re.split(r"\s+(?:Co\.,|Corp\.?|Ltd\.?)", supplied, maxsplit=1)[0]
        for prefix in (supplied, display_company(company)):
            if first.startswith(prefix + " "):
                first = first[len(prefix):].strip()
    first = re.sub(r"\(p\.\s*\d+.*", "", first).strip()
    return first if len(first) <= 14 else first[:14] + "…"


def report_input(data, company=None):
    """Deterministic existing esg-learning-report/1 request; no derived numbers."""
    require(data["information_cutoff"], "report requires corpus information_cutoff or --information-cutoff for a company file")
    selected = [p for p in data["companies"] if company is None or p["company"]["id"] == company]
    require(bool(selected), f"unknown company selection: {company}")
    names = " · ".join(display_company(p["company"]) for p in selected)
    by_company = {p["company"]["id"]: p["company"] for p in selected}
    metrics, claims, sources, pages = [], [], [], []
    source_fields = ("id", "title", "url", "path", "sha256", "pages")
    for packet in selected:
        sources.extend({k: s[k] for k in source_fields} for s in packet["sources"])
        claims.extend(copy.deepcopy(packet["claims"]))
    selected_sources = {s["id"] for s in sources}
    selected_notes = [n for n in data.get("report_notes", []) if (n["company_id"] in by_company if "company_id" in n else any(r["source_id"] in selected_sources for r in n["source_refs"]))]
    note_sources = {r["source_id"] for n in selected_notes for r in n["source_refs"]}
    sources.extend({k: s[k] for k in source_fields} for p in data["companies"] for s in p["sources"] if s["id"] in note_sources - selected_sources)

    def page(title, lead, blocks):
        pages.append({"id": f"page-{len(pages)+1:02d}", "title": title, "kicker": "비공식 학습용 · 원문 관찰과 방법론", "lead": "방법론 안내(기업 주장 아님): " + lead,
                      "classification": "analysis", "non_company_assertion": True, "blocks": blocks})

    page("ESG 공시를 읽는 공통 틀", "20개 후보 지표의 원래 값·단위·범위·방법을 함께 읽는다.", [
        analysis("이 자료는 입력 corpus에서 선정한 공시 관찰을 재구성한 학습 문서다. 전체 데이터 원장과 보고서용 corpus의 포함 관찰은 다를 수 있다. corpus-projection-selection 기록에서 표시 선택과 전체 보존 위치를 확인한다. 규모와 경계가 다른 총량으로 기업의 우열을 결정하지 않는다."),
        analysis("원문 수치는 단위 변환, 합산, 배출 원단위 계산 없이 표시한다. 값이 null이면 미확인·부재·정의 불일치 등을 설명하는 원래 note를 보존한다. 자료가 없다는 사실을 영으로 바꾸거나 공시 자체가 없다는 결론으로 확장하지 않는다."),
        analysis("모든 비교는 context_only다. 같은 후보명·연도·단위가 있어도 호환성과 순위는 승인되지 않는다. 자료의 SHA와 물리 페이지 연결 검사는 출처 동일성과 위치를 확인할 뿐 수치 의미나 번역의 정확성을 보증하지 않는다.")])
    page("근거와 해석의 연결", "등록된 PDF와 페이지, 관찰 ID를 따라 검토한다.", [
        analysis("출처 번호는 등록된 PDF의 1부터 시작하는 물리 페이지다. 발행사 원본과 생성한 웹 스냅샷은 구분하며 출처 제목의 설명을 유지한다. 해시는 등록 파일의 동일성을 확인할 뿐 발행사 원본을 취득했다는 증명이 아니다. 생성 스냅샷의 페이지 번호를 발행사 원본의 번호로 해석하지 않는다. UTF-8 추출문은 동반 자료이며 이미지 공시는 시각 검토가 별도로 필요하다."),
        analysis("관찰마다 원래 경계와 산정 방법을 붙인다. 그룹 전체, 특정 사업부, 모회사, 특정 지역의 자료를 하나의 모집단으로 묶지 않는다. 노동 지표는 임직원·도급인과 시점의 정의를, 환경 지표는 활동과 조직 경계를 먼저 확인한다. series-bindings.json에서 boundary, method, observations.note 전체를 확인한다."),
        analysis("source_id와 page가 있는 claim은 제출된 문구를 그대로 인용한 주장이다. 검사는 독립적인 진위 판정이 아니다. 본문은 모든 관찰 주석을 인쇄하지 않는다. 주요 해석 제한은 제공된 검토 문구를 표시하며, 원래 note 전체는 동반 원장에서 확인한다. 방법론 문장은 기업 사실을 추가하지 않고 별도 분류한다.")])
    missing_blocks = [analysis("등록 관찰이 없는 후보와 null 관찰을 구분한다. not_registered는 이 corpus에 기록이 없다는 상태일 뿐 공시가 없다는 주장이나 영 실적이 아니다. explicit_missing과 partial_missing은 note 및 제공된 원문 위치를 읽어 원인을 확인한다.")]
    identity_refs = sorted({(packet["sources"][0]["id"], 1) for packet in selected if packet["sources"]})
    if identity_refs:
        missing_blocks.append({"kind": "table", "headers": ["선택 목록 번호", "등록 회사"],
                               "rows": [[str(i), display_company(p["company"])] for i, p in enumerate(selected, 1)],
                               "source_refs": [{"source_id": sid, "page": number} for sid, number in identity_refs]})
    states = comparison({**data, "companies": selected})["missingness"]
    for packet_number, packet in enumerate(selected, 1):
        missing = [r for r in states if r["company_id"] == packet["company"]["id"] and r["state"] != "reported"]
        missing_blocks.append(analysis("선택 목록 " + str(packet_number) + "번 입력 기록의 상태: " + ("; ".join(r["metric_id"] + "=" + r["state"] for r in missing) or "모든 후보에 숫자 관찰이 등록됨") + ". 이 표현은 입력 등록 상태를 설명하며 해당 기업의 공시 완전성이나 준수 여부에 관한 판단이 아니다."))
    page("결측과 미등록을 읽는 방법", "빈칸을 영으로 채우지 않고 증거의 한계를 보존한다.", missing_blocks)
    # Every original claim is displayed, without generated business-model claims.
    batch_size = max(4, math.ceil(len(claims) / 7))
    batches = [claims[i:i+batch_size] for i in range(0, len(claims), batch_size)] or [[]]
    for batch in batches:
        blocks = [analysis("이 페이지의 인용 문구는 입력 claim을 변경 없이 표시한다. 주장이 연결된 원문 페이지에서 같은 의미로 뒷받침되는지 독립 원문 검토가 필요하다. 위치 연결만으로 인과관계, 성과, 준수 또는 보증 결론을 인정하지 않는다. CLI는 독립 검토를 수행·인증하지 않으며 실제 검토는 호스트 기록을 참조한다.")]
        blocks += [{"kind": "paragraph", "text": c["text"], "claim_ids": [c["id"]]} for c in batch]
        if not batch:
            blocks.append(analysis("입력 corpus에는 서술형 claim이 등록되지 않았다. 이 등록 상태를 기업에 대한 사실 주장으로 확대하지 않는다. 숫자 관찰의 원문 위치는 각 후보 지표 페이지에서 별도로 연결한다."))
        page("제출된 주장과 원문 위치", "원문 의미의 검토를 위해 제출 문구와 근거를 연결한다.", blocks)
    for metric_id, (label, explanation) in METRICS.items():
        chosen, refs, groups = [], set(), {}
        for packet in selected:
            for o in sorted(packet["observations"], key=lambda item: (item["year"], item["id"])):
                if o["metric_id"] != metric_id:
                    continue
                if o["source_id"] is not None:
                    refs.add((o["source_id"], o["page"]))
                group_key = (packet["company"]["id"], o["unit"], o["boundary"], o["method"])
                # Repeated observations in one year must remain distinct. Start
                # another row instead of selecting/overwriting the last value.
                variants = groups.setdefault(group_key, [])
                target = next((variant for variant in variants if o["year"] not in variant), None)
                if target is None:
                    target = {}
                    variants.append(target)
                target[o["year"]] = o
        # The report adapter needs unique years in each metric. Keep boundary /
        # method variants separate, including repeated same-year observations.
        for (cid, unit, boundary, method), variants in groups.items():
            binding = fingerprint({"company_id": cid, "metric_id": metric_id, "unit": unit, "boundary": boundary, "method": method})[:12]
            for variant_number, variant in enumerate(variants, 1):
                mid = "series_" + binding + "_" + str(variant_number)
                values = []
                for year, o in sorted(variant.items()):
                    value = {"year": year, "value": o["value"]}
                    if o["source_id"] is not None:
                        value.update(source_id=o["source_id"], page=o["page"])
                    values.append(value)
                metrics.append({"id": mid, "label": display_company(by_company[cid]) + " · " + display_scope(boundary, by_company[cid], method) + " · " + label, "unit": unit, "boundary": boundary, "method": method, "values": values,
                                "footnotes": ["관찰별 원문 주석과 추출문 전체는 동반 원장과 계열 기록에 보존."]})
                chosen.append(mid)
        blocks = [analysis(explanation)]
        if chosen and refs:
            years = sorted({year for variants in groups.values() for variant in variants for year in variant})
            # Multi-company exhibits focus on the latest two registered years;
            # every original year remains in metrics, the ledger and companions.
            if len(selected) > 1:
                years = years[-2:]
            rows = []
            for group_key, variants in groups.items():
                cid, unit, boundary, method = group_key
                for variant in variants:
                    # Every cell's observation ID resolves full unabridged scope,
                    # method, note, evidence text and original physical locator.
                    cells = [display_company(by_company[cid]) + " · " + display_scope(boundary, by_company[cid], method), unit]
                    for year in years:
                        o = variant.get(year)
                        cells.append("미등록" if o is None else "null" if o["value"] is None else str(o["value"]))
                    rows.append(cells)
            blocks.append({"kind": "table", "headers": ["회사 · 보고 범위", "원래 단위", *[str(year) for year in years]], "rows": rows, "metric_ids": chosen, "source_refs": [{"source_id": sid, "page": number} for sid, number in sorted(refs)]})
        elif chosen:
            blocks.append({"kind": "metrics", "ids": chosen})
        else:
            blocks.append(analysis("선택한 회사의 입력 corpus에 이 후보의 관찰이 등록되지 않았다. 보고기간이나 단위를 추정해 수치를 만들지 않는다. missingness.json에서 not_registered를 확인하고 원문 재검색의 대상과 정의 확인 과제를 별도로 남긴다."))
        if not chosen:
            blocks.append(analysis("미등록은 관찰 없음이며 null과 영과는 구분한다. 필요한 공시 정의와 조직 경계를 원문에서 확인한 뒤 다음 검토 과제를 정한다. 단위나 이름의 유사성만으로 대체값을 만들지 않는다."))
        cautions = [n for n in selected_notes if n["metric_id"] == metric_id]
        if cautions:
            note_refs = sorted({(r["source_id"], r["page"]) for n in cautions for r in n["source_refs"]})
            blocks.append({"kind": "table", "headers": ["주요 해석 제한 · 제공된 검토 문구"], "rows": [[n["text"]] for n in cautions], "source_refs": [{"source_id": sid, "page": number} for sid, number in note_refs]})
        page("후보 · " + label, "각 숫자의 의미는 단위·범위·방법과 원문 페이지를 함께 읽어야 한다.", blocks)
    years = sorted({o["year"] for p in selected for o in p["observations"]})
    if len(selected) > 1 and len(years) > 2:
        pages[0]["blocks"].insert(0, analysis("여러 회사의 비교 표는 후보별 최신 두 등록 연도를 표시한다. 더 이른 연도의 원래 값과 정의는 원장·계열 기록에 그대로 보존한다. 미등록·null·영을 구분하며, 표시 연도 선택으로 모집단이나 정의의 호환성을 승인하지 않는다."))
    # Short factual register horizon in repeated footers; full source reporting
    # periods stay unchanged in the ledger and receive a source-bound table.
    periods = []
    for packet in selected:
        for source in packet["sources"]:
            title_label = re.search(r"\b(Sustainability Report|Annual Report)\b", source["title"], re.I)
            source_label = title_label.group(0) if title_label else source["id"]
            periods.append([display_company(packet["company"]) + " · " + source_label, source["reporting_period"]])
    period_locators = {}
    for packet in selected:
        for original in [*packet["claims"], *packet["observations"]]:
            if original["source_id"] is not None:
                period_locators.setdefault(original["source_id"], original["page"])
    period_refs = sorted(period_locators.items())
    if period_refs:
        pages[1]["blocks"].append({"kind": "table", "headers": ["등록 회사", "입력 출처 보고기간 (원문 재확인)"], "rows": periods, "source_refs": [{"source_id": sid, "page": number} for sid, number in period_refs]})
        source_status = []
        supplied_status = {n["company_id"]: n for n in data.get("source_status_notes", [])}
        status_refs = set(period_refs)
        for packet in selected:
            generated = [s for s in packet["sources"] if "GENERATED" in s["title"]]
            if len(generated) == len(packet["sources"]):
                status = "생성 텍스트 스냅샷만 등록됨. 발행사 원본 PDF로 간주하지 않음. 추가 원천과 지속가능성보고서를 구분하며 원본 취득 상태는 별도 근거를 확인한다."
            elif generated:
                status = "등록 PDF와 생성 텍스트 스냅샷이 함께 있음. 각 출처의 제목과 원본 취득 근거를 구분해 확인한다."
            else:
                status = "PDF 자료 등록. 확보 판본과 보고기간·보증 적용 범위는 별도 원문 검토 기록에서 확인한다."
            if packet["company"]["id"] in supplied_status:
                supplied = supplied_status[packet["company"]["id"]]
                status = supplied["text"]
                status_refs.update((r["source_id"], r["page"]) for r in supplied["source_refs"])
            source_status.append([display_company(packet["company"]), status])
        pages[0]["blocks"].append({"kind": "table", "headers": ["등록 회사", "입력 근거 형태 · 원본 취득 구분"], "rows": source_status, "source_refs": [{"source_id": sid, "page": number} for sid, number in sorted(status_refs)]})
    unknown = [s["id"] for p in selected for s in p["sources"] if s["publication_date"] is None]
    if unknown:
        pages[1]["blocks"].append(analysis("입력 출처의 정확한 PDF 버전 발행일이 알려지지 않은 경우 정보 기준일 이전 유통 여부의 확인이 필요하다. 원장의 null을 발표일이나 파일 생성일로 대체하지 않는다. 해당 출처 목록과 날짜 근거는 동반 원장의 sources.publication_date와 source_date_note에서 확인한다."))
    period_label = (str(years[0]) if len(years) == 1 else str(years[0]) + "–" + str(years[-1])) if years else "등록 관찰연도 없음"
    return {"schema": "esg-learning-report/1", "company": names, "title": "ESG 공시 맥락 비교", "reporting_period": "등록 관찰연도 " + period_label, "information_cutoff": data["information_cutoff"], "status": "비공식 학습용", "sources": sources, "metrics": metrics, "claims": claims, "pages": pages,
            "framework": {"basis": "원문 연결·맥락 비교 학습", "qualification": "순위·호환성 미승인. CLI는 독립 검토를 인증하지 않음; 실제 검토는 호스트 기록."}}


def series_bindings(data, company=None):
    groups = {}
    for packet in data["companies"]:
        if company is not None and packet["company"]["id"] != company:
            continue
        for o in packet["observations"]:
            fields = {k: o[k] for k in ("company_id", "metric_id", "unit", "boundary", "method")}
            key = fingerprint(fields)[:12]
            entry = groups.setdefault(key, {"series_id": key, **fields, "observations": []})
            require(all(entry[k] == fields[k] for k in fields), "series ID collision")
            entry["observations"].append(copy.deepcopy(o))
    return sorted(groups.values(), key=lambda entry: (entry["metric_id"], entry["company_id"], entry["series_id"]))


def report(input_file, out, company=None, html_only=False, chromium=None, node=None, playwright_module=None, information_cutoff=None, policy=None):
    from . import esg
    data, path = load_corpus(input_file, information_cutoff, policy)
    original_hash = digest(path)
    files, _ = validate_corpus(data, path.parent)
    frozen = portable(data)
    generated = report_input(frozen, company)
    key = fingerprint({"report_input": generated, "corpus": frozen, "html_only": html_only, "chromium": chromium, "node": node, "playwright_module": playwright_module, "adapter": esg.adapter_hashes(), "implementation": implementation()})
    protected = [path, *files.values(), *([input_path(policy)] if policy else [])]
    cached = reuse(out, protected, "report", key)
    if cached:
        checks = esg.check(Path(out) / "report-input.json", Path(out) / "report", html_only=html_only)
        require(checks["ok"], "cached report failed adapter checks: " + "; ".join(checks["errors"]))
        return cached
    with atomic_output(out, protected) as staging:
        copy_sources(staging, frozen, files)
        write_json(staging / "ledger.json", frozen)
        write_json(staging / "report-input.json", generated)
        write_json(staging / "series-bindings.json", series_bindings(frozen, company))
        export_comparison(staging, {**frozen, "companies": [p for p in frozen["companies"] if company is None or p["company"]["id"] == company]})
        checks = esg.build(staging / "report-input.json", staging / "report", html_only, chromium, node, playwright_module)
        require(checks["ok"], "report adapter failed: " + "; ".join(checks["errors"]))
        require(digest(path) == original_hash, "input changed during report generation")
        validate_corpus(data, path.parent)
        result = seal(staging, "report", key, company_selection=company or "all", authored_pages=len(generated["pages"]), pdf_success=checks["pdf_success"], stage=checks["stage"], qualifications=qualifications(frozen), implementation=implementation())
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("collect", help="download declared official PDFs; extract hash-bound UTF-8 pages")
    command.add_argument("--config", required=True)
    command.add_argument("--out", required=True)
    command.add_argument("--official-host", action="append", default=[], help="additional publisher CDN host allowed for redirects; source URL hosts are declared by config")
    command.add_argument("--local-snapshots", action="store_true", help="explicitly verify/copy existing generated web snapshot PDFs with required path/SHA/pages; no HTTP or issuer-original acquisition")
    for name in ("ingest", "report"):
        command = sub.add_parser(name)
        command.add_argument("--input", required=True)
        command.add_argument("--out", required=True)
        command.add_argument("--information-cutoff", help="required for single-company reports; never infer a cutoff from current time")
        command.add_argument("--policy", help="optional comparison-policy.json; embedded unchanged in the portable ledger")
        if name == "report":
            command.add_argument("--company", help="omit for combined report; otherwise exact company ID")
            command.add_argument("--html-only", action="store_true")
            command.add_argument("--chromium")
            command.add_argument("--node")
            command.add_argument("--playwright-module")
    command = sub.add_parser("compare")
    command.add_argument("--db", required=True)
    command.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            result = collect(args.config, args.out, args.official_host, args.local_snapshots)
        elif args.command == "ingest":
            result = ingest(args.input, args.out, args.information_cutoff, args.policy)
        elif args.command == "compare":
            result = compare(args.db, args.out)
        else:
            result = report(args.input, args.out, args.company, args.html_only, args.chromium, args.node, args.playwright_module, args.information_cutoff, args.policy)
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error), "independent_review": "not_performed", "runtime_model_telemetry": "unknown"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
