"""Observed native report costs. Cumulative counters are not billing or response IDs."""
import argparse
import json
from pathlib import Path


def usage(agent_id, sessions=None):
    sessions = Path(sessions or Path.home()/'.codex/sessions')
    matches = [p for p in sessions.glob('*/*/*/*.jsonl') if p.name.endswith(agent_id+'.jsonl')]
    if len(matches) != 1:
        return {'agent_id': agent_id, 'status': 'unknown', 'matches': len(matches), 'usage': None}
    latest = None
    stamp = None
    calls = set()
    for line in matches[0].open():
        d = json.loads(line)
        p = d.get('payload', {})
        if d.get('type') == 'event_msg' and p.get('type') == 'token_count':
            counter = (p.get('info') or {}).get('total_token_usage')
            if counter:
                latest, stamp = dict(counter), d.get('timestamp')
        if d.get('type') == 'response_item' and p.get('type') in {'function_call','custom_tool_call'}:
            if p.get('call_id'):
                calls.add(p['call_id'])
    if latest is not None:
        cached = latest.get('cached_input_tokens')
        latest['uncached_input_tokens'] = None if cached is None else latest['input_tokens']-cached
    return {'agent_id': agent_id, 'status': 'observed' if latest else 'unknown',
            'usage': latest, 'observed_at': stamp, 'source': str(matches[0]), 'tool_calls': len(calls),
            'response_id_deduplication': 'unavailable; one final cumulative counter per distinct native session'}


def summarize(out):
    out = Path(out)
    actors = {}
    for role in ('supervisor','coordinator','curator','analyst','analysis-reviewer','author','reviewer','visual-left','visual-right'):
        path = out/(role+'-spawn.json')
        if path.exists():
            receipt=json.loads(path.read_text())
            actors[role] = receipt.get('agent_id') or receipt['response']['agent_id']
    if len(set(actors.values())) != len(actors):
        raise ValueError('Duplicate actor IDs would double count cumulative usage')
    observations = {role: usage(agent) for role,agent in actors.items()}
    known = [v['usage'] for v in observations.values() if v['usage'] is not None]
    fields = ('input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens','reasoning_output_tokens')
    totals = {k: sum(v[k] for v in known if v.get(k) is not None)
              if any(v.get(k) is not None for v in known) else None for k in fields}
    if any(v.get(k) is None for v in known for k in fields):
        missing = [k for k in fields if any(v.get(k) is None for v in known)]
    else:
        missing = []
    dispatch_path = out/'dispatch.json'
    dispatch = json.loads(dispatch_path.read_text()) if dispatch_path.exists() else {}
    required = ('coordinator','analyst','author','reviewer') if 'analyst_prompt' in dispatch else ('coordinator','author','reviewer')
    if 'curator_prompt' in dispatch:required = ('coordinator','curator','analyst','author','reviewer')
    required=tuple(required)+tuple(r for r in ('analysis-reviewer','visual-left','visual-right') if r+'_prompt' in dispatch)
    missing_roles = [role for role in required if role not in actors]
    return {'native_session_usage': observations, 'known_child_totals': totals,
            'all_three_child_counters_observed': all(observations.get(r,{}).get('usage') is not None for r in ('coordinator','author','reviewer')),
            'all_required_native_counters_observed':not missing_roles and all(observations[role]['usage'] is not None for role in required),
            'required_roles':list(required), 'missing_roles':missing_roles,
            'missing_fields': missing,
            'scope': 'Distinct spawned native sessions including the full-valuation analyst. Main-parent dispatch/monitoring and compression remain separate and must be added for full-path cost; partial totals are not complete cost.',
            'billing_conversion': None, 'reasoning_is_part_of_output': True}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('out'); a = p.parse_args()
    out = Path(a.out); data = summarize(out)
    (out/'usage-observations.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'known_child_totals': data['known_child_totals'],
                      'all_three_child_counters_observed': data['all_three_child_counters_observed']}))
