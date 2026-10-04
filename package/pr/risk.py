"""Deterministic risk contracts; policy approval and evidence review remain external.

Plan hashes use pr.util.hash_data. The engine verifies the profile FILE digest
before freezing it; this function cannot reconstruct that digest from an object.
Snapshots are the current engine ID->record mapping. Generic detects text never
establishes semantic assurance, and controls cannot waive mandatory floors.
The caller establishes approval/status and test-evidence assertions independently.
"""
from pathlib import Path
import json

from .schema import validate
from .util import ContractError, canonical, hash_data, read_json


ROOT = Path(__file__).resolve().parents[1]
ORDER = ("code", "source", "recalculate", "judgment", "document")
FLOORS = {"low": {"code"}, "medium": {"code", "source"},
          "high": {"code", "source", "recalculate", "judgment"}}


def _shape(name, value):
    from jsonschema import Draft202012Validator
    schema = read_json(ROOT / "schemas/risk.schema.json")
    schema["$ref"] = f"#/$defs/{name}"
    # The root describes the bundle; only the referenced input applies here.
    for key in ("type", "properties", "required", "additionalProperties"):
        schema.pop(key, None)
    errors = sorted(Draft202012Validator(schema).iter_errors(value),
                    key=lambda e: str(list(e.path)))
    if errors:
        raise ContractError(f"risk.{name}: {errors[0].message}")


def _index(items, field, label):
    result = {}
    for item in items:
        key = item[field]
        if key in result:
            raise ContractError(f"Duplicate {label}: {key}")
        result[key] = item
    return result


def _refs(refs, snapshots, label):
    result = _index(refs, "id", f"{label} input ID")
    for identity, ref in result.items():
        current = snapshots.get(identity)
        if current is None or ref["sha256"] != current["sha256"]:
            raise ContractError(f"Missing or changed {label} input: {identity}")
        if current["eligible"] is not True:
            raise ContractError(f"Ineligible {label} input: {identity}")
    return {key: ref["sha256"] for key, ref in result.items()}


def _basis(basis, clauses, sources):
    seen = set()
    for ref in basis:
        pair = (ref["clause"], ref["source_id"])
        if pair in seen:
            raise ContractError("Duplicate policy basis")
        seen.add(pair)
        clause = clauses.get(ref["clause"])
        if (clause is None or ref["source_id"] not in sources
                or ref["source_id"] not in clause["source_ids"]):
            raise ContractError("Policy basis does not reference a bound profile source/clause")


def _acyclic(claims):
    pending = {key: set(c["dependencies"]) for key, c in claims.items()}
    for key, deps in pending.items():
        if key in deps or deps - claims.keys():
            raise ContractError("Unknown or self claim dependency")
    while pending:
        ready = {key for key, deps in pending.items() if not deps}
        if not ready:
            raise ContractError("Cyclic claim dependencies")
        pending = {key: deps - ready for key, deps in pending.items() if key not in ready}


def check_bundle(bundle, profile, plan, snapshots):
    """Return blocking issues, required procedures per claim, and reduction intent.

    Malformed structures, forged bindings and stale/ineligible inputs raise
    ContractError. Well-formed but insufficient evidence returns blocking issues.
    Effective controls must bind node.component_sha256 (or a node component ref),
    and node.environment_sha256 or plan.environment_sha256. No filesystem reads
    of evidence, numerical calibration, reviewer approval or engine transitions
    are performed by this function. Required procedures always include selected
    procedures AND mandatory floors; omitted floors remain blocking even with
    effective controls. Profile file digest verification belongs to register_risk.
    """
    try:
        for value in (bundle, profile, plan, snapshots):
            if json.loads(canonical(value)) != value:
                raise ContractError("Risk inputs must contain only JSON types and string object keys")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ContractError("Risk inputs must be finite JSON values") from exc
    validate(ROOT, "risk", bundle)
    for name, value in (("profile", profile), ("plan", plan), ("snapshots", snapshots)):
        _shape(name, value)
    if bundle["plan_sha256"] != hash_data(plan):
        raise ContractError("Risk bundle plan binding changed")
    if (bundle["revision"] == 1) != (bundle["previous"] is None):
        raise ContractError("Risk revision/previous binding invalid")
    for identity, snapshot in snapshots.items():
        if snapshot["id"] != identity:
            raise ContractError("Snapshot mapping ID mismatch")
    sources = _index(profile["sources"], "id", "profile source ID")
    clauses = _index(profile["clauses"], "id", "profile clause ID")
    _index(profile.get("fact_rules", []), "fact", "profile fact rule")
    for clause in clauses.values():
        if set(clause["source_ids"]) - sources.keys():
            raise ContractError("Profile clause references an unknown source")
    for level in FLOORS:
        declared = set(profile[f"{('all' if level == 'low' else level)}_minimum"])
        if FLOORS[level] - declared:
            raise ContractError(f"Profile weakens the {level} procedure floor")
    nodes = _index(plan["nodes"], "id", "plan node ID")
    claims = _index(bundle["claims"], "id", "claim ID")
    controls = _index(bundle["controls"], "id", "control ID")
    if claims.keys() & controls.keys():
        raise ContractError("Duplicate claim/control ID")
    assessments = _index(bundle["assessments"], "claim_id", "assessment claim ID")
    if assessments.keys() != claims.keys():
        raise ContractError("Every claim needs exactly one assessment")
    _acyclic(claims)
    claim_inputs = {}
    for identity, claim in claims.items():
        node = nodes.get(claim["node_id"])
        if node is None or node.get("review_role") or not node["outputs"]:
            raise ContractError("Claim must belong to an output-producing nonreview node")
        if node.get("producer_agent_id") is not None and claim["producer_agent_id"] != node["producer_agent_id"]:
            raise ContractError("Claim producer does not match node producer")
        claim_inputs[identity] = _refs(claim["input_refs"], snapshots, "claim")
        if set(node["inputs"]) - claim_inputs[identity].keys():
            raise ContractError("Claim omits a planned node input")
    covered = {c["node_id"] for c in claims.values()}
    if any(n["outputs"] and not n.get("review_role") and key not in covered for key, n in nodes.items()):
        raise ContractError("Output-producing plan node has no claim")
    issues = []

    def issue(code, claim_id=None, **detail):
        issues.append(dict(code=code, blocking=True, claim_id=claim_id, **detail))

    if profile["status"] != "approved":
        issue("profile_unapproved")
    materiality = bundle["materiality"]
    materiality_approved = materiality is not None and materiality["status"] == "approved"
    if materiality is not None:
        _basis(materiality["basis"], clauses, sources)
        if not materiality_approved:
            issue("materiality_unapproved")
        if materiality.get("quantitative_reduction", False):
            issue("quantitative_reduction_uncalibrated" if profile["quantitative_rules"] is None
                  else "quantitative_reduction_requires_external_calibration")
    bound_controls = {key: [] for key in claims}
    for control in controls.values():
        key = control["claim_id"]
        if key not in claims:
            raise ContractError("Control references unknown claim")
        if _refs(control["input_refs"], snapshots, "control") != claim_inputs[key]:
            raise ContractError("Control inputs do not exactly match claim inputs")
        node = nodes[claims[key]["node_id"]]
        component_hashes = {node["component_sha256"]} if "component_sha256" in node else set()
        for ref in node.get("skills", []) + [node.get("runtime", {}), node.get("expert", {})]:
            if isinstance(ref, dict) and "sha256" in ref:
                component_hashes.add(ref["sha256"])
        environment = node.get("environment_sha256", plan.get("environment_sha256"))
        if component_hashes and control["component_sha256"] not in component_hashes:
            raise ContractError("Control component binding changed")
        if environment is not None and control["environment_sha256"] != environment:
            raise ContractError("Control environment binding changed")
        if control["status"] == "effective":
            if not component_hashes or environment is None:
                issue("control_binding_unverifiable", key, control_id=control["id"])
            else:
                bound_controls[key].append(control)
    required = {}
    reduction_requested = bool(materiality and materiality.get("quantitative_reduction", False))
    for key in sorted(claims):
        assessment = assessments[key]
        _basis(assessment["basis"], clauses, sources)
        node = nodes[claims[key]["node_id"]]
        level = assessment["inherent"]
        unknown_facts = []
        fact_high = False
        for rule in profile.get("fact_rules", []):
            value = plan.get("facts", {}).get(rule["fact"])
            if value is True:
                fact_high = True
            elif value is not False:
                unknown_facts.append(rule["fact"])
        provisional = (node.get("provisional", False) or
                       any(e.lower().startswith("provisional") for e in assessment["exposures"]))
        if fact_high or unknown_facts or provisional or set(assessment["exposures"]) & set(profile["high_exposures"]):
            level = "high"
        elif level == "low" and (assessment["control"] in {"unknown", "failed"}
                                 or not bound_controls[key]):
            level = "medium"
        minimum = set(profile["all_minimum"])
        if level in {"medium", "high"}:
            minimum.update(profile["medium_minimum"])
        if level == "high":
            minimum.update(profile["high_minimum"])
        # Evidence uncertainty is not converted into effective control assurance.
        if assessment["control"] == "effective" and not bound_controls[key]:
            issue("effective_control_unsubstantiated", key)
        if any(c["status"] != "effective" for c in controls.values() if c["claim_id"] == key):
            if level == "low":
                minimum.update(profile["medium_minimum"])
            if assessment["control"] == "effective":
                issue("conflicting_control_status", key)
        planned = set(assessment["procedures"])
        if unknown_facts:
            issue("fact_applicability_unknown", key, facts=sorted(unknown_facts))
        missing = minimum - planned
        reduction_requested = reduction_requested or bool(missing)
        if missing:
            issue("procedure_reduction_blocked", key, missing=[p for p in ORDER if p in missing])
        effective_required = minimum | planned
        required[key] = [p for p in ORDER if p in effective_required]
    return dict(issues=issues, required_procedures=required, reduction_requested=reduction_requested)
