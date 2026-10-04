# Native Codex handoff

`pr.native` is a deterministic helper module for an already-dispatched attempt.
It exports `prepare_binding`, `bind_spawn`, `prepare_submission`,
`submit_template`, `prepare_review`, and `review_template`. Import these from
`pr.native`; the main package CLI and engine are unchanged. Preparation returns
a new dictionary without writing files or the ledger. The three action helpers
delegate persistence and final contract checks to `Run.bind`, `Run.submit`, and
`Run.review`. Each accepts a Run instance or a run directory path and reloads it.

This module does not execute models, dispatch tasks, invent worker identities,
infer success from a template, or certify report quality. Receipt authenticity
and faithful prompt delivery remain host attestations. Synthetic tests exercise
contracts, not model performance, independent judgment, or financial quality.

## Select the pinned installed release

For a new run, use the existing `professional-reports load --state /absolute/state`
command and record its release hash. For an existing run, its `run.json` is the
authority; the currently active release may differ. Select its executable:

```sh
RUN=/absolute/state/runs/example
PINNED=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["package_root"])' "$RUN/run.json")
# Use a Python environment with that release's pinned requirements installed.
PYTHON=$(command -v python3)
cd "$PINNED"
"$PYTHON" "$PINNED/professional-reports" verify --release "$PINNED"
"$PYTHON" -m pr.native --help
```

Use absolute paths for the run, receipt, prompt, support and dispatch output.
Run subsequent module commands from this pinned directory. Do not import the
helper from a checkout via `PYTHONPATH`. It checks the existing Run code pin,
its own installation path, and the verified release hash before preparation or
mutation. Different source code, changed releases and changed loaded engines
are rejected, including an identical copy imported from another directory.
It does not silently switch interpreters or releases.

The run's installed release must already contain `pr/native.py`. Package and
install a new release through the normal release workflow for future runs;
never copy this file into an immutable existing installation or rewrite a run
pin. Older runs must continue using their original release's existing commands.

## Actual host tool order

1. In the pinned executable, dispatch the ready task using the actual supported
   capabilities and reasoning settings:

   ```sh
   "$PYTHON" "$PINNED/professional-reports" dispatch --run "$RUN" \
     --node worker-node --support /absolute/support.json --out /absolute/brief.json
   ```

   Retain the returned `attempt_id`, `brief_sha256` and `result_directory`.
   Compose and save the exact UTF-8 text to be delivered to the worker. Include
   the dispatched brief/instructions and work directory, plus directions to
   produce the submission template and artifacts there.

2. In Codex, call the actual `multi_agent_v1.spawn_agent` tool (exposed to the
   orchestration bridge as `tools.multi_agent_v1__spawn_agent`) with that exact
   text as `message` (at most 8,000 characters) and `fork_context=false`.
   Inherit the user's model by omitting `model` or using supported `inherit`;
   pass the planned `reasoning_effort` explicitly.
   Save the actual tool response and capture timestamp immediately, with the
   exact request arguments, including `fork_context=false`. A successful response has the shape
   `{ "agent_id": "<host-returned-id>", "nickname": null }`; the nickname may
   also be a string. This is a shape illustration, not a usable receipt.

3. Bind before waiting or submitting. Save this envelope with the untouched
   response object; substitute only real observed values:

   ```json
   {
     "tool": "multi_agent_v1.spawn_agent",
     "captured_at": "<actual timezone-qualified capture timestamp>",
     "request": {"message": "<exact delivered text>", "fork_context": false, "reasoning_effort": "high"},
     "response": {"agent_id": "<actual host-returned ID>", "nickname": null}
   }
   ```

   ```sh
   "$PYTHON" -m pr.native bind --run "$RUN" --attempt "$ATTEMPT" \
     --receipt /absolute/spawn-receipt.json --prompt /absolute/delivered-prompt.txt \
     --requested-model inherit --requested-effort high
   ```

   Set `ATTEMPT` to the dispatched ID. The receipt's response supplies the actor;
   there is no actor override. Both dotted and bridge tool names are accepted,
   with the reported alias retained. Unsupported tools, missing actors, error
   receipts, changed prompt/request settings and already-bound attempts fail.
   Only plain `message` calls are supported when request arguments are retained;
   structured `items` need a future explicit contract. The optional `request`
   object permits checking the delivered text and settings; without it, the
   caller attests those supplied values. Never pass an error response as success.

4. Use Codex's actual `multi_agent_v1.wait_agent` on the returned agent ID.
   A timeout is not completion. After the worker completes and its files exist,
   use `submit` below. Host errors still need the existing failure/release
   workflow; this helper does not manufacture completion or free capacity.

5. Once the target result exists, dispatch a fresh independent reviewer each round with the
   target in its dependencies. Spawn and bind that reviewer in the same order,
   then wait for its actual completion. Submit the reviewer's own result through
   `submit` first. Only then call `review` with the reviewer's attempt ID and its
   completed review template. Run enforces the assigned role, independent actor,
   dependency snapshot and exact target artifact hashes. Record per-finding
   resolution/reopening evidence; the original reviewer ID is historical, not
   required for later independent closure.

6. Preserve results and raw receipts, actually call the host close tool, then
   retain its successful receipt (using installed session helpers when available).
   Wait completion, ledger release and a written summary do not prove closure.
   Completed workers never resume for new tasks. Failed or unknown close calls
   leave closure unconfirmed and must not silently free host capacity.

The binding retains `delivered_prompt` and its SHA-256 over exact UTF-8 bytes,
including whitespace and CRLF. `instruction_sha256` remains the dispatched
brief's canonical hash; it is a different object. The supported host response
does not establish actual model or effort: both `resolved` and `observed` remain
JSON `null`. `requested` records the supplied request, with model defaulting to
`inherit` and effort defaulting to the dispatched plan. A retained host request
must agree; an omitted host effort is inheritance, not evidence of an explicit
`high` request. Additional response metadata is preserved without interpreting
it as verified execution settings. The prompt file must contain the actual
delivered text, not a later reconstruction or hidden reasoning.

## Worker and reviewer templates

```python
from pr.native import bind_spawn, submit_template, review_template

binding = bind_spawn(run_path, attempt_id, actual_receipt, exact_prompt,
                     requested_model="inherit", requested_effort="high")
result = submit_template(run_path, attempt_id, "submission.json")
# After separate reviewer binding, completion and result submission:
status = review_template(run_path, reviewer_attempt_id, "review.json")
```

The worker uses the existing result schema. It may omit `attempt_id` and
`agent_id`, use `null`, or use the explicit `${BOUND_AGENT_ID}` actor placeholder.
An already populated identity must equal the current binding; another actor or
attempt is rejected, never silently replaced. Example submission shape:

```json
{
  "agent_id": "${BOUND_AGENT_ID}",
  "artifacts": [{"name": "report", "type": "report", "path": "report.txt"}],
  "checks": [{"id": "required-check-id", "passed": true, "evidence": "<actual evidence>"}],
  "summary": "<worker's actual summary>",
  "usage": null
}
```

The actual artifact types and checks must match the dispatched plan. Optional
artifact `sha256` must match the existing file; a present null or incorrect hash
fails. No check, verdict, summary or usage value is generated by the helper.

```sh
"$PYTHON" -m pr.native submit --run "$RUN" --attempt "$ATTEMPT" --template submission.json
"$PYTHON" -m pr.native review --run "$RUN" --attempt "$REVIEW_ATTEMPT" --template review.json
```

Review templates use the existing review schema. Only `review_task_attempt` and
`reviewer_agent_id` may be omitted/null (the actor placeholder also works).
`attempt_id` must identify the target, and `targets` must preserve the actual
frozen artifact names and hashes. Verdicts, scope, evidence and findings must
come from the reviewer. Reviewer artifacts are checked for integrity before
binding the review template, and a separate bound author is required.

Relative template and artifact paths resolve from the relevant attempt's work
directory, never the current directory. Absolute paths are allowed only inside
that work directory. Parent traversal, outward symlinks, redirected work
directories and missing files fail. Preparation validates all artifact paths
and declared hashes before submission. This follows Run's cooperating-local-
process boundary; it is not protection against a hostile concurrent filesystem
writer. Mapping templates are deep-copied and template files are only read.
The CLI prints the resulting binding/submission/review status as JSON; errors
go to stderr with exit code 2. Do not redirect stdout over original templates.

## Targeted validation

From the source package, with its dependencies available:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_native.py -v
```

Fixtures are explicitly synthetic, including the positive real-format spawn
response fixture. Tests create/install a temporary package from public code and
schemas with synthetic policies, then execute the helper in fresh interpreters
from that pinned release. They do not invoke a model or read protected holdouts.

## Task-scoped session contract

Read [session-workflow.md](session-workflow.md) for scoped handoffs and the runtime's versioned `session-policy.json` for limits. Every new worker uses `fork_context=false`; keep exact actual request arguments with its spawn receipt. An older helper's tolerance for omitted request fields does not establish that isolation was observed. Use fresh attempts/actors for new tasks and completed workers, including reviewers.

Prepare at 10 observed calls; hand off at 15 or 100,000 last-input tokens. These native thresholds are observational, not tool-enforced caps. Persist complete raw outputs before returning a tool summary (at most 4,000 characters); handoff summaries are at most 1,000 characters. Preserve hash/version/range references. Never label the continuing parent conversation as reset.
