# Design judgment and independent selection

## Native sourcebook and design identities

Read the actual [report-outfit guide](../../../../report-outfit/README.md), [native generator](../../../../report-outfit/build.py), [full-report constructors](../../../../report-outfit/full_report.py), [preparation adapter](../../../../report-outfit/prepare_report.py), [design sourcebook/proposal](../../../../output/deloitte-design-proposals/proposal/report.html) and [style handbook](../../../../output/deloitte-design-proposals/style-guide/report.html) when available in the authoring workspace. The original native `DESIGNS` are:

| Actual identifier | Native name | Actual composition |
| --- | --- | --- |
| A / `transaction` | Transaction Precision | Ruled tables, indexed issues, evidence hierarchy |
| B / `executive` | Executive Clarity | Spacious single-column reading, a principal value, open comparisons |
| C / `editorial` | Insight Editorial | Vector-led opening, chapter rhythm, explanatory columns and exhibits |

The guide supplies the actual generation system; it is not just an aesthetic reference. The style handbook specifies A4 portrait and a twelve-column grid with 18 mm default side margins, local Open Sans, body 10.5 pt, tables at least 9.5 pt and source notes/captions at least 8.5 pt. It describes A's ruled evidence hierarchy, B's generous principal-value hierarchy and C's vector opening/column rhythm. Preserve native constructors/assets and verify actual pagination/language fit rather than inventing a replacement design system. The full-report path extends the specimen structure with all supplied content.

Prior [A](../../../../output/deloitte-design-proposals/specimens/transaction-valuation/report.pdf), [B](../../../../output/deloitte-design-proposals/specimens/executive-valuation/report.pdf) and [C](../../../../output/deloitte-design-proposals/specimens/editorial-valuation/report.pdf) specimen outputs and their hash-bound reviews document the native system's history. The package records 30 populated and 30 blank specimens. Those records do not select the new report, transfer review to changed bytes or establish its financial truth. Independently judge the three newly generated full native reports, not old layouts or a previous custom-design alternative.

Read the actual [design-reference record](../../../../output/deloitte-design-proposals/references/design-reference-record.md) when available. It records public-reference inspection on 3 October 2026:

- [CFO Guide to Tech Trends 2026](https://www.deloitte.com/content/dam/assets-zone3/us/en/docs/services/finance-transformation/2026/cfo-guide-to-tech-trends-2026.pdf): the record reports cover/page 2 inspection, portrait hierarchy, measured leading, structured commentary and embedded Open Sans variants.
- [M&A Trends Pulse Survey 2026](https://www.deloitte.com/content/dam/assets-zone3/us/en/docs/services/merger-and-acquisitions/2026/2026-ma-trends-pulse-survey.pdf): the record reports cover/page 4 inspection, a green-led opening and labelled exhibits.
- The record also identifies the [public wordmark SVG](https://www.deloitte.com/content/dam/assets-shared/logos/svg/a-d/deloitte.svg), locally licensed fonts and hashes. Those provenance records do not confer authorization to present another report as Deloitte work.

Supporting palette, pattern artwork and direction names in the collection were authored proposals; reference photographs were not reused. In this workflow, execute the native system with its bundled assets rather than merely borrowing its formatting. Retain actual asset provenance and font licences. The native wordmark/concept presentation must remain distinguishable from a Deloitte-issued opinion or approval; preserve the explicit concept/application boundary and user constraints.

The installed bundle must work from its native scripts/assets without depending on workspace output directories. The links above identify actual authoring sources; if absent after installation, inspect the bundled native source/assets and available sourcebook records, disclose missing reference evidence and do not substitute another generator. Reading an inspection record is not a new visual inspection of its public reference PDFs.

## Eligibility and weighted scoring

Disqualify a candidate with missing/changed material arguments, values or qualifications; misleading chart encodings; clipped/hidden content; unreadable essential text; broken essential references; a material violation of the user's format/template; unsupported approval/brand claims; failed content checks; or a PDF/image/review hash mismatch. Numerical fidelity is to the supplied reviewed or conditional content, not new financial certification. Missing independent coverage makes selection incomplete rather than a presumed pass. Minor preferences do not become disqualifiers.

Score eligible candidates from 0 to 5 per criterion, then compute `sum(weight * raw_score / 5)` out of 100:

| Criterion | Weight | Judge |
| --- | ---: | --- |
| Decision | 25 | Visibility of conclusion, tradeoffs, conditions and supporting evidence |
| Readability | 25 | Reading order, density, navigation, tables and long-report continuity |
| Charts | 20 | Truthful encodings, clear units/labels, useful comparisons and evidence linkage |
| Typography | 20 | Hierarchy, spacing, legibility, language/font coverage and page rhythm |
| Genre | 10 | Fit to the requested report type, audience, tone and user constraints |

When the content legitimately has no charts, judge figure/exhibit treatment and whether the absence suits the task; do not reward invented charts. Document that interpretation, consistently across candidates. Give page/exhibit evidence for scores and distinguish subjective preferences from observable defects.

## Blind independent scoring prompt

Dispatch to a reviewer who did not author the competing reports. Give opaque labels and the same reviewed native input/model-review basis, all three actual full PDFs and PDF-page images, rendered HTML, retention/layout checks and a hash manifest. Remove author preference, previous scores, A/B/C labels and suggested winner from the handoff where feasible. Preserve financial content and native concept status; record unavoidable visual identity cues. A different model name alone does not establish independence.

```text
Independently select the strongest of THREE newly generated complete native reports
for the supplied audience,
decision, genre, language and format constraints. You did not author these designs.
Candidates have opaque labels; no preferred winner is supplied.

Read the common reviewed native input, model-review basis, manifests and checks.
Inspect every actual PDF page of all THREE full candidates; inspect rendered HTML
where the requested deliverable depends on it. Record exact inspected paths/hashes
and page coverage. Do not infer inspection from a contact sheet or passing bounds.
Treat the supplied financial/domain review basis and conditional wording as retained
content; do not independently approve its economics or upgrade its review status.

First test disqualifiers: material content/value/qualification change or omission,
misleading chart encoding, clipping/hidden content, unreadable essential text,
broken essential references, violated user format/template, unsupported approval or
brand claims, failed content checks, or artifact/review hash mismatch. State each
finding with candidate, page/exhibit, severity, evidence and needed correction.
Do not award an eligible verdict when inspection coverage is incomplete.

For eligible candidates score 0–5 each: decision 25%, readability 25%, charts 20%,
typography 20%, genre 10%. Use sum(weight * score / 5) for the total out of 100.
If there are legitimately no charts, apply the same documented exhibit-treatment
interpretation to all three. Give concise artifact-based reasons, strengths, weaknesses
and the tradeoff behind the selection. Preserve ties when evidence does not separate
them. If all fail, return no selection and concrete bounded revision priorities.
Compare only these three current native outputs; no old-design comparison is asked.

Return reviewer identity/independence, coverage, artifact and native-input hashes,
disqualifiers/findings, scorecards, total, selected opaque label or no-selection,
limitations and model metadata. Distinguish requested model/effort from observed
model/effort supplied by the runtime; mark unavailable observed fields unknown.
Do not claim partner signoff, brand certification, financial correctness or an
inspection/model invocation that did not occur.
```

Request the highest capable available model and reasoning effort through the actual review tool. If `gpt-6-astra`/`ultra` is available and supported, it is suitable; otherwise discover the highest supported option and record the fallback. Capture actual invocation and response metadata as described in [workflow.md](workflow.md). Availability, a declared request and an observed execution are separate facts. Do not fabricate a high-reasoning independent verdict when the channel is absent.
