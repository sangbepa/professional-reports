"""Company-independent fresh valuation stages, append-only observable timing.

The caller must supply actual sourced inputs and independent native receipts.
Neither a successful build nor synthetic fixtures constitute completed valuation.
"""
from pathlib import Path
import argparse,json,hashlib,time,sys,os,subprocess,copy,signal
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from adapters.valuation.model import calculate
from adapters.valuation.workbook import export,audit,recalculate
from pr.report_path import actor,envelope,captured
from adapters.valuation.report import prepare
from adapters.valuation.build import verify_vendor
from adapters.valuation.verify import verify_html
from adapters.valuation.schema_tools import validate_schema

PUBLICATION_TARGETS={'narrative.json','argument-record.json','publication-verification.json'}
PROFILE_TARGETS={'protected/evaluations/valuation-v1.json'}|{'protected/reviewer-profiles/valuation-2026-10-03.1/'+n for n in ('adoption.json','approval.json','candidate-reviewer-config.json','candidate-five-axis-anchors.md','candidate-reviewer-instructions.md')}

def validate_profile(out,review):
 snapshot=json.loads((out/'component-snapshot.json').read_text())
 references=review.get('evaluation_profile_hashes',{})
 root=Path(snapshot['root'])
 for relative in PROFILE_TARGETS:
  expected=snapshot.get('components',{}).get(relative)
  if not expected or references.get(relative)!=expected:raise ValueError('Review evaluation profile unbound: '+relative)
  if sha(root/relative)!=expected:raise ValueError('Protected evaluation changed after dispatch: '+relative)

def remaining(mandate):
 budget=mandate['requested_epoch']+585-time.time()
 if budget<=0:raise TimeoutError('Work cutoff exceeded; preserve this failed attempt, no clock reset')
 return budget

def native(cmd,out,log,mandate,limit):
 """Bound the entire process tree, including the PDF engine's child processes."""
 timeout=min(limit,remaining(mandate))
 with (out/log).open('x') as stream:
  proc=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,
                        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  try:proc.wait(timeout=timeout)
  except BaseException:
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   proc.wait()
   raise
 if proc.returncode:raise RuntimeError('Native publication process failed; see '+log)
 remaining(mandate)

def author_bindings(out,mandate):
 receipt=json.loads((out/'author-result.json').read_text())
 if receipt.get('kind')=='unreviewed_artifact_handoff':
  spawn=envelope(out,'author','spawn',mandate)
  identity=spawn['response'].get('agent_id');request=spawn['request']
  dispatch=json.loads((out/'dispatch.json').read_text())
  if not isinstance(identity,str) or not identity or request.get('fork_context') is not False or request.get('model','inherit')!='inherit' or request.get('message')!=dispatch['author_prompt']:raise ValueError('Fresh exact author spawn required')
  closed=json.loads((out/'author-interrupted-close.json').read_text())
  missing=json.loads((out/'author-interrupted-status.json').read_text())
  accepted=json.loads((out/'author-handoff-accepted.json').read_text())
  snapshot=json.loads((out/'author-input-snapshot.json').read_text())
  if closed.get('request',{}).get('target')!=identity or not isinstance(closed.get('response'),dict) or any(closed['response'].get(k) for k in ('error','errors','isError')) or 'previous_status' not in closed['response']:raise ValueError('Actual author close required')
  if missing.get('agent_id')!=identity or missing.get('response',{}).get('status',{}).get(identity)!='not_found':raise ValueError('Author host termination unconfirmed')
  if not mandate['requested_epoch']<=captured(snapshot)<=captured(spawn)<=captured(closed)<=captured(missing)<=captured(receipt)<=time.time():raise ValueError('Author handoff ordering invalid')
  if receipt.get('attempt_id')!=mandate['attempt_id'] or receipt.get('author_agent_id')!=identity or receipt.get('native_completion_claimed') is not False or receipt.get('financial_approval') is not False:raise ValueError('Unreviewed author handoff identity invalid')
  if receipt.get('input_snapshot_sha256')!=sha(out/'author-input-snapshot.json'):raise ValueError('Author input snapshot unbound')
  if set(snapshot.get('artifacts',{}))!={'valuation-input.json','model-result.json','model-verification.json'} or any(sha(out/n)!=h for n,h in snapshot['artifacts'].items()):raise ValueError('Immutable author inputs changed')
  from adapters.valuation.ready import validated
  hashes=validated(out,'author')
  if accepted.get('financial_approval') is not False or accepted.get('native_completion_claimed') is not False or accepted.get('readiness',{}).get('artifacts')!=hashes:raise ValueError('Author handoff not bound')
 else:
  identity,_,receipt,_=actor(out,'author',mandate)
 hashes={name:sha(out/name) for name in ('narrative.json','argument-record.json')}
 if receipt.get('artifacts')!=hashes or receipt.get('fresh_generation') is not True or receipt.get('no_previous_report_read') is not True:
  raise ValueError('Author result must bind exact fresh narrative and argument hashes')
 return identity,hashes

def publication_checks(out,verification):
 if verification.get('status')!='published':raise ValueError('Publication incomplete')
 required={'valuation-input.json','model-result.json','model-verification.json','narrative.json',
           'argument-record.json','author-result.json','report-input.json','report-bindings.json',
           'report.html','report.pdf','rendered.html','layout-checks.json','specification.json','render-status.json','input.json'}
 if not required.issubset(verification.get('artifacts',{})):raise ValueError('Publication bindings incomplete')
 for name,digest in verification['artifacts'].items():
  path=(out/name).resolve()
  if not path.is_relative_to(out.resolve()):raise ValueError('Publication artifact outside attempt')
  if sha(path)!=digest:raise ValueError('Publication artifact changed: '+name)
 if any(verification.get(key,{}).get('passed') is not True for key in ('html_bindings','rendered_bindings')):
  raise ValueError('Publication numeric binding checks failed')
 if verification.get('pdf',{}).get('status')!='rendered' or verification['pdf'].get('layout_passed') is not True:raise ValueError('PDF render incomplete')
 from pypdf import PdfReader
 pages=len(PdfReader(out/'report.pdf').pages)
 layout=json.loads((out/'layout-checks.json').read_text())
 coverage=layout.get('pages',[])
 if (pages<1 or layout.get('passed') is not True or len(coverage)!=pages
     or {p.get('page') for p in coverage}!=set(range(1,pages+1))
     or any(not isinstance(p.get(k),list) for p in coverage for k in ('overflow','horizontal','svgCollisions'))
     or any(p.get(k) for p in coverage for k in ('overflow','horizontal','svgCollisions'))):
  raise ValueError('Actual all-page renderer overflow checks required')

def publish(out,mandate):
 remaining(mandate)
 if any((out/name).exists() for name in ('publication-verification.json','report-input.json','report.html','report.pdf','assets')):
  raise ValueError('One fresh publication only; preserve previous output')
 status={'status':'incomplete','financial_review':'pending'}
 try:
  identity,authored=author_bindings(out,mandate)
  originals={name:sha(out/name) for name in ('valuation-input.json','model-result.json','model-verification.json')}
  verification=json.loads((out/'model-verification.json').read_text())
  if verification.get('input_sha256')!=originals['valuation-input.json'] or verification.get('result_sha256')!=originals['model-result.json']:
   raise ValueError('Model verification bound to stale input or result')
  recalc=verification.get('recalculation',{});checks=verification.get('audit',{})
  if recalc.get('status')!='passed' or any(recalc.get(k) is not True for k in ('recalculated','saved','reopened')) or checks.get('passed') is not True or checks.get('cached_values_required') is not True:
   raise ValueError('Saved and reopened recalculated spreadsheet required for publication')
  data=json.loads((out/'valuation-input.json').read_text())
  result=json.loads((out/'model-result.json').read_text())
  narrative=json.loads((out/'narrative.json').read_text())
  if not isinstance(narrative,dict) or set(narrative)-{'language','report_sections','section_order'}:
   raise ValueError('Narrative may override only data.report; numeric input override refused')
  if not narrative.get('report_sections'):raise ValueError('Authored report_sections required')
  arguments=json.loads((out/'argument-record.json').read_text())
  if not isinstance(arguments,dict) or not arguments:raise ValueError('Authored argument record required')
  data=copy.deepcopy(data);data['report']={**data.get('report',{}),**narrative}
  validate_schema(data)
  report,bindings=prepare(data,result)
  charts=[b['chart'] for s in report['report_sections'] for b in s['blocks'] if b['kind']=='chart']
  verify_vendor();remaining(mandate)
  save(out/'report-input.json',report)
  save(out/'report-bindings.json',{'input_sha256':originals['valuation-input.json'],
       'model_sha256':originals['model-result.json'],'author_agent_id':identity,
       'author_result_sha256':sha(out/'author-result.json'),'authored_artifacts':authored,'cells':bindings,'charts':charts})
  constructor=HERE/'vendor/report_outfit/build.py'
  native([sys.executable,str(constructor),'--input',str(out/'report-input.json'),'--mode','report',
          '--template','valuation','--design','executive','--out',str(out),'--html-only'],out,'native-build.log',mandate,60)
  status['html_bindings']=verify_html(out/'report.html',bindings,charts)
  if status['html_bindings']['passed'] is not True:raise ValueError('HTML numeric binding checks failed')
  # Use the existing renderer in an isolated process so its probes and children
  # share this attempt's remaining budget without changing the renderer API.
  script=('import json,sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
          'from adapters.valuation.render import render_pdf; '
          'out=Path(sys.argv[2]); status=render_pdf(out,"required"); '
          '(out/"render-status.json").write_text(json.dumps(status))')
  native([sys.executable,'-c',script,str(HERE.parents[1]),str(out)],out,'publication-render.log',mandate,225)
  status['pdf']=json.loads((out/'render-status.json').read_text())
  if status['pdf'].get('status')!='rendered' or status['pdf'].get('layout_passed') is not True:
   raise ValueError('PDF render incomplete or layout failed')
  status['rendered_bindings']=verify_html(out/'rendered.html',bindings,charts)
  for name,digest in originals.items():
   if sha(out/name)!=digest:raise ValueError('Immutable model artifact changed: '+name)
  current_identity,current_authored=author_bindings(out,mandate)
  if (identity,authored)!=(current_identity,current_authored):raise ValueError('Author binding changed during publication')
  names={'report-input.json','report-bindings.json','author-result.json','report.html','report.pdf',
         'rendered.html','layout-checks.json','specification.json','render-status.json','input.json'}|set(originals)|set(authored)
  names.update(p.relative_to(out).as_posix() for p in (out/'assets').rglob('*') if p.is_file())
  status.update(status='published',author_agent_id=identity,authored_artifacts=authored,
                original_artifacts=originals,artifacts={name:sha(out/name) for name in sorted(names)},
                native_constructor_sha256=sha(constructor),vendor_manifest_sha256=sha(HERE/'vendor/manifest.json'))
  publication_checks(out,status);remaining(mandate)
 except Exception as exc:
  status.update(status='incomplete',error=str(exc))
  save(out/'publication-verification.json',status)
  event(out,'publish','failed',error=str(exc),elapsed_seconds=time.time()-mandate['requested_epoch'])
  raise
 save(out/'publication-verification.json',status)

def validate_document_team(out,mandate,review,targets,author,reviewer):
 dispatch=json.loads((out/'dispatch.json').read_text())
 roles=('visual-left','visual-right')
 if not any(role+'_prompt' in dispatch for role in roles):return
 if not all(role+'_prompt' in dispatch for role in roles):raise ValueError('Incomplete document team dispatch')
 final_receipt=actor(out,'reviewer',mandate)[2]
 navigation=json.loads((out/'review-navigation.json').read_text())
 nav_hash=sha(out/'review-navigation.json');pdf_hash=targets['artifacts']['report.pdf']
 if targets['artifacts'].get('review-navigation.json')!=nav_hash:raise ValueError('Document navigation unbound')
 identities={author,reviewer};union=[];scores=[]
 for role in roles:
  identity,_,receipt,closed=actor(out,role,mandate)
  if captured(closed)>captured(final_receipt):raise ValueError('Document closure occurred after final reviewer completion')
  if identity in identities:raise ValueError('Independent distinct document reviewers required')
  identities.add(identity);name=role+'-review.json';digest=sha(out/name)
  if receipt.get('artifacts')!={name:digest} or review.get('document_review_refs',{}).get(role)!=digest:raise ValueError('Document review exact artifact unbound')
  d=json.loads((out/name).read_text());expected=navigation['document_assignments'][role]
  if d.get('reviewer_agent_id')!=identity or d.get('attempt_id')!=mandate['attempt_id'] or d.get('navigation_sha256')!=nav_hash or d.get('pdf_sha256')!=pdf_hash:raise ValueError('Stale document review identity or inputs')
  if d.get('scaffold_only') is True or d.get('visual_review_performed') is False:raise ValueError('Unreviewed document scaffold is not approval')
  score=d.get('document_quality_score')
  if d.get('status')!='pass' or type(score) is not int or not 3<=score<=4:raise ValueError('Document quality not passed')
  if any(f.get('severity') in ('material','major','high','critical') for f in d.get('findings',[])):raise ValueError('Material document finding unresolved')
  pages=d.get('pdf_page_reviews',[])
  if len(pages)!=len(expected) or {p.get('page') for p in pages}!=set(expected) or any(p.get('pdf_sha256')!=pdf_hash or p.get('status')!='pass' or not p.get('scope') for p in pages):raise ValueError('Assigned document coverage incomplete')
  validate_profile(out,d);union.extend(pages);scores.append(score)
 reported=review.get('pdf_page_reviews',[])
 if {p['page'] for p in union}!={p.get('page') for p in reported}:raise ValueError('Document team coverage not propagated')
 for p in union:
  other=next(x for x in reported if x['page']==p['page'])
  if other!=p:raise ValueError('Final document coverage differs from actual scoped review')
 if review.get('axis_scores',{}).get('document_quality',5)>min(scores):raise ValueError('Final document score exceeds scoped evidence')

def validate_review(out, mandate, review, targets):
 """Require closed independent actors and current, physically inspectable outputs."""
 if (out/'author-result.json').is_file() and json.loads((out/'author-result.json').read_text()).get('kind')=='unreviewed_artifact_handoff':
  author,_=author_bindings(out,mandate)
 else:author,_,_,_=actor(out,'author',mandate)
 reviewer,_,_,_=actor(out,'reviewer',mandate)
 if author==reviewer or review.get('reviewer_agent_id')!=reviewer:
  raise ValueError('Independent actual native reviewer required')
 if review.get('attempt_id')!=mandate['attempt_id']:
  raise ValueError('Review attempt mismatch')
 artifacts=targets.get('artifacts',{})
 required={'valuation-input.json','model-result.json','model-verification.json','workbook/valuation.xlsx','report.html','report.pdf'}
 if not required.issubset(artifacts):raise ValueError('Full valuation artifact targets missing')
 for name,digest in artifacts.items():
  candidate=(out/name).resolve()
  if not candidate.is_relative_to(out.resolve()):raise ValueError('Artifact path outside attempt')
  if sha(candidate)!=digest:raise ValueError('Reviewed artifact changed: '+name)
 verification=json.loads((out/'model-verification.json').read_text())
 if verification.get('input_sha256')!=artifacts['valuation-input.json'] or verification.get('result_sha256')!=artifacts['model-result.json']:
  raise ValueError('Model verification bound to stale input or result')
 recalculation=verification.get('recalculation',{})
 checks=verification.get('audit',{})
 if recalculation.get('status')!='passed' or any(recalculation.get(k) is not True for k in ('recalculated','saved','reopened')) or checks.get('cached_values_required') is not True or checks.get('passed') is not True:
  raise ValueError('Saved and reopened recalculated spreadsheet required')
 from pypdf import PdfReader
 pages=len(PdfReader(out/'report.pdf').pages)
 coverage=review.get('pdf_page_reviews',[])
 if len(coverage)!=pages or {x.get('page') for x in coverage}!=set(range(1,pages+1)) or any(x.get('pdf_sha256')!=artifacts['report.pdf'] or x.get('status')!='pass' for x in coverage):
  raise ValueError('Actual current PDF page-by-page review coverage required')
 if review.get('reviewed_target_sha256')!=sha(out/'reviewed-target.json'):
  raise ValueError('Review targets unbound')
 if not PUBLICATION_TARGETS.issubset(artifacts):raise ValueError('Full valuation publication artifact targets missing')
 publication=json.loads((out/'publication-verification.json').read_text())
 identity,authored=author_bindings(out,mandate)
 if publication.get('author_agent_id')!=identity or publication.get('authored_artifacts')!=authored:
  raise ValueError('Publication bound to stale author')
 publication_checks(out,publication)
 validate_profile(out,review)
 validate_document_team(out,mandate,review,targets,author,reviewer)
 dispatch=json.loads((out/'dispatch.json').read_text())
 if 'analysis-reviewer_prompt' in dispatch:
  from adapters.valuation.analysis_review import validate as validate_analysis
  validate_analysis(out,mandate,json.loads((out/'analysis-review.json').read_text()),actor,validate_profile,review,targets)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
def event(out,stage,status,**extra):
 with (out/'events.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'stage':stage,'status':status,**extra},ensure_ascii=False)+'\n')
def preserve_producer_calculation_diagnostics(out):
 """Separate a producer's same-attempt scratch output from engine-owned outputs."""
 if (out/'model-verification.json').exists():raise ValueError('Existing calculation verification cannot be replaced')
 paths=[out/name for name in ('model-result.json','calculation-graph.json','workbook') if (out/name).exists()]
 if not paths:return
 folder=out/'producer-calculation-diagnostics';folder.mkdir(exist_ok=False);preserved={}
 for path in paths:
  if path.is_symlink() or (path.is_dir() and any(p.is_symlink() for p in path.rglob('*'))):raise ValueError('Diagnostic output cannot contain a symlink')
  files=[path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
  before={p.relative_to(out).as_posix():sha(p) for p in files}
  target=folder/path.name;path.rename(target)
  for old,digest in before.items():
   copied=folder/old
   if sha(copied)!=digest:raise ValueError('Preserved diagnostic hash changed')
   preserved[old]={'sha256':digest,'preserved_path':copied.relative_to(out).as_posix()}
 save(out/'producer-calculation-diagnostics.json',{'status':'unreviewed_producer_outputs_preserved','artifacts':preserved,'financial_approval':False,'official_model_recompute_required':True})
 event(out,'calculation_namespace','producer_diagnostics_preserved',artifacts=preserved)

def run(out,stage):
 m=json.loads((out/'mandate.json').read_text());elapsed=time.time()-m['requested_epoch']
 if (out/'attempt-result.json').exists():raise ValueError('Attempt already ended; preserve its outcome')
 if elapsed>=585:raise TimeoutError('Work cutoff exceeded; preserve this failed attempt, no clock reset')
 event(out,stage,'running',elapsed_seconds=elapsed)
 if stage=='model':
  data=json.loads((out/'valuation-input.json').read_text())
  if data['synthetic']:raise ValueError('A synthetic model cannot satisfy a full company valuation')
  from adapters.valuation.ready import validate_history_receipt
  validate_history_receipt(out)
  result,g=calculate(data);preserve_producer_calculation_diagnostics(out);save(out/'model-result.json',result);save(out/'calculation-graph.json',g.serializable());directory=out/'workbook';directory.mkdir()
  # Bind the tested authoring engine; do not silently switch to an untested
  # optional artifact engine with a four-minute subprocess allowance.
  engine=m.get('workbook_engine','openpyxl')
  if engine not in {'openpyxl','artifact'}:raise ValueError('Explicit supported workbook engine required')
  exported=export(data,g,directory,engine);recalc=recalculate(directory,g,'auto');checks=audit(directory/'valuation.xlsx',g,require_cached=recalc['status']=='passed')
  save(out/'model-verification.json',{'input_sha256':sha(out/'valuation-input.json'),'result_sha256':sha(out/'model-result.json'),'workbook':exported,'recalculation':recalc,'audit':checks,'full_economic_review':'pending'})
 elif stage=='publish':
  publish(out,m)
 elif stage=='finish':
  review=json.loads((out/'review.json').read_text());targets=json.loads((out/'reviewed-target.json').read_text())
  validate_review(out,m,review,targets)
  scores=review['axis_scores']
  if set(scores)!={'evidence','economics','calculation','decision_usefulness','document_quality'} or any(type(v)!=int or v<3 or v>4 for v in scores.values()) or sum(scores.values())<17 or review['status']!='pass':raise ValueError('Full independent review gate not met')
  if any(f.get('severity') in {'material','major','high','critical'} for f in review.get('findings',[])):raise ValueError('Unresolved material findings')
  if not all(review.get(k) is True for k in ['source_review_complete','calculation_review_complete','economic_review_complete','all_pdf_pages_reviewed']):raise ValueError('Four review channels incomplete')
  elapsed=time.time()-m['requested_epoch']
  if elapsed>600:raise TimeoutError('Delivery exceeded600seconds')
  save(out/'completion.json',{'status':'complete','elapsed_seconds':elapsed,'score':sum(scores.values()),'company':m['company'],'scope':m['scope'],'review_sha256':sha(out/'review.json'),'targets_sha256':sha(out/'reviewed-target.json'),'grading_basis':'unchanged approved calibration profile','professional_grader_calibration':'pending; no certification or release approval implied','release_promoted':False})
 else:raise ValueError('Unknown stage')
 if stage in {'model','publish'}:remaining(m)
 event(out,stage,'completed',elapsed_seconds=time.time()-m['requested_epoch'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['model','publish','finish']);p.add_argument('out',type=Path);a=p.parse_args()
 try:run(a.out.resolve(),a.stage)
 except Exception as e:
  event(a.out.resolve(),a.stage,'failed',error=str(e));print(json.dumps({'status':'incomplete','error':str(e)}));sys.exit(2)
