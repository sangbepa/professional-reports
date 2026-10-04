# Provisional expert personas

Version: `0.1.0-dev.1`. All ten components are provisional native-agent behavioral definitions. Their stable IDs are the directory names; `kind` is singular `persona`; `requires` is initially `[]`. Each `ROLE.md` is a relative, component-local entrypoint and includes inputs, substantive methods, output boundaries, review authority, blindspots, and advisory skill IDs.

Each component carries `reasoning-guidance.json` and `development-cases.json` inside its own content-hash boundary. The reasoning file distinguishes requested instructions, resolved host configuration, and observed execution metadata; it inherits the host/session model. Central runtime policy owns max6 and effort allocation. These files neither schedule agents nor implement result-envelope validation.

The DEVELOPMENT files contain hypothetical input/expected-behavior pairs. They have not been executed, contain no numeric answer keys or heldout answers, and are not independent reviews, approval decisions, benchmark scores, or production-verification evidence. Protected evaluations belong outside candidate-owned libraries; none are authored here.

Independent review requires producer/reviewer separation supported by actual provenance. Source, arithmetic, economics, and design coverage must be recorded separately. Criterion weakening requires explicit human authorization. The design editor preserves the exact user-supplied approveddesign reference and hash while rerendering new content, with a separate output identity and actual page-inspection scope.

## Components

- `project-manager`: Frames the mandate and coordinates plans, dependencies, expert handoffs, and blockers without granting review approval.
- `evidence-researcher`: Acquires decision-relevant original evidence with provenance, exact locators, and explicit collection gaps.
- `source-critic`: Challenges provenance, information timing, authority, and coverage of evidence independently from its collection.
- `accounting-reconciler`: Builds traceable bridges across accounting definitions, periods, currencies, and entity perimeters.
- `finance-analyst`: Designs reproducible valuation methods, operating scenarios, and value bridges consistent with supplied evidence.
- `industry-specialist`: Tests business-driver explanations against industry structure, cycles, competitive behavior, and operating constraints.
- `investment-challenger`: Challenges investment conclusions through competing hypotheses, downside mechanisms, and explicit judgment limits.
- `report-writer`: Writes decision-oriented report prose from accepted evidence and analysis while preserving qualifiers and traceability.
- `design-editor`: Preserves a user-supplied approved design while rerendering current report content and inspecting the actual rendered pages.
- `supervisor`: Reviews exact artifact revisions independently from their producers across separately evidenced source, arithmetic, economics, and design channels.

## Integration limits

Skill IDs are advisory intended handoffs, not declared installed dependencies; resolve them through the actual registry before use. No host dispatch, rendering, model execution, actual review, or production release is established by these definitions. Behavioral constraints require enforcement by the central runtime and evidence-based review. If engine requirements conflict with the documented metadata or string-ID dependency contract, report the conflict rather than changing the contract silently.

The main orchestration ID is `meta-orchestrator` and the runtime ID is `codex-native`. These are routing hints; actual component references must be exactly `{id, version, sha256}` obtained from registry membership and bytes. Protected evaluations and release authority remain main-owned. The central plan and binding schemas govern wire formats and review routing; persona channel descriptions do not extend their enums.
