---
name: dcf-model
description: Build a selected DCF from calibrated drivers, consistent cash flows and an explicit equity bridge; spreadsheet execution remains tool-dependent.
---

# Driver-based discounted cash flow

Modified adaptation of the installed Anthropic financial-services `dcf-model`.
Read `NOTICE`, `provenance.json`, [method contract](contract.json) and
[execution boundary](references/execution-contract.md). This is an agent method,
not a bundled spreadsheet engine or live data connector.

## Inputs and suitability

Consume the current mandate, reconciled historicals, selected method and scenario
records from `valuation-design`, discount-rate result/policy, ownership/claims
schedule and actual tool inventory. Resolve each observation and assumption to
its source or judgment binding. A DCF is appropriate only when the forecast,
capital burden and relevant cash-flow claim can be defended. For banks or other
regulated financial businesses, reconsider distributable equity cash flow or an
alternative method rather than applying industrial FCFF mechanically.

Plan periods, units, signs, input rows and formula locations before creating a
workbook. Maintain a driver dictionary with source, classification, date, unit,
calibration, model input path, alternatives and sensitivity consequence. Keep
reported history, normalized history and prospective assumptions distinct.

## Forecast and capital needs

1. Build revenue from supported volume, price, mix, capacity, utilization or
   contractual drivers. Reconcile segments and eliminations to consolidated
   revenue and profit. A residual labeled price/mix is not a measured forecast.
2. Model margins through supported cost and operating leverage drivers; do not
   assume margins improve with scale. Use separate scenarios only when decision
   uncertainty warrants them, with coherent links among demand, costs, capacity,
   working capital and financing. No default horizon or bear/base/bull quotas.
3. Derive operating taxes from the selected perimeter, losses and tax policy.
   FCFF = EBIT minus operating cash taxes + noncash D&A - capex - change in
   operating NWC, with other adjustments separately justified. Positive growth
   in operating NWC uses cash. Do not subtract interest from FCFF and then also
   give a WACC tax shield. FCFE requires a separately consistent financing build
   and cost of equity; do not bridge from FCFE as though it were enterprise value.
4. Separate maintenance/growth investment, depreciation, leases and replacement
   needs. Derive NWC from operating balances or supported turnover; reconcile
   acquisition, FX and classification effects before equating balance changes
   with cash flow. No sector-neutral percentage defaults.

## Discounting and terminal state

Bind the selected rate from `valuation-wacc` when WACC fits the method. Use gross
financing debt market values for nonnegative weights; cash belongs in the chosen
operating/nonoperating perimeter and bridge. Negative net debt is not a negative
financing weight. Nominal/real currency, inflation, taxes and risk perimeter must
match cash flows. Reconcile any independent rate build before replacing a model
rate.

Record each payment time from valuation date, including stub periods. For end-year
FCF, PV_t = FCF_t/(1+r)^t. Mid-year timing requires a stated flow convention. If
TV_T is the value at end of year T of cash flows beginning T+1, discount TV_T by
T even if explicit annual cash flows use mid-year points; adjust only through an
explicitly derived alternative terminal convention. Do not automatically reuse
T-0.5 for an end-T terminal value.

For a supported perpetuity, TV_T = FCF_(T+1)/(r-g) with r>g and a feasible steady
state. Under compatible stable growth and incremental ROIC assumptions, terminal
net reinvestment = NOPAT_(T+1) * g/incremental_ROIC. Document units, steady-state
conditions and replacement needs; the formula does not establish ROIC. Exit
multiples require comparable, dated, consistent terminal metrics. Explain
terminal-value share and dependence without universal acceptance thresholds.

## Claims, scenarios and spreadsheet construction

Use one enterprise-to-equity bridge, following the selected consolidation, NCI,
lease, associate, restricted-cash and share-rights policies. Match awards, treasury
shares, actual buybacks and issued classes to the date and economic rights. Avoid
subtracting NCI for already proportionate cash flows or adding associates whose
earnings are already capitalized. Financial-subsidiary funding is not automatically
industrial net debt. Price gap is conditional valuation output, not promised return.

Where a workbook is requested and a working tool is available, store raw inputs
and assumption drivers with source/judgment comments; derived cells use linked
formulas. Preserve editable scenario switches and traceable cell addresses. A
parallel numerical calculation can test formulas but cannot prove native workbook
recalculation. Avoid copying source sample company values or row numbers.

Sensitivity varies material uncertain drivers within justified bounds. Rebuild all
affected cash flows, discounting and bridge effects for every point; retain a
base-case tie and disclose invalid combinations such as r<=g. Use enough points
to reveal the decision effect, with no mandatory grid size, table count or routine
approval gate. Changes to the evaluation criterion or mandate use the applicable
change process; sensitivity under the current criterion proceeds within scope.

## Acceptance and failure

Return the editable model or formula specification, driver and scenario records,
DCF results, claims bridge, sensitivity results if relevant and explicit tool
verification states. Check source-to-history tie, forecast identities, NWC signs,
discount timing, terminal-state consistency, bridge completeness and rights-aware
per-share reconciliation. Native spreadsheet recalculation and rendered layout are
`unverified` until executed on the current workbook and saved/reopened successfully.
Do not promise a missing `recalc.py`, formula cache or working data connector.
Return evidence gaps to research, disputed economics/policies to `valuation-design`,
and actual formula defects to the model owner with affected artifacts invalidated.

## Stable planning clauses

### dcf-model-method

Execute the substantive method in this component against current bound inputs. Capabilities: dcf-modeling, cashflow-projection, terminal-economics, sensitivity-analysis, equity-bridge-modeling.

### dcf-model-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### dcf-model-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.


For domain-plan output names, read [artifact mapping](references/domain-artifacts.md).
