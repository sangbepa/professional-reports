"""Scoped original queries with complete file retention and bounded stdout.

This is evidence access, not an inference, valuation or source approval.
"""
import argparse,hashlib,json,re,copy
from pathlib import Path
try:
 from .source_cells import SourceCache
except ImportError:
 from source_cells import SourceCache

PATTERN=re.compile('Revenue|OperatingIncome|CashAndCash|Borrowing|LeaseLiabil|Noncontrolling|InvestmentsIn|Depreciation|Amortisation|PurchaseOf|매출액|영업이익|현금및현금|차입금|리스부채|비지배|관계기업|공동기업|감가상각|상각비|유형자산의 취득|무형자산의 취득|매출채권|재고자산|매입채무',re.I)

def packet(out):
 data=json.loads((out/'statement-facts.json').read_text());chosen={}
 for row in data['facts']:
  if PATTERN.search((row.get('account_id') or '')+' '+(row.get('account_name') or '')):
   name=row['source_file'];chosen.setdefault(name,[]).append({'row':row['row_index'],'statement':row['statement'],'account':row['account_name'],'id':row['account_id'],'exact':row['amount_exact'],'field':row['amount_field'],'currency':row['currency'],'missing_cumulative':row['missing_cumulative_amount']})
 refs={name:{'file':'sources/'+name,'sha256':hashlib.sha256((out/'sources'/name).read_bytes()).hexdigest()} for name in chosen}
 return {'identity':data['identity'],'cutoff':data['cutoff'],'sources':refs,'selected_original_rows':chosen,'limits':['Selection is an index, not an exhaustive balance sheet or valuation perimeter','All source values retain original account labels, cumulative column and units','Use scoped queries for additional accounts and note tables; no prior reports needed']}

class SourceReader:
 def __init__(self,out):self.out=Path(out);self.cache=SourceCache()
 def __enter__(self):return self
 def __exit__(self,*args):self.cache.verify()
 def select(self,kind,term='',year=None,table=None,source=None):return select(self.out,kind,term,year,table,source,cache=self.cache)
 def verify(self):self.cache.verify()

def select(out,kind,term='',year=None,table=None,source=None,cache=None):
 def read(path):return cache.data(path) if cache else json.loads(path.read_text())
 if kind=='facts':
  data=read(out/'statement-facts.json')['facts']
  return copy.deepcopy([r for r in data if (year is None or r['year']==year) and (not term or term.casefold() in ((r.get('account_name') or '')+' '+(r.get('account_id') or '')).casefold())])
 if kind=='tables':
  if table is None:
   data=read(out/'source-table-index.json')
   return copy.deepcopy([r for r in data if not r['wrapper'] and (not source or r['source_file']==source) and (not term or term.casefold() in json.dumps(r,ensure_ascii=False).casefold())])
  if not source:raise ValueError('Exact indexed source required with table number')
  p=(out/'sources'/source).resolve()
  if p.parent!=(out/'sources').resolve() or not source.endswith('.tables.json'):raise ValueError('Indexed table source required')
  data=read(p)
  digest=cache.digest(p) if cache else hashlib.sha256(p.read_bytes()).hexdigest()
  return copy.deepcopy([{'source_file':source,'source_sha256':digest,'zip_sha256':data.get('original_archive_sha256'),'member':data['member'],**r} for r in data['tables'] if r['table_index']==table])
 raise ValueError('Known query kind required')

def emit(out,results):
 folder=out/'reads';folder.mkdir(exist_ok=True)
 raw=json.dumps(results,ensure_ascii=False,indent=2);digest=hashlib.sha256(raw.encode()).hexdigest();path=folder/(digest+'.json')
 if not path.exists():path.write_text(raw)
 response={'result_file':str(path),'sha256':digest,'records':len(results) if isinstance(results,list) else None,'complete_result_preserved':True,'preview':raw[:3000],'preview_truncated':len(raw)>3000}
 printed=json.dumps(response,ensure_ascii=False)
 # Escapes may expand preview bytes; the console envelope still has a hard character cap.
 while len(printed)>4000:
  response['preview']=response['preview'][:-100];response['preview_truncated']=True;printed=json.dumps(response,ensure_ascii=False)
 return printed

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('kind',choices=['packet','facts','tables']);p.add_argument('--term',default='');p.add_argument('--year',type=int);p.add_argument('--table',type=int);p.add_argument('--source');a=p.parse_args();out=a.out.resolve()
 if a.kind=='packet':
  data=packet(out);target=out/'source-packet.json'
  with target.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2)
  print(json.dumps({'packet':str(target),'datasets':len(data['sources']),'financial_review':'not_performed'}))
 else:print(emit(out,select(out,a.kind,a.term,a.year,a.table,a.source)))
