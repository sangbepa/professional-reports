---
name: valuation-wacc
description: Calculate a reproducible WACC from selected capital-market inputs and consistent market-value weights. Use as an isolated discount-rate work unit within an enterprise valuation.
---

# A discount-rate work unit

Accept a current capital-cost input packet, its source/assumption bindings and the operating cash-flow perimeter from `valuation-design`. This operation computes a selected rate; it does not select the economic assumptions or certify their suitability. Read the valuation profile in [financial-report-research](../financial-report-research/references/valuation.md) when the support for an input remains disputed.

Keep rates as decimal fractions. Equity and gross financing debt must use the same currency and monetary scale; use market values for the selected weighting policy. Include all relevant equity classes consistently. An authorized repurchase is not an executed reduction in cash or shares. Do not infer that all reported cash can be removed from beta or that manufacturing debt includes financial-subsidiary funding.

Choose and explain the debt, lease, tax-shield and beta policies before calculating. The supplied beta must already match the selected operating perimeter and leverage policy; this helper does not silently unlever, remove portfolio assets or relever an observed issuer beta. Such adjustments need their own supported design record. A risk-free rate, ERP and debt cost must fit the currency, date and forecast basis. Do not insert default country premia, tax rates, beta or weights.

Run `python3 scripts/calculate.py --input <capital-cost-input.json> --out <fresh-result.json>`. The input contains `currency`, `monetary_unit`, `risk_free`, `erp`, `beta`, `pre_tax_debt_cost`, `tax_shield_rate`, `equity_market_value`, `debt_market_value`, and `input_bindings` (nonempty artifact/path/hash references). Output rates, weights, intermediate costs, checks, input hash and the helper hash. The result is mechanically checked; an independent economic review still owns assumption acceptance.

Return `capital-cost-result.json` plus the policy/selection record. Feed the rate with its actual acceptance disposition and binding into the cash-flow model. If that model already computes WACC, reconcile both policies before replacing its rate; do not paste an override merely to force numerical agreement. A changed share count, market price, financing balance or beta invalidates this work unit and its downstream calculations, arguments and reviews.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Stable planning clauses

### valuation-wacc-method

Execute the substantive method in this component against current bound inputs. Capabilities: wacc-calculation, capital-cost-policy-check.

### valuation-wacc-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### valuation-wacc-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.


## Portable helper scope

The bundled `scripts/calculate.py` is the only numerical helper in this component.
Bindings use paths relative to the input JSON directory and must remain inside
that directory; absolute, parent-traversing and escaping symlink bindings fail.
Each binding SHA-256 is checked before calculation and carried into the result.
Use a fresh output path; existing versions are never overwritten. Output records
input/helper hashes and `economic_review: pending`; successful arithmetic never
marks independent review complete. The core helper accepts selected beta and
market values; it does not fetch sources, adjust beta, choose policies, produce
a workbook, evaluate regulatory capital or check policy adequacy. Host operation
records must bind the separate policy/perimeter files and their actual review.

For domain-plan output names, read [artifact mapping](references/domain-artifacts.md).
