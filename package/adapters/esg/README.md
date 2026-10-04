# ESG learning report adapter (development)

This standalone adapter builds 20–30 **explicitly authored** A4 pages. It does
not generate company facts, fill a report with repeated pages, advance the core
production engagement, or perform independent review. Each result records
`independent_review: "not_performed"`. Source checking is structural provenance
checking; it cannot establish that a quotation or interpretation faithfully
represents a source. The parent author/reviewer owns that assessment.

## Install and run

From `professional-reports`, using Python 3.10+ and Node 20+:

```sh
python3 -m venv /tmp/esg-learning-venv
/tmp/esg-learning-venv/bin/python -m pip install -r adapters/esg/requirements.txt
cd adapters/esg
npm ci
npx playwright install chromium
cd ../..
/tmp/esg-learning-venv/bin/python -m pr.esg prepare --input /absolute/request.json --out /absolute/delivery
/tmp/esg-learning-venv/bin/python -m pr.esg build --input /absolute/request.json --out /absolute/delivery
/tmp/esg-learning-venv/bin/python -m pr.esg check --input /absolute/request.json --out /absolute/delivery
```

Exact dependency pins: pypdf 6.19.0 and Playwright 1.62.1, including the npm
lockfile. No data acquisition, charting, or templating dependency is required.
`npm ci --offline --ignore-scripts --no-audit --no-fund` also works if the pinned
packages are already in npm's cache. Chromium is a separate browser installation.

The renderer searches the adapter-local Playwright, `NODE_PATH`, then the Codex
bundled runtime in `~/.cache/codex-runtimes/codex-primary-runtime/dependencies`.
Override Node with `--node` or `ESG_NODE`, Playwright with
`--playwright-module` or `ESG_PLAYWRIGHT_MODULE`, and the browser with
`--chromium` or `ESG_CHROMIUM_EXECUTABLE` (an existing Chromium/Chrome executable).
Network requests are blocked during rendering. The local OFL-licensed
NanumGothic font is copied into each delivery for portable Korean text.

Until a browser is available:

```sh
python3 -m pr.esg build --input /absolute/request.json --out /absolute/delivery --html-only
python3 -m pr.esg check --input /absolute/request.json --out /absolute/delivery --html-only
```

HTML-only checks record `pdf_success: false`; ordinary `check` fails on them.
`prepare` is also never a successful PDF build. Failed renders invalidate the
previous success manifest and leave diagnostic geometry/screenshots when available.

## Input contract: esg-learning-report/1

Use `schema: "esg-learning-report/1"` (`contract` is accepted as an alias).
Unknown fields are rejected. Required top-level fields:

| Field | Shape |
| --- | --- |
| company, title, reporting_period, information_cutoff | nonblank strings |
| status | exactly `"비공식 학습용"` |
| framework | `{basis: string, qualification: string}`; displayed on every page |
| sources | `[{id,title,url,path,sha256,pages}]` |
| metrics | `[{id,label,unit,boundary,method,values,footnotes}]` |
| claims | `[{id,text,source_id,page}]` |
| pages | `[{id,title,kicker,lead,blocks}]`, 20–30 pages |

IDs are unique within their collection and use ASCII letters, numbers, `_`, or
`-` (1–80 characters). All page titles, kickers, leads, and blocks must be
nonblank. Page order is authored array order; no automatic padding or truncation.
Titles and leads are supplied editorial text; factual introductory statements
must use page `claim_ids`, while purely methodological introductions
can use `classification:"analysis", non_company_assertion:true` on the page.

Sources are **local PDFs**, with an original HTTP(S) URL, lowercase SHA-256 and
positive integer `pages` equal to the actual physical PDF count. Paths resolve
relative to the input JSON's parent; absolute paths, `..`, backslashes, and
symlinks escaping that parent are rejected. Copy originals under that parent
before authoring. `page` always means a one-based physical PDF page, including
covers, rather than a page number printed in the document. Encrypted PDFs are
unsupported. Sources are copied to `sources/{id}.pdf` and rechecked against hashes.

Metric `values` use `[{year: integer, value: number|null, source_id, page}]`.
Each finite numeric value, **including zero**, requires `source_id` plus `page`.
Boolean/string/nonfinite numbers are rejected. A null can omit both citation
fields; if either is supplied, both must be valid. Null means unavailable and is
rendered as `자료 없음 (null)`; it is never replaced by zero or connected across
in a line chart. Years must be unique within a metric. `footnotes` is a string
array for boundary/method qualifications; company assertions belong in claims.
Every declared metric and claim must be used in an authored page, preventing
orphan claimed values and unrendered evidence.

Blocks use the `kind` field:

| Kind | Required fields |
| --- | --- |
| paragraph, finding (company assertion) | `text, claim_ids:[claim_id,...]` |
| paragraph, finding (method commentary) | `text, classification:"analysis", non_company_assertion:true` |
| metrics | `ids:[metric_id,...]` |
| chart | `metric_ids:[metric_id,...], caption` |
| table | `headers:[string,...], rows:[[string,...]], source_refs:[{source_id,page},...]`; optional `metric_ids` |
| source | `refs:[{source_id,page},...]` |

`analysis` is an explicit author attestation that the text contains methodological
commentary and **no company assertion**. It cannot include claim IDs or name the
company. The validator checks this classification and obvious misuse, not semantic
truth. A paragraph/finding without that classification requires nonempty claim IDs;
the claim ID and its exact PDF citation are displayed compactly; the full claim
text remains auditable in `input.json`. Tables
use primitive source refs; their cells remain author-controlled source transcriptions.
Optional table `metric_ids` explicitly bind metrics rendered as compact aggregate
rows instead of separate metric panels. All source/page pairs of those metrics
must be covered by the table's source refs. The author must faithfully transcribe
the values; the adapter does not silently infer metric usage from matching numbers.
All collections of references and metric/claim IDs in blocks are nonempty.
Charts render separate panels for each metric, with a title, unit, year axis,
value labels, boundary, method, caption and source links. They never normalize
different metrics to create an invented intensity comparison.
Multiple IDs in one `metrics` block render one compact comparison table: 지표,
단위, and the sorted union of authored years. Every numeric cell has a visible
source ID and physical-page link; null or absent years remain unavailable. Each
metric's boundary, method and footnotes appear compactly below. A single ID
retains the vertical year/value/source table.

## Editable outputs and verification

`prepare` copies source PDFs/font assets and writes editable `input.json` and
`report.md`. JSON is the authoritative build input. Markdown is an editable
companion, not a second parser: synchronize edits into JSON before rebuilding.
To revise the frozen copy in place:

```sh
python3 -m pr.esg build --input /absolute/delivery/input.json --out /absolute/delivery
python3 -m pr.esg check --input /absolute/delivery/input.json --out /absolute/delivery
```

Always `check` using the same input path/content used for the latest build. A
whitespace-only input mutation invalidates the original raw-byte fingerprint.
Source-path normalization lets the content hash stay stable across relocated
deliveries. `content_sha256` is a reproducible canonical authored-content hash,
distinct from the actual PDF byte hash (Chromium metadata may vary). The build
fingerprint also includes the adapter implementation, CSS, renderer, pins and font.

Full builds add deterministic `report.html`, `report.pdf`, `geometry.json`,
`render.json`, and `screenshots/page-01.png` through the last authored page.
Screenshots cover every HTML print sheet under print media; `check` separately
reads the PDF to require the same number of physical A4 pages and nonblank text. Geometry checks
element/text bounds, scrolling, and footer overlaps. Overflow fails the build;
the author must shorten or restructure an explicitly authored page. Content is
never silently shrunk, clipped, or split onto invented pages.

`manifest.json` freezes raw input hash, normalized content hash, adapter hashes
and output inventory/hashes. `checks.json` records freshly computed input/output
SHA-256, PDF page count, and check failures. Missing, edited, stale, or incompletely
rendered artifacts fail. Source citations in HTML/Markdown use local
`sources/{id}.pdf#page=N` links; browser PDF export preserves those hyperlinks
as portable relative links after a pypdf annotation rewrite (desktop reader
support varies). Keep the source folder with the
report. Checks are reproducibility/structure checks, not a source-content audit,
framework compliance certification, independent review, or production approval.

## Development tests

```sh
python3 -m unittest discover -s tests -p test_esg_learning.py -v
```

Tests generate local synthetic PDF fixtures and never access the network. Real
company numbers do not occur in the adapter. Browser smoke tests are recorded
separately in the development receipt, not represented as independent review.
