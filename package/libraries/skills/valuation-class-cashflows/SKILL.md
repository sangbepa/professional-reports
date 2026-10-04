---
name: valuation-class-cashflows
description: Model dated going-concern distributions and funding for distinct share classes when their economic rights cannot be represented by a supported fixed-claim residual waterfall.
---

Use the current released model contract and supplied, cutoff-eligible rights evidence. Liquidation parity does not establish going-concern dividend participation. Market discounts are a separate diagnostic.

Select `class_rights=explicit_distribution_streams` explicitly. Supply typed `class_cashflows`: terminal_time, terminal_total_claim, parent_events and classes. Each owner-flow event contains time, distribution and capital_contribution. Each class has its actual share-class ID, cost_equity, terminal_claim, rights_reference, terminal_reference, perimeter `existing_cutoff_holders`, and events at every parent-event time, including explicit zero flows. Preserve the current-holder cohort under funding or dilution; missing entitlement evidence remains a gap.

`skeleton.py --describe` exposes the current fields and fixed units. `assembly.ModelBuilder.class_streams(supplied_typed_atoms)` registers provenance without importing approvals or choosing financial values. Monetary amounts use the model amount scale; current per-share values use issued shares less treasury shares. The model emits editable formula-linked Excel schedules. `math_audit.py` independently rebuilds arithmetic.

Reconcile distributions and capital contributions separately, terminal claims and aggregate class PV against current parent equity. A mismatch is unresolved; never manufacture terminal claims, participation weights or cash distributions to plug it. Substantiate declaration contingencies, dividend capacity, selected class rates and continuing terminal rights. Arithmetic reconciliation is not financial approval.

Frozen class streams do not automatically reprice when the parent case changes. Design a supported changed class case or retain parent-only diagnostics with their declared scope. Return unsupported rights, stale scopes and material divergences to valuation-design and the independent reviewer.
