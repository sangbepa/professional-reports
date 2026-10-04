"""Reproduce explicitly selected original cells without LLM ledger boilerplate.

Experts choose coordinates, units, period and perimeter. Code verifies the exact
raw cell, admission and conversion; it supplies no economic/default assumption.
"""
import argparse,hashlib,json,re
from datetime import date
from decimal import Decimal
from pathlib import Path

SCALES={'KRW':Decimal(1),'KRW_thousand':Decimal(1000),'KRW_million':Decimal(1000000),'shares':Decimal(1),'fraction':Decimal(1),'percent':Decimal('.01'),'text':Decimal(1)}
UNIT_LABELS={'KRW':'원','KRW_thousand':'천원','KRW_million':'백만원','shares':'주','percent':'%','fraction':'비율'}
OUTPUT_SCALES={'KRW':1,'KRW per share':1,'KRW thousand':1000,'KRW million':1000000,'KRW billion':1000000000,'KRW trillion':1000000000000,'KRW_trillion':1000000000000,'shares':1,'fraction':1,'ratio':1,'text':1}

class SourceCache:
 """One invocation only; bind initial bytes and recheck all originals at exit."""
 def __init__(self):self.entries={}
 def raw(self,path):
  path=path.resolve()
  if path not in self.entries:
   raw=path.read_bytes();self.entries[path]={'raw':raw,'sha256':hashlib.sha256(raw).hexdigest(),'data':None}
  return self.entries[path]
 def data(self,path):
  entry=self.raw(path)
  if entry['data'] is None:entry['data']=json.loads(entry['raw'])
  return entry['data']
 def digest(self,path):return self.raw(path)['sha256']
 def verify(self):
  for path,entry in self.entries.items():
   if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Original changed during extraction: '+path.name)

def preceding_caption(data,table,index):
 caption=next((x for x in data['tables'] if x['table_index']==index),None)
 if caption is None or index!=table['table_index']-1 or not 0<len(caption['rows'])<=6 or caption.get('attributes',{}).get('border')!='0' or caption['line']>=table['line']:
  raise ValueError('Unit caption must be the immediately preceding small borderless heading table')
 # DART primary statements use a four-row, single-column heading: title,
 # comparative dates and exact unit. Do not confuse it with a data table or
 # borrow a caption from an earlier statement. Period/perimeter remain explicit
 # expert inputs and are independently reviewed; this only binds the unit cell.
 if len(caption['rows'])>2:
  rows=caption['rows']
  if any(len(row)!=1 for row in rows) or not re.fullmatch(r'(?:연결|별도)?\s*(?:재무상태표|손익계산서|포괄손익계산서|자본변동표|현금흐름표)',rows[0][0]['text'].strip()) or not any('단위' in row[0]['text'] for row in rows):
   raise ValueError('Long caption must be a single-column statement heading with exact unit')
  for row in rows[1:]:
   text=row[0]['text']
   if '단위' not in text and not re.search(r'\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}',text):
    raise ValueError('Statement heading contains an unrecognized data row')
 return caption

def requests_to_ledgers(out,spec,cutoff):
 """Resolve raw coordinates in code; preserve valid items and explicit gaps."""
 if set(spec)!={'requests'}:raise ValueError('Explicit request list required')
 expanded=[];gaps=[];ids=set();cache=SourceCache()
 ledgers={n:{'status':'extracted_unreviewed','observations':[],'sources':{},'gaps':[],'financial_approval':False} for n in ('accounting','capital')}
 for request in spec['requests']:
  q=dict(request);identity=q.get('id');group=q.get('output')
  if not isinstance(identity,str) or identity in ids or group not in ledgers:raise ValueError('Unique request ID and output required')
  ids.add(identity)
  try:
   source=(out/'sources'/q['source_file']).resolve()
   if source.parent!=(out/'sources').resolve():raise ValueError('Source path outside originals')
   data=cache.data(source);loc=q['locator']
   if q['kind']=='table':
    table=next(t for t in data['tables'] if t['table_index']==loc['table']);raw=table['rows'][loc['row']][loc['col']]['text']
    if q['source_unit']!='text' and 'unit_evidence' not in q:
     label=UNIT_LABELS[q['source_unit']];pattern=label if label=='%' else r'(?<![가-힣])'+re.escape(label)+r'(?![가-힣])'
     if re.search(pattern,table['context']):q['unit_evidence']={'quote':table['context']}
     else:
      for i,row in enumerate(table['rows'][:4]):
       for j,cell in enumerate(row):
        if re.search(pattern,cell['text']):q['unit_evidence']={'cell':{'row':i,'col':j},'quote':cell['text']};break
       if 'unit_evidence' in q:break
      if 'unit_evidence' not in q:
       try:caption=preceding_caption(data,table,table['table_index']-1)
       except ValueError:caption=None
       if caption:
        for i,row in enumerate(caption['rows']):
         for j,cell in enumerate(row):
          if '단위' in cell['text'] and re.search(pattern,cell['text']):q['unit_evidence']={'table':caption['table_index'],'cell':{'row':i,'col':j},'quote':cell['text']};break
         if 'unit_evidence' in q:break
   elif q['kind']=='json':
    raw=data
    for key in loc['path']:raw=raw[key]
   else:raise ValueError('Known source kind required')
   q['expected_raw']=raw
   if q['unit'] not in OUTPUT_SCALES:raise ValueError('Known explicit output unit required')
   scale=OUTPUT_SCALES[q['unit']]
   if 'target_scale' in q and Decimal(str(q['target_scale']))!=Decimal(scale):raise ValueError('Output unit and target scale disagree')
   q['target_scale']=scale
   result=extract(out,{'selectors':[q]},cutoff,_cache=cache)[group]
   expanded.append(q);ledgers[group]['observations'].extend(result['observations']);ledgers[group]['sources'].update(result['sources']);ledgers[group]['gaps'].extend(result['gaps'])
  except (ValueError,IndexError,KeyError,StopIteration,FileNotFoundError) as error:
   gap={'id':identity,'source_file':q.get('source_file'),'locator':q.get('locator'),'reason':type(error).__name__+': '+str(error),'value':None};gaps.append(gap);ledgers[group]['gaps'].append(gap)
 for ledger in ledgers.values():
  if ledger['gaps']:ledger['status']='partial_extraction_unreviewed'
 cache.verify()
 return {'selectors':expanded},ledgers,gaps

def save_generation(out,spec,expanded,results,gaps,revise=False):
 files={'requests-snapshot.json':spec,'selectors.json':expanded,'selection-gaps.json':gaps,**{group+'-evidence.json':ledger for group,ledger in results.items()}}
 existing=[out/name for name in files if (out/name).exists()]
 if existing:
  if not revise:raise ValueError('Existing extraction: use --revise to preserve the previous generation')
  signature=hashlib.sha256(b''.join(p.name.encode()+p.read_bytes() for p in sorted(existing))).hexdigest()
  history=out/'extraction-history'/signature;history.mkdir(parents=True,exist_ok=False)
  for path in existing:
   (history/path.name).write_bytes(path.read_bytes())
  for path in existing:path.unlink()
 for name,data in files.items():
  with (out/name).open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2)

def number(raw):
 if raw is None:return None
 text=str(raw).strip().replace(',','').replace('−','-')
 if text in ('','-','—'):return None
 if text.startswith('(') and text.endswith(')'):text='-'+text[1:-1]
 if text.endswith('%'):text=text[:-1]
 if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?',text):raise ValueError('Ambiguous numeric cell; explicit original required')
 return Decimal(text)

def extract(out,spec,cutoff,_cache=None):
 cache=_cache or SourceCache()
 date.fromisoformat(cutoff)
 if set(spec)!={'selectors'} or not isinstance(spec['selectors'],list):raise ValueError('Explicit selector list required')
 ledgers={name:{'status':'extracted_unreviewed','observations':[],'sources':{},'gaps':[],'financial_approval':False} for name in ('accounting','capital')};seen=set()
 for item in spec['selectors']:
  required={'id','output','source_file','kind','locator','source_unit','target_scale','unit','period_end','perimeter','rationale','expected_raw'}
  if not required.issubset(item) or item['id'] in seen:raise ValueError('Unique complete selection required')
  if item['output'] not in ledgers:raise ValueError('Accounting or capital output required')
  seen.add(item['id']);ledger=ledgers[item['output']];source_unit=item['source_unit']
  if source_unit not in SCALES:raise ValueError('Unsupported explicitly declared unit')
  if date.fromisoformat(item['period_end'])>date.fromisoformat(cutoff):raise ValueError('After-cutoff observation period')
  p=(out/'sources'/item['source_file']).resolve()
  if p.parent!=(out/'sources').resolve() or not p.is_file():raise ValueError('Preserved local original/index required')
  data=cache.data(p);locator=item['locator'];parent=None;context='';archive=None
  if item['kind']=='table':
   tables=[t for t in data['tables'] if t['table_index']==locator['table']]
   if len(tables)!=1:raise ValueError('Exact indexed table required')
   t=tables[0];raw=t['rows'][locator['row']][locator['col']]['text'];context=t['context']
   archive=p.with_name(p.name.removesuffix('.tables.json'))
   if not archive.is_file() or cache.digest(archive)!=data.get('original_archive_sha256'):raise ValueError('Table index is not bound to preserved original archive')
   receipt=re.search(r'filing-(\d{14})',p.name)
   receipt=receipt.group(1) if receipt else None
  elif item['kind']=='json':
   raw=data;receipt=None
   for key in locator['path']:
    parent=raw
    if isinstance(parent,dict) and parent.get('rcept_no'):receipt=parent['rcept_no']
    raw=raw[key]
   if isinstance(parent,dict):receipt=parent.get('rcept_no',receipt)
   # Interim income columns are cumulative; never silently accept quarter-only amounts.
   if isinstance(parent,dict) and parent.get('sj_div') in {'IS','CIS'} and re.search(r'CFS-\d{4}-(11012|11013|11014)',p.name):
    if locator['path'][-1]!='thstrm_add_amount':raise ValueError('Interim income requires cumulative field')
  else:raise ValueError('Known original selection kind required')
  if not receipt or not re.fullmatch(r'\d{14}',receipt) or receipt[:8]>cutoff.replace('-',''):raise ValueError('Unknown or after-cutoff publication quarantined')
  if str(raw).strip()!=str(item['expected_raw']).strip():raise ValueError('Selected original differs from expected exact cell')
  scale=Decimal(str(item['target_scale']))
  if not scale.is_finite() or scale<=0:raise ValueError('Positive explicit target scale required')
  if source_unit in {'shares','fraction','percent','text'} and scale!=1:raise ValueError('Nonmonetary units cannot use money scaling')
  if item['kind']=='json' and source_unit=='KRW':
   if not isinstance(parent,dict) or parent.get('currency')!='KRW':raise ValueError('Original currency evidence required')
  elif item['kind']=='json' and source_unit=='shares':
   if locator['path'][-1] not in {'istc_totqy','tsstk_co','distb_stock_co','istc_totqy_totqy','istc_totqy_cotc'}:raise ValueError('Documented share quantity field required')
  elif source_unit!='text':
   if item['kind']!='table':raise ValueError('Numeric JSON units need documented currency/quantity fields')
   evidence=item.get('unit_evidence',{})
   if source_unit=='percent' and str(raw).strip().endswith('%'):pass
   else:
    proof=context
    if 'cell' in evidence:
     c=evidence['cell'];unit_table=preceding_caption(data,t,evidence['table']) if 'table' in evidence else t;proof=unit_table['rows'][c['row']][c['col']]['text']
     if 'table' in evidence and '단위' not in proof:raise ValueError('Heading proof must explicitly label a unit')
    quote=evidence.get('quote','')
    label=UNIT_LABELS[source_unit]
    pattern=label if label=='%' else r'(?<![가-힣])'+re.escape(label)+r'(?![가-힣])'
    if not quote or quote not in proof or not re.search(pattern,quote):raise ValueError('Exact source unit evidence required')
  digest=cache.digest(p);source_id=item['source_file'];ledger['sources'][source_id]={'file':'sources/'+source_id,'sha256':digest,'publication_date':receipt[:4]+'-'+receipt[4:6]+'-'+receipt[6:8],'receipt':receipt}
  if archive:ledger['sources'][source_id].update({'original_file':'sources/'+archive.name,'original_archive_sha256':data['original_archive_sha256'],'member':data['member'],'xml_sha256':data['xml_sha256']})
  numeric=None if source_unit=='text' else number(raw)
  exact=str(raw) if source_unit=='text' else None if numeric is None else str(numeric*SCALES[source_unit]/scale)
  observation={k:item[k] for k in ('id','unit','period_end','perimeter','rationale')};observation.update({'value':str(raw) if source_unit=='text' else None if exact is None else float(exact),'amount_exact':exact,'raw':raw,'source_id':source_id,'locator':locator,'source_unit':source_unit,'target_scale':str(scale),'review':'unreviewed'})
  ledger['observations'].append(observation)
  if exact is None:ledger['gaps'].append({'id':item['id'],'reason':'Missing original scalar; not zero'})
 if _cache is None:cache.verify()
 return ledgers

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path,nargs='?');p.add_argument('selection',type=Path,nargs='?');p.add_argument('--cutoff');p.add_argument('--describe',action='store_true');p.add_argument('--verify',action='store_true');p.add_argument('--requests',action='store_true');p.add_argument('--revise',action='store_true');a=p.parse_args()
 if a.describe:
  print(json.dumps({'root':{'requests':'list of explicit coordinate requests; use --requests'},'generated':'selectors.json, selection-gaps.json and both evidence ledgers; preserve request versions before corrections','request_omissions':['expected_raw','target_scale','unit_evidence (optional explicit proof)'],'output_units':list(OUTPUT_SCALES),'required_request':['id','output (accounting/capital)','source_file (filename below sources)','kind (table/json)','locator','source_unit','unit','period_end','perimeter','rationale'],'locator_examples':{'table':{'table':'exact table_index','row':'zero-based row','col':'zero-based cell'},'json':{'path':['list','zero-based index','exact amount/quantity field']}},'unit_rules':'KRW/KRW_thousand/KRW_million monetary source units; explicit target_scale e.g trillion1e12. Code resolves declared units from context, same-table cells or the immediately preceding small borderless unit heading; generated unit_evidence retains exact table/cell/quote. Percent suffix is explicit evidence; percent uses fraction value and target_scale1. JSON currency/quantity fields must be documented. Missing values never become zero. No fiscal period, perimeter or fair value is inferred.'},ensure_ascii=False));raise SystemExit(0)
 if a.out is None or a.selection is None or a.cutoff is None:p.error('Attempt, selection file and cutoff required')
 out=a.out.resolve();spec=json.loads(a.selection.read_text())
 if a.requests:
  expanded,results,gaps=requests_to_ledgers(out,spec,a.cutoff)
 else:results=extract(out,spec,a.cutoff)
 if a.verify:
  if a.requests:
   for name,data in [('requests-snapshot.json',spec),('selectors.json',expanded),('selection-gaps.json',gaps)]:
    if json.loads((out/name).read_text())!=data:raise ValueError('Selection or gap record differs from current requests')
  for group,ledger in results.items():
   if json.loads((out/(group+'-evidence.json')).read_text())!=ledger:raise ValueError('Ledger differs from current selected originals')
  print(json.dumps({'status':'replayed_selected_originals','selection_sha256':hashlib.sha256(a.selection.read_bytes()).hexdigest(),'financial_approval':False}));raise SystemExit(0)
 if a.requests:save_generation(out,spec,expanded,results,gaps,a.revise)
 else:
  if a.revise:p.error('--revise requires --requests')
  for group,ledger in results.items():
   with (out/(group+'-evidence.json')).open('x') as f:json.dump(ledger,f,ensure_ascii=False,indent=2)
 print(json.dumps({'status':'extracted_unreviewed','observations':{k:len(v['observations']) for k,v in results.items()},'gaps':sum(len(v['gaps']) for v in results.values()),'financial_approval':False}))
