# Domain integration and stable IDs — 0.1.0-dev.1

## valuation-integration-wire — Authoritative interface

Read domain-contract.json for the domain's conceptual input/output contract. This is not a second engine plan schema. The main-owned schemas/plan.schema.json and schemas/meta.schema.json are authoritative for engine submission. Map required_work into nodes, gates into planned review nodes and checks, and unknowns into applicability_assessments plus concrete assessment nodes. Bind all actual component references as exactly `{id, version, sha256}`, obtained from the registry after the component is frozen. Never put dummy hashes or unbound illustrative sketches into an engine plan. meta-orchestrator and codex-native are main-owned IDs; this library does not redefine them or protected evaluation profiles.

`execution_support` is `complete` for valuation and `planning-only` for fdd, esg, market-research and investment-memo. Current meta_check permits valuation report-mode selection and rejects the other four in report mode. Complete denotes valuation domain execution-instruction coverage through installed native skills and main-owned adapters; status remains provisional and production_quality_verified is false. Actual execution capability, tools, data, rendering and independent review are per-run gates. Orchestration capabilities do not substitute for installed method skills. `requires: []` means the declarative component has no static installed-component dependency; actual plan nodes must still bind capable skills, personas and runtime.

## valuation-integration-rules — Simple rule semantics

plan-rules.json contains only a rules array. Each rule has a globally unique stable id, optional when with exactly fact and equals, require_capabilities, require_review_roles, require_artifacts, and on_unknown set to assessment. The single core rule omits when and is unconditional, as supported by pr/planning.py. Every conditional rule compares one boolean fact to true. There are no compound conditions, executable expressions, paths, actions or evaluation scripts.

Supply plan.facts as a map of the names below to **true, false or null**. Missing is unknown. Do not use numbers, strings or truthy values; the engine's generic facts schema currently does not enforce boolean/null types. Derive facts from profile/mandate evidence or an explicit method decision, preserving evidence and unit attribution separately. Materiality needs a mandate-specific rationale; absence of disclosure is not evidence of immateriality.

A true fact requires the union of that rule's listed capabilities, review roles and output names across plan nodes. A false fact does not trigger it. No first-match or priority applies. Required outputs are logical artifact IDs, not filename patterns. Spell them exactly as artifact-catalog.json and place each in the producing node's outputs. File paths, versions and hashes are bound by the runtime later. For every bound skill, union all acceptance/validations IDs into node.required_checks, all contract consumes into node.consumes, and all contract outputs into node.outputs. Domain output aliases are additional exact output names, not replacements for required skill outputs. Require only source/model/judgment/document review roles.

For a missing/null fact, current plan_check looks up applicability_assessments by rule ID. It requires a nonempty reason and evidence. A pending assessment must have status pending and task_id referencing an actual node; the returned pending_rules remain unresolved. Evidence may explicitly describe the observed access gap and source request; it must not invent evidence resolving applicability. A resolved assessment must state applies as a boolean with actual supporting evidence. This expresses whether the rule applies, not a raw fact of arbitrary type. After assessment, preferably revise facts with preserved provenance and recompile. No implicit false default.

The current checker tests plan-wide sets; it does not prove the capability is used for the right unit, the reviewer is independent, a model is economically sound or outputs exist. The domain policy and actual review must inspect per-unit coverage and dependencies. on_unknown documents the required convention; the current engine implements assessment handling for every unknown condition rather than selecting behavior from that string.

## valuation-integration-facts — Fact dictionary

| Fact | True means | Unknown assessment |
|---|---|---|
| financial_segment_material | A financial economic unit materially affects the subject interest, including mixed groups. | Classify financial business model, prudential perimeter and size. |
| full_consolidation_nci_material | At least one material externally owned subsidiary is valued at full value. | Establish ownership/rights and full-value treatment by unit. |
| proportional_nci_material | At least one material externally owned unit is already valued proportionally to the parent. | Trace ownership scaling and any existing NCI adjustment. |
| mixed_consolidation_material | Material unit values/bridges mix full and proportional bases. | Build unit ownership/perimeter map; do not infer from accounting labels alone. |
| leases_material | Lease economics materially affect model, peer metric or bridge. | Identify leases and assess coherent valuation conventions. |
| multiple_share_classes | More than one relevant legal/economic equity class exists. | Inspect charter/terms and distribution/conversion rights. |
| potential_dilution_material | Awards, options, convertibles or other contingent claims may materially dilute the interest. | Inspect point-in-time claims and proceeds. |
| financial_subsidiary_debt_material | Financial unit funding could materially affect group financing classification or bridge. | Reconcile funding, parent recourse and already-valued liabilities. |
| associates_material | Associate stakes or their income/cash flows materially affect valuation. | Trace earnings, stake value and look-through/separate-stake treatment. |
| industrial_fcff_selected | A supported current method decision selects industrial FCFF for at least one named eligible unit. | Assess method fit; selection is not presumed from being industrial. |
| comparables_selected | A current method decision selects a supported peer valuation for at least one named unit. | Assess peer economics and metric compatibility. |
| sotp_selected | A current method decision selects a separable unit valuation build. | Test unit separability, eliminations, capital and cost allocation. |
| cyclical_business_material | Cycle position could materially distort maintainable economics. | Assess cycle drivers and historical-to-maintainable evidence. |
| distress_material | Going-concern or financing/recovery uncertainty may materially change method/conclusion. | Inspect liquidity, maturities, covenants, claims and recovery alternatives. |

Full/proportional flags can both be true for different units. Financial/industrial-FCFF flags can both be true in a mixed group. These are work-coverage flags, not unit-level method permissions. POLICY.md prohibits applying industrial FCFF to balance-sheet financial intermediation.

## valuation-integration-stable-ids — Identity and version policy

Component IDs are globally unique across orchestration/persona/skill/runtime, use readable lowercase kebab names and are stable: valuation, fdd, esg, market-research, investment-memo. requires is an array of string component IDs. No contrary requires contract was found in the implementation contract or registry.

Internal rule and policy IDs carry their domain prefix. Every node basis clause must literally occur in the selected component's Markdown; valuation-rule-* headings in POLICY.md provide the rule clauses. Basis facts and reason must be nonempty and substantively support the node; substring presence alone is not evidence. Artifact IDs are stable logical outputs local to the plan; scope repeated unit instances in the artifact metadata and use unique producer nodes without inventing a second overall artifact of the same identity.

Preserve IDs for the same responsibility across revisions. Semantic changes get a new version and frozen hash; new responsibilities get new IDs; retired IDs are never reassigned. Task IDs should use domain, unit and responsibility in readable kebab form and remain stable within a lineage; duplicate IDs are invalid. A plan revision records the prior version/hash and why it changed. No author-machine absolute paths are permitted in delivered content. Repository-relative provenance paths are labels, not component-relative entrypoints.

## valuation-integration-development — Examples and checks

development/few-shot-cases.json contains visible DEVELOPMENT input/decision sketches. They are not full engine plans, heldout evaluation answers, completed reviews or accepted economic conclusions. Synthetic supplied premises are explicitly fictional, not original evidence. Compile any actual plan with live exact component references, actual actor, actual meta selection/hash and the main-owned evaluation reference. Never copy example prose as evidence for a real company.
