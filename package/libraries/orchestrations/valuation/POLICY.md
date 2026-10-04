# Valuation domain policy — 0.1.0-dev.1

Status: provisional. Execution support: **complete**. Production quality verified: **false**. This domain covers the valuation execution workflow through installed native skills and main-owned adapters. Report-mode selection is allowed; actual tools, method coverage, data, model, rendering and review are checked for each run. Instruction coverage is not evidence of a completed valuation, independent review or production quality. Release authority remains with the host.

## valuation-rule-core — Frame, evidence, methods and review

Fix subject interest, intended decision, valuation basis, ownership/control, currency, valuation date and information cutoff before adopting methods. Preserve the company profile's stable unit IDs and map every material exposure to legal and economic ownership. Start fresh cutoff and source snapshots for every engagement. Bind original hashes, publication/availability evidence, retrieval time, precise page/table/cell, periods, currencies, units and transformations. A later website timestamp does not establish earlier availability.

Separate source facts, calculations, analyst assumptions and estimates/proxies. For each material selected assumption retain observations, calibration, credible alternatives, the chosen judgment and its value consequence. A source describing industry prospects does not calibrate a numerical long-term margin. Missing disclosure, denied access and a negative finding are distinct.

Choose methods contingently. DCF, direct FCFE, DDM, residual income, comparable multiples, NAV, liquidation/recovery and SOTP are candidates. A plan can legitimately select neither DCF nor comps. Require positive economic fit and usable inputs, record excluded/deferred alternatives and commission missing evidence. Do not automatically average incompatible indications; explain material divergence and shared forecast/bridge dependencies. Reverse DCF is a market-implied diagnostic under specified assumptions, not independent corroboration.

Separate required work from selected methods and completed analysis. Each method decision identifies the unit, method, primary/cross-check/diagnostic/excluded role, evidence bindings, alternatives, rationale and limits. Method selection flags in plan.facts are derived from those decisions, never from a universal recipe. A selected method with no actual capable provider is a capability gap. Persona or orchestration capabilities do not substitute for bound skill capabilities.

Build one attribution-controlled equity bridge. Align date, currency, cash-flow perimeter, ownership, financing claims and equity rights. Distinguish excess cash from operating/restricted cash; evidence pensions, tax, provisions and guarantees. Track signed adjustments and stable attribution IDs; do not insert an unexplained balancing plug.

Required source/model/judgment/document roles identify future independent review work. They do not certify that review happened. Source review inspects originals and coverage; model review checks calculations and basis; judgment review challenges economics and conclusion strength; document review inspects actual final content, numerical bindings, qualifications and rendered artifacts. Record actual independent channel/identity, inspected versions and findings. Authors cannot simulate reviewer approval or close an independent finding for its reviewer. User authorization is not assumption approval.

## valuation-rule-financial-segment — Financial equity and capital

Identify balance-sheet intermediation, insurance, lending and fee-business economics within the financial segment. For balance-sheet financial businesses, assess equity valuation using **dividend discount, residual income and regulatory-capital-constrained distributions**, with cost of equity. Industrial FCFF, industrial net-debt logic and enterprise WACC are not a default or substitute. A fee-only business may justify industrial-style analysis after an explicit classification and perimeter decision.

DDM needs support for sustainable, distributable equity cash after growth capital, prudential requirements, buffers, stress needs and legal distribution restrictions. Historical dividends alone are insufficient. Reconcile statutory earnings, cash availability and capital movements. Required/target regulatory capital is not automatically excess cash or a second deduction from equity value.

Residual income needs attributable opening book equity, cost of equity and expected returns, plus clean-surplus reconciliation, OCI, acquisitions/disposals, distributions and material accounting distortions. Residual income and DDM may be alternatives, not mandatory simultaneous calculations. A method may be deferred if its prerequisites are absent.

Record framework, jurisdiction, entity perimeter and evidence for actual capital requirements. Do not invent regulatory ratios or assume a published standard applies. financial-regulatory-capital-schedule can record a supported non-applicability decision for a fee business; an empty schedule cannot do so. Direct equity cash flows use cost of equity, and book/return measures must cover the same equity claims. Reconcile the financial segment to group reporting before SOTP inclusion.

## valuation-rule-full-nci — Full consolidation

When the unit is valued at 100% of business value, include matching full operating value, assets and financing claims, then deduct economic value of external NCI in included subsidiaries once. Book NCI is not automatically economic value. Match ownership dates and NCI economic rights. For a subsidiary valued directly on equity, apply parent/NCI allocation to that equity value; do not rebuild and subtract its funding through an industrial EV bridge.

## valuation-rule-proportional-nci — Proportional ownership

When unit values already reflect the parent's economic interest, use matching attributable cash, debt and other adjustments. Do not deduct the same NCI again. Reconcile parent-only financing and assets separately. Equal ownership percentage is not enough where preference or participation rights differ.

## valuation-rule-mixed-consolidation — Mixed bases

Map each unit's full or proportional treatment, parent ownership and claims, including corporate costs, cross-holdings and intercompany elimination. Reconcile to consolidated totals before aggregation. Both full and proportional NCI rules may apply to different units; they are not contradictory company-wide flags. A mixed group must not conceal a unit-level double deduction in a net group residual.

## valuation-rule-leases — One coherent lease convention

Choose a supported operating or financing convention for each model and reconcile across forecasts, earnings metrics, peer EV, reinvestment, capital weights and equity bridge.

Under an operating convention, include the full economic lease operating burden and do not deduct the same lease liability again. Under a financing convention, reconcile operating cash flows and reinvestment, including right-of-use asset additions/depreciation and replacement needs, and include corresponding lease debt once. Do not combine cash flows after full rent with another lease-debt deduction, or pre-rent earnings with lease-excluded enterprise values without adjustments. A balance-sheet liability label alone cannot choose the valuation convention.

## valuation-rule-share-rights — Equity allocation

Identify contractual dividend, preference, participation, conversion and liquidation rights for every material class. Allocate total equity using the actual rights/waterfall and class-specific dilution; equal division is valid only with evidenced equal economic rights. Discuss observed liquidity, voting/control or market discounts separately from contractual economic allocation. A price difference is not by itself proof of a particular intrinsic rights adjustment.

## valuation-rule-dilution — Shares and financing events

Use point-in-time shares and claims, not weighted-average EPS denominators. Reconcile options, awards, convertibles, exercise/conversion proceeds and extinguished claims. Executed repurchases/issuances affect cash and shares together; authorized but unexecuted events are explicitly scenario-labeled. Avoid counting both a converted claim and its old debt/preference liability.

## valuation-rule-financial-debt — Financial funding versus industrial debt

Do not subtract deposits, policyholder funding or other financial subsidiary liabilities again when they are already reflected in its direct equity value. Separately identify industrial financing, parent holding-company debt, recourse guarantees, pledged assets, restricted cash and intra-group loans. Attribute each obligation once, on the same ownership basis as its associated unit value. Financial subsidiary funding is not automatically manufacturing debt for WACC weights or an industrial EV-to-equity deduction.

## valuation-rule-associates — No duplicated associate value

Choose one coherent policy for each associate. With separate stake valuation, remove the same associate earnings/dividends/cash-flow value from the operating earnings metric or DCF before adding the stake, and handle taxes, holding costs and encumbrances once. With proportional look-through, include matching assets, operating results, financing and ownership and do not add the stake again. Track each exposure across metrics, cash flows, unit values and bridge through one stable attribution ID. Apply the same discipline to cross-holdings and intercompany balances.

## valuation-rule-industrial-fcff-selected — Contingent FCFF

Only after supported method selection, model industrial operating cash flows with compatible tax, inflation, nominal/real currency, discount timing, reinvestment and terminal economics. Cost-of-capital inputs need source/assumption bindings and the same operating perimeter. Equity class values and gross financing weights must be consistent and nonnegative; net cash is not negative financing debt. A beta including nonoperating holdings may require explicit adjustment. No default risk premium, growth rate, tax rate or margin is supplied here.

A mixed group may select industrial FCFF for industrial units while using direct equity methods for financial units. The company-level financial and FCFF flags can therefore both be true; the method decision map and independent review enforce unit-level separation.

## valuation-rule-comparables-selected — Contingent comparables

Only after supported selection, reconcile peers by economic exposure, calendar, metric normalization, currency, date, ownership/control and equity/enterprise numerator-denominator pairing. For financial businesses assess equity-compatible multiples and differences in book value, ROE and capital. Exclude incomparable observations with reasons. No suitable peers means the method may be omitted, not populated with arbitrary names. Shared models and bridge inputs reduce independence.

## valuation-rule-sotp-selected — Unit-specific methods

SOTP requires supportable unit separability, methods by unit, corporate cost/capital allocation, ownership, tax leakage and elimination. Reconcile to consolidated totals. Financial units can use DDM/residual income while industrial units use FCFF or other justified methods. Do not separately capitalize a revenue elimination whose profit is already removed. Estimated allocation remains conditional and sensitivity-tested.

## valuation-rule-cycle — Maintainable economics

Separate price/mix, volume/capacity, utilization, costs, working capital and maintenance/growth investment. Explain the transition from a peak/trough to a supportable terminal state. Management aspirations are not attributed numerical forecasts. Investigate why method indications diverge; saying 'cyclicality' does not resolve the adopted conclusion.

## valuation-rule-distress — Recovery and going concern

Assess going-concern, restructuring and liquidation alternatives with claim ranking, realization timing, costs, tax and recovery evidence. Do not apply an unsupported terminal perpetuity. Early-stage or otherwise sparse-evidence businesses need milestone, financing and survival scenarios; do not invent probabilities. Explicitly identify a missing specialist/model capability and limit the conclusion until resolved.

## valuation-policy-unknowns — Assessment and dependency limits

Unknown means missing evidence, not false. Preserve affected unit IDs, original evidence/access limits, a concrete assessment task and the interim conclusion restriction. Reassess plan.facts after that work and create a new plan revision. A pending applicability assessment is not a passed financial gate, even if the engine accepts the plan graph. Block affected model/conclusion dispatch until material unknowns are resolved or an independently supported bounded conclusion is established. Unaffected evidence work can continue.

## valuation-policy-release — Version and actual review

Freeze exact component references, source/model artifacts and plan revisions. Changes invalidate consumers and dependent argument, prose, presentation and reviews. No development example, structural check or schema pass supplies a review or production approval. Actual native execution, reviewer independence, current output hashes and resolved findings belong to the host runtime and release process. Provisional status does not block report-mode selection; missing actual capabilities or unresolved material gates block the affected execution or final release.

## valuation-policy-execution — Execute the selected domain

1. Frame the actual engagement, inspect available inputs and freeze the cutoff and original-source manifest. Use bound mandate-framing, research and evidence skills. Record unknowns, access limits and dependencies before calculation. Do not reuse a prior issuer's figures as defaults.
2. Create the unit method/ownership map, assumption calibration and equity-bridge policy. Apply the simple plan rules and commission applicability assessments for unknown facts. Bind actual installed skill capabilities and exact references for each chosen method. Generic native skills may implement an engagement-specific model; successful capability-name matching alone does not establish its numerical adequacy.
3. Dispatch ready nodes through main-owned codex-native and its actual host tools/adapters. Each node uses a current attempt, its explicit input bindings, an accountable producer, declared outputs and observed checks. Never simulate agent returns, execution logs or reviews. Missing method functionality yields a named capability gap and proposed bounded next work, not invented output.
4. Build and calculate the chosen models, reconcile units/ownership and the single equity bridge, and test material assumptions and alternatives. Preserve editable formulas or reproducible calculation instructions, inputs, actual outputs and applicable tolerances. Native financial-equity analysis must implement the selected DDM/residual-income/capital model rather than run an industrial DCF under a new label. Obtain actual source, model and economic judgment review against the current artifacts; return defects to their responsible producers.
5. Develop findings, arguments, reader-specific outline and sections using accepted current analysis. Bind every quantitative claim to model/source paths; keep conditional estimates conditional. Compose through available native writing/design/rendering capabilities and main-owned adapters, preserving an approved design when supplied. Verify actual generated output and rendered pages. A missing renderer/tool or stale design/input binding is an explicit run-level gap.
6. Obtain actual independent document review against the selected final artifacts, plus re-review of any changed source/model/judgment dependencies. Resolve material findings through the actual originating review channel. Export the report and agreed formats, model/workbook, source manifest, planned and actual work specification, component pins and observed checks through the host release gates. Mark inaccessible or unperformed checks honestly; do not represent author self-checks as independent approval.

Substantive evidence or model changes create a new input/plan version and invalidate dependent results and reviews. Independent work may proceed while a bounded gap is resolved, but final conclusions and release cannot consume unverified material prerequisites. Changing the selected method within the mandate is analysis; changing protected acceptance criteria follows the main-owned approval process.


## valuation-rule-history-calibration — Amounts, subsets and economic support

Provisional corrective policy grounded in independently recorded development findings; protected grading is unchanged. Keep original reported operating-profit amounts, shares of group profit and margins in distinct fields. Reconcile available same-period segment amounts and signed eliminations to an independently extracted consolidated control; a contribution percentage is not an EBIT amount. Preserve exact amount/percentage column headings and source units. A history amount that cannot reconcile is unresolved evidence, not a forecast calibration anchor.

Map depreciation/amortization components and explicit subset relations before summing. PPE depreciation that already includes right-of-use assets must not be combined additively with its ROU subset. Reconcile historical capital charges, future depreciable assets, investment and lease cash flows with the selected lease convention. The source table's inclusion language controls the subset assertion; arithmetic consistency does not independently establish that language.

Support discount-rate choices with cutoff-eligible original term yields, equity-risk and beta/leverage evidence and borrowing costs. An observed policy rate is not a term bond yield. When proxies remain necessary, demonstrate the calibrated choice and value consequence; candid labeling alone does not establish decision adequacy.

Reconcile minority/investee returns, distributions, capital movements and rights to the same consolidated operating case. Check the timing of actual expenditure and share changes instead of treating an authorization/contract envelope as executed cash. Distinguish liquidation rights from going-concern dividend participation. Preserve new findings until a fresh independent reviewer verifies the exact corrected artifacts.
