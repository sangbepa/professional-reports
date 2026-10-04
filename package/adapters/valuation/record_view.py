"""Bounded, lossless-by-reference JSON inspection of current author artifacts.

This is navigation, not evidence approval or an authored report. Full records
remain on disk; continuation pointers never imply that omitted fields were read.
"""
import hashlib,json
from pathlib import Path

AUTHOR_FILES=frozenset(('author-navigation.json','evidence.json','judgments.json',
 'valuation-input.json','model-result.json','model-verification.json',
 'economic-calibration.json','economic-source-selections.json','equity-claim-calibration.json',
 'capital-evidence.json','accounting-evidence.json','calibration-registry.json',
 'calibration.json','economic-facts.json','economic-evidence.json','equity-claims.json',
 'historical-reconciliation.json','analysis-review-navigation.json','analysis-review-target.json',
 'audit-kit-manifest.json','source-audit.json','math-audit.json','capital-event-acquisition.json',
 'scenario-cases.json','scenario-analysis.json','terminal-capital-cases.json','terminal-capital-analysis.json'))

def encoded(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def escape(key):return str(key).replace('~','~0').replace('/','~1')

def resolve(data,pointer):
 if not pointer:return data
 if not pointer.startswith('/'):raise ValueError('JSON pointer must begin with slash')
 for part in pointer[1:].split('/'):
  # RFC 6901 escape sequences only; reject silently misaddressed paths.
  if '~' in part.replace('~0','').replace('~1',''):raise ValueError('Invalid JSON pointer escape')
  key=part.replace('~1','/').replace('~0','~')
  if isinstance(data,list):
   if not key.isdigit() or (len(key)>1 and key.startswith('0')):raise ValueError('Exact list index required')
   data=data[int(key)]
  elif isinstance(data,dict):data=data[key]
  else:raise ValueError('Pointer traverses a scalar')
 return data

def view(out,name,pointer='',offset=0,limit=4000):
 if name not in AUTHOR_FILES:
  if not (Path(out)/'valuation-input.json').is_file():raise ValueError('Author artifact is not registered')
  try:from .model_support import local_support
  except ImportError:from model_support import local_support
  if name not in local_support(out) or Path(name).suffix!='.json':raise ValueError('Author artifact is not registered')
 if isinstance(offset,bool) or not isinstance(offset,int) or offset<0:raise ValueError('Nonnegative offset required')
 if isinstance(limit,bool) or not isinstance(limit,int) or not 1600<=limit<=4000:raise ValueError('Output cap must be 1600..4000 characters')
 root=Path(out).resolve();path=(root/name).resolve()
 if not path.is_relative_to(root):raise ValueError('Artifact escaped current attempt')
 raw=path.read_bytes();data=json.loads(raw);value=resolve(data,pointer)
 result={'kind':'bounded_current_record_not_approval','file':name,'sha256':hashlib.sha256(raw).hexdigest(),
  'pointer':pointer,'offset':offset,'financial_approval':False}
 if isinstance(value,(dict,list)):
  pairs=list(value.items()) if isinstance(value,dict) else list(enumerate(value))
  if offset>len(pairs):raise ValueError('Offset exceeds container')
  result.update(type='object' if isinstance(value,dict) else 'array',total_items=len(pairs),items=[],next_offset=None)
  for key,item in pairs[offset:]:
   ref=pointer+'/'+escape(key);row={'key':key,'pointer':ref}
   if len(encoded(item))<=500:row['value']=item
   else:
    row.update(type='object' if isinstance(item,dict) else 'array' if isinstance(item,list) else 'string',
               size=len(item),read_pointer=ref,value_omitted=True)
   result['items'].append(row);result['next_offset']=offset+len(result['items']) if offset+len(result['items'])<len(pairs) else None
   if len(encoded(result))>limit:
    result['items'].pop();result['next_offset']=offset+len(result['items']);break
  if offset<len(pairs) and not result['items']:raise ValueError('Pointer metadata exceeds cap; use a shorter registered path')
 elif isinstance(value,str):
  if offset>len(value):raise ValueError('Offset exceeds text')
  end=min(len(value),offset+limit-650)
  result.update(type='string',total_characters=len(value),text=value[offset:end],next_offset=end if end<len(value) else None)
  while len(encoded(result))>limit and end>offset:
   end-=1;result.update(text=value[offset:end],next_offset=end)
  if end==offset and offset<len(value):raise ValueError('Pointer metadata exceeds cap')
 else:
  if offset:raise ValueError('Scalar offset must be zero')
  result.update(type='scalar',value=value,next_offset=None)
 if len(encoded(result))>limit:raise ValueError('Output metadata exceeds cap')
 if path.read_bytes()!=raw:raise ValueError('Artifact changed during bounded read')
 return result
