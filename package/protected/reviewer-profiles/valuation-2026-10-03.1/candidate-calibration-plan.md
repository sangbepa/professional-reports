# Candidate reviewer and calibration plan

Status: **CANDIDATE - explicit user approval of the exact hashed version is required before protected adoption.** No calibration has been run by this review. This file proposes future work; it does not assign benchmark, company, release or system scores.

## Contract to preserve

The only scored axes remain `evidence`, `economics`, `calculation`, `decision_usefulness`, `document_quality`. Each receives an integer 0-4. Passing requires **each axis >=3 and total >=17/20**. There is no 100-point conversion, criterion weighting, axis waiver, rounding-up rule, or compensation for a failed axis. Consequently, five 3s do not pass. The 14 existing rubric criteria can supply review questions within those axes. Existing protected gates and independent-review requirements remain unchanged.

The proposed 25 examples in `candidate-five-axis-anchors.json` are behavioural anchors. Lower levels describe constructed failure modes; they are not retrospective grades for KPMG, Grant Thornton or Deloitte. A source's reputation does not establish a score of 4. A reviewer signature alone also does not establish 4: the work must demonstrate stronger, independently challenged support. Independent review completion is separately recorded.

## People, workers and configuration

For an eventual report run, use four real independent reviewer actors, separate from its author: evidence; economics; calculation; decision and document. The last role must be competent to assess both argument and the rendered document, or obtain documented specialist help. Four labels emitted by one actor do not satisfy this arrangement. A reviewer can use several methods; methods are not worker identities. These roles implement a candidate arrangement consistent with the four reviews described in `docs/evaluation.md`; compatibility with actual protected contracts must be checked by an authorised adopter, not inferred by this review.

Human reference judgments are **optional additional calibration evidence when available**, not a prerequisite, minimum-person gate or part of the immutable scoring contract. If available, record their provenance, relevant expertise, mandate familiarity, conflicts, actual scope and disagreements, then measure agreement with them. There is no required human count. Source-anchored independent reviewer calibration can proceed without human labels, with human-comparison metrics marked unavailable and no claim of human-validated grading. No human panel participated in this review. The present review is one Codex session, independent of the existing extraction/rubric authoring in this turn; it is not a four-worker review or a professional credential claim.

The concrete initial proposal is **requested model `inherit-current`, requested reasoning `high`**. Resolved and observed model/reasoning remain null until actually available. Compare `high` with supported `xhigh` and `max` settings during calibration on the same frozen source-backed packets and unchanged five-axis contract; record unsupported settings without silently substituting. Compare substantive findings, disagreements, stability and resource cost, then freeze the user-approved choice and exact configuration hash. No comparison or approval has occurred here.

Pin source pack, candidate output, actual resolved model and prompts by exact version/hash. Record requested, resolved and observed model/reasoning separately; do not invent backend observations. Record sampling settings or `not_supported`, tools and versions, context and tool budgets, actual pages opened/rendered, failed attempts and incomplete reviews. The candidate config is disabled and calibration results remain null. The requested settings above are testable proposals, not observed execution settings.

Reviewers receive the mandate, cutoff, frozen outputs/models, available originals and limitations. They do not receive the candidate's identity, change intent, another reviewer's initial grades, or protected answer keys. Source identity remains visible where required to verify provenance. First judgments must be independent. An independent adjudicator with appropriate task competence, agent or human, resolves pass/fail disagreements, differences above one point on an axis and any material unresolved finding against the original evidence. This does not require a human panel. Do not average disagreement away.

## Stage A: validate what the anchors mean

1. Review the three original evidence groups with the exact locators and SHA-256s in `source-anchors.json`. Test the observed features, private-information boundaries and whether the proposed 2/3 and 3/4 distinctions are understandable. Preserve dissent and reasons. Do not require all three reports to be full-score exemplars.
2. Correct the extraction gaps before using a text-only reviewer. In particular, transcribe and independently verify the relevant B02 figures, complete the omitted 7.4 sentence, and retain original page images and printed/PDF pagination. A render is evidence access, not independent numeric validation by itself.
3. Present the 25 proposed examples without a score to genuine independent reviewers. Compare their evidence-based judgments with the proposed levels; revise ambiguous anchors in development. If human judgments are available, add that comparison separately. Changes create a new candidate version and invalidate previous calibration for the changed configuration. Agreement between agents alone is not proof of professional validity.
4. Keep derived examples from a given source in the same partition. A rewritten extract from SG Fleet is not independent of SG Fleet. All B01-B03 originals, this review and its examples are exposed development material.

## Stage B: development trials on complete report packets

Use source-backed reports and their actual model/evidence/render packs, not only isolated arithmetic puzzles. Include appropriate partial/abstaining outputs as well as unconditional conclusions; an honest limitation may be excellent conduct but does not turn an incomplete full-valuation mandate into a completed report.

Use both intact and deliberately degraded packets, including:

| Axis | Boundary that must be tested |
|---|---|
| evidence | Genuine citation with incomplete extraction; private forecast presented as public; contradictory source retained versus hidden; statement date versus availability |
| economics | Cyclical EOL income; deliveries versus orders; funding advance rates; finite-life residual resources; ownership/control and coherent reinvestment |
| calculation | Correct arithmetic with wrong units/perimeter; double-counted debt; real/nominal mismatch; diluted shares; rounding versus an unresolved discrepancy |
| decision_usefulness | Strong analysis without a conclusion test; a plausible contrary case; dependence between cross-checks; missing scrip evidence; a scenario that reverses the decision |
| document_quality | Polished but analytically empty output; omitted graphic information; misleading units/signs; source-note loss; dense but readable exhibits; final summary/body inconsistency |

Make important errors subtle enough to test professional discrimination. Include near-boundary examples around scores 2/3 and 3/4 and around total 16/17, retaining the per-axis minimum. Include correct reports that lack private information but use a legitimate public-data mandate and restricted conclusions. Do not punish honest access disclosure or reward invented private work.

Use pairs that change one material feature to diagnose score sensitivity, but do not treat pairs or multiple pages from one report as statistically independent mandates. Render the full candidate documents in the format ultimately delivered. Record outcomes for failures, aborts and budget exhaustion; never exclude them from assigned-case accounting. No Stage B cases were executed here.

## Stage C: independent calibration and evaluation

A separate evaluation owner selects fresh, source-disjoint reports after the development configuration is frozen. Development authors must not see the protected cases' expected answers. This proposal neither creates nor reads holdout answers. Extend beyond the three Australian transaction opinions before claiming broad expert-report generalisation. For FDD, ESG, earnings or board work, first obtain purpose-matched primary examples and acceptance evidence under the same five axes; the present examples do not calibrate those purposes.

Candidate measurements, all to be approved before running:

- Required contract remains the unchanged axes, scale, thresholds, genuine review and approval boundaries. The following measurement design is a candidate proposal, not an added immutable gate. Measure per-axis inter-reviewer agreement, evidence-grounded discrepancy detection, repeatability and source-adjudicated case outcomes; distinguish agreement from validity and record how reference judgments were established.
- **When human judgments are available**, additionally measure per-axis exact agreement, within-one agreement and ordinal weighted kappa against those judgments, with distributions, sample counts and disagreement/adjudication records. Where multiple human judgments exist, human-human agreement can also be measured. Suggested investigation targets are >=80% exact and weighted kappa >=0.70 on each axis; these are optional comparison targets, not measured results, mandatory human gates or evidence-derived industry standards. Without human data these metrics are unavailable, not zero or failed.
- False passes and false failures against independently established reference decisions under the **unchanged** five-axis/17-point rule may be measured with counts and confidence intervals; identify whether references are source-adjudicated agent judgments or optional human judgments. Where no defensible reference exists, report unresolved disagreement rather than invent an error rate. Report critical false passes separately. A missed fabrication, material financing mismatch or unsupported unconditional conclusion prevents a claim that the tested configuration has resolved that substantive defect; this limit does not impose a human-label prerequisite.
- Agreement near the 2/3 and 16/17 boundaries; source/sector/purpose breakdowns; prompt-order effects; repeatability with fixed configuration; resource cost and completion rate. Three repeated ratings of one packet measure repeatability, not three new professional cases.
- Preserve both first judgments and adjudication. Unexpected disagreement is evidence about the rubric, not an invitation to relax passing thresholds.

Preregister the desired precision and size the independent sample accordingly. For an **optional human-reference comparison only**, zero false passes in 30 genuinely independent human-fail packets gives a one-sided 95% exact binomial upper bound of approximately 9.5% (`1 - 0.05**(1/30)`). Thirty successes, repeated ratings, or 30 correlated variants would not supply that denominator. An equivalent calculation can be made against defensible non-human reference judgments but must identify that different reference basis. This is a statistical illustration, not a required sample size, human-label prerequisite or claim that 30 covers every axis, sector or rare failure mode. Stratification and observed disagreement may require more. A small pilot can identify defects while remaining insufficient for broad professional-validity claims.

The existing **24 arithmetic/cutoff fixtures**, as described in the request, may test mechanics. They supply no professional report scores, expert reference judgments, layout assessment or meaningful estimate of these calibration measures. Their contents and outputs were not read or rerun here. No zero-error rate, kappa, validity, or calibration result is inferred from them.

## Adoption boundary

After defects are resolved, freeze the final anchor/config/calibration evidence versions. A separate authorised adopter checks compatibility with protected requirements, presents the concrete hashes and measured results to the user, and obtains explicit approval before touching protected files. Approval of this proposal would not itself establish calibration or approve a company valuation. A later change to examples, prompt, model, tool setup, case mixture or decision rules requires a new version and appropriately scoped recalibration. None of these adoption actions is performed here.
