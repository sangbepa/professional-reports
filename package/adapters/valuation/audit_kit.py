"""Prebuilt independent numerical/source checks, never a reviewer verdict."""
import argparse,hashlib,json
from pathlib import Path
try:
 from .source_audit import audit_sources
 from .math_audit import audit_files
except ImportError:
 from source_audit import audit_sources
 from math_audit import audit_files

FILES={'source':'source-audit.json','math':'math-audit.json'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
def generate(out):
 out=Path(out).resolve()
 if any((out/n).exists() for n in (*FILES.values(),'audit-kit-manifest.json')):raise FileExistsError('Independent audit generation is append-only')
 source=audit_sources(out);math=audit_files(out)
 save(out/FILES['source'],source);save(out/FILES['math'],math)
 manifest={'kind':'precomputed_independent_arithmetic_not_approval','attempt_id':json.loads((out/'mandate.json').read_text())['attempt_id'],
  'analysis_target_sha256':sha(out/'analysis-review-target.json'),
  'audits':{kind:{'path':name,'sha256':sha(out/name),'status':receipt['status']} for kind,name,receipt in [('source',FILES['source'],source),('math',FILES['math'],math)]},
  'implementation_sha256':{n:sha(Path(__file__).with_name(n)) for n in ('source_audit.py','math_audit.py','audit_kit.py')},
  'financial_approval':False,'economic_approval':False,
  'limitations':'Original scalar/unit/cutoff and calculation replay only. No independent semantic/source-suitability judgment, chosen assumption or report approval.'}
 save(out/'audit-kit-manifest.json',manifest);return summary(out)

def summary(out):
 out=Path(out).resolve();m=json.loads((out/'audit-kit-manifest.json').read_text());receipts={}
 if set(m.get('audits',{}))!=set(FILES):raise ValueError('Audit receipts incomplete or unknown')
 if m.get('financial_approval') is not False or m.get('economic_approval') is not False:raise ValueError('Mechanical audits cannot grant approval')
 if m.get('analysis_target_sha256')!=sha(out/'analysis-review-target.json'):raise ValueError('Audit target stale')
 for kind,entry in m['audits'].items():
  if entry['path']!=FILES.get(kind) or sha(out/entry['path'])!=entry['sha256']:raise ValueError('Audit receipt changed')
  receipts[kind]=json.loads((out/entry['path']).read_text())
 s=receipts['source'];calc=receipts['math']
 return {'kind':m['kind'],'financial_approval':False,'economic_approval':False,'attempt_id':m['attempt_id'],
  'source':{'status':s['status'],'counts':s['counts'],'mismatches':s['mismatches'][:4],'full_receipt':FILES['source']},
  'math':{'status':calc['status'],'checked_paths':calc['checked_paths'],'issues':calc['issues'][:4],'full_receipt':FILES['math']},
  'terminal_diagnostics':calc['terminal_diagnostics'][:4],
  'additional_terminal_segments':max(0,len(calc['terminal_diagnostics'])-4),
  'review_duties':'Independently inspect original meaning/period/perimeter, assumption calibration, NCI/class rights, normalization and reinvestment. Use diagnostics as questions; never convert arithmetic pass into economic approval.'}

def validate(out):
 out=Path(out).resolve();m=json.loads((out/'audit-kit-manifest.json').read_text());summary(out)
 mandate=json.loads((out/'mandate.json').read_text())
 if m.get('attempt_id')!=mandate['attempt_id'] or m.get('financial_approval') is not False or m.get('economic_approval') is not False:raise ValueError('Audit manifest identity or approval invalid')
 for n,h in m['implementation_sha256'].items():
  if n not in ('source_audit.py','math_audit.py','audit_kit.py') or sha(Path(__file__).with_name(n))!=h:raise ValueError('Audit implementation changed')
 if set(m['implementation_sha256'])!={'source_audit.py','math_audit.py','audit_kit.py'}:raise ValueError('Audit implementations incomplete')
 current={'source':audit_sources(out),'math':audit_files(out)}
 for kind,receipt in current.items():
  if json.loads((out/FILES[kind]).read_text())!=receipt:raise ValueError('Independent audit no longer matches current inputs: '+kind)
  if receipt['status']!='passed' or m['audits'][kind]['status']!='passed':raise ValueError('Mechanical audit not passed: '+kind)
 return {'status':'passed','manifest_sha256':sha(out/'audit-kit-manifest.json'),'financial_approval':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--summary',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args();r=validate(a.out) if a.verify else summary(a.out) if a.summary else generate(a.out)
 text=json.dumps(r,ensure_ascii=False,separators=(',',':'),allow_nan=False)
 if len(text)>4000:
  text=json.dumps({'kind':'bounded_audit_summary','financial_approval':False,'full_summary':'audit-kit-manifest.json and source-audit.json/math-audit.json','source':r.get('source',{}).get('status'),'math':r.get('math',{}).get('status'),'notice':'Details exceed4000characters; use exact pointer reads, full receipts preserved.'},ensure_ascii=False)
 print(text)
