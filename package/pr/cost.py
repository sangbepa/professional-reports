"""Actual response accounting, without subscription pricing or FX assumptions.

Records use start/end ISO timezone timestamps, optional owner (string/object)
and scope (main/child). Null/missing usage is unknown. Exact duplicates collapse;
any differing record under the same response_id is a conflict. Monetary evidence
is a nonempty string or list of nonempty source strings, never an inferred price.
"""
from __future__ import annotations

from datetime import timezone
from decimal import Context, Decimal, localcontext
import math

from .util import ContractError, canonical, timestamp

PHASES = {'package_development', 'setup', 'report', 'experiment', 'grading'}
FIELDS = ('input_tokens', 'cached_input_tokens', 'uncached_input_tokens',
          'output_tokens', 'reasoning_tokens', 'total_tokens')


def _finite(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f'{field} must be a finite number')
    try:
        result = float(value)
    except OverflowError as exc:
        raise ContractError(f'{field} must be finite') from exc
    if not math.isfinite(result) or result < 0:
        raise ContractError(f'{field} must be finite and nonnegative')
    return result


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f'{field} must be nonempty')
    return value


def _token(value):
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ContractError('Token counts must be nonnegative integers or unknown')
    return value


def _duration(rows):
    intervals = sorted((timestamp(r['start']), timestamp(r['end'])) for r in rows)
    union, total, left, right = 0.0, 0.0, None, None
    for start, end in intervals:
        total += (end - start).total_seconds()
        if right is None or start > right:
            if right is not None:
                union += (right - left).total_seconds()
            left, right = start, end
        else:
            right = max(right, end)
    if right is not None:
        union += (right - left).total_seconds()
    return dict(wallclock_union_seconds=union, response_duration_sum_seconds=total)


def _aggregate(rows):
    usage, known, coverage = {}, {}, {}
    for field in FIELDS:
        observed = [r['usage'][field] for r in rows if r['usage'][field] is not None]
        coverage[field] = dict(known=len(observed), unknown=len(rows) - len(observed))
        known[field] = sum(observed) if observed else None
        usage[field] = sum(observed) if rows and len(observed) == len(rows) else None
    money = {}
    for currency in sorted({r['currency'] for r in rows if r.get('amount') is not None}):
        priced = [r for r in rows if r.get('amount') is not None and r['currency'] == currency]
        with localcontext(Context(prec=700 + len(str(len(priced))))):
            amount = sum((Decimal(str(r['amount'])) for r in priced), Decimal(0))
        money[currency] = dict(observed_amount=_finite(float(amount), 'amount sum'),
                               response_count=len(priced))
    return dict(response_count=len(rows), usage=usage, known_usage=known,
                usage_coverage=coverage, amounts_by_currency=money,
                unknown_amount_count=sum(r.get('amount') is None for r in rows), **_duration(rows))


def summarize(records):
    """Return deduplicated records, complete/partial usage, phases and owners.

    total_tokens = input + output; reasoning is already inside output. Wallclock
    is interval union and excludes gaps. Phase/owner unions must not be summed
    to infer global wallclock. Currency totals remain separate partial receipts.
    """
    if not isinstance(records, (list, tuple)):
        raise ContractError('records must be an array')
    seen, normalized = {}, []
    for record in records:
        if not isinstance(record, dict):
            raise ContractError('record must be an object')
        key = _text(record.get('response_id'), 'response_id')
        try:
            signature = canonical(record)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ContractError('Record must contain finite JSON data') from exc
        if key in seen:
            if signature != seen[key]:
                raise ContractError(f'Conflicting response_id: {key}')
            continue
        seen[key] = signature
        if not isinstance(record.get('phase'), str) or record['phase'] not in PHASES:
            raise ContractError('Unsupported phase')
        scope = record.get('scope')
        if scope is not None and scope not in ('main', 'child'):
            raise ContractError('scope must be main or child')
        owner = record.get('owner')
        if owner is not None and not isinstance(owner, (str, dict)):
            raise ContractError('owner must be a string or object')
        if owner == '' or owner == {}:
            raise ContractError('owner must be nonempty when supplied')
        if isinstance(owner, str):
            _text(owner, 'owner')
        start = timestamp(record.get('start')).astimezone(timezone.utc)
        end = timestamp(record.get('end')).astimezone(timezone.utc)
        if end < start:
            raise ContractError('end precedes start')
        raw_usage = record.get('usage')
        if not isinstance(raw_usage, dict):
            raise ContractError('usage must be an object (nullable counters)')
        usage = {k: _token(raw_usage.get(k)) for k in FIELDS[:2] + FIELDS[3:5]}
        inp, cached, out, reasoning = (usage[k] for k in FIELDS[:2] + FIELDS[3:5])
        if inp is not None and cached is not None and cached > inp:
            raise ContractError('Cached input is a subset of input')
        if out is not None and reasoning is not None and reasoning > out:
            raise ContractError('Reasoning is a subset of output')
        usage['uncached_input_tokens'] = None if inp is None or cached is None else inp - cached
        usage['total_tokens'] = None if inp is None or out is None else inp + out
        for derived in ('uncached_input_tokens', 'total_tokens'):
            if derived in raw_usage and _token(raw_usage[derived]) != usage[derived]:
                raise ContractError(f'Inconsistent {derived}')
        amount = record.get('amount')
        if amount is not None:
            _finite(amount, 'amount')
            _text(record.get('currency'), 'currency')
            evidence = record.get('pricing_evidence')
            if isinstance(evidence, str):
                _text(evidence, 'pricing_evidence')
            elif isinstance(evidence, list) and evidence:
                for ref in evidence:
                    _text(ref, 'pricing_evidence')
            else:
                raise ContractError('Amount requires pricing_evidence')
        normalized.append(dict(record, start=start.isoformat(), end=end.isoformat(),
                               usage=usage, owner=owner, scope=scope))
    normalized.sort(key=lambda r: r['response_id'])
    phases = {p: _aggregate([r for r in normalized if r['phase'] == p]) for p in sorted(PHASES)}
    owners = []
    for key in sorted({canonical([r['owner'], r['scope']]) for r in normalized}):
        rows = [r for r in normalized if canonical([r['owner'], r['scope']]) == key]
        owners.append(dict(owner=rows[0]['owner'], scope=rows[0]['scope'], **_aggregate(rows)))
    return dict(records=normalized, phases=phases, owners=owners, **_aggregate(normalized))


def report_budget(records, *, baseline_records=None, expected_responses=None,
                  token_budget=None, wallclock_budget_seconds=None):
    """Observe report receipts and optionally estimate remaining response work.

    expected_responses is a caller estimate of total report response count.
    The baseline is separate observed report receipts. Means times remaining
    count are estimates; no parallel wallclock forecast is fabricated.
    """
    observed = summarize(records)['phases']['report']
    if token_budget is not None:
        _token(token_budget)
    if wallclock_budget_seconds is not None:
        _finite(wallclock_budget_seconds, 'wallclock budget')
    if expected_responses is not None:
        _token(expected_responses)
        if expected_responses < observed['response_count']:
            raise ContractError('Expected responses is below observed count')
    result = dict(observed=observed, token_budget=token_budget,
                  wallclock_budget_seconds=wallclock_budget_seconds,
                  observed_token_remaining=None if token_budget is None or observed['usage']['total_tokens'] is None
                  else token_budget - observed['usage']['total_tokens'],
                  observed_wallclock_remaining_seconds=None if wallclock_budget_seconds is None
                  else wallclock_budget_seconds - observed['wallclock_union_seconds'],
                  forecast=None, forecast_basis='No observed report baseline and response-count estimate.',
                  estimated_wallclock_seconds=None)
    baseline = summarize(baseline_records)['phases']['report'] if baseline_records is not None else None
    if baseline and baseline['response_count'] and expected_responses is not None:
        count = baseline['response_count']
        remaining = expected_responses - observed['response_count']
        tokens = baseline['usage']['total_tokens']
        with localcontext(Context(prec=700)):
            estimated_tokens = None if tokens is None else _finite(
                float(Decimal(tokens) * Decimal(remaining) / Decimal(count)), 'token forecast')
        result['forecast'] = dict(baseline_response_count=count, estimated_remaining_responses=remaining,
                                  estimated_remaining_tokens=estimated_tokens,
                                  estimated_remaining_response_duration_sum_seconds=
                                  _finite(baseline['response_duration_sum_seconds'] / count * remaining, 'duration forecast'))
        result['forecast_basis'] = ('Estimate: observed report baseline means times caller-estimated remaining responses; '
                                    'missing counters stay unknown; overlap and gaps are not forecast.')
    return result
