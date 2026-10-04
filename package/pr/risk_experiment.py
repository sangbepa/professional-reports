"""File-only risk_review experiment records; never dispatches or activates anything.

Local cooperating writers, not cryptographic authentication. An agent MUST NOT
call adopt without explicit human adoption of the exact registration bundle.
"""
from copy import deepcopy
from decimal import Decimal
import math
from pathlib import Path

from .util import ContractError, canonical, digest, hash_data, identifier, immutable_json, lock, now, read_json

INPUT_CAP = 6_000_000
SECONDS_CAP = 1800
PAIRS = [1, 2, 3]
METRICS = ('input', 'cached', 'uncached', 'elapsed')
QUALITY = ('major_misses', 'unsupported_major', 'minor_detected',
           'unjustified_reopens', 'unsupported_reversals', 'false_positives')


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _number(value, name, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or value < 0 or (integer and not isinstance(value, int))):
        raise ContractError('Invalid observed metric: ' + name)
    return value


def _path(value):
    if not isinstance(value, str) or not Path(value).is_absolute() or not Path(value).is_file():
        raise ContractError('Referenced file must exist at an absolute path')
    return Path(value)


def _snapshot(value, snapshots, expected=None):
    path = _path(value)
    data = path.read_bytes()
    from hashlib import sha256
    sha = sha256(data).hexdigest()
    if expected is not None and (not _sha(expected) or sha != expected):
        raise ContractError('Referenced file hash mismatch: ' + value)
    if value in snapshots and snapshots[value][0] != sha:
        raise ContractError('Referenced bytes changed while collecting: ' + value)
    snapshots[value] = (sha, data)
    return data


def _references(value, snapshots):
    """Explicit JSON references: path/*_path, evidence_ref and absolute hash maps.

    Follow referenced JSON transitively, including relative paths (rejected).
    URLs and source descriptions are provenance, not local file references.
    """
    if isinstance(value, list):
        for item in value:
            _references(item, snapshots)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key == 'path' or key.endswith('_path') or key == 'evidence_ref':
                if item is None or item == '':
                    continue
                if key == 'evidence_ref' and isinstance(item, str) and not Path(item).is_file():
                    continue  # Preserve a missing evidence reference as incomplete.
                fresh = item not in snapshots if isinstance(item, str) else True
                data = _snapshot(item, snapshots, value.get('sha256') if key in {'path', 'evidence_ref'} else None)
                if fresh and Path(item).suffix.lower() == '.json':
                    import json
                    try:
                        _references(json.loads(data), snapshots)
                    except (ValueError, UnicodeError) as exc:
                        raise ContractError('Invalid referenced JSON') from exc
            elif isinstance(key, str) and Path(key).is_absolute() and isinstance(item, str):
                fresh = key not in snapshots
                data = _snapshot(key, snapshots, item)
                if fresh and Path(key).suffix.lower() == '.json':
                    import json
                    _references(json.loads(data), snapshots)
            else:
                _references(item, snapshots)


def _store_objects(folder, snapshots):
    frozen = {}
    for source, (sha, data) in snapshots.items():
        target = folder / 'objects' / sha
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if digest(target) != sha:
                raise ContractError('Frozen object mutated')
        else:
            with target.open('xb') as stream:
                stream.write(data)
        frozen[source] = dict(sha256=sha, frozen_path='objects/' + sha)
    return frozen


def preregister(folder, spec):
    """Freeze the complete proposed bundle before any experiment calls.

    fixture_manifest must contain nonempty public/private hash collections:
    either {absolute_path: sha256}, or [{path: absolute_path, sha256: ...}].
    Private labels stay private; registration is not a candidate worker packet.
    """
    spec = deepcopy(spec)
    canonical(spec)  # No executable callbacks, NaN, or opaque objects.
    identifier(spec.get('id'))
    if spec.get('mode', 'risk_review') != 'risk_review':
        raise ContractError('Only risk_review records are supported')
    if spec.get('pairs', PAIRS) != PAIRS or any(type(x) is not int for x in spec.get('pairs', PAIRS)):
        raise ContractError('Exactly pairs 1, 2, 3 must be frozen')
    if spec.get('budget', dict(input=INPUT_CAP, seconds=SECONDS_CAP)) != dict(input=INPUT_CAP, seconds=SECONDS_CAP):
        raise ContractError('Budget is fixed at 6M input and 1800 seconds')
    for key in ('profile_path', 'criteria_path', 'fixture_manifest_path', 'reviewer_config_path'):
        _path(spec.get(key))
    protected = spec.get('protected_baseline')
    if not isinstance(protected, dict) or not protected:
        raise ContractError('Protected baseline path->sha256 is required')
    snapshots = {}
    _references(spec, snapshots)
    manifest = read_json(spec['fixture_manifest_path'])
    for visibility in ('public', 'private'):
        collection = manifest.get(visibility)
        if not isinstance(collection, (dict, list)) or not collection:
            raise ContractError('Public and private fixture hashes are required')
        entries = collection.items() if isinstance(collection, dict) else (
            (entry.get('path'), entry.get('sha256')) for entry in collection if isinstance(entry, dict))
        entries = list(entries)
        if len(entries) != len(collection):
            raise ContractError('Invalid fixture manifest entry')
        for path, sha in entries:
            _snapshot(path, snapshots, sha)
    for path, sha in protected.items():
        _snapshot(path, snapshots, sha)
    spec.update(mode='risk_review', pairs=PAIRS, budget=dict(input=INPUT_CAP, seconds=SECONDS_CAP))
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    frozen = _store_objects(folder, snapshots)
    immutable_json(folder / 'spec.json', spec)
    registration = dict(version=1, registered_at=now(), status='experimental_candidate',
                        adoption_status='pending', spec_sha256=hash_data(spec), frozen=frozen,
                        pairs=PAIRS, budget=spec['budget'])
    registration['adoption_sha256'] = hash_data(registration)
    immutable_json(folder / 'registration.json', registration)
    return registration


def _check_frozen(folder, references):
    for source, record in references.items():
        relative = record.get('frozen_path')
        if relative != 'objects/' + record['sha256'] or not _sha(record['sha256']):
            raise ContractError('Invalid frozen file binding')
        target = folder / relative
        if target.is_symlink() or not target.is_file() or digest(target) != record['sha256']:
            raise ContractError('Frozen bytes mutated: ' + source)
        if not Path(source).is_file() or digest(source) != record['sha256']:
            raise ContractError('Referenced source mutated: ' + source)


def _registration(folder):
    registration = read_json(folder / 'registration.json')
    unsigned = {k: v for k, v in registration.items() if k != 'adoption_sha256'}
    if hash_data(unsigned) != registration.get('adoption_sha256'):
        raise ContractError('Registration mutated')
    spec = read_json(folder / 'spec.json')
    if hash_data(spec) != registration['spec_sha256']:
        raise ContractError('Specification mutated')
    if registration['pairs'] != PAIRS or registration['budget'] != dict(input=INPUT_CAP, seconds=SECONDS_CAP):
        raise ContractError('Frozen assignment or budget mutated')
    _check_frozen(folder, registration['frozen'])
    return registration, spec


def _adoption_receipt(receipt, registration):
    if (not isinstance(receipt, dict) or receipt.get('kind') != 'human-approval' or
            receipt.get('bundle_sha256') != registration['adoption_sha256'] or
            not isinstance(receipt.get('user_message_reference'), str) or
            not receipt['user_message_reference'].strip()):
        raise ContractError('Explicit human adoption must reference exact registration hash and user message')
    if 'actual_user_message' in receipt and (
            not isinstance(receipt['actual_user_message'], str) or not receipt['actual_user_message'].strip()):
        raise ContractError('Actual user message, when supplied, must be nonempty')


def _record(folder, name, payload, snapshots):
    frozen = _store_objects(folder, snapshots)
    body = dict(payload=payload, frozen=frozen)
    immutable_json(folder / name, dict(body, record_sha256=hash_data(body)))


def _read_record(folder, path):
    record = read_json(path)
    body = {k: v for k, v in record.items() if k != 'record_sha256'}
    if hash_data(body) != record.get('record_sha256'):
        raise ContractError('Observed record mutated')
    _check_frozen(folder, record['frozen'])
    return record['payload']


def adopt(folder, receipt):
    """Record consent only after a HUMAN explicitly adopts this exact bundle.

    This validates a local record, not the origin or meaning of a human message.
    Implementation authorization and quality callbacks cannot authorize adoption.
    """
    folder = Path(folder)
    receipt = deepcopy(receipt)
    canonical(receipt)
    with lock(folder / '.lock'):
        registration, spec = _registration(folder)
        _adoption_receipt(receipt, registration)
        target = folder / 'adoption.json'
        if target.exists():
            if _read_record(folder, target) != receipt:
                raise ContractError('Conflicting adoption receipt')
            return receipt
        snapshots = {}
        _references(receipt, snapshots)
        _budget([spec, receipt])
        _record(folder, 'adoption.json', receipt, snapshots)
    return receipt


def _metrics(arm):
    metrics = arm.get('metrics')
    if not isinstance(metrics, dict):
        return None
    for key in METRICS:
        if metrics.get(key) is not None:
            _number(metrics[key], key, key != 'elapsed')
    if any(metrics.get(k) is None for k in METRICS):
        return None
    if metrics['input'] != metrics['cached'] + metrics['uncached']:
        raise ContractError('Input must equal cached plus uncached')
    return metrics


def _native(receipts):
    if not isinstance(receipts, list) or not receipts:
        return False
    return all(isinstance(r, dict) and
               any(isinstance(r.get(k), str) and r[k].strip() for k in ('agent_id', 'response_id')) and
               isinstance(r.get('evidence_ref'), str) and Path(r['evidence_ref']).is_absolute() and
               Path(r['evidence_ref']).is_file() for r in receipts)


def _arm_complete(arm, producers):
    if not isinstance(arm, dict):
        return False
    metrics = _metrics(arm)
    quality = arm.get('quality', {})
    if not isinstance(quality, dict):
        return False
    for key in QUALITY:
        if quality.get(key) is not None:
            _number(quality[key], key, True)
    if quality.get('minor_detected', 0) > 8:
        raise ContractError('Known minor count cannot exceed eight')
    grading = arm.get('grading')
    return bool(metrics is not None and all(quality.get(k) is not None for k in QUALITY) and
                _native(arm.get('native_receipts')) and isinstance(arm.get('author_agent_id'), str) and
                arm['author_agent_id'].strip() and
                any(r.get('agent_id') == arm['author_agent_id'] for r in arm['native_receipts']) and
                isinstance(grading, dict) and _native(grading.get('native_receipts')) and
                isinstance(grading.get('reviewer_agent_id'), str) and grading['reviewer_agent_id'].strip() and
                grading['reviewer_agent_id'] not in producers and
                any(r.get('agent_id') == grading['reviewer_agent_id'] for r in grading['native_receipts']) and
                isinstance(grading.get('evidence_ref'), str) and Path(grading['evidence_ref']).is_absolute() and
                Path(grading['evidence_ref']).is_file() and
                _sha(grading.get('artifact_sha256')) and _sha(arm.get('artifact_sha256')) and
                grading['artifact_sha256'] == arm['artifact_sha256'])


def _pair_complete(pair):
    producers = {a.get('author_agent_id') for a in (pair.get('baseline', {}), pair.get('candidate', {}))
                 if isinstance(a, dict) and isinstance(a.get('author_agent_id'), str)}
    checks = [_arm_complete(pair.get(side), producers) for side in ('baseline', 'candidate')]
    return all(checks) and pair.get('status', 'complete') == 'complete'


def _budget(records):
    """Disjoint per-event receipts, never add arm totals again or sum worker clocks.

    Full-scope coverage cannot be verified by this file manager. Overall totals
    remain unknown; known receipts are lower bounds, with observed stop signals.
    """
    seen, receipts = {}, {}
    for record in records:
        events = record.get('scope_events', [])
        if not isinstance(events, list):
            raise ContractError('scope_events must be a list')
        for event in events:
            if not isinstance(event, dict):
                raise ContractError('Invalid scope event')
            identifier(event.get('event_id'))
            if not _native(event.get('native_receipts')) or not event.get('scope'):
                raise ContractError('Actual scope event requires native receipt and scope')
            _metrics(event)
            if isinstance(event.get('metrics'), dict) and event['metrics'].get('output') is not None:
                _number(event['metrics']['output'], 'output', True)
            if event.get('observed_elapsed_seconds') is not None:
                _number(event['observed_elapsed_seconds'], 'observed_elapsed_seconds')
            key = event['event_id']
            if key in seen and seen[key] != event:
                raise ContractError('Conflicting duplicate scope event')
            for receipt in event['native_receipts']:
                identity = receipt.get('response_id') or (receipt.get('agent_id'), receipt['evidence_ref'])
                if identity in receipts and receipts[identity] != key:
                    raise ContractError('Native scope receipt counted under multiple event IDs')
                receipts[identity] = key
            seen[key] = event
    observed = {k: sum(e.get('metrics', {}).get(k) or 0 for e in seen.values() if isinstance(e.get('metrics'), dict))
                for k in ('input', 'cached', 'uncached')}
    outputs = [e['metrics'].get('output') if isinstance(e.get('metrics'), dict) else None for e in seen.values()]
    output = sum(outputs) if outputs and all(v is not None for v in outputs) else None
    clocks = [e['observed_elapsed_seconds'] for e in seen.values() if e.get('observed_elapsed_seconds') is not None]
    elapsed = max(clocks) if clocks else None
    stopped = observed['input'] >= INPUT_CAP or (elapsed is not None and elapsed >= SECONDS_CAP)
    return dict(input_cap=INPUT_CAP, seconds_cap=SECONDS_CAP, measurement_complete=False,
                input_tokens=None, total_tokens=None, elapsed_seconds=None,
                observed_input_tokens=observed['input'] if any(isinstance(e.get('metrics'), dict) and e['metrics'].get('input') is not None for e in seen.values()) else None,
                observed_cached_input_tokens=observed['cached'] if any(isinstance(e.get('metrics'), dict) and e['metrics'].get('cached') is not None for e in seen.values()) else None,
                observed_uncached_input_tokens=observed['uncached'] if any(isinstance(e.get('metrics'), dict) and e['metrics'].get('uncached') is not None for e in seen.values()) else None,
                observed_output_tokens=output,
                observed_input_plus_output_tokens=observed['input'] + output if output is not None and
                any(isinstance(e.get('metrics'), dict) and e['metrics'].get('input') is not None for e in seen.values()) else None,
                observed_elapsed_seconds=elapsed, observed_events=len(seen),
                stop_work=stopped, native_hard_cancel=False, enforcement='observed_receipts_only')


def record_pair(folder, pair):
    """Append once per preregistered pair; exact repetition is idempotent.

    Missing measurements/evidence are retained, never replaced with invented 0.
    Incomplete pairs cannot subsequently be overwritten; preregister anew.
    Optional holdout evidence and scope_events are retained in the same record.
    """
    folder = Path(folder)
    pair = deepcopy(pair)
    canonical(pair)
    if not isinstance(pair, dict) or type(pair.get('pair_id')) is not int or pair['pair_id'] not in PAIRS:
        raise ContractError('Pair ID must be an assigned integer 1..3')
    with lock(folder / '.lock'):
        registration, spec = _registration(folder)
        if not (folder / 'adoption.json').exists():
            raise ContractError('Experiment adoption is pending')
        adoption = _read_record(folder, folder / 'adoption.json')
        _adoption_receipt(adoption, registration)
        existing = [_read_record(folder, p) for p in sorted((folder / 'pairs').glob('*.json'))]
        target = folder / 'pairs' / f"{pair['pair_id']}.json"
        if target.exists():
            if _read_record(folder, target) != pair:
                raise ContractError('Conflicting duplicate pair')
            return pair
        _pair_complete(pair)
        identities = set()
        for outcome in [*existing, pair]:
            for side in ('baseline', 'candidate'):
                arm = outcome.get(side)
                if not isinstance(arm, dict):
                    continue
                for receipt in arm.get('native_receipts', []) or []:
                    if not isinstance(receipt, dict) or not receipt.get('response_id'):
                        continue
                    identity = receipt['response_id']
                    if identity in identities:
                        raise ContractError('A native response cannot count in multiple arms or pairs')
                    identities.add(identity)
        _budget([spec, adoption, *existing, pair])
        snapshots = {}
        _references(pair, snapshots)
        _record(folder, f"pairs/{pair['pair_id']}.json", pair, snapshots)
    return pair


def _nonregression(baseline, candidate, percent):
    return Decimal(str(candidate)) * 100 <= Decimal(str(baseline)) * (100 + percent)


def _input_outcome(baseline, candidate):
    b, c = Decimal(str(baseline)), Decimal(str(candidate))
    if (b - c) * 100 > b * 5:
        return 'improved'
    return 'equivalent' if abs(b - c) * 100 <= b * 5 else 'regression'


def _quality_passes(baseline, candidate):
    return (candidate['major_misses'] == candidate['unsupported_major'] == 0 and
            candidate['minor_detected'] >= baseline['minor_detected'] - 1 and
            all(candidate[k] <= baseline[k] for k in ('false_positives', 'unjustified_reopens', 'unsupported_reversals')))


def verdict(folder):
    """Eligibility for further validation only, never release or profile activation."""
    folder = Path(folder)
    with lock(folder / '.lock'):
        registration, spec = _registration(folder)
        adoption = _read_record(folder, folder / 'adoption.json') if (folder / 'adoption.json').exists() else None
        if adoption:
            _adoption_receipt(adoption, registration)
        records = [_read_record(folder, p) for p in sorted((folder / 'pairs').glob('*.json'))]
        if any(type(p.get('pair_id')) is not int or p['pair_id'] not in PAIRS for p in records):
            raise ContractError('Unassigned recorded pair')
        if len({p['pair_id'] for p in records}) != len(records):
            raise ContractError('Duplicate recorded pair')
        by_id = {p['pair_id']: p for p in records}
        totals = {side: {key: 0 for key in ('input', 'uncached', 'elapsed')} for side in ('baseline', 'candidate')}
        outcomes, complete = [], 0
        for pair_id in PAIRS:
            pair = by_id.get(pair_id)
            if pair is None:
                outcomes.append('missing')
                continue
            if not adoption or not _pair_complete(pair):
                outcomes.append('incomplete')
                continue
            complete += 1
            b, c = (pair[side]['metrics'] for side in ('baseline', 'candidate'))
            for side in totals:
                for key in totals[side]:
                    totals[side][key] += Decimal(str(pair[side]['metrics'][key]))
            passed = (_nonregression(b['uncached'], c['uncached'], 5) and
                      _nonregression(b['elapsed'], c['elapsed'], 10) and
                      _quality_passes(pair['baseline']['quality'], pair['candidate']['quality']))
            outcomes.append(_input_outcome(b['input'], c['input']) if passed else 'regression')
        aggregate = complete == 3 and all(_nonregression(totals['baseline'][k], totals['candidate'][k], margin)
                                        for k, margin in (('uncached', 5), ('elapsed', 10)))
        producers = {p[s].get('author_agent_id') for p in records for s in ('baseline', 'candidate')
                     if isinstance(p.get(s), dict) and isinstance(p[s].get('author_agent_id'), str)}
        holdouts = [p['holdout'] for p in records if isinstance(p.get('holdout'), dict)]
        holdout_passed = len(holdouts) == 1 and bool(
            holdouts[0].get('passed') is True and _native(holdouts[0].get('native_receipts')) and
            isinstance(holdouts[0].get('evidence_ref'), str) and Path(holdouts[0]['evidence_ref']).is_absolute() and
            Path(holdouts[0]['evidence_ref']).is_file() and holdouts[0].get('reviewer_agent_id') and
            holdouts[0]['reviewer_agent_id'] not in producers and
            any(r.get('agent_id') == holdouts[0]['reviewer_agent_id'] for r in holdouts[0]['native_receipts']) and
            holdouts[0].get('fixture_manifest_sha256') == registration['frozen'][spec['fixture_manifest_path']]['sha256'] and
            holdouts[0].get('reviewer_config_sha256') == registration['frozen'][spec['reviewer_config_path']]['sha256'])
        budget = _budget([spec, *([adoption] if adoption else []), *records])
        eligible = (adoption is not None and outcomes.count('improved') >= 2 and
                    all(o in {'improved', 'equivalent'} for o in outcomes) and aggregate and
                    holdout_passed and not budget['stop_work'])
        return dict(status='experimental_candidate', adoption_status='adopted' if adoption else 'pending',
                    gate='eligible_for_further_validation' if eligible else 'incomplete_or_failed',
                    assigned_pairs=3, recorded_pairs=len(records), complete_pairs=complete,
                    outcomes=outcomes, aggregate_passed=aggregate,
                    totals={s: {k: float(v) for k, v in t.items()} for s, t in totals.items()} if complete == 3 else None,
                    holdout_passed=holdout_passed, blind_grading_verified=False,
                    budget=budget, actual_activation=False, native_calls=0,
                    full_report_validation=False)
