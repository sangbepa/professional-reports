"""Fresh numeric exhibits and bounded writer handoff, never a report-body fixture."""
from pathlib import Path
import json, sys, shlex, hashlib
ROOT=Path(__file__).resolve().parents[2]
def read(p): return json.loads(p.read_text())
def save(p,d):
    with p.open('x') as f: json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
def table(headers,rows,caption): return {'kind':'table','headers':headers,'rows':rows,'caption_html':caption}
def prepare(out):
    r=read(out/'analysis/result.json'); s=read(out/'analysis/stress.json'); v=read(out/'analysis/value-components.json')['values']; e=read(out/'analysis/comparison-evidence.json')
    pct=lambda x:f'{x*100:.2f}%'; num=lambda x:f'{x:,.3f}'; b=r['bridge_trillion_krw']; f=r['forecast']; shares=r['shares_million']
    residual=(s['zero_growth_price_after_full_haircut']-r['target_price'])*shares['outstanding']/1e6
    chart={'type':'bar','title':'고정 가정 아래 역산한 비금융 매출 경로','unit':'조원','categories':[str(x['year']) for x in f], 'series':[{'name':'자동차·기타 비금융 매출','values':[x['revenue'] for x in f],'result_paths':[f'forecast.{i}.revenue' for i in range(len(f))]}], 'note':'2027–2033 동일 성장률 역산. 관측 실적·시장 전망이 아닌 조건부 계산. analysis/result.json forecast.'}
    slots=['decision','cashflows','bridge','evidence','alternatives','actions']
    exhibits={
      'decision':[{'kind':'metrics','items':[{'value':pct(r['growth']),'label':'조건부 연간 비금융 매출 성장률'},{'value':f'{r["target_price"]:,.0f}원','label':'검증되지 않은 모델 가격 입력'},{'value':pct(v['terminal_share']),'label':'잔존가치 현재가치 / 비금융 EV'}]}],
      'cashflows':[{'kind':'chart','chart':chart},table(['연도','매출(조원)','영업이익률','FCFF(조원)','FCFF 현재가치(조원)'],[[str(x['year']),num(x['revenue']),pct(x['margin']),num(x['fcff']),num(x['pv'])] for x in f],'analysis/result.json forecast; 자동차·기타, 금융 제외. 2027–2033 동일 성장률. 운전자본 증감 음수는 축소에 따른 회수 가정.'),table(['EV 구성','현재가치(조원)'],[['잔여기간 100일',num(v['stub_pv'])],['명시적 7개 연도',num(v['explicit_pv'])],['잔존가치',num(v['terminal_pv'])],['비금융 EV',num(v['operating_ev'])]],'analysis/value-components.json values. 100일 잔여기간은 연간 예측과 별도이며 연간 PV 차액은 순수 잔존가치가 아님.')],
      'bridge':[table(['지분가치 연결','조원'],[['비금융 EV',num(b['industrial_ev'])],['비금융 순금융자산',num(b['nonfinancial_nfa'])],['금융부문 지분가치',num(b['finance_equity'])],['관계기업 가치',num(b['associates'])],['비지배지분 차감',num(-b['nci_deduction'])],['브리지 순합계 (EV 제외)',num(b['total'])],['지배주주 지분가치',num(b['parent_equity'])]],'analysis/result.json bridge_trillion_krw. 금융부문은 EV/부채 차감 대신 기존 지분가치 고정; NCI 장부값·리스·연결조정 경제적 적합성은 미해결.'),table(['주식수 연결','백만 주'],[['발행',f'{shares["issued"]:.6f}'],['자기주식 차감',f'{shares["treasury"]:.6f}'],['순주식수',f'{shares["outstanding"]:.6f}']],'2026년 Q2 모델 기준; 이후 변동 미대사. 보통·우선주 동일 경제적 권리 가정; 종가 검증 또는 Excel 저장·재열기 인증 없음.')],
      'evidence':[table(['근거 / 발표일','관측·가정','비교 한계'],[['HMC-2025 / 2026-01-29','2025 매출 186.2545조원·증가 6.3%; 2026 가이던스 1–2%','연결 잠정 미감사 실적/경영진 1년 가이던스'],['HMC-CID / 2026-08-26','2026 H1 성장 2.7%; 2030 판매 555만대·마진 9% 초과 목표','연결 반기/경영진 판매량·마진 목표, 매출 7년 전망 아님'],['MIRAE / 2026-01-19','자동차+기타 2023 140.263, 2024 146.784, 2025F 156.828, 2026F 166.865조원; 2026F 성장 6.40%','단일 브로커, 당시 전망; 시장 컨센서스·동일 7년 범위 아님']], 'analysis/source-originals/locator-index.json; Mirae 물리 p.2 Table2 Wbn을 조원 변환. 발표일 기준일 이전·수집일 2026-10-03 이후; 당시 동일 바이트 보존 증명 없음.')],
      'alternatives':[table(['금융+관계기업 공동 할인','새 역산 성장률','브리지 감소(조원)'],[[pct(x['haircut']),pct(x['growth']),num(x['bridge_reduction'])] for x in s['rows']],'analysis/stress.json rows. 진단용 가치 haircut이며 손상 추정·확률 아님. 나머지 가정 고정.'),table(['제로 성장 진단','계산값'],[['할인 전 조건부 가격',f'{s["zero_growth_price"]:,.2f}원'],['필요 공동 할인율',pct(s['zero_growth_haircut_threshold'])],['100% 할인 후 조건부 가격',f'{s["zero_growth_price_after_full_haircut"]:,.2f}원'],['가격 입력 대비 잔여 지분가치 차이',f'{residual:.6f}조원']], 'analysis/stress.json / analysis/result.json shares_million. 필요 할인율 >100%이므로 두 자산 비음수 조건에서 해 불가능; 잔여 차이의 원인은 식별되지 않음.')],
      'actions':[]}
    sources=[{'id':x['id'],'url':x['url'],'display_name':x['id']+' / '+x['published_at'],'locator':x['locator']} for x in e['observations']]+[{'id':'MODEL','url':'analysis/result.json','display_name':'이번 실행의 조건부 계산','locator':'forecast; bridge_trillion_krw; shares_million'}, {'id':'STRESS','url':'analysis/stress.json','display_name':'현재 가정의 대안 진단','locator':'rows; zero_growth_*'}]
    scaffold={'schema_version':2,'key':'valuation','audience':'투자위원회·이사회','scope':'현대차 / 2026-09-22 정보기준 / 고정 입력 조건부 역산 DCF; 전체 가치평가 아님','status':'조건부 분석 · 독립 내용 검토 전','headers':['구성','조원'],'rows':[[k,num(b[k])] for k in ['industrial_ev','total','parent_equity']], 'hero':[pct(r['growth']),'연간 / 2027–2033','조건부 비금융 매출 역산'], 'kpis':[[f'{r["target_price"]:,.0f}','원/주','미확인 모델 가격 입력'],[pct(v['terminal_share']),'비금융 EV 비중','잔존가치 현재가치']], 'chart':chart,'sources':sources,'unit_note':'금액 조원, 주당 원, 주식수 백만주. 금융부문 기존 지분가치 고정.','formula':'비금융 EV + 순금융자산 + 금융 지분가치 + 관계기업 가치 − 비지배지분 = 지배주주 지분가치','overview_mode':'integrated','report_footer':'현대차 | 2026-09-22 | 조건부 역산 진단 · 전체 가치평가 아님','design_boundary':'기존 executive 시안의 독립 분석용 재사용. 회계법인 작성·보증·추천을 의미하지 않음.','section_slots':slots,'exhibits':exhibits}
    save(out/'writer-scaffold.json',scaffold)
    # Only task-relevant exact excerpts of the pinned role/writing policies; full definitions remain version-bound.
    role=(ROOT/'libraries/personas/report-writer/ROLE.md').read_text().split('## Behavior and method')[1].split('## Output contract')[0]
    policy=(ROOT/'libraries/skills/financial-report-writing/SKILL.md').read_text().split('## Composition and review')[0]
    packet={'mandate':scaffold['scope'],'section_slots':slots,'facts':{'growth':pct(r['growth']),'target_price':r['target_price'],'wacc':pct(r['wacc']),'terminal_growth':pct(r['terminal_growth']),'pv':{k:v[k] for k in ['stub_pv','explicit_pv','terminal_pv','terminal_share','operating_ev']},'bridge':b,'shares':shares,'stress':{'haircuts':[[x['haircut'],x['growth'],x['bridge_reduction']] for x in s['rows']], **{k:s[k] for k in s if k.startswith('zero_growth')}},'zero_growth_residual_trillion':residual,'forecast_endpoints':[{k:x[k] for k in ['year','revenue','margin','fcff']} for x in [f[0],f[-1]]],'comparison':[{'id':x['id'],'facts':x['facts']} for x in e['observations']]},'qualifications':r['limitations']+e['gaps'], 'sources':sources,'source_classification':'HMC2025 preliminary unaudited connected results, HMC CID management targets, MIRAE single dated broker forecast. Collected later, historical byte identity unproven; quantities/periods/perimeters not directly equivalent.','role_policy_excerpt':role,'writing_policy_excerpt':policy,'exhibits_path':'writer-scaffold.json (fresh generated tables/chart; do not edit)','assemble_command':shlex.join([sys.executable,str(Path(__file__).resolve()),'assemble',str(out)])}
    # Separate excerpts can exceed the requested summary envelope; trim at semantic paragraph boundaries, preserving core writer rules.
    packet['writing_policy_excerpt']='\n\n'.join(policy[policy.index('## Build and test the argument'):].split('\n\n')[1:3])
    packet['role_policy_excerpt']='\n'.join(role.strip().splitlines()[:4])
    encoded=json.dumps(packet,ensure_ascii=False,separators=(',',':'))
    if len(encoded)>6000: raise ValueError('Author packet exceeds 6000-character envelope: '+str(len(encoded)))
    (out/'author-packet.json').write_text(encoded)
def assemble(out):
    a=read(out/'attempt.json'); c=read(out/'writer-content.json'); d=read(out/'writer-scaffold.json')
    for name,field in [('author-packet.json','writer_packet_sha256'),('writer-scaffold.json','writer_scaffold_sha256')]:
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=a[field]: raise ValueError('Writer inputs changed')
    slots=d.pop('section_slots'); exhibits=d.pop('exhibits')
    if [s['id'] for s in c['sections']]!=slots: raise ValueError('Missing section slots')
    for k in ['title','subtitle','conclusion','findings','needs']: d[k]=c[k]
    if len(d['findings'])!=3 or len(d['needs'])!=3: raise ValueError('Need 3 genuine findings and evidence requests')
    d['report_sections']=[]
    for s in c['sections']:
        if not s['paragraphs'] or not all(isinstance(p,str) and p.strip() and '<' not in p for p in s['paragraphs']): raise ValueError('Fresh plain-text prose required')
        blocks=[{'kind':'paragraph','html':p} for p in s['paragraphs']]+exhibits[s['id']]
        if s['id']=='actions':
            blocks.append(table(['근거','원문·계산 위치'],[[x['display_name'],{'text':x['locator'],'html':'<a href="'+x['url']+'">'+x['locator']+'</a>'}] for x in d['sources']],'발표일·범위 확인된 원문과 이번 실행의 모델. 미해결 항목은 별도 증거 요청으로 유지.'))
        d['report_sections'].append({k:s[k] for k in ['id','title','lead']}|{'blocks':blocks})
    if not c.get('claim_map'): raise ValueError('Claim mapping required')
    save(out/'input.json',d)
    save(out/'argument-record.json',{'attempt_id':a['attempt_id'],'scope':d['scope'],'judgment':c['judgment'],'claim_map':c['claim_map'],'unresolved':read(out/'analysis/result.json')['limitations']+read(out/'analysis/comparison-evidence.json')['gaps'],'self_check_only':True,'writer_packet_sha256':a['writer_packet_sha256']})
    print(json.dumps({'saved':['input.json','argument-record.json'],'sections':len(d['report_sections'])}))
if __name__=='__main__':
    {'prepare':prepare,'assemble':assemble}[sys.argv[1]](Path(sys.argv[2]).resolve())
