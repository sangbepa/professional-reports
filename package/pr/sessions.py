"""Task-scoped native sessions and evidence pointers.

Native budgets are observations, never claims of host enforcement. Receipts are
caller-supplied host envelopes: we validate consistency, not authenticity. Ranges
are inclusive, one-based text lines; page numbers are one-based.
"""
from __future__ import annotations

import copy
import functools
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

from .schema import validate
from .util import (ContractError, canonical, digest, hash_data, identifier,
                   immutable_json, lock, now, read_json, timestamp)

DEFAULTS = MappingProxyType(dict(soft_calls=10, handoff_calls=15,
    last_input_tokens=100000, prompt_chars=8000, summary_chars=1000,
    tool_summary_chars=4000, images_per_batch=2, pages_per_session=5))
__all__ = ["DEFAULTS", "session_policy", "observe_limits", "spawn_request",
    "validate_prompt", "file_reference", "safe_read", "persist_output",
    "build_handoff", "validate_handoff", "record_handoff", "record_session", "close_session",
    "read_closure",
    "read_session", "page_manifest", "image_change_impact"]


def _text(value, limit, name):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ContractError(f"{name} must contain 1..{limit} characters")
    return value


def session_policy():
    return dict(DEFAULTS, native_enforcement="observational")


def observe_limits(*, calls, last_input_tokens):
    for value in (calls, last_input_tokens):
        if type(value) is not int or value < 0:
            raise ContractError("Usage observations must be nonnegative integers")
    return dict(native_enforcement="observational", soft_limit=calls >= DEFAULTS['soft_calls'],
                handoff_recommended=(calls >= DEFAULTS['handoff_calls'] or
                                     last_input_tokens >= DEFAULTS['last_input_tokens']),
                calls=calls, last_input_tokens=last_input_tokens)


def validate_prompt(prompt):
    return _text(prompt, DEFAULTS['prompt_chars'], "Exact delivered prompt")


def spawn_request(prompt, *, reasoning_effort="inherit"):
    """Return exact native arguments; no execution or fabricated spawn receipt."""
    validate_prompt(prompt)
    _text(reasoning_effort, 64, "reasoning_effort")
    request = dict(message=prompt, fork_context=False)
    if reasoning_effort != "inherit":
        request['reasoning_effort'] = reasoning_effort
    return request


def _path(root, relative, *, exists=True):
    root = Path(root).resolve()
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ContractError("Expected a relative path inside the evidence root")
    candidate = root / p
    for parent in (candidate, *candidate.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise ContractError("Redirected evidence paths are not allowed")
    if not candidate.resolve().is_relative_to(root):
        raise ContractError("Path escapes evidence root")
    if exists and not candidate.is_file():
        raise ContractError(f"Evidence file missing: {relative}")
    return candidate


def _ranges(ranges, count):
    if not isinstance(ranges, list):
        raise ContractError("read_ranges must be a list")
    end = 0
    for r in ranges:
        if (not isinstance(r, dict) or set(r) != {'start', 'end'} or
                type(r['start']) is not int or type(r['end']) is not int or
                not end < r['start'] <= r['end'] <= count):
            raise ContractError("Invalid, overlapping or unordered read ranges")
        end = r['end']


def file_reference(root, path, *, version, read_ranges=None):
    _text(version, 128, "version")
    source = _path(root, path)
    ranges = copy.deepcopy(read_ranges if read_ranges is not None else [])
    try:
        count = len(source.read_bytes().decode('utf-8').splitlines()) if ranges else 0
    except UnicodeError as exc:
        raise ContractError("Text read ranges require UTF-8 evidence") from exc
    _ranges(ranges, count)
    return dict(path=Path(path).as_posix(), sha256=digest(source), version=version,
                read_ranges=ranges)


def _reference(root, ref):
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256', 'version', 'read_ranges'}:
        raise ContractError("Expected path/hash/version/read_ranges reference")
    current = file_reference(root, ref['path'], version=ref['version'],
                             read_ranges=ref['read_ranges'])
    if current != ref:
        raise ContractError("Evidence hash or path mismatch")
    return current


def safe_read(root, reference, *, max_chars=4000):
    """Read only explicitly selected ranges; never silently truncate evidence."""
    if type(max_chars) is not int or not 1 <= max_chars <= DEFAULTS['tool_summary_chars']:
        raise ContractError("Invalid read bound")
    _reference(root, reference)
    if not reference['read_ranges']:
        raise ContractError("Explicit read ranges are required")
    raw = _path(root, reference['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference['sha256']:
        raise ContractError("Evidence changed during read")
    try:
        lines = raw.decode('utf-8').splitlines(keepends=True)
    except UnicodeError as exc:
        raise ContractError("Evidence is not UTF-8 text") from exc
    text = ''.join(''.join(lines[r['start']-1:r['end']]) for r in reference['read_ranges'])
    if len(text) > max_chars:
        raise ContractError("Selected read exceeds bound; choose smaller ranges")
    return dict(text=text, reference=copy.deepcopy(reference))


def persist_output(root, path, raw_text, *, version, summary=None, selected_fields=None):
    """Save all raw UTF-8 bytes FIRST, even if the requested compact view fails.

    Exactly one explicit summary or JSON top-level field selection is required.
    Existing files are never overwritten; exceptions never return partial views.
    """
    if not isinstance(raw_text, str):
        raise ContractError("Raw output must be text")
    dest = _path(root, path, exists=False)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as f:
        f.write(raw_text.encode('utf-8'))
    ref = file_reference(root, path, version=version,
        read_ranges=[dict(start=1, end=len(raw_text.splitlines()))] if raw_text else [])
    if (summary is None) == (selected_fields is None):
        raise ContractError("Supply exactly one explicit summary or field selection; raw output saved")
    if summary is not None:
        view = dict(summary=_text(summary, DEFAULTS['tool_summary_chars'], "Tool summary"))
    else:
        if (not isinstance(selected_fields, list) or not selected_fields or
                any(not isinstance(k, str) for k in selected_fields) or
                len(set(selected_fields)) != len(selected_fields)):
            raise ContractError("Select unique JSON field names")
        try:
            data = json.loads(raw_text)
            if not isinstance(data, dict):
                raise ContractError("Field selection requires a JSON object")
            fields = {k: data[k] for k in selected_fields}
            if len(canonical(fields)) > DEFAULTS['tool_summary_chars']:
                raise ContractError("Selected fields exceed tool summary bound")
        except (ValueError, KeyError) as exc:
            raise ContractError(f"Cannot select fields; raw output saved: {exc}") from exc
        view = dict(selected_fields=fields)
    return dict(view, raw=ref, view_kind="explicit_summary" if summary is not None else "selected_fields")


def validate_handoff(root, handoff, *, task_id, scope):
    """Validate a deliberately selected task packet, never a global ledger dump."""
    data = copy.deepcopy(handoff)
    validate(Path(__file__).resolve().parents[1], 'handoff', data)
    if data['task_id'] != task_id or set(data['scope']) != set(scope):
        raise ContractError("Handoff task/scope mismatch")
    references = data['artifacts'] + data['inputs']
    for ref in references:
        _reference(root, ref)
    ids = {hash_data(ref) for ref in references}
    for ref in data['no_reread_refs']:
        _reference(root, ref)
        if hash_data(ref) not in ids or not ref['read_ranges']:
            raise ContractError("No-reread reference must identify an already read packet input/artifact")
    seen = set()
    for name in ('open_findings', 'closed_findings', 'accepted_judgments', 'checks', 'next_actions'):
        for item in data[name]:
            if not set(item['scope']).issubset(set(scope)):
                raise ContractError("Item outside handoff scope")
            if item['id'] in seen:
                raise ContractError("Duplicate scoped item id")
            seen.add(item['id'])
            for ref in item.get('evidence', []):
                _reference(root, ref)
                if hash_data(ref) not in ids:
                    raise ContractError("Evidence missing from scoped packet references")
    return data


def build_handoff(root, *, task_id, scope, from_session, to_attempt, summary,
                  open_findings=(), closed_findings=(), accepted_judgments=(),
                  artifacts=(), inputs=(), checks=(), next_actions=(), no_reread_refs=()):
    packet = dict(schema_version='task-handoff/1', task_id=task_id, scope=list(scope),
        from_session=from_session, to_attempt=to_attempt, summary=summary,
        open_findings=list(open_findings), closed_findings=list(closed_findings),
        accepted_judgments=list(accepted_judgments), artifacts=list(artifacts),
        inputs=list(inputs), checks=list(checks), next_actions=list(next_actions),
        no_reread_refs=list(no_reread_refs))
    return validate_handoff(root, packet, task_id=task_id, scope=scope)


def _run(run):
    # Import lazily so native can use prompt validation without an import cycle.
    from .native import _run as checked_run
    return checked_run(run)


def _session_transaction(fn):
    @functools.wraps(fn)
    def wrapped(run, *args, **kwargs):
        run = _run(run)
        with lock(run.path / '.sessions.lock'):
            run._assert_open(fn.__name__)
            return fn(run, *args, **kwargs)
    return wrapped


def read_session(run, session_id, *, _seen=None):
    run = _run(run)
    identifier(session_id)
    seen = set() if _seen is None else set(_seen)
    if session_id in seen:
        raise ContractError("Cyclic session predecessor")
    seen.add(session_id)
    record = read_json(_path(run.path, f'sessions/{session_id}.json'))
    original = dict(record)
    claimed = original.pop('sha256')
    if hash_data(original) != claimed or original['run_sha256'] != digest(run.path/'run.json'):
        raise ContractError("Session record integrity failure")
    attempt = run.attempt(original['attempt_id'])
    binding = run.binding(original['attempt_id'])
    if (not binding or original['attempt_sha256'] != hash_data(attempt) or
            original['binding_sha256'] != hash_data(binding) or
            original['agent_id'] != binding['agent_id'] or original['task_id'] != attempt['node_id'] or
            original['session_id'] != session_id or original['policy'] != session_policy()):
        raise ContractError("Session differs from immutable attempt/binding/policy")
    previous = original['predecessor']
    if previous is not None:
        prior = read_session(run, previous['session_id'], _seen=seen)
        if (prior['sha256'] != previous['sha256'] or prior['task_id'] != original['task_id'] or
                prior['agent_id'] == original['agent_id']):
            raise ContractError("Session predecessor differs from frozen reference")
    return record


@_session_transaction
def record_session(run, session_id, attempt_id, *, predecessor=None):
    """Persist actual bound identity; no model calls, guessed IDs or close claims."""
    run = _run(run)
    identifier(session_id)
    attempt = run._current(attempt_id, {'running'})
    binding = run.binding(attempt_id)
    if not binding or binding['provider'] != 'codex-native':
        raise ContractError("Session requires an actual native binding")
    previous = None
    if predecessor is not None:
        prior = read_session(run, predecessor)
        if prior['task_id'] != attempt['node_id'] or prior['agent_id'] == binding['agent_id']:
            raise ContractError("Predecessor must be the same task and a different native actor")
        previous = dict(session_id=predecessor, sha256=prior['sha256'])
    for path in (run.path/'sessions').glob('*.json'):
        if read_session(run, path.stem)['attempt_id'] == attempt_id:
            raise ContractError("Attempt already has a session")
    record = dict(session_id=session_id, attempt_id=attempt_id, task_id=attempt['node_id'],
        agent_id=binding['agent_id'], run_sha256=digest(run.path/'run.json'),
        attempt_sha256=hash_data(attempt), binding_sha256=hash_data(binding),
        predecessor=previous, policy=session_policy(), created_at=now())
    record['sha256'] = hash_data(record)
    immutable_json(_path(run.path, f'sessions/{session_id}.json', exists=False), record)
    return record


@_session_transaction
def close_session(run, session_id, receipt):
    """Record observed closure only from an explicit successful close receipt.

    A completed result or a wait response is not evidence of a close call.
    The caller supplies the actual host envelope; no receipt is synthesized.
    """
    run = _run(run)
    session = read_session(run, session_id)
    r = copy.deepcopy(receipt)
    if not isinstance(r, dict) or r.get('tool') not in {
            'multi_agent_v1.close_agent', 'multi_agent_v1__close_agent'}:
        raise ContractError("Actual native close receipt required")
    timestamp(r.get('captured_at'))
    response = r.get('response')
    actor = session['agent_id']
    if (r.get('agent_id') != actor or not isinstance(response, dict) or
            not isinstance(r.get('request', {}), dict) or
            r.get('request', {}).get('agent_id', actor) != actor):
        raise ContractError("Close receipt identity mismatch")
    for part in (r, response):
        if (any(part.get(k) for k in ('error', 'errors', 'isError', 'timed_out')) or
                part.get('success') is False or part.get('status') in ('failed', 'error', 'errored')):
            raise ContractError("Failed native close receipt")
    status = response.get('status')
    previous = response.get('previous_status')
    previous_confirmed = (previous in ('completed', 'shutdown', 'running', 'pending_init') or
                          isinstance(previous, dict) and bool({'completed', 'errored'} & set(previous)))
    confirmed = response.get('success') is True or status in ('closed', 'shutdown') or previous_confirmed
    if not confirmed or response.get('agent_id', actor) != actor:
        raise ContractError("Close receipt does not confirm closure")
    record = dict(session_id=session_id, session_sha256=session['sha256'], attempt_id=session['attempt_id'],
                  agent_id=actor, observed_closed=True, close_receipt=r, captured_at=now())
    record['sha256'] = hash_data(record)
    immutable_json(_path(run.path, f'session-closures/{session_id}.json', exists=False), record)
    return record


def read_closure(run, session_id):
    """Read a frozen close observation linked to the original session."""
    run = _run(run)
    session = read_session(run, session_id)
    record = read_json(_path(run.path, f'session-closures/{session_id}.json'))
    value = dict(record)
    claimed = value.pop('sha256')
    if (hash_data(value) != claimed or value['session_sha256'] != session['sha256'] or
            value['agent_id'] != session['agent_id'] or value['attempt_id'] != session['attempt_id'] or
            value['session_id'] != session_id or value['observed_closed'] is not True):
        raise ContractError("Close record integrity failure")
    return record


@_session_transaction
def record_handoff(run, handoff):
    """Freeze a packet only for actual predecessor and destination task attempts."""
    run = _run(run)
    prior = read_session(run, handoff['from_session'])
    target = run._current(handoff['to_attempt'], {'running'})
    if target['node_id'] != prior['task_id'] or target['attempt_id'] == prior['attempt_id']:
        raise ContractError("Handoff destination must be a new attempt of the same task")
    packet = validate_handoff(run.path, handoff, task_id=target['node_id'], scope=handoff['scope'])
    record = dict(handoff=packet, predecessor_sha256=prior['sha256'],
                  attempt_sha256=hash_data(target), run_sha256=digest(run.path/'run.json'))
    record['sha256'] = hash_data(record)
    immutable_json(_path(run.path, f"handoffs/{record['sha256']}.json", exists=False), record)
    return record


def page_manifest(root, pages, *, version):
    """Hash every rendered page; caller must supply the complete ordered document."""
    if not isinstance(pages, list) or not pages:
        raise ContractError("Full page list required")
    refs = [file_reference(root, p, version=version) for p in pages]
    if len({r['path'] for r in refs}) != len(refs):
        raise ContractError("Duplicate page path")
    return [dict(page=i, **ref) for i, ref in enumerate(refs, 1)]


def image_change_impact(current, previous=None, *, affected_pages=()):
    """Plan full initial coverage, then changed/explicitly affected pages.

    Batches and sessions respect helper bounds, not claimed native limits.
    Manifest creation/planning is not evidence that images were inspected.
    """
    if not isinstance(current, list) or not current:
        raise ContractError('Complete current page manifest required')
    affected_pages = list(affected_pages)
    for manifest in (current, previous):
        if manifest is None:
            continue
        if not isinstance(manifest, list) or not manifest:
            raise ContractError("Complete page manifest required")
        for i, item in enumerate(manifest, 1):
            if (item.get('page') != i or not isinstance(item.get('sha256'), str) or
                    len(item['sha256']) != 64 or any(c not in '0123456789abcdef' for c in item['sha256'])):
                raise ContractError("Invalid ordered page manifest")
    if any(type(p) is not int or not 1 <= p <= len(current) for p in affected_pages):
        raise ContractError("Invalid affected page")
    old = {p['page']: p for p in previous or []}
    changed = {p['page'] for p in current if old.get(p['page'], {}).get('sha256') != p['sha256']}
    selected = sorted(changed | set(affected_pages))
    sessions = []
    for start in range(0, len(selected), DEFAULTS['pages_per_session']):
        pages = selected[start:start + DEFAULTS['pages_per_session']]
        sessions.append([pages[i:i+DEFAULTS['images_per_batch']] for i in range(0, len(pages), DEFAULTS['images_per_batch'])])
    return dict(first_full_coverage=previous is None, pages=selected,
                removed_pages=sorted(set(old) - {p['page'] for p in current}),
                sessions=sessions, coverage_observed=False, native_enforcement='observational')
