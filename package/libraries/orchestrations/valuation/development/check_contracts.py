"""DEVELOPMENT structural tests only. No model calls, review results or release checks.
Run with python3 -B libraries/orchestrations/valuation/development/check_contracts.py
from professional-reports. Uses real installed refs and the real plan checker;
the minimal meta context is only an in-memory plan-check fixture, not a submitted
meta selection. No protected evaluation is read or generated.
"""
import copy
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from pr.registry import Registry
from pr.planning import plan_check
from pr.util import ContractError, hash_data

DOMAINS = ['valuation', 'fdd', 'esg', 'market-research', 'investment-memo']
registry = Registry(ROOT)
roles = {'source', 'model', 'judgment', 'document'}
allowed = {'id', 'when', 'require_capabilities', 'require_review_roles', 'require_artifacts', 'on_unknown'}
skills = {i: (d, p) for i, (d, p) in registry.entries.items() if d['kind'] == 'skill'}
providers = {}
for i, (d, _) in sorted(skills.items()):
    for cap in d['capabilities']:
        providers.setdefault(cap, i)
rule_ids = set()
for domain in DOMAINS:
    d, folder = registry.entries[domain]
    assert d['kind'] == 'orchestration' and d['version'] == '0.1.0-dev.1'
    assert d['status'] == 'provisional' and d['production_quality_verified'] is False
    assert d['execution_support'] == ('complete' if domain == 'valuation' else 'planning-only')
    assert all(isinstance(x, str) for x in d['requires'])
    assert not Path(d['entrypoint']).is_absolute() and '..' not in Path(d['entrypoint']).parts
    markdown = '\n'.join(f.read_text() for f in folder.glob('*.md'))
    for file in folder.rglob('*'):
        if file.is_file() and file.suffix in {'.json', '.md'}:
            content = file.read_text()
            assert '/Users/' not in content and '/home/' not in content
            if file.suffix == '.json':
                json.loads(content)
    rules = json.loads((folder / 'plan-rules.json').read_text())['rules']
    for rule in rules:
        assert set(rule) <= allowed and rule['id'] not in rule_ids
        rule_ids.add(rule['id'])
        assert rule['id'] in markdown
        assert rule['on_unknown'] == 'assessment'
        assert set(rule['require_review_roles']) <= roles
        assert set(rule['require_capabilities']) <= set(providers)
        if 'when' in rule:
            assert set(rule['when']) == {'fact', 'equals'}
            assert rule['when']['equals'] is True

folder = registry.entries['valuation'][1]
rules = json.loads((folder / 'plan-rules.json').read_text())['rules']
cases = json.loads((folder / 'development/few-shot-cases.json').read_text())['cases']
ref = registry.reference('valuation')
# This is a coverage fixture, not an executable engagement DAG or reviewed answer.
meta = {'selected': [ref]}
expert = registry.reference(next(i for i, (d, _) in registry.entries.items() if d['kind'] == 'persona'))
runtime = registry.reference('codex-native')
checks_run = 0
for case in cases:
    facts = case['input']['facts']
    assert all(type(x) is bool or x is None for x in facts.values())
    active = [r for r in rules if 'when' not in r or facts.get(r['when']['fact']) is True]
    unknown = [r for r in rules if 'when' in r and facts.get(r['when']['fact']) is None]
    caps = set(c for r in active for c in r['require_capabilities'])
    outputs = set(o for r in active for o in r['require_artifacts'])
    assert outputs <= set(o for n in case['illustrative_output']['nodes'] for o in n['outputs'])
    chosen = sorted({providers[c] for c in caps})
    required_checks, consumes, bound_outputs = set(), set(), set(outputs)
    for identity in chosen:
        contract_file = skills[identity][1] / 'contract.json'
        if contract_file.exists():
            contract = json.loads(contract_file.read_text())
            for key in ['acceptance', 'validations']:
                required_checks.update(c['id'] if isinstance(c, dict) else c for c in contract.get(key, []))
            consumes.update(contract.get('consumes', []))
            bound_outputs.update(contract.get('outputs', []))
    node = {'id':case['id']+'-coverage','revision':1,'goal':'DEVELOPMENT rule coverage only','question':'Does the real checker enforce this declared plan coverage?',
            'basis':[{'component':ref,'clause':'valuation-rule-core','facts':['fictional-development-premise'],'reason':'Structural development fixture; not real evidence.'}],
            'expert':expert,'skills':[registry.reference(i) for i in chosen],'runtime':runtime,'capabilities':sorted(caps),'execution':'agent','reasoning':'high',
            'inputs':[],'consumes':sorted(consumes),'outputs':sorted(bound_outputs),'required_checks':sorted(required_checks or {'development-structure'}),
            'depends_on':[],'review_required':True,'review_role':None}
    nodes = [node]
    for role in sorted(roles):
        nodes.append({**node,'id':case['id']+'-'+role,'skills':[],'capabilities':[],'execution':'human-gate','outputs':[case['id']+'-'+role+'-planned-review'],
                      'required_checks':['development-review-coverage-only'],'consumes':[],'depends_on':[node['id']],'review_required':False,'review_role':role})
    assessments = {r['id']:{'status':'pending','task_id':node['id'],'reason':'Synthetic profile lacks this fact; assessment remains unperformed.','evidence':['Development prompt explicitly marks this fact null.']} for r in unknown}
    plan = {'id':case['id'],'revision':1,'previous':None,'meta_hash':hash_data(meta),'reason':'DEVELOPMENT structural check only','actor':'development-contract-test','facts':facts,'nodes':nodes,'applicability_assessments':assessments}
    result = plan_check(registry, meta, plan)
    assert len(result['pending_rules']) == len(unknown)
    checks_run += 1
    broken = copy.deepcopy(plan)
    for n in broken['nodes']:
        n['outputs'] = [o for o in n['outputs'] if o != 'valuation-method-decisions']
    try:
        plan_check(registry, meta, broken)
    except ContractError:
        checks_run += 1
    else:
        raise AssertionError('Missing required artifact was accepted')
    if unknown:
        broken = copy.deepcopy(plan);broken.pop('applicability_assessments')
        try:
            plan_check(registry, meta, broken)
        except ContractError:
            checks_run += 1
        else:
            raise AssertionError('Unassessed unknown was accepted')
print(json.dumps({'domains':len(DOMAINS),'unique_rules':len(rule_ids),'development_cases':len(cases),'real_engine_positive_negative_checks':checks_run,'production_quality_verified':False,'review_or_release_performed':False}))
