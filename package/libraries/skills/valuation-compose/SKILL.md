---
name: valuation-compose
description: Bind current valuation arguments and model metrics into a content packet and pass presentation to an explicitly verified renderer.
---

# Compose valuation content and its presentation handoff

Read [method contract](contract.json), [execution boundary](references/execution-contract.md),
[writing policy](../financial-report-writing/SKILL.md) and its valuation profile.
Consume current accepted arguments, evidence, model results, metric bindings,
outline, format requirements and actual review dispositions. Analytical acceptance
is not independent approval or signoff; retain its scope and author/source.

Build the document around the actual decision, strongest support, competing
explanations and consequences. Explain why the selected earning/reinvestment path
and methods fit the economic unit, how material alternatives change the judgment,
and which evidence would change it. Use a structure justified by these arguments,
not a fixed DCF-plus-comps template, prescribed page count or company fixture.

Bind each numeric sentence, exhibit and chart datum to current result paths and
source facts. Record units, scenario, date, perimeter, rounding and qualifications.
Use one reconciled enterprise-to-interest bridge, preserving NCI, leases,
consolidation and share-class rights. Distinguish selected indications, conditional
scenarios and statistical intervals; a model price gap is not a trading forecast.
Never insert an unbound amount, retune assumptions in prose or resolve method
divergence through a silent average.

Separate editorial and substantive revisions. For editorial revisions preserve
current accepted meaning and numerical bindings. Return inadequate evidence or
changed judgments to research/design, version inputs and invalidate dependent
results/reviews, then consume the updated record. An old review cannot approve
new bytes or a stronger conclusion. Source/model checks and typography review
are different evidence.

Deliver section drafts, claim/exhibit bindings, content-retention map and a design
handoff to [report-design](../report-design/SKILL.md). Reuse the hash-bound existing
reference where suitable. The package-level `adapters/valuation/build.py` includes the shared calculation,
editable XLSX and neutral report-outfit renderer. Read its input schema and
README from the pinned release root; supply current accepted narrative and exact
model/input bindings. Its synthetic validation is engineering evidence only.
Probe and execute required runtime tools; when unavailable, return the exact
missing capability and current content packet. Inspect every final PDF page,
reconcile content/numbers, and keep the print report self-contained.

Keep execution machinery, hash records and formula counts in supporting records;
retain in the business document only limitations that affect its reader. Return
unsupported conclusions to argument/research owners and binding errors to the
model/reconciliation owner. Publication disposition remains restricted while
material current substantive or required document checks remain unresolved.

## Stable planning clauses

### valuation-compose-method

Execute the substantive method in this component against current bound inputs. Capabilities: valuation-content-composition, model-to-report-binding.

### valuation-compose-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### valuation-compose-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

