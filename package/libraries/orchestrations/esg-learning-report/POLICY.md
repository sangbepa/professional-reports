# ESG learning report — 0.1.0-dev.1

## esgl-policy-scope — Public-source teaching reconstruction

Frame the company, reporting period, information cutoff, intended learner,
entity/sites/value-chain perimeter, available original disclosures and framework
basis. The request's company and period fields identify the reconstruction;
metric `boundary` and `method` fields carry measurement-specific scope. Put
unresolved perimeter, publication timing and access gaps in the qualifications
and limitations. Public disclosures do not establish access to operating records.

Retain `status: "비공식 학습용"` visibly. This is an unofficial teaching
reconstruction, not the issuer's report, a GRI compliance declaration, an
assurance engagement or an investment recommendation. A framework reference is
a disclosed learning basis, not evidence of compliance or legal applicability.

## esgl-policy-evidence — Claims, metrics and methodological commentary

Use frozen public originals with measured SHA-256, source identity, original URL,
local file and physical PDF page count. Bind every company claim and numeric
metric observation to a source ID and physical PDF page. Unavailable `null`
observations may omit both citation fields; this is missing data, not a sourced
numeric assertion. Preserve the original meaning,
period, units, exclusions and qualifications. Reconcile printed page labels to
physical pages explicitly. A matching file hash proves byte identity, not truth,
cutoff eligibility or citation entailment. Missing publication evidence remains
unknown; the input schema has no publication-eligibility adjudication field.

For emissions, preserve reported Scopes 1/2/3, category/perimeter exclusions and
location-based versus market-based Scope 2 where the source distinguishes them.
Keep gross emissions, offsets, removals and avoided emissions separate. Do not
invent factors, restatements, denominators or intensity comparisons. For all ESG
metrics, `null` means unavailable, not zero. Policies and targets remain reported
statements unless separate evidence establishes implementation.

Paragraph/finding blocks use `claim_ids` for company assertions. A paragraph or
finding classified `analysis` requires `non_company_assertion: true`, no claim
IDs, and is only methodological commentary. It must make
its non-company scope clear in the text. It cannot hide an uncited factual claim.
Table cells and captions require substantive source review even when their
source references are structurally valid. Charts preserve units, years,
boundaries, unavailable values and traceable metric IDs.

## esgl-rule-learning-coverage — Independent review obligations

Define source, judgment and document review separately. Source review inspects
original meaning, dates, physical pages, metric methods and numerical fidelity.
Judgment review tests conclusions, counterevidence, omissions and teaching scope.
Document review inspects exact current output hashes, all rendered pages,
citations, charts/tables, qualifications and clipping.

Each review records an actual independent reviewer identity, independence
evidence, inspected artifacts and hashes, coverage, observations, issue-level
findings, disposition and limitations. Producers cannot self-certify independent
review. Changed inputs or output artifacts require affected reviews to be
revisited. Pending, unavailable and unperformed reviews stay explicitly so.

`plan-rules.json` can check declared capability, output and role coverage when
the generic planner is used in an allowed development context. It does not
perform source review or verify reviewer independence. The standalone adapter
does not execute those plan rules or arrange reviews. These are host obligations;
CLI success is never recorded as an independent review pass.

## esgl-policy-standalone — Supported interface and production boundary

The supported learning interface is `python -m pr.esg prepare|build|check` with
`--input` and `--out`, plus the `python -m pr esg-*` aliases. Inspect installed
help and the adapter documentation for optional rendering arguments, output
filenames and observed checks. The adapter lifecycle is standalone; it is not a
general engine `Run.finish` lifecycle. HTML-only output is not a PDF success.

The component is provisional and declares
`execution_support: "standalone-learning-adapter"`, never `complete`.
`production_report_execution_allowed` and `production_quality_verified` remain
false. General `esg` remains planning-only. The existing engine rejects this
component as a report-mode domain; no production ESG block, protected acceptance,
600-second valuation gate or release promotion criterion is changed.

Pin installed component references through `Registry.reference`/`resolve` as
actual `{id, version, sha256}` values. Method dependencies are string IDs in
`requires`; they are not invented plan edges or review receipts. Source edits
require a newly packed and explicitly activated development release.
