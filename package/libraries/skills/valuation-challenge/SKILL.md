---
name: valuation-challenge
description: Independently challenge valuation evidence, maintainable economics, method selection, equity adjustments and the resulting investment or board conclusion.
---

# Independent valuation challenge

Receive the mandate, frozen original sources, editable model, source register and proposed conclusions. Inspect them directly; do not rely on the author's claimed quality grade. Review original data and actual artifact versions. Keep author and reviewer identities distinct.

Challenge whether the conclusion follows from the evidence: maintainable margins, cycles, capital needs, terminal economics, discount rates, method comparability, control/ownership basis and enterprise-to-equity adjustments. Identify a credible alternative and quantify how it changes value where possible. Verify that downside assumptions are economically connected rather than arbitrary simultaneous shocks.

Calculation audit is a separate responsibility of `audit-xls`. A formula-error-free model is not evidence that its forecast is plausible. Neither a checklist nor presence of evidence rows substantiates an assumption.

Record each finding with artifact hashes, severity, consequence, source locator, affected work unit and requested action. Distinguish material defects from disclosed bounded estimation uncertainty. Reviewer closure requires checking the revised artifact/author response; the author cannot close findings by relabeling them.

Assess the requested conclusion strength under `financial-report-writing`'s [argument contract](../financial-report-writing/references/argument-contract.md). Review selection rationale and calibration for dominant assumptions, credible adverse explanations, cross-check dependence and consequences. Distinguish supported observations, reasoned judgments, scenario-only calculations and material research needs. Do not accept a rejected valuation recommendation merely because it acquires a conditional disclaimer; accept defensible bounded judgments without demanding impossible certainty.

Record `substantive_claim_support` against the actual purpose and current argument/evidence/model artifacts: what level is supported, what is not, which material work remains, and why. Existing source/model checks or layout scores do not substitute for this judgment. An AI reviewer must state its actual scope and identity/configuration evidence; no professional title or serving-model setting is inferred.

Recommend a bounded review disposition only after checking revisions; release authority remains with the mandate owner. Material errors and conditional estimates must be reflected in the actual conclusion. Record actual review scope and AI identity/model when exposed by the environment; do not invent a human/partner review. Follow the local method contract and execution boundary.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Ownership and policy challenge

Inspect the actual `ownership_policy` and `segment_reconciliation`. Challenge
eliminations, central allocations and associate double counting; 100% versus
proportionate NCI treatment; lease EBITDA/cash flow/funding/bridge consistency;
and share rights, dilution proceeds and actual buyback timing. A mechanically
balanced bridge can still value the wrong claim. Record an alternative treatment
and consequence where the available model permits, otherwise identify the exact
missing work. No agent is spawned by this component; unavailable independent
review remains unavailable and an author challenge is labeled self-check.

## Stable planning clauses

### valuation-challenge-method

Execute the substantive method in this component against current bound inputs. Capabilities: valuation-challenge, economic-assumption-challenge, nci-policy, consolidation-policy, lease-policy, share-rights-policy.

### valuation-challenge-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### valuation-challenge-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

