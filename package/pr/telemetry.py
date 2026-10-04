"""Observational rollout telemetry; no message/tool bodies or reasoning are exported.

CLI: python -m pr.telemetry --rollout session.jsonl --events receipts.jsonl \
    --output telemetry.json

JSONL native records: session_meta, turn_context, token_usage_record, compacted.
Usage payloads contain response_id and usage counters. Explicit session_id, role,
round_id and scope (main/child/compaction) override session/turn metadata. Missing
scope stays unknown: a compaction marker does not relabel neighboring responses.
Session metadata may include parent_session_id or source.subagent.thread_spawn.

Optional explicit event payloads (top-level type or event_msg.payload.type):
* session_spawn / first_task_action: session_id, timestamp, optional role/round_id.
* tool_read_receipt: receipt_id, resource_id, content_hash (SHA256), range
  {unit: bytes|lines, start: integer, end: integer} (half-open), purpose,
  truncated: bool|null, followup_of: [receipt_id]. No read text is accepted/exported.
* review_scope: universe_complete: bool. This asserts a complete candidate finding
  universe ONLY for that exact role/session/round; do not infer it from findings.
* review_finding: finding_id, artifact_hash, criteria_hash, detected: bool|null,
  adjudicated_status: valid|invalid|unknown, adjudication_id,
  adjudicator_session_id. Independent adjudication is required for classification.
* review_transition: transition_id, finding_id, transition: reopen|reversal,
  previous_artifact_hash, artifact_hash, previous_criteria_hash, criteria_hash,
  classification: justified|unjustified|unknown, justification_kind:
  regression|new_evidence|correction, evidence_ref, adjudication_id,
  adjudicator_session_id. A changed artifact alone never justifies a transition.

Counters are exact partial observations, never costs. Reasoning is a subset of
output, cached input is a subset of input. First input is an observed proxy, never
an estimate of a fixed prompt floor. Truncation links express correlation only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

from .util import ContractError, canonical, write_json

FIELDS = ("input_tokens", "cached_input_tokens", "uncached_input_tokens",
          "output_tokens", "reasoning_output_tokens", "total_tokens")
EVENTS = {"session_spawn", "first_task_action", "tool_read_receipt",
          "review_finding", "review_transition", "review_scope", "compacted"}


def _label(value):
    return value if isinstance(value, str) and value else None


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _counter(value):
    if value is not None and (type(value) is not int or value < 0):
        raise ContractError("Token counters must be nonnegative integers or null")
    return value


def _usage(raw):
    if not isinstance(raw, dict):
        raise ContractError("Usage must be an object")
    values = {key: _counter(raw.get(key)) for key in FIELDS}
    for key, container, nested in (
        ("cached_input_tokens", "input_tokens_details", "cached_tokens"),
        ("reasoning_output_tokens", "output_tokens_details", "reasoning_tokens"),
    ):
        details = raw.get(container) or {}
        if not isinstance(details, dict):
            raise ContractError("Token details must be objects")
        alternate = _counter(details.get(nested))
        if values[key] is not None and alternate is not None and values[key] != alternate:
            raise ContractError("Conflicting token counter aliases")
        if values[key] is None:
            values[key] = alternate
    inp, cached, output, reasoning, total = (values[k] for k in
        ("input_tokens", "cached_input_tokens", "output_tokens",
         "reasoning_output_tokens", "total_tokens"))
    if inp is not None and cached is not None:
        if cached > inp:
            raise ContractError("Cached input exceeds input")
        uncached = inp - cached
        if values["uncached_input_tokens"] not in (None, uncached):
            raise ContractError("Conflicting uncached input")
        values["uncached_input_tokens"] = uncached
    if inp is not None and values["uncached_input_tokens"] is not None and values["uncached_input_tokens"] > inp:
        raise ContractError("Uncached input exceeds input")
    if reasoning is not None and output is not None and reasoning > output:
        raise ContractError("Reasoning subset exceeds output")
    if inp is not None and output is not None and total is not None and total != inp + output:
        raise ContractError("Total tokens differ from input plus output")
    return values


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _required(payload, name):
    value = _label(payload.get(name))
    if value is None:
        raise ContractError("Missing required receipt identifier: " + name)
    return value


def _receipt(payload):
    content_hash = payload.get("content_hash")
    region = payload.get("range")
    if not _hash(content_hash) or not isinstance(region, dict):
        raise ContractError("Read receipt needs SHA256 and an explicit range")
    start, end = region.get("start"), region.get("end")
    if (region.get("unit") not in {"bytes", "lines"} or type(start) is not int
            or type(end) is not int or start < 0 or end < start):
        raise ContractError("Read range must be nonnegative and half-open")
    truncated = payload.get("truncated")
    if truncated is not None and type(truncated) is not bool:
        raise ContractError("Truncated must be boolean or null")
    followups = payload.get("followup_of", [])
    if not isinstance(followups, list) or any(_label(v) is None for v in followups):
        raise ContractError("followup_of must be a list of receipt IDs")
    if payload.get("receipt_id") in followups:
        raise ContractError("A receipt cannot follow itself")
    identity = {"resource_id": _required(payload, "resource_id"),
                "content_hash": content_hash,
                "range": {"unit": region["unit"], "start": start, "end": end}}
    return {**identity, "receipt_id": _required(payload, "receipt_id"),
            "read_identity": hashlib.sha256(canonical(identity).encode()).hexdigest(),
            "purpose": _label(payload.get("purpose")), "truncated": truncated,
            "followup_of": sorted(set(followups))}


def _adjudicated(payload, session):
    return bool(session and _label(payload.get("adjudication_id"))
                and _label(payload.get("adjudicator_session_id"))
                and payload["adjudicator_session_id"] != session)


def _review(payload, kind, session):
    keys = ("finding_id", "artifact_hash", "criteria_hash", "adjudication_id",
            "adjudicator_session_id")
    row = {k: _label(payload.get(k)) for k in keys}
    row["finding_id"] = _required(payload, "finding_id")
    independent = _adjudicated(payload, session)
    if kind == "review_finding":
        row["detected"] = payload.get("detected") if type(payload.get("detected")) is bool else None
        status = payload.get("adjudicated_status")
        row["adjudicated_status"] = status if independent and status in {"valid", "invalid"} else "unknown"
        # Exact reviewed artifact and criteria must be identified before adjudication counts.
        if not row["artifact_hash"] or not row["criteria_hash"]:
            row["adjudicated_status"] = "unknown"
        return row
    row.update({k: _label(payload.get(k)) for k in
                ("transition_id", "transition", "previous_artifact_hash",
                 "previous_criteria_hash", "justification_kind", "evidence_ref")})
    row["transition_id"] = _required(payload, "transition_id")
    if row["transition"] not in {"reopen", "reversal"}:
        raise ContractError("Unknown review transition")
    pairs = [(row["artifact_hash"], row["previous_artifact_hash"]),
             (row["criteria_hash"], row["previous_criteria_hash"])]
    row["comparison"] = ("unknown" if any(not a or not b for a, b in pairs)
                         else "same_artifact_and_criteria" if all(a == b for a, b in pairs)
                         else "changed_artifact_or_criteria")
    classification = payload.get("classification")
    if not independent or classification not in {"justified", "unjustified"}:
        classification = "unknown"
    if classification == "justified" and (row["justification_kind"] not in
            {"regression", "new_evidence", "correction"} or not row["evidence_ref"]):
        classification = "unknown"
    if row["comparison"] == "unknown":
        classification = "unknown"
    row["classification"] = classification
    return row


def _merge(existing, incoming):
    """Deduplicate observations, enriching missing context but rejecting contradictions."""
    for key, value in incoming.items():
        if key in {"locators", "sequence"}:
            continue
        old = existing.get(key)
        if old is not None and value is not None and old != value:
            raise ContractError("Conflicting duplicate observation field: " + key)
        if old is None:
            existing[key] = value
    existing["locators"].extend(incoming["locators"])


def _tokens(rows):
    result = {}
    for key in FIELDS:
        known = [r["usage"][key] for r in rows if r["usage"][key] is not None]
        result[key] = {"observed_sum": sum(known), "known_responses": len(known),
                       "unknown_responses": len(rows) - len(known),
                       "complete_sum": sum(known) if rows and len(known) == len(rows) else None}
    return result


def _timeline(rows):
    """Use native stream order, or unambiguous timestamps across separate streams."""
    times = [r["timestamp_seconds"] for r in rows if r["timestamp_seconds"] is not None]
    common_sources = None
    for row in rows:
        sources = {loc["source"] for loc in row["locators"]}
        common_sources = sources if common_sources is None else common_sources & sources
    basis = None
    if common_sources:
        source = sorted(common_sources)[0]
        ordered = sorted(rows, key=lambda r: min(loc["line"] for loc in r["locators"] if loc["source"] == source))
        basis = "observed_stream_order"
    elif rows and len(times) == len(rows) and len(set(times)) == len(times):
        ordered = sorted(rows, key=lambda r: r["timestamp_seconds"])
        basis = "observed_timestamp_order"
    else:
        ordered = rows
    complete = (bool(rows) and len(times) == len(rows) and basis is not None
                and all(ordered[i]["timestamp_seconds"] >= ordered[i - 1]["timestamp_seconds"]
                        for i in range(1, len(ordered))))
    first = ordered[0]["usage"]["input_tokens"] if basis else None
    last = ordered[-1]["usage"]["input_tokens"] if basis else None
    trajectory = []
    for index, row in enumerate(ordered):
        prev = ordered[index - 1] if index and basis else None
        current_input = row["usage"]["input_tokens"]
        old_input = prev["usage"]["input_tokens"] if prev else None
        now = row["timestamp_seconds"]
        before = prev["timestamp_seconds"] if prev else None
        trajectory.append({"response_id": row["response_id"], "scope": row["scope"],
                           "timestamp_seconds": now, "input_tokens": current_input,
                           "input_change": current_input - old_input if current_input is not None and old_input is not None else None,
                           "elapsed_since_previous_seconds": now - before if now is not None and before is not None and now >= before else None})
    return {"order_basis": basis, "timing_complete": complete, "first_input_proxy": first,
            "first_input_interpretation": "Observed first response input; not a fixed prompt floor",
            "input_growth": last - first if first is not None and last is not None else None,
            "observed_span_seconds": max(times) - min(times) if len(times) >= 2 else None,
            "elapsed_seconds": ordered[-1]["timestamp_seconds"] - ordered[0]["timestamp_seconds"] if complete and len(times) >= 2 else None,
            "trajectory": trajectory}


def review_stability(events):
    """Precision/recall require a complete, independently adjudicated finding universe."""
    findings = [e for e in events if e["kind"] == "review_finding"]
    transitions = [e for e in events if e["kind"] == "review_transition"]
    confusion = Counter({k: 0 for k in ("tp", "fp", "fn", "tn", "unknown")})
    for row in findings:
        status, detected = row["adjudicated_status"], row["detected"]
        if status == "unknown" or detected is None:
            confusion["unknown"] += 1
        else:
            confusion[{("valid", True): "tp", ("invalid", True): "fp",
                       ("valid", False): "fn", ("invalid", False): "tn"}[status, detected]] += 1
    scopes = [e["universe_complete"] for e in events if e["kind"] == "review_scope"]
    complete = bool(scopes) and all(v is True for v in scopes) and not confusion["unknown"]
    def ratio(a, b):
        return a / b if b else None
    precision = ratio(confusion["tp"], confusion["tp"] + confusion["fp"])
    recall = ratio(confusion["tp"], confusion["tp"] + confusion["fn"])
    counts = {comparison: {kind: dict.fromkeys(("justified", "unjustified", "unknown"), 0)
                          for kind in ("reopen", "reversal")}
              for comparison in ("same_artifact_and_criteria", "changed_artifact_or_criteria", "unknown")}
    for row in transitions:
        counts[row["comparison"]][row["transition"]][row["classification"]] += 1
    same = [e for e in transitions if e["comparison"] == "same_artifact_and_criteria"]
    unknown = sum(e["classification"] == "unknown" for e in transitions)
    unjustified = sum(e["classification"] == "unjustified" for e in same)
    return {"confusion": dict(confusion), "universe_complete": complete,
            "precision": precision if complete else None, "recall": recall if complete else None,
            "adjudicated_subset_precision": precision, "adjudicated_subset_recall": recall,
            "transition_counts": counts,
            "same_artifact_unjustified_rate": ratio(unjustified, len(same)) if same and not unknown else None,
            "stability_status": "unstable" if unjustified else "unknown" if unknown or not same else "stable_observed",
            "quality_status": "unknown" if not complete or precision is None or recall is None else "adjudicated",
            "findings": findings, "transitions": transitions}


def _startup(events, responses):
    spawns = [e for e in events if e["kind"] == "session_spawn"]
    actions = [e for e in events if e["kind"] == "first_task_action"]
    result = {"spawn_observations": len(spawns), "first_task_action_observations": len(actions),
              "latency_seconds": None, "usage_response_count": None, "tool_read_count": None,
              "unknown_reason": "Missing or ambiguous startup boundary"}
    if len(spawns) != 1 or len(actions) != 1:
        return result
    start, end = spawns[0]["timestamp_seconds"], actions[0]["timestamp_seconds"]
    if start is None or end is None or end < start:
        result["unknown_reason"] = "Missing, invalid, or reversed timestamps"
        return result
    result.update(latency_seconds=end - start, unknown_reason=None)
    for key, rows in (("usage_response_count", responses),
                      ("tool_read_count", [e for e in events if e["kind"] == "tool_read_receipt"])):
        result[key] = sum(start <= r["timestamp_seconds"] < end for r in rows
                          if r["timestamp_seconds"] is not None)
        result[key + "_unknown_timing"] = sum(r["timestamp_seconds"] is None for r in rows)
    return result


def _reads(events, all_receipts):
    reads = [e for e in events if e["kind"] == "tool_read_receipt"]
    links = []
    for row in reads:
        for parent_id in row["followup_of"]:
            parent = all_receipts.get(parent_id)
            a, b = (parent["timestamp_seconds"] if parent else None), row["timestamp_seconds"]
            links.append({"receipt_id": row["receipt_id"], "followup_of": parent_id,
                          "parent_observed": parent is not None,
                          "parent_truncated": parent["truncated"] if parent else None,
                          "same_read_identity": parent["read_identity"] == row["read_identity"] if parent else None,
                          "elapsed_seconds": b - a if a is not None and b is not None and b >= a else None})
    identities = Counter(e["read_identity"] for e in reads)
    followed = {ref for receipt in all_receipts.values() for ref in receipt["followup_of"]}
    return {"observed_count": len(reads), "unique_read_identities": len(identities),
            "repeated_identity_count": sum(n - 1 for n in identities.values()),
            "truncated_count": sum(e["truncated"] is True for e in reads),
            "unknown_truncation_count": sum(e["truncated"] is None for e in reads),
            "truncated_with_explicit_followup_count": sum(e["truncated"] is True and e["receipt_id"] in followed for e in reads),
            "truncated_without_observed_followup_count": sum(e["truncated"] is True and e["receipt_id"] not in followed for e in reads),
            "followup_links": links, "interpretation": "Explicit followup correlation; no causality inferred"}


def analyze_sources(sources):
    """Analyze (source_label, iterable_of_records) pairs; labels are provenance only."""
    responses, events, dedup_events = {}, [], {}
    duplicates = 0
    sequence = 0
    for source, records in sources:
        context = dict(session_id=None, role=None, round_id=None, session_scope=None)
        for line, record in enumerate(records, 1):
            sequence += 1
            if not isinstance(record, dict):
                raise ContractError("Record must be an object")
            payload = record.get("payload", {})
            if not isinstance(payload, dict):
                continue
            kind = record.get("type")
            if kind == "session_meta":
                parent = payload.get("parent_session_id")
                origin = payload.get("source")
                if isinstance(origin, dict):
                    subagent = origin.get("subagent")
                    spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
                    if isinstance(spawn, dict):
                        parent = parent or spawn.get("parent_thread_id")
                context = dict(session_id=_label(payload.get("id")),
                               role=_label(payload.get("role") or payload.get("agent_role")),
                               round_id=None,
                               session_scope="child" if parent else payload.get("scope") if payload.get("scope") in {"main", "child"} else None)
                continue
            if kind == "turn_context":
                context["round_id"] = _label(payload.get("round_id") or payload.get("turn_id"))
                continue
            if kind == "event_msg":
                kind = payload.get("type")
            if kind != "token_usage_record" and kind not in EVENTS:
                continue  # Never inspect message content, tool output, or reasoning bodies.
            session = _label(payload.get("session_id")) or context["session_id"]
            scope = payload.get("scope", payload.get("usage_scope", payload.get("source")))
            scope = scope if isinstance(scope, str) and scope in {"main", "child", "compaction"} else None
            base = {"session_id": session, "role": _label(payload.get("role")) or context["role"],
                    "round_id": _label(payload.get("round_id") or payload.get("turn_id")) or context["round_id"],
                    "timestamp_seconds": _time(record.get("timestamp", payload.get("timestamp"))),
                    "locators": [{"source": str(source), "line": line}], "sequence": sequence}
            if kind == "token_usage_record":
                rid = _required(payload, "response_id")
                row = {**base, "response_id": rid, "scope": scope or context["session_scope"],
                       "usage": _usage(payload.get("usage"))}
                if rid in responses:
                    _merge(responses[rid], row)
                    duplicates += 1
                else:
                    responses[rid] = row
                continue
            row = {**base, "kind": kind}
            event_key = None
            if kind == "tool_read_receipt":
                row.update(_receipt(payload))
                event_key = (kind, row["receipt_id"])
            elif kind in {"review_finding", "review_transition"}:
                row.update(_review(payload, kind, session))
                event_key = ((kind, row["transition_id"]) if kind == "review_transition" else
                             (kind, session, row["role"], row["round_id"], row["finding_id"], row["artifact_hash"], row["criteria_hash"]))
            elif kind == "review_scope":
                row["universe_complete"] = payload.get("universe_complete") is True
                event_key = (kind, session, row["role"], row["round_id"])
            elif _label(payload.get("event_id")):
                event_key = (kind, payload["event_id"])
            if event_key in dedup_events:
                _merge(dedup_events[event_key], row)
            else:
                events.append(row)
                if event_key is not None:
                    dedup_events[event_key] = row
    rows = list(responses.values())
    receipts = {e["receipt_id"]: e for e in events if e["kind"] == "tool_read_receipt"}
    groups = defaultdict(lambda: {"responses": [], "events": []})
    sessions = defaultdict(lambda: {"responses": [], "events": []})
    for category, items in (("responses", rows), ("events", events)):
        for row in items:
            # Unknown sessions from different files must never form a fictional shared session.
            session_key = row["session_id"] or ("unknown_source", row["locators"][0]["source"])
            key = (session_key, row["role"], row["round_id"])
            groups[key][category].append(row)
            sessions[session_key][category].append(row)
    summaries = []
    for (_, role, round_id), group in groups.items():
        observed = group["responses"] + group["events"]
        summaries.append({"session_id": observed[0]["session_id"], "role": role, "round_id": round_id,
                          "sources": sorted({loc["source"] for row in observed for loc in row["locators"]}),
                          "tokens": _tokens(group["responses"]),
                          "input_and_time": _timeline(group["responses"]),
                          "input_and_time_by_scope": {
                              scope: _timeline([r for r in group["responses"] if (r["scope"] or "unknown") == scope])
                              for scope in sorted({r["scope"] or "unknown" for r in group["responses"]})},
                          "reads": _reads(group["events"], receipts),
                          "review": review_stability(group["events"])})
    session_summaries = []
    for group in sessions.values():
        observed = group["responses"] + group["events"]
        session_summaries.append({"session_id": observed[0]["session_id"],
                                  "sources": sorted({loc["source"] for row in observed for loc in row["locators"]}),
                                  "tokens": _tokens(group["responses"]),
                                  "input_and_time": _timeline(group["responses"]),
                                  "startup": _startup(group["events"], group["responses"]) if observed[0]["session_id"] else
                                  {"latency_seconds": None, "usage_response_count": None, "tool_read_count": None,
                                   "unknown_reason": "Session identity unobserved"}})
    return {"schema_version": 1, "observational_only": True,
            "response_count": len(rows), "duplicate_response_count": duplicates,
            "tokens": _tokens(rows),
            "scope_counts": dict(Counter(r["scope"] or "unknown" for r in rows)),
            "tokens_by_scope": {scope: _tokens([r for r in rows if (r["scope"] or "unknown") == scope])
                                for scope in ("main", "child", "compaction", "unknown")},
            "unknowns": {key: sum(r[key] is None for r in rows)
                         for key in ("session_id", "role", "round_id", "scope", "timestamp_seconds")},
            "roles": [{"role": role, "response_count": sum(r["role"] == role for r in rows),
                       "tokens": _tokens([r for r in rows if r["role"] == role])}
                      for role in sorted({r["role"] for r in rows}, key=lambda v: (v is None, v or ""))],
            "sessions": session_summaries, "groups": summaries,
            "responses": rows, "events": events,
            "limitations": ["Partial observed counters; no billing or quota estimates",
                            "Reasoning tokens are a subset of output, not additive",
                            "No hidden reasoning, message bodies, or tool result content exported",
                            "Missing events do not establish absence of work",
                            "First input is a proxy, not a fixed floor",
                            "Followup links are correlations, not causal attribution"]}


def analyze_records(records):
    """Convenience entry point for one synthetic or native stream."""
    return analyze_sources([("records", records)])


def _records(path):
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                yield {}  # Preserve physical line locators.
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                raise ContractError("Invalid JSONL record (content omitted)") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rollout", type=Path, action="append", default=[])
    parser.add_argument("--events", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    paths = args.rollout + args.events
    if not paths:
        parser.error("At least one --rollout or --events file is required")
    try:
        if args.output.resolve() in {p.resolve() for p in paths}:
            raise ContractError("Output must not overwrite a source")
        report = analyze_sources([(str(p), _records(p)) for p in paths])
        write_json(args.output, report)
    except (ContractError, OSError) as exc:
        # No source lines, model text or arbitrarily long identifiers reach the console.
        print("Telemetry failed: " + str(exc)[:180], file=sys.stderr)
        return 2
    summary = {"responses": report["response_count"], "duplicates": report["duplicate_response_count"],
               "sessions": len(report["sessions"]), "groups": len(report["groups"]),
               "observed_input_tokens": report["tokens"]["input_tokens"]["observed_sum"],
               "unknown_input_responses": report["tokens"]["input_tokens"]["unknown_responses"],
               "artifact_written": True}
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
