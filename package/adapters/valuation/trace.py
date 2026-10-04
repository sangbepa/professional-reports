"""Export planned and observed orchestration from receipts; never certify a run."""
import argparse,hashlib,html,json
from pathlib import Path

def load(path):
 return json.loads(path.read_text()) if path.exists() else None

def export_trace(out):
 out=out.resolve();plan=load(out/'plan.json');mandate=load(out/'mandate.json')
 if plan is None or mandate is None:raise ValueError('Actual mandate and pre-dispatch plan required')
 records=[]
 for node in plan['nodes']:
  role=node['role'];names=[n for n in (role+'-spawn.json',role+'-result.json',role+'-close.json',role+'-stop-request.json',role+'-interrupted-close.json',role+'-interrupted-status.json',role+'-ready.json',role+'-handoff-accepted.json') if (out/n).exists()]
  spawn=load(out/(role+'-spawn.json'));result=load(out/(role+'-result.json'));stop=load(out/(role+'-stop-request.json'))
  identity=(spawn or {}).get('response',{}).get('agent_id')
  status='not_observed'
  if spawn:status='dispatched'
  if result:status='native_completion_observed' if not result.get('missing_artifacts') else 'native_completion_with_missing_artifacts'
  if stop:status='termination_requested'
  accepted=load(out/(role+'-handoff-accepted.json'))
  if accepted and accepted.get('native_completion_claimed') is False:status='handoff_accepted_unreviewed'
  outputs=[name for name in node.get('outputs',[]) if (out/name).is_file()]
  if not spawn and outputs:status='outputs_present_not_approved'
  records.append({'node':node,'actual_agent_id':identity,'observed_state':status,'receipts':names,'outputs':outputs})
 refs={}
 names={'plan.json','meta-selection.json','mandate.json','component-snapshot.json','source-acquisition.json','reviewed-target.json','review.json','completion.json','attempt-result.json'}
 for r in records:names.update(r['receipts']);names.update(r['outputs'])
 for name in sorted(names):
  p=out/name
  if p.is_file():refs[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 data={'attempt_id':mandate['attempt_id'],'original_requested_epoch':mandate['requested_epoch'],'claims_financial_approval':False,'plan':records,'references':refs,'completion_record':load(out/'completion.json'),'incomplete_record':load(out/'attempt-result.json')}
 signature=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 target=out/'execution-specification'/signature
 if target.exists():return {'status':'observable_records_reused','directory':str(target),'financial_approval':False,'nodes':len(records)}
 target.mkdir(parents=True,exist_ok=False)
 for kind in ('plan','execution'):
  lines=['flowchart TD'];cards=[]
  for i,r in enumerate(records):
   node=r['node'];label=node['id']+((' / '+r['observed_state']) if kind=='execution' else '')
   lines.append(f' n{i}["{label}"]');lines.append(f' click n{i} "nodes/{node["id"]}.html"')
   for parent in node.get('depends_on',[]):
    j=next((j for j,x in enumerate(records) if x['node']['id']==parent),None)
    if j is not None:lines.append(f' n{j} --> n{i}')
   for parent in node.get('consumes_before_completion',[]):
    j=next((j for j,x in enumerate(records) if x['node']['id']==parent),None)
    if j is not None:lines.append(f' n{j} -. completion evidence .-> n{i}')
   cards.append('<li><a href="nodes/'+html.escape(node['id'])+'.html">'+html.escape(label)+'</a></li>')
  (target/(kind+'.mmd')).write_text('\n'.join(lines)+'\n')
  (target/(kind+'.html')).write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+kind+' orchestration</title><h1>'+kind+'</h1><p>Each node opens actual inputs, outputs and receipts. Present output is not approval.</p><ol>'+''.join(cards)+'</ol><pre>'+html.escape('\n'.join(lines))+'</pre></html>')
 (target/'nodes').mkdir(exist_ok=True)
 for r in records:
  links=''.join('<li><a href="'+html.escape((out/n).as_uri(),quote=True)+'">'+html.escape(n)+'</a></li>' for n in r['receipts']+r['outputs'])
  (target/'nodes'/(r['node']['id']+'.html')).write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>'+html.escape(r['node']['id'])+'</h1><pre>'+html.escape(json.dumps(r,ensure_ascii=False,indent=2))+'</pre><ul>'+links+'</ul>')
 (target/'records.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 body=['# 작업명세',f"원래 요청: {mandate['original_request']}",'','파일 존재나 네이티브 작업 종료는 재무 검토 통과를 뜻하지 않습니다.','', '[계획 도식](plan.html) · [실행 도식](execution.html)','', '| 작업 | 관측 상태 | 실제 에이전트 |','|---|---|---|']
 body += [f"| [{r['node']['id']}](nodes/{r['node']['id']}.html) | {r['observed_state']} | {r['actual_agent_id'] or '미확인/결정적 코드'} |" for r in records]
 for kind in ('plan','execution'):
  body += ['', '## '+('계획 도식' if kind=='plan' else '실행 도식'),'', '```mermaid', (target/(kind+'.mmd')).read_text().rstrip(),'```']
 body += ['', '## 근거 파일']+[f"- [{name}]({ref['path']}) — `{ref['sha256']}`" for name,ref in refs.items()]
 (target/'REPRODUCTION.md').write_text('''# 계산 재현

component-snapshot.json에 고정된 코드 버전과 sources 원문 해시가 먼저 일치해야 합니다. 설치된 활성 버전과 이 개발 실행의 소스 버전은 별개입니다.

동일한 valuation-input.json을 고정된 adapters.valuation.model.calculate에 전달하면 (model-result, calculation-graph)를 반환합니다. 현재 model-result.json과 숫자별 허용 오차를 명시하여 대조합니다. 원문 추출은 requests.json으로 source_cells.py --requests --cutoff ORIGINAL_CUTOFF --verify를 실행해 재현합니다. 입력 변경은 새 작업과 새 검토를 요구하며, 기존 완료 기록을 재사용하면 안 됩니다.

Excel은 수식을 수정할 수 있으나 수정 후 다시 재계산·저장·재열기와 독립 검토가 필요합니다. 계산 재현은 가정의 경제적 타당성이나 새 보고서 완료를 뜻하지 않습니다.
''')
 (target/'WORK-SPECIFICATION.md').write_text('\n'.join(body)+'\n')
 return {'status':'observable_records_exported','directory':str(target),'financial_approval':False,'nodes':len(records)}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();print(json.dumps(export_trace(a.out)))
