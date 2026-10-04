# Native full-report input contract

## Content and generator boundaries

The native `build.py` accepts `--mode report --template <supported-key> --input <currentinput.json> --design transaction|executive|editorial --out <freshdir>`. The input `key` must match the supported template key. The current valuation adapter emits `schema_version: 2`, native overview fields, `report_sections`, `retention` and `provenance`.

Inspect the installed `build.py` validation and adapter before authoring input. Native overview fields include `title`, `scope`, `status`, `conclusion`, `headers`, `rows`, `findings`, `needs`, `hero`, `chart` and `sources`, with optional fields such as `subtitle`, `audience`, `kpis`, `formula` and `design_boundary`. The existing overview constructor requires three genuine analysis notes and three genuine evidence requests. Select those highlights from supplied analysis without inventing filler; the full analysis remains unrestricted in `report_sections`. Table row lengths must match headers and chart series must match categories with finite values.

Domain authors select methods, findings, structure and assumptions. The renderer consumes those decisions; it does not supply a DCF, FDD procedure or ESG analysis. Keep current entity, period, information cutoff, units, audience and review status consistent across overview and full body. An approved design never upgrades an unreviewed or conditional financial conclusion.

## Generic report_sections blocks

Each full section has a stable `id`, `title`, `lead` and `blocks` array. The current generic block kinds are:

Tables and charts may carry `caption_html`. The constructor places it inside the exhibit group, so its units and period stay with the corresponding table or plot through pagination. Rebuild an original chart at its semantic source position; do not prepend every chart and strand its original caption elsewhere.

| `kind` | Supplied content | Native presentation |
| --- | --- | --- |
| `table` | `headers`, `rows`; rich cells may contain `text` and `html` | Native table constructor with preserved row/cell content |
| `paragraph` | `html` | Paragraph |
| `finding` | `html` | Finding/blockquote |
| `metrics` | `items` with `value` and `label` | Native metric strip |
| `hero` | `html` | Prominent retained value/content |
| `source-note` | `html` | Source/evidence note |
| `chart` | `chart` definition | Newly generated native chart SVG |
| `text` | `html` | Other supplied textual content |

Keep actual evidence links, qualifications and numeric bindings within these blocks. Preserve content meaning while removing the former page/CSS composition. Inspect mapper output for unsupported markup or retained decorative/chart assets; do not silently lose substantive content because a source node was unrecognized. Full-report pagination may split blocks/table rows and repeat headings with continuation labels. It must not clip, hide or discard content to reach eight/four pages.

Generic blocks are a content/presentation interface, not proof that every domain adapter exists. `fdd` is an actual native template key and can receive supplied domain-authored content. Generic reports generate supplied overview, findings, requests and source locators as native pages; their footer uses the supplied status. Set `overview_mode: integrated` only when the complete section content already incorporates the overview. Reviewed retention inputs default to integrated mode; other inputs default to generated mode. Optional `report_footer` and `comparison_href` must reflect the current document; a standalone generated report omits the comparison link unless explicitly supplied. The concrete valuation adapter remains Samsung-specific. `esg` is not currently in native `TEMPLATES`: do not advertise or invoke `--template esg`, or claim ESG analysis.

When both `retention` and `provenance` are absent, `verify_report.py` performs presentation-only checks against supplied section content, overview, chart values, PDF and seals. Its financial source/model verification is explicitly `not performed`. With reviewed provenance and retention it checks original/model hashes and recorded chart result paths. Do not confuse these scopes or add fictional source/model fields to make a generic fixture pass.

## Original reviewed source and current results

For the matching Samsung valuation case, `prepare_report.py --source <ORIGINAL-reviewed-HTML> --results <corresponding-results-JSON> --out <input>` parses sections and binds model results. It is an optional concrete adapter with specific markup (`section.page`, `pagebody`, headings/leads and metric attributes) and result structure (`cases.base`, related scenarios/rows). Its source must be the original reviewed valuation HTML, not an old redesigned output. Keep financial content only; native art/pages/tables/charts provide the new presentation.

The current adapter has Samsung-specific cover/summary language, dates, units and analytical notes. Do not silently apply it to another issuer, another cutoff or FDD/ESG content. Supply a new current native input or route mapper work to its authorized owner. Never fall back to bundled `inputs/valuation.json` or an earlier Samsung fixture when input is missing. A missing mapping is a disclosed capability gap, not permission to reuse irrelevant content.

Use actual source/model SHA-256 values and provenance paths. The adapter's `provenance` records `source_report`, `source_report_sha256`, `model_results`, `model_results_sha256` and `previous_design_retained: false`. Record the supplied domain-review basis in the engagement/review sidecar; do not fabricate financial approval fields inside the native schema. Verify these bytes and current review coverage before generation.

## Retention and regenerated charts

The adapter's `retention` records metric triples in `metrics` and normalized paragraph/table-cell multiplicity counters in `paragraphs` and `table_cells`. Compare lists/counters as actually emitted, not only distinct-key counts. The integration's supplied current Samsung baseline is **389 metric bindings, 43 paragraphs and 598 table cells**. Confirm those counts against the actual current input/source; they are not universal thresholds or a claim that this instruction-only work ran the mapper. Different reports need their own complete baseline.

New chart definitions contain `title`, `unit`, `categories`, `series`, `note` and where relevant `type`. Series contain a name, numerical values and `result_paths`. Bind each plotted value to the matching reviewed result location, documenting any supported scale transformation such as `cases.base.common_value/10000`. Units and labels must reflect that transformation. Keep half-year versus annual periods, scenario ranges versus probabilities, and allocated contribution diagnostics versus standalone business values distinguishable.

Generate charts with the native chart function during the new build; do not carry old SVGs, chart screenshots or prior chart geometry into the report. Inspect the actual generated attributes/labels and result-value correspondence, not merely a visually similar drawing. This regeneration consumes reviewed numbers and must not recalculate WACC, alter share count or introduce a financial judgment.

Freeze one current input for all three full native reports. Verify original metric binding identities/values, paragraph and table-cell content/multiplicity, complete section coverage, units, sources and every generated overview claim. Repeated table headings/continuations may add presentation text; distinguish those additions from missing source content. Retention and layout checks establish preservation within their inspected scope, not source truth or valuation economics. Changed content/results require new input versions, regenerated candidates and current domain/document review coverage.
