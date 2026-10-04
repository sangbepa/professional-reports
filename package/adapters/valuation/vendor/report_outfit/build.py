"""Deterministic, art-directed report specimens, independent of valuation logic."""
import argparse, copy, hashlib, html, json, math, re, shutil, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
ASSETS=HERE/'assets'if(HERE/'assets').exists()else HERE.parent/'assets'
DEFAULT=ROOT/'output/native-report-output'
DESIGNS={
 'transaction':dict(code='A',name='Transaction Precision',tag='Evidence. Judgement. Detail.',description='A rigorous deal-advisory language with indexed issues, ruled tables and evidence-led reading.',layout='Ruled tables; asymmetric value hierarchy; black hairlines; restrained green.'),
 'executive':dict(code='B',name='Executive Clarity',tag='The insight. The implication. The decision.',description='A boardroom language that gives the conclusion room, then connects it to the evidence.',layout='Generous single-column reading; oversized key values; green chapter field; open comparisons.'),
 'editorial':dict(code='C',name='Insight Editorial',tag='A clearer view of what comes next.',description='An editorial language with a strong visual opening, chapter rhythm and explanatory exhibits.',layout='Vector-led cover; two-column prose; circle chapter markers; side notes and explanatory diagrams.')}
TEMPLATES=['fdd','valuation','earnings','credit','cashflow','working_capital','variance','comps','price_adjustment','investment_memo']
E=lambda x:html.escape(str(x),quote=True)
def jread(p):return json.loads(Path(p).read_text())
def jwrite(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def validate(d,blank=False):
 if d.get('key') not in TEMPLATES:raise ValueError('Unknown report key')
 if not blank:
  for k in ['title','scope','status','conclusion','headers','rows','findings','needs','hero','chart','sources']:
   if not d.get(k):raise ValueError('Missing specimen field: '+k)
  if len(d['findings'])!=3 or len(d['needs'])!=3:raise ValueError('Three analysis notes and evidence requests are required for the art-directed pages')
  if any(len(r)!=len(d['headers']) for r in d['rows']):raise ValueError('Table row / header mismatch')
  c=d['chart']
  for s in c['series']:
   if len(s['values'])!=len(c['categories']) or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in s['values']):raise ValueError('Invalid chart series')
 if d.get('report_sections'):
  from html_dom import DOM
  ids=[]
  for section in d['report_sections']:
   if not all(k in section for k in ['id','title','lead','blocks']):raise ValueError('Incomplete report section')
   if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',section['id']):raise ValueError('Invalid report section ID')
   ids.append(section['id'])
   for block in ([section['summary']] if section.get('summary') else [])+section['blocks']:
    if block.get('kind')=='table'and any(len(row)!=len(block['headers'])for row in block['rows']):raise ValueError('Report table row / header mismatch')
    fragments=[block.get('html',''),block.get('caption_html','')]+block.get('headers',[])+[v.get('html','')for row in block.get('rows',[])for v in row if isinstance(v,dict)]
    for fragment in fragments:
     for node in DOM(fragment).root.walk():
      if node.tag in {'script','iframe','object','embed','form'}or any(k.startswith('on')for k in node.attrs)or node.attrs.get('href','').lower().startswith('javascript:'):raise ValueError('Active HTML is not allowed in report content')
    if block.get('kind')=='chart':
     chart=block['chart']
     for series in chart['series']:
      if len(series['values'])!=len(chart['categories'])or any(not isinstance(v,(int,float))or not math.isfinite(v)for v in series['values']):raise ValueError('Invalid report chart series')
  if len(ids)!=len(set(ids)):raise ValueError('Duplicate report section ID')

def logo():return '<strong class="model-mark">VALUATION SCENARIO</strong>'
def label(text):return '<div class="eyebrow">'+E(text)+'</div>'
def p(text,cls=''):return f'<p class="{cls}">'+E(text)+'</p>'
def finding(text):return '<blockquote>'+E(text)+'</blockquote>'
def art(seed,design):
 """Original vector artwork: no reference-report photograph is reproduced."""
 if design=='transaction':
  lines=''.join(f'<path d="M {20+i*27} 460 L {20+i*27} {420-i*12} L {80+i*24} {420-i*12}" fill="none" stroke="'+('#86bc25' if i%4==0 else '#b2b8af')+'" stroke-width="1"/>'for i in range(20))
  return f'<svg viewBox="0 0 620 480" aria-hidden="true"><circle cx="510" cy="110" r="80" fill="#86bc25"/>{lines}<path d="M20 450H600" stroke="#fff"/></svg>'
 if design=='executive':
  rings=''.join(f'<circle cx="440" cy="270" r="{r}" stroke="#000" stroke-width="{1 if r%3 else 2}" fill="none" opacity="{.15+r/900}"/>'for r in range(40,290,20))
  return f'<svg viewBox="0 0 620 480" aria-hidden="true">{rings}<circle cx="440" cy="270" r="20" fill="#000"/><path d="M55 355H430V270" fill="none" stroke="#fff" stroke-width="2"/><circle cx="55" cy="355" r="6" fill="#fff"/></svg>'
 paths=''
 for i in range(18):
  x=34+i*21;y=305-i*11+seed*2
  paths+=f'<path d="M{x} 470 L{x} {y} Q{x} {y-170} {x+155} {y-178} L{x+170} {y-178}" fill="none" stroke="'+(['#86bc25','#1b5257','#b5d334'][i%3])+f'" stroke-width="{3 if i%5==0 else 1.2}"/>'
 return f'<svg viewBox="0 0 620 480" aria-hidden="true"><rect width="620" height="480" fill="#092529"/>{paths}<circle cx="458" cy="91" r="28" fill="#86bc25"/><path d="M40 420H570" stroke="#fff" stroke-opacity=".2"/></svg>'

def table(d,blank=False):
 heads=d['headers'];rows=d.get('rows',[])
 if blank:
  heads=[re.sub(r'(?:H[12] |Q[1-4] )?(?:FY)?20\d{2}(?: H[12]| Q[1-4])?', '[period]',h).replace('KRW','[currency]').replace(' tn',' [scale]')for h in heads]
  rows=[['Enter '+h.split(' / ')[0].lower() for h in heads] for _ in range(4)]
 units={'credit':'Amounts in KRW trillions; ratios are shown as x or %.','investment_memo':'Amounts in KRW trillions unless an explicit per-share unit is stated.','valuation':'Enterprise and equity values in KRW trillions; ordinary-share values in KRW per share.'}
 unit_note='Replace periods, currency, units and column labels for the current assignment.'if blank else d.get('unit_note',units.get(d['key'],''))
 out=(p(unit_note,'caption')if unit_note else'')+'<div class="exhibit-title">Exhibit 01 <span>'+('Authoring grid' if blank else E(d.get('title','Retained financial observations')))+'</span></div><table><thead><tr>'+''.join('<th>'+(h if d.get('rich')else E(h))+'</th>'for h in heads)+'</tr></thead><tbody>'
 for i,row in enumerate(rows):
  def value(v):return v['html']if d.get('rich')and isinstance(v,dict)else E(v)
  def content(v):return v.get('text','')if isinstance(v,dict)else str(v)
  role=d.get('row_roles',[])[i] if i<len(d.get('row_roles',[])) else ''
  out+='<tr'+((' class="row-'+E(role)+'"') if role else '')+(' class="total"' if i==len(rows)-1 and d['key'] in ['working_capital','variance','price_adjustment'] else '')+'>'+''.join('<td class="'+('base-cell ' if d.get('base_cell')==[i,j] else '')+('num' if j>0 and re.fullmatch(r'[+\-\d,\. %x]+(?: tn)?',content(v)) else '')+'" data-cell="'+f'{i}:{j}'+'">'+value(v)+('<strong class="base-marker">BASE</strong>' if d.get('base_cell')==[i,j] else '')+'</td>' for j,v in enumerate(row))+'</tr>'
 return out+'</tbody></table>'

def chart(d,design,blank=False):
 if blank:return '<div class="chart-guide"><div>EXHIBIT 02 / CHART FIELD</div><h3>Insert comparable observations.</h3><p>Provide a title, units, period, series labels and source. Keep forecasts distinct from reported results.</p><svg viewBox="0 0 640 240" aria-hidden="true"><path d="M55 20V205H605" fill="none" stroke="#919a91"/><path d="M55 155H605M55 105H605M55 55H605" stroke="#dae0d6" stroke-dasharray="4 4"/></svg></div>'
 c=d['chart']
 if c.get('type')=='role-bars':return role_chart(c,design)
 n=len(c['categories']);series=c['series'];vals=[v for s in series for v in s['values']]
 if d['key'] in ['valuation','investment_memo'] and c.get('type') != 'bars':
  maximum=max(vals)*1.15;xx=lambda v:70+v/maximum*530
  svg='<svg class="data-chart" viewBox="0 0 680 310" role="img" aria-label="'+E(c['title'])+'"><title>'+E(c['title'])+'</title>'
  svg+='<text x="70" y="24" class="axis-unit">'+E(c['unit'])+'</text>'
  tick_step=10**math.floor(math.log10(maximum/5));tick_step*=min([1,2,2.5,5,10],key=lambda z:abs(z-maximum/5/tick_step))
  for i in range(math.floor(maximum/tick_step)+1):
   v=i*tick_step
   x=xx(v);svg+=f'<path d="M{x:.1f} 90V220" class="gridline"/><text x="{x:.1f}" y="245" text-anchor="middle" class="tick">{v}</text>'
  svg+=f'<path d="M{xx(min(vals)):.1f} 155H{xx(max(vals)):.1f}" stroke="#d2e4b6" stroke-width="18"/>'
  for i,(cat,v) in enumerate(zip(c['categories'],vals)):
   x=xx(v);svg+=f'<path d="M{x:.1f} 111V202" stroke="#182d16" stroke-width="1"/><circle data-chart-value="{v}" data-series="0" data-category="{i}" cx="{x:.1f}" cy="155" r="{9 if i==1 else 6}" fill="'+('#86bc25' if i==1 else '#2e4d46')+f'"/><text x="{x:.1f}" y="69" text-anchor="middle" class="category">{E(cat)}</text><text x="{x:.1f}" y="94" text-anchor="middle" class="bar-value">{v:.2f}</text>'
  return '<div class="exhibit-title">Exhibit 02 <span>'+E(c['title'])+'</span></div>'+svg+'</svg>'+p(c['note'],'caption')
 if d['key']=='working_capital':
  maximum=max(vals)*1.15;yy=lambda v:260-v/maximum*190
  svg='<svg class="data-chart" viewBox="0 0 680 340" role="img" aria-label="'+E(c['title'])+'"><title>'+E(c['title'])+'</title><text x="65" y="22" class="axis-unit">'+E(c['unit'])+'</text>'
  for v in range(0,121,30):
   y=yy(v);svg+=f'<path d="M65 {y:.1f}H520" class="gridline"/><text x="50" y="{y+4:.1f}" text-anchor="end" class="tick">{v}</text>'
  for i,cat in enumerate(c['categories']):
   va,vb=series[0]['values'][i],series[1]['values'][i];color=['#1f4e54','#86bc25'][i]
   svg+=f'<path d="M145 {yy(va):.1f}L470 {yy(vb):.1f}" stroke="{color}" stroke-width="3" fill="none"/>'
   for j,v in enumerate([va,vb]):
    x=[145,470][j];lx=125 if j==0 else 455;ly=yy(v)+(-18 if j or i%2==0 else 23)
    svg+=f'<circle data-chart-value="{v}" data-series="{j}" data-category="{i}" cx="{x}" cy="{yy(v):.1f}" r="5" fill="{color}"/><path d="M{lx+5} {ly-4:.1f}L{x-7} {yy(v):.1f}" fill="none" stroke="{color}" stroke-width=".7"/><text x="{lx}" y="{ly:.1f}" text-anchor="end" fill="{color}" class="bar-value">{v:.2f}</text>'
   svg+=f'<text x="490" y="{yy(vb)+5:.1f}" class="category">{E(cat)}</text>'
  svg+='<text x="145" y="297" text-anchor="middle" class="category">FY2025 end</text><text x="470" y="297" text-anchor="middle" class="category">H1 2026 end</text></svg>'
  return '<div class="exhibit-title">Exhibit 02 <span>'+E(c['title'])+'</span></div>'+svg+p(c['note'],'caption')
 lo=min(0,min(vals));hi=max(0,max(vals));span=hi-lo or 1
 scale=10**math.floor(math.log10(span/5));step=scale*min([1,2,2.5,5,10],key=lambda z:abs(z-span/5/scale))
 lo=math.floor(lo/step)*step;hi=math.ceil(hi/step)*step
 if lo==hi:hi=lo+step
 colors=['#86bc25','#1f4e54','#aeb6aa'];height=max(280,80+n*max(41,17*len(series)+10));L=180;R=560
 x=lambda v:L+(v-lo)/(hi-lo)*(R-L)
 svg=f'<svg class="data-chart" viewBox="0 0 680 {height}" role="img" aria-label="{E(c["title"])}"><title>{E(c["title"])}</title><text x="180" y="19" class="axis-unit">{E(c["unit"])}</text><text x="665" y="19" text-anchor="end" class="axis-unit">VALUE</text>'
 for i in range(round((hi-lo)/step)+1):
  v=lo+step*i;xx=x(v);tick=f'{v:,.3f}'.rstrip('0').rstrip('.')
  svg+=f'<path d="M{xx:.2f} 32V{height-35}" class="gridline"/><text x="{xx:.2f}" y="{height-14}" text-anchor="middle" class="tick">{tick}</text>'
 for i,cat in enumerate(c['categories']):
  yy=50+i*(height-95)/n
  svg+=f'<text x="152" y="{yy+8:.2f}" text-anchor="end" class="category">{E(cat)}</text>'
  for j,s in enumerate(series):
   v=s['values'][i];bh=14 if len(series)>1 else 20;y=yy+j*17
   xx=min(x(0),x(v));w=abs(x(v)-x(0))
   svg+=f'<rect data-chart-value="{v}" data-series="{j}" data-category="{i}" x="{xx:.2f}" y="{y:.2f}" width="{max(w,.5):.2f}" height="{bh}" fill="{colors[j]}"/>'
   svg+=f'<text x="665" y="{y+bh-3:.2f}" text-anchor="end" class="bar-value">{v:,.2f}</text>'
 svg+=f'<path d="M{x(0):.2f} 30V{height-35}" stroke="#344438"/></svg>'
 legend='<div class="legend">'+''.join(f'<span><i style="background:{colors[j]}"></i>{E(s["name"])}</span>' for j,s in enumerate(series))+'</div>'
 return '<div class="exhibit-title">Exhibit 02 <span>'+E(c['title'])+'</span></div>'+svg+legend+p(c['note'],'caption')

def role_chart(c, design):
 """Separated EV, equity-input, deduction and outcome lanes; never additive bars."""
 colors={'transaction':['#293d36','#637b6a','#925333','#172c23'],
         'executive':['#536b29','#809d4b','#925333','#273c12'],
         'editorial':['#285660','#6b8c8b','#925333','#103b40']}[design]
 values=c['series'][0]['values'];lo=min(0,min(values));hi=max(0,max(values));span=hi-lo or 1
 x=lambda v:245+(v-lo)/span*275
 svg='<svg class="data-chart role-chart" viewBox="0 0 680 400" role="img" aria-label="'+E(c['title'])+'"><title>'+E(c['title'])+'</title>'
 svg+='<text x="245" y="24" class="axis-unit">'+E(c['unit'])+'</text>'
 for i,(label,role,value) in enumerate(zip(c['categories'],c['roles'],values)):
  y=55+i*80
  svg+=f'<path d="M0 {y-14}H680" class="gridline"/><text x="0" y="{y+5}" class="category">{E(label)}</text><text x="0" y="{y+24}" class="role-label">{E(role)}</text>'
  svg+=f'<rect data-chart-value="{value}" data-series="0" data-category="{i}" x="{min(x(0),x(value)):.2f}" y="{y-2}" width="{max(abs(x(value)-x(0)),.5):.2f}" height="23" fill="{colors[i]}"'+(' stroke="#572c13" stroke-dasharray="4 3"' if i==2 else '')+'/>'
  svg+=f'<text x="675" y="{y+15}" text-anchor="end" class="bar-value">{value:,.2f}</text>'
 for fraction in (0,.5,1):
  value=lo+span*fraction;xx=x(value)
  svg+=f'<text x="{xx:.2f}" y="380" text-anchor="middle" class="tick">{value:,.0f}</text>'
 svg+='</svg>'
 return '<div class="exhibit-title">Exhibit 02 <span>'+E(c['title'])+'</span></div>'+svg+p(c['note'],'caption')

def metrics(d,blank=False):
 items=[d['hero']]+d['kpis']
 if blank:items=[['Value','Unit / period','Key observation / status'],['Value','Unit / period','Supporting observation / status'],['Value','Unit / period','Supporting observation / status']]
 return '<div class="metric-row">'+''.join('<div class="metric"><div class="metric-value" data-kpi="'+str(i)+'">'+E(z[0])+'</div><div class="metric-unit">'+E(z[1])+'</div><div class="metric-label">'+E(z[2])+'</div></div>'for i,z in enumerate(items))+'</div>'

def source_entries(d,blank=False):
 if blank:return '<div class="source-entry"><b>01 / Source identifier</b><p>Document title, issuer, date and locator.</p><p>URL or local file reference; explain whether the item is a reported fact, model assumption or illustrative input.</p></div>'
 if d['sources'] and all(s['id'].startswith('P-')for s in d['sources']):
  groups={}
  for s in d['sources']:groups.setdefault(s['id'][2:].split('-')[0],[]).append(s)
  out='<p class="caption">Retained consolidated Open DART responses: revenue and operating profit. Each company has separate annual and quarterly disclosure references.</p><div class="sources-grid">'
  for company,items in groups.items():
   out+='<div class="source-entry"><b>'+E(company.replace('_',' ').upper())+'</b><p>Consolidated financial disclosure</p>'
   for s in items:out+='<a data-source-id="'+E(s['id'])+'" href="'+E(s['url'])+'">'+E(s['id'])+'</a><br>'
   out+='</div>'
  return out+'</div>'
 out=''
 for i,s in enumerate(d['sources'],1):
  sid=s['id'];peer=sid.startswith('P-')
  if s.get('display_name') and s.get('locator'):name=s['display_name'];loc=s['locator']
  elif sid=='S1':name='Samsung Electronics | FY2025 consolidated financial statements';loc='PDF pp. 6-9, 15-16; key audit matters pp. 3-4'
  elif sid=='S2':name='Samsung Electronics | H1 2026 consolidated financial statements';loc='PDF pp. 5-8, 14; segment disclosures pp. 63-64'
  elif sid=='M1':name='Retained Samsung DCF model | valuation-stage5.json';loc='Scenarios, assumptions and material assumptions / gaps | 22 September 2026'
  elif sid=='M2':name='Retained FCFF forecast | cashflow-stage3.json';loc='Base-scenario forecast rows | 2026 H2 onward'
  elif peer:name=sid[2:].replace('-',' | ').replace('_',' ');loc='Retained Open DART financial response | consolidated revenue and operating profit'
  else:name='Financial due diligence | methodology reference';loc='Quality of earnings and net working capital'
  url=s.get('url','');link='<a href="'+E(url)+'">Open original source</a>' if url else '<span>Retained local model; supplied with source fixture identifiers.</span>'
  out+=f'<div class="source-entry"><b>{E(sid)} / {E(name)}</b><p>{E(loc)}</p>{link}</div>'
 return out

def pages(d,design,blank=False):
 title=d['title'];sections=[];desc=DESIGNS[design]
 note='Blank authoring template' if blank else 'Conditional model output / not financially reviewed'
 findings=d['findings'] if not blank else ['State a supported observation and its evidence.','Explain the implication, keeping assumptions visible.','Define the limitation and the evidence that would change the conclusion.']
 needs=d['needs'] if not blank else ['List the first evidence request.','List the second evidence request.','List the third evidence request.']
 conclusion=d['conclusion'] if not blank else 'Write the principal conclusion. Identify the reporting basis, its limits and the decision it supports.'
 scope=d['scope'] if not blank else 'Client / reporting period / currency / scope'
 status=d['status'] if not blank else 'Document status / information cut-off'
 subtitle=d['subtitle'] if not blank else 'A clear statement.\nA purposeful report.'
 def add(kind,name,lead,body):sections.append(dict(kind=kind,title=name,lead=lead,body=body))
 if d['key']=='investment_memo':
  add('memo-opening','Investment review memo','Separate evidence from conviction.',label('INVESTMENT COMMITTEE / DECISION NOTE')+'<div class="memo-name">'+E(scope)+'</div>'+p(status,'caption')+metrics(d,blank)+finding(conclusion)+p(findings[0]))
  add('analysis','The thesis and the challenge','What supports the case; what remains conditional.','<div class="analysis-notes">'+''.join('<article><span class="note-num">0'+str(i+1)+'</span><div><h3>'+z+'</h3>'+p(findings[i])+'</div></article>'for i,z in enumerate(['Scenario definition','Assumption challenge','Decision boundary']))+'</div>'+table(d,blank))
  add('chart','Value and decision conditions','A range of scenarios is not an expected return.',chart(d,design,blank)+'<div class="requests compact">'+''.join('<article><b>0'+str(i+1)+'</b><div><h3>'+E(n)+'</h3>'+(p('Assign an owner, due date and completion evidence.')if blank else'')+'</div></article>'for i,n in enumerate(needs))+'</div>')
  add('sources','Sources and scope','The basis of the specimen.',source_entries(d,blank)+p(d.get('design_boundary','Blank authoring template. Replace the authoring guidance with supported content.'),'boundary'))
  return sections
 cover='<div class="cover-meta">'+label('VALUATION SCENARIO / REVIEW UNPERFORMED')+p(note)+'</div><div class="cover-art">'+art(int(d.get('id','1')),design)+'</div><div class="cover-titles"><h1>'+E(title)+'</h1><div class="cover-subtitle">'+E(subtitle).replace('\n','<br> ')+'</div></div><div class="cover-details"><div>'+E(scope)+'</div><div>'+E(status)+'</div></div>'
 add('cover',title,'',cover)
 specific={
 'fdd':['Diligence at a glance','Earnings quality and cash exposure','The working-capital question','What needs normalisation','Diligence evidence requests','Sources and review perimeter'],
 'valuation':['The valuation perspective','Scenario valuation outputs','The range of conditional values','Assumptions that matter','Before fixing the conclusion','Model basis and definitions'],
 'earnings':['The earnings story','Reported performance','Where the EBIT uplift sits','Attribution and comparability','Questions for management','Disclosure basis'],
 'credit':['Liquidity at a glance','Balance-sheet resources','Resources against obligations','Access, maturity and timing','Credit evidence requests','Definitions and disclosure basis'],
 'cashflow':['The cash-conversion story','Reported cash measures','Operating cash and reinvestment','What the residual excludes','Complete the cash bridge','Sources and classifications'],
 'working_capital':['The working-capital movement','Selected balance-sheet accounts','Receivables and inventory','Balance changes are not cash flows','Test normality and recovery','Scope and account definitions'],
 'variance':['The performance movement','Accounting-line comparison','The signed EBIT effects','Movement versus business cause','From explanation to action','Comparison basis'],
 'comps':['The peer-group perspective','Comparable operating measures','The margin distribution','Outliers and comparability','Before making a valuation claim','The disclosure register'],
 'price_adjustment':['The value-to-price perspective','The enterprise-to-equity bridge','Selected bridge adjustments','Where duplication can arise','Settlement evidence requests','Definitions and valuation basis']}
 names=specific[d['key']]
 boundary='This is a blank native report template. Replace its authoring guidance with supported observations, assumptions and judgements before issuing a report.'if blank else'This is a conditional valuation scenario. Source evidence and financial methods have not been independently reviewed.'
 add('mandate','Purpose. Scope. Reading order.','A transparent basis for a useful conversation.','<div class="mandate-grid"><div><h3>Prepared for</h3>'+p(d['audience'])+'<h3>Reporting basis</h3>'+p(scope)+'<h3>Document status</h3>'+p(status)+'</div><div><h3>Inside this specimen</h3><ol class="contents">'+''.join('<li><a href="#p'+str(i+3)+'">'+E(n)+'<span>'+f'{i+3:02}'+'</span></a></li>'for i,n in enumerate(names))+'</ol></div></div>'+finding('A report should make the distinction between an observation, an assumption and a judgement visible.')+p(boundary,'boundary'))
 add('summary',names[0],'Start with what matters.',metrics(d,blank)+finding(conclusion)+'<div class="summary-grid"><div><h3>The observation</h3>'+p(findings[0])+'</div><div><h3>The next question</h3>'+p(needs[0])+'</div></div>')
 add('table',names[1],'A consistent basis makes a comparison useful.',table(d,blank)+'<div class="table-note"><h3>Read the exhibit</h3>'+p(d['formula'] if not blank else 'Define the calculation, unit, time period and consolidation scope. Keep rounding and missing observations explicit.')+'</div>'+p('Basis: '+scope+'. '+status+'.','caption'))
 chart_note=findings[2]if not blank and d['key']=='fdd'else('Retained FY2025 operating margins are compared on a consolidated annual basis. Quarterly measures remain separate; no relative valuation is inferred.'if not blank and d['key']=='comps'else findings[1])
 add('chart',names[2],'Make the relationship visible.',chart(d,design,blank)+'<div class="chart-interpretation"><span class="small-tag">INTERPRETATION</span>'+p(chart_note)+'</div>')
 add('analysis',names[3],'Three notes that keep the judgement grounded.','<div class="analysis-notes">'+''.join('<article><span class="note-num">0'+str(i+1)+'</span><div><h3>'+z+'</h3>'+p(findings[i])+'</div></article>'for i,z in enumerate(['Observation and definition','Comparability and attribution','What remains conditional']))+'</div>'+finding('The strength of the conclusion follows the strength of the evidence.'))
 request_details=['Assign an owner and due date. Define the records that will complete this request.','State the test, reviewer and expected completion evidence.','Record the disposition and the decision that follows from the evidence.']if blank else['Establish the reporting perimeter and reconcile the underlying records.','Test the explanation against transaction-level or operating evidence.','Resolve the remaining scope and timing differences before fixing a conclusion.']
 add('requests',names[4],'Turn an open question into a specific next step.','<div class="requests">'+''.join('<article><b>0'+str(i+1)+'</b><div><span class="small-tag">EVIDENCE REQUEST</span><h3>'+E(n)+'</h3><p>'+E(request_details[i])+'</p></div></article>'for i,n in enumerate(needs))+'</div><div class="request-note">'+p('An evidence request is a review action, not a finding that the evidence is absent or that a misstatement exists.')+'</div>')
 add('sources',names[5],'Traceable observations. Explicit boundaries.',source_entries(d,blank)+p(d.get('design_boundary','Blank authoring template. Replace guidance with supported content.'),'boundary'))
 return sections

def document(d,design,blank=False):
 sections=pages(d,design,blank);dd=DESIGNS[design];doc='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+E(dd['name']+' | '+d['title'])+'</title><link rel="stylesheet" href="assets/base.css"><link rel="stylesheet" href="assets/'+design+'.css"></head><body class="'+design+' report-'+d['key']+'"><nav class="reader"><a href="../../index.html">Design collection</a><span>'+E(dd['name'])+'</span><button onclick="document.body.classList.toggle(\'continuous\')">Page / reading view</button><a href="report.pdf">PDF</a></nav><main>'
 for i,s in enumerate(sections,1):
  head='' if s['kind']=='cover' else '<div class="page-heading">'+label('0'+str(i)+' / '+s['kind'].upper())+'<h1>'+E(s['title'])+'</h1>'+p(s['lead'],'lead')+'</div>'
  doc+=f'<section class="page {s["kind"]}" id="p{i}" data-page="{i}"><header>'+logo()+'<div>'+E(d['title'])+'<span>'+('BLANK AUTHORING TEMPLATE' if blank else 'DESIGN CONCEPT / '+dd['code'])+'</span></div></header>'+head+'<div class="page-body">'+s['body']+'</div><footer><span>Native report design application · '+('Blank authoring template' if blank else 'Retained data specimen')+'</span><b>'+f'{i:02} / {len(sections):02}'+'</b></footer></section>'
 return doc+'</main></body></html>',sections

def node_command():
 import os
 return os.environ.get('REPORT_OUTFIT_NODE',shutil.which('node') or 'node')

def build(template,design,mode='specimen',input_path=None,out=None,render=True):
 blank=mode=='blank';input_path=Path(input_path) if input_path else HERE/'inputs'/(template+('.blank'if blank else '')+'.json')
 d=jread(input_path);validate(d,blank)
 if d['key']!=template:raise ValueError('Input report key differs from requested template')
 out=Path(out) if out else DEFAULT/('blanks'if blank else'specimens')/(design+'-'+template)
 if mode=='report'and(out/'report.html').exists():raise FileExistsError('Use a new report revision directory; previous generated reports are preserved.')
 out.mkdir(parents=True,exist_ok=True);shutil.copytree(ASSETS,out/'assets',dirs_exist_ok=True)
 if mode=='report':
  if not d.get('report_sections'):raise ValueError('Full report input requires report_sections; prepare_report.py maps reviewed content and model results.')
  from full_report import document as report_document
  text,sections=report_document(d,design)
 else:text,sections=document(d,design,blank)
 (out/'report.html').write_text(text);jwrite(out/'input.json',d)
 jwrite(out/'specification.json',dict(design=design,template=template,mode=mode,pages=len(sections),input_sha256=sha(input_path),layout=[{'page':i+1,'kind':s['kind'],'title':s['title']}for i,s in enumerate(sections)]))
 if render:subprocess.run([node_command(),str(HERE/'render.mjs'),str(out)],check=True)
 return out

def main(default_template=None):
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--template',choices=TEMPLATES,default=default_template,required=not default_template);a.add_argument('--design',choices=DESIGNS,default='transaction');a.add_argument('--mode',choices=['specimen','blank','report'],default='specimen');a.add_argument('--input');a.add_argument('--out');a.add_argument('--html-only',action='store_true');z=a.parse_args()
 print(build(z.template,z.design,z.mode,z.input,z.out,not z.html_only))

if __name__=='__main__':main()
