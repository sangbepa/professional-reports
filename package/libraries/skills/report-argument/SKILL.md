---
name: report-argument
description: Synthesize accepted findings into decision arguments with support, credible counterarguments, bound consequences and explicit judgment limits.
---

# Synthesize the decision argument

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the argument contract](../financial-report-writing/references/argument-contract.md). Select the matching existing writing profile: [valuation](../financial-report-writing/references/valuation.md), [FDD](../financial-report-writing/references/fdd.md), [ESG](../financial-report-writing/references/esg.md), [earnings](../financial-report-writing/references/earnings.md), or [board](../financial-report-writing/references/board.md).

## Execute

1. Read `engagement_frame`, `finding_records`, `conclusion_limits`, `metric_bindings` and `domain_analysis`. Confirm which findings are accepted for the analytical case, by whom or which recorded disposition, on which current inputs. Acceptance is not independent review, agreement or professional signoff.
2. Build each `argument_id` around a consequential claim, its strength/scope, supporting findings and mechanism, strongest credible counterargument, discriminating evidence and disposition. Synthesize relationships and dependencies; do not merely concatenate facts or select a preferred recommendation before weighing evidence.
3. Bind the decision consequence to supplied metric IDs and current model paths, with scenario, horizon, units and conditions. Explain how the choice affects value, earnings, cash, disclosure, contract or governance as appropriate. If a quantified consequence is unsupported or inapplicable, record why, the qualitative implication and what work could quantify it; do not invent zero, probability or price mechanics.
4. Record selected judgment, rejected/open interpretations, uncertainty, reversal trigger and reader action. Reconcile cross-finding conflicts explicitly. Respect the narrowest material conclusion limit rather than averaging incompatible methods or strengthening a conditional case.
5. For minutes, the argument records event meaning and source fidelity, not a newly invented recommendation, debate or counterfactual. Mark analytic consequence/counterargument inapplicable with its reason where appropriate. Fictional samples stay illustrative; proposals never become documented approvals.

## Return and restrict

Return `argument_records` with claim, finding/evidence/metric links, counterargument, selection rationale, quantified consequence or explicit limitation, conditions and action; `argument_acceptance` with actual analytical disposition and review status; and `argument_returns` for unsupported relationships.

Return mandate conflicts to `report-frame`, unsupported inference or calibration to `report-findings`, and stale/inconsistent numerical consequences to `report-data-reconcile` or the actual domain calculation owner. Do not calculate new assumptions or close rejected judgments editorially. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### report-argument-method

Execute the substantive method in this component against current bound inputs. Capabilities: argument-synthesis, counterargument-assessment.

### report-argument-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-argument-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

