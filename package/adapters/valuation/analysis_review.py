"""Current-model independent review bindings before report composition.

No source or model is approved by this navigation generator. A separate actual
reviewer must complete and close; final report/HTML/PDF review remains required.
"""
import argparse,hashlib,json
from pathlib import Path
try:from .review_packet import protected_paths
except ImportError:from review_packet import protected_paths

REQUIRED={'valuation-input.json','model-result.json','model-verification.json',
 'workbook/valuation.xlsx','evidence.json','judgments.json','accounting-evidence.json',
 'capital-evidence.json','historical-reconciliation.json','mandate.json','selectors.json','history-spec.json'}
OPTIONAL={'calibration-registry.json','calibration.json','economic-calibration.json',
 'capital-event-acquisition.json','scenario-cases.json','scenario-analysis.json',
 'terminal-capital-cases.json','terminal-capital-analysis.json',
 'economic-facts.json','economic-evidence.json','economic-originals.json',
 'economic-source-selections.json','equity-claim-calibration.json','equity-claims.json'}
AXES={'evidence','economics','calculation'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def build(out):
 out=Path(out).resolve();m=json.loads((out/'mandate.json').read_text())
 names=REQUIRED|{n for n in OPTIONAL if (out/n).exists()}
 try:from .model_support import local_support
 except ImportError:from model_support import local_support
 names.update(local_support(out))
 names|={p.relative_to(out).as_posix() for p in (out/'sources').rglob('*') if p.is_file()}
 artifacts={}
 for n in sorted(names):
  p=(out/n).resolve()
  if not p.is_relative_to(out):raise ValueError('Analysis artifact escaped attempt')
  artifacts[n]=sha(p)
 profiles=protected_paths(out)
 target={'attempt_id':m['attempt_id'],'artifacts':artifacts,'evaluation_profile_hashes':{p:v['sha256'] for p,v in profiles.items()}}
 write(out/'analysis-review-target.json',target)
 packet={'kind':'analysis_review_navigation_not_approval','financial_approval':False,
  'attempt_id':m['attempt_id'],'target_sha256':sha(out/'analysis-review-target.json'),
  'protected_profiles':profiles,'artifact_paths':sorted(names),
  'prebuilt_mechanical_audits':['audit-kit-manifest.json','source-audit.json','math-audit.json'],
  'output':'analysis-review.json','axes':sorted(AXES),
  'required_record_fields':['attempt_id','reviewer_agent_id','target_sha256','audit_manifest_ref','status','axis_scores',
   'source_review_complete','calculation_review_complete','economic_review_complete','findings',
   'evaluation_profile_hashes','scope'],
  'scope':'Original sources, current model and economic judgments only. No report, recommendation or document approval; final fresh report review remains mandatory.'}
 write(out/'analysis-review-navigation.json',packet)
 return {'status':'analysis_navigation_prepared','artifacts':len(artifacts),'financial_approval':False}

def starter(out):
 """Identity/provenance scaffolding only. Scores and review flags stay empty."""
 out=Path(out).resolve();nav=json.loads((out/'analysis-review-navigation.json').read_text());profiles=protected_paths(out)
 if profiles!=nav['protected_profiles'] or sha(out/'analysis-review-target.json')!=nav['target_sha256']:raise ValueError('Analysis navigation stale')
 identity=json.loads((out/'analysis-reviewer-spawn.json').read_text())['response']['agent_id']
 record={'attempt_id':nav['attempt_id'],'reviewer_agent_id':identity,'target_sha256':nav['target_sha256'],
  'audit_manifest_ref':sha(out/'audit-kit-manifest.json'),'status':'insufficient','axis_scores':{k:None for k in sorted(AXES)},
  'source_review_complete':False,'calculation_review_complete':False,'economic_review_complete':False,
  'findings':[],'evaluation_profile_hashes':{p:v['sha256'] for p,v in profiles.items()},
  'scope':'Not reviewed; identity/provenance scaffold only','scaffold_only':True}
 write(out/'analysis-review-draft.json',record)
 return {'kind':'analysis_role_start_not_approval','financial_approval':False,'agent_id':identity,
  'draft_path':str(out/'analysis-review-draft.json'),'protected_profiles':profiles,
  'instructions':'Read assigned approved profile and actual originals/judgments. Fill actual scores, findings and scope only after inspection. Save analysis-review.json, set scaffold_only=false. The draft and precomputed arithmetic are not a review.'}

def validate(out,mandate,record,actor_reader,profile_validator,final=None,targets=None):
 out=Path(out).resolve();identity,_,receipt,closed=actor_reader(out,'analysis-reviewer',mandate)
 for role in ('curator','analyst','author','reviewer','visual-left','visual-right'):
  p=out/(role+'-spawn.json')
  if p.exists() and json.loads(p.read_text())['response']['agent_id']==identity:raise ValueError('Independent distinct analysis reviewer required')
 h=sha(out/'analysis-review.json');target=json.loads((out/'analysis-review-target.json').read_text())
 if receipt.get('artifacts')!={'analysis-review.json':h}:raise ValueError('Analysis review receipt unbound')
 if record.get('reviewer_agent_id')!=identity or record.get('attempt_id')!=mandate['attempt_id'] or target.get('attempt_id')!=mandate['attempt_id']:raise ValueError('Analysis reviewer identity or attempt mismatch')
 if record.get('target_sha256')!=sha(out/'analysis-review-target.json'):raise ValueError('Analysis target unbound')
 if not REQUIRED.issubset(target.get('artifacts',{})):raise ValueError('Analysis targets incomplete')
 for n,digest in target['artifacts'].items():
  p=(out/n).resolve()
  if not p.is_relative_to(out) or sha(p)!=digest:raise ValueError('Analysis artifact changed: '+n)
  if targets is not None and targets.get('artifacts',{}).get(n)!=digest:raise ValueError('Analysis target not propagated: '+n)
 profiles=protected_paths(out)
 if target.get('evaluation_profile_hashes')!={p:v['sha256'] for p,v in profiles.items()}:raise ValueError('Analysis protected profile changed')
 profile_validator(out,record)
 scores=record.get('axis_scores',{})
 if record.get('status')!='pass' or set(scores)!=AXES or any(type(x)!=int or not 3<=x<=4 for x in scores.values()):raise ValueError('Independent analysis review not passed')
 if not all(record.get(k) is True for k in ('source_review_complete','calculation_review_complete','economic_review_complete')) or not record.get('scope'):raise ValueError('Analysis review scope incomplete')
 if record.get('scaffold_only') is True or any(f.get('material') is True or f.get('severity') in ('material','major','high','critical') for f in record.get('findings',[])):raise ValueError('Material analysis finding or unreviewed scaffold')
 if final is not None:
  from pr.report_path import captured
  final_receipt=actor_reader(out,'reviewer',mandate)[2]
  if captured(closed)>captured(final_receipt):raise ValueError('Analysis closure after final review')
  if final.get('analysis_review_ref')!=h or final.get('analysis_review_reuse_scope')!='unchanged_sources_model_only':raise ValueError('Analysis review reuse unbound')
  if final.get('new_report_claims_review_complete') is not True:raise ValueError('New report claims independently unreviewed')
  if any(final.get('axis_scores',{}).get(k,5)>v for k,v in scores.items()):raise ValueError('Final grade exceeds scoped analysis review')
 if (out/'dispatch.json').exists() and json.loads((out/'dispatch.json').read_text()).get('prebuilt_independent_audits') is True:
  try:from .audit_kit import validate as validate_kit
  except ImportError:from audit_kit import validate as validate_kit
  kit=validate_kit(out)
  if record.get('audit_manifest_ref')!=kit['manifest_sha256']:raise ValueError('Independent audit manifest unbound in scoped review')
 return {'status':'passed','reviewer_agent_id':identity,'sha256':h,'report_approval':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--start',action='store_true');a=p.parse_args();print(json.dumps(starter(a.out) if a.start else build(a.out),ensure_ascii=False))
