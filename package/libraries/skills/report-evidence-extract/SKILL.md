---
name: report-evidence-extract
description: Extract faithful observations and tables from assessed originals with exact locators, units, periods, perimeter and evidence classification.
---

# Extract observations faithfully

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the evidence contract](../financial-report-research/references/evidence-contract.md). Select the matching existing research profile: [valuation](../financial-report-research/references/valuation.md), [FDD](../financial-report-research/references/fdd.md), [ESG](../financial-report-research/references/esg.md), [earnings](../financial-report-research/references/earnings.md), or [board](../financial-report-research/references/board.md).

## Execute

1. Read `question_plan`, `source_assessments`, `original_artifacts` and `extraction_scope`. Resolve each selected source ID/version to its actual original. Extract eligible records for current support; if quarantined content is requested for investigation, retain its excluded status throughout.
2. Record `observation_id`, question/source IDs, original page/note/table/row or timestamp, exact relevant value or statement, metric definition, period, unit/currency/scale and entity/business/ownership perimeter. Preserve reported/adjusted basis, sign, footnotes, exclusions and whether a passage is quoted, faithfully paraphrased or transcribed.
3. Link every table and cell to its original table, header, row/column and footnote locators. Keep merged-header context, denominators, blanks, not-applicable markers and totals distinct. Check OCR against visible originals where available; uncertain characters remain unresolved. A missing cell is not zero.
4. Classify reported actuals, management guidance, market observations, third-party estimates, analyst judgments, proposals and unresolved items faithfully. For minutes, preserve documented event status and attributed speech; illustrative samples remain illustrative. Do not turn commentary into verified causation.
5. Preserve conflicts and unresolved definition/coverage gaps. Do not normalize, recompute, interpolate or select a preferred conflicting amount here; request reconciliation or further source work.

## Return and restrict

Return `evidence_observations` carrying exact observations, classifications, locators, scope and inherited source eligibility; `faithful_tables` with cell/header/footnote links; and `extraction_exceptions` with uncertain transcription, missing definitions or contradictory passages.

Return inaccessible originals, timing/provenance or version issues to `report-source-assess`; missing discriminating material to `report-research-plan`. Keep unusable observations out of the support set while preserving them in the exception record. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### report-evidence-extract-method

Execute the substantive method in this component against current bound inputs. Capabilities: evidence-extraction, table-transcription, evidence-classification.

### report-evidence-extract-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-evidence-extract-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

