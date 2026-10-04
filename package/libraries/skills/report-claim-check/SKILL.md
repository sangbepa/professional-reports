---
name: report-claim-check
description: Check report claim meaning, numbers, qualifications and citations independently against originals and current model artifacts, recording actual review scope and channel.
---

# Check the claim against its actual basis

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the evidence contract](../financial-report-research/references/evidence-contract.md) and [the argument contract](../financial-report-writing/references/argument-contract.md). Select the matching existing writing profile: [valuation](../financial-report-writing/references/valuation.md), [FDD](../financial-report-writing/references/fdd.md), [ESG](../financial-report-writing/references/esg.md), [earnings](../financial-report-writing/references/earnings.md), or [board](../financial-report-writing/references/board.md). Consult [the research skill](../financial-report-research/SKILL.md) when the selected purpose requires evidence interpretation.

## Execute

1. Read `engagement_frame`, `section_draft`, `claim_bindings`, `argument_records`, `source_assessments`, `original_artifacts`, `metric_bindings`, `current_model_artifacts` and `review_request`. Identify requested independence and coverage. Use only an actual available independent review channel when independence is required/requested; record observed reviewer/channel identity, requested/observed settings and artifacts actually inspected. An author's self-check is labeled as such. If no independent channel is available, return that review as unavailable; never simulate a reviewer or its pass.
2. Check material claims, exhibits and headline conclusions against original passages/table cells/event records and current model inputs/results. Do not rely only on generated ledgers. Verify content/version availability at cutoff, citation entailment, classification, period, definition, unit, scale, sign, perimeter and displayed rounding.
3. Inspect meaning as well as arithmetic: support for the selected interpretation, adverse evidence, calibration, counterargument disposition and actual decision consequence. A correct number and citation do not establish economic adequacy or permit a stronger conclusion.
4. Check omissions and qualifications that change meaning, including scenario status, restricted populations, source conflicts and shared dependencies. For minutes, verify proposal/adoption and documented event/participant distinctions; fictional samples never pass as actual records.
5. Create issue-level findings with passage/metric/argument IDs, original/model locator, observed discrepancy, decision consequence, severity and responsible upstream operation or domain owner. Report separate source fidelity, numerical integrity, substantive adequacy and editorial results as supported, issue found or unverified. Acceptance covers only actual inspected artifacts and completed scope.

## Return and restrict

Return `claim_check_findings`, `claim_check_coverage` and `review_record` containing actual channel/independence, checked versions/hashes, results and limitations. Missing originals/model access or stale inputs remain unverified. Do not grant professional assurance or invent closure.

Route mandate issues to `report-frame`, missing inquiry to `report-research-plan`, source/timing to `report-source-assess`, extraction to `report-evidence-extract`, numerical alignment to `report-data-reconcile`, unsupported inference to `report-findings`, synthesis to `report-argument`, organization to `report-outline`, and wording/citation placement to `report-section-write`. Domain calculation changes go to the actual owner. Authors respond with new versions; the actual review channel rechecks affected claims before closure. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### report-claim-check-method

Execute the substantive method in this component against current bound inputs. Capabilities: claim-checking, citation-entailment, review-coverage-recording.

### report-claim-check-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-claim-check-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

