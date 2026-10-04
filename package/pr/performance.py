"""Read-only DAG estimates and attempt-level ledger observations; never enforcement."""
from __future__ import annotations

import copy
import heapq
import math
from dataclasses import dataclass

from .planning import graph
from .util import ContractError, canonical, hash_data, timestamp


def analyze_plan(plan, estimates, workers=6):
    """Estimate a generic DAG. Numeric inputs are explicitly hypothetical.

    Structured estimates: {seconds: number | None, provenance: str,
    kind: 'measured' | 'hypothetical' | 'unknown'}. Missing values stay unknown.
    """
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 6:
        raise ContractError('workers must be an integer from 1 to 6')
    nodes = plan['nodes']
    layers = graph(nodes)
    deps = {n['id']: set(n['depends_on']) for n in nodes}
    if set(estimates) - set(deps):
        raise ContractError('Estimates refer to unknown nodes')
    normalized = {}
    for key in deps:
        value = estimates.get(key)
        item = (copy.deepcopy(value) if isinstance(value, dict) else
                dict(seconds=value, provenance=None, kind='unknown' if value is None else 'hypothetical'))
        item.setdefault('kind', 'hypothetical')
        item.setdefault('provenance', None)
        seconds = item.get('seconds')
        if item['kind'] not in {'measured', 'hypothetical', 'unknown'}:
            raise ContractError('Unknown estimate kind')
        if item['kind'] == 'measured' and not item['provenance']:
            raise ContractError('Measured estimates require provenance')
        if seconds is not None and (isinstance(seconds, bool) or not isinstance(seconds, (int, float))
                                    or not math.isfinite(seconds) or seconds < 0):
            raise ContractError('Durations must be finite nonnegative seconds or None')
        if item['kind'] == 'unknown':
            item['seconds'] = None
        else:
            item['seconds'] = seconds
        normalized[key] = item
    missing = sorted(k for k, v in normalized.items() if v['seconds'] is None)
    result = dict(workers=workers, estimates=normalized, missing_estimates=missing,
                  projection_kind='estimate, not a guarantee', critical_path=None,
                  critical_path_seconds=None, work_seconds=None, work_worker_lower_bound_seconds=None,
                  lower_bound_seconds=None, projected_seconds=None, schedule=None,
                  slack_seconds={'300': None, '600': None})
    if missing:
        return result
    durations = {k: v['seconds'] for k, v in normalized.items()}
    finish, paths = {}, {}
    for layer in layers:
        for key in layer:
            parent = max(sorted(deps[key]), key=lambda k: finish[k], default=None)
            finish[key] = durations[key] + (finish[parent] if parent else 0)
            paths[key] = (paths[parent] if parent else []) + [key]
    last = max(sorted(finish), key=finish.get, default=None)
    critical = finish[last] if last else 0
    work = sum(durations.values())
    # Deterministic non-preemptive list scheduling, lexical ready-node priority.
    pending, done, running, schedule, clock = set(deps), set(), [], [], 0
    while pending or running:
        ready = sorted(k for k in pending if deps[k] <= done)
        for key in ready[:workers - len(running)]:
            pending.remove(key)
            end = clock + durations[key]
            heapq.heappush(running, (end, key))
            schedule.append(dict(node_id=key, start_seconds=clock, end_seconds=end))
        if running:
            clock = running[0][0]
            while running and running[0][0] == clock:
                _, key = heapq.heappop(running)
                done.add(key)
    result.update(critical_path=paths[last] if last else [], critical_path_seconds=critical,
                  work_seconds=work, work_worker_lower_bound_seconds=work / workers,
                  lower_bound_seconds=max(critical, work / workers), projected_seconds=clock,
                  schedule=schedule, slack_seconds={'300': 300 - clock, '600': 600 - clock})
    return result


def interval_summary(intervals):
    """Union walltime and time with >=2 concurrent intervals (not duration sums)."""
    changes = {}
    for start, end in intervals:
        if not all(math.isfinite(x) for x in (start, end)) or end < start:
            raise ContractError('Invalid interval')
        changes[start] = changes.get(start, 0) + 1
        changes[end] = changes.get(end, 0) - 1
    active = union = overlap = total = 0
    previous = None
    for point, change in sorted(changes.items()):
        if previous is not None:
            elapsed = point - previous
            union += elapsed if active else 0
            overlap += elapsed if active >= 2 else 0
            total += elapsed * active
        active += change
        previous = point
    return dict(union_seconds=union, overlap_seconds=overlap,
                summed_interval_seconds=total, excess_concurrency_seconds=total - union)


@dataclass(frozen=True)
class EventSnapshot:
    """Immutable content snapshot; canonical JSON is detached from the live Run."""
    events_json: str
    sha256: str
    count: int
    tail_seq: int | None
    tail_sha256: str | None


def profile_run(run):
    """Observe a supplied (preferably pinned-version) Run without loading/mutating it.

    No filesystem writes, refresh, transactions, pin checks or ledger migration.
    Open intervals are censored at the captured event tail, not extrapolated.
    """
    view = copy.copy(run)
    view.events = copy.deepcopy(run.events)
    events = view.events
    snapshot = EventSnapshot(canonical(events), hash_data(events), len(events),
                             events[-1].get('seq') if events else None,
                             events[-1].get('sha256') if events else None)
    timing = copy.deepcopy(view.timing())
    observations = []
    result = dict(snapshot=snapshot, timing=timing, attempts=observations,
                  true_compute_seconds=None, actual_cost=None,
                  deadline_slack_seconds={str(b): b - timing['report_seconds']
                                          if timing.get('report_seconds') is not None else None
                                          for b in (300, 600)},
                  notes=['Run.timing is authoritative for deadlines; intervals end at event tail.',
                         'Bound-agent elapsed is measured elapsed, not CPU/GPU compute time.',
                         'Gaps include orchestration, waiting and unobserved activity; attribution is unknown.',
                         'Requested/resolved models do not establish observed model or actual cost.'])
    if not events:
        result.update(intervals={}, observation_seconds=0, non_task_gap_seconds=0,
                      unobserved_agent_gap_seconds=0, clock_basis='unavailable')
        return result
    same_boot = bool(events[0].get('boot_id')) and all(
        e.get('boot_id') == events[0]['boot_id'] for e in events)
    if same_boot:
        points = [(e['monotonic_ns'] - events[0]['monotonic_ns']) / 1e9 for e in events]
    else:
        origin = timestamp(events[0]['utc'])
        points = [(timestamp(e['utc']) - origin).total_seconds() for e in events]
    result['clock_basis'] = 'monotonic' if same_boot else 'UTC fallback; uncertain'
    if any(b < a for a, b in zip(points, points[1:])):
        raise ContractError('Clock moved backwards; interval union cannot be measured reliably')
    horizon = points[-1]
    buckets = {name: [] for name in ('attempted', 'execution', 'review_wait', 'review_execution')}
    ids = [e['data']['attempt_id'] for e in events if e['kind'] == 'dispatched']
    if len(ids) != len(set(ids)):
        raise ContractError('Duplicate dispatch attempt ID')
    for aid in ids:
        related = [(e, t) for e, t in zip(events, points) if e['data'].get('attempt_id') == aid]
        dispatch, start = next((e, t) for e, t in related if e['kind'] == 'dispatched')
        attempt = view.attempt(aid)
        node = attempt['node']
        terminal = next(((e, t) for e, t in related if e['kind'] in
                         {'result_submitted', 'attempt_failed', 'worker_released'}), None)
        end = terminal[1] if terminal else horizon
        row = dict(attempt_id=aid, node_id=dispatch['data']['node_id'],
                   execution=node.get('execution'), review_role=node.get('review_role'),
                   attempted_interval=[start, end], censored=terminal is None,
                   execution_interval=None, review_wait_interval=None,
                   failures=[copy.deepcopy(e['data']) for e, _ in related if e['kind'] == 'attempt_failed'],
                   model=None, actual_cost=None)
        buckets['attempted'].append((start, end))
        bound = next(((e, t) for e, t in related if e['kind'] == 'agent_bound'), None)
        if bound and node.get('execution') == 'agent':
            if bound[1] > end:
                raise ContractError('Agent binding follows attempt termination')
            row['execution_interval'] = [bound[1], end]
            buckets['execution'].append((bound[1], end))
            if node.get('review_role'):
                buckets['review_execution'].append((bound[1], end))
            binding = view.binding(aid) or {}
            row['model'] = {k: copy.deepcopy(v) for k, v in binding.items() if 'model' in k} or None
        submitted = next(((e, t) for e, t in related if e['kind'] == 'result_submitted'
                          and e['data'].get('status') == 'review_pending'), None)
        if submitted:
            reviewed = next(((e, t) for e, t in related if t >= submitted[1]
                             and e['kind'] in {'task_reviewed', 'attempt_failed'}), None)
            row['review_wait_interval'] = [submitted[1], reviewed[1] if reviewed else horizon]
            row['review_wait_censored'] = reviewed is None
            buckets['review_wait'].append(row['review_wait_interval'])
        observations.append(row)
    summaries = {k: interval_summary(v) for k, v in buckets.items()}
    result.update(intervals=summaries, observation_seconds=horizon,
                  non_task_gap_seconds=horizon - summaries['attempted']['union_seconds'],
                  unobserved_agent_gap_seconds=horizon - summaries['execution']['union_seconds'])
    return result
