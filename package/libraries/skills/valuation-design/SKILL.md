---
name: valuation-design
description: Select defensible valuation methods, design operating scenarios, reconcile enterprise-to-equity adjustments and explain differences between valuation indications.
---

# Valuation design

Select methods for the mandate and economic unit. Record reasons for inclusion/exclusion, cross-checks and source constraints. Make useful work units rather than forcing all businesses into one DCF template.

Consume the valuation evidence packet from `financial-report-research` ([entrypoint](../financial-report-research/SKILL.md)). For each dominant selected assumption retain observations, calibration, credible alternatives, selection rationale, model path and decision consequence. A source about industry prospects is not numerical calibration. A bounded reasoned judgment is legitimate; an uncalibrated scenario cannot be promoted to the selected valuation solely by naming it “base”. Return material research gaps to the orchestrator.

For cyclical firms separate current price/mix, volume/capacity, costs, working capital and reinvestment from maintainable economics. Determine a transition period to a supportable terminal state. Explicitly identify judgment assumptions and credible alternatives. Do not turn management's qualitative outlook into an attributed numerical forecast.

Align FCFF/FCFE, nominal/real currency, tax, inflation, capital structure, discount timing, terminal growth and reinvestment returns. For a net-cash company keep debt weights nonnegative; assess whether equity beta includes significant nonoperating assets. When selected on economic grounds, use `dcf-model` or `comps-analysis` for the relevant calculation; neither method nor their combination is mandatory. Other justified methods require a supplied capable implementation or an explicit unresolved capability return.

Use segment SOTP only where business scope, costs, elimination and capital allocation can be explained. Allocation estimates are conditional and sensitivity-tested. Reconcile the SOTP to the consolidated build. Avoid separately capitalizing a revenue elimination that already has zero consolidated profit.

Build the equity bridge once: excess cash, debt/leases, nonoperating holdings, associate earnings, tax, pension, NCI, shares, awards, dividends and buybacks. Match cash and denominator effects of repurchases. Weighted-average EPS shares are not point-in-time awards. Preserve different share-class economic rights; separately discuss market discounts.

Comps must match economic exposure, metric/calendar basis, currency and valuation date. Explain outliers and exclusions; do not average incompatible methods automatically. Reverse DCF is a market-implied diagnostic, not independent corroboration. Reconcile discrepancies before reporting a value range.

For material method divergence, test the economic explanations and specify what the evidence supports for the adopted conclusion. Identify shared forecast/bridge components and correlated source inputs. Neither describing the difference nor stating “cyclicality” alone resolves the choice between competing valuation indications.

Return model inputs/parameters, bridge schedules, method reconciliation and the decisions affecting the conclusion. Follow the local method contract and execution boundary.

## Portable package contract

Read [execution boundary](references/execution-contract.md) and [method contract](contract.json).
This adapted package overrides upstream tool and approval assumptions as specified there.

## Ownership, consolidation and claims policy record

Return `ownership_policy` with named fields `consolidation_policy`, `nci_policy`,
`lease_policy` and `share_rights_policy`, each recording chosen treatment,
source/judgment bindings, rationale, alternatives, affected model paths and
remaining uncertainty. These are substantive methods declared as capabilities;
the host still declares its required capabilities on each plan node.

* Consolidation: identify fully consolidated, equity-accounted and proportionate
  units. Reconcile segments plus central costs, intercompany revenues/profits and
  eliminations to group results; carry residuals explicitly. Explain shared asset,
  capex, tax and funding allocation. Do not separately value an elimination that
  has already removed the related profit or associate contribution.
* NCI: match the valued profit/cash-flow perimeter to ownership. A 100% subsidiary
  enterprise build needs the corresponding minority claim addressed once; a
  proportionate build must not subtract the same NCI again. Carry valuation versus
  book-value limitations and financial-subsidiary funding separately.
* Leases: choose a coherent operating-expense or financing treatment. Align
  EBIT/EBITDA, D&A, capex, cash flows, debt weights, terminal replacement burden and
  EV-to-equity deductions. No universal add-back or automatic liability deduction.
* Share rights: identify issued, treasury, option, award, convertible and preferred
  classes at the valuation date. Preserve dividend, conversion and liquidation
  rights; choose dilution/cash proceeds consistently. Weighted-average EPS shares
  and authorized future buybacks do not establish current economic ownership.

Return `segment_reconciliation` with units, ownership, periods, eliminations,
central allocations, consolidated control totals and residuals. Unsupported
allocation is a disclosed scenario with consequences, not an observed fact.

## Alternative units and method assessments

Required assessment never requires method adoption. For regulated financial units,
classify the business and map distributable capital before selecting direct FCFE,
DDM or residual income; the `financial-equity-valuation` method supplies the
substantive calculation contract when selected. Do not use industrial FCFF for
balance-sheet financial intermediation.

For asset/NAV approaches, test separability, realizability, embedded claims, tax,
selling costs and ownership; book value is not a default fair value. Distress work
compares evidenced going-concern, restructuring and liquidation paths with claim
ranking, recovery costs and timing; unsupported perpetual terminal value is not
available. Early-stage work uses sourced milestones, funding/dilution and scenario
conditions; unsupported survival/exit probabilities remain unknown. If needed
calculation tools are unavailable, return an assessment and capability gap rather
than label a numeric model complete.

SOTP requires distinct unit economics plus reconciled central costs, assets,
intercompany flows, tax and ownership. Reverse DCF solves a specified implied
driver using a dated market value and disclosed constraints; record nonunique
solutions and shared inputs. It is a diagnostic, never independent evidence of
the market's actual forecast. Method divergence requires a discriminating economic
test and conclusion impact rather than an automatic weighted average.

## Stable planning clauses

### valuation-design-method

Execute the substantive method in this component against current bound inputs. Capabilities: valuation-method-selection, scenario-design, segment-reconciliation, nci-policy, consolidation-policy, lease-policy, share-rights-policy, equity-bridge-design, method-reconciliation, financial-equity-assessment, asset-nav-assessment, distress-assessment, early-stage-assessment, sotp-assessment, assumption-calibration, cycle-normalization, associate-attribution, financial-debt-perimeter, intercompany-elimination, dilution-analysis, reverse-dcf-assessment.

### valuation-design-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### valuation-design-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.


For domain-plan output names, read [artifact mapping](references/domain-artifacts.md).
