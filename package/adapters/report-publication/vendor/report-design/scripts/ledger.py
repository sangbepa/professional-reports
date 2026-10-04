"""Append-only design execution log; hash-bound events generate both orchestration views."""
import argparse, hashlib, json, datetime
from pathlib import Path

def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def append(root,event):
 root=Path(root);root.mkdir(parents=True,exist_ok=True);p=root/'events.jsonl';prev=p.read_text().splitlines()[-1] if p.exists() and p.stat().st_size else ''
 event={'time':stamp(),**event,'previous_event_hash':hashlib.sha256(prev.encode()).hexdigest() if prev else None}
 with p.open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
def start(root,job,inputs,depends=(),actor='report-designer'):
 p=Path(root)/'events.jsonl';events=[json.loads(l)for l in p.read_text().splitlines()]if p.exists()else[]
 version=1+sum(e.get('job')==job and e['kind']=='start'for e in events)
 append(root,{'kind':'start','job':job,'version':version,'actor':actor,'depends':list(depends),'inputs':{str(Path(p).resolve()):digest(p) for p in inputs}})
def finish(root,job,outputs,passed,actor='report-designer',notes=''):
 events=[json.loads(l)for l in (Path(root)/'events.jsonl').read_text().splitlines()];starts=[e for e in events if e.get('job')==job and e['kind']=='start']
 if not starts:raise ValueError('Start a job before finishing it')
 current=all(Path(p).is_file()and digest(p)==h for p,h in starts[-1]['inputs'].items())
 append(root,{'kind':'finish','job':job,'version':starts[-1]['version'],'actor':actor,'passed':bool(passed and current),'inputs_current':current,'outputs':{str(Path(p).resolve()):digest(p) for p in outputs},'notes':notes})
def inspect(root):
 root=Path(root);plan=json.loads((root/'plan.json').read_text());lines=(root/'events.jsonl').read_text().splitlines()if(root/'events.jsonl').exists()else[];events=[json.loads(l)for l in lines]
 chain=all(e['previous_event_hash']==(hashlib.sha256(lines[i-1].encode()).hexdigest()if i else None)for i,e in enumerate(events));states={};details={}
 for j in plan['jobs']:
  es=[e for e in events if e.get('job')==j['id']];last=es[-1]if es else None;starts=[e for e in es if e['kind']=='start'];inputs=starts[-1]['inputs']if starts else{}
  state='planned'if not last else'running'if last['kind']=='start'else'verified'if last.get('passed')else'needs_revision'
  stale=[p for p,h in {**inputs,**(last.get('outputs',{})if last else{})}.items()if not Path(p).is_file()or digest(p)!=h]
  if stale or not chain:state='invalidated'
  states[j['id']]=state;details[j['id']]={'events':es,'stale_files':stale,'version':starts[-1]['version']if starts else 0}
 changed=True
 while changed:
  changed=False
  for j in plan['jobs']:
   if states[j['id']]!='planned'and any(states[d]in{'invalidated','needs_revision','running','planned'}for d in j.get('depends',[]))and states[j['id']]!='invalidated':states[j['id']]='invalidated';changed=True
 return {'chain_valid':chain,'states':states,'details':details}
def selection(root,record):
 r=json.loads(Path(record).read_text())
 if not r.get('selected') or not r.get('candidate_artifacts') or not r.get('reviewer'):raise ValueError('Selection needs selected, candidate_artifacts and reviewer')
 for p,h in r['candidate_artifacts'].items():
  if digest(p)!=h:raise ValueError('Stale selection artifact: '+p)
 append(root,{'kind':'select','record':str(Path(record).resolve()),'sha256':digest(record),'selected':r['selected'],'reviewer':r['reviewer']})
def graphs(root):
 import html
 root=Path(root);plan=json.loads((root/'plan.json').read_text());events=[json.loads(l) for l in (root/'events.jsonl').read_text().splitlines()]
 # These are deterministic views of observed records, never invented execution nodes.
 observation=inspect(root);summaries=[]
 for j in plan['jobs']:
  es=[e for e in events if e.get('job')==j['id']]; last=es[-1] if es else None
  state=observation['states'][j['id']]
  summaries.append({**j,'state':state,**observation['details'][j['id']]})
 (root/'work-specification.json').write_text(json.dumps({'plan':plan,'jobs':summaries,'events':events},ensure_ascii=False,indent=2))
 for actual in [False,True]:
  typ='execution' if actual else 'planned';lines=['flowchart TD'];cards=[]
  for i,j in enumerate(summaries):
   label=j['title']+(' / '+j['state'] if actual else '')
   lines.append('  N'+str(i)+'["'+label.replace('"',"'")+'"]')
   for d in j.get('depends',[]):
    di=next(k for k,v in enumerate(summaries) if v['id']==d);lines.append('  N'+str(di)+' --> N'+str(i))
   paths=sorted({p for e in j['events']for field in ['inputs','outputs']for p in e.get(field,{})})
   links=''.join('<li><a href="'+html.escape(Path(p).resolve().as_uri())+'">'+html.escape(Path(p).name)+'</a></li>'for p in paths)
   cards.append('<details id="'+html.escape(j['id'])+'"><summary>'+html.escape(label)+'</summary><ul>'+links+'</ul><pre>'+html.escape(json.dumps(j,ensure_ascii=False,indent=2))+'</pre></details>')
  (root/(typ+'.mmd')).write_text('\n'.join(lines)+'\n')
  # A local dependency view, with direct links to job records and artifacts; no CDN required.
  ranks={}
  for j in summaries:ranks[j['id']]=1+max((ranks[d]for d in j.get('depends',[])),default=-1)
  positions={};rows={}
  for j in summaries:
   rank=ranks[j['id']];row=rows.get(rank,0);rows[rank]=row+1;positions[j['id']]=(rank*220+10,row*110+15)
  width=max(x for x,y in positions.values())+220;height=max(y for x,y in positions.values())+100
  nodes='<svg viewBox="0 0 '+str(width)+' '+str(height)+'" style="width:100%;min-width:700px" xmlns="http://www.w3.org/2000/svg"><defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10" fill="#77958c"/></marker></defs>'
  for j in summaries:
   x,y=positions[j['id']]
   for dep in j.get('depends',[]):
    dx,dy=positions[dep];nodes+=f'<path d="M{dx+195} {dy+35}L{x} {y+35}" fill="none" stroke="#77958c" marker-end="url(#arrow)"/>'
  for j in summaries:
   x,y=positions[j['id']];color='#e5f4e5'if actual and j['state']=='verified'else'#f4e8dc'if actual and j['state']=='invalidated'else'#eef2f2'
   nodes+=f'<a href="#{html.escape(j["id"])}"><rect x="{x}" y="{y}" width="195" height="70" rx="3" fill="{color}" stroke="#7e9a90"/><text x="{x+10}" y="{y+26}" font-size="12">'+html.escape(j['title'])+f'</text><text x="{x+10}" y="{y+49}" font-size="10" fill="#56776b">'+html.escape(j['state']if actual else'planned')+'</text></a>'
  nodes+='</svg>'
  (root/(typ+'-orchestration.html')).write_text('<!doctype html><meta charset="utf-8"><title>'+typ+' orchestration</title><style>body{font:14px sans-serif;margin:40px;color:#153543}.graph{display:flex;flex-wrap:wrap;gap:14px;margin:25px 0}.graph a{border:1px solid #abc;padding:14px;text-decoration:none;color:inherit;max-width:230px}small{display:block;color:#467568;margin-top:8px}summary{cursor:pointer;padding:12px;background:#eef4f4}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:12px 0}</style><h1>'+typ+' orchestration</h1><div class="graph">'+nodes+'</div><pre>'+html.escape('\n'.join(lines))+'</pre>'+''.join(cards))
 (root/'work-specification.md').write_text('# 보고서 디자인 작업명세\n\n'+ '\n'.join('- '+j['title']+' — '+j['state']+'; 선행: '+', '.join(j.get('depends',[])) for j in summaries)+'\n\n기계 기록: work-specification.json · events.jsonl. 각 출력 및 검토는 실제 파일 해시에 연결됩니다.\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('cmd',choices=['start','finish','select','graphs','inspect']);p.add_argument('--root',required=True);p.add_argument('--job');p.add_argument('--files',nargs='*',default=[]);p.add_argument('--depends',nargs='*',default=[]);p.add_argument('--actor',default='report-designer');p.add_argument('--record');p.add_argument('--failed',action='store_true');p.add_argument('--notes',default='');a=p.parse_args()
 if a.cmd=='start':start(a.root,a.job,a.files,a.depends,a.actor)
 elif a.cmd=='finish':finish(a.root,a.job,a.files,not a.failed,a.actor,a.notes)
 elif a.cmd=='select':selection(a.root,a.record)
 elif a.cmd=='inspect':print(json.dumps(inspect(a.root),ensure_ascii=False,indent=2))
 else:graphs(a.root)
