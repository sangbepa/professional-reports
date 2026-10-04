# ESG learning report development adapter

`esg-learning-report` is a provisional, versioned orchestration for public-source
teaching reconstruction. Its method component is `esg-learning-report-method`.
Reports retain `status: "비공식 학습용"`; they are not issuer reports, GRI
compliance declarations or assurance opinions. General `esg` remains planning-only.

The supported lifecycle is standalone `python -m pr.esg prepare|build|check`.
Aliases `python -m pr esg-prepare|esg-build|esg-check` forward `--input` and `--out`
and preserve the adapter's exit status. Optional adapter flags are available on
`pr.esg` itself; inspect its installed `--help`. This is not `Run.finish` support,
and neither component is eligible for generic engine report-mode completion.

## Source development dependencies and isolated installation

Run from the source `professional-reports` directory with Python >=3.11 and the
Node/npm runtime required by `adapters/esg`. Keep the development environment and
state isolated. Root requirements provide package/schema tools; the adapter's
own requirements and package manifest provide PDF/rendering dependencies. They
are source prerequisites, not dependencies installed automatically by `pr install`.

```sh
cd /path/to/professional-reports/package
ESGL_SOURCE="$PWD"
ESGL_WORK=$(mktemp -d /tmp/esg-learning-install.XXXXXX)
python3 -m venv "$ESGL_WORK/venv"
ESGL_PY="$ESGL_WORK/venv/bin/python"
"$ESGL_PY" -m pip install -r "$ESGL_SOURCE/requirements.txt"
"$ESGL_PY" -m pip install -r "$ESGL_SOURCE/adapters/esg/requirements.txt"
```

The development adapter pins its Python PDF reader and Playwright versions, and
requires Node >=20, in its own manifests. Install source rendering dependencies as documented in
`adapters/esg/README.md`.
Use `npm ci --prefix adapters/esg` when a checked-in lockfile is present; otherwise
use `npm install --prefix adapters/esg` against its pinned manifest and retain the
resolved lockfile as development evidence. Install a compatible Chromium or use
the adapter's documented existing-browser option. Browser installation is separate
from package installation. Do not place `node_modules` inside an immutable release
after verification; use the source dependency directory and the adapter's supported
external resolver. For this adapter, set
`ESG_PLAYWRIGHT_MODULE="$ESGL_SOURCE/adapters/esg/node_modules/playwright"`
before invoking installed code, or pass `--playwright-module` to `pr.esg build`.
Use `ESG_CHROMIUM_EXECUTABLE`/`--chromium` for an existing compatible browser and
`ESG_NODE`/`--node` for a selected Node runtime. Consult the adapter README for
resolver precedence and browser installation.

```sh
npm ci --prefix "$ESGL_SOURCE/adapters/esg"
export ESG_PLAYWRIGHT_MODULE="$ESGL_SOURCE/adapters/esg/node_modules/playwright"
# If no compatible existing browser is selected:
"$ESGL_SOURCE/adapters/esg/node_modules/.bin/playwright" install chromium
```

```sh
"$ESGL_PY" -m pr doctor
"$ESGL_PY" -m pr catalog
"$ESGL_PY" -m pr pack --out "$ESGL_WORK/release" --version 0.1.0-esg-learning-dev.1
"$ESGL_PY" -m pr verify --release "$ESGL_WORK/release"
"$ESGL_PY" -m pr install --release "$ESGL_WORK/release" --state "$ESGL_WORK/state"
ESGL_RELEASE_ID=$("$ESGL_PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["release_id"])' "$ESGL_WORK/release/release.json")
"$ESGL_PY" -m pr activate --state "$ESGL_WORK/state" --release-id "$ESGL_RELEASE_ID" --development
"$ESGL_PY" -m pr load --state "$ESGL_WORK/state" > "$ESGL_WORK/loaded.json"
ESGL_INSTALLED=$("$ESGL_PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["path"])' "$ESGL_WORK/loaded.json")
cd "$ESGL_INSTALLED"
"$ESGL_PY" -m pr.esg --help
"$ESGL_PY" -m pr.esg prepare --help
"$ESGL_PY" -m pr.esg build --help
"$ESGL_PY" -m pr.esg check --help
```

`load` verifies the installed active release and returns its root/version/hash;
retain that root. Run from it so Python imports installed code. `--root` is an
engine definition selector and does not switch the imported adapter. `doctor`
probes its listed tools only; it is not an ESG browser-readiness or source-truth
certificate. `catalog` and `pack` resolve components and dependency IDs through
the existing registry. Source edits require a new release; they do not update an
installed release in place.

## Input and invocation

The parent input contract is `esg-learning-report/1` with `schema` (or `contract`)
equal to that version string, plus
`company`, `title`, `reporting_period`, `information_cutoff`, `status`, `sources`,
`metrics`, `claims`, `pages` and `framework`. The JSON Schema is
`schemas/esg-learning-report.schema.json` in the package root. Source paths are
resolved relative to the authored input's parent by the adapter; preserve the
input and originals together, outside the installed release.

- Sources: `{id,title,url,path,sha256,pages}`. `pages` is the original PDF's physical
  page count; each citation's `page` is one-based physical PDF numbering.
- Metrics: `{id,label,unit,boundary,method,values,footnotes}` with each observation
  `{year,value,source_id,page}` with integer `year`. `value: null` means unavailable,
  never zero; an unavailable observation may omit both citation fields. If either
  citation field is supplied, both must be present. Numeric values always require both.
- Claims: `{id,text,source_id,page}`.
- Pages: `{id,title,kicker,lead,blocks}`; author 20–30 substantive pages.
- Framework: `{basis,qualification}`; disclose limitations without claiming compliance.

Blocks use `kind`: `paragraph`/`finding` with `text` and nonempty `claim_ids`, or
explicit `classification: "analysis", non_company_assertion: true` for methodological
commentary whose text states its non-company scope and has no claim IDs;
`metrics` with `ids`; `table` with string `headers`,
string-cell `rows` and `source_refs`; `chart` with `metric_ids` and `caption`; and
`source` with `refs`. A source reference is `{source_id,page}`. A valid reference
does not prove that the original supports the claim. The schema cannot establish
unique IDs, reference existence, original page bounds, hash identity, finite
numbers, table width or whether prose has uncited factual assertions; keep actual
adapter and source-review outcomes distinct.

Factual page titles/leads can bind optional page `claim_ids`; methodological
introductions can declare page `classification: "analysis", non_company_assertion: true`.
Keep introductory company assertions cited even though these fields are optional.

```sh
# Still in the verified installed root. Choose an actual authored request.
ESGL_INPUT=/absolute/path/to/learning-input.json
"$ESGL_PY" -m pr.esg prepare --input "$ESGL_INPUT" --out "$ESGL_WORK/report"
"$ESGL_PY" -m pr.esg build --input "$ESGL_INPUT" --out "$ESGL_WORK/report"
"$ESGL_PY" -m pr.esg check --input "$ESGL_INPUT" --out "$ESGL_WORK/report"
```

Use exact installed adapter help/README for generated filenames, browser options
and external Node dependency resolution. HTML-only output, if requested through
the adapter, is not successful PDF delivery. Failed, stale and missing-output
checks must be retained as failures. No lifecycle command supplies independent
reviewer evidence or production acceptance.

## Independent review and remaining boundaries

The host arranges independent **source**, **judgment** and **document** reviews.
Record reviewer identity and independence evidence, inspected artifact hashes,
actual coverage, observations, findings and disposition. Source review checks
original meaning, cutoff evidence, units, methods, perimeter and numerical
fidelity. Judgment review challenges omissions, counterevidence, commentary and
conclusion strength. Document review inspects every exact current rendered page,
including charts, tables, visible citations, qualifications and clipping.
Changed artifacts invalidate affected review coverage. Unperformed review remains
pending/unavailable, never a CLI-generated independent pass.

The new method and plan rules define obligations; the generic planner can validate
declared coverage in an allowed development plan. The standalone CLI does not
run those rules or enforce host review completion. Public-source reconstruction
does not establish operating records, control effectiveness, legal applicability,
GRI compliance or assurance. Structural tests and development release activation
do not satisfy protected acceptance or alter the 600-second valuation gates.
