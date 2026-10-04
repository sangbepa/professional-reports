"""Producer handoff readiness, independent of financial approval or host completion."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from adapters.valuation.model import calculate
from adapters.valuation.source_cells import requests_to_ledgers
from adapters.valuation.history import reconcile

FILES={'curator':['requests.json','requests-snapshot.json','selectors.json','selection-gaps.json','accounting-evidence.json','capital-evidence.json','history-spec.json','historical-reconciliation.json'],'analyst':['valuation-input.json','evidence.json','judgments.json'],'author':['narrative.json','argument-record.json']}
def validate_history_receipt(out):
 names=('accounting-evidence.json','history-spec.json','historical-reconciliation.json')
 ledger,spec,receipt=[json.loads((out/n).read_text()) for n in names]
 expected=reconcile(ledger,spec)
 expected.update(input_binding='input_bytes_sha256',ledger_sha256=hashlib.sha256((out/names[0]).read_bytes()).hexdigest(),spec_sha256=hashlib.sha256((out/names[1]).read_bytes()).hexdigest())
 if receipt!=expected:raise ValueError('Historical reconciliation does not reproduce from current ledger/spec')
 if receipt['status']!='passed':raise ValueError('Historical arithmetic evidence remains unresolved')
 return receipt

def validated(out,role):
 if role not in FILES:raise ValueError('Only unreviewed producers use early handoff; reviewer completion remains mandatory')
 files=FILES[role];data={name:json.loads((out/name).read_text()) for name in files}
 if role=='curator':
  mandate=json.loads((out/'mandate.json').read_text());expanded,ledgers,gaps=requests_to_ledgers(out,data['requests.json'],mandate['cutoff'])
  expected={'requests-snapshot.json':data['requests.json'],'selectors.json':expanded,'selection-gaps.json':gaps,**{k+'-evidence.json':v for k,v in ledgers.items()}}
  if any(data[n]!=v for n,v in expected.items()):raise ValueError('Current extraction does not reproduce')
  validate_history_receipt(out)
 elif role=='analyst':
  if data['valuation-input.json'].get('synthetic') is not False:raise ValueError('Actual non-synthetic input required')
  validate_history_receipt(out)
  from adapters.valuation.model_support import local_support,validate_judgments
  validate_judgments(data['judgments.json']);local_support(out,data['valuation-input.json'])
  calculate(data['valuation-input.json'])
 else:
  from adapters.valuation.report import prepare
  from adapters.valuation.schema_tools import validate_schema
  snapshot=json.loads((out/'author-input-snapshot.json').read_text())
  expected={'valuation-input.json','model-result.json','model-verification.json'}
  if set(snapshot.get('artifacts',{}))!=expected:raise ValueError('Author input snapshot incomplete')
  for name,digest in snapshot['artifacts'].items():
   if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Author changed immutable input: '+name)
  narrative=data['narrative.json']
  if not isinstance(narrative,dict) or set(narrative)-{'language','report_sections','section_order'} or not narrative.get('report_sections'):raise ValueError('Narrative contract invalid')
  if not isinstance(data['argument-record.json'],dict) or not data['argument-record.json']:raise ValueError('Argument record required')
  model=json.loads((out/'valuation-input.json').read_text());model['report']={**model.get('report',{}),**narrative}
  validate_schema(model);prepare(model,json.loads((out/'model-result.json').read_text()))
 return {name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in files}

def handoff(out,role,verify=False,probe=False):
 path=out/(role+'-ready.json')
 if probe:
  try:hashes=validated(out,role)
  except (FileNotFoundError,ValueError,KeyError,TypeError,json.JSONDecodeError):return {'status':'draft_unavailable','financial_approval':False}
  return {'status':'draft_available_unreviewed','role':role,'artifacts':hashes,'financial_approval':False,'producer_completion_claimed':False}
 if verify and not path.exists():return {'status':'not_ready','financial_approval':False}
 hashes=validated(out,role)
 if verify:
  record=json.loads(path.read_text())
  if record.get('artifacts')!=hashes or record.get('role')!=role or record.get('financial_approval') is not False:raise ValueError('Handoff changed after declaration')
  return {'status':'ready_unreviewed','role':role,'artifacts':hashes,'financial_approval':False}
 record={'status':'ready_unreviewed','role':role,'artifacts':hashes,'financial_approval':False,'host_completion_claimed':False}
 with path.open('x') as f:json.dump(record,f,indent=2)
 return record

if __name__=='__main__':
 import sys
 p=argparse.ArgumentParser();p.add_argument('role',choices=list(FILES));p.add_argument('out',type=Path);p.add_argument('--verify',action='store_true');p.add_argument('--probe',action='store_true');a=p.parse_args();print(json.dumps(handoff(a.out.resolve(),a.role,a.verify,a.probe)))
