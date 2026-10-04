"""Bounded arithmetic checks over explicit source_cells observation references.

Spec: {"tolerance": 1e-7, "periods": [{"period_end": "YYYY-MM-DD",
"revenue": {"segments": [ids], "eliminations": [ids], "consolidated": id},
"ebit": {same keys}, "da": {"items": [ids], "subset_of": {child: parent}}}]}.
Tolerance is absolute, in the unchanged ledger unit. No conversion is performed.
Passed means arithmetic/declared relationship checks passed, never source approval.
The CLI takes ledger_path spec_path output_path and creates a new output only.
"""

import argparse
import hashlib
import json
import math
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path


def _hash(data):
    try:
        raw = json.dumps(data, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(raw).hexdigest()


def _safe(data):
    """Keep invalid evidence inspectable without emitting non-JSON numbers."""
    if isinstance(data, float) and not math.isfinite(data):
        return str(data)
    if isinstance(data, dict):
        return {key: _safe(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_safe(value) for value in data]
    return data


def _decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError('Finite numeric scalar required')
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('Finite numeric scalar required') from error
    if not number.is_finite():
        raise ValueError('Finite numeric scalar required')
    return number


def _status(issues):
    states = {issue['status'] for issue in issues}
    return 'failed' if 'failed' in states else 'insufficient' if 'insufficient' in states else 'passed'


def _sum(values):
    # Preserve source_cells amount_exact even across very different magnitudes.
    nonzero = [value for value in values if value]
    if not nonzero:
        return Decimal(0)
    precision = (max(value.adjusted() for value in nonzero)
                 - min(value.as_tuple().exponent for value in nonzero)
                 + len(str(len(nonzero))) + 3)
    with localcontext() as context:
        context.prec = max(28, precision)
        return sum(values, Decimal(0))


def reconcile(ledger, spec):
    """Return JSON-compatible, hash-bound diagnostics; never infer amounts."""
    checks, references, differences = [], {}, []
    result = {
        'status': 'insufficient', 'checks': checks, 'differences': differences,
        'references': [], 'input_binding': 'canonical_json_sha256',
        'ledger_sha256': _hash(ledger), 'spec_sha256': _hash(spec),
        'financial_approval': False, 'semantic_source_approval': False,
        'semantic_inclusion_status': 'unverified',
    }

    def issue(check, code, message, ids=(), status='failed'):
        check['issues'].append({'code': code, 'message': message,
                                'references': list(ids), 'status': status})

    def finish():
        for check in checks:
            check['status'] = _status(check['issues'])
        result['status'] = _status([{'status': check['status']} for check in checks])
        result['references'] = list(references.values())
        return result

    schema = {'kind': 'input', 'issues': []}
    checks.append(schema)
    observations = ledger.get('observations') if isinstance(ledger, dict) else None
    if not isinstance(observations, list):
        issue(schema, 'missing_observations', 'Observation list required', status='insufficient')
        return finish()
    index = {}
    for observation in observations:
        identity = observation.get('id') if isinstance(observation, dict) else None
        if not isinstance(identity, str) or not identity.strip():
            issue(schema, 'invalid_observation_id', 'Nonempty observation ID required')
        elif identity in index:
            issue(schema, 'duplicate_observation_id', 'Ambiguous ledger ID', [identity])
            index[identity] = None
        else:
            index[identity] = observation
    if not isinstance(spec, dict) or set(spec) - {'periods', 'tolerance'}:
        issue(schema, 'invalid_spec', 'Only periods and absolute tolerance are accepted')
        return finish()
    try:
        tolerance = _decimal(spec.get('tolerance', 1e-7))
        if tolerance < 0 or not math.isfinite(float(tolerance)):
            raise ValueError('Nonnegative finite absolute tolerance required')
    except ValueError as error:
        issue(schema, 'invalid_tolerance', str(error))
        return finish()
    periods = spec.get('periods')
    if not isinstance(periods, list) or not periods:
        issue(schema, 'missing_periods', 'Nonempty explicit periods required', status='insufficient')
        return finish()

    sources = ledger.get('sources', {})
    used, seen_periods = set(), set()

    def resolve(identity, check, period):
        if not isinstance(identity, str) or not identity.strip():
            issue(check, 'invalid_reference', 'Nonempty observation ID required')
            return None
        if identity not in references:
            observation = index.get(identity)
            source_id = observation.get('source_id') if observation else None
            references[identity] = {
                'observation_id': identity, 'resolved': observation is not None,
                'observation': _safe(observation),
                'source': _safe(sources.get(source_id)) if isinstance(sources, dict) else None,
            }
        if identity not in index:
            issue(check, 'unknown_reference', 'Reference is absent from observations',
                  [identity], status='insufficient')
            return None
        observation = index[identity]
        if observation is None:
            issue(check, 'ambiguous_reference', 'Duplicate ledger ID', [identity])
            return None
        for key in ('period_end', 'perimeter', 'unit'):
            if not isinstance(observation.get(key), str) or not observation[key].strip():
                issue(check, 'missing_dimension', 'Explicit ' + key + ' required',
                      [identity], status='insufficient')
        if observation.get('period_end') and observation['period_end'] != period:
            issue(check, 'wrong_period', 'Observation period differs from requested period', [identity])
        # These explicit source units cannot substantiate an amount history.
        if (observation.get('source_unit') in {'percent', 'fraction', 'text', 'shares'}
                or observation.get('unit') in {'percent', '%', 'fraction', 'ratio', 'text', 'shares'}):
            issue(check, 'non_amount_unit', 'Amount reference has a non-amount unit', [identity])
        try:
            value = observation.get('value')
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                if value is None:
                    issue(check, 'missing_value', 'Missing scalar is not zero', [identity],
                          status='insufficient')
                    return observation
                raise ValueError('Extracted value must be numeric')
            numeric = _decimal(value)
            exact = observation.get('amount_exact')
            if exact is not None:
                numeric = _decimal(exact)
                if float(numeric) != value:
                    raise ValueError('amount_exact and value disagree')
            if not math.isfinite(float(numeric)):
                raise ValueError('Finite ledger value required')
        except (ValueError, OverflowError) as error:
            issue(check, 'invalid_value', str(error), [identity])
        return observation

    for period_spec in periods:
        if not isinstance(period_spec, dict) or set(period_spec) - {'period_end', 'revenue', 'ebit', 'da'}:
            issue(schema, 'invalid_period_spec', 'Explicit period and three metric groups required')
            continue
        period = period_spec.get('period_end')
        try:
            if not isinstance(period, str) or date.fromisoformat(period).isoformat() != period:
                raise ValueError('ISO period_end required')
        except ValueError:
            issue(schema, 'invalid_period', 'ISO period_end required')
            continue
        if period in seen_periods:
            issue(schema, 'duplicate_period', 'Period appears more than once')
        seen_periods.add(period)
        for metric in ('revenue', 'ebit', 'da'):
            check = {'kind': metric, 'period_end': period, 'issues': [],
                     'included': [], 'excluded': [], 'semantic_inclusion_status': 'unverified'}
            checks.append(check)
            group = period_spec.get(metric)
            if group is None:
                issue(check, 'missing_metric', 'Explicit metric specification required', status='insufficient')
                continue
            keys = {'items', 'subset_of'} if metric == 'da' else {'segments', 'eliminations', 'consolidated'}
            if not isinstance(group, dict) or set(group) - keys:
                issue(check, 'invalid_metric_spec', 'Unsupported metric fields')
                continue
            if not keys.issubset(group):
                issue(check, 'incomplete_metric_spec', 'All metric fields must be explicit', status='insufficient')
                continue
            list_keys = ('items',) if metric == 'da' else ('segments', 'eliminations')
            if any(not isinstance(group[key], list) for key in list_keys):
                issue(check, 'invalid_id_list', 'Observation references must be lists')
                continue
            leaves = [identity for key in list_keys for identity in group[key]]
            if not group[list_keys[0]]:
                issue(check, 'empty_contributions', 'At least one contribution required', status='insufficient')
            total_ids = leaves + ([] if metric == 'da' else [group['consolidated']])
            local_ids = set()
            for identity in total_ids:
                if not isinstance(identity, str):
                    continue  # resolve records the invalid reference
                if identity in local_ids or identity in used:
                    issue(check, 'duplicate_id', 'Observation reused as an arithmetic input', [identity])
                local_ids.add(identity)
            used.update(local_ids)
            relationships = group.get('subset_of', {}) if metric == 'da' else {}
            if not isinstance(relationships, dict):
                issue(check, 'invalid_subsets', 'subset_of must map child IDs to parent IDs')
                relationships = {}
            if metric == 'da':
                check['declared_subset_of'] = _safe(dict(relationships))
            nodes = list(dict.fromkeys(identity for identity in total_ids if isinstance(identity, str)))
            for child, parent in relationships.items():
                for identity in (child, parent):
                    if isinstance(identity, str) and identity not in nodes:
                        nodes.append(identity)
                    elif not isinstance(identity, str):
                        issue(check, 'invalid_subset_reference', 'Subset IDs must be strings')
            resolved = {identity: resolve(identity, check, period) for identity in nodes}
            if any(not isinstance(identity, str) for identity in total_ids):
                issue(check, 'invalid_reference', 'Observation IDs must be strings')
            dimensions = {(obs.get('period_end'), obs.get('perimeter'), obs.get('unit'))
                          for obs in resolved.values() if obs is not None
                          and all(isinstance(obs.get(key), str) and obs[key].strip()
                                  for key in ('period_end', 'perimeter', 'unit'))}
            if len(dimensions) > 1:
                issue(check, 'dimension_mismatch', 'Period, perimeter and unit must match exactly', nodes)
            if len(dimensions) == 1:
                _, check['perimeter'], check['unit'] = next(iter(dimensions))
            for child in relationships:
                trail, current = set(), child
                while isinstance(current, str) and current in relationships:
                    if current in trail:
                        issue(check, 'subset_cycle', 'Subset relationship cycle', sorted(trail))
                        break
                    trail.add(current)
                    current = relationships[current]
            if check['issues']:
                continue
            for identity in leaves:
                chain, current, included_parent = [], identity, None
                while current in relationships:
                    current = relationships[current]
                    chain.append(current)
                    if current in leaves:
                        included_parent = current
                if included_parent is not None:
                    check['excluded'].append({
                        'observation_id': identity, 'reason': 'declared_subset_of_included_parent',
                        'included_parent': included_parent, 'relationship_chain': [identity] + chain,
                    })
                else:
                    reason = ('included_without_included_declared_ancestor' if metric == 'da'
                              else 'signed_elimination' if identity in group['eliminations']
                              else 'segment_amount')
                    check['included'].append({'observation_id': identity, 'reason': reason})
            def amount(identity):
                obs = resolved[identity]
                return _decimal(obs['amount_exact'] if obs.get('amount_exact') is not None else obs['value'])
            total = _sum([amount(item['observation_id']) for item in check['included']])
            check['sum_exact'] = str(total)
            if not math.isfinite(float(total)):
                issue(check, 'nonfinite_sum', 'Sum cannot be represented as a finite ledger value', leaves)
                continue
            check['sum'] = float(total)
            if metric != 'da':
                consolidated = amount(group['consolidated'])
                difference = _sum([total, consolidated.copy_negate()])
                check.update({'consolidated_reference': group['consolidated'],
                              'consolidated_exact': str(consolidated),
                              'difference_exact': str(difference), 'tolerance_exact': str(tolerance)})
                differences.append({'kind': metric, 'period_end': period, 'unit': check['unit'],
                                    'difference_exact': str(difference), 'tolerance_exact': str(tolerance)})
                if difference.copy_abs() > tolerance:
                    issue(check, 'reconciliation_mismatch', 'Signed contributions differ from consolidated amount', nodes)
    return finish()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger_path', type=Path)
    parser.add_argument('spec_path', type=Path)
    parser.add_argument('output_path', type=Path)
    args = parser.parse_args(argv)
    ledger_raw, spec_raw = args.ledger_path.read_bytes(), args.spec_path.read_bytes()
    result = reconcile(json.loads(ledger_raw, object_pairs_hook=_unique_object),
                       json.loads(spec_raw, object_pairs_hook=_unique_object))
    result.update({'input_binding': 'input_bytes_sha256',
                   'ledger_sha256': hashlib.sha256(ledger_raw).hexdigest(),
                   'spec_sha256': hashlib.sha256(spec_raw).hexdigest()})
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    # Exclusive creation preserves every earlier receipt and both input files.
    with args.output_path.open('x', encoding='utf-8') as output:
        output.write(payload)
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
