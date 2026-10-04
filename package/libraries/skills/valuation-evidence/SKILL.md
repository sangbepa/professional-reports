---
name: valuation-evidence
description: Acquire and normalize source evidence for company valuation, with publication cutoffs, original locators, units, financial reconciliations and frozen snapshots.
---

# Valuation evidence

For a substantive valuation report, consume the question/evidence plan from `financial-report-research` ([entrypoint](../financial-report-research/SKILL.md)) and its valuation profile. This skill owns acquisition, extraction and normalization; research synthesis owns what an observation actually supports and which contrary evidence matters. If that plan is missing, identify material evidence questions for the orchestrator rather than recursively starting the entire engagement. A narrow source extraction remains proportionate.

Read the run mandate before collecting. Prefer issuer filings, exchange disclosures, regulator filings and dated issuer releases. Use price vendors for historical market observations with exact exchange session/time/currency; distinguish them from issuer accounting evidence.

For every source record publication/availability evidence, applicable period, retrieval time, original hash and precise locator. Enforce the information cutoff on content, not the current website's metadata. Exclude later results even if they cover an earlier financial period. Preserve originals so replay does not depend on changing URLs.

Extract reported actuals separately from normalized values. Keep unit/sign conversions, group/segment scope, elimination adjustments, fiscal-calendar differences and source cross-checks visible. Annual/interim recombination must match periods; LTM is annual + current interim − comparative interim.

Reconcile segment totals, accounting controls and cash/debt/shares. Source explanations do not substantiate precise forecast percentages. Mark absent data unavailable; attach an estimated/proxy classification only when the analysis deliberately chooses it and tests its impact.

Return source-backed observations separately from calibration/judgment claims. Correct dates, hashes and financial tie-outs do not validate maintainable margins, incremental returns or a valuation conclusion. Link material gaps to the affected assumption and the next useful primary-source inquiry, preserving the difference between absent disclosure, unavailable access and a negative finding.

Publish normalized data and an evidence register with source IDs and locators. Record discrepancies and downstream affected fields in the lifecycle specification. Notify the orchestrator before an input version changes. Follow the local method contract and execution boundary.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### valuation-evidence-method

Execute the substantive method in this component against current bound inputs. Capabilities: valuation-evidence, segment-reconciliation, source-acquisition-method.

### valuation-evidence-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### valuation-evidence-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.


## Packaged primary-source tools

For Korean issuer filings, `adapters/evidence/dart.py` at the pinned release root freezes official filing lists and receipt-bound originals using the host-provided `OPENDART_API_KEY`; credentials never enter artifacts. `dart_extract.py` preserves original table order, merged-cell attributes, raw hashes and nested-table text. This does not normalize accounting meaning or approve numeric facts. Register publication-day windows as intervals; never invent an intraday publication time. Probe network/access and verify original material table context before adopting observations. Other jurisdictions use suitable source tools chosen for the mandate.
