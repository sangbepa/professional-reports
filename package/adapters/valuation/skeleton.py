"""Generate contract structure, never company values or economic assumptions."""
import argparse,json
from pathlib import Path

SCHEMA=Path(__file__).with_name('input.schema.json')

def skeleton(industrial,finance,classes,horizon,stub=False):
 if not 0<=industrial<=20 or not 0<=finance<=20 or not 1<=classes<=20 or not 1<=horizon<=20:raise ValueError('Explicit valid structural counts required')
 if industrial+finance==0:raise ValueError('At least one valuation unit required')
 if stub and horizon<2:raise ValueError('Stub horizon includes the stub and at least one full period')
 root=json.loads(SCHEMA.read_text());bases={}
 def resolve(s):return root['$defs'][s['$ref'].split('/')[-1]] if '$ref' in s else s
 def walk(s,path):
  s=resolve(s);props=s.get('properties',{})
  if {'value','source','review'}.issubset(props):
   bases[path]={'kind':None,'source':{'id':None,'uri':None,'sha256':None,'locator':None},'as_of':None,'unit':None,'rationale':None}
   return {'$basis':path,'value':None}
  if s.get('type')=='object':
   keys=list(s.get('required',[]))
   if path=='bridge':keys+=['separately_valued_nci']
   if path.startswith('share_classes.') and path.count('.')==1:
    keys+=['participation_weight','fixed_claim_per_share']
   if stub and path.startswith(('industrial.','finance.')) and path.count('.')==1:keys+=['stub']
   if stub and path=='':keys+=['timing']
   return {k:walk(props[k],(path+'.'+k).strip('.')) for k in keys}
  if s.get('type')=='array':
   count={'industrial':industrial,'finance':finance,'share_classes':classes}.get(path,horizon-int(stub) if path.endswith('.forecast') else horizon if path=='timing.time_to_cashflow' else s.get('minItems',0))
   return [walk(s['items'],path+'.'+str(i)) for i in range(count)]
  # Single schema-version literals describe compatibility, not economic choices.
  if path=='schema_version':return s['enum'][0]
  if path=='horizon':return horizon
  return None
 return {'bases':bases,'input':walk(root,'')}

def describe():
 s=json.loads(SCHEMA.read_text());p=s['properties'];out={'root_required':s['required'],'horizon_semantics':'Horizon counts all periods: with stub, one stub plus horizon-1 full forecast rows for industrial and finance, and horizon explicit time slots. Values remain null.','atom_contract':'Each numeric/text atom uses explicit $basis and value; all unknowns stay null until analyst supplies them; compile_input.py validates. No financial values/default assumptions provided.'}
 def resolved(node):return s['$defs'][node['$ref'].split('/')[-1]] if '$ref' in node else node
 for name in ('industrial','finance','share_classes','bridge','consolidation','class_rights','sensitivity','timing','class_cashflows'):
  if name not in p:continue
  node=p[name]
  node=resolved(node)
  if node.get('type')=='array':node=resolved(node['items'])
  out[name]={'required':node.get('required',[]),'optional':sorted(set(node.get('properties',{}))-set(node.get('required',[])))}
  if name=='class_cashflows':
   cls=resolved(node['properties']['classes']['items']);event=resolved(node['properties']['parent_events']['items'])
   out[name].update(class_fields=cls.get('required',[]),event_fields=event.get('required',[]),
    build='Explicitly choose class_rights, then ModelBuilder.class_streams(supplied typed atoms). No payout/rights/terminal forecast defaults; numerical parent reconciliation is mandatory.')
 def enums(node,path=''):
  found={}
  if isinstance(node,dict):
   if 'enum' in node:found[path]=node['enum']
   for key,value in node.items():
    if key!='enum':found.update(enums(value,path+'/'+key))
  elif isinstance(node,list):
   for index,value in enumerate(node):found.update(enums(value,path+'/'+str(index)))
  return found
 out['allowed_enum_choices']=enums(s)
 try:from .input_units import describe_units
 except ImportError:from input_units import describe_units
 out['field_units']=describe_units()
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--describe',action='store_true');p.add_argument('--out',type=Path);p.add_argument('--industrial',type=int);p.add_argument('--finance',type=int);p.add_argument('--classes',type=int);p.add_argument('--horizon',type=int);p.add_argument('--stub',action='store_true');a=p.parse_args()
 if a.describe:print(json.dumps(describe(),ensure_ascii=False))
 else:
  if a.out is None or any(v is None for v in [a.industrial,a.finance,a.classes,a.horizon]):p.error('Output and every structural count required')
  data=skeleton(a.industrial,a.finance,a.classes,a.horizon,a.stub)
  with a.out.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2)
  print(json.dumps({'out':str(a.out),'unfilled_provenance_bases':len(data['bases']),'financial_approval':False,'instructions':'Fill explicit values/provenance in code; never dump the whole skeleton into context'}))
