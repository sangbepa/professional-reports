---
name: report-research-plan
description: Plan material decision questions, discriminating evidence, calibration work and search stopping conditions for a framed report mandate.
---

# Plan research around material questions

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the evidence contract](../financial-report-research/references/evidence-contract.md). Select the matching existing research profile: [valuation](../financial-report-research/references/valuation.md), [FDD](../financial-report-research/references/fdd.md), [ESG](../financial-report-research/references/esg.md), [earnings](../financial-report-research/references/earnings.md), or [board](../financial-report-research/references/board.md).

## Execute

1. Read `engagement_frame`, `deliverable_acceptance` and `existing_evidence`. Identify questions whose answers can change the reader's decision or the fidelity of the requested record. Reuse current evidence; do not prescribe a report-wide source quota.
2. For each question assign `question_id`, consequence, materiality rationale, credible competing hypotheses and discriminating observation/test. In factual minutes, competing interpretations concern ambiguous records rather than invented debate; illustrative samples retain their mode.
3. Specify original-source targets, search terms or authorized record requests, availability/cutoff checks, feasible access, expected record fields and downstream work affected. Rank inquiries by decision value and feasibility. Separate a planned search from an actually executed search; do not invent requests, interviews or search failures.
4. Define the calibration task connecting observations to candidate assumptions: required history/regimes, definitions, transformations, alternatives, sensitivity and responsible domain calculation owner. A qualitative statement cannot calibrate an exact input merely by citation.
5. Set per-question stopping conditions: evidence supports the requested strength, defensible uncertainty bounds permit the mandate, or remaining feasible work has diminishing decision value. An unresolved issue that can reverse the conclusion without a defensible bound requires a restricted conclusion and a return, even when search stops.

## Return and restrict

Return `question_plan` with question/hypothesis/test records and priorities; `search_plan` with feasible source targets, access, planned inquiries, stop conditions and gap handling; and `calibration_plan` with the required observation-to-input method, alternatives and owner. Record actual completed inquiries separately if supplied.

Return unclear decision/perimeter/cutoff or acceptance to `report-frame`. An unavailable record belongs in the plan's gap and feasible-next-inquiry fields, not a fabricated finding. Search completion is not evidence sufficiency, and this operation does not select model inputs or run a model. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### report-research-plan-method

Execute the substantive method in this component against current bound inputs. Capabilities: research-planning, hypothesis-testing-plan, calibration-planning.

### report-research-plan-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-research-plan-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

