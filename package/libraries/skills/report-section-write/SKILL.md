---
name: report-section-write
description: Write expert report sections from current accepted arguments, preserving qualifications and binding all metrics without adding numbers or changing calculations.
---

# Write the accepted argument as expert prose

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the argument contract](../financial-report-writing/references/argument-contract.md). Select the matching existing writing profile: [valuation](../financial-report-writing/references/valuation.md), [FDD](../financial-report-writing/references/fdd.md), [ESG](../financial-report-writing/references/esg.md), [earnings](../financial-report-writing/references/earnings.md), or [board](../financial-report-writing/references/board.md).

## Execute

1. Read `engagement_frame`, `reader_outline`, `argument_records`, `argument_acceptance`, `metric_bindings` and `evidence_observations`. Identify the selected section IDs and verify actual acceptance, input versions and numerical bindings. An author disposition cannot stand in for independent review.
2. Write in the requested language for the named expert reader. Develop the finding, mechanism, strongest material alternative, supported consequence and action naturally; keep claim strength, dates, units, perimeter and uncertainty near the assertions they qualify. Avoid formula tutorials, generic maxims and execution logs.
3. Bind every metric to its `metric_id`, original/model locator, version and approved display/rounding. Bind dates, votes and other numeric facts to supplied fact/event IDs. Introduce no new amounts, ratios, ranges, dates, vote counts or scenario inputs; request any missing calculation or fact upstream. Editorial changes do not change model inputs, methods or results.
4. Add citations from accepted evidence locators and exhibits from existing bound content. Preserve reported actuals, attributed management statements, forecasts and judgments in natural prose. Do not fabricate citations, silently resolve source contradictions or manufacture an exhibit to fill space.
5. For board minutes use only documented events, attendance, discussion, motion status and commitments. Keep proposals prospective and fictional samples prominently illustrative. Do not invent signatures, review passes or assurance wording. Rendering is a separate capability; this operation promises no generic ESG renderer.

## Return and restrict

Return `section_draft` with section/version and scoped text; `claim_bindings` mapping material passages to argument, evidence/fact and metric IDs plus qualifications; `exhibit_bindings` mapping displayed content to its supplied data; and `editorial_change_record` describing meaning-preserving edits and material returns.

Return unclear mandate to `report-frame`, structural conflicts to `report-outline`, and unsupported claims, missing numbers or changed argument strength to `report-argument`. Numerical faults go through that return to the actual reconciliation/model owner; never fix them in text. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### report-section-write-method

Execute the substantive method in this component against current bound inputs. Capabilities: section-writing, claim-binding.

### report-section-write-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-section-write-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

