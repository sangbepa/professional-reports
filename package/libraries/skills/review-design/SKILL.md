---
name: review-design
description: Design independent review coverage for task risks while preserving existing acceptance criteria.
---

# review-design

Read [the operation contract](contract.json) when dispatched; use the supplied mandate and actual task scope. Read [execution boundary](references/execution-contract.md) before binding evidence or returning results. Contract inputs may be mapped from equivalent supplied records; preserve their ledger meanings. This method provides no generic FDD or ESG execution implementation.

## Execute

1. Map each risk and material assertion to source, arithmetic, economics or design coverage using existing wire-schema review channels. Record required competence, actual producer lineage and independent reviewer scope.

2. Propose concrete review tasks with current node IDs/revisions, artifact hashes, criteria references, method bindings and failure routes. Use fresh independent reviewers per round and preserve resolution and reopening evidence.

3. Candidate review allocation remains shadow until concrete adoption. Never omit protected criteria, replace independent review with author checks or lower thresholds to satisfy cost. Return uncovered risks and conflicts for scoped resolution.

## Return

Return `review_plan`, `coverage_gaps`, `operation_record` and `failure_records` with actual input/output bindings. Distinguish observed facts, conditional calculations, assumptions, judgments and unresolved evidence. Restrict dependent conclusions when required work is unperformed. Do not record a planned control, review or runtime setting as observed execution. Keep original evidence and prior attempts; return changed inputs and affected descendants for revalidation.

## Stable planning clauses

### review-design-method

Apply the substantive method above to current bound inputs only. Capabilities: risk-review-design.

### review-design-acceptance

Apply the contract acceptance tests; retain actual checks and limitations separately. Completion covers only the performed operation.

### review-design-failure

Return failed prerequisites to the contract's named owners; restrict conclusions and invalidate affected descendants.
