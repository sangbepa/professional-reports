"""Small explicit model-building API; no forecast or company defaults."""
import copy,json,math
from decimal import Decimal
try:
 from .source_cells import OUTPUT_SCALES
except ImportError:
 from source_cells import OUTPUT_SCALES
from pathlib import Path
try:from .input_units import canonical_unit
except ImportError:from input_units import canonical_unit
try:
 from .skeleton import skeleton
 from .compile_input import compile_input
except ImportError:
 from skeleton import skeleton
 from compile_input import compile_input

def original_source(observation,ledger):
 entry=ledger['sources'][observation['source_id']]
 return {'id':observation['id'],'uri':'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+entry['receipt'],'sha256':entry.get('original_archive_sha256',entry['sha256']),'locator':json.dumps({'index_file':entry['file'],'index_sha256':entry['sha256'],'selection':observation['locator'],'raw':observation['raw'],'period':observation['period_end'],'perimeter':observation['perimeter']},ensure_ascii=False,separators=(',',':'))}

class ModelBuilder:
 def __init__(self,*,industrial,finance,classes,horizon,stub):
  self.compact=skeleton(industrial,finance,classes,horizon,stub)
  self._money_observations={}
 def _target(self,path):
  parts=path.split('.');node=self.compact['input']
  for key in parts[:-1]:node=node[int(key)] if isinstance(node,list) else node[key]
  last=int(parts[-1]) if isinstance(node,list) else parts[-1]
  return node,last
 def plain(self,path,value):
  node,key=self._target(path)
  if isinstance(node[key],(dict,list)) or isinstance(value,(dict,list)):raise ValueError('Structural scalar only; financial atoms require provenance')
  node[key]=value;return self
 def atom(self,path,value,*,kind,source,unit=None,rationale,as_of):
  if kind not in {'evidence','assumption','synthetic'}:raise ValueError('Canonical kind must be evidence, assumption or synthetic')
  node,key=self._target(path);existing=node[key]
  if not isinstance(existing,dict) or set(existing)!={'$basis','value'}:raise ValueError('Exact declared atom path required')
  expected=canonical_unit(path,value)
  if unit is None:unit=expected
  if isinstance(value,(int,float)) and not isinstance(value,bool) and unit!=expected:raise ValueError(path+': unit must be '+expected)
  self._money_observations.pop(path,None)
  basis=existing['$basis'];self.compact['bases'][basis]={'kind':kind,'source':copy.deepcopy(source),'as_of':as_of,'unit':unit,'rationale':rationale};existing['value']=value;return self
 def observed(self,path,observation,ledger):
  if observation['value'] is None:raise ValueError('Missing observation cannot become a financial input')
  value=observation['value'];unit=observation['unit']
  if isinstance(value,(int,float)) and (isinstance(value,bool) or not math.isfinite(value)):raise ValueError('Finite observed scalar required')
  canonical={'fraction':'ratio','ratio':'ratio','shares':'shares','text':'text','KRW per share':'currency_per_share'}.get(unit,unit)
  money=unit in OUTPUT_SCALES and unit.startswith('KRW') and unit!='KRW per share'
  if money:canonical='amount'
  pending=None
  if money:
   scale=Decimal(str(OUTPUT_SCALES[unit]))
   if 'target_scale' in observation and Decimal(str(observation['target_scale']))!=scale:raise ValueError('Observed unit and declared scale disagree')
   raw_exact=observation.get('amount_exact')
   exact=Decimal(str(value if raw_exact is None else raw_exact))
   if not exact.is_finite() or float(exact)!=value:raise ValueError('Observed scalar and exact amount disagree')
   pending={'amount_exact':exact,'source_scale':scale,'output_unit':unit}
  self.atom(path,value,kind='evidence',source=original_source(observation,ledger),unit=canonical,rationale=observation['rationale']+'; '+observation['perimeter'],as_of=observation['period_end'])
  if pending is not None:self._money_observations[path]=pending
  return self
 def observed_id(self,path,identity,ledger):
  matches=[o for o in ledger['observations'] if o['id']==identity]
  if len(matches)!=1:raise ValueError('One exact observation ID required')
  return self.observed(path,matches[0],ledger)
 def chosen(self,path,value,*,source,unit=None,rationale,as_of,kind='assumption'):
  if kind not in {'assumption','derived'}:raise ValueError('Chosen estimate/calculation must not masquerade as observation')
  if kind=='derived':rationale='[Calculated derivation, not an observed original; unreviewed] '+rationale
  return self.atom(path,value,kind='assumption',source=source,unit=unit,rationale=rationale,as_of=as_of)
 def class_streams(self,streams):
  """Register supplied typed owner flows after an explicit method choice.

  No distributions, terminal claims, rights or provenance are manufactured.
  Canonical atoms become unreviewed registered bases, never imported approvals.
  """
  if self.compact['input']['class_rights'].get('value')!='explicit_distribution_streams':raise ValueError('Select explicit_distribution_streams before attaching supplied flows')
  if 'class_cashflows' in self.compact['input']:raise ValueError('Class cashflows already registered')
  required={'value','kind','source','as_of','rationale','unit'}
  additions={}
  def register(node,path):
   if isinstance(node,list):return [register(v,path+'.'+str(i)) for i,v in enumerate(node)]
   if not isinstance(node,dict):return copy.deepcopy(node)
   if 'value' in node:
    if not required.issubset(node) or set(node)-required-{'review'}:raise ValueError('Complete supplied financial atom required: '+path)
    if node.get('review',{'status':'unreviewed','reviewer':'','reference':''})!={'status':'unreviewed','reviewer':'','reference':''}:raise ValueError('Imported approval cannot override independent review')
    if node['kind'] not in ('evidence','assumption','synthetic'):raise ValueError('Explicit supported atom kind required')
    if isinstance(node['value'],(int,float)) and node['unit']!=canonical_unit(path,node['value']):raise ValueError('Supplied class atom unit disagrees with fixed contract: '+path)
    additions[path]={k:copy.deepcopy(node[k]) for k in required-{'value'}}
    return {'$basis':path,'value':copy.deepcopy(node['value'])}
   return {k:register(v,path+'.'+k) for k,v in node.items()}
  registered=register(streams,'class_cashflows')
  self.compact['bases'].update(additions);self.compact['input']['class_cashflows']=registered
  for i,cls in enumerate(self.compact['input']['share_classes']):
   for key in ('participation_weight','fixed_claim_per_share'):
    cls.pop(key,None);self.compact['bases'].pop('share_classes.'+str(i)+'.'+key,None)
  return self
 def result(self):
  compact=copy.deepcopy(self.compact)
  if self._money_observations:
   if compact['input']['currency']!='KRW':raise ValueError('Explicit KRW model currency required for KRW observations')
   chosen=compact['input']['amount_scale']['value']
   if isinstance(chosen,bool) or not isinstance(chosen,(int,float)) or not math.isfinite(chosen) or chosen<=0:raise ValueError('Explicit positive model amount scale required')
   scale=Decimal(str(chosen))
   for path,observation in self._money_observations.items():
    node=compact['input'];parts=path.split('.')
    for key in parts:node=node[int(key)] if isinstance(node,list) else node[key]
    value=observation['amount_exact']*observation['source_scale']/scale
    if not math.isfinite(float(value)):raise ValueError('Normalized observation must be finite')
    node['value']=float(value);basis=compact['bases'][node['$basis']]
    loc=json.loads(basis['source']['locator']);loc['normalization']={'observation_output_unit':observation['output_unit'],'observation_scale':str(observation['source_scale']),'model_amount_scale':str(scale),'canonical_unit':'amount','operation':'observed_value * observation_scale / model_amount_scale'}
    basis['source']['locator']=json.dumps(loc,ensure_ascii=False,separators=(',',':'))
  return compile_input(compact)
 def write(self,path):
  data=self.result()
  with Path(path).open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
  return data
