"""Conditional sensitivity of the existing valuation adapter, never a risk grade."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re

from adapters.valuation import model as adapter
from .util import ContractError, digest, hash_data


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _label(value):
    return isinstance(value, str) and bool(value.strip())


def _tokens(path):
    if not isinstance(path, str) or not path.startswith('/'):
        raise ContractError('Expected an absolute JSON pointer')
    tokens = path[1:].split('/')
    if any(re.search(r'~(?![01])', token) for token in tokens):
        raise ContractError('Invalid JSON pointer escape')
    return [token.replace('~1', '/').replace('~0', '~') for token in tokens]


def _lookup(data, path):
    for token in _tokens(path):
        if isinstance(data, dict) and token in data:
            data = data[token]
        elif isinstance(data, list) and re.fullmatch(r'0|[1-9][0-9]*', token):
            index = int(token)
            if index >= len(data):
                raise ContractError('JSON pointer index out of bounds')
            data = data[index]
        else:
            raise ContractError('JSON pointer does not select an existing node')
    return data


def _replace(data, path, value):
    tokens = _tokens(path)
    parent = data
    for token in tokens[:-1]:
        parent = parent[int(token)] if isinstance(parent, list) else parent[token]
    key = int(tokens[-1]) if isinstance(parent, list) else tokens[-1]
    parent[key] = value


def _numeric_leaves(data, path='', parent=None, key=None):
    """All supplied numeric leaves, including structural/metadata inputs."""
    if isinstance(data, dict):
        for name in sorted(data):
            token = name.replace('~', '~0').replace('/', '~1')
            yield from _numeric_leaves(data[name], path + '/' + token, data, name)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from _numeric_leaves(value, path + '/' + str(index), data, index)
    elif isinstance(data, (int, float)) and not isinstance(data, bool):
        value_leaf = isinstance(parent, dict) and key == 'value'
        yield dict(path=path, value=data, value_leaf=value_leaf,
                   input_kind='value' if value_leaf else 'structural_or_metadata',
                   unit=parent.get('unit') if value_leaf else None)


def _evidence(row, sources, prefix):
    reasons = []
    if not _label(row.get('basis')):
        reasons.append('missing_or_invalid_' + prefix + '_basis')
    refs = row.get('source_ids')
    if not isinstance(refs, list) or not refs or not all(_label(x) for x in refs):
        reasons.append('missing_or_invalid_' + prefix + '_sources')
    elif not set(refs) <= sources:
        reasons.append('unknown_' + prefix + '_sources')
    return reasons


def _calculate(data, metric):
    # Keep both public adapter contracts intact; calculate also validates internally.
    adapter.validate(data)
    result, _ = adapter.calculate(data)
    value = _lookup(result, metric)
    if not _number(value):
        raise ContractError('metric must select a finite numeric output')
    return value, result


_FAILURES = (ValueError, TypeError, KeyError, IndexError, ArithmeticError)


def _compare(model, changes, metric, baseline):
    changed = copy.deepcopy(model)
    for path, value in changes:
        _replace(changed, path, value)
    try:
        value, _ = _calculate(changed, metric)
        delta = value - baseline
        if not _number(delta):
            raise ContractError('Non-finite metric change')
        return dict(status='calculated', value=value, delta=delta,
                    model_sha256=hash_data(changed))
    except _FAILURES as exc:
        return dict(status='unsupported', reason='calculation_incompatible', detail=str(exc))


def analyze(spec):
    """Recalculate evidenced endpoints and joint scenarios without control plugs.

    metric is an absolute JSON pointer into calculate(...)[0], for example
    /values/bridge.parent_equity. Flat dotted output keys remain single tokens.
    All supplied numeric leaves are enumerated; independence is operational (a
    supplied input), not an assertion that financial reconciliation permits a
    one-at-a-time change. Missing ranges always remain unknown.
    """
    if not isinstance(spec, dict) or not _label(spec.get('id')):
        raise ContractError('spec requires a nonempty id')
    model = spec.get('model')
    if not isinstance(model, dict):
        raise ContractError('model must be an actual valuation adapter input object')
    for field in ('ranges', 'scenarios', 'source_ids', 'omitted_risks'):
        if not isinstance(spec.get(field), list):
            raise ContractError(field + ' must be an array')
    if not all(_label(x) for x in spec['source_ids']):
        raise ContractError('source_ids must contain nonempty strings')
    # Non-finite *comparison* endpoints are invalid but still frozen and reported.
    # Finite JSON uses the same encoding/hash as util.hash_data. NaN/Infinity
    # tokens only freeze invalid supplied data; they are never evaluated.
    try:
        encoded = json.dumps(spec, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=True).encode()
    except (ValueError, TypeError, OverflowError) as exc:
        raise ContractError('spec must contain serializable JSON data') from exc
    frozen = copy.deepcopy(spec)
    model = frozen['model']
    adapter_path = Path(adapter.__file__).resolve()
    adapter_source_sha256 = digest(adapter_path)
    adapter_dependencies_sha256 = {name: digest(adapter_path.with_name(name))
                                   for name in ('schema_tools.py', 'input.schema.json')}
    metric = frozen.get('metric')
    try:
        baseline, base_result = _calculate(copy.deepcopy(model), metric)
    except _FAILURES as exc:
        raise ContractError('Malformed baseline or metric: ' + str(exc)) from exc
    sources = set(frozen['source_ids'])
    leaves = list(_numeric_leaves(model))
    by_path = {row['path']: row for row in leaves}
    ranges, invalid_nodes, unassessed, ranking = {}, [], [], []

    def invalid(kind, row_id, path, reason, **extra):
        invalid_nodes.append(dict(kind=kind, id=row_id, path=path, reason=reason, **extra))

    for index, row in enumerate(frozen['ranges']):
        path = row.get('path') if isinstance(row, dict) else None
        if not isinstance(path, str) or path not in by_path:
            reason = 'unknown_or_nonnumeric_input_path' if isinstance(row, dict) else 'invalid_range_object'
            invalid('range', index, path, reason)
            unassessed.append(dict(path=path, range_index=index, reasons=[reason]))
            continue
        ranges.setdefault(path, []).append((index, row))

    for leaf in leaves:
        path = leaf['path']
        supplied = ranges.get(path, [])
        reasons, endpoints = [], {}
        if not supplied:
            reasons.append('missing_range')
        elif len(supplied) > 1:
            reasons.append('duplicate_range')
            for index, _ in supplied:
                invalid('range', index, path, 'duplicate_range')
        else:
            index, row = supplied[0]
            reasons.extend(_evidence(row, sources, 'range'))
            if not _label(row.get('unit')):
                reasons.append('missing_or_invalid_range_unit')
            elif leaf['unit'] is not None and row['unit'] != leaf['unit']:
                reasons.append('range_unit_mismatch')
            if not all(_number(row.get(bound)) for bound in ('low', 'high')):
                reasons.append('invalid_range_bounds')
            elif not row['low'] <= leaf['value'] <= row['high']:
                reasons.append('range_must_be_ordered_and_contain_baseline')
            for reason in reasons:
                invalid('range', index, path, reason)
            if not reasons:
                for bound in ('low', 'high'):
                    endpoint = _compare(model, [(path, row[bound])], metric, baseline)
                    endpoints[bound] = dict(input_value=row[bound], **endpoint)
                    if endpoint['status'] != 'calculated':
                        reasons.append(bound + '_calculation_incompatible')
                        invalid('range', index, path, endpoint['reason'], endpoint=bound,
                                detail=endpoint['detail'])
                if not reasons:
                    swing = abs(endpoints['high']['value'] - endpoints['low']['value'])
                    if not _number(swing):
                        reasons.append('nonfinite_swing')
                        invalid('range', index, path, 'nonfinite_swing')
                    else:
                        ranking.append(dict(path=path, unit=row['unit'],
                                            low_value=endpoints['low']['value'],
                                            high_value=endpoints['high']['value'],
                                            absolute_swing=swing, basis=row['basis'],
                                            source_ids=row['source_ids']))
        leaf.update(status='unassessed' if reasons else 'assessed', reasons=reasons,
                    endpoints=endpoints)
        if reasons:
            unassessed.append(dict(path=path, reasons=reasons))
    ranking.sort(key=lambda row: (-row['absolute_swing'], row['path']))

    scenarios, seen = [], set()
    for index, scenario in enumerate(frozen['scenarios']):
        if not isinstance(scenario, dict):
            invalid('scenario', index, None, 'invalid_scenario_object')
            scenarios.append(dict(id=None, scenario_index=index, status='unsupported',
                                  reasons=['invalid_scenario_object']))
            continue
        key = scenario.get('id')
        reasons = _evidence(scenario, sources, 'scenario')
        if not _label(key):
            reasons.append('invalid_scenario_id')
        elif key in seen:
            reasons.append('duplicate_scenario_id')
        else:
            seen.add(key)
        changes = scenario.get('changes')
        valid_changes, changed_paths = [], set()
        if not isinstance(changes, list) or not changes:
            reasons.append('missing_or_invalid_changes')
        else:
            for change in changes:
                path = change.get('path') if isinstance(change, dict) else None
                reason = None
                if not isinstance(path, str) or path not in by_path:
                    reason = 'unknown_or_nonnumeric_input_path'
                elif path in changed_paths:
                    reason = 'duplicate_change_path'
                elif not _number(change.get('value')):
                    reason = 'invalid_change_value'
                if reason:
                    reasons.append(reason)
                    invalid('scenario', key, path, reason, scenario_index=index)
                else:
                    changed_paths.add(path)
                    valid_changes.append((path, change['value']))
        result = dict(id=key, scenario_index=index, basis=scenario.get('basis'),
                      source_ids=scenario.get('source_ids'), changes=changes)
        if reasons:
            result.update(status='unsupported', reasons=reasons)
            # Retain every compared path, including those blocked by evidence.
            for path, _ in valid_changes:
                invalid('scenario', key, path, 'scenario_contract_invalid',
                        reasons=list(reasons), scenario_index=index)
            if not valid_changes:
                invalid('scenario', key, None, 'scenario_contract_invalid',
                        reasons=list(reasons), scenario_index=index)
        else:
            comparison = _compare(model, valid_changes, metric, baseline)
            result.update(comparison)
            if comparison['status'] == 'unsupported':
                result['reasons'] = [comparison['reason']]
                for path, _ in valid_changes:
                    invalid('scenario', key, path, comparison['reason'],
                            detail=comparison['detail'], scenario_index=index)
        scenarios.append(result)
    scenario_ranking = [dict(id=row['id'], scenario_index=row['scenario_index'],
                             delta=row['delta'], absolute_change=abs(row['delta']))
                        for row in scenarios if row['status'] == 'calculated']
    scenario_ranking.sort(key=lambda row: (-row['absolute_change'], row['id'], row['scenario_index']))
    metric_tokens = _tokens(metric)
    metric_unit = base_result['units'].get(metric_tokens[1]) \
        if len(metric_tokens) == 2 and metric_tokens[0] == 'values' else None
    return dict(id=frozen['id'], model_kind='valuation_adapter', metric=metric,
                metric_unit=metric_unit,
                base_value=baseline, drivers=leaves, ranking=ranking, scenarios=scenarios,
                scenario_ranking=scenario_ranking, unassessed=unassessed,
                invalid_nodes=invalid_nodes, omitted_risks=frozen['omitted_risks'],
                model_outside_omissions=copy.deepcopy(base_result['warnings']),
                spec_sha256=hashlib.sha256(encoded).hexdigest(), model_sha256=hash_data(model),
                adapter_source_sha256=adapter_source_sha256,
                adapter_dependencies_sha256=adapter_dependencies_sha256,
                limitations=['Sensitivity is conditional model response, not risk or likelihood.',
                             'Missing/invalid ranges remain unknown, never low risk.',
                             'Only supplied endpoints and scenarios are tested; no interior extrema guarantee.',
                             'Reconciliation controls are preserved; no automatic plugs or repairs.',
                             'Numeric structural/metadata inputs are enumerated, not assumed to affect value.',
                             'Model omissions and source/method/review uncertainty remain outside sensitivity.'])
