# Component execution boundary

This is a provisional method package. Read `contract.json` for inputs, outputs,
acceptance and failure routing; it describes a method, not a callable AI service.
`component.json` declares only the capabilities this component supplies. A plan
node must explicitly declare its required capabilities and pin every selected
component to the exact `{id, version, sha256}` returned by the registry. `requires`
contains globally unique dependency IDs, resolved and pinned by the runtime.
It is package dependency metadata, not a mandatory sequence or plan-node edge.

Use native host execution only. Do not spawn agents from this skill, simulate a
model call, impersonate reviewers, infer serving-model settings, or read protected
evaluation answers. The host owns dispatch and protected evaluations. A capability
label for an analytical method does not assert access to a source tool, spreadsheet
application, rendering tool, or independent reviewer.

Bind each actual input by ID, artifact location relative to the run root, version,
measured SHA-256 or explicit access limitation, and consumed fields. Begin every
new report attempt with a fresh cutoff and frozen source snapshot; reusing an old
snapshot requires an explicit current eligibility check. Outputs record IDs,
relative locations, versions, input bindings and actual checks. Never write author
machine absolute paths into portable outputs. Preserve current ledger meanings;
map equivalent supplied fields rather than requiring a second data store.

A changed consumed field, source version, criterion, calculation or artifact hash
invalidates affected descendants and their reviews. Return stale bindings before
using them. Changes to accepted evaluation criteria require actual user approval; preserve
existing authorization and do not infer new approval. Keep the criterion diff
and the affected artifacts explicit. Ordinary sensitivity work under the existing
criterion has no blanket user approval gate. Select methods for the economic unit:
DCF and comps are optional tools, never a compulsory pair.

Every operation returns `operation_record` (actual identity/channel evidence,
input/output bindings, checks performed, limitations, status `complete`,
`restricted` or `returned`) and `failure_records`. Each failure identifies the
record, missing evidence/test, decision effect, upstream operation or domain owner,
next action and interim conclusion restriction. Completion is bounded to actual
scope. Author self-check, independent review, approval, source fidelity, arithmetic,
economic adequacy and layout checks are separate facts, never interchangeable.
Missing tools or evidence yield unverified/restricted outputs, not fictional passes.

Source acquisition/browser/PDF OCR tools, authenticated datasets, spreadsheet
native recalculation, workbook rendering, document rendering and independent
review channels are unresolved unless the current run supplies and tests them.
No external integration or production verification is included. References to
current laws/standards or market data require fresh authoritative checks in the
actual engagement. License and provenance records describe inspected local source
snapshots; do not infer rights for external data, branding or unavailable notices.
