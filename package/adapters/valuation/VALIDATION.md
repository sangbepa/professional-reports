# Executed validation scope - 2026-10-03

**Synthetic implementation validation only. Not Hyundai results, a financial
review, a firm opinion or professional-quality approval.** All writes in this
implementation are scoped to `adapters/valuation/` and
`tests/test_valuation_adapter.py`. Parent engine files were not changed.

The single final demonstration is
`.validation/final-synthetic-cross-company/`, built from
`examples/synthetic-stub.json`. It uses an actual 2026-10-03 evaluation date,
explicit synthetic stub amounts and times, Korean supplied arguments/evidence/
conditions, selected calculation sections, and neutral scenario branding. Prior
intermediate attempts remain under ignored `.validation/`; they are not final
examples. Machine-readable evidence and artifact hashes are in
`validation-evidence.json` and the final build's `manifest.json`.

Executed command (from the project root):

```sh
python3 adapters/valuation/build.py \
  --input adapters/valuation/examples/synthetic-stub.json \
  --out adapters/valuation/.validation/final-synthetic-cross-company \
  --recalc required --pdf required
```

The initiating Python lacked openpyxl. The CLI capability-probed the bundled
Python, then executed there. Artifact-tool and LibreOffice were discovered from
host runtime/package capabilities; no author checkout path is needed in release
code. `openpyxl==3.1.5` is pinned for ordinary portable installations.

## Observed checks

- **26 tests passed**, including the actual native-engine integration flag.
  Year-end fixed-input DCF/RI/PB/class-rights arithmetic, finance debt exclusion,
  lease treatment, NCI equity basis, NWC stock changes, reconciliations,
  sensitivities, reverse repricing, invalid inputs and zero/negative recoveries.
- Current-date stub tests include an independent industrial DCF and finance
  dividend-discount identity, explicit-time perturbation, missing/inconsistent
  stub rejection, sensitivity repricing and reverse diagnostics holding stubs
  fixed. No annual cash flows were prorated into a stub.
- Narrative tests cover ordered section selection, Korean default for real
  reports, model/input numeric bindings, unbound literal-number rejection,
  missing references, unchanged unreviewed status and HTML escaping.
- Fresh relocated CLI replay in a path with spaces generated all three native
  HTML profiles. Repeated model/graph/report-input/HTML bytes matched. Nonempty
  output directories were rejected. No original renderer checkout was needed.
- The final workbook was authored, recalculated, saved and reopened through
  **artifact-tool 2.8.84**, then independently recalculated/saved/reopened through
  **LibreOfficeDev 26.8.0.0.alpha0**. All **246 calculation cells** matched the
  Python graph; no formula errors, lost formulas, missing caches or value
  differences were found. The integration test also changed a later-year margin
  inside an existing workbook and verified the recalculated downstream values;
  it separately recalculated the explicit-stub workbook.
- **232 numeric bindings** and all plotted values matched before and after native
  pagination. Binding verification is a retention check, not source verification.
- The neutral native report rendered to **21 PDF pages** using Chrome
  **154.0.8037.97** via Playwright. The helper first launched a browser and
  generated real probe PDF bytes. All native layout checks passed; mobile body
  width was within its viewport. No firm wordmarks remained in the final HTML,
  assets or extracted PDF text.
- All 21 actual PDF page rasters were inspected through contact sheets. The final
  page rasters were byte-identical to the inspected report revision. Workbook
  visual inspection covered columns A:C in the first 22 rows of all nine sheets,
  with the revised Evidence wrapping separately inspected. This was an author
  inspection, not an independent design review or every-cell visual audit.

Chrome could not launch in the restrictive sandbox at first. The support probe
reported unavailable rather than claiming PDF success. The final run used
approved local browser access and recorded successful actual rendering. The
adapter itself does not assume that an installed browser can execute.

## Remaining support / review boundaries

- No actual Hyundai data, current financial reconstruction, source authentication,
  professional financial-methodology review, or legal verification of class
  rights was performed. Numeric tests do not establish those facts.
- Explicit-stub mode supports within-year valuation dates for a December fiscal
  calendar, with at least one full annual period after the stub. The caller must
  supply stub FCFF components, finance income/dividends, valuation-date balance
  inputs, revenue/NWC anchors and explicit discount times. There is no automatic
  balance-sheet roll-forward, annual-to-stub conversion or day-count inference.
- Other fiscal calendars, multiple intrayear cash-flow dates, finance regulatory
  capital/OCI/issuance schedules, complex priority/convertible rights, tax-loss
  carryforwards and multiple-currency conversion are not modeled.
- Workbook numeric inputs are editable; changing structural/policy assumptions
  or producing a synchronized report requires a new JSON-driven build. Workbook
  edits do not update frozen report evidence or create an approval.
- Calculated appendix content retains standard English financial terms and
  supplied labels alongside Korean headings. The main author supplies the Korean
  expert narrative and decides the composition; the adapter is not an automatic
  financial report writer or reviewer.
- Native Microsoft Excel was not executed. Native What-If Data Tables were not
  used; both sensitivity grids contain ordinary recalculating formulas.
- Independent design selection, source review and financial review remain
  `not_performed`; professional quality remains `not_assessed`.
