"""Bounded original-data acquisition; API credentials never enter stored URLs/logs."""
import argparse,hashlib,io,json,os,time,urllib.request,urllib.parse,zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import date

BASE='https://opendart.fss.or.kr/api/'
def request(endpoint,parameters):
 key=os.environ.get('OPENDART_API_KEY') or os.environ.get('DART_API_KEY')
 if not key:raise RuntimeError('OpenDART key unavailable')
 query=urllib.parse.urlencode(dict(parameters,crtfc_key=key))
 try:
  with urllib.request.urlopen(BASE+endpoint+'?'+query,timeout=25) as r:return r.read()
 except urllib.error.HTTPError as e:raise RuntimeError('OpenDART HTTP '+str(e.code)) from None
 except Exception as e:raise RuntimeError('OpenDART transport '+type(e).__name__) from None

def save(out,name,body,endpoint,parameters):
 if any(k.lower() in {'crtfc_key','api_key','authorization','password'} for k in parameters):
  raise ValueError('Credential parameters cannot be persisted')
 path=out/name
 with path.open('xb') as f:f.write(body)
 return {'file':name,'sha256':hashlib.sha256(body).hexdigest(),'uri':BASE+endpoint+'?'+urllib.parse.urlencode(parameters),'collected_epoch':time.time(),'credential_included':False}

def acquire(out,stock_code,year,report_code,cutoff=None):
 if cutoff is not None:date.fromisoformat(cutoff)
 started=time.time();out.mkdir(parents=True,exist_ok=True)
 if any(out.iterdir()):raise ValueError('Fresh acquisition directory required')
 body=request('corpCode.xml',{});manifest=[save(out,'corporations.zip',body,'corpCode.xml',{})]
 with zipfile.ZipFile(io.BytesIO(body)) as z:xml=z.read('CORPCODE.xml')
 candidates=[n for n in ET.fromstring(xml).findall('list') if (n.findtext('stock_code') or '').strip()==stock_code]
 if len(candidates)!=1:raise ValueError('Unambiguous listed entity identity required')
 corp=candidates[0];identity={k:corp.findtext(k) for k in ('corp_code','corp_name','stock_code','modify_date')}
 params={'corp_code':identity['corp_code'],'bsns_year':str(year),'reprt_code':report_code,'fs_div':'CFS'}
 body=request('fnlttSinglAcntAll.json',params);manifest.append(save(out,'financials.json',body,'fnlttSinglAcntAll.json',params));data=json.loads(body)
 rows=data.get('list',[])
 records=[]
 for row in rows:
  name=row.get('account_nm','')
  if any(s in name for s in ['비지배','관계기업','공동기업','현금및현금','차입금','리스','감가상각','상각비','유형자산의 취득','무형자산의 취득','매출채권','재고자산','매입채무','영업이익','매출액']):
   records.append({k:row.get(k) for k in ['rcept_no','sj_div','account_id','account_nm','thstrm_nm','thstrm_amount','thstrm_add_amount','frmtrm_nm','frmtrm_amount','currency']})
 receipts={r.get('rcept_no','') for r in rows}
 admitted=cutoff is not None and bool(receipts) and all(len(r)>=8 and r[:8].isdigit() and r[:8]<=cutoff.replace('-','') for r in receipts)
 availability='admitted_by_filing_receipt_date' if admitted else 'quarantined' if cutoff is not None else 'unassessed'
 result={'identity':identity,'status':data.get('status'),'message':data.get('message'),'period':{'year':year,'report_code':report_code,'basis':'consolidated'},'originals':manifest,'selected_rows':records,'information_cutoff':cutoff,'source_availability':availability,'elapsed_seconds':time.time()-started,'report_completed':False,'limits':'Financial statement amounts are not fair values; receipt date admission does not validate classification or estimate quality.'}
 (out/'acquisition.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 return {'status':data.get('status'),'company':identity['corp_name'],'row_count':len(rows),'selected_count':len(records),'out':str(out),'elapsed_seconds':round(result['elapsed_seconds'],2)}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--stock',required=True);p.add_argument('--year',required=True,type=int);p.add_argument('--report-code',default='11012');p.add_argument('--cutoff');a=p.parse_args()
 try:print(json.dumps(acquire(a.out,a.stock,a.year,a.report_code,a.cutoff),ensure_ascii=False))
 except Exception as e:print(json.dumps({'status':'failed','error':str(e)}));raise SystemExit(2)
