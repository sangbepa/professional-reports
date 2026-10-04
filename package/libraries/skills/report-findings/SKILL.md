---
name: report-findings
description: Infer scoped findings from reconciled evidence, separating observed or calculated results from explanations and the conclusion strength the evidence permits.
---

# Infer findings at the supported strength

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the evidence contract](../financial-report-research/references/evidence-contract.md) and [the argument contract](../financial-report-writing/references/argument-contract.md). Select the matching existing research profile: [valuation](../financial-report-research/references/valuation.md), [FDD](../financial-report-research/references/fdd.md), [ESG](../financial-report-research/references/esg.md), [earnings](../financial-report-research/references/earnings.md), or [board](../financial-report-research/references/board.md).

## Execute

1. Read `engagement_frame`, `question_plan`, `source_assessments`, `evidence_observations`, `reconciled_data`, `metric_bindings` and `domain_analysis`. Check eligibility, unresolved reconciliation and actual domain review coverage before drawing a conclusion.
2. For each material question create `finding_id` and separate the observed/calculated result, attributed explanation and analyst inference. Describe the mechanism supported by evidence, not a cause inferred from arithmetic, correlation or management confidence.
3. Weigh credible alternatives, contrary evidence, coverage, shared dependencies and calibration. Explain the selection rationale and conditions that would change it. Use current bound metrics for consequences; unsupported precision returns to the domain owner.
4. Assign a disposition such as `supported_observation`, `reasoned_judgment`, `bounded_scenario_only` or `research_required`; use `analysis_required` for missing domain calculations. Record allowed conclusion strength, scope, uncertainty and question consequence. Unbounded issues capable of reversing the conclusion cannot support the stronger selection.
5. For factual minutes infer only what event records establish; do not supply hypothetical economic mechanisms, discussion or adopted resolutions. Fictional sample findings remain labeled illustrative. Source validity does not establish maintainability, transaction agreement, statutory applicability or assurance.

## Return and restrict

Return `finding_records` with question links, result/explanation/inference distinctions, supporting and contrary observation/metric IDs, rationale, disposition and conclusion limits; `finding_gaps` with discriminating evidence or domain tests; and `conclusion_limits` for downstream synthesis.

Return unclear mandate/strength to `report-frame`, missing discriminating research to `report-research-plan`, source eligibility to `report-source-assess`, extraction faults to `report-evidence-extract`, and measurement/bridge faults to `report-data-reconcile`. Return economic-method or recalculation work to the named domain owner. A narrower finding is acceptable only when it fits the mandate and is explicit in the conclusion. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### report-findings-method

Execute the substantive method in this component against current bound inputs. Capabilities: finding-inference, conclusion-strength-assessment.

### report-findings-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-findings-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

