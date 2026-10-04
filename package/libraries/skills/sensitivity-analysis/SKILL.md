---
name: sensitivity-analysis
description: Measure how bounded assumption changes affect current model outputs and decision boundaries.
---

# sensitivity-analysis

Read [the operation contract](contract.json) when dispatched; use the supplied mandate and actual task scope. Read [execution boundary](references/execution-contract.md) before binding evidence or returning results. Contract inputs may be mapped from equivalent supplied records; preserve their ledger meanings. This method provides no generic FDD or ESG execution implementation.

## Execute

1. Confirm the baseline reproduces the bound model. Record units, horizon, perimeter, formula versions, baseline assumptions and feasible joint scenario constraints before changing selected variables.

2. Recompute supplied scenarios, including dependencies and nonlinear discontinuities; show absolute and relative changes with denominators and identify decision boundary crossings. Flag noncomputable cases rather than filling fabricated results.

3. Sensitivity is a conditional output response, not event likelihood, control effectiveness or a calibrated risk score. Link results to risk IDs as evidence only; do not reduce review because an output appears stable.

## Return

Return `sensitivity_results`, `decision_boundaries`, `operation_record` and `failure_records` with actual input/output bindings. Distinguish observed facts, conditional calculations, assumptions, judgments and unresolved evidence. Restrict dependent conclusions when required work is unperformed. Do not record a planned control, review or runtime setting as observed execution. Keep original evidence and prior attempts; return changed inputs and affected descendants for revalidation.

## Stable planning clauses

### sensitivity-analysis-method

Apply the substantive method above to current bound inputs only. Capabilities: sensitivity-analysis.

### sensitivity-analysis-acceptance

Apply the contract acceptance tests; retain actual checks and limitations separately. Completion covers only the performed operation.

### sensitivity-analysis-failure

Return failed prerequisites to the contract's named owners; restrict conclusions and invalidate affected descendants.
