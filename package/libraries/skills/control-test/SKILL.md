---
name: control-test
description: Test specified controls against current risk objects and retain execution and exception evidence.
---

# control-test

Read [the operation contract](contract.json) when dispatched; use the supplied mandate and actual task scope. Read [execution boundary](references/execution-contract.md) before binding evidence or returning results. Contract inputs may be mapped from equivalent supplied records; preserve their ledger meanings. This method provides no generic FDD or ESG execution implementation.

## Execute

1. Bind each control to risk IDs and assertions, owner, frequency, input population and expected evidence. Separate design adequacy from actual operating effectiveness.

2. Retain test selection rationale, coverage, exclusions and executed evidence. Test failure paths when applicable. Report observed exceptions with numerator and denominator; samples alone do not establish population error or a probability guarantee.

3. Compare actual evidence with unchanged criteria and link uncovered exposure to plan nodes. Unperformed checks remain unverified. Route remediation and fresh independent retest; a producer self-check cannot become independent assurance.

## Return

Return `control_test_results`, `control_exceptions`, `operation_record` and `failure_records` with actual input/output bindings. Distinguish observed facts, conditional calculations, assumptions, judgments and unresolved evidence. Restrict dependent conclusions when required work is unperformed. Do not record a planned control, review or runtime setting as observed execution. Keep original evidence and prior attempts; return changed inputs and affected descendants for revalidation.

## Stable planning clauses

### control-test-method

Apply the substantive method above to current bound inputs only. Capabilities: control-testing.

### control-test-acceptance

Apply the contract acceptance tests; retain actual checks and limitations separately. Completion covers only the performed operation.

### control-test-failure

Return failed prerequisites to the contract's named owners; restrict conclusions and invalidate affected descendants.
