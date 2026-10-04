---
name: audit-xls
description: Inspect spreadsheet formulas and financial-model integrity with explicit scope, recalculation limits and artifact-bound findings.
---

# Audit formulas and financial-model integrity

Modified adaptation of Anthropic financial-services `audit-xls`. Read `NOTICE`,
`provenance.json`, [method contract](contract.json) and
[execution boundary](references/execution-contract.md). This is an audit method;
it includes no native spreadsheet execution or rendering engine.

## Scope and evidence

Use the requested range, sheet or whole-model scope. If context clearly requests
an integrated-model audit, cover the workbook and its relevant dependencies;
otherwise record a bounded chosen scope or return material ambiguity. Do not add
routine approval gates. Bind the original workbook hash, requested criteria,
materiality/tolerances, source/model inputs and actual available tools. Inventory
visible/hidden sheets and rows, named ranges, external links, formulas, caches,
macros, data tables, dynamic arrays and iterative calculations within the scope.

Record four separate states: structural inspection, independently recomputed
arithmetic, native recalculation and rendered visual inspection. Each has tested
coverage, actual tool/version when known, current artifact hash and limitations.
Opening a file, counting formulas or finding no cached errors establishes neither
native recalculation nor economic correctness. Library `data_only` reads can be
stale or absent. Missing macros, credentials, external files or unsupported
functions remain unverified even if the visible workbook opens.

## Formula and dependency inspection

Trace material outputs backwards to drivers. Check #REF!, #VALUE!, #N/A, #DIV/0!,
#NAME?, #NUM! and spills where the tool exposes them; missing cached errors are
not evidence of no errors. Detect off-by-one sums, shifts in relative/absolute
references, formula-pattern breaks, overwritten formulas, hidden overrides,
embedded unexplained constants, circularity and broken names/cross-sheet links.
Trace units, sign, scale, dates and annual/interim distinctions through formulas.
A flagged constant or different formula may be intentional: record evidence,
quantified consequence and disposition rather than automatic defect labels.

## Financial integrity for a model audit

* Reconcile assets = liabilities + equity each period; explain the difference and
  earliest break. Test retained earnings with dividends and other actual equity
  movements, not an incomplete rollforward assumed universal.
* Tie ending cash between cash flow and balance sheet including FX/scope effects;
  trace operating, investing and financing changes. Reconcile PP&E with capex,
  depreciation, acquisitions, disposals, impairment and FX as applicable.
* Tie revenues to segments after eliminations, tax expense/cash to tax schedules,
  working-capital signs to underlying balances, debt to funding/maturities,
  interest to average balance/timing and share counts to actual rights/dilution.
* For DCF inspect FCFF/FCFE consistency, discount timing, terminal cash flow and
  reinvestment, WACC market weights, tax shield duplication and the single
  enterprise-to-equity bridge. Positive formula agreement is not economic review.
* For LBO inspect cash sweeps, minimum cash, revolver/PIK, fees, entry funding,
  management rollover and exit proceeds. For merger inspect sources/uses,
  purchase accounting, financing/foregone interest, synergies, fees and post-deal
  dilution. For comps inspect date/denominator alignment and exclusion handling.

Test meaningful edge cases selected for this model, preserving the original and
restoring the selected case in an authorized working copy. Zero growth, losses,
negative working capital or reduced leverage are valid in some businesses, not
automatic failures. Invalidate impossible terminal combinations explicitly.
Reasonableness flags use supported sector/mandate context, not universal growth,
margin or terminal-share thresholds. Intentionally iterative models require
actual observed convergence/settings; do not claim it from a checkbox.

## Findings, repair and acceptance

Return findings with issue ID, sheet/cell/range, formula/dependency, expected versus
observed result, discrepancy/consequence, severity, source locator, fix proposal
and verification state. Distinguish material output errors, risks requiring
explanation and presentation issues. Record checked and unchecked populations;
reserve `clean within tested scope` for a complete stated scope, never an
unqualified clean model when material coverage remains unavailable.

Audit-only work reports findings. When repairs are already authorized, make a
versioned copy, preserve originals, repair the cause and recheck affected outputs;
do not ask again solely because the upstream skill prescribed confirmation.
Separate author self-check from a genuine independent reviewer and keep actual
closure tied to revised hashes. Missing native recalculation/render capability
must remain explicit; no repaired or reviewed workbook is production-verified
merely through this package.

## Stable planning clauses

### audit-xls-method

Execute the substantive method in this component against current bound inputs. Capabilities: spreadsheet-audit, formula-inspection, financial-model-integrity, recalculation-evidence-assessment.

### audit-xls-acceptance

Apply the inputs, outputs and acceptance tests in contract.json; record completed checks and limitations separately.

### audit-xls-failure

Return failed or missing prerequisites to the named upstream owner; restrict dependent conclusions and invalidate stale descendants.

