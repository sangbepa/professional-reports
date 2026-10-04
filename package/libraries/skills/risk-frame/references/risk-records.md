# Risk evidence records

These descriptive records are operation artifacts, not new engine schema enums or permission files. Bind them through supported plan `facts`/artifact references and component basis clauses, after checking the pinned schema.

- `artifact_manifest`: record IDs, relative paths, versions, measured hashes/access limits, consumed fields and acceptance/review references.
- `risk_register`: each object has `risk_id`, failure event/assertion, `object_refs`, `task_refs` (actual node ID/revision), causes, consequence/perimeter, inherent exposure, control IDs, residual exposure, evidence refs, uncertainty/confidence basis, assessor/producer lineage and change/invalidation status. Likelihood stays qualitative or unknown unless evidence justifies a calibrated measure; do not multiply ordinal labels into invented precision.
- `profile_record`/`profile_binding`: profile ID/version/hash, package release reference, task IDs/revisions, scope, criteria references, proposed/adopted settings, `shadow` or `adopted`, concrete adoption evidence and evidence limitations. Package release approval and implementation authorization do not adopt a task profile. Missing concrete adoption evidence means shadow even when a riskfile exists.
- `sourcepack`: supplied original standards/guidance with issuer, version, applicability, exact locators and measured snapshots; missing coverage is a gap for main coordination, never invented authority.
- `invalidation_map`: changed consumed fields/versions, affected risk objects/tasks/controls, invalidated artifacts and confidence/reviews, prior evidence retained, required rerun/retest/review and current restriction.

Sensitivity results bind baseline, scenario inputs and recomputed outputs; control results bind test population/selection and actual evidence; review plans bind coverage and independent lineage. Cost records bind task/attempt/risk IDs, forecast versus actual, rate provenance, currency/unit, setup versus company work, elapsed interval/cache/token evidence and unknowns. Keep these meanings distinct rather than treating sensitivity, a control pass, low cost or a risk label as report approval.
