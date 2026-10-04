---
name: risk-frame
description: Frame task-specific failure risks from supplied evidence and a shadow or explicitly adopted profile.
---

# risk-frame

Read [the operation contract](contract.json) when dispatched; use the supplied mandate and actual task scope. Read [execution boundary](references/execution-contract.md) before binding evidence or returning results. Contract inputs may be mapped from equivalent supplied records; preserve their ledger meanings. This method provides no generic FDD or ESG execution implementation.

## Execute

1. Identify failure events for the actual decision, task and assertion; record causes, affected objects, consequences, current controls and evidence gaps. Separate inherent exposure from residual exposure and qualitative judgment from measured likelihood.

2. Bind every risk to a current plan node ID/revision and source, calculation, claim or artifact ID/hash. Map impact and control coverage to the proposed profile without converting unsupported estimates to probabilities.

3. Check package adoption and task settings separately. A profile stays shadow unless a concrete version/hash and scoped user adoption record exist. Missing sourcepack standards remain missing; do not invent normative thresholds.

## Return

Return `risk_register`, `profile_binding`, `invalidation_map`, `operation_record` and `failure_records` with actual input/output bindings. Distinguish observed facts, conditional calculations, assumptions, judgments and unresolved evidence. Restrict dependent conclusions when required work is unperformed. Do not record a planned control, review or runtime setting as observed execution. Keep original evidence and prior attempts; return changed inputs and affected descendants for revalidation.

## Stable planning clauses

### risk-frame-method

Apply the substantive method above to current bound inputs only. Capabilities: risk-framing.

### risk-frame-acceptance

Apply the contract acceptance tests; retain actual checks and limitations separately. Completion covers only the performed operation.

### risk-frame-failure

Return failed prerequisites to the contract's named owners; restrict conclusions and invalidate affected descendants.

Read [risk record fields](references/risk-records.md) when constructing or changing a register or profile binding.
