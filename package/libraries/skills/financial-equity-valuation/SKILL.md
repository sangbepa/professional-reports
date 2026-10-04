---
name: financial-equity-valuation
description: Value financial businesses through equity cash flows, sustainable distributions or residual income with capital and ownership reconciliations.
---

# Financial business equity methods

Adapted from the valuation research industry lens, valuation-design and the
current domain's financial-unit method policy. Read [method contract](contract.json)
and [execution boundary](references/execution-contract.md). These are agent
calculation/assessment methods, not a bundled banking model, source connector or
verified spreadsheet runtime. Use only current sourced inputs and documented
method selection; return unavailable implementation when the host cannot execute
and verify the required calculation.

## Classify and map capital

Separate balance-sheet financial intermediation from fee-based services. Identify
regulated entities, ownership, funding obligations, guarantees, parent recourse
and intercompany financing. Deposits, policyholder obligations and funding debt
already reflected in financial equity value are not a second industrial net-debt
deduction. Segregate financial, industrial and holding-company claims.

Map applicable prudential constraints to the current entity, jurisdiction and
cutoff with primary evidence. Reconcile accounting equity, regulatory capital,
required buffers, deductions, risk-weighted/exposure bases, and legal restrictions
on distributions. Do not assume all regulatory capital is distributable, add it
as excess cash, or deduct the same buffer twice. A public accounting balance is
not proof of supervisory distributability. Unknown applicable capital constraints
restrict the conclusion and return to research.

## Select and implement a coherent equity method

For direct equity cash flow, project earnings, credit losses/claims, funding costs,
operating expenses and required capital growth together. In a compatible build,
distributable equity cash flow is earnings minus incremental required equity
capital and other evidenced equity cash requirements, with explicit treatment of
new issuance and exceptional releases. Reconcile beginning capital + retained
earnings + issuance + other capital movements - distributions = ending capital.
Discount the selected equity claim at a currency/risk-consistent cost of equity;
industrial WACC and an industrial enterprise-to-equity bridge do not fit this
balance-sheet financial unit.

Use dividend discount only if distribution policy, sustainable payout and capital
constraints are supported. V0 = sum(distribution_t/(1+ke)^t) + discounted terminal
equity value, under documented payment timing. If a steady perpetuity is justified,
TV_T = distribution_(T+1)/(ke-g), with ke>g and capital sufficient for the implied
growth. Historical dividends alone are not evidence of sustainable payout.

Use residual income only with reliable opening equity and reconciled clean-surplus
accounting. RI_t = earnings attributable to the selected common-equity claim -
ke * opening common book equity_t. V0 = current common book equity + sum discounted
RI_t + discounted continuing residual income under a supported transition.
Reconcile OCI, buybacks, new shares, acquisitions and other dirty-surplus movements
explicitly; do not force a clean-surplus identity by dropping them. Define tangible
versus total equity and goodwill consistently. Per-share values require the same
common-equity claim and rights-aware point-in-time denominator.

An equity peer indication needs comparable profitability, capital adequacy, asset
quality, accounting, duration, regulation and growth. Price/book without these
controls is only a market observation. Read `comps-analysis` when the host selects
that method; it is optional. Compare methods by drivers and shared dependencies,
without automatic averaging or declaring correlated models independent evidence.

## Challenge and hand off

Test coherent credit/claims, rate, liquidity and capital stress paths, recognizing
how distribution constraints bind. Do not fabricate default/survival probabilities
or offset an unsupported earnings forecast through a discount-rate premium.
Return method inclusion/exclusion, capital reconciliation, assumptions/calibration,
equity results and alternative consequences, ownership allocation and unresolved
limits. For a subsidiary valued at full equity, allocate parent/NCI once; for an
already attributable result do not deduct minority claims again. Group SOTP must
reconcile this value and related parent obligations to the consolidated perimeter.

Check source/cutoff eligibility, capital rollforward, distribution limits, discount
timing, continuing economics and ownership allocation with recorded tolerances.
A formula pass does not establish regulatory applicability or maintainable returns.
Current independent challenge and any native workbook recalculation remain separate
observable work. Return disputed methods to `valuation-design`, measurement gaps
to `report-data-reconcile` and unavailable source support to research.

## Stable planning clauses

### financial-equity-valuation-method

Execute the substantive method in this component against current bound inputs. Capabilities: financial-equity-valuation, financial-business-classification, regulatory-capital-assessment, dividend-discount-assessment, residual-income-assessment, financial-debt-perimeter.

### financial-equity-valuation-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### financial-equity-valuation-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.


For domain-plan output names, read [artifact mapping](references/domain-artifacts.md).
