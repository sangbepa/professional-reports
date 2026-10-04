"""Full analysis through report-outfit's own art, page, table and chart builders."""
import html,json
import build as native

def emit(block,index):
 kind=block['kind']
 if kind=='chart':
  d={'key':'valuation'if block['chart'].get('type')=='range'else'financial_detail','chart':block['chart']}
  caption='<div class="retained-text">'+block['caption_html']+'</div>'if block.get('caption_html')else''
  return '<div class="native-chart" data-report-chart="'+str(index)+'">'+caption+native.chart(d,'transaction').replace('Exhibit 02','Exhibit '+str(index).zfill(2))+'</div>'
 if kind=='table':
  caption='<p class="caption">'+block['caption_html']+'</p>'if block.get('caption_html')else''
  return '<div class="native-table">'+caption+native.table({'key':'financial_detail','headers':block['headers'],'rows':block['rows'],'unit_note':'','rich':True}).replace('Exhibit 01','Exhibit '+str(index).zfill(2)).replace('Retained financial observations','분석을 지지하는 재무정보')+'</div>'
 if kind=='paragraph':return '<p>'+block['html']+'</p>'
 if kind=='finding':return '<blockquote>'+block['html']+'</blockquote>'
 if kind=='hero':return '<div class="metric-row retained-hero"><div class="metric"><div class="metric-value">'+block['html']+'</div></div></div>'
 if kind=='metrics':return '<div class="metric-row detail-metrics">'+''.join('<div class="metric"><div class="metric-value">'+x['value']+'</div><div class="metric-label">'+x['label']+'</div></div>'for x in block['items'])+'</div>'
 if kind=='source-note':return '<div class="source-entry retained-source">'+block['html']+'</div>'
 if kind=='text':return '<div class="retained-text">'+block['html']+'</div>'
 raise ValueError('Unsupported block '+kind)

def document(d,design):
 sections=native.pages(d,design,False)[:2];idx=1
 integrated=d.get('overview_mode','integrated'if d.get('retention')else'generated')=='integrated'
 # The full report uses the native cover and mandate, then the complete actual argument.
 # Sample-only summary/questions pages are replaced by the actual analysis, not appended twice.
 links=''.join('<li><a href="#'+native.E(s['id'])+'"><span>'+native.E(s['title'])+'</span><b class="content-page" data-section-link="'+native.E(s['id'])+'"></b></a></li>'for s in d['report_sections'])
 sections[1]={'kind':'mandate','title':'평가 범위와 읽는 순서'if d['key']=='valuation'else'보고 범위와 읽는 순서','lead':'결론에서 가정, 현금흐름과 원문 근거까지.'if d['key']=='valuation'else'관찰·판단·근거를 연결합니다.','body':native.label('REPORTING BASIS')+(''if integrated else native.p(d.get('audience','')))+native.p(d['scope'])+native.p(d['status'])+'<ol class="contents report-contents">'+links+'</ol>'+native.p(d['design_boundary'],'boundary')}
 if not integrated:
  overview_links=''.join('<li><a href="#'+key+'"><span>'+title+'</span><b class="content-page" data-section-link="'+key+'"></b></a></li>'for key,title in [('overview','주요 관찰과 결론'),('overview-basis','요약 정보와 검토 과제'),('overview-evidence','요약 근거와 적용 범위')])
  sections[1]['body']=sections[1]['body'].replace('<ol class="contents report-contents">','<ol class="contents report-contents">'+overview_links)
  sections.extend([
   {'id':'overview','kind':'summary','title':'주요 관찰과 결론','lead':d['status'],'body':native.metrics(d)+native.finding(d['conclusion'])+''.join('<h3>'+str(i+1).zfill(2)+'</h3>'+native.p(t)for i,t in enumerate(d['findings']))},
   {'id':'overview-basis','kind':'table','title':'요약 정보와 검토 과제','lead':d['scope'],'body':native.table(d)+native.p(d.get('formula',''))+'<h3>검토 과제</h3>'+''.join(native.p(t)for t in d['needs'])},
   {'id':'overview-evidence','kind':'sources','title':'요약 근거와 적용 범위','lead':d['status'],'body':native.source_entries(d)+native.p(d['design_boundary'],'boundary')}])
  if not any(b['kind']=='chart'and b['chart']==d['chart']for s in d['report_sections']for b in s['blocks']):
   sections.append({'id':'overview-chart','kind':'chart','title':d['chart']['title'],'lead':d['chart']['unit'],'body':native.chart(d,design)})
 for s in d['report_sections']:
  content=[]
  for b in s['blocks']:
   rendered=emit(b,idx);idx+=b['kind']in{'chart','table'}
   if b['kind']=='source-note'and content:content[-1]='<div class="keep-with-source">'+content[-1]+rendered+'</div>'
   else:content.append(rendered)
  kind='sources'if s['id'].startswith('sources')else'analysis'if s['id']in{'conditions','quality','normalization'}else'table'
  sections.append({'id':s['id'],'kind':kind,'title':s['title'],'lead':s['lead'],'body':''.join(content),'retained_section':True})
 # Actual native page constructors, not a transplanted prior HTML/CSS layout.
 dd=native.DESIGNS[design];E=native.E
 comparison=d.get('comparison_href','../index.html'if integrated else None)
 compare_link='<a href="'+E(comparison)+'">세 가지 시안</a>'if comparison else''
 footer=d.get('report_footer','시안 제작기 적용본 · 공개자료 기반 조건부 평가'if d['key']=='valuation'else'시안 제작기 적용본 · '+d['status'])
 doc='<!doctype html><html lang="'+E(d.get('language','ko'))+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+E(dd['name']+' | '+d['title'])+'</title><link rel="stylesheet" href="assets/base.css"><link rel="stylesheet" href="assets/'+design+'.css"><link rel="stylesheet" href="assets/full-report.css"></head><body class="'+design+' report-'+E(d['key'])+' full-report"><nav class="reader">'+compare_link+'<span>'+E(dd['name'])+'</span><button onclick="document.body.classList.toggle(\'continuous\')">Page / reading view</button><a href="report.pdf">PDF</a></nav><main>'
 for i,s in enumerate(sections,1):
  key=s.get('id','p'+str(i));head=''if s['kind']=='cover'else'<div class="page-heading">'+native.label(str(i).zfill(2)+' / '+s['kind'].upper())+'<h1>'+E(s['title'])+'</h1>'+native.p(s['lead'],'lead')+'</div>'
  doc+=f'<section class="page {s["kind"]}" id="{key}" data-page="{i}" data-native-page="{i}"'+(' data-retained="true"'if s.get('retained_section')else'')+'><header>'+native.logo()+'<div>'+E(d['title'])+'<span>DESIGN APPLICATION / '+dd['code']+'</span></div></header>'+head+'<div class="page-body">'+s['body']+'</div><footer><span>'+E(footer)+'</span><b>'+f'{i:02} / {len(sections):02}'+'</b></footer></section>'
 return doc+'</main><script src="assets/full-report.js"></script></body></html>',sections
