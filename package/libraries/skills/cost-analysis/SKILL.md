---
name: cost-analysis
description: Compare evidenced setup and per-company task costs without reducing protected review requirements.
---

# cost-analysis

Read [the operation contract](contract.json) when dispatched; use the supplied mandate and actual task scope. Read [execution boundary](references/execution-contract.md) before binding evidence or returning results. Contract inputs may be mapped from equivalent supplied records; preserve their ledger meanings. This method provides no generic FDD or ESG execution implementation.

## Execute

1. Separate one-time package development, sourcepack collection and environment preparation from each company engagement and its retries, fresh evidence collection, calculation, review, rendering and delivery.

2. Bind estimates and actuals to task ID/revision, attempt and risk/control/review coverage. Record currency, unit, rate source/date, observed tokens/cache split, elapsed intervals and uncertainty; unknown cost or usage is not zero. Prevent double counting shared setup and parallel wall-clock intervals.

3. Compare only options preserving mandatory checks and approved settings. Record forecast versus actual and cost tradeoffs; do not invent a cheapest feasible option. Report budget is exactly 600 seconds: 585 work plus 15 preservation/delivery; preparation is separate and engagement work cannot be relabeled setup.

## Return

Return `task_cost_ledger`, `cost_options`, `budget_feasibility`, `operation_record` and `failure_records` with actual input/output bindings. Distinguish observed facts, conditional calculations, assumptions, judgments and unresolved evidence. Restrict dependent conclusions when required work is unperformed. Do not record a planned control, review or runtime setting as observed execution. Keep original evidence and prior attempts; return changed inputs and affected descendants for revalidation.

## Stable planning clauses

### cost-analysis-method

Apply the substantive method above to current bound inputs only. Capabilities: task-cost-analysis.

### cost-analysis-acceptance

Apply the contract acceptance tests; retain actual checks and limitations separately. Completion covers only the performed operation.

### cost-analysis-failure

Return failed prerequisites to the contract's named owners; restrict conclusions and invalidate affected descendants.
