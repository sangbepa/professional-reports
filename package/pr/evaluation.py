"""Preregistered, blinded paired experiments and a protected promotion boundary."""
import random
import math
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from .schema import validate
from .util import ContractError, digest, hash_data, immutable_json, lock, now, read_json, write_json, identifier


def preregister(root,folder,spec):
    spec=deepcopy(spec)
    if spec.get('mode')=='session_efficiency':
        spec.setdefault('round_lengths',[3,6,3])
        spec.setdefault('metric','input_tokens')
        spec.setdefault('min_delta',0.05)
        spec.setdefault('equivalence_margin',0.05)
        spec.setdefault('six_round_exploratory_target',0.30)
    validate(root,'experiment',spec)
    for key in ('min_delta','equivalence_margin'):_number(spec[key],key)
    if spec['baseline_release']==spec['candidate_release']:raise ContractError('Releases must differ')
    if spec['equivalence_margin']>spec['min_delta']:
        raise ContractError('Equivalence margin cannot exceed improvement threshold')
    if _efficiency(spec) and spec['holdout']['input_snapshot']==spec['input_snapshot']:
        raise ContractError('Holdout must have a distinct input snapshot')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    immutable_json(folder/'spec.json',spec)
    immutable_json(folder/'registration.json',dict(spec_sha256=hash_data(spec),registered_at=now(),status='candidate'))
    return dict(spec_sha256=hash_data(spec),path=str(folder))


def assignments(folder,pair_ids,seed):
    folder=Path(folder);spec=_frozen_spec(folder)
    if _efficiency(spec) and len(pair_ids)!=3:
        raise ContractError('Session efficiency requires exactly three assigned pairs')
    for pair_id in pair_ids:identifier(pair_id)
    if _efficiency(spec) and set(pair_ids)&set(spec['holdout']['case_ids']):
        raise ContractError('Holdout cases cannot be assigned for development')
    if len(pair_ids)<spec['min_pairs'] or len(set(pair_ids))!=len(pair_ids):raise ContractError('Need distinct paired trials')
    rng=random.Random(seed);first=rng.choice([True,False]);private=[];public=[]
    for i,p in enumerate(pair_ids):
        baseline_first=first if i%2==0 else not first
        mapping=dict(A=spec['baseline_release'] if baseline_first else spec['candidate_release'],
                     B=spec['candidate_release'] if baseline_first else spec['baseline_release'])
        private.append(dict(pair_id=p,mapping=mapping));public.append(dict(pair_id=p,labels=['A','B']))
    immutable_json(folder/'private-assignment.json',dict(seed=seed,pairs=private))
    immutable_json(folder/'grader-assignment.json',dict(pairs=public,evaluation=spec['evaluation']))
    if _efficiency(spec):immutable_json(folder/'assignment-registration.json',dict(sha256=hash_data(private)))
    return public


def record_pair(folder,pair):
    folder=Path(folder);spec=_frozen_spec(folder)
    identifier(pair['pair_id'])
    if pair['input_snapshot']!=spec['input_snapshot'] or pair['evaluation']!=spec['evaluation']:
        raise ContractError('Paired comparison changed inputs or evaluation profile')
    if pair.get('status') not in {'complete','failed','incomplete','timeout'}:
        raise ContractError('All assigned outcomes including failures must be retained')
    if _efficiency(spec):
        _record_efficiency_pair(folder,spec,pair)
        return pair
    for side in ('A','B'):
        r=pair[side]
        for key in ('run_id','release_id','artifact_sha256','score','operational_seconds','posthoc_seconds','grader_agent_id'):
            if key not in r:raise ContractError('Paired result missing '+key)
        if r['score'] is not None and not isinstance(r['score'],(int,float)):raise ContractError('Invalid score')
        if r.get('author_agent_id')==r['grader_agent_id']:raise ContractError('Author cannot be blind grader')
    if pair['A']['run_id']==pair['B']['run_id']:raise ContractError('Both sides cannot be same run')
    known={p['pair_id'] for p in read_json(folder/'private-assignment.json')['pairs']}
    if pair['pair_id'] not in known:raise ContractError('Pair was not assigned before execution')
    with lock(folder/'.lock'):
        assignment=next(p for p in read_json(folder/'private-assignment.json')['pairs'] if p['pair_id']==pair['pair_id'])
        for side in ('A','B'):
            if pair[side]['release_id']!=assignment['mapping'][side]:raise ContractError('Paired result release differs from blind assignment')
        used={d[s]['run_id'] for p in (folder/'pairs').glob('*.json') for d in [read_json(p)] for s in ('A','B')}
        if any(pair[s]['run_id'] in used for s in ('A','B')):raise ContractError('A run cannot be counted again in another paired trial')
        immutable_json(folder/'pairs'/f"{pair['pair_id']}.json",pair)
    return pair


def verdict(folder,holdout):
    folder=Path(folder);spec=read_json(folder/'spec.json')
    if hash_data(spec)!=read_json(folder/'registration.json')['spec_sha256']:raise ContractError('Experiment specification changed after registration')
    if _efficiency(spec):return _efficiency_verdict(folder,spec,holdout)
    assignments=read_json(folder/'private-assignment.json')['pairs'];outcomes=[]
    for a in assignments:
        p=folder/'pairs'/f"{a['pair_id']}.json"
        if not p.exists():outcomes.append('missing');continue
        pair=read_json(p)
        candidate=pair['A'] if a['mapping']['A']==spec['candidate_release'] else pair['B']
        baseline=pair['B'] if a['mapping']['A']==spec['candidate_release'] else pair['A']
        if pair['status']!='complete' or candidate['score'] is None or baseline['score'] is None:outcomes.append('incomplete');continue
        if pair.get('material_regression'):outcomes.append('regression');continue
        delta=candidate['score']-baseline['score']
        if delta>spec['min_delta']:outcomes.append('improved')
        elif abs(delta)<=spec['equivalence_margin']:outcomes.append('equivalent')
        else:outcomes.append('mixed' if delta>0 else 'regression')
    passed=len(outcomes)>=spec['min_pairs'] and outcomes.count('improved')>=2 and all(o in {'improved','equivalent'} for o in outcomes)
    holdout_passed=(holdout.get('status')=='pass' and bool(holdout.get('evidence_sha256'))
                    and holdout.get('evaluation')==spec['evaluation'] and holdout.get('candidate_release')==spec['candidate_release'])
    return dict(status='eligible' if passed and holdout_passed else 'candidate',outcomes=outcomes,assigned_cases=len(outcomes),
                holdout_passed=bool(holdout_passed),causal_claim='Evidence supports this controlled comparison; does not identify unique cause')


def promote(folder,holdout,reviewer,receipt,protected_before,protected_after):
    folder=Path(folder);spec=read_json(folder/'spec.json');v=verdict(folder,holdout)
    if reviewer==spec['proposed_by'] or not reviewer or not receipt:
        raise ContractError('Candidate author cannot approve its own promotion')
    if protected_before!=protected_after:
        if receipt.get('kind')!='human-approval' or not receipt.get('approved_protected_sha256')==protected_after:
            raise ContractError('Evaluation/criteria changes require explicit human approval of exact hash')
    if v['status']!='eligible':raise ContractError('Mixed, incomplete, or regressing comparison cannot be promoted')
    record=dict(verdict=v,reviewer=reviewer,approval=receipt,protected_sha256=protected_after,approved_at=now())
    immutable_json(folder/'promotion.json',record)
    return record


def calibrate(labels,runs):
    """Known-error labels only: do not treat another LLM's guess as ground truth."""
    if not labels or not runs:raise ContractError('Need fixed known-error labels and actual evaluator runs')
    fp=fn=correct=total=0;agreement={k:[] for k in labels}
    for run in runs:
        if set(run)!=set(labels):raise ContractError('Every calibration run must cover all fixed cases')
        for key,truth in labels.items():
            pred=run[key]
            if not isinstance(pred,bool) or not isinstance(truth,bool):raise ContractError('Error-presence calibration labels must be boolean')
            fp+=int(pred and not truth);fn+=int(not pred and truth);correct+=int(pred==truth);total+=1;agreement[key].append(pred)
    return dict(false_positive=fp,false_negative=fn,correct=correct,total=total,
                stable_cases=sum(len(set(v))==1 for v in agreement.values()),cases=len(labels),
                human_agreement=None,automatic_release_approval=False)


def enqueue(state,run_id,problem,evidence,layer_hypotheses):
    allowed={'meta','plan','persona','skill','runtime','reasoning','input','evaluator','engine','unknown'}
    if not set(layer_hypotheses)<=allowed or not evidence:raise ContractError('Attribution requires observable evidence and valid hypotheses')
    item=dict(run_id=run_id,problem=problem,evidence=evidence,layer_hypotheses=layer_hypotheses,
              status='untriaged',created_at=now(),causality='unconfirmed')
    write_json(Path(state)/'maintenance'/f'{hash_data(item)}.json',item)
    return item


# session_efficiency mode_version=1. Ratios use total input, including cached
# input. For a zero baseline, zero is equivalent and any positive cost regresses.
SESSION_INPUT_CAP = 6_000_000
SESSION_SECONDS_CAP = 1800
BUDGET_SOURCES = ('main', 'child', 'compaction', 'grade')


def _number(value, name, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or (isinstance(value, float) and not math.isfinite(value)) or value < 0
            or (integer and not isinstance(value, int))):
        raise ContractError('Missing, negative or nonfinite metric: ' + name)
    return value


def _efficiency(spec):
    if spec.get('mode', 'quality') not in {'quality', 'session_efficiency'}:
        raise ContractError('Unknown experiment mode')
    if spec.get('mode') == 'session_efficiency':
        if spec.get('mode_version') != 1:
            raise ContractError('Unsupported session efficiency version')
        if spec.get('min_pairs') != 3 or spec.get('round_lengths') != [3,6,3]:
            raise ContractError('Session efficiency requires exactly three pairs and round lengths [3,6,3]')
        return True
    return False


def _frozen_spec(folder):
    spec = read_json(folder / 'spec.json')
    if hash_data(spec) != read_json(folder / 'registration.json')['spec_sha256']:
        raise ContractError('Experiment specification changed after registration')
    return spec


def _efficiency_assignments(folder):
    pairs = read_json(folder / 'private-assignment.json')['pairs']
    if hash_data(pairs) != read_json(folder / 'assignment-registration.json')['sha256']:
        raise ContractError('Assigned cases changed after assignment')
    if len(pairs)!=3 or len({p['pair_id'] for p in pairs})!=3:
        raise ContractError('Session efficiency requires exactly three distinct assigned pairs')
    return pairs


def _metrics(result, spec):
    if not isinstance(result, dict):
        raise ContractError('Missing result evidence')
    metrics = result.get('metrics', {})
    if not isinstance(metrics, dict):
        raise ContractError('Missing metrics')
    values = {k: _number(metrics.get(k), k, k != 'elapsed_seconds')
              for k in ('input_tokens', 'cached_input_tokens', 'elapsed_seconds')}
    if values['cached_input_tokens'] > values['input_tokens']:
        raise ContractError('Cached input exceeds total input')
    values['uncached_input_tokens'] = values['input_tokens'] - values['cached_input_tokens']
    if 'uncached_input_tokens' in metrics:
        supplied = _number(metrics['uncached_input_tokens'], 'uncached_input_tokens', True)
        if supplied != values['uncached_input_tokens']:
            raise ContractError('Contradictory uncached input')
    quality = result.get('quality', {})
    if not isinstance(quality, dict) or not _sha256(result.get('artifact_sha256')):
        raise ContractError('Missing quality/artifact evidence')
    reference = spec['quality_reference']
    if (quality.get('reference') != reference or quality.get('artifact_sha256') != result.get('artifact_sha256')
            or not _sha256(quality.get('evidence_sha256'))):
        raise ContractError('Quality requires fixed-reference/calibrated artifact-bound evidence')
    counts = {k: _number(quality.get(k), k, True) for k in (
        'known_defects', 'detected_known_defects', 'closure_cases', 'correct_closures',
        'material_misses', 'unsupported_material_findings', 'unjustified_reopenings', 'reversals')}
    for total, observed in (('known_defects', 'detected_known_defects'), ('closure_cases', 'correct_closures')):
        if counts[total] != reference[total] or counts[observed] > counts[total]:
            raise ContractError('Contradictory fixed quality reference counts')
    return values, counts


def _sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _check_pair_identity(pair, assignment, spec):
    if not isinstance(pair, dict):
        raise ContractError('Missing pair evidence')
    if (pair.get('pair_id') != assignment['pair_id'] or pair.get('input_snapshot') != spec['input_snapshot']
            or pair.get('evaluation') != spec['evaluation']):
        raise ContractError('Paired identity or frozen profile mismatch')
    if pair.get('status') not in {'complete', 'failed', 'incomplete', 'timeout'}:
        raise ContractError('Invalid assigned outcome')
    for side in ('A', 'B'):
        result = pair.get(side, {})
        if not isinstance(result, dict):
            raise ContractError('Missing assigned result')
        if result.get('release_id') != assignment['mapping'][side] or not result.get('run_id'):
            raise ContractError('Paired release/run differs from assignment')
        if pair['status'] == 'complete':
            if (not _sha256(result.get('artifact_sha256')) or not result.get('grader_agent_id')
                    or not result.get('author_agent_id')
                    or result['grader_agent_id'] in {result['author_agent_id'], spec['proposed_by']}):
                raise ContractError('Complete result requires artifact and independent grader')
            _metrics(result, spec)
    if pair['A']['run_id'] == pair['B']['run_id']:
        raise ContractError('Both sides cannot be same run')
    if pair['status'] == 'complete' and any(pair[s]['grader_agent_id'] in
            {pair[t]['author_agent_id'] for t in ('A', 'B')} for s in ('A', 'B')):
        raise ContractError('Blind grader cannot author either side')


def _record_efficiency_pair(folder, spec, pair):
    assigned = {a['pair_id']: a for a in _efficiency_assignments(folder)}
    if pair['pair_id'] not in assigned:
        raise ContractError('Pair was not assigned before execution')
    _check_pair_identity(pair, assigned[pair['pair_id']], spec)
    with lock(folder / '.lock'):
        used = {d[s]['run_id'] for p in (folder / 'pairs').glob('*.json')
                for d in [read_json(p)] for s in ('A', 'B')}
        if any(pair[s]['run_id'] in used for s in ('A', 'B')):
            raise ContractError('A run cannot be counted again in another paired trial')
        immutable_json(folder / 'pairs' / (pair['pair_id'] + '.json'), pair)


def _nonregression(baseline, candidate, percent):
    # Decimal avoids boundary errors at exactly 5% or 10%.
    return Decimal(str(candidate)) * 100 <= Decimal(str(baseline)) * (100 + percent)


def _input_outcome(baseline, candidate):
    b, c = Decimal(str(baseline)), Decimal(str(candidate))
    if b == 0:
        return 'equivalent' if c == 0 else 'regression'
    if (b - c) * 100 > b * 5:
        return 'improved'
    return 'equivalent' if abs(b - c) * 100 <= b * 5 else 'regression'


def _quality_passes(baseline, candidate):
    return (candidate['material_misses'] == candidate['unsupported_material_findings'] == 0
            and candidate['detected_known_defects'] == candidate['known_defects']
            and candidate['correct_closures'] == candidate['closure_cases']
            and all(candidate[k] <= baseline[k] for k in ('unjustified_reopenings', 'reversals')))


def _efficiency_verdict(folder, spec, holdout):
    assigned = _efficiency_assignments(folder)
    outcomes, used = [], set()
    totals = {side: {k: Decimal(0) for k in ('input_tokens', 'uncached_input_tokens', 'elapsed_seconds')}
              for side in ('baseline', 'candidate')}
    extras = {p.stem for p in (folder / 'pairs').glob('*.json')} - {a['pair_id'] for a in assigned}
    for assignment in assigned:
        path = folder / 'pairs' / (assignment['pair_id'] + '.json')
        if not path.exists():
            outcomes.append('missing')
            continue
        try:
            pair = read_json(path)
            _check_pair_identity(pair, assignment, spec)
            runs = {pair[s]['run_id'] for s in ('A', 'B')}
            if used & runs:
                raise ContractError('Duplicate paired run')
            used.update(runs)
            if pair['status'] != 'complete':
                outcomes.append('incomplete')
                continue
            candidate_side = 'A' if assignment['mapping']['A'] == spec['candidate_release'] else 'B'
            baseline_side = 'B' if candidate_side == 'A' else 'A'
            b, bq = _metrics(pair[baseline_side], spec)
            c, cq = _metrics(pair[candidate_side], spec)
            for side, metrics in (('baseline', b), ('candidate', c)):
                for key in totals[side]:
                    totals[side][key] += Decimal(str(metrics[key]))
            safe = (not pair.get('material_regression') and _quality_passes(bq, cq)
                    and _nonregression(b['uncached_input_tokens'], c['uncached_input_tokens'], 5)
                    and _nonregression(b['elapsed_seconds'], c['elapsed_seconds'], 10))
            outcomes.append(_input_outcome(b['input_tokens'], c['input_tokens']) if safe else 'regression')
        except (ContractError, KeyError, TypeError, ValueError):
            outcomes.append('incomplete')
    aggregate_passed = (all(o in {'improved', 'equivalent'} for o in outcomes)
                        and _nonregression(totals['baseline']['uncached_input_tokens'], totals['candidate']['uncached_input_tokens'], 5)
                        and _nonregression(totals['baseline']['elapsed_seconds'], totals['candidate']['elapsed_seconds'], 10))
    holdout_passed = False
    try:
        hmetrics, hquality = _metrics(holdout, spec)
        holdout_passed = (holdout.get('status') == 'pass' and not holdout.get('material_regression') and _sha256(holdout.get('evidence_sha256'))
                          and holdout.get('evaluation') == spec['evaluation']
                          and holdout.get('candidate_release') == spec['candidate_release']
                          and holdout.get('release_id') == spec['candidate_release']
                          and holdout.get('input_snapshot') == spec['holdout']['input_snapshot']
                          and holdout.get('case_ids') == spec['holdout']['case_ids']
                          and holdout.get('author_exposed') is False
                          and bool(holdout.get('run_id')) and holdout['run_id'] not in used
                          and bool(holdout.get('grader_agent_id'))
                          and bool(holdout.get('author_agent_id'))
                          and holdout['grader_agent_id'] not in {spec['proposed_by'], holdout['author_agent_id']}
                          and hquality['unjustified_reopenings'] == hquality['reversals'] == 0
                          and _quality_passes(hquality, hquality))
    except (ContractError, KeyError, TypeError, ValueError):
        pass
    passed = (len(outcomes) == spec['min_pairs'] == 3 and outcomes.count('improved') >= 2
              and aggregate_passed and not extras)
    return dict(status='eligible' if passed and holdout_passed else 'candidate', outcomes=outcomes,
                assigned_cases=len(outcomes), aggregate_passed=aggregate_passed,
                holdout_passed=bool(holdout_passed), unassigned_cases=sorted(extras),
                totals={side: {k: float(v) for k, v in values.items()} for side, values in totals.items()},
                six_round_exploratory_target=0.30,
                causal_claim='Evidence supports this controlled comparison; does not identify unique cause')


def create_budget_ledger(folder):
    """Create once for the whole session, across rounds/restarts/compactions.

    Caller supplies cumulative, disjoint category counts (including grade costs).
    Observed elapsed time is session wall time, not summed parallel worker time.
    This ledger reports an observed stop signal; it cannot cancel native workers.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    immutable_json(folder / 'budget.json', dict(version=1, input_cap=SESSION_INPUT_CAP,
                   seconds_cap=SESSION_SECONDS_CAP, sources=list(BUDGET_SOURCES), created_at=now()))
    write_json(folder / 'head.json', dict(observations=0, sha256=hash_data(read_json(folder / 'budget.json'))))
    return budget_status(folder)


def _budget_observation(observation, previous=None):
    if not isinstance(observation, dict) or set(observation) - {
            'observation_id', 'observed_elapsed_seconds', 'counts', 'previous_sha256'}:
        raise ContractError('Budget observations must use cumulative session fields only')
    identifier(observation.get('observation_id'))
    elapsed = _number(observation.get('observed_elapsed_seconds'), 'observed_elapsed_seconds')
    counts = observation.get('counts', {})
    if not isinstance(counts, dict) or set(counts) != set(BUDGET_SOURCES):
        raise ContractError('Budget requires main/child/compaction/grade cumulative counts')
    for source in BUDGET_SOURCES:
        if not isinstance(counts[source], dict) or set(counts[source]) != {'input_tokens', 'cached_input_tokens', 'output_tokens'}:
            raise ContractError('Budget source must contain explicit token counters')
        for key in ('input_tokens', 'cached_input_tokens', 'output_tokens'):
            value = _number(counts[source].get(key), source + '.' + key, True)
            if previous and value < previous['counts'][source][key]:
                raise ContractError('Cumulative counts cannot reset or move to a new window')
        if counts[source]['cached_input_tokens'] > counts[source]['input_tokens']:
            raise ContractError('Cached input exceeds total input')
    if previous and elapsed < previous['observed_elapsed_seconds']:
        raise ContractError('Elapsed session time cannot reset')
    return sum(counts[s]['input_tokens'] for s in BUDGET_SOURCES), elapsed


def _budget_history(folder):
    config = read_json(folder / 'budget.json')
    if (config.get('version') != 1 or config.get('input_cap') != SESSION_INPUT_CAP
            or config.get('seconds_cap') != SESSION_SECONDS_CAP or config.get('sources') != list(BUDGET_SOURCES)):
        raise ContractError('Budget caps and accounting sources cannot change')
    previous, seen, history = None, set(), []
    for index, path in enumerate(sorted((folder / 'observations').glob('*.json')), 1):
        record = read_json(path)
        if path.name != f'{index:08d}.json' or record.get('previous_sha256') != (hash_data(previous) if previous else hash_data(config)):
            raise ContractError('Budget history cannot be truncated or reset')
        _budget_observation(record, previous)
        if record['observation_id'] in seen:
            raise ContractError('Duplicate budget observation')
        seen.add(record['observation_id'])
        history.append(record)
        previous = record
    head = read_json(folder / 'head.json')
    if head != dict(observations=len(history), sha256=hash_data(history[-1] if history else config)):
        raise ContractError('Budget history differs from cumulative ledger head')
    return config, history


def budget_status(folder):
    """Observed inclusive caps; remaining counts are not a native hard limit."""
    _, history = _budget_history(Path(folder))
    total, elapsed = _budget_observation(history[-1]) if history else (0, 0)
    return dict(status='observed' if history else 'incomplete', measurement_complete=bool(history),
                input_tokens=total, observed_elapsed_seconds=elapsed,
                input_cap=SESSION_INPUT_CAP, seconds_cap=SESSION_SECONDS_CAP,
                remaining_input_tokens=max(0, SESSION_INPUT_CAP-total),
                remaining_seconds=max(0, SESSION_SECONDS_CAP-elapsed),
                stop_work=total >= SESSION_INPUT_CAP or elapsed >= SESSION_SECONDS_CAP,
                enforcement='observed', native_hard_cancel=False, observations=len(history))


def record_budget(folder, observation):
    """Append a cumulative observation. Reusing this ledger is mandatory per session."""
    folder = Path(folder)
    with lock(folder / '.lock'):
        config, history = _budget_history(folder)
        _budget_observation(observation, history[-1] if history else None)
        if any(r['observation_id'] == observation['observation_id'] for r in history):
            raise ContractError('Duplicate budget observation')
        record = deepcopy(observation)
        record['previous_sha256'] = hash_data(history[-1] if history else config)
        immutable_json(folder / 'observations' / f'{len(history)+1:08d}.json', record)
        write_json(folder / 'head.json', dict(observations=len(history)+1, sha256=hash_data(record)))
        return budget_status(folder)
