# Meta orchestration — 0.1.0-dev.1

This component chooses and coordinates work. The deterministic engine owns release resolution, attempts, bindings, state, review records and export. The meta component is the bootstrap policy, not a selected domain for a report-mode plan. Select the actual domain in `meta.selected`; including this planning-only meta component in a report composition is invalid. Read `contract.json`, `selection-policy.json`, `stable-ids.json`, and the selected domain's contract and plan rules. Read `development-cases.json` only for development examples; it is not an evaluation profile.

## META-FRAME: Frame and compile

1. Bind the actual mandate, reader decision, entity and ownership perimeter, valuation and information dates, currency, desired deliverable and existing approved criteria. Create a fresh cutoff declaration and source snapshot manifest for each report attempt, including deliberate revalidation of any reused source. A prior report is context, not a current source pack.
2. Resolve the installed pinned release and every selected component with the engine registry. Keep the exact `{id, version, sha256}` references. Missing capabilities, changed files, unavailable source access and design resources remain explicit gaps. A persona supplies behavior; it does not supply a tool, subscription or method implementation.
3. Choose a domain. `valuation` supports a contingent research/analysis/review plan. FDD, ESG, market research and investment memo are planning-only profiles at this version: deliver their plans and access gaps, never a completed domain engagement or production report.
4. Establish material company facts from evidence. Preserve `true`, `false` and unknown `null` distinctly. Apply the selected domain's machine plan rules through the engine. Unknown facts require an assessment work unit; a writer cannot default them to false. For each unknown applicable rule, populate `applicability_assessments[rule_id]` with `status: pending`, the actual assessment `task_id`, a nonempty reason and evidence describing the actual gap. The node alone is insufficient. On resolution preserve assessment evidence and a boolean `applies` per installed schema. Recompile after assessment establishes the fact and keep the prior plan revision.
5. Select methods based on business economics, evidence availability and decision. For a financial business, test equity-based methods and regulatory capital constraints; do not force industrial FCFF/WACC. For an industrial issuer, DCF, comparables, asset value or another supported method must each earn inclusion. Adding a second method without comparable economics is not corroboration.
6. Build a DAG whose nodes have concrete inputs, an accountable expert persona, one or more substantive skills, the native runtime, declared capabilities and testable artifacts. Add only real dependencies. Partition independent source work when it reduces latency; keep a reconciliation with its dependent bridge together where necessary. Infeasible branches return a gap and bounded conclusion, not made-up inputs.
7. Bind review ownership, criterion ids and current artifact dependencies before dispatch. Source adequacy, model arithmetic, economic judgment and document fidelity are separate review scopes. A reviewer must be a real independent agent and must not have authored the artifacts under review. One independent reviewer may inspect multiple scopes only with explicit coverage and demonstrated capability.


## Skill contract preservation

Before registering a node, read every bound skill's `contract.json`. The union of its `acceptance` (or `validations`) IDs must be included in `node.required_checks`; its `consumes` must be included in `node.consumes`; and its `outputs` must be included in `node.outputs`. Preserve domain rule output names too. Multiple skills may share a physical output packet, but every declared output type must remain represented in the submission, with distinct artifact names and precise section/key locators where needed. A domain alias does not silently replace a required skill output type. Bind fewer skills when their full contracts are unnecessary; never remove checks just to simplify a node. Only actual observed checks can pass. Unperformed or unsupported required work remains failed/not-run or a capability gap.

## META-SELECT: Reuse, compose or return a precise gap

Use the installed meta schema and `selection-policy.json` to choose `reuse`, `compose`, `candidate`, `clarify` or `capability-gap`. Reuse exactly one domain when it covers the reader decision and requested mode. Composition requires at least two useful domains and a shared contract: assign every responsibility, align scope/perimeter/currency/cutoff, define actual artifact handoffs and resolve conflicts before registration. A planning-only member prevents a report-mode composition; composition is not a capability upgrade.

If the mandate is materially ambiguous, return the smallest necessary clarification and continue independent evidence work. If the mandate is clear but support is missing, return the exact capability gap and its consequence. A candidate orchestration is a development proposal with a version and review needs, never a silent edit of the installed release or evaluation criteria. Record rejected alternatives and why they would not support the decision. Choose an evaluation profile for the mandate, never to improve a failing score.

## META-DISPATCH: Allocate and execute

Use `codex-native/reasoning-policy.json` for requested effort and host scheduling. Read only the node's pinned persona, skill and resources. Dispatch ready independent work through the engine and actual native host tools. At most six child agents may be live; ten personas are reusable roles, not ten simultaneous workers. The project manager owns sequencing and issue routing; specialist agents own their output; the supervisor checks the current evidence and conclusions without rewriting a target and then self-approving it.

No local script simulates a model response. A dispatched brief, running agent, submitted artifact and accepted review are distinct facts. Preserve actual agent ids, attempt identities, observed tool results and requested/resolved/observed reasoning settings. Use the runtime runbook for binding and result submission.

## META-CRITERIA: Revise without moving the goalposts

A material finding names a responsible node, affected claim or calculation, current artifact hashes, severity, consequence and proposed remedy. Route it back to the evidence, accounting, model, argument or design owner. Changes invalidate dependent analysis, prose and reviews. Keep revisions and earlier failed attempts; stale results cannot satisfy a new attempt.

Changing a method or assumption is ordinary analysis when it stays within the approved mandate and acceptance criteria. Changing a criterion, threshold, required review, scope acceptance, waiver or conclusion standard requires explicit human approval. Submit a concrete old/new criteria diff, rationale, material effect and affected work; keep existing criteria active until approval evidence is bound. Reviewer suggestions, agent agreement and elapsed time are not approval. No skill or persona may edit protected evaluation profiles.

Stop a repeated unchanged failure with a bounded issue report and missing prerequisite. A higher reasoning setting is useful for a harder judgment; it does not produce missing source evidence or close an independent finding.

## META-DELIVER: Build and deliver

Findings support arguments; arguments determine the reader-specific outline and sections. Quantitative claims bind to current model paths and sources. An expression node cannot invent financial assumptions or increase conclusion strength.

If `approveddesign` exists, reuse its actual selected design and assets by measured hash. Do not rerun template competition or reset visual style for a content refresh. Obtain rendering capability, generate the current artifact and inspect its actual pages; a historical design approval does not approve new content. Missing assets or rendering remain explicit limitations.

Export only what the engine's current state permits. Include plan, actual execution state, component pins, evidence/model bindings, performed checks, open issues and supported conclusion limits. A structurally valid package is not automatically a professionally accepted report. Only actual review and engine-owned release criteria determine eligibility.
