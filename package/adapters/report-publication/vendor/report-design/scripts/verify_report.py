"""Check native-generator reports against the reviewed content and model, with PDF rasters."""
import argparse, hashlib, json, math, re, unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse,unquote
from html_dom import DOM

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(s):return ' '.join(s.split())
def resolve(model,path):
 if ' / 'in path:
  numerator,rest=path.split(' / ',1);denominator,sep,multiplier=rest.partition(' * ')
  return resolve(model,numerator)/resolve(model,denominator)*(float(multiplier)if sep else 1)
 path,sep,divisor=path.partition('/');v=model
 for p in path.split('.'):v=v[int(p)]if isinstance(v,list)else v[p]
 return v/float(divisor)if sep else v
def chart_geometry(tree):
 checks=[]
 for svg in [n for n in tree.walk()if n.tag=='svg'and'data-chart'in n.attrs.get('class','').split()]:
  ticks=[n for n in svg.walk()if n.tag=='text'and'tick'in n.attrs.get('class','').split()]
  ticks=[n for n in ticks if re.fullmatch(r'[+\-\d,.]+',norm(n.text()))]
  if len(ticks)<2:checks.append({'passed':False,'reason':'Insufficient visible axis tick labels'});continue
  a,z=ticks[0],ticks[-1];x0,x1=float(a.attrs['x']),float(z.attrs['x']);v0,v1=float(a.text().replace(',','')),float(z.text().replace(',',''));slope=(v1-v0)/(x1-x0)
  for shape in [n for n in svg.walk()if'data-chart-value'in n.attrs]:
   value=float(shape.attrs['data-chart-value']);x=float(shape.attrs['cx'])if shape.tag=='circle'else float(shape.attrs['x'])+(float(shape.attrs['width'])if value>=0 else 0)
   measured=v0+(x-x0)*slope;tolerance=abs(slope)*.56+1e-6
   checks.append({'passed':abs(measured-value)<=tolerance,'value':value,'decoded_from_visible_axis':measured,'tolerance':tolerance})
 return checks
def verify(root,input_path,render=False):
 root=Path(root);d=json.loads(Path(input_path).read_text());p=d.get('provenance');tree=DOM((root/'rendered.html').read_text()).root
 if bool(p)!=bool(d.get('retention')):raise ValueError('Reviewed model verification requires both provenance and retention; omit both for presentation-only input')
 bodies=[s.find(cls='page-body')for s in tree.walk()if s.tag=='section'and s.attrs.get('data-retained')=='true']
 metrics=[(n.attrs['data-metric'],n.attrs.get('data-value'),norm(n.text()))for b in bodies for n in b.walk()if'data-metric'in n.attrs]
 paragraphs=Counter(norm(n.text())for b in bodies for n in b.walk()if n.tag=='p');cells=Counter(norm(n.text())for b in bodies for n in b.walk()if n.tag=='td')
 if p:expected=d['retention'];model=json.loads(Path(p['model_results']).read_text())
 else:
  expected={'metrics':[],'paragraphs':Counter(),'table_cells':Counter()};model=None
  for s in d['report_sections']:
   for b in s['blocks']:
    if b['kind']=='table':
     for row in b['rows']:
      for v in row:expected['table_cells'][norm(DOM(v['html']).root.text()if isinstance(v,dict)and'html'in v else str(v['text']if isinstance(v,dict)else v))]+=1
    if b['kind']=='paragraph':expected['paragraphs'][norm(DOM(b['html']).root.text())]+=1
    if b['kind']=='table'and b.get('caption_html'):expected['paragraphs'][norm(DOM(b['caption_html']).root.text())]+=1
    fragments=[b.get('html',''),b.get('caption_html','')]+b.get('headers',[])+[v.get('html','')for row in b.get('rows',[])for v in row if isinstance(v,dict)]
    for fragment in fragments:
     for n in DOM(fragment).root.walk():
      if'data-metric'in n.attrs:expected['metrics'].append([n.attrs['data-metric'],n.attrs.get('data-value'),norm(n.text())])
 expected_charts=[]
 charts=[b['chart']for s in d['report_sections']for b in s['blocks']if b['kind']=='chart']
 if not p and d.get('overview_mode','generated')!='integrated'and d['chart']not in charts:charts.insert(0,d['chart'])
 for c in charts:
  for j,series in enumerate(c['series']):
   for i,v in enumerate(series['values']):
    if model is not None and not math.isclose(v,resolve(model,series['result_paths'][i]),rel_tol=1e-12,abs_tol=1e-9):raise ValueError('Model path differs from chart '+series['result_paths'][i])
    expected_charts.append((j,i,v))
 layout=json.loads((root/'layout-checks.json').read_text());mobile=json.loads((root/'mobile-checks.json').read_text());spec=json.loads((root/'specification.json').read_text())
 actual_charts=[(x['series'],x['category'],x['value'])for x in layout['chartValues']]
 from pypdf import PdfReader
 pdf=PdfReader(root/'report.pdf');pdftext=''.join(''.join(unicodedata.normalize('NFKC',page.extract_text()or'').split())for page in pdf.pages)
 missing_paras=Counter(expected['paragraphs'])-paragraphs;missing_cells=Counter(expected['table_cells'])-cells
 geometry=chart_geometry(tree)
 local_links=[]
 for a in [n for n in tree.walk()if n.tag=='a'and n.attrs.get('href')]:
  href=a.attrs['href'];parsed=urlparse(href)
  if href.startswith('#')or parsed.scheme in {'http','https','mailto'}:continue
  if parsed.scheme not in {'','file'}:continue
  target=Path(unquote(parsed.path))if parsed.scheme=='file'else root/unquote(parsed.path)
  local_links.append({'href':href,'target':str(target.resolve()),'exists':target.exists()})
 seal=json.loads((root/'render-seal.json').read_text())if(root/'render-seal.json').exists()else None
 checks={'local_links_current':all(x['exists']for x in local_links),'chart_geometry_from_visible_axes':bool(geometry)and all(x['passed']for x in geometry),'all_retained_metrics':not(Counter(tuple(x)for x in expected['metrics'])-Counter(metrics)), 'retained_metric_ids':set(x[0]for x in metrics)==set(x[0]for x in expected['metrics']),
 'all_retained_paragraphs':not missing_paras,'all_retained_cells':not missing_cells,('chart_values_from_model'if p else'chart_values_from_input'):Counter(actual_charts)==Counter(expected_charts),
 'render_seal_current':bool(seal)and all((root/f).is_file()and sha(root/f)==h for f,h in seal['artifacts'].items()),'input_version_current':sha(input_path)==spec['input_sha256'],'layout':layout['passed'],'mobile':not mobile['overflow'],'pdf_page_count':len(pdf.pages)==len(layout['pages']),
 'pdf_numbers_visible':all(''.join(unicodedata.normalize('NFKC',str(v)).split())in pdftext for v in expected['table_cells']),
 'pdf_has_no_literal_html':'data-metric'not in pdftext and'<span'not in pdftext}
 if p:checks.update(source_report_current=sha(p['source_report'])==p['source_report_sha256'],source_model_current=sha(p['model_results'])==p['model_results_sha256'],prior_design_excluded=p['previous_design_retained']is False)
 else:
  required=[d.get(k,'')for k in ['audience','scope','status','conclusion','formula','design_boundary']]+d['findings']+d['needs']+[s.get(k,'')for s in d['sources']for k in ['display_name','locator']]
  checks['supplied_overview_visible']=all(''.join(unicodedata.normalize('NFKC',v).split())in pdftext for v in required if v)
 result={'passed':all(checks.values()),'checks':checks,'counts':{'pages':len(pdf.pages),'unique_retained_metric_ids':len(set(x[0]for x in metrics)),'retained_cells_required':sum(expected['table_cells'].values()),'retained_paragraphs_required':sum(expected['paragraphs'].values()),'model_bound_chart_values':len(expected_charts)if p else 0,'input_bound_chart_values':len(expected_charts)},
 'input_sha256':sha(input_path),'artifacts':{str((root/file).resolve()):sha(root/file)for file in ['report.html','rendered.html','report.pdf','layout-checks.json','mobile-checks.json']},
 'scope':'Presentation/content retention; original source/model/judgment reviews inherited by exact source/model hashes. No new financial valuation or human partner signoff.'if p else'Presentation/content retention from supplied input only. No financial source/model verification, economic opinion or human professional signoff.',
 'financial_source_model_verification':'hash-bound inherited basis'if p else'not performed',
 'missing':{'paragraphs':dict(missing_paras),'cells':dict(missing_cells)},'chart_geometry':geometry,'local_links':local_links}
 if render:
  import pypdfium2
  from PIL import Image,ImageDraw
  out=root/'renders';out.mkdir(exist_ok=True);doc=pypdfium2.PdfDocument(root/'report.pdf');records=[];tiles=[]
  for i in range(len(doc)):
   pg=doc[i];bm=pg.render(scale=120/72);im=bm.to_pil().convert('RGB');file=out/f'page-{i+1:03}.png';im.save(file);records.append({'page':i+1,'path':str(file.resolve()),'sha256':sha(file)});thumb=im.copy();thumb.thumbnail((280,396));tile=Image.new('RGB',(300,424),'#e9eee4');tile.paste(thumb,((300-thumb.width)//2,8));ImageDraw.Draw(tile).text((10,407),f'PAGE {i+1}',fill='#203c20');tiles.append(tile);bm.close();pg.close()
  for offset in range(0,len(tiles),4):
   contact=Image.new('RGB',(600,848),'#e9eee4')
   for j,t in enumerate(tiles[offset:offset+4]):contact.paste(t,((j%2)*300,(j//2)*424))
   contact.save(out/f'contact-{offset//4+1:02}.jpg',quality=92)
  doc.close();raster={'pdf_sha256':sha(root/'report.pdf'),'dpi':120,'pages':records,'visual_inspection_claimed':False};(out/'manifest.json').write_text(json.dumps(raster,indent=2))
 manifest=root/'renders/manifest.json'
 if manifest.exists():
  raster=json.loads(manifest.read_text());result['rasters']=raster;current=raster['pdf_sha256']==sha(root/'report.pdf')and len(raster['pages'])==len(pdf.pages)and all(Path(x['path']).is_file()and sha(x['path'])==x['sha256']for x in raster['pages'])
  result['checks']['raster_manifest_current']=current;result['passed']=result['passed']and current
 (root/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--input',required=True);a.add_argument('--render',action='store_true');z=a.parse_args();r=verify(z.root,z.input,z.render);print(json.dumps({'passed':r['passed'],'checks':r['checks'],'counts':r['counts']}));raise SystemExit(0 if r['passed']else 1)
