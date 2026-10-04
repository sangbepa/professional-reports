---
name: report-outline
description: Order accepted report arguments and findings for the specified expert reader and decision, without imposing a universal table of contents.
---

# Order the document for its reader

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the argument contract](../financial-report-writing/references/argument-contract.md). Select the matching existing writing profile: [valuation](../financial-report-writing/references/valuation.md), [FDD](../financial-report-writing/references/fdd.md), [ESG](../financial-report-writing/references/esg.md), [earnings](../financial-report-writing/references/earnings.md), or [board](../financial-report-writing/references/board.md).

## Execute

1. Read `engagement_frame`, `deliverable_acceptance`, `argument_records` and `argument_acceptance`. Identify the reader's decision sequence, known context, requested structure and materially open issues. Use only arguments accepted within their recorded conclusion limits.
2. Select an order that lets the reader assess the supported conclusion, important dispute, mechanism, consequence and action. Use dependencies and decision materiality, not file arrival order, an obligatory TOC, page quotas or a universal set of report headings.
3. For each `section_id` state its reader question, scoped finding/claim title, argument IDs, essential evidence/exhibits, metric IDs, adjacent qualifications and transition. Assign a home to every material accepted argument and unresolved issue, with purposeful cross-references for necessary reuse.
4. Keep board mode intact: decision papers distinguish requested action from adoption; minutes follow documented meeting/agenda/event relationships without an invented analytic narrative; fictional sample labels remain visible. Preserve required user structure and record any conflict requiring upstream resolution.
5. Mark material unsupported sections as restricted and route the missing argument. Remove repetitive background only where it does not remove necessary support, qualifications or event fidelity. Structure is editorial work, not new inference or numerical selection.

## Return and restrict

Return `reader_outline` with ordered section IDs, reader questions, titles, argument/exhibit bindings and transitions; `coverage_map` linking material arguments and gaps to sections; and `outline_returns` for uncovered or conflicting claims. Describe an exhibit's purpose and existing content, not an unimplemented renderer.

Return decision/format conflicts to `report-frame` and incomplete, contradictory or unsupported argument coverage to `report-argument`. Do not fill a conventional heading with invented material or relabel incomplete FDD/ESG work as completed assurance. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### report-outline-method

Execute the substantive method in this component against current bound inputs. Capabilities: reader-outline, argument-coverage.

### report-outline-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-outline-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

