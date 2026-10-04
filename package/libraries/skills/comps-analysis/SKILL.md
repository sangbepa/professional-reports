---
name: comps-analysis
description: Construct economically comparable peer evidence and reproducible multiples without automatic method averaging or zero-filled missing data.
---

# Comparable companies with explicit comparability

Modified adaptation of Anthropic financial-services `comps-analysis`. Read
`NOTICE`, `provenance.json`, [method contract](contract.json) and
[execution boundary](references/execution-contract.md). This supplies methods;
market data access and native spreadsheet execution are unresolved until tested.

## Select the question and population

Start from the economic unit, interest valued, date, currency, forecast/actual
basis and role of market evidence: primary indication, calibration or cross-check.
Select peers by products, customer exposure, geography, growth, margins, capital
intensity, cyclicality and regulation. Record the search population, inclusion
rationale, exclusions and imperfect matches. A few selectively favorable names
are not a defensible universe; do not impose a fixed peer count or metric quota.

Choose measures that answer the decision. Preserve losses and incompatible
companies visibly while excluding undefined multiples from relevant statistics.
Negative EBITDA does not by itself justify switching to revenue multiples; that
choice needs evidence on margins, capital needs and comparability. Financial
firms may require equity and capital measures rather than industrial EV multiples.

## Gather, align and calculate

Freeze original filings and dated market observations. Each raw value records
source, locator, publication/availability date, measurement date, period, unit,
currency, consolidation basis and reported/adjusted classification. Record the
price session/time and point-in-time issued/diluted rights; consensus must have a
dated provider snapshot. Current data cannot silently support a historic cutoff.

Reconcile LTM = latest full year + current interim - comparable prior interim
only for matching durations, definitions and scope. Keep NTM forecasts separate;
calendarization is an explicit, supported transformation. Align fiscal years, FX,
leases, stock compensation, acquisitions and one-offs through visible bridges.
No balancing plugs or convenient silent selection between conflicting sources.

Build market equity from actual economic classes. Enterprise value adds financing
claims and NCI where the earnings denominator includes them, and removes eligible
nonoperating cash/assets consistently. Record NCI, lease, associate, consolidation
and share-rights treatment per peer. Neither all cash nor all debt is necessarily
nonoperating. EV/revenue and EV/EBITDA use whole-enterprise denominators; P/E uses
earnings attributable to the same equity claim. Equity FCF yield and enterprise
cash yield require different denominators.

Write derived ratios as formulas with input links when creating a workbook. Show
zero/negative/absent denominators as undefined or not meaningful with a reason.
Never use `IFERROR(...,0)` to include missing multiples as zero observations.
Calculate sample counts, median and other useful distribution statistics on the
explicit eligible population. Identify percentile convention and limited small-
sample interpretability. A weighted aggregate margin and a median company margin
answer different questions; name the measure. Do not compare raw per-share EPS
across unrelated share denominations as an operating-efficiency statistic.

## Interpret and challenge

Explain observed dispersion using growth, profitability, risk, capital intensity,
accounting and exposure; a quartile is not automatically a justified valuation
multiple. Keep outliers visible, test exclusions and state whether the result
survives reasonable alternative peer selections. No universal multiple bands or
unconditional ordering of gross, EBITDA and net margins serves as acceptance.

Apply a selected multiple only to the compatible target metric and ownership
basis. Bind the method result to the target's single claims bridge; describe
shared forecasts/bridge items when comparing to DCF or SOTP. Do not average
incompatible indications. Document material divergence and the test needed to
resolve it; no data or no comparable population may mean no defensible comps
indication.

## Deliver and restrict

Return peer inclusion/exclusion, raw and aligned metrics, formula/value bindings,
EV/equity bridges, eligible-population statistics, selected interpretation and
limitations. If producing a workbook, preserve sources, editable assumptions,
units and readable layout; test actual recalculation and rendering separately.
Missing tools yield an explicit method/data packet, not a falsely finished XLSX.
Return inconsistent bases to `report-data-reconcile`, unsupported peer/multiple
selection to `valuation-design`, and unavailable originals to research. Arithmetic
checks never establish economic comparability or independent approval.

## Stable planning clauses

### comps-analysis-method

Execute the substantive method in this component against current bound inputs. Capabilities: comparable-company-analysis, peer-selection, multiple-reconciliation.

### comps-analysis-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### comps-analysis-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.


For domain-plan output names, read [artifact mapping](references/domain-artifacts.md).
