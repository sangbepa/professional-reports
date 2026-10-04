---
name: report-data-reconcile
description: Align evidence and supplied model metrics across calendars, currencies, scale and perimeter, preserving bridges and detecting duplicated attribution.
---

# Reconcile measurement bases and attribution

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the evidence contract](../financial-report-research/references/evidence-contract.md). Select the matching existing research profile: [valuation](../financial-report-research/references/valuation.md), [FDD](../financial-report-research/references/fdd.md), [ESG](../financial-report-research/references/esg.md), [earnings](../financial-report-research/references/earnings.md), or [board](../financial-report-research/references/board.md). Use supplied domain-approved definitions and model results; this operation does not choose valuation, accounting or ESG measurement methods.

## Execute

1. Read `engagement_frame`, `evidence_observations`, `faithful_tables`, `reconciliation_basis` and `current_model_artifacts`. Identify comparable measures by calendar, point-in-time versus duration, currency/FX date or period, scale, sign, definition, ownership/perimeter and classification. Mark incompatible or missing bases before aggregation.
2. Perform only supported, authorized alignment transformations. Record original and aligned values, input observation IDs, formula, conversion source/date, assumptions and target basis. Preserve quarter/YTD/annual and stock/flow distinctions. Do not invent FX rates, annualization, acquisition allocations, maintainable adjustments or domain tolerances.
3. Construct reconciliations and bridges with signed components, opening/closing or source/target totals, attributable drivers and residuals. Retain differences rather than inserting a balancing plug. Any tolerance must come from the supplied basis and be justified for the decision.
4. Track each underlying event/exposure across bridges and outputs through `attribution_id`. Flag overlapping treatments, reused components, shared model inputs and duplicated deductions/benefits. An arithmetic bridge is not evidence of operating causation or an independent cross-check.
5. Return `metric_bindings` for supported passthrough and transformed metrics: metric ID, value, unit/scale, period, perimeter, classification, observation/original locator or current model result path, input/output version/hash and allowed display/rounding. Preserve supplied domain review status; do not invent acceptance.

## Return and restrict

Return `reconciled_data`, `reconciliation_bridges`, `metric_bindings`, `attribution_map` and `reconciliation_exceptions`. Link each residual/incompatibility/overlap to the affected decision and result.

Return scope/date ambiguity to `report-frame` and missing or contradictory extracted fields to `report-evidence-extract`. Unsupported domain methods or changed model assumptions go to the named model/domain owner, with affected results invalidated; do not repair calculations through prose. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Apply supplied ownership policies

Consume `reconciliation_basis.ownership_policy` when consolidation, NCI, leases
or share rights affect the output. Check all four named policies for consistency
with observed legal/economic perimeter; do not choose missing policies here.
Reconcile group and segment totals after eliminations and central allocations.
Trace NCI to fully consolidated versus proportionate cash flows, lease treatment
to both earnings and claims, and point-in-time share rights to the denominator.
Return `segment_reconciliation` and `ownership_policy_exceptions` with supported
control totals, residuals, duplicate exposures and affected outputs. Missing
policy selection returns to `valuation-design` or the named domain owner.

## Stable planning clauses

### report-data-reconcile-method

Execute the substantive method in this component against current bound inputs. Capabilities: data-reconciliation, segment-reconciliation, consolidation-policy, lease-policy, nci-policy, share-rights-policy, metric-binding, duplicate-attribution-detection.

### report-data-reconcile-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-data-reconcile-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.


For domain-plan output names, read [artifact mapping](references/domain-artifacts.md).
