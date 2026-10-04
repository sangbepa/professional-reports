# Task-scoped sessions

Use the pinned runtime's [session-policy.json](../libraries/runtimes/codex-native/session-policy.json), version `0.2.0-dev.1`. This operational contract distinguishes helper validation from native enforcement; JSON alone does not configure the host. Inspect installed schemas and discovered host tool signatures before writing requests. See [native-handoff.md](native-handoff.md) for the binding sequence.

## Lifecycle and boundaries

Assign one bounded task and scope to each fresh native worker. Every spawn explicitly uses `fork_context=false` and inherits the user's model. Bind the actual spawn receipt to the immutable dispatch attempt before accepting results. Continue an active worker only for the same task with unchanged frozen inputs. New work, changed inputs or a completed worker require a fresh attempt and actor; never resume a completed worker for new tasks.

Preserve outputs and actual host evidence, call the actual close tool, and record its successful close receipt. Wait completion, an engine release, timeout or an intended close is not observed closure. Preserve failed/unknown close results and reconcile capacity rather than declaring the slot free. Keep at most six live workers, or the lower confirmed host/user limit, including timed-out and unconfirmed closures.

Meta-Orchestrator, Project Manager, coordination and integration work use separate task-scoped main-role sessions with explicit input/output packets. A role name, local session ID or ledger event does not reset the actual parent conversation. If the host cannot provide a fresh role session, record that limitation; keep the real parent usage and intake time. Never create user-facing chats as a substitute for native workers.

## Observations and compact evidence

| Measure | Action or bound |
| --- | --- |
| Observed native tool calls: 10 | Prepare scoped handoff |
| Observed native tool calls: 15, or last-input tokens: 100,000 | Hand off to a fresh worker |
| Exact delivered prompt | At most 8,000 characters |
| Handoff summary | At most 1,000 characters |
| Tool-output summary/selected fields | At most 4,000 characters |
| Image inspection | At most 2 images per batch, 5 pages per session |

Call/token thresholds are observational guidance, not native tool-enforced caps. Count actual session calls including follow-ups; do not reset at a dispatch batch. Last-input tokens are the latest observed input, not cumulative tokens. Missing telemetry remains unknown. Helpers can validate local character and image plans without enforcing native usage.

Persist complete raw tool output before producing a summary or selecting fields, even when compact-view validation fails. Preserve immutable path, SHA-256, version and explicit one-based inclusive text read ranges. A summary is a navigation aid, never replacement evidence. Narrow reads by referenced ranges; do not silently truncate the original or dump the global ledger into the next worker's prompt.

## Handoffs and independent review

Use the installed `task-handoff/1` schema and session helpers where available. Include task ID/scope, predecessor session and destination attempt, compact summary, relevant inputs/artifacts, open findings, closed findings, accepted judgments, observed checks, next actions and no-reread references. Keep each item within the assigned scope and link its evidence to packet references. Preserve current hashes and acceptance conditions; omit unrelated decisions and full conversation history. Keep resolution details in referenced evidence if the schema has no dedicated field.

Each round gets a fresh independent reviewer, separate from all producers of the target. Give it the current target hashes, unchanged criteria, necessary originals and scoped finding/decision history, without a desired verdict. Submit its actual output before recording review. Prior reviewer IDs remain provenance; do not retain or resume the original reviewer merely to obtain closure.

For every finding, preserve a stable ID, affected scope, original evidence, current artifact hashes, proposed change, actual independent checks and explicit disposition. Closure requires evidence that this finding is resolved on the current target, plus the actual reviewer/round identity. A general pass does not silently close all findings. Producers may propose resolutions but cannot approve their own closures.

Carry forward unchanged accepted judgments with their evidence and conditions, and closed findings with closure evidence. No-reread applies only while hashes, versions, dependencies, scope and acceptance conditions remain unchanged. Real counterevidence, changed dependencies or demonstrated invalid closure permits targeted rereading and reopening. Record the original finding/decision ID, reopening reason, counterevidence locator/hash, affected scope, independent reviewer and resulting disposition; retain prior history. Do not reopen merely because the new reviewer prefers another style, or suppress valid counterevidence to protect a metric.

If a pinned older engine requires the original reviewer identity or lacks the necessary resolution fields, report the compatibility gap. Preserve the new review evidence and use a compatible release for future runs; never edit old bindings/ledgers or claim unsupported closure.

## Document inspection

Render the complete first document and actually inspect every page across fresh sessions, with at most two images per batch and five pages per session. Save a full ordered page/hash manifest and actual inspection evidence per page. A manifest or planned image call is not proof of inspection. For revisions, compare complete manifests and inspect changed pages plus affected neighbors, pagination, references and shared layout dependencies. Record removed pages and coverage justification; uncertain impact requires full inspection. Session limits never justify omitting pages.

## Measurement and release

Follow [report-speed.md](report-speed.md) for report deadlines and the bounded comparison experiment; use [performance-profiler.md](performance-profiler.md) for diagnostics. Separate logical task-session counters from actual parent telemetry. Unknown measurements cannot establish success, and neither fewer tokens nor fresh sessions waive independent review or protected quality gates.
