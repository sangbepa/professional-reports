---
name: report-source-assess
description: Assess originals, provenance, period and information-set availability of candidate report sources; quarantine uncertain timing without judging assumption plausibility.
---

# Assess the source, not the assumption

Read [the operation contract](contract.json). Supply `artifact_manifest` with current input IDs, locations, versions, hashes/access limits and actual acceptance/review references. Map equivalent supplied records to contract field names for isolated execution; preserve the existing ledger schema. Verify accessible hashes/versions and return stale bindings. In `operation_record`, retain actual input bindings and consumed fields. A changed `consumes` input field invalidates this operation's outputs and dependent artifacts/reviews.

Read [the evidence contract](../financial-report-research/references/evidence-contract.md). Select the matching existing research profile: [valuation](../financial-report-research/references/valuation.md), [FDD](../financial-report-research/references/fdd.md), [ESG](../financial-report-research/references/esg.md), [earnings](../financial-report-research/references/earnings.md), or [board](../financial-report-research/references/board.md).

## Execute

1. Read `engagement_frame`, `question_plan` and `candidate_sources`. Open accessible original content; distinguish original, reproduction, commentary and unavailable material. Record source ID, originator, URL/file, document version, retrieval time, measured content hash and availability evidence. Do not infer content from a landing page or inaccessible citation.
2. Separate covered period, publication, content-version availability and retrieval time. Compare the actual frozen content's availability with the cutoff. A later restatement covering an earlier period remains later information. Unknown publication/version timing is `quarantined_unknown_timing`; post-cutoff content is `excluded_post_cutoff`. Neither can support an as-of conclusion until eligibility is established, though both remain visible for follow-up.
3. Assess provenance, proximity to the underlying record, coverage and shared origins. Several retellings of one release are one observation. Identify conflicts between originals and repeated claims, superseded versions and inaccessible populations; preserve source-specific contradictions rather than selecting the convenient source.
4. Set `information_set_status` and `access_status` separately, plus provenance limitations, precise locators and permitted uses for each source. An eligible source can still be a management assertion or lack coverage; availability does not establish independence or an economically plausible assumption. Illustrative sample material is never real event evidence.

## Return and restrict

Return `source_assessments` with source/version, periods, availability evidence, statuses, provenance/dependency groups and question links; `timing_quarantine` with unknown/post-cutoff items and the evidence needed to resolve eligibility; and `source_conflicts` linking disputed records and next discriminating inquiry.

Return ambiguity in cutoff/perimeter to `report-frame`; missing originals, availability proof or unresolved source conflict to `report-research-plan` with a feasible target. Retain unusable sources in the register without lending them current support. Leave assumption calibration and economic adequacy to later judgment and domain work. Return the named outputs with IDs, locations and versions. `operation_record` records actual checks, limitations, status (`complete`, `restricted`, or `returned`) and affected downstream artifacts. Each `failure_records` entry identifies the affected record, missing evidence/test, target operation or domain owner, next action and interim conclusion restriction. Never record an unperformed check or review as passed.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### report-source-assess-method

Execute the substantive method in this component against current bound inputs. Capabilities: source-assessment, information-cutoff-validation, source-provenance.

### report-source-assess-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### report-source-assess-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

