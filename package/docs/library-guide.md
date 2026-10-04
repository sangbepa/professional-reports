# Professional reports library guide

The four reusable libraries are **orchestrations**, **personas**, **skills**, and **runtimes**. Each has a `library.json` catalog definition and individually pinned component folders. This development version is `0.1.0-dev.1`; components are provisional. Content existence, schema checks and deterministic calculations do not establish production quality.

The entry skill is `skills/professional-reports/SKILL.md`. It bootstraps an **installed pinned release**, loads the meta policy and selected domain, and delegates method execution to actual native Codex agents through the deterministic engine. The engine, installation state, protected evaluations and report adapters are maintained separately from these libraries.

## Ownership and resolution

| Library | Owns | Does not establish |
| --- | --- | --- |
| `libraries/orchestrations/` | Mandate-specific planning, domain contracts, conditional machine rules, stable identities and review boundaries | Actual inference, live source truth or production approval |
| `libraries/personas/` | Expert behavior, blind spots, role-specific artifacts and challenge expectations | Tool access, professional credentials or independent identity by a name alone |
| `libraries/skills/` | Reusable substantive procedures, contracts, small necessary resources and provenance | Data subscriptions, unperformed checks or authority to change criteria |
| `libraries/runtimes/` | Native agent handshake, concurrency and setting provenance | A simulated model service or a replacement state ledger |

Every component includes `component.json` with globally unique `id`, singular `kind`, `version`, `status`, `description`, `capabilities`, `requires` and a component-relative `entrypoint`. Dependency ids in `requires` identify required components; executable plans must resolve the actual components to exact `{id, version, sha256}` references. No symbolic latest reference or guessed hash is acceptable.

Use `pr.registry.Registry(root).reference(id)` and `resolve(ref)` from the installed engine for actual pins. The registry hashes canonical relative file membership and file contents; do not substitute a hash of `component.json` alone. The library catalogs are discovery metadata, not component references. Resolve references again when loading a pinned release and reject mutations. Do not change installed component bytes in place.

## Available domains and decision boundaries

`meta-orchestrator` supplies the general planning policy. Load it as a bootstrap, then select the actual domain for `meta.selected`; the meta component itself is planning-only and must not be selected as a report-mode domain. Its stable-ID policy preserves semantic identities across revisions and separates node ids from engine-issued attempt identities.

`valuation` contains company-sensitive method and evidence contracts. Financial segments require equity methods and capital/funding analysis when material; industrial FCFF and group debt cannot be applied indiscriminately. Consolidation perimeter, NCI, associates, leases, share-class economic rights and double counting are explicit policy concerns. DCF and comparable analysis are available capabilities, not a mandatory paired pipeline.

`fdd`, `esg`, `market-research`, and `investment-memo` are **planning-only** in this release. They can return decision scope, questions, source/data requests, proposed analysis, review responsibilities and capability gaps. Their presence does not authorize a completed diligence opinion, assurance conclusion, market report or investment recommendation. A future implementation must add real domain capabilities and pass the applicable engine-owned evaluation profile before promising execution.

Machine plan rules have the main engine's simple shape:

```json
{
  "rules": [
    {
      "id": "example-financial-segment",
      "when": {"fact": "financial_segment_material", "equals": true},
      "require_capabilities": ["financial-equity-valuation", "segment-reconciliation"],
      "on_unknown": "assessment"
    }
  ]
}
```

Rules may also include `require_review_roles` and `require_artifacts`. Conditions use `when.fact` and `when.equals`; semantic qualifications live in Markdown. Plans hold facts as true, false or null. Null requires evidence or a declared assessment task plus `applicability_assessments[rule_id]` with `status: pending`, that task id, reason and evidence, followed by a versioned fact/plan update; it is not false. Required capabilities must be declared on plan nodes and supplied by their pinned skills. Persona expertise alone cannot satisfy a capability rule. Required artifact names must occur in node outputs, and review roles use engine-supported values.

The actual plan schema uses `expert` for the persona reference, `skills` for an array of skill references, `runtime` for the runtime reference, and `reasoning` for requested effort. A node's `basis` must identify a real clause in the pinned component's Markdown, supporting facts and a reason. Use the installed schema rather than converting conceptual contract terms into invented wire fields.


## Skill contract preservation

Before registering a node, read every bound skill's `contract.json`. The union of its `acceptance` (or `validations`) IDs must be included in `node.required_checks`; its `consumes` must be included in `node.consumes`; and its `outputs` must be included in `node.outputs`. Preserve domain rule output names too. Multiple skills may share a physical output packet, but every declared output type must remain represented in the submission, with distinct artifact names and precise section/key locators where needed. A domain alias does not silently replace a required skill output type. Bind fewer skills when their full contracts are unnecessary; never remove checks just to simplify a node. Only actual observed checks can pass. Unperformed or unsupported required work remains failed/not-run or a capability gap.

## Twelve expert personas

| Component id | Accountability |
| --- | --- |
| `project-manager` | Scope, plan dependencies, capability gaps and revision routing |
| `evidence-researcher` | Original sources, exact locators, dates and evidence gaps |
| `source-critic` | Provenance, availability at cutoff and source entailment |
| `accounting-reconciler` | Periods, units, consolidation, segment bridges and double counting |
| `finance-analyst` | Economic model, appropriate valuation methods and reproducible assumptions |
| `industry-specialist` | Business drivers, cycle position and comparable economics |
| `investment-challenger` | Credible alternatives, counterevidence and decision consequences |
| `report-writer` | Supported arguments, qualifications and quantitative bindings |
| `design-editor` | Approved design reuse and actual rendered-page fidelity |
| `supervisor` | Independent scoped review, findings and defensible closure |
| `valuation-specialist` | Enterprise/equity methods, adjustments and assumption accountability |
| `runtime-engineer` | Capability resolution, preparation and actual smoke tests |

A role can be reused across tasks. Twelve personas do not imply twelve workers or that each report must use every persona. Review independence attaches to the actual host agent and artifact authorship. A producer renamed “supervisor” is still the producer. If the supervisor revises an artifact, another independent reviewer must review that revision.

## Reusable skill components

The component inventory covers the following operations; bind only those relevant to the mandate:

- Framing and research: `report-frame`, `report-research-plan`, `financial-report-research`, `report-source-assess`, `report-evidence-extract`, `valuation-evidence`.
- Reconciliation and valuation: `report-data-reconcile`, `valuation-design`, `financial-equity-valuation`, `valuation-wacc`, `dcf-model`, `comps-analysis`, `audit-xls`, `valuation-challenge`.
- Reasoning and expression: `report-findings`, `report-argument`, `report-outline`, `report-section-write`, `financial-report-writing`, `valuation-compose`.
- Claim and design handoff: `report-claim-check`, `report-design`.

Each method keeps its `SKILL.md`, method contract and necessary references under its component directory. Read its provenance and execution-boundary records before claiming a local executable or external capability. The financial-equity skill has a separate identity so a plan cannot satisfy a financial-segment requirement with an industrial DCF label alone.

## CLI and actual native execution

Run `python3 -m pr --help` from the installed release root or use the installed `professional-reports` executable. **Exact command `--help` is authoritative.** Supply request JSON files using that command's documented syntax. This table describes intent, not invented flags or positional arguments.

| Command | Operation |
| --- | --- |
| `load` | Resolve installed release and its component pins |
| `run` | Start/open authorized run state with current mandate and cutoff |
| `meta` | Validate/register agent-authored domain selection and scope |
| `plan` | Validate/register agent-authored graph, references, basis and machine rules |
| `dispatch` | Prepare/select a ready node and issue its immutable work brief/attempt |
| `bind` | Bind actual native host agent id/receipt to the dispatch |
| `submit` | Validate and record actual result artifacts and observed checks |
| `review` | Record the actual independent reviewer result against current bindings |
| `status` | Inspect current state, work readiness and unresolved issues |
| `export` | Export permitted current plan, execution and evidence artifacts |

Read the pinned `codex-native/RUNTIME.md` before dispatch. Register actual source and approved-design snapshots first through the installed `source`/`snapshot` operations; mandate references alone do not establish ready inputs. Final quality evaluation and `finish` are separate from ordinary review and `export`, and remain subject to the protected evaluator's calibration gate. Invoke actual native `spawn_agent`, retain the real returned agent id, bind it, wait for its completion, and submit its actual files and observations. The runtime specifies discovered tool names and a concrete host call example. Engine scripts never simulate agent inference. A brief is not a result, and a result is not an independent review.

Omit a model override to inherit the current session model. Allocate medium effort to bounded extraction/formatting, high to reconciliation and supported argument work, and xhigh to material economic judgment and independent review, subject to host support. Keep requested, resolved and observed settings separate; unavailable telemetry remains null. A sent option proves only a request. Keep at most six live subagents across the run, including timed-out workers that remain active, and obey any lower confirmed host/user/session limit. One observed spawn rejection occurred with multiple live and nested agents; the exact global limit was not established. Unknown host capacity must be probed and scheduled conservatively.

## Criteria, review and existing design

Acceptance criteria changes require explicit human approval with old/new criteria, reason, consequences and affected work. Preserve the active criteria until that evidence is bound. Ordinary analytical revisions within approved criteria may proceed, but agents cannot waive failed checks, delete a difficult criterion or alter protected evaluations to obtain a pass.

Reviews distinguish source, model, judgment and document coverage. Record the actual independent reviewer, inspected current hashes, observations, issue-level findings and disposition. Structural validation, source fidelity, arithmetic correctness, economic adequacy, native workbook recalculation and visual inspection are different checks. Authors cannot fabricate review closure. Material open findings limit or block release according to the approved criteria.

Reuse the user's existing `approveddesign` reference and measured assets/hashes. Do not restart style selection for content changes. Re-render and inspect the new output. Missing approved assets, a missing renderer or an untested native application is an explicit unresolved capability, not proof of delivery quality.

## Adaptation, examples and limitations

The skills adapt the local `valuation-workbench/skills` methods and installed `dcf-model`, `comps-analysis`, and `audit-xls` instructions. Component provenance records identify actual sources and retained resources without depending on an author's absolute checkout path. Necessary generic instructions are local to each component; large renderer/font bundles and proprietary data connectors are not duplicated as a shortcut. Per-component capability gaps identify required external adapters or tools.

Versioned few-shot cases are labeled **DEVELOPMENT**. They illustrate decisions, branch selection, missing evidence and escalation. They are not hidden-test answers, passing reviewer reports, real financial figures or production evaluation evidence. Engine-owned `protected/evaluations` is outside this implementation's write scope; these libraries do not create or weaken those profiles.

The library does not bundle market-data access, credentials, native spreadsheet recalculation, all report renderers or effective-effort telemetry. Probe these capabilities in the installed environment. Installed release resolution, CLI lifecycle enforcement, protected evaluation and report-adapter execution remain integration responsibilities of the main engine. A development library's successful structural check must be reported as such.

The protected `valuation-v1` evaluator is provisional and blocks final completion pending calibration. This library implementation does not change that status. The native bridge's real agent-id/receipt-hash host attestation provides cooperating-process integrity, not cryptographic identity. The five-prompt author forward check is recorded separately in `library-forward-check.json`; it is not an independent evaluation.

## Delivered file inventory and verification

See `../libraries/inventory.json` for the exact library file list and current component references, and `../libraries/skills/inventory.json` for per-skill resources and dependency metadata. The delivered catalog contains 39 components: six orchestrations (including meta), ten personas, 22 skills and one native runtime. The four `library.json` files define the reusable library categories. The entry skill and five-prompt author selfcheck live outside those component folders at the paths listed in the inventory.

Observed checks: the actual `python3 -m pr catalog` command resolves all 39 components; registry roundtrips, local references, capability coverage and author-path checks pass. The domain development checker exercises 13 positive/negative cases against the main engine, including skill acceptance/consumes/outputs preservation. The entry skill passes the skill-creator validator. These are structural/development checks. Actual report production, renderer execution, native workbook recalculation, calibrated final quality acceptance and completed independent financial review were not performed by this library implementation.
