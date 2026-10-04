"""Readable work specifications and clickable plan/actual views from the ledger."""
import html
import json
from pathlib import Path
from .util import canonical, hash_data, write_json


def export(run):
    out=run.path/'views';out.mkdir(exist_ok=True)
    states=run.states();plan=run.plan or {'nodes':[]};reviews=run.reviews()
    risk = run.risk_status() if run.risk or run.header['request'].get('risk_mode') == 'enforced' else None
    cost = run.cost_status()
    write_json(out/'risk-status.json', dict(assessment=run.risk,status=risk))
    write_json(out/'cost-status.json', cost)
    record=dict(risk=run.risk,risk_status=risk,cost=cost,request=run.header['request'],release_sha256=run.header['release_sha256'],meta=run.meta,plan=run.plan,
                states=states,events=run.events,reviews=reviews,snapshots=run.snapshots(),timing=run.timing())
    write_json(out/'workspec.json',record)
    summary=['# 작업명세', '',f"요청: {run.header['request']['text']}",f"실행 릴리스: {run.header['release_sha256']}",
             '', '상태·수행 시간은 실제 원장 이벤트에서 생성합니다. 숨은 사고 과정은 기록하지 않습니다.','']
    cards=[]
    for n in plan['nodes']:
        s=states[n['id']];a=run.attempt(s['attempt_id']) if s['attempt_id'] else None
        r=run.result(s['attempt_id']) if s['attempt_id'] else None
        b=run.binding(s['attempt_id']) if s['attempt_id'] else None
        summary.extend([f"## {n['id']} — {n['goal']}",f"상태: {s['status']} / 버전: {n['revision']}",f"선행: {', '.join(n['depends_on']) or '없음'}",
                        f"근거: {', '.join(x['clause'] for x in n['basis'])}",f"수행 주체: {b['agent_id'] if b else '미수행'}",''])
        node_data=dict(node=n,state=s,binding=b,attempt=a,result=r,reviews=[v for v in reviews if v['attempt_id']==s['attempt_id']])
        write_json(out/f"node-{n['id']}.json",node_data)
        links=[]
        for f in (r or {}).get('artifacts',[]):links.append(f"<a href='../{html.escape(f['path'],quote=True)}'>{html.escape(f['name'])}</a>")
        for i in (a or {}).get('inputs',[]):links.append(f"<a href='../{html.escape(i['path'],quote=True)}'>원문 {html.escape(i['id'])}</a>")
        cards.append(f"<article id='node-{html.escape(n['id'],quote=True)}'><h2>{html.escape(n['goal'])}</h2><p>{html.escape(s['status'])} · {html.escape(n['id'])} v{n['revision']}</p><p>선행: {html.escape(', '.join(n['depends_on']))}</p><a href='node-{html.escape(n['id'],quote=True)}.json'>입력·배정·결과·검토 기록</a><p>{' · '.join(links)}</p></article>")
    (out/'workspec.md').write_text('\n'.join(summary),encoding='utf-8')
    for mode in ('plan','execution'):
        lines=['flowchart TD']
        for n in plan['nodes']:
            status='planned' if mode=='plan' else states[n['id']]['status']
            label=(n['id']+' / '+status).replace('"',"'")
            lines.append(f'  {n["id"].replace("-","_")}["{label}"]')
            lines.append(f'  click {n["id"].replace("-","_")} "index.html#node-{n["id"]}" "Open work record"')
            for dep in n['depends_on']:lines.append(f'  {dep.replace("-","_")} --> {n["id"].replace("-","_")}')
        (out/f'{mode}.mmd').write_text('\n'.join(lines)+'\n')
    # Native HTML graph: no remote JS/CDN, real links on every task, includes historical plan revisions.
    positions={};layer=0;pending={n['id']:set(n['depends_on']) for n in plan['nodes']}
    while pending:
        ready=sorted(k for k,v in pending.items() if not v)
        for col,k in enumerate(ready):positions[k]=(30+col*245,35+layer*108)
        pending={k:v-set(ready) for k,v in pending.items() if k not in ready};layer+=1
    width=max([x+250 for x,y in positions.values()]+[700]);height=max(180,layer*108+30)
    def graph(actual):
        svg=[f"<svg viewBox='0 0 {width} {height}' role='img' aria-label='작업 의존관계'>"]
        for n in plan['nodes']:
            x,y=positions[n['id']]
            for dep in n['depends_on']:
                px,py=positions[dep];svg.append(f"<path d='M {px+100} {py+60} L {x+100} {y}' stroke='#91a5b0' fill='none'/>")
        for n in plan['nodes']:
            x,y=positions[n['id']];s=states[n['id']]['status'] if actual else 'planned'
            color='#d4efdc' if s=='verified' else '#eaf0f3'
            svg.append(f"<a href='#node-{html.escape(n['id'],quote=True)}'><rect x='{x}' y='{y}' width='220' height='64' rx='8' fill='{color}'/><text x='{x+12}' y='{y+23}'>{html.escape(n['id'])}</text><text x='{x+12}' y='{y+47}'>{html.escape(s)}</text></a>")
        return ''.join(svg)+"</svg>"
    history=''.join(f"<li><a href='../{html.escape(e['data']['object']['path'],quote=True)}'>계획 기록 #{e['seq']}</a></li>" for e in run.events if e['kind']=='plan_registered')
    page=f"""<!doctype html><html lang='ko'><meta charset='utf-8'><title>전문조직 실행 명세</title>
<style>body{{font:16px system-ui;color:#173245;background:#f3f5f4;max-width:1180px;margin:48px auto;padding:0 24px}}h1{{font-size:38px}}article{{background:white;padding:24px;margin:16px 0;border-radius:12px}}svg{{width:100%;background:white;border-radius:12px}}svg text{{font-size:13px}}a{{color:#076b72}}pre{{white-space:pre-wrap}}</style>
<h1>{html.escape(run.header['request']['text'])}</h1><p>메타 선택 → 프로젝트 계획 → 실제 수행 · 릴리스 {run.header['release_sha256'][:16]}</p>
<a href='workspec.json'>구조화 명세</a> · <a href='workspec.md'>읽기용 명세</a> · <a href='risk-status.json'>위험·검토 근거</a> · <a href='cost-status.json'>수행원가 기록</a><h2>계획 도식</h2>{graph(False)}<h2>실행 도식</h2>{graph(True)}<ul>{history}</ul>{''.join(cards)}
<h2>시간 측정</h2><pre>{html.escape(json.dumps(run.timing(),ensure_ascii=False,indent=2))}</pre></html>"""
    (out/'index.html').write_text(page,encoding='utf-8')
    return dict(index=str(out/'index.html'),workspec=str(out/'workspec.json'),record_sha256=hash_data(record))
