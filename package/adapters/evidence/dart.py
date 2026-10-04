#!/usr/bin/env python3
"""Freeze OpenDART filing metadata and originals without exposing credentials."""
import argparse
from datetime import datetime,timezone
import hashlib,io,json,os,time,urllib.parse,urllib.request,zipfile
from pathlib import Path

BASE='https://opendart.fss.or.kr/api/'

def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def sha(data):return hashlib.sha256(data).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()

def fetch(endpoint,params,out,name):
 key=os.environ.get('OPENDART_API_KEY')
 if not key:raise RuntimeError('OPENDART_API_KEY unavailable')
 start=time.monotonic();requested=utc();url=BASE+endpoint+'?'+urllib.parse.urlencode(dict(params,crtfc_key=key))
 try:
  with urllib.request.urlopen(url,timeout=45) as response:raw=response.read()
 except Exception as exc:
  write(out/(name+'.failure.json'),{'endpoint':endpoint,'parameters':params,'requested_at':requested,'error_type':type(exc).__name__,'elapsed_seconds':time.monotonic()-start})
  raise RuntimeError('DART fetch failed: '+type(exc).__name__) from None
 p=out/name;p.write_bytes(raw)
 record={'endpoint':BASE+endpoint,'parameters':params,'requested_at':requested,'retrieved_at':utc(),'path':name,'sha256':sha(raw),'bytes':len(raw),'elapsed_seconds':time.monotonic()-start}
 write(out/(name+'.provenance.json'),record);return raw,record

def collect(corp_code,start,end,out,receipt=None):
 if not corp_code.isdigit() or len(corp_code)!=8:raise ValueError('DART corporation code must be eight digits')
 if not all(d.isdigit() and len(d)==8 for d in (start,end)):raise ValueError('Date must be YYYYMMDD')
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 entries=[];records=[];page=1
 while True:
  raw,rec=fetch('list.json',dict(corp_code=corp_code,bgn_de=start,end_de=end,page_count=100,page_no=page),out,f'list-{page}.json');records.append(rec)
  data=json.loads(raw)
  if data.get('status')=='013':break
  if data.get('status')!='000':raise RuntimeError('DART listing status '+str(data.get('status')))
  entries.extend(data.get('list',[]))
  if page>=int(data.get('total_page',1)):break
  page+=1
  if page>100:raise RuntimeError('Unexpectedly large filing list; narrow request dates')
 document=None
 if receipt:
  match=next((r for r in entries if r['rcept_no']==receipt and r['corp_code']==corp_code),None)
  if not match:raise ValueError('Requested receipt not verified in company/date metadata')
  raw,rec=fetch('document.xml',dict(rcept_no=receipt),out,'filing.zip');records.append(rec)
  try:archive=zipfile.ZipFile(io.BytesIO(raw))
  except zipfile.BadZipFile:raise RuntimeError('DART returned non-archive document response') from None
  files=[];total=0
  for member in archive.infolist():
   name=Path(member.filename);total+=member.file_size
   if name.is_absolute() or '..' in name.parts or total>150*1024*1024:raise ValueError('Unsafe archive member or expanded size')
   if member.is_dir():continue
   p=out/'filing'/name;p.parent.mkdir(parents=True,exist_ok=True);data=archive.read(member);p.write_bytes(data);files.append({'path':str(p.relative_to(out)),'sha256':sha(data)})
  day=match['rcept_dt'];day=f'{day[:4]}-{day[4:6]}-{day[6:]}'
  document={'receipt':receipt,'entity':match['corp_name'],'stock_code':match['stock_code'],'title':match['report_nm'],'files':files,'published_at':None,
            'publication_window':{'not_before':day+'T00:00:00+09:00','not_after':day+'T23:59:59.999999+09:00','precision':'day','basis':'OpenDART company filing list rcept_dt; receipt bound to document.xml archive'},'publication_evidence':'list-*.json receipt identity and rcept_dt','model_input_review':'not_performed'}
 manifest={'source':'OpenDART','corp_code':corp_code,'documents':document,'filing_count':len(entries),'filings':entries,'requests':records,'credentials_saved':False}
 write(out/'manifest.json',manifest);return manifest

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corp-code',required=True);p.add_argument('--start',required=True);p.add_argument('--end',required=True);p.add_argument('--out',required=True);p.add_argument('--receipt');a=p.parse_args()
 result=collect(a.corp_code,a.start,a.end,a.out,a.receipt);print(json.dumps({'out':str(Path(a.out).resolve()),'filing_count':result['filing_count'],'downloaded_document':bool(result['documents'])}))
