"""Fresh timed acquisition of listed Korean financial originals and table indices.

No forecast, method selection, materiality judgment or valuation is generated.
"""
import argparse,hashlib,io,json,re,time,zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal,InvalidOperation
from datetime import date
import xml.etree.ElementTree as ET
try:
 from .dart_probe import request,save
 from .dart_tables import extract
except ImportError:
 from dart_probe import request,save
 from dart_tables import extract

def facts(data,year,code,source_file):
 rows=[];cumulative=code!='11011'
 for index,row in enumerate(data.get('list',[])):
  field='thstrm_add_amount' if cumulative and row.get('sj_div') in {'IS','CIS'} else 'thstrm_amount'
  raw=row.get(field);amount=None
  if raw not in (None,'','-'):
   try:amount=str(Decimal(raw.replace(',','')))
   except InvalidOperation:pass
  rows.append({'source_file':source_file,'row_index':index,'receipt':row.get('rcept_no'),'statement':row.get('sj_div'),'account_id':row.get('account_id'),'account_name':row.get('account_nm'),'amount_field':field,'amount_raw':raw,'amount_exact':amount,'currency':row.get('currency'),'term_label':row.get('thstrm_nm'),'year':year,'report_code':code,'missing_cumulative_amount':cumulative and row.get('sj_div') in {'IS','CIS'} and amount is None})
 return rows

def capital_documents(events,latest,cutoff,limit=8):
 """Lexical acquisition candidates only; event meaning remains curator judgment."""
 endings={'11011':'1231','11013':'0331','11012':'0630','11014':'0930'}
 period=str(latest['year'])+endings[latest['code']];end=cutoff.replace('-','')
 candidates=[]
 for row in events.get('list',[]):
  receipt=row.get('rcept_no','');day=row.get('rcept_dt','');name=row.get('report_nm','')
  if re.fullmatch(r'\d{14}',receipt) and re.fullmatch(r'\d{8}',day) and period<day<=end and receipt[:8]==day and any(t in name for t in ('자기주식','감자','증자','주식소각','전환사채','교환사채')):
   candidates.append({'receipt':receipt,'publication_date':day,'report_name':name})
 unique={r['receipt']:r for r in candidates};ordered=[unique[k] for k in sorted(unique,reverse=True)]
 return ordered[:limit],{'latest_statement_period':period,'candidate_count':len(ordered),'selected_count':min(limit,len(ordered)),'omitted_receipts':[r['receipt'] for r in ordered[limit:]],'candidate_selection_complete':len(ordered)<=limit,'semantic_event_review':False}

def collect(out,stock,cutoff):
 date.fromisoformat(cutoff)
 if not re.fullmatch(r'\d{6}',stock):raise ValueError('Six-digit listed stock identity required')
 started=time.time();sources=out/'sources';sources.mkdir(parents=True,exist_ok=False);manifest=[];datasets=[]
 def get(endpoint,params,name):
  raw=request(endpoint,params);record=save(sources,name,raw,endpoint,params)
  return raw,record
 raw,record=get('corpCode.xml',{},'corporations.zip');manifest.append(record)
 with zipfile.ZipFile(io.BytesIO(raw)) as z:xml=z.read('CORPCODE.xml')
 found=[x for x in ET.fromstring(xml).findall('list') if (x.findtext('stock_code') or '').strip()==stock]
 if len(found)!=1:raise ValueError('Unambiguous listed identity required')
 identity={k:found[0].findtext(k) for k in ('corp_code','corp_name','stock_code')};corp=identity['corp_code'];year=int(cutoff[:4]);limit=cutoff.replace('-','')
 def financial(y,code):
  name=f'CFS-{y}-{code}.json';raw,record=get('fnlttSinglAcntAll.json',{'corp_code':corp,'bsns_year':str(y),'reprt_code':code,'fs_div':'CFS'},name);data=json.loads(raw)
  receipts={r.get('rcept_no','') for r in data.get('list',[])}
  admitted=data.get('status')=='000' and bool(receipts) and all(re.fullmatch(r'\d{14}',r) and r[:8]<=limit for r in receipts)
  return {'year':y,'code':code,'name':name,'data':data,'record':record,'admitted':bool(admitted)}
 latest=None
 for y,code in [(year,'11014'),(year,'11012'),(year,'11013'),(year-1,'11011')]:
  dataset=financial(y,code);datasets.append(dataset);manifest.append(dataset['record'])
  if dataset['admitted']:latest=dataset;break
 if latest is None:raise ValueError('No cutoff-admissible consolidated financial statement available')
 have={(d['year'],d['code']) for d in datasets}
 with ThreadPoolExecutor(max_workers=3) as pool:
  futures=[pool.submit(financial,y,'11011') for y in range(year-1,year-4,-1) if (y,'11011') not in have]
  for f in futures:
   d=f.result();datasets.append(d);manifest.append(d['record'])
 admitted=[d for d in datasets if d['admitted']];annual=next((d for d in admitted if d['code']=='11011'),None)
 receipts=[]
 for d in (latest,annual):
  if d:
   receipt=d['data']['list'][0]['rcept_no']
   if receipt not in receipts:receipts.append(receipt)
 tasks=[('document.xml',{'rcept_no':r},'filing-'+r+'.zip') for r in receipts]
 tasks+=[('stockTotqySttus.json',{'corp_code':corp,'bsns_year':str(latest['year']),'reprt_code':latest['code']},'share-totals.json'),('list.json',{'corp_code':corp,'bgn_de':str(year)+'0101','end_de':limit,'page_count':'100'},'current-filings.json')]
 with ThreadPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(get,*task) for task in tasks]
  for f in futures:
   raw,record=f.result();manifest.append(record)
   if record['file'].endswith('.zip'):
    extract(sources/record['file'],sources/(record['file']+'.tables.json'))
 events=json.loads((sources/'current-filings.json').read_text())
 capital,capital_coverage=capital_documents(events,latest,cutoff)
 extra=[r for r in capital if r['receipt'] not in receipts]
 with ThreadPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(get,'document.xml',{'rcept_no':r['receipt']},'filing-'+r['receipt']+'.zip') for r in extra]
  for f in futures:
   raw,record=f.result();manifest.append(record);extract(sources/record['file'],sources/(record['file']+'.tables.json'))
 normalized=[row for d in admitted for row in facts(d['data'],d['year'],d['code'],d['name'])]
 table_index=[]
 for file in sources.glob('*.tables.json'):
  data=json.loads(file.read_text())
  for t in data['tables']:
   sizes=[len(c['text']) for r in t['rows'] for c in r]
   table_index.append({'source_file':file.name,'table_index':t['table_index'],'line':t['line'],'context':t['context'][-400:],'rows':len(t['rows']),'wrapper':bool(sizes and max(sizes)>2000),'head':[[c['text'][:120] for c in r] for r in t['rows'][:3]]})
 (out/'statement-facts.json').write_text(json.dumps({'identity':identity,'cutoff':cutoff,'facts':normalized,'scope':'Exact original values and explicit cumulative-column selection; not financial approval'},ensure_ascii=False,indent=2))
 (out/'source-table-index.json').write_text(json.dumps(table_index,ensure_ascii=False,indent=2))
 coverage={'available':events.get('status')=='000','total_count':events.get('total_count'),'retrieved_count':len(events.get('list',[])),'complete':len(events.get('list',[]))==events.get('total_count')}
 capital_coverage.update(filing_list_complete=coverage['complete'],documents=capital)
 (out/'capital-event-acquisition.json').write_text(json.dumps(capital_coverage,ensure_ascii=False,indent=2))
 summary={'status':'acquired','identity':identity,'information_cutoff':cutoff,'latest_period':{'year':latest['year'],'report_code':latest['code']},'dataset_admission':[{'file':d['name'],'status':d['data'].get('status'),'admitted':d['admitted']} for d in datasets],'originals':manifest,'filing_list_coverage':coverage,'elapsed_seconds':time.time()-started,'financial_review':'not_performed','company_research_time_excluded':False,'limitations':['Source table spans and perimeter must be assessed before normalization','Material capital events and forecast/claim judgments remain analyst work','A partial filing list cannot establish absence of capital changes']}
 (out/'source-acquisition.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));return {'status':summary['status'],'company':identity['corp_name'],'fact_count':len(normalized),'source_count':len(manifest),'seconds':round(summary['elapsed_seconds'],2)}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--stock',required=True);p.add_argument('--cutoff',required=True);a=p.parse_args()
 try:print(json.dumps(collect(a.out.resolve(),a.stock,a.cutoff),ensure_ascii=False))
 except Exception as e:print(json.dumps({'status':'incomplete','error':str(e)}));raise SystemExit(2)
