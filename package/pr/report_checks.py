"""Deterministic developer regression checks, separate from protected evaluation.

All public checks raise ReportCheckError (a ValueError) on malformed or
inconsistent input. They neither read old runs nor approve economic assumptions.
DCF contract: trillion KRW, million shares, annual rates as fractions, a
365-day stub and midyear explicit discounting. Callers must supply literal
inputs independently of reported outputs. Hashes need a trusted upstream seal.
Typed claims must enumerate every material conclusion; this module cannot
discover omitted prose claims or establish evidence truth or reviewer judgment.
Text retention covers registered blocks and multiplicity, not visual fidelity,
link targets, reading order, or the correctness of the extraction process.
"""
from collections import Counter
from datetime import date
from functools import wraps
import hashlib
import math
from pathlib import Path
import re
import unicodedata


class ReportCheckError(ValueError):
    """An actionable field-specific regression failure."""


def _fail(field, message):
    raise ReportCheckError(f"{field}: {message}")


def _mapping(value, field):
    if not isinstance(value, dict):
        _fail(field, "object required")
    return value


def _get(obj, key, field):
    _mapping(obj, field)
    if key not in obj:
        _fail(f"{field}.{key}", "required field missing")
    return obj[key]


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(field, "finite numeric value required")
    try:
        finite = math.isfinite(value)
    except (OverflowError, TypeError):
        finite = False
    if not finite:
        _fail(field, "finite numeric value required")
    return value


def _num(obj, key, field):
    return _number(_get(obj, key, field), f"{field}.{key}")


def _list(value, field):
    if not isinstance(value, list) or not value:
        _fail(field, "nonempty list required")
    return value


def _sum(obj, key, field):
    return math.fsum(_number(x, f"{field}.{key}[{i}]")
                     for i, x in enumerate(_list(_get(obj, key, field), f"{field}.{key}")))


def _equal(actual, expected, field):
    _number(actual, field)
    _number(expected, field + ".expected")
    if not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-8):
        _fail(field, f"expected {expected:.12g}, got {actual:.12g}")


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail(field, "nonempty text required")
    return value


def _date(value, field):
    _text(value, field)
    try:
        return date.fromisoformat(value)
    except ValueError:
        _fail(field, "ISO date required")


def _guard_input_errors(check):
    """Keep numerical overflow and malformed containers in the check API."""
    @wraps(check)
    def guarded(*args, **kwargs):
        try:
            return check(*args, **kwargs)
        except ReportCheckError:
            raise
        except (ArithmeticError, TypeError, ValueError) as exc:
            _fail(check.__name__, f"invalid input or numerical range: {exc}")
    return guarded


@_guard_input_errors
def check_value_components(literals, values, forecast):
    """Recompute stub/annual/terminal PV from literals; return expected values.

Required literal fields are demonstrated in defect-suite.json. Terminal FCFF
uses the last year's margin/reinvestment rates and terminal revenue change;
it is deliberately not last explicit FCFF multiplied by (1 + g).
"""
    f = "literals"
    valuation = _date(_get(literals, "valuation_date", f), f + ".valuation_date")
    year = _num(literals, "first_year", f)
    if int(year) != year or not 2 <= year <= 9999:
        _fail(f + ".first_year", "integer calendar year required")
    days = (date(int(year) - 1, 12, 31) - valuation).days
    if not 0 <= days <= 365:
        _fail(f + ".valuation_date", "stub must be between 0 and 365 days")
    rate, g, tax = (_num(literals, k, f) for k in ("wacc", "terminal_growth", "tax_rate"))
    if not rate > g > -1 or not 0 <= tax <= 1:
        _fail(f, "require wacc > terminal_growth > -1 and tax in [0, 1]")
    half = _sum(literals, "half_year_revenue", f)
    profit = _list(_get(literals, "stub_operating_profit", f), f + ".stub_operating_profit")
    if half <= 0 or len(profit) != 2:
        _fail(f, "positive half-year revenue and two operating-profit inputs required")
    margin = (_number(profit[0], "stub_profit[0]") - _number(profit[1], "stub_profit[1]")) / half
    base = 2 * half
    annual_stub = base * (margin * (1 - tax) + _num(literals, "stub_da_rate", f)
                         - _num(literals, "stub_capex_rate", f)) - _num(literals, "stub_nwc", f)
    stub = days / 365
    expected = dict(stub_days=days, stub_years=stub, stub_fcff=annual_stub * stub,
                    stub_period=stub / 2)
    expected["stub_pv"] = expected["stub_fcff"] / (1 + rate) ** expected["stub_period"]
    annual = _list(_get(literals, "annual", f), f + ".annual")
    forecast = _list(forecast, "forecast")
    if len(annual) != len(forecast):
        _fail("forecast", "length differs from literal annual inputs")
    pvs, previous = [], base
    for i, (row, report) in enumerate(zip(annual, forecast)):
        prefix = f"literals.annual[{i}]"
        growth, margin, da, capex, wc = (_num(row, k, prefix) for k in
                                        ("growth", "margin", "da_rate", "capex_rate", "nwc_rate"))
        if growth <= -1:
            _fail(prefix + ".growth", "must exceed -1")
        revenue = previous * (1 + growth)
        ebit = revenue * margin
        nwc = (revenue - previous) * wc
        fcff = ebit * (1 - tax) + revenue * da - revenue * capex - nwc
        period = stub + .5 + i
        df = (1 + rate) ** -period
        row_expected = dict(year=int(year) + i, revenue=revenue, growth=growth,
                            margin=margin, ebit=ebit, tax=ebit * tax, nopat=ebit * (1 - tax),
                            da=revenue * da, capex=revenue * capex, nwc=nwc, fcff=fcff,
                            period=period, discount_factor=df, pv=fcff * df)
        for key, value in row_expected.items():
            _equal(_get(report, key, f"forecast[{i}]"), value, f"forecast[{i}].{key}")
        pvs.append(fcff * df)
        previous = revenue
    terminal_revenue = previous * (1 + g)
    terminal_fcff = terminal_revenue * (margin * (1 - tax) + da - capex) - (terminal_revenue - previous) * wc
    expected.update(explicit_pv=math.fsum(pvs), terminal_period=stub + len(annual),
                    terminal_fcff=terminal_fcff, terminal_value=terminal_fcff / (rate - g))
    expected["terminal_pv"] = expected["terminal_value"] / (1 + rate) ** expected["terminal_period"]
    ev = math.fsum(expected[k] for k in ("stub_pv", "explicit_pv", "terminal_pv"))
    if ev <= 0:
        _fail("operating_ev", "positive EV required for terminal-share diagnostic")
    expected.update(operating_ev=ev, terminal_share=expected["terminal_pv"] / ev)
    for key, value in expected.items():
        _equal(_get(values, key, "values"), value, "values." + key)
    return expected


@_guard_input_errors
def check_equity_bridge(bridge, shares, inputs, *, operating_ev, forward_price):
    """Recompute assets/liabilities, subtract NCI once and treasury per class.

Pass operating_ev returned by check_value_components, not a report pass flag.
Input asset/liability amounts are trillion KRW; shares are millions.
"""
    f = "bridge_inputs"
    nfa = (_sum(inputs, "consolidated_assets", f) - _sum(inputs, "consolidated_liabilities", f)
           - _sum(inputs, "finance_nfa_assets", f) + _sum(inputs, "finance_nfa_liabilities", f))
    finance = (_num(inputs, "finance_assets", f) - _num(inputs, "finance_liabilities", f)) * _num(inputs, "finance_factor", f)
    associates = (_num(inputs, "associate_assets", f) - _num(inputs, "associate_liabilities", f)) * _num(inputs, "associate_factor", f)
    nci = _num(inputs, "nci", f)
    if nci < 0:
        _fail(f + ".nci", "deduction magnitude must be nonnegative")
    total = math.fsum([nfa, finance, associates, -nci])
    expected = dict(nonfinancial_nfa=nfa, finance_equity=finance, associates=associates,
                    nci_deduction=nci, total=total, industrial_ev=_number(operating_ev, "operating_ev"),
                    parent_equity=operating_ev + total)
    for key, value in expected.items():
        _equal(_get(bridge, key, "bridge"), value, "bridge." + key)
    issued, treasury = [], []
    for i, row in enumerate(_list(_get(inputs, "share_classes", f), f + ".share_classes")):
        a, b = _num(row, "issued", f"share_classes[{i}]"), _num(row, "treasury", f"share_classes[{i}]")
        if not 0 <= b <= a:
            _fail(f"share_classes[{i}]", "require 0 <= treasury <= issued")
        issued.append(a)
        treasury.append(b)
    expected_shares = dict(issued=math.fsum(issued), treasury=math.fsum(treasury),
                           outstanding=math.fsum(issued) - math.fsum(treasury))
    if expected_shares["outstanding"] <= 0:
        _fail("shares.outstanding", "positive issued minus treasury required")
    for key, value in expected_shares.items():
        _equal(_get(shares, key, "shares"), value, "shares." + key)
    price = expected["parent_equity"] * 1e6 / expected_shares["outstanding"]
    _equal(forward_price, price, "forward_price")
    return dict(bridge=expected, shares=expected_shares, forward_price=price)


@_guard_input_errors
def check_hashes(artifacts, expected):
    """Exact label-to-Path/bytes bindings; compare to pre-existing SHA-256 seal.

Neither builds a new seal from current artifacts nor searches previous runs.
Missing, extra and empty bindings fail. Hash equality is integrity, not truth.
"""
    _mapping(artifacts, "artifacts")
    _mapping(expected, "expected_hashes")
    if not artifacts or artifacts.keys() != expected.keys():
        _fail("hash_bindings", "nonempty identical artifact and seal label sets required")
    for label, artifact in artifacts.items():
        digest = _text(expected[label], f"hashes.{label}")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            _fail(f"hashes.{label}", "lowercase SHA-256 required")
        if isinstance(artifact, bytes):
            actual = hashlib.sha256(artifact).hexdigest()
        elif isinstance(artifact, Path):
            try:
                h = hashlib.sha256()
                with artifact.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(chunk)
                actual = h.hexdigest()
            except OSError as exc:
                _fail(f"hashes.{label}", f"cannot read artifact: {exc}")
        else:
            _fail(f"hashes.{label}", "Path or bytes required")
        if actual != digest:
            _fail(f"hashes.{label}", f"stale SHA-256: expected {digest}, got {actual}")


@_guard_input_errors
def check_claim_scope(record):
    """Validate report-check-claims/1 typed metadata, never keyword economics.

Equivalent argument-record envelope: diagnostic_scope, source_classes, claims.
Evidence includes classification, locator, artifact_id/hash, as_of, horizon,
perimeter. An evidence declaration alone is not independently verified truth.
Unqualified investment judgments require separate review outside this module.
"""
    if _get(record, "schema", "claims_record") != "report-check-claims/1":
        _fail("claims_record.schema", "report-check-claims/1 required")
    scope = _get(record, "diagnostic_scope", "claims_record")
    mode = _text(_get(scope, "mode", "diagnostic_scope"), "diagnostic_scope.mode")
    if mode not in {"conditional_model_diagnostic", "evaluated_market_comparison"}:
        _fail("diagnostic_scope.mode", "unknown scope")
    cutoff = _date(_get(scope, "cutoff", "diagnostic_scope"), "diagnostic_scope.cutoff")
    for key in ("horizon", "perimeter"):
        _text(_get(scope, key, "diagnostic_scope"), "diagnostic_scope." + key)
    allowed_kinds = {"model_diagnostic", "live_market", "consensus", "investment_judgment"}
    exclusions = _get(scope, "exclusions", "diagnostic_scope")
    if not isinstance(exclusions, list) or any(not isinstance(x, str) or x not in allowed_kinds for x in exclusions):
        _fail("diagnostic_scope.exclusions", "list of known claim kinds required")
    if mode == "conditional_model_diagnostic" and not {"live_market", "consensus", "investment_judgment"} <= set(exclusions):
        _fail("diagnostic_scope.exclusions", "diagnostic must exclude unqualified market/consensus/investment conclusions")
    classes = {"frozen_model_input", "company_actual", "management_guidance", "management_target",
               "single_broker_forecast", "market_consensus", "verified_market_price"}
    evidence = {}
    for source in _list(_get(record, "source_classes", "claims_record"), "source_classes"):
        sid = _text(_get(source, "id", "source"), "source.id")
        if sid in evidence:
            _fail("source.id", "duplicate evidence ID: " + sid)
        classification = _text(_get(source, "classification", "source"), "source.classification")
        if classification not in classes:
            _fail("source.classification", "unknown or missing evidence classification")
        for key in ("locator", "artifact_id", "horizon", "perimeter"):
            _text(_get(source, key, "source"), "source." + key)
        digest = _text(_get(source, "artifact_sha256", "source"), "source.artifact_sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            _fail("source.artifact_sha256", "lowercase SHA-256 required")
        as_of = _date(_get(source, "as_of", "source"), "source.as_of")
        if as_of > cutoff:
            _fail("source.as_of", "evidence falls after information cutoff")
        evidence[sid] = source
    ids = set()
    for claim in _list(_get(record, "claims", "claims_record"), "claims"):
        cid = _text(_get(claim, "id", "claim"), "claim.id")
        if cid in ids:
            _fail("claim.id", "duplicate claim ID: " + cid)
        ids.add(cid)
        kind = _text(_get(claim, "kind", "claim"), "claim.kind")
        status = _text(_get(claim, "status", "claim"), "claim.status")
        if kind not in allowed_kinds or status not in {"conditional", "unqualified"}:
            _fail("claim", "known kind and conditional/unqualified status required")
        refs = _list(_get(claim, "evidence_ids", "claim"), "claim.evidence_ids")
        if any(not isinstance(s, str) or s not in evidence for s in refs):
            _fail("claim.evidence_ids", "unknown evidence reference")
        qualifications = _get(claim, "qualifications", "claim")
        if not isinstance(qualifications, list):
            _fail("claim.qualifications", "list required")
        for q in qualifications:
            _text(q, "claim.qualifications")
        if status == "conditional":
            if not qualifications:
                _fail("claim.qualifications", "conditional claim needs explicit qualifications")
            continue
        if kind in exclusions or kind == "investment_judgment":
            _fail("claim.scope", "unqualified " + kind + " exceeds diagnostic scope; independent review required")
        required = {"live_market": "verified_market_price", "consensus": "market_consensus"}.get(kind)
        if required:
            sources = [evidence[s] for s in refs if evidence[s]["classification"] == required]
            if not sources:
                _fail("claim.classification", kind + " requires " + required + " evidence")
            if not any(s["as_of"] == scope["cutoff"] and s["horizon"] == scope["horizon"]
                       and s["perimeter"] == scope["perimeter"] for s in sources):
                _fail("claim.evidence_scope", "cutoff/horizon/perimeter must match for unqualified comparison")


def normalize_retained_text(text):
    """NFKC and whitespace folding only; punctuation/numbers remain material."""
    _text(text, "retained_text")
    return "".join(unicodedata.normalize("NFKC", text).split())


@_guard_input_errors
def check_pdf_text(source_blocks, extracted_text):
    """Require each registered source block, including duplicate multiplicity.

Use paragraphs, citations and individual cells, not whole table rows. Do not
register auto-renumbered exhibit labels. Only extraction whitespace is ignored.
Caller must seal the PDF, source-block manifest and extraction receipt together.
"""
    blocks = _list(source_blocks, "source_blocks")
    target = normalize_retained_text(extracted_text)
    required = Counter(normalize_retained_text(block) for block in blocks)
    for block, count in required.items():
        actual = target.count(block)
        if actual < count:
            _fail("pdf_text", f"source text loss: expected {count} occurrences, got {actual}; {block[:80]!r}")
