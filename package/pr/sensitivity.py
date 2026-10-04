"""Evidence-bound linear sensitivity, not a calibrated financial-model adapter.

Units are caller-declared nonempty labels; dimensional calibration is outside
this adapter. Ranges must use the input unit (optional range.unit may confirm it).
Missing drivers prevent a base calculation; missing evidence prevents assessment.
"""
from __future__ import annotations

import math
from decimal import Context, Decimal, localcontext

from .util import ContractError, hash_data


def _label(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f'{field} must be a nonempty string')
    return value


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f'{field} must be a finite number')
    try:
        result = float(value)
    except OverflowError as exc:
        raise ContractError(f'{field} must be finite') from exc
    if not math.isfinite(result):
        raise ContractError(f'{field} must be finite')
    return value


def _sources(value, field):
    if not isinstance(value, list):
        raise ContractError(f'{field} must be a list')
    return [_label(item, field) for item in value]


def _evaluate(intercept, coefficients, values):
    if any(key not in values for key in coefficients):
        return None
    # Enough precision for the entire exponent span of finite binary64 inputs,
    # their products, and carry digits. Only the final public number is rounded.
    with localcontext(Context(prec=1600 + len(str(len(coefficients))))):
        result = Decimal(str(intercept))
        for key in sorted(coefficients):
            result += Decimal(str(coefficients[key])) * Decimal(str(values[key]))
        return _number(float(result), 'model result')


def _shift(coefficients, before, after):
    with localcontext(Context(prec=1600 + len(str(len(coefficients))))):
        result = sum((Decimal(str(coefficients[k])) *
                      (Decimal(str(after[k])) - Decimal(str(before[k])))
                      for k in sorted(coefficients)), Decimal(0))
        return _number(float(result), 'model change')


def analyze(spec):
    """Analyze all declared drivers without eval, assumptions, or risk grades.

    ranking.absolute_swing is abs(coefficient * (high - low)), changing only
    one driver, computed before output rounding. Dependent drivers are unassessed.
    Joint scenarios override base inputs and require their own evidence.
    """
    if not isinstance(spec, dict):
        raise ContractError('spec must be an object')
    _label(spec.get('id'), 'id')
    model = spec.get('model')
    if not isinstance(model, dict) or model.get('kind') != 'linear':
        raise ContractError('Unsupported model kind; a separately calibrated adapter is required')
    intercept = _number(model.get('intercept'), 'intercept')
    raw = model.get('coefficients')
    if not isinstance(raw, dict):
        raise ContractError('coefficients must be an object')
    coefficients = {_label(k, 'driver id'): _number(v, 'coefficient') for k, v in raw.items()}
    sources = set(_sources(spec.get('source_ids'), 'source_ids'))
    omitted = spec.get('omitted_risks')
    if not isinstance(omitted, list):
        raise ContractError('omitted_risks must be an array')
    inputs = spec.get('inputs')
    if not isinstance(inputs, list):
        raise ContractError('inputs must be an array')
    by_id, ranges, reasons = {}, {}, {}
    for item in inputs:
        if not isinstance(item, dict):
            raise ContractError('input must be an object')
        key = _label(item.get('id'), 'input id')
        if key in by_id:
            raise ContractError('Duplicate input id')
        unit = _label(item.get('unit'), 'unit')
        value = _number(item.get('value'), 'input value')
        by_id[key] = dict(item, value=value)
        why = []
        if key not in coefficients:
            why.append('unknown_model_driver')
        independent = item.get('independent')
        if independent is not None and not isinstance(independent, bool):
            raise ContractError('independent must be boolean')
        if independent is not True:
            why.append('independence_not_established')
        bounds = item.get('range')
        if bounds is None:
            why.append('missing_range')
        elif not isinstance(bounds, dict):
            raise ContractError('range must be an object')
        else:
            if 'unit' in bounds and bounds['unit'] != unit:
                raise ContractError('Range unit differs from input unit')
            if bounds.get('low') is None or bounds.get('high') is None:
                why.append('incomplete_range')
                # Still reject malformed finite endpoints when partially supplied.
                for endpoint in ('low', 'high'):
                    if bounds.get(endpoint) is not None:
                        _number(bounds[endpoint], endpoint)
            else:
                low, high = (_number(bounds[k], k) for k in ('low', 'high'))
                if not low <= value <= high:
                    raise ContractError('Range must be ordered and contain the base value')
                ranges[key] = (low, high)
            basis = bounds.get('basis')
            if basis is None or basis == '':
                why.append('missing_range_basis')
            else:
                _label(basis, 'range basis')
            refs = _sources(bounds.get('source_ids', []), 'range source_ids')
            if not refs:
                why.append('missing_range_sources')
            elif not set(refs) <= sources:
                why.append('unknown_range_sources')
        reasons[key] = why
    values = {k: item['value'] for k, item in by_id.items() if k in coefficients}
    base = _evaluate(intercept, coefficients, values)
    drivers, unassessed, ranking = [], [], []
    for key in sorted(set(coefficients) | set(by_id)):
        why = list(reasons.get(key, ['missing_input', 'missing_range']))
        if key in coefficients and base is None and not why:
            why.append('base_incomplete')
        status = 'unassessed' if why else 'assessed'
        drivers.append(dict(id=key, coefficient=coefficients.get(key), status=status))
        if why:
            unassessed.append(dict(id=key, reasons=why))
            continue
        low, high = ranges[key]
        lo = _evaluate(intercept, coefficients, dict(values, **{key: low}))
        hi = _evaluate(intercept, coefficients, dict(values, **{key: high}))
        ranking.append(dict(id=key, unit=by_id[key]['unit'], low_value=lo,
                            high_value=hi, absolute_swing=abs(_shift({key: coefficients[key]},
                                                                  {key: low}, {key: high})),
                            basis=by_id[key]['range']['basis'],
                            source_ids=by_id[key]['range']['source_ids']))
    ranking.sort(key=lambda row: (-row['absolute_swing'], row['id']))
    scenarios, seen = [], set()
    raw_scenarios = spec.get('scenarios')
    if not isinstance(raw_scenarios, list):
        raise ContractError('scenarios must be an array')
    for scenario in raw_scenarios:
        if not isinstance(scenario, dict):
            raise ContractError('scenario must be an object')
        key = _label(scenario.get('id'), 'scenario id')
        if key in seen:
            raise ContractError('Duplicate scenario id')
        seen.add(key)
        basis = _label(scenario.get('basis'), 'scenario basis')
        refs = _sources(scenario.get('source_ids'), 'scenario source_ids')
        if not refs or not set(refs) <= sources:
            raise ContractError('Scenario evidence must reference known sources')
        overrides = scenario.get('values')
        if not isinstance(overrides, dict) or not set(overrides) <= set(coefficients):
            raise ContractError('Scenario values must reference model drivers')
        changed = dict(values)
        changed.update({k: _number(v, 'scenario value') for k, v in overrides.items()})
        result = _evaluate(intercept, coefficients, changed)
        scenarios.append(dict(id=key, value=result,
                              delta=None if result is None or base is None else _shift(coefficients, values, changed),
                              status='unassessed' if result is None else 'calculated',
                              basis=basis, source_ids=refs))
    try:
        digest = hash_data(spec)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContractError('spec must contain finite JSON data') from exc
    return dict(id=spec['id'], model_kind='linear', base_value=base, drivers=drivers,
                ranking=ranking, scenarios=sorted(scenarios, key=lambda row: row['id']),
                unassessed=unassessed, omitted_risks=omitted, spec_sha256=digest,
                limitations=['Linear model only; no nonadditive financial calibration.',
                             'Units are declared labels, not independently calibrated dimensions.',
                             'Unassessed drivers and omitted risks cannot imply low risk.'])
