"""Reprice analyst-supplied interacting alternatives without changing the base.

No company defaults, chosen downside, forecast or financial approval is supplied.
"""
import argparse,copy,hashlib,json,math
from pathlib import Path
try:
 from .model import calculate
 from .math_audit import audit_math
except ImportError:
 from model import calculate
 from math_audit import audit_math

def sha(raw):return hashlib.sha256(raw).hexdigest()
def atom_at(data,pointer):
 if not isinstance(pointer,str) or not pointer.startswith('/'):raise ValueError('Exact input JSON pointer required')
 value=data
 for key in pointer[1:].split('/'):
  if '~' in key.replace('~0','').replace('~1',''):raise ValueError('Invalid pointer escape')
  key=key.replace('~1','/').replace('~0','~')
  if isinstance(value,list):
   if not key.isdigit() or (len(key)>1 and key.startswith('0')):raise ValueError('Exact list index required')
   value=value[int(key)]
  elif isinstance(value,dict):value=value[key]
  else:raise ValueError('Scenario pointer traverses scalar')
 if not isinstance(value,dict) or value.get('kind') not in ('assumption','evidence','synthetic') or 'value' not in value:raise ValueError('Scenario may change financial atom values only')
 if type(value['value']) not in (int,float):raise ValueError('Scenario numeric atom required')
 return value

def run_cases(model,cases):
 if not isinstance(cases,list) or not cases:raise ValueError('Explicit analyst cases required')
 base,_=calculate(copy.deepcopy(model));seen=set();outputs=[]
 for case in cases:
  identity=case.get('id');rationale=case.get('rationale');patches=case.get('patches')
  if not isinstance(identity,str) or not identity or identity in seen or not isinstance(rationale,str) or not rationale.strip():raise ValueError('Unique scenario ID and actual rationale required')
  seen.add(identity)
  if not isinstance(patches,list) or not patches:raise ValueError('Explicit scenario patches required')
  candidate=copy.deepcopy(model);paths=set();changes=[]
  for patch in patches:
   pointer=patch['pointer'];chosen=patch['value']
   if pointer in paths:raise ValueError('Duplicate scenario pointer')
   paths.add(pointer)
   if type(chosen) not in (int,float) or not math.isfinite(chosen):raise ValueError('Finite numerical choice required')
   atom=atom_at(candidate,pointer);before=atom['value'];atom['value']=chosen
   # A counterfactual to an observation is an assumption, never a new observation.
   atom['kind']='assumption';atom['rationale']='Unreviewed alternative '+identity+': '+rationale
   atom['review']={'status':'unreviewed','reviewer':'','reference':''}
   changes.append({'pointer':pointer,'before':before,'after':chosen})
  result,_=calculate(candidate)
  replay=audit_math(candidate,result)
  if replay['status']!='passed':raise ValueError('Independent alternative calculation replay failed')
  keys=[k for k in result['values'] if k.startswith('bridge.') or (k.startswith('classes.') and k.endswith('.per_share')) or k.endswith('.ev')]
  outputs.append({'id':identity,'rationale':rationale,'support_refs':case.get('support_refs',[]),'changes':changes,
   'values':{k:result['values'][k] for k in keys},'units':{k:result['units'][k] for k in keys},
   'delta_from_base':{k:result['values'][k]-base['values'][k] for k in keys},
   'mechanical_replay':{'status':replay['status'],'checked_paths':replay['checked_paths'],'financial_approval':False},'economic_approval':False})
 return {'kind':'analyst_chosen_alternatives_not_approval','financial_approval':False,'base_case_changed':False,'cases':outputs}

def run_files(out,cases_name='scenario-cases.json'):
 out=Path(out).resolve();p=(out/cases_name).resolve()
 if not p.is_relative_to(out):raise ValueError('Scenario cases escaped current attempt')
 model_path=(out/'valuation-input.json').resolve()
 if not model_path.is_relative_to(out):raise ValueError('Model escaped current attempt')
 destination=out/'scenario-analysis.json'
 if destination.exists():raise FileExistsError('Scenario results are append-only')
 model_raw=model_path.read_bytes();cases_raw=p.read_bytes();receipt=run_cases(json.loads(model_raw),json.loads(cases_raw))
 if model_path.read_bytes()!=model_raw or p.read_bytes()!=cases_raw:raise ValueError('Scenario inputs changed during calculation')
 receipt.update(model_input_sha256=sha(model_raw),cases_sha256=sha(cases_raw))
 with destination.open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2,allow_nan=False)
 return {'status':'computed_unreviewed','cases':len(receipt['cases']),'financial_approval':False,'base_case_changed':False,'path':str(destination)}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--cases',default='scenario-cases.json');a=p.parse_args();print(json.dumps(run_files(a.out,a.cases),ensure_ascii=False))
