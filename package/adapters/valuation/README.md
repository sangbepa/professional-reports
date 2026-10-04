# Portable valuation adapter (0.1.0-dev.1)

This adapter is a runnable **conditional calculation and artifact pipeline**. It
is not a professional-quality certification, financial review, legal class-rights
review, market recommendation, or an approved company valuation. The included
fixture is **SYNTHETIC TEST DATA, not Hyundai results**. No live figures are fetched.
It is independent of the parent `pr` engine and writes only to a fresh `--out`.

## Fresh call / replay

From the `professional-reports` root, with Python 3.11+:

```sh
python -m pip install -r adapters/valuation/requirements.txt
python adapters/valuation/build.py \
  --input adapters/valuation/examples/synthetic-stub.json \
  --out adapters/valuation/.validation/my-first-run
```

Use a different empty output directory for each replay. A nonempty directory is
rejected. JSON duplicate keys, unknown fields, missing metadata, invalid dates,
nonfinite values, invalid model domains and unreconciled controls are rejected.
`input.schema.json` is the machine-readable input contract. `_make_schema.py` is
a maintainer utility to regenerate that schema and the fixed synthetic fixture;
it does not invent inputs for an engagement.

Portable minimum: Python plus `openpyxl`. The model and HTML constructor require
only the Python standard library; optional spreadsheet and PDF engines have their
own dependencies. In Codex, the adapter discovers the bundled artifact-tool and
uses it to author, recalculate, export and reopen the workbook. Outside that host,
`--xlsx-engine openpyxl` writes live formulas. It never fabricates formula caches.
Install LibreOffice for independent saved-file recalculation, and Node/Playwright
plus a Chromium browser for native PDF rendering. No network access occurs in a
build and no dependencies are downloaded automatically.

```sh
python adapters/valuation/build.py --input INPUT.json --out NEW_DIRECTORY \
  --xlsx-engine openpyxl --recalc required --pdf required --design transaction
```

Options:

- `--design transaction|executive|editorial`: real native A/B/C constructor.
  Default is `transaction`; no independent design selection is implied.
- `--xlsx-engine auto|artifact|openpyxl`: `auto` chooses available artifact-tool,
  otherwise openpyxl. An attempted engine failure is not silently swallowed.
- `--recalc auto|required|skip`: isolated LibreOffice conversion, then reopen and
  compare every calculation cell against the common model. `required` fails if
  unavailable. A detected but failed calculation fails the run even in auto mode.
- `--pdf auto|required|skip`: actually launch the browser and create probe PDF
  bytes before attempting the native renderer. Auto records unavailable support;
  required returns nonzero. Rendering/layout failures always fail the run.

Environment overrides are optional discovered/configured locations, not paths to
an author's checkout: `VALUATION_NODE`, `VALUATION_ARTIFACT_TOOL` (module file),
`VALUATION_PYTHON`, `VALUATION_SOFFICE`, `REPORT_OUTFIT_NODE`, `REPORT_OUTFIT_PLAYWRIGHT` (package path),
`REPORT_OUTFIT_CHROME` (browser executable). Standard Node package resolution is
used by the PDF tools, with host runtime discovery when available. On macOS the
native renderer defaults to installed Chrome; elsewhere Playwright's Chromium.
Browser launch can be blocked by a sandbox even when packages are installed.
A CLI invoked from a lean parent Python probes the optional bundled Python for
openpyxl and re-executes there if available. No author-specific path is stored;
ordinary installations can use the exactly pinned requirements instead.

To render an already generated native report separately:

```sh
python adapters/valuation/render.py --report NEW_DIRECTORY/report --mode required
```

This writes `render-status.json`; the original build manifest is a frozen record
of the original build, not retroactively upgraded. `render-seal.json` binds native
renderer outputs. Rerun the full build to produce one new consolidated manifest.

## Model contract

All economic inputs, including each annual driver and categorical policy, carry
`value`, `kind` (`evidence`, `assumption`, `synthetic`), source ID/locator/URI/hash,
`as_of`, `unit`, `rationale`, and a declared review status/reviewer/reference.
Evidence requires a source URI and SHA-256; the adapter does **not** fetch or
independently authenticate that source. `reviewed` requires reviewer/reference;
`rejected` is not usable. Synthetic inputs cannot be hidden in a non-synthetic
engagement. Every generated model/report remains `unreviewed_conditional`, even
if individual inputs declare reviewed status.

Identifiers, entity/currency names, schema version and annual period structure
are structural fields. All amount inputs share `currency` and `amount_scale`;
`amount` is the scaled model amount, `currency_per_share` is unscaled price,
`shares` is absolute shares, and `ratio` is a decimal fraction. Mixed units are
rejected. Year-end mode uses December 31 and annual year-end discounting. For arbitrary
within-year cutoffs, explicit-stub mode is mandatory as described below. There is
no inferred stub, FX conversion or midyear convention.

### Industrial DCF

Each segment starts from supplied revenue and opening working-capital ratio.
Every full annual year has independent editable sales growth, EBIT margin, D&A, capex and
working-capital ratios. Change in NWC is a **stock difference**, including changes
in its ratio, not only sales growth. FCFF is NOPAT + D&A - capex - delta NWC.
Taxes use the supplied flat rate, including immediate modeled tax benefits for
losses (no deferred-tax/NOL schedule). WACC is a supplied scoped assumption, not
computed using group finance debt or negative net-debt capital weights.

Terminal NOPAT uses next-year revenue and an explicit normalized margin.
Terminal reinvestment is NOPAT × g/ROIC; FCFF and terminal value follow from that.
Discount must exceed growth throughout the 5×5 sensitivity domain; nonnegative
growth cannot exceed ROIC. Each segment equity is EV + segment cash - segment
nonlease debt - debt-like leases. NCI is that equity times the non-parent fraction,
not NCI book value and not a percentage of EV.

Lease policy is mandatory:

- `operating_expense`: supplied EBIT includes rent and capex/D&A exclude ROU;
  lease liability is disclosed but not deducted again.
- `debt_like`: supplied EBIT excludes lease interest; capex and D&A include the
  corresponding ROU additions/depreciation; lease liability is deducted once.

`lease_basis` must explain the supplied treatment. These declarations do not
prove that the forecast inputs have actually been normalized consistently.

### Finance residual income and P/B

Opening equity + discounted (income - cost of equity × opening book) + terminal
RI gives finance equity. Book rolls through earnings and dividends under clean
surplus. Terminal ROE applies to final forecast closing book; subsequent book
and RI grow at g. The terminal payout implied by g/ROE must be feasible over the
sensitivity domain. P/B × opening book is a separate supplied crosscheck, never
silently averaged into the selected RI value.

Finance funding debt, cash and finance leases are already reflected in book
capital/ROE/payout inputs, as declared in `finance_basis`; funding debt is
reconciled and disclosed, never deducted again in the industrial bridge.
There is no regulatory capital, OCI, issuance, acquisition or capital-adequacy
schedule. Users must reject or extend this model where those are material.

### Consolidation, equity bridge and class rights

Signed historic revenue, EBIT, nonlease-debt, cash and finance-book adjustments
must reconcile to explicit consolidated controls within 1e-7 model amounts.
Historical reconciliation is **not** forecast elimination valuation. The supplied
`industrial_ev_adjustment` and `finance_equity_adjustment` handle explicit,
evidenced parent-attributable valuation adjustments. Nonoperating assets and
parent liabilities are positive balances with explicit opposing bridge signs.
Group adjustments are parent-level and must not duplicate segment balances.
No automatic plug or inferred NCI allocation is made.

Class rights use `pari_passu_fixed_then_weighted_residual`: issued less treasury
shares, fixed claims with equal recovery ranking, then residual equity weighted
by outstanding shares × economic participation weight. Available class equity
is floored at zero; fixed-claim shortfalls recover proportionately. These weights
are economic inputs, not inferred from voting rights or trading discounts.
Seniority ladders, conversion, cumulative dividends, options and redemption
schedules are unsupported. A zero participation weight supports a nonparticipating fixed-claim class; at
least one outstanding class must participate in the residual. Negative segment equity is retained in proportional
NCI and explicitly flagged for loss-sharing review.

Two 5×5 grids perform full formula recalculation of parent equity: industrial
WACC/g shifts and finance cost-of-equity/terminal-ROE shifts. They update NCI and
have exact base centers. These are ordinary portable formulas, not Excel What-If
Data Tables. The reverse diagnostic solves the uniform industrial EBIT-margin
change that matches the supplied total class market capitalization, holding other
drivers fixed. No parent industrial exposure yields an explicit unavailable
result; an arithmetic solution is not a credible operating forecast.

## Common result and artifacts

`model.calculate(data)` returns `(result, graph)` without side effects. One
expression DAG evaluates Python numbers and emits Excel formulas. Reports read
that result, including source-input metadata; charts carry result paths and use
new native SVG geometry. `build.run(input_path, out, ...)` is the callable adapter
entrypoint; `build.py` is the portable CLI. No parent engine imports are required.

Outputs include frozen input, model-result and calculation-graph JSON; editable
`valuation.xlsx`; workbook specification/audits; native report input, HTML,
vendored/copied fonts and assets; numeric retention bindings; optional PDF,
rendered HTML, layout checks, browser screenshots and hashes; and `manifest.json`.
Core JSON results and HTML are deterministic for identical inputs/code. Office
ZIP timestamps and browser PDF metadata are not promised byte-identical.

Edit numeric drivers in **Inputs**. Calculation sheets contain formulas; Evidence
is a provenance snapshot, not a second set of active drivers. Policy changes,
period/class/segment structure changes, source changes and review changes require
editing JSON and a fresh build. Workbook edits do not update the frozen JSON/HTML,
provenance declarations or approval status. Rebuild artifacts from changed JSON
to keep the common result and evidence synchronized.

A plain openpyxl export with no engine available contains uncached formulas.
`calculated_values_verified=false` reports that limit. The workbook audit and
engine records distinguish formula structure, actual recalculation, save/reopen,
value comparison, previews and unperformed financial review. A completed
conditional build is not an approved professional deliverable.

## Validation

```sh
python -m unittest discover -s tests -p test_valuation_adapter.py -v
VALUATION_TEST_NATIVE=1 python -m unittest discover -s tests -p test_valuation_adapter.py -v
```

The suite uses independent fixed-input arithmetic, changes financing debt,
leases, NWC ratios, margins and sensitivity coordinates, tests zero/negative
class recoveries, metadata/schema errors and reconciliation failures, executes
fresh relocated CLI calls (including paths with spaces), checks no overwrite and
all three native HTML profiles, and optionally mutates a saved workbook before a
real LibreOffice recalculate/save/reopen. All fixtures/results are synthetic.
See `VALIDATION.md` for the scope actually executed in this implementation run.

The native renderer, pagination, fonts and font licenses are contained in
`vendor/`. Its file manifest is checked on every build. See `vendor/NOTICE.md`
for origin, exact local changes, branding and license limitations. There are no
references to the original report-outfit checkout at runtime.


## Explicit current-date stub contract

Set `discount_timing.value` to `explicit_stub` for a cutoff inside the first
forecast fiscal year (e.g. 2026-10-03 with `base_year: 2025`). `horizon` counts the
stub plus subsequent full annual periods. Each segment's `forecast` array then
contains `horizon - 1` annual driver sets. The schema requires a `timing` object:

- `time_to_cashflow`: one individually evidenced number of years per period,
  strictly increasing, first between zero and one.
- `terminal_time`: explicitly supplied, equal to the final cash-flow time.
- `finance_stub_charge`: evidenced policy `compound_effective_rate`; required
  equity returns use `(1 + cost_equity) ^ period_length - 1`. No stub earnings or
  dividends are inferred by scaling annual ROE or payout.

Each industrial segment requires `stub` amounts: `revenue`, `ebit`, `cash_tax`,
`da`, `capex`, `delta_nwc`, `opening_nwc`, `closing_nwc`, `fcff`, and
`full_year_revenue_anchor`. FCFF must reconcile to EBIT less supplied cash taxes,
plus D&A, less capex and delta NWC. NWC closing must equal opening plus delta.
The annual revenue anchor is a separate full-year amount for the first full-year
forecast growth calculation; stub revenue is **never annualized**. The first
annual NWC change starts from supplied stub closing NWC.

Each finance segment requires explicit `stub.income` and `stub.dividends`; its
opening `book_equity` must be the valuation-date equity basis. Those roll into
closing book; the declared effective capital charge is deducted to obtain RI.
All cash flows, terminal PV, finance sensitivity and reverse calculations use the
explicit times. The reverse annual-margin diagnostic holds stub FCFF fixed.

`examples/synthetic-stub.json` contains a fully specified **synthetic** current-
date example. Its 0.25 year first time is an explicit fixed test assumption, not
a day-count calculation for October 3. The adapter does not guess ACT/365,
settlement dates, bridge an old balance sheet to today, synthesize current stub
cash flows, or infer intraperiod dividends. Current-date data availability and
source reconciliation remain prerequisites for an actual company report.

Support boundaries: the fiscal calendar remains December year-end; subsequent
full-year periods use annual drivers. Other fiscal calendars, multiple interim
cash-flow dates per year, stub-only terminal valuation, regulatory finance
capital requirements, OCI and complex capital rights require explicit extension.
There must be at least one full annual forecast after the stub.

## Supplied narrative and report composition

Optional `report` lets the main author supply the argument instead of accepting a
fixed calculation ledger as the report. Real/non-synthetic reports default to
`language: "ko"`; `ko` and `en` can be selected explicitly. The calculation
appendix retains supplied entity/input names and standard financial terms.
The adapter supplies no research or expert judgment and never upgrades review.

```json
{
  "report": {
    "language": "ko",
    "report_sections": [
      {
        "id": "argument",
        "title": "조건부 결론과 근거",
        "lead": "승인되지 않은 가정을 포함한 시나리오",
        "blocks": [
          {
            "kind": "argument",
            "text": "{{context:valuation_date}} 기준 지배주주 지분가치는 {{model:bridge.parent_equity|amount}} 모형 단위다.",
            "evidence_ids": []
          },
          {
            "kind": "condition",
            "text": "영구성장률 {{input:industrial.0.terminal_growth|percent}}의 타당성을 별도로 검토해야 한다.",
            "evidence_ids": []
          }
        ]
      }
    ],
    "section_order": ["narrative:argument", "calculated:bridge", "calculated:timing"]
  }
}
```

Block kinds are `argument`, `evidence`, `condition`, `paragraph`. Bodies are plain
text escaped into native blocks, not raw HTML. `evidence_ids` must resolve to
source IDs in the input metadata, and `evidence` blocks require at least one ID.
Qualitative arguments and source truth remain unreviewed author statements.

Quantitative claims must use placeholders, never typed numeric literals:
`{{model:PATH|amount}}` references a key in `model-result.json.values`;
`{{input:PATH|percent}}` references input metadata; and `{{context:KEY}}` permits
company, valuation date, currency, amount scale, horizon and the fixed unreviewed
status. Formats are `amount` (two decimals), `percent` (ratio inputs only),
`integer` (display rounding) and `raw`. Unknown paths/formats and literal numeric
characters are rejected; callers cannot pass replacement values or expressions.
Claims in body blocks have exact result-path bindings that are checked again in
HTML after pagination. Numeric amount claims belong in body blocks, not headings.
This is mechanical binding, not semantic financial review of the author's prose.

`section_order` selects and orders any calculated sections alongside narratives.
All supplied narrative sections must appear exactly once if an order is supplied.
Calculated keys include `conclusion`, `timing`, `industrial-0`, `industrial-1`,
`finance-0`, `bridge`, `consolidation`, `rights`, `sensitivity-industrial`,
`sensitivity-finance`, `reverse`, `chart`, and generated `sources-N` registers.
Indices follow input order; absent finance means no finance section. With no
order, narratives precede the complete appendix. The adapter retains an explicit
model-conditions/review-status section even when calculated sections are omitted.
Review status is not a narrative-controlled field. All three native profile
constructors remain available, with neutral scenario branding and no firm marks.
