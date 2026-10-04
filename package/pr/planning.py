"""Check agent-authored selections and plans; never manufacture a workflow."""
from .util import ContractError, hash_data, read_json, timestamp
from .schema import validate


def graph(nodes):
    ids = [n["id"] for n in nodes]
    if len(ids) != len(set(ids)):
        raise ContractError("Duplicate task IDs")
    pending = {n["id"]: set(n["depends_on"]) for n in nodes}
    for key, deps in pending.items():
        if key in deps or deps - set(ids):
            raise ContractError("Unknown or self dependency")
    layers = []
    while pending:
        layer = sorted(k for k, v in pending.items() if not v)
        if not layer:
            raise ContractError("Cyclic plan")
        layers.append(layer)
        pending = {k: v - set(layer) for k, v in pending.items() if k not in layer}
    return layers


def impact(nodes, fields=(), seeds=()):
    affected = set(seeds) | {n["id"] for n in nodes if set(n["consumes"]) & set(fields)}
    while True:
        expanded = affected | {n["id"] for n in nodes if set(n["depends_on"]) & affected}
        if expanded == affected:
            return sorted(affected)
        affected = expanded


def meta_check(registry, request, meta):
    validate(registry.root, "meta", meta)
    if meta["request_id"] != request["id"]:
        raise ContractError("Meta selection belongs to another request")
    if meta['mode']=='report' and request['mode']!='report':
        raise ContractError('A development/experiment mandate cannot be relabeled as a completed report')
    registry.evaluation(meta["evaluation"])
    for ref in meta["selected"]:
        data, _ = registry.resolve(ref, "orchestration")
        if meta["mode"] == "report" and data.get("execution_support") != "complete":
            raise ContractError(f"Planning-only capability cannot promise execution: {ref['id']}")
    if meta["action"] == "reuse" and len(meta["selected"]) != 1:
        raise ContractError("Reuse selects exactly one orchestration")
    if meta["action"] == "compose":
        c = meta.get("composition")
        if len(meta["selected"]) < 2 or not c:
            raise ContractError("Composition needs at least two definitions and a shared contract")
        validate(registry.root, "composition", c)
        selected = {r["id"] for r in meta["selected"]}
        if set(c["responsibilities"]) != selected:
            raise ContractError("Composition must assign every orchestration's responsibility")
        if c["information_cutoff"] != request["information_cutoff"]:
            raise ContractError("Composition cutoff conflicts with request; amend mandate first")
        if c["conflicts"]:
            raise ContractError("Unresolved composition contract conflicts")
        for h in c["handoffs"]:
            if h["from"] not in selected or h["to"] not in selected or h["from"] == h["to"]:
                raise ContractError("Composition handoff endpoint invalid")
            for field in ("scope", "perimeter", "currency", "information_cutoff"):
                if h.get(field, c[field]) != c[field]:
                    raise ContractError(f"Unresolved handoff {field} conflict")
    if meta["action"] in {"clarify", "capability-gap", "candidate"} and not meta["gaps"]:
        raise ContractError("Incomplete selection must state the missing condition")
    return meta


def plan_check(registry, meta, plan):
    validate(registry.root, "plan", plan)
    if plan["meta_hash"] != hash_data(meta):
        raise ContractError("Plan uses a superseded meta selection")
    graph(plan["nodes"])
    capabilities = set()
    review_roles = set()
    for n in plan["nodes"]:
        persona, _ = registry.resolve(n["expert"], "persona")
        runtime, _ = registry.resolve(n["runtime"], "runtime")
        skill_caps = set()
        for ref in n["skills"]:
            skill, skill_path = registry.resolve(ref, "skill")
            skill_caps.update(skill["capabilities"])
            contract_path = skill_path / "contract.json"
            if contract_path.exists():
                contract = read_json(contract_path)
                checks = contract.get('acceptance',contract.get('validations',[]))
                needed = {c['id'] if isinstance(c,dict) else c for c in checks}
                if needed-set(n['required_checks']):
                    raise ContractError(f"Task weakens skill acceptance contract: {n['id']} / {ref['id']}")
                if set(contract.get('consumes',[]))-set(n['consumes']):
                    raise ContractError(f"Task omits skill dependency fields: {n['id']} / {ref['id']}")
                if set(contract.get('outputs',[]))-set(n['outputs']):
                    raise ContractError(f"Task omits skill outputs: {n['id']} / {ref['id']}")
        if set(n["capabilities"]) - skill_caps:
            raise ContractError(f"Task claims capability absent from skills: {n['id']}")
        if n["execution"] == "agent" and not n["skills"]:
            raise ContractError("Agent task must bind its skills")
        if n.get("review_role"):
            review_roles.add(n["review_role"])
        capabilities.update(n["capabilities"])
        for b in n["basis"]:
            _, p = registry.resolve(b["component"])
            # Clause IDs must exist in the actual bound policy, not merely in the plan.
            policy = "\n".join(f.read_text() for f in p.rglob("*.md"))
            if b["clause"] not in policy or not b["facts"] or not b["reason"]:
                raise ContractError(f"Unsubstantiated policy basis: {n['id']} {b['clause']}")
    findings = []
    for ref in meta["selected"]:
        _, folder = registry.resolve(ref)
        for rulefile in [folder / "plan-rules.json", folder / "rules.json"]:
            if not rulefile.exists():
                continue
            for r in read_json(rulefile)["rules"]:
                when = r.get("when")
                fact = plan["facts"].get(when["fact"]) if when else True
                if when and fact is None:
                    assessments = plan.get("applicability_assessments", {})
                    assessment = assessments.get(r["id"])
                    if not assessment or not assessment.get("reason") or not assessment.get("evidence"):
                        findings.append({"rule": r["id"], "issue": "unknown applicability requires evidence or assessment task"})
                        continue
                    if assessment.get("status") == "pending":
                        if not any(n["id"] == assessment.get("task_id") for n in plan["nodes"]):
                            raise ContractError("Assessment task missing")
                        findings.append({"rule": r["id"], "issue": "pending applicability", "pending": True})
                        continue
                    fact = assessment.get("applies")
                    if not isinstance(fact, bool):
                        raise ContractError("Assessment must state applies true/false or pending")
                    applies = fact
                else:
                    applies = not when or fact == when["equals"]
                if applies:
                    missing = set(r.get("require_capabilities", [])) - capabilities
                    missing_reviews = set(r.get("require_review_roles", [])) - review_roles
                    missing_outputs = set(r.get("require_artifacts", [])) - {o for n in plan["nodes"] for o in n["outputs"]}
                    if missing or missing_reviews or missing_outputs:
                        findings.append({"rule": r["id"], "missing": sorted(missing | missing_reviews | missing_outputs)})
    if any(not f.get("pending") for f in findings):
        raise ContractError(f"Plan violates machine rules: {findings}")
    profile=registry.evaluation(meta['evaluation'])
    outputs={o for n in plan['nodes'] for o in n['outputs']}
    checks={c for n in plan['nodes'] for c in n['required_checks']}
    delivery_gaps=[]
    for key,present in [('required_artifacts',outputs),('required_checks',checks),('required_review_roles',review_roles)]:
        delivery_gaps.extend(key+': '+v for v in sorted(set(profile.get(key,[]))-present))
    for role,types in profile.get('coverage',{}).items():
        produced={o for n in plan['nodes'] if not n.get('review_role') for o in n['outputs']}
        delivery_gaps.extend(f'{role} review coverage has no producer: {t}' for t in sorted(set(types)-produced))
        for n in plan['nodes']:
            if n.get('review_role') or not set(n['outputs']) & set(types):continue
            if not any(r.get('review_role')==role and n['id'] in r['depends_on'] for r in plan['nodes']):
                delivery_gaps.append(f'{role} review has no direct target dependency: {n["id"]}')
    if meta['mode']=='report' and delivery_gaps:
        raise ContractError('Report plan omits protected delivery/review obligations: '+str(delivery_gaps))
    return {"layers": graph(plan["nodes"]), "pending_rules": findings,'delivery_gaps':delivery_gaps}
