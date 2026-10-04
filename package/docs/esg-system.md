# Reusable company-configured ESG corpus subsystem

`python -m pr.esg_system collect|ingest|compare|report` is a source development
subsystem. It leaves the general ESG gates, runtime, protected evaluations and
existing `pr.esg` adapter unchanged. Run from the source checkout or an explicitly
verified development release containing this module. Source edits never activate
or patch an installed release. The parent owns aliases and packaging changes.

The mandate used for development is
`output/esg-common-20261004/mandate.json`, cutoff 2026-10-04. Its 20 candidate IDs,
company-file fields, original-value preservation, physical PDF locators, null
handling and context-only comparison rules are implemented here. This is a
reusable input contract, not embedded SK hynix/Samsung/TSMC research.

## Dependencies

Python >=3.11, isolated venv. No automatic/global installation:

```sh
python3 -m venv /absolute/work/venv
/absolute/work/venv/bin/python -m pip install -r requirements.txt
/absolute/work/venv/bin/python -m pip install -r adapters/esg-system/requirements.txt
```

`duckdb==1.5.6` is the current stable Python client verified on 2026-10-04 against
the [official Python documentation](https://duckdb.org/docs/stable/clients/python/overview)
and [official release announcement](https://duckdb.org/2026/09/28/announcing-duckdb-156).
The actual parent development venv successfully imported 1.5.6. `pypdf==6.19.0`
and `jsonschema==4.26.0` agree with the existing adapter/root dependencies.
DuckDB operations reject a different client version. Browser dependencies are
separate; see [the existing adapter README](../adapters/esg/README.md).

## Authoritative input contract

The exact company-file shape from the mandate remains:

```text
{company:{id,name,business_model},
 sources:[{id,title,url,path,sha256,pages,reporting_period,publication_date}],
 observations:[{id,company_id,metric_id,year,value,unit,boundary,method,
                source_id,page,evidence_text,note}],
 claims:[{id,text,source_id,page}]}
```

Merge those objects, not filenames, into:

```json
{
  "schema": "esg-corpus/1",
  "information_cutoff": "2026-10-04",
  "companies": [
    {"company": {"id": "issuer_a", "name": "Issuer A", "business_model": "Author-supplied scope"},
     "sources": [], "observations": [], "claims": []}
  ]
}
```

This envelope example illustrates shape only; ingestion requires at least one
actual registered local source PDF per company. The JSON Schema is
[`schemas/esg-corpus.schema.json`](../schemas/esg-corpus.schema.json). Each ID
uses 1–80 ASCII letters/numbers/underscores/hyphens. Company, source, observation
and claim IDs are unique globally within their respective collections. A source
and each citing observation/claim must belong to the same company.

`ingest` and `report` also accept one exact company-file object. Use
`--information-cutoff YYYY-MM-DD` to set its report cutoff; the CLI never infers a
cutoff from the current date. A company-file ingestion without this flag retains
an unknown (`null`) cutoff. Envelope cutoffs and explicit flags must agree.

The parent-authorized source provenance extension has these **optional** fields;
the mandatory mandate fields remain unchanged:

| Field | Preserved type and meaning |
| --- | --- |
| `report_release_date` | ISO date or null; announcement date, not availability of this PDF hash |
| `publication_date_basis` | String explaining the exact-hash publication-date evidence/uncertainty |
| `pdf_created_at`, `pdf_modified_at` | Original metadata strings or null; retain `D:...` syntax literally |
| `acquired_at` | ISO timestamp with timezone or null; actual acquisition, not inferred publication |
| `first_distribution_of_hash_verified` | Boolean; preserve author/reviewer observation, never infer true |
| `assurance_version_equivalence_verified` | Boolean; preserve author/reviewer observation, never infer true |
| `source_date_note` | String retaining version/date qualifications |

All optional fields survive portable copying and `source.raw_json`. A known
announcement or file metadata date never substitutes for unknown exact-hash
`publication_date`, and only known `publication_date` is compared to the cutoff.
The logical dataset fingerprint excludes `acquired_at` but the actual ledger and
operation-cache fingerprint retain it, preventing stale cached provenance from
replacing a revised acquisition record.

Optional envelope `comparison_policy` contains an unmodified
`esg-comparison-policy/1` object with `default: "context_only"` and `rules`.
Alternatively `--policy /absolute/comparison-policy.json` supplies that same
object to `ingest`/`report`. Conflicting embedded/companion policies are rejected.
The policy is preserved in the ledger, comparison and logical fingerprint; it
cannot authorize rankings or automatic unit compatibility. Candidate IDs in
policy rules are validated. Additional author policy fields remain intact.

Optional envelope `report_notes` supplies **author/reviewer-authored**, compact
material cautions to print on the respective metric page:

```json
"report_notes": [{
  "company_id": "issuer_a",
  "metric_id": "women_workforce_share",
  "text": "Source-reviewed unresolved difference and its interpretation limit.",
  "source_refs": [{"source_id": "issuer_a_report", "page": 108}]
}]
```

`metric_id`, `text`, `source_refs` are the only required fields. `company_id` is
optional, allowing the actual candidate note file to be embedded unchanged.
When supplied it must identify a registered company with at least one own source
ref. Notes without it continue to derive display selection from source refs.
Every note requires nonblank text and nonempty valid physical source refs.
The CLI preserves its complete wording and renders a visible
`주요 해석 제한 · 제공된 검토 문구` table with citations. It does not infer a
reviewer's conclusion from long `observations.note`, select meaningful sentences
by blind truncation, or certify the note as independently reviewed. Use this
field to surface unreconciled percentages, excluded definitions, material gaps,
bounded missing-data searches and version-equivalence uncertainty. Original
observation notes still remain unabridged in the ledger, and the report explicitly
states that all observation notes are **not** printed. All notes bind the logical
fingerprint; changing one invalidates affected report caching.

For `--company`, a scoped note is selected only for its optional `company_id`;
an unscoped note is selected when any source ref belongs to the selected company.
A cross-company note retains its full text/refs and includes
its other referenced PDFs in the generated report input. Unrelated notes are
not displayed in that selected report, but remain in the full ledger. A selected
comparison companion includes only notes whose full refs are inside its source
set, avoiding dangling refs. The main report can retain cross-company note
context without adding the other company's numeric series/claims. Dense authored
cautions must pass the same unchanged adapter geometry checks; nothing is silently
truncated to satisfy them.

### Source and observation semantics

- Research source paths may be absolute. Relative paths resolve beside the input
  JSON. `..`, backslashes, symlink paths and hardlinked files are rejected before
  resolution. Output copies use `sources/{sha256}.pdf`; caller originals are read
  only. Use canonical `/private/tmp/...` rather than macOS's `/tmp` symlink when
  supplying temporary paths directly.
- `pages` is the verified physical count. Each `page` is a 1-based physical PDF
  page, including covers. Every source is parsed with pypdf, with encryption,
  missing bytes, invalid headers, hash/count mismatches and blank cited pages
  rejected. Extracted text files are UTF-8 and have individual SHA-256 hashes.
  A registered PDF can also be a clearly labelled generated official-web snapshot:
  its original `title`, URL, SHA and qualification are preserved unchanged in the
  ledger/DB and forwarded to existing adapter citations. Physical page checks
  concern that registered local PDF, not an unavailable issuer-original PDF.
  Registration never upgrades a generated snapshot to an issuer original or
  establishes that a failed/403 issuer download succeeded. The report introduction
  explicitly requires this distinction and warns that snapshot page numbers are
  not issuer-original page numbers. `collect` still requires an actual downloadable
  PDF; it does not manufacture a fallback snapshot for an HTML/403 response.
- `publication_date` may be an ISO date or `null` when unknown. Known declared
  dates later than the cutoff are rejected. Unknown dates stay unknown;
  `system-manifest.json.qualifications` lists them and makes clear that cutoff
  availability still needs independent source review. The system does not invent
  publication dates or attest the truth of declared dates.
- Values are original finite JSON numbers or `null`; booleans, numeric strings,
  nonfinite/overflowing numbers and missing numeric references are rejected. Raw
  units, geographic/entity/workforce boundaries, methods, notes, evidence text
  and original claims remain intact in `ledger.json`. DuckDB also retains each
  original row as `raw_json`; its `DOUBLE` is only a query projection.
- Missing observations must have a nonblank explanatory `note`. Source/page may
  both be `null` only for a missing observation. Partial references are rejected.
  No observed year, zero, unit conversion, inferred headline, denominator or
  derivative is generated for an unregistered candidate.
- `evidence_text` may contain the full original page text, OCR extraction,
  shorter submitted evidence, or be `null`/empty for physical locator linkage.
  It is never truncated in the ledger or compared as a semantic-truth test.
  The PDF SHA, page bounds and nonblank extracted text/image content establish
  physical linkage. Claim text is retained verbatim and linked to the cited PDF
  page; neither quote presence nor linkage establishes support for its meaning.

## Acquisition stub and collection

Use the exact same company file as config. For a source not yet downloaded, set
**all** `path`, `sha256`, `pages` to `null`. Collection-stub nulls are accepted
only by `collect`; they are not valid ingested corpus sources. Keep all other
source fields, including `reporting_period` and known/unknown publication date.
Existing numeric observations may be collected, but must validate against the
downloaded originals before the collection is published. No metric is extracted
automatically from a PDF table.

```json
{
  "company": {"id": "issuer_a", "name": "Issuer A", "business_model": "Author-supplied scope"},
  "sources": [{"id": "issuer_a_report", "title": "Official publisher PDF",
    "url": "https://publisher.example.com/report.pdf",
    "path": null, "sha256": null, "pages": null,
    "reporting_period": "2025", "publication_date": null}],
  "observations": [], "claims": []
}
```

```sh
python -m pr.esg_system collect --config /research/issuer_a.json --out /work/collected-a
# A publisher may serve redirects through an explicitly approved CDN hostname:
python -m pr.esg_system collect --config /research/issuer_b.json --out /work/collected-b --official-host cdn.publisher.example.com
```

Config URL hosts are the author's declared official publishers. Additional CDN
hosts require `--official-host`; a declared host is not independently certified
as belonging to the issuer. No filename is derived from a remote path. Requests
permit only public HTTP(S), standard ports and no credentials/fragments/control
characters. All DNS addresses for each hop must be public. The transport pins a
checked address and uses the original host for TLS/Host, bypassing ambient
proxies. Redirects are checked hop by hop; HTTPS downgrade, private/file URLs,
undeclared redirect hosts, excessive redirects, encoded responses, empty PDFs
and downloads exceeding 200 MiB fail. TLS certificate verification remains on.

Outputs are `company.json`, `sources/{sha256}.pdf`, `acquisition.json`,
`page-text/{source_id}-{page:05d}.txt`, `page-evidence.json`,
`system-manifest.json`. Acquisition retains original URL, final URL, SHA, actual
bytes/pages and UTC retrieval timestamp. Its timestamps are real provenance,
not part of the logical corpus fingerprint. Preserve acquisition companions
when packaging collected research. A cached collection is used only after file
inventory/hash verification and reopening each PDF to verify its pages.

## Explicit local generated-snapshot collection

```sh
python -m pr.esg_system collect --config /research/tsmc.json --out /work/collected-tsmc --local-snapshots
```

This explicit mode verifies and copies existing `config.path` PDFs; it never
calls HTTP and never silently follows a failed download with a local fallback.
Each source requires non-null existing path, expected SHA-256 and positive page
count. Its supplied title must clearly say `GENERATED`, `web`, `snapshot` and
`NOT issuer PDF` (including `NOT issuer-original PDF`). No source type is inferred
or rewritten. Local source hashes/pages and physical evidence links are checked
before cache reuse and after copying. A changed caller snapshot cannot be hidden
by a valid old cached copy. Normal path/symlink/hardlink/output guards apply.

`acquisition.json` explicitly records `mode: "verified_local_snapshot"`, the
supplied provenance URL, `final_url: null`, local input path, actual verification
timestamp, bytes/SHA/pages, `http_acquisition: false`,
`issuer_original_acquired: false` and the unmodified origin qualification title.
The URL identifies supplied provenance, not a network acquisition performed by
this invocation. Original source provenance dates/fields remain intact. An issuer
403/unavailable-PDF gap remains unresolved. Default collection continues to use
HTTP with `mode: "http_download"`; download failures stay failures. Collection mode
is part of the cache fingerprint and manifest, so a network collection and local
snapshot collection cannot reuse each other's output. `--official-host` is a
network-only option and cannot be combined with `--local-snapshots`.

## Ingestion, query tables and comparison

```sh
python -m pr.esg_system ingest --input /research/corpus.json --out /work/ingested --policy /research/comparison-policy.json
python -m pr.esg_system compare --db /work/ingested/corpus.duckdb --out /work/comparison
```

Ingestion writes an authoritative portable `ledger.json`, original PDF copies,
page extraction/hashes and `corpus.duckdb`. Tables:

| Table | Contents |
| --- | --- |
| `companies` | ID, supplied name/business model, original JSON |
| `source` | Company ID, original URL/title, portable path, SHA/pages, reporting period, nullable publication date, original JSON |
| `observations` | All observation contract fields; numeric query value plus authoritative original JSON |
| `claims` | Company ID, original claim text, physical source/page, original JSON |
| `page_evidence` | Source SHA, physical page, UTF-8 extraction path/hash/text, image flag |
| `metadata` | Schema, logical ledger fingerprint and dependency versions |

Database construction uses an explicit transaction and checkpoint in the staged
output. `compare` accepts only a managed `corpus.duckdb` with its original
manifest/ledger/source bundle, verifies that bundle and checks DB raw rows
against the ledger. Read-only query connections disable external access and
automatic extension loading/installation.

Both `ingest` and `compare` export `comparison.json`, `missingness.json` and
`observations.csv`. There are exactly the mandate's 20 candidate entries, and
one state per company/candidate: `reported`, `explicit_missing`,
`partial_missing`, `not_registered`. JSON preserves every original observation
and source/page ref, including each company's separate divisions and methods.
The comparison carries all selected sources and original claims. Matching
labels/units/years never approves compatibility: the output is `context_only`,
`ranking_authorized: false`, `unit_compatibility: "not_approved"` throughout.
There is no sorting by ESG performance, score or inferred efficiency.

CSV is a convenience companion. Nulls are spelled `null`, and formula-like
strings receive a leading apostrophe for spreadsheet use. JSON remains
authoritative and does not undergo that CSV display escaping.

## Same report command for one or all companies

```sh
# Combined selected corpus; all its companies:
python -m pr.esg_system report --input /research/corpus.json --out /work/report-all --html-only
# Exact company selection (same generator and adapter):
python -m pr.esg_system report --input /research/corpus.json --out /work/report-a --company issuer_a --html-only
# Actual PDF with existing adapter's browser flags:
python -m pr.esg_system report --input /research/corpus.json --out /work/report-all-pdf --chromium /absolute/Chrome --node /absolute/node --playwright-module /absolute/playwright
```

`report` emits `report-input.json` in the existing `esg-learning-report/1`
contract and calls **existing** `pr.esg.build`. The request references safe PDF
copies beside it. Output includes the full ledger, comparison/CSV companions,
`series-bindings.json` and the adapter's `report/` directory with editable JSON,
Markdown, HTML, manifests/checks, and PDF/geometry/screenshots on a PDF build.
`--html-only` explicitly records `pdf_success: false`. Browser flags are forwarded
unchanged. Failed builds do not publish a successful output directory.

The Korean report has three methodological/reading/missingness pages, one to
seven verbatim claim pages, and 20 distinct candidate pages: **24–30 physical
pages**, subject to the existing adapter's actual render/page/overflow checks.
The standard 28-claim three-company corpus uses seven pages of four claims,
giving 30 pages. The generator neither silently drops claims nor pads a report
with duplicate pages. An unusually long/dense input may fail the geometry check;
it needs a reviewed presentation revision, not deletion or invented compression
of observations. The complete ledger remains preserved regardless of selected
company. The comparison companion uses the report's selected companies.

Series partition by `(company_id, metric_id, unit, boundary, method)`, never by
company/candidate alone. Repeated observations in the same year become separate
rows. Every original selected observation stays in generated metric values and
series mappings. Numeric tables show years in ascending order; absent cells show
`미등록`, explicit missing values show `null`, and zero stays zero. No chart joins
incompatible boundaries or converts original units.

Each numeric row displays the supplied company name (or its explicitly supplied
Korean alternative/acronym, including TSMC) and an extractive division/scope label.
Samsung DX+DS, DX Division and DS Division are distinguishable. Per the parent's
revised page-budget instruction, the repeated full boundary/method table is
omitted: a small methodological note identifies `series-bindings.json` and its
`company_id`, `metric_id`, `boundary`, `method`, `observations.note` fields. Those
fields remain unabridged in the companion and generated metric metadata. Source-
bound `report_notes` print material cautions without truncation. The report
explicitly states that the brief scope label does not print all qualifications.
Machine series hashes live in companions rather than replacing meaningful
reader labels. Null-only groups
use compact existing adapter metric blocks with full boundary/method and all
original years. Missing numeric references are not invented to make a table pass.
Long notes and evidence text remain unabridged in the ledger/series companion.
Repeated company prefixes are removed only from extractive navigation labels so
overseas, Korean and whole-workforce scopes remain visible. The complete original
boundary remains in the explicitly referenced companion. Repeated footers show the registered
observation-year horizon; a reading-page table preserves full submitted source
reporting-period metadata and links existing submitted physical source locators,
without inventing first-page citations. These metadata declarations still require
source review.

Each factual claim paragraph binds its original `claim_ids`; methodological
paragraphs and introductory titles/leads explicitly use
`classification: "analysis", non_company_assertion: true`. Candidate names are
methodological categories, not proof that the original satisfies a definition.
The footer says the CLI does not conduct/certify independent reviews and refers
to host review records. It does not deny reviews actually arranged by the host.
CLI manifests record only this invocation's `independent_review: not_performed`
and `runtime_model_telemetry: unknown`; they never create independent passes.

## Atomic outputs, caching and portable fingerprints

All outputs are assembled in a new sibling staging directory. Ingest commits
the database transaction and verifies input/original hashes before the directory
is published by rename; cooperating publishers use an exclusive sibling lock.
Files/manifests are sealed only after successful work. Failure removes the
temporary stage. No operation overwrites an unmanaged, changed or differently
configured output directory: choose a fresh `--out`. Output must not contain an
input/original, be a symlink/hardlink alias, or reside inside a release bundle.
Every cached inventory and file hash is checked, including nested paths; modified
cache files are rejected. This is local cooperative publication, not an adversarial
filesystem access-control system.

The logical `ledger_fingerprint` canonicalizes company/source/observation/claim
ordering and rewrites machine-specific source paths to their SHA-based portable
names. It includes source bytes via SHA, source metadata, every original
observation/claim and any comparison policy. Relocating the same corpus keeps
that fingerprint identical. `request_fingerprint` additionally binds code/schema
hashes, dependency/extractor versions and report options/adapter hashes where
applicable; code changes invalidate cached operations without altering the
logical dataset identity. Retrieval timestamps remain in the separate acquisition
receipt; optional source `acquired_at` is also retained verbatim in the ledger but
excluded from the logical data identity. PDF binary bytes need not be deterministic across browser runs; actual
artifact hashes and stable logical fingerprints are separate measurements.

## Actual verification record

Tests use actual local text-bearing PDFs authored with pypdf and a real pinned
DuckDB database. Network collection uses controlled download/connection mocks;
they do not establish availability or semantic fidelity of real issuer websites.
Coverage includes null/nonfinite/type/reference errors, original hashes/counts,
full-page/OCR physical linkage, private URLs/DNS/redirects, symlink/hardlink/input
collisions, atomic failure, verified caches, portable logical fingerprints/policy,
20-candidate missingness, non-approved unit compatibility, source refs,
same-year/division separation, all/each-company CLI reports, 28 claims, compact
null series, meaningful reader scope labels, and browser option forwarding.

Run from the source root with the parent's isolated development venv:

```sh
PYTHONDONTWRITEBYTECODE=1 development/esg-common-001/venv/bin/python -m unittest tests.test_esg_system tests.test_esg_learning tests.test_esg_learning_integration -v
```

Actual test log, 2026-10-04:

```text
Initial system test run: Ran 25 tests in 2.157s; FAILED (failures=4).
Cause: existing adapter blocked company names in method-classified missingness prose.
Correction: use selection-list positions and explicitly describe input registration state.
Next system test run: Ran 25 tests in 2.552s; FAILED (failures=1, errors=2).
Cause: operation-cache hash was accidentally applied to the logical database ledger check.
Correction: keep logical ledger hash separate from code/operation hash.
System recheck: Ran 25 tests in 2.465s; OK.
Expanded system + existing adapter/integration regression:
Ran 88 tests in 4.835s
OK
After provenance extension and exact-version date preservation:
Ran 89 tests in 4.747s
OK
```

This records developer checks, not an independent review. Installed-release
activation, live-source validity and host source/judgment/document review remain
separate deliverables owned by the parent workflow.


Final source-contract/report-note regression, 2026-10-04 (verbatim unittest tail;
exit code 0):

```text
----------------------------------------------------------------------
Ran 90 tests in 4.587s

OK
```

Real-source developer checks used temporary outputs, removed after verification:

```text
Input: corpus-two-company-preview-02.json
companies: 2
observations: 136
candidate_metrics: 20
unknown_publication_date_source_ids: ["samsung-sr-2026"]
ledger_fingerprint: ba2b962299786918a2487de6554e2679dfc407de1654e565853efd0b94604b72
independent_review: not_performed (CLI scope only)
```

Actual PDF rendering of the earlier two-company preview initially failed the
sandboxed Chrome launch (`SIGABRT`/`EPERM`). A permitted headless-browser run then
identified geometry overflow on pages 15 and 25, later only page 25. Full
boundary/method tables were retained; extractive reader labels, wider two-column
scope/method rows, reduced repeated prose and compact observation-year footers
resolved the overflow. Actual successful adapter output was:

```text
{'authored_pages': 28, 'pdf_success': True, 'stage': 'pdf'}
```

That developer render validated physical page count and all geometry. It is not
an independent visual/source/judgment review. The later optional `report_notes`
contract is tested with source-bound synthetic cautions; the parent's actual
reviewed cautions and final three-company PDF still need their actual render and
host reviews. No claim of success for an unrendered final dataset is recorded.

Changed source paths, limited to this worker's assigned scope:

```text
pr/esg_system.py
schemas/esg-corpus.schema.json
tests/test_esg_system.py
docs/esg-system.md
adapters/esg-system/requirements.txt
```


Latest bounded follow-up, 2026-10-04:

- Actual candidate file: 11/11 `report_notes` entries fit the schema, including
  optional `company_id`; no candidate or company data was modified.
- Actual TSMC source metadata: 2/2 entries fit the source schema. Portable
  normalization preserves every supplied source field except the content-safe
  path rewrite. GENERATED/NOT issuer PDF titles and original URLs stay intact.
  This check did not inspect TSMC PDF bytes or assess disclosure meaning.
- Generic report prose now says registered source PDF and explicitly separates
  generated snapshot pages from issuer-original pages; no new source-kind field
  or automatic provenance inference was introduced.

Complete actual final regression log (exit code 0):

```text
test_atomic_failure_leaves_no_outputs_or_input_changes (tests.test_esg_system.ESGSystemTests.test_atomic_failure_leaves_no_outputs_or_input_changes) ... ok
test_browser_flags_forwarded_and_failed_build_not_published (tests.test_esg_system.ESGSystemTests.test_browser_flags_forwarded_and_failed_build_not_published) ... ok
test_claims_cross_company_and_duplicate_ids_rejected (tests.test_esg_system.ESGSystemTests.test_claims_cross_company_and_duplicate_ids_rejected) ... ok
test_cli_errors_unknown_company_and_no_report_replacement (tests.test_esg_system.ESGSystemTests.test_cli_errors_unknown_company_and_no_report_replacement) ... ok
test_collect_host_redirect_and_download_limit (tests.test_esg_system.ESGSystemTests.test_collect_host_redirect_and_download_limit) ... ok
test_collect_invalid_download_rolls_back (tests.test_esg_system.ESGSystemTests.test_collect_invalid_download_rolls_back) ... ok
test_collect_verified_cache_and_provenance (tests.test_esg_system.ESGSystemTests.test_collect_verified_cache_and_provenance) ... ok
test_company_scoped_note_selected_only_for_its_company (tests.test_esg_system.ESGSystemTests.test_company_scoped_note_selected_only_for_its_company) ... ok
test_compare_twenty_metrics_missingness_all_refs_no_rankings (tests.test_esg_system.ESGSystemTests.test_compare_twenty_metrics_missingness_all_refs_no_rankings) ... ok
test_database_tampering_rejected (tests.test_esg_system.ESGSystemTests.test_database_tampering_rejected) ... ok
test_duplicate_json_keys_nonfinite_json_and_overflow (tests.test_esg_system.ESGSystemTests.test_duplicate_json_keys_nonfinite_json_and_overflow) ... ok
test_generated_web_snapshot_metadata_keeps_provenance_distinction (tests.test_esg_system.ESGSystemTests.test_generated_web_snapshot_metadata_keeps_provenance_distinction) ... ok
test_hardlinked_input_and_source_preserved (tests.test_esg_system.ESGSystemTests.test_hardlinked_input_and_source_preserved) ... ok
test_human_visible_divisions_and_unabridged_scope_method (tests.test_esg_system.ESGSystemTests.test_human_visible_divisions_and_unabridged_scope_method) ... ok
test_ingest_real_duckdb_projection_portable_and_idempotent (tests.test_esg_system.ESGSystemTests.test_ingest_real_duckdb_projection_portable_and_idempotent) ... ok
test_input_source_and_output_symlinks_rejected (tests.test_esg_system.ESGSystemTests.test_input_source_and_output_symlinks_rejected) ... ok
test_invalid_refs_types_null_notes_and_nonfinite (tests.test_esg_system.ESGSystemTests.test_invalid_refs_types_null_notes_and_nonfinite) ... ok
test_local_pdf_evidence_full_text_and_ocr_linkage (tests.test_esg_system.ESGSystemTests.test_local_pdf_evidence_full_text_and_ocr_linkage) ... ok
test_multiple_boundaries_methods_and_duplicate_year_not_dropped (tests.test_esg_system.ESGSystemTests.test_multiple_boundaries_methods_and_duplicate_year_not_dropped) ... ok
test_nested_symlink_and_hardlink_cache_rejected (tests.test_esg_system.ESGSystemTests.test_nested_symlink_and_hardlink_cache_rejected) ... ok
test_null_only_series_compact_and_preserves_all_years (tests.test_esg_system.ESGSystemTests.test_null_only_series_compact_and_preserves_all_years) ... ok
test_output_input_original_and_unmanaged_collisions (tests.test_esg_system.ESGSystemTests.test_output_input_original_and_unmanaged_collisions) ... ok
test_pdf_hash_count_and_blank_page_checks (tests.test_esg_system.ESGSystemTests.test_pdf_hash_count_and_blank_page_checks) ... ok
test_policy_companion_preserved_and_cannot_authorize_rankings (tests.test_esg_system.ESGSystemTests.test_policy_companion_preserved_and_cannot_authorize_rankings) ... ok
test_portable_fingerprint_same_across_paths_order_and_policy_changes (tests.test_esg_system.ESGSystemTests.test_portable_fingerprint_same_across_paths_order_and_policy_changes) ... ok
test_release_destination_is_never_mutated (tests.test_esg_system.ESGSystemTests.test_release_destination_is_never_mutated) ... ok
test_report_all_and_every_company_same_cli_and_existing_schema (tests.test_esg_system.ESGSystemTests.test_report_all_and_every_company_same_cli_and_existing_schema) ... ok
test_reviewed_report_notes_visible_source_bound_and_preserved (tests.test_esg_system.ESGSystemTests.test_reviewed_report_notes_visible_source_bound_and_preserved) ... ok
test_schema_contract_and_metric_set_match_mandate (tests.test_esg_system.ESGSystemTests.test_schema_contract_and_metric_set_match_mandate) ... ok
test_single_company_input_requires_explicit_report_cutoff (tests.test_esg_system.ESGSystemTests.test_single_company_input_requires_explicit_report_cutoff) ... ok
test_source_paths_traversal_and_cutoff_rejected (tests.test_esg_system.ESGSystemTests.test_source_paths_traversal_and_cutoff_rejected) ... ok
test_twenty_eight_claims_fit_thirty_pages_without_dropping (tests.test_esg_system.ESGSystemTests.test_twenty_eight_claims_fit_thirty_pages_without_dropping) ... ok
test_unknown_publication_date_preserved_and_qualified (tests.test_esg_system.ESGSystemTests.test_unknown_publication_date_preserved_and_qualified) ... ok
test_url_private_file_and_dns_addresses_rejected (tests.test_esg_system.ESGSystemTests.test_url_private_file_and_dns_addresses_rejected) ... ok
test_version_date_provenance_is_preserved_without_inferred_availability (tests.test_esg_system.ESGSystemTests.test_version_date_provenance_is_preserved_without_inferred_availability) ... ok
test_adapter_change_invalidates_fingerprint (tests.test_esg_learning.ESGLearningTests.test_adapter_change_invalidates_fingerprint) ... ok
test_all_null_has_no_invented_numeric_axis (tests.test_esg_learning.ESGLearningTests.test_all_null_has_no_invented_numeric_axis) ... ok
test_analysis_requires_explicit_non_company_assertion (tests.test_esg_learning.ESGLearningTests.test_analysis_requires_explicit_non_company_assertion) ... ok
test_blank_page_and_page_limits (tests.test_esg_learning.ESGLearningTests.test_blank_page_and_page_limits) ... ok
test_check_guard_failure_preserves_existing_files (tests.test_esg_learning.ESGLearningTests.test_check_guard_failure_preserves_existing_files) ... ok
test_check_hardlinked_diagnostic_preserves_input (tests.test_esg_learning.ESGLearningTests.test_check_hardlinked_diagnostic_preserves_input) ... ok
test_citation_bounds_and_boolean_page (tests.test_esg_learning.ESGLearningTests.test_citation_bounds_and_boolean_page) ... ok
test_claim_unknown_source (tests.test_esg_learning.ESGLearningTests.test_claim_unknown_source) ... ok
test_cli_failure_exit_and_html_success (tests.test_esg_learning.ESGLearningTests.test_cli_failure_exit_and_html_success) ... ok
test_compact_claim_citation_does_not_repeat_claim_text (tests.test_esg_learning.ESGLearningTests.test_compact_claim_citation_does_not_repeat_claim_text) ... ok
test_copied_source_mutation_invalidates (tests.test_esg_learning.ESGLearningTests.test_copied_source_mutation_invalidates) ... ok
test_deterministic_content_html_and_markdown (tests.test_esg_learning.ESGLearningTests.test_deterministic_content_html_and_markdown) ... ok
test_duplicate_ids_and_years (tests.test_esg_learning.ESGLearningTests.test_duplicate_ids_and_years) ... ok
test_edit_and_build_prepared_input_in_place (tests.test_esg_learning.ESGLearningTests.test_edit_and_build_prepared_input_in_place) ... ok
test_escaping_does_not_execute_html (tests.test_esg_learning.ESGLearningTests.test_escaping_does_not_execute_html) ... ok
test_failed_renderer_leaves_no_success_manifest (tests.test_esg_learning.ESGLearningTests.test_failed_renderer_leaves_no_success_manifest) ... ok
test_header_requires_classification_or_claims (tests.test_esg_learning.ESGLearningTests.test_header_requires_classification_or_claims) ... ok
test_html_only_requires_explicit_check_flag (tests.test_esg_learning.ESGLearningTests.test_html_only_requires_explicit_check_flag) ... ok
test_input_mutation_invalidates_output (tests.test_esg_learning.ESGLearningTests.test_input_mutation_invalidates_output) ... ok
test_large_finite_chart_does_not_overflow (tests.test_esg_learning.ESGLearningTests.test_large_finite_chart_does_not_overflow) ... ok
test_manifest_cannot_omit_artifacts (tests.test_esg_learning.ESGLearningTests.test_manifest_cannot_omit_artifacts) ... ok
test_metric_missing_page (tests.test_esg_learning.ESGLearningTests.test_metric_missing_page) ... ok
test_metric_missing_source (tests.test_esg_learning.ESGLearningTests.test_metric_missing_source) ... ok
test_multi_metric_comparison_union_years_and_cell_sources (tests.test_esg_learning.ESGLearningTests.test_multi_metric_comparison_union_years_and_cell_sources) ... ok
test_nonfinite_bool_and_numeric_string_rejected (tests.test_esg_learning.ESGLearningTests.test_nonfinite_bool_and_numeric_string_rejected) ... ok
test_null_is_unavailable_and_chart_gap (tests.test_esg_learning.ESGLearningTests.test_null_is_unavailable_and_chart_gap) ... ok
test_null_with_invalid_citation_is_rejected (tests.test_esg_learning.ESGLearningTests.test_null_with_invalid_citation_is_rejected) ... ok
test_output_cannot_overwrite_input_or_source (tests.test_esg_learning.ESGLearningTests.test_output_cannot_overwrite_input_or_source) ... ok
test_output_hash_change_and_missing_file (tests.test_esg_learning.ESGLearningTests.test_output_hash_change_and_missing_file) ... ok
test_output_symlink_rejected (tests.test_esg_learning.ESGLearningTests.test_output_symlink_rejected) ... ok
test_path_traversal_absolute_and_escape_symlink (tests.test_esg_learning.ESGLearningTests.test_path_traversal_absolute_and_escape_symlink) ... ok
test_pdf_details_rejects_blank_and_non_a4 (tests.test_esg_learning.ESGLearningTests.test_pdf_details_rejects_blank_and_non_a4) ... ok
test_physical_pdf_page_count (tests.test_esg_learning.ESGLearningTests.test_physical_pdf_page_count) ... ok
test_prepare_copies_sources_and_is_not_pdf (tests.test_esg_learning.ESGLearningTests.test_prepare_copies_sources_and_is_not_pdf) ... ok
test_prepare_hardlinked_destination_preserves_source (tests.test_esg_learning.ESGLearningTests.test_prepare_hardlinked_destination_preserves_source) ... ok
test_prepare_source_destination_collision_preserves_original (tests.test_esg_learning.ESGLearningTests.test_prepare_source_destination_collision_preserves_original) ... ok
test_real_zero_is_retained (tests.test_esg_learning.ESGLearningTests.test_real_zero_is_retained) ... ok
test_schema_adapter_header_table_and_source_contract_agree (tests.test_esg_learning.ESGLearningTests.test_schema_adapter_header_table_and_source_contract_agree) ... ok
test_source_hash_change (tests.test_esg_learning.ESGLearningTests.test_source_hash_change) ... ok
test_strict_json_parser (tests.test_esg_learning.ESGLearningTests.test_strict_json_parser) ... ok
test_table_and_source_citation_errors (tests.test_esg_learning.ESGLearningTests.test_table_and_source_citation_errors) ... ok
test_table_metric_binding_requires_all_value_citations (tests.test_esg_learning.ESGLearningTests.test_table_metric_binding_requires_all_value_citations) ... ok
test_unknown_claim_and_metric (tests.test_esg_learning.ESGLearningTests.test_unknown_claim_and_metric) ... ok
test_unknown_fields_and_table_shape (tests.test_esg_learning.ESGLearningTests.test_unknown_fields_and_table_shape) ... ok
test_unreferenced_claim_and_values (tests.test_esg_learning.ESGLearningTests.test_unreferenced_claim_and_values) ... ok
test_value_precision_is_not_rounded_to_fifteen_digits (tests.test_esg_learning.ESGLearningTests.test_value_precision_is_not_rounded_to_fifteen_digits) ... ok
test_whitespace_input_mutation_also_invalidates (tests.test_esg_learning.ESGLearningTests.test_whitespace_input_mutation_also_invalidates) ... ok
test_alias_delegates_exact_arguments_and_preserves_exit_status (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_alias_delegates_exact_arguments_and_preserves_exit_status) ... ok
test_alias_help_lists_required_interface_without_importing_adapter (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_alias_help_lists_required_interface_without_importing_adapter) ... ok
test_alias_serializes_missing_input_and_contract_errors (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_alias_serializes_missing_input_and_contract_errors) ... ok
test_development_plan_preserves_method_checks_outputs_and_review_roles (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_development_plan_preserves_method_checks_outputs_and_review_roles) ... ok
test_general_and_learning_esg_cannot_enter_production_report_mode (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_general_and_learning_esg_cannot_enter_production_report_mode) ... ok
test_missing_adapter_reports_actionable_error_without_engine_run (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_missing_adapter_reports_actionable_error_without_engine_run) ... ok
test_pack_verify_install_load_carries_real_adapter_schema_and_docs (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_pack_verify_install_load_carries_real_adapter_schema_and_docs) ... ok
test_parent_schema_accepts_all_block_kinds_and_null_without_fabrication (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_parent_schema_accepts_all_block_kinds_and_null_without_fabrication) ... ok
test_registry_discovers_versioned_components_and_rejects_stale_pins (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_registry_discovers_versioned_components_and_rejects_stale_pins) ... ok
test_schema_rejects_uncited_prose_bad_blocks_and_false_official_status (tests.test_esg_learning_integration.ESGLearningIntegrationTests.test_schema_rejects_uncited_prose_bad_blocks_and_false_official_status) ... ok

----------------------------------------------------------------------
Ran 92 tests in 4.941s

OK
```


Final local-collection and compact-report revision, 2026-10-04:

The parent withdrew the full boundary/method-table instruction after its actual
three-company report overflow. The final generator retains one numeric table,
meaningful extractive scope labels, a companion-field reference and complete
source-bound authored material cautions. All original values, boundaries,
methods, notes and series remain in metadata/companions. Geometry criteria and
protected core were not changed. The parent's latest three-company render still
needs its actual current-target check; this revision does not record a PDF pass.

Actual regression command is unchanged; final exit code 0, verbatim tail:

```text
----------------------------------------------------------------------
Ran 95 tests in 5.199s

OK
```

Three added collection tests exercised no-HTTP CLI/cache collection, null
path/SHA/page stub rejection, explicit generated origin title, hash/page errors,
changed caller-original rejection, separate mode fingerprints and no fallback
on an HTTP 403. Existing all/each-company, source-note, provenance and protected
ESG adapter/integration regressions also passed.

Actual TSMC collection invoked the same module CLI against the caller's config
with `--local-snapshots`, writing only a temporary output that was removed after
verification. A second identical command verified cache reuse. Actual summary:

```json
{"ok": true, "sources": 2, "physical_pages": 11, "mode": "verified_local_snapshot", "http_acquisition": false, "issuer_original_acquired": false, "cache_verified": true}
```

The company data and generated snapshot originals were not edited. Failed issuer
PDF acquisition remains a gap. This is registered-byte/extraction verification,
not independent origin/source-meaning review.
