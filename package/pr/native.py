"""Deterministic Codex handoff helpers; never execute models or invent actors."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

from .engine import Run
from .package import verify
from .schema import validate
from .sessions import validate_prompt, spawn_request, read_closure
from .util import ContractError, digest, hash_data, identifier, read_json, timestamp

__all__ = ["prepare_binding", "bind_spawn", "prepare_submission", "submit_template",
           "prepare_review", "review_template", "spawn_request"]

BOUND_AGENT = "${BOUND_AGENT_ID}"
SPAWN = "multi_agent_v1.spawn_agent"


def _run(run):
    run = Run(run.path if isinstance(run, Run) else run)
    run._check_pin()
    if Path(__file__).resolve().parent.parent != run.registry.root.resolve():
        raise ContractError("Use python -m pr.native from the run's pinned installed release")
    if verify(run.registry.root)["release_id"] != run.header["release_sha256"]:
        raise ContractError("Installed release differs from run pin")
    return run


def prepare_binding(run, attempt_id, receipt, prompt, *, requested_model="inherit",
                    requested_effort=None):
    """Build a binding from a supplied spawn envelope and exact delivered text.

    The caller attests delivery; this cannot authenticate a host receipt. The
    supported spawn response reports identity, not resolved/observed settings.
    No files or ledger entries are written by preparation functions.
    """
    run = _run(run)
    attempt = run._current(attempt_id, {"running"})
    if run.binding(attempt_id):
        raise ContractError("Attempt already bound")
    receipt = copy.deepcopy(receipt)
    if not isinstance(receipt, dict) or receipt.get("tool") not in {SPAWN, "multi_agent_v1__spawn_agent"}:
        raise ContractError("Unsupported native spawn receipt")
    response = receipt.get("response")
    if not isinstance(response, dict):
        raise ContractError("Expected actual spawn response object")
    for record in (receipt, response):
        if (record.get("success") is False or record.get("error") or record.get("errors")
                or record.get("isError") or record.get("timed_out")
                or record.get("status") in ("failed", "error", "errored")):
            raise ContractError("Failed native spawn receipt")
    actor = response.get("agent_id")
    if not isinstance(actor, str) or not actor.strip() or actor == BOUND_AGENT:
        raise ContractError("Spawn response must report an actual agent_id")
    timestamp(receipt.get("captured_at"))
    validate_prompt(prompt)
    if requested_model != "inherit":
        raise ContractError("Native model must inherit the user model")
    # Read immutable attempt/result/release events, not only current task state.
    terminal = {e['data']['attempt_id'] for e in run.events
                if e['kind'] in {'result_submitted', 'worker_released'}}
    for closed in (run.path / 'session-closures').glob('*.json'):
        terminal.add(read_closure(run, closed.stem)['attempt_id'])
    for prior in terminal - {attempt_id}:
        prior_binding = run.binding(prior)
        if prior_binding and prior_binding['agent_id'] == actor:
            raise ContractError("Completed native actor cannot be reused across attempts")
    effort = requested_effort if requested_effort is not None else attempt["node"]["reasoning"]
    if effort != attempt["node"]["reasoning"]:
        raise ContractError("Reasoning request changed after dispatch")
    if "request" in receipt:
        request = receipt["request"]
        if not isinstance(request, dict) or request.get("message") != prompt or "items" in request:
            raise ContractError("Only exact plain-text spawn message requests are supported")
        if request.get("fork_context", False) is not False:
            raise ContractError("Native spawn requires fork_context=false")
        if request.get("model", "inherit") != requested_model:
            raise ContractError("Requested model differs from host request")
        if request.get("reasoning_effort", "inherit") != effort:
            raise ContractError("Requested effort differs from host request; record inheritance explicitly")
    raw_tool = receipt["tool"]
    receipt["tool"] = SPAWN
    if raw_tool != SPAWN:
        receipt["reported_tool"] = raw_tool
    binding = dict(
        attempt_id=attempt_id, agent_id=actor, provider="codex-native",
        instruction_sha256=hash_data(attempt),
        model=dict(requested=requested_model, resolved=None, observed=None),
        reasoning=dict(requested=effort, resolved=None, observed=None),
        host_receipt=receipt, delivered_prompt=prompt,
        delivered_prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest())
    return validate(run.registry.root, "binding", binding)


def bind_spawn(run, attempt_id, receipt, prompt, **settings):
    """Prepare and persist through Run.bind, retaining the original receipt."""
    run = _run(run)
    return run.bind(prepare_binding(run, attempt_id, receipt, prompt, **settings))


def _workdir(run, attempt_id, statuses):
    identifier(attempt_id)
    run._current(attempt_id, statuses)
    work = run.path / "work" / attempt_id
    if work.resolve() != work or not work.is_dir():
        raise ContractError("Attempt work directory is missing or redirected")
    return work


def _file(work, value):
    path = Path(value)
    resolved = (work / path).resolve()
    if ".." in path.parts or not resolved.is_relative_to(work) or not resolved.is_file():
        raise ContractError("File must exist inside the attempt work directory")
    return resolved


def _template(work, template):
    data = copy.deepcopy(template) if isinstance(template, dict) else read_json(_file(work, template))
    if not isinstance(data, dict):
        raise ContractError("Template must be a JSON object")
    return data


def _identity(data, field, actual, *, actor=False):
    supplied = data.get(field)
    if supplied is not None and supplied != actual and not (actor and supplied == BOUND_AGENT):
        raise ContractError(f"Template {field} differs from current binding/attempt")
    data[field] = actual


def _actor(run, attempt_id):
    binding = run.binding(attempt_id)
    if not binding or binding["provider"] != "codex-native":
        raise ContractError("Attempt needs a current native binding")
    return binding["agent_id"]


def prepare_submission(run, attempt_id, template):
    """Copy a worker template, bind identity and check all paths/hashes first."""
    run = _run(run)
    work = _workdir(run, attempt_id, {"running"})
    result = _template(work, template)
    _identity(result, "attempt_id", attempt_id)
    _identity(result, "agent_id", _actor(run, attempt_id), actor=True)
    validate(run.registry.root, "result", result)
    for artifact in result["artifacts"]:
        source = _file(work, artifact["path"])
        if "sha256" in artifact and artifact["sha256"] != digest(source):
            raise ContractError(f"Artifact sha256 mismatch: {artifact['name']}")
        artifact["path"] = str(source)
    return result


def submit_template(run, attempt_id, template):
    """Submit a prepared copy through Run; never overwrite the template."""
    run = _run(run)
    return run.submit(prepare_submission(run, attempt_id, template))


def prepare_review(run, reviewer_attempt_id, template):
    """Bind a review only after its independent reviewer's result exists."""
    run = _run(run)
    work = _workdir(run, reviewer_attempt_id, {"verified", "review_pending"})
    actor = _actor(run, reviewer_attempt_id)
    result = run._artifacts_intact(reviewer_attempt_id)
    if result["agent_id"] != actor:
        raise ContractError("Reviewer result author differs from binding")
    review = _template(work, template)
    _identity(review, "review_task_attempt", reviewer_attempt_id)
    _identity(review, "reviewer_agent_id", actor, actor=True)
    validate(run.registry.root, "review", review)
    run._current(review["attempt_id"], {"review_pending", "verified", "needs_revision"})
    if _actor(run, review["attempt_id"]) == actor:
        raise ContractError("Review requires a separate bound actor")
    return review


def review_template(run, reviewer_attempt_id, template):
    """Record through Run.review, preserving target hashes and reviewer verdict."""
    run = _run(run)
    return run.review(prepare_review(run, reviewer_attempt_id, template))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("bind", "submit", "review"):
        command = commands.add_parser(name)
        command.add_argument("--run", required=True)
        command.add_argument("--attempt", required=True)
        if name == "bind":
            command.add_argument("--receipt", required=True)
            command.add_argument("--prompt", required=True)
            command.add_argument("--requested-model", default="inherit")
            command.add_argument("--requested-effort")
        else:
            command.add_argument("--template", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "bind":
            result = bind_spawn(args.run, args.attempt, read_json(args.receipt),
                                Path(args.prompt).read_bytes().decode("utf-8"),
                                requested_model=args.requested_model,
                                requested_effort=args.requested_effort)
        else:
            helper = submit_template if args.command == "submit" else review_template
            result = helper(args.run, args.attempt, args.template)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps(dict(error=type(exc).__name__, message=str(exc))), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
