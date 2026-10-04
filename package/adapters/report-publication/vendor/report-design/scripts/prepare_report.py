"""Map reviewed analysis/model into the EXISTING report-outfit generator's inputs."""
import argparse, hashlib, json, re
from pathlib import Path
from collections import Counter
from html_dom import DOM,Node

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normalized(n):return ' '.join(n.text().split())
def retained(tree):
 bodies=[s.find(cls='pagebody')for s in tree.walk()if s.tag=='section'and'page'in s.attrs.get('class','').split()]
 bodies=[b for b in bodies if b]
 return {'metrics':[[n.attrs['data-metric'],n.attrs.get('data-value'),normalized(n)]for b in bodies for n in b.walk()if'data-metric'in n.attrs],
 'paragraphs':dict(Counter(normalized(n)for b in bodies for n in b.walk()if n.tag=='p')),
 'table_cells':dict(Counter(normalized(n)for b in bodies for n in b.walk()if n.tag=='td'))}

def content_blocks(body,base):
 out=[]
 for n in body.children:
  if not isinstance(n,Node):continue
  if n.tag=='svg':
   # Rebuild at the original semantic location; keep its caption with the plot.
   caption=out.pop()['html'] if out and out[-1]['kind']=='text' else ''
   out.append({'kind':'chart-slot','caption_html':caption})
   continue
  for x in n.walk():
   if x.tag=='a'and x.attrs.get('href'):
    h=x.attrs['href']
    if h.startswith('#'):x.attrs['href']=base.as_uri()+h
    elif not re.match(r'^[a-zA-Z]+:',h):
     file,sep,fragment=h.partition('#');x.attrs['href']=(base.parent/file).resolve().as_uri()+('#'+fragment if sep else'')
  cls=n.attrs.get('class','')
  if n.tag=='table':
   rows=[r for r in n.walk()if r.tag=='tr'];heads=[x.inner()for x in rows[0].children if isinstance(x,Node)and x.tag in{'td','th'}]
   cells=[[{'text':x.text(),'html':x.inner()}for x in row.children if isinstance(x,Node)and x.tag=='td']for row in rows[1:]]
   out.append({'kind':'table','headers':heads,'rows':cells})
  elif n.tag=='p':out.append({'kind':'paragraph','html':n.inner()})
  elif n.tag=='aside':out.append({'kind':'source-note','html':n.inner()})
  elif cls=='finding':out.append({'kind':'finding','html':n.inner()})
  elif cls=='hero':out.append({'kind':'hero','html':n.inner()})
  elif cls=='bars':out.append({'kind':'metrics','items':[{'value':c.find('b').inner(),'label':c.find('label').inner()}for c in n.children if isinstance(c,Node)]})
  else:out.append({'kind':'text','html':n.inner()})
 return out

def prepare(source,results,out):
 source=Path(source).resolve();results=Path(results).resolve();tree=DOM(source.read_text()).root;r=json.loads(results.read_text());b=r['cases']['base']
 sections=[]
 for s in tree.walk():
  if s.tag!='section'or'page'not in s.attrs.get('class','').split():continue
  body=s.find(cls='pagebody')
  if not body:continue
  sections.append({'id':s.attrs['id'],'title':s.find('h1').text(),'lead':s.find(cls='lead').text(),'blocks':content_blocks(body,source)})
 def chart(title,unit,categories,values,note,paths,kind='bar',series_name='기준 시나리오'):
  return {'title':title,'unit':unit,'categories':categories,'series':[{'name':series_name,'values':values,'result_paths':paths}], 'note':note,'type':kind}
 sc=['bear','base','bull'];case_names=['하방','기준','상방'];vals=[r['cases'][k]['common_value']/10000 for k in sc]
 charts={
 'decision':chart('조건부 보통주 가치','만원 / 주',case_names,vals,'시나리오에 확률을 부여하지 않았습니다. 정보 기준일 2026-09-22.',[f'cases.{k}.common_value/10000'for k in sc],kind='range',series_name='조건부 DCF'),
 'cashflow':chart('기준 FCFF 경로','조원 · 26H2는 반기',[str(x['period'])for x in b['rows']],[x['fcff']for x in b['rows']],'예측 가정입니다. 반기와 연간 기간을 구분합니다.',[f'cases.base.rows.{i}.fcff'for i in range(len(b['rows']))],kind='bar',series_name='기준 FCFF'),
 'dcf':chart('사업별 기업가치 기여','조원 · 연결 배부 진단',list(b['segment_ev']),list(b['segment_ev'].values()),'독립 사업별 기업가치가 아닌 연결 배부 진단입니다. 연결 합계와 차이를 본문 표에서 확인합니다.',[f'cases.base.segment_ev.{k}'for k in b['segment_ev']],series_name='기준 EV 기여'),
 'terminal':chart('현금흐름과 재투자','조원 · 26H2는 반기',[str(x['period'])for x in b['rows']],[x['fcff']for x in b['rows']],'총투자는 리스를 포함한 모델 capex입니다. 장기 성장에는 재투자가 필요합니다. 반기와 연간 기간을 구분합니다.',[f'cases.base.rows.{i}.fcff'for i in range(len(b['rows']))],series_name='기준 FCFF')}
 charts['forecast']={'title':'DS 영업이익률 시나리오 경로','unit':'% · 조건부 운영 가정','categories':[str(x['period'])for x in b['rows']],
 'series':[{'name':case_names[j],'values':[x['segments']['DS']['ebit']/x['segments']['DS']['revenue']*100 for x in r['cases'][k]['rows']], 'result_paths':[f'cases.{k}.rows.{i}.segments.DS.ebit / cases.{k}.rows.{i}.segments.DS.revenue * 100'for i in range(len(b['rows']))]}for j,k in enumerate(sc)],
 'note':'공시된 확정 실적이 아닌 시나리오 가정입니다. DS 마진 정상화 경로의 차이를 표시합니다.','type':'bar'}
 charts['terminal']['series'].append({'name':'총투자','values':[x['capex']for x in b['rows']],'result_paths':[f'cases.base.rows.{i}.capex'for i in range(len(b['rows']))]})
 for s in sections:
  if s['id'] not in charts:continue
  slots=[i for i,x in enumerate(s['blocks']) if x['kind']=='chart-slot']
  if slots:
   if len(slots)!=1:raise ValueError('Expected one original plot for '+s['id'])
   i=slots[0];s['blocks'][i]={'kind':'chart','chart':charts[s['id']],'caption_html':s['blocks'][i]['caption_html']}
  else:s['blocks'].insert(0,{'kind':'chart','chart':charts[s['id']]})
  if s['id']=='terminal':
   # The won/share paragraph is a table caption, not a free-standing body block.
   if s['blocks'][0]['kind']!='paragraph' or s['blocks'][1]['kind']!='table':raise ValueError('Sensitivity caption/table source contract changed')
   caption=s['blocks'].pop(0)['html'];s['blocks'][0]['caption_html']=caption
   # Put the Excel sensitivity explanation/source immediately after that grid,
   # and the terminal-economics explanation immediately after its FCFF plot.
   table,plot,economics,excel,source_note=s['blocks']
   if [x['kind']for x in [table,plot,economics,excel,source_note]]!=['table','chart','paragraph','paragraph','source-note']:raise ValueError('Terminal exhibit/interpretation source contract changed')
   s['blocks']=[table,excel,source_note,plot,economics]
 if any(x['kind']=='chart-slot'for s in sections for x in s['blocks']):raise ValueError('Original plot has no reviewed native model mapping')
 d={'schema_version':2,'key':'valuation','title':'삼성전자 기업·지분가치 평가','subtitle':'가치는 가정의 결과입니다.\n지속 가능한 이익에서 출발합니다.','audience':'투자위원회와 이사회','status':'조건부 분석 | 정보 기준일 2026-09-22','scope':'삼성전자 | 공개자료 | 계속기업의 독립적인 기업·지분가치 평가','id':'02',
 'conclusion':f'기준 보통주 가치는 {b["common_value"]:,.0f}원입니다. 시장가격 {b["market_common"]:,.0f}원 대비 {b["common_gap"]:.1%}의 차이를 보이며, 반도체 수익성의 지속성과 재투자 경로에 좌우됩니다.',
 'headers':['시나리오','영업 EV / 조원','전체 지분 / 조원','보통주 / 원'],
 'rows':[[case_names[i],f'{r["cases"][k]["operating_ev"]:,.2f}',f'{r["cases"][k]["equity_value"]:,.2f}',f'{r["cases"][k]["common_value"]:,.0f}']for i,k in enumerate(sc)],
 'hero':[f'{b["common_value"]:,.0f}','원 / 보통주','기준 시나리오'],
 'kpis':[[f'{b["wacc"]:.2%}','FCFF WACC','모델 가정'],[f'{b["terminal_share"]:.1%}','기업가치 중 잔존가치 비중','기준 시나리오']],
 'findings':[f'연결 영업 기업가치는 {b["operating_ev"]:,.1f}조원, 전체 보통·우선 지분가치는 {b["equity_value"]:,.1f}조원입니다. 기업가치에서 주주 청구권까지의 조정을 일관되게 반영합니다.','현재의 초과 수익을 장기 평균으로 고정하면 가치가 과대해질 수 있습니다. 반도체 마진 정상화, 장기 재투자, 사업별 공시 제약을 시나리오와 민감도로 검토했습니다.','공시·시장 자료와 분석 가정을 구분합니다. 독립 AI의 원문·모델·판단 검토 기록을 연결하며, 조건부 가치 범위를 주가 예측이나 확률 구간으로 해석하지 않습니다.'],
 'needs':['지속 가능한 DS 수익성과 장기 재투자 수준','기준일의 현금·차입·비영업자산·주식수 대조','사업별 공시 제약과 결론을 바꾸는 조건'],
 'formula':'기업가치 = 예측 FCFF 현재가치 + 잔존가치 현재가치. 전체 지분가치는 순현금, 비영업자산 및 다른 청구권 조정 후 주식 종류별 권리를 반영합니다.',
 'chart':charts['decision'],'sources':[{'id':'V-REPORT','display_name':'삼성전자 검토된 가치평가 본문','locator':'2026-09-22 기준; 원문·모델·판단·문서 검토 기록 연결','url':source.as_uri()},{'id':'V-MODEL','display_name':'삼성전자 검토된 공통 모델 결과','locator':'cases / sensitivities / reconciliation; 본문과 같은 결과','url':results.as_uri()}],
 'design_boundary':'시안 제작기를 사용한 디자인 적용본입니다. 재무 분석의 내용과 검토 범위를 기존 검증본에서 유지했습니다. Deloitte가 발행하거나 서명한 가치평가 의견이 아닙니다.',
 'report_sections':sections,'retention':retained(tree),'provenance':{'source_report':str(source),'source_report_sha256':sha(source),'model_results':str(results),'model_results_sha256':sha(results),'previous_design_retained':False}}
 Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');return d
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--results',required=True);a.add_argument('--out',required=True);z=a.parse_args();d=prepare(z.source,z.results,z.out);print(json.dumps({'sections':len(d['report_sections']),'metrics':len(d['retention']['metrics']),'output':z.out}))
