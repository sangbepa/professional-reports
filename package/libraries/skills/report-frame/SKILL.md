---
name: report-frame
description: Frame a report mandate into its reader decision, perimeter, information cutoff and deliverable acceptance conditions before research or drafting.
---

# Frame the mandate

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the evidence contract](../financial-report-research/references/evidence-contract.md) and [the argument contract](../financial-report-writing/references/argument-contract.md). Select the matching existing research profile: [valuation](../financial-report-research/references/valuation.md), [FDD](../financial-report-research/references/fdd.md), [ESG](../financial-report-research/references/esg.md), [earnings](../financial-report-research/references/earnings.md), or [board](../financial-report-research/references/board.md). Consult [the existing writing skill](../financial-report-writing/SKILL.md) for actual deliverable capabilities; keep domain methods in those profiles.

## Execute

1. Read `mandate`, `supplied_constraints` and `available_deliverables`. Identify the decision or recordkeeping purpose, expert audience, requested conclusion strength, language and user format. Distinguish confirmed instructions, proposed choices and unresolved requirements; do not assume an issuer, transaction role or desired recommendation.
2. Record entity/interest, ownership and business perimeter, valuation/reporting date, information cutoff with timezone where material, evidence access and applicable framework/jurisdiction questions. Distinguish period end from information availability. Leave uncertain applicability unresolved.
3. Define acceptance by what the deliverable must enable the reader to decide or establish, evidence/calculation coverage and allowed uncertainty. Scope source access honestly: screening cannot promise completed transaction FDD or assurance. Verify requested output capability; do not promise a generic ESG renderer or an implemented service from instructions.
4. For board work set `document_mode` to decision paper, factual minutes or fictional sample. Proposals remain prospective, minutes require event evidence, and invented sample events remain prominently illustrative. Set feasible deliverables and their substantive versus format checks, without source or length quotas.

## Return and restrict

Return `engagement_frame` containing purpose, audience, decision, language, perimeter, valuation/reporting dates, information cutoff, access, document mode, framework/jurisdiction questions, requested conclusion strength and selected profile references; and `deliverable_acceptance` containing formats, required structure, capability evidence, completion criteria and open constraints. No model assumptions are selected here.

If a missing mandate fact changes the work materially, return it to the mandate owner with feasible bounded work identified. `failure_returns` is empty because framing has no upstream operation. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

These contracts describe agent work, not JSON Schema validation or a callable AI service.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### report-frame-method

Execute the substantive method in this component against current bound inputs. Capabilities: mandate-framing, deliverable-acceptance.

### report-frame-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-frame-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

