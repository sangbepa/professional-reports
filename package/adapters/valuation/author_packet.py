"""Current author navigation and output contract; contains no authored arguments."""
import argparse,hashlib,json
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(out):
 out=Path(out).resolve();snapshot=json.loads((out/'author-input-snapshot.json').read_text())
 names={'valuation-input.json','model-result.json','model-verification.json'}
 if set(snapshot.get('artifacts',{}))!=names or any(sha(out/n)!=h for n,h in snapshot['artifacts'].items()):raise ValueError('Author input snapshot stale')
 result=json.loads((out/'model-result.json').read_text())
 schema=json.loads((Path(__file__).parent/'input.schema.json').read_text())['properties']['report']
 summary={p:{'value':v,'unit':result['units'][p],'token':'{{model:'+p+'|'+('percent' if result['units'][p]=='ratio' else 'amount')+'}}'} for p,v in result['values'].items() if p.startswith('bridge.') or (p.startswith('classes.') and p.endswith('.per_share'))}
 sources={}
 try:from .model_support import local_support
 except ImportError:from model_support import local_support
 support=local_support(out)
 for path,meta in result['input_metadata'].items():
  source=meta['source'];key=json.dumps(source,sort_keys=True)
  record=sources.setdefault(key,{'source':source,'input_paths':[],'review_status':'unreviewed'})
  record['input_paths'].append(path)
 packet={'kind':'author_navigation_not_approval','financial_approval':False,'input_snapshot_sha256':sha(out/'author-input-snapshot.json'),
  'inputs':snapshot['artifacts'],'report_schema':schema,'summary_values':summary,
  'registered_evidence_ids':sorted({m['source']['id'] for m in result['input_metadata'].values()}),
  'source_groups':list(sources.values()),'company':result['company'],'valuation_date':result['valuation_date'],
  'currency':result['currency'],'amount_scale':result['amount_scale'],
  'analysis_record_paths':sorted(set(support)|{n for n in ('evidence.json','judgments.json','scenario-cases.json','scenario-analysis.json','terminal-capital-cases.json','terminal-capital-analysis.json','economic-calibration.json','economic-source-selections.json','equity-claim-calibration.json','capital-evidence.json','accounting-evidence.json','calibration-registry.json','calibration.json','economic-facts.json','economic-evidence.json','equity-claims.json','historical-reconciliation.json') if (out/n).exists()}),
  'local_support_hashes':support,
  'contract':{'outputs':['narrative.json','argument-record.json'],'narrative_keys':['language','report_sections','section_order'],
   'numeric_text':'No literal numeric characters. Use {{model:exact.values.path|amount/percent/integer/raw}}, {{input:exact.input_metadata.path|format}} or {{context:company/valuation_date/currency}}. Percent only ratio units. Numeric claims only body blocks, not headings.',
   'evidence':'Block evidence_ids must be registered IDs; preserve observed/assumed and qualification distinctions.',
   'scope':'Choose decision-led sections and arguments yourself. Use current evidence and economic calibration; do not invent facts or recompute/change model inputs. Existing calculated tables append automatically unless explicit section_order is supplied.',
   'read_strategy':'Use author_packet.py ATTEMPT --read FILE --pointer /exact/path --offset N. Start with /contract, /summary_values and /analysis_record_paths in author-navigation.json. Follow next_offset; omitted values are not reviewed. Responses are capped at4000characters. Read relevant current calibration and qualifications; never dump full records. Save substantive drafts early and run ready.py author before returning.'}}
 with (out/'author-navigation.json').open('x') as f:json.dump(packet,f,ensure_ascii=False,indent=2)
 return {'status':'author_navigation_prepared','summary_values':len(summary),'sources':len(sources),'financial_approval':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--read');p.add_argument('--pointer',default='');p.add_argument('--offset',type=int,default=0);a=p.parse_args()
 if a.read:
  try:from .record_view import view,encoded
  except ImportError:from record_view import view,encoded
  print(encoded(view(a.out,a.read,a.pointer,a.offset)))
 else:print(json.dumps(build(a.out)))
