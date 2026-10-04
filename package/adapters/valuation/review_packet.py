"""Deterministic reviewer navigation, never a verdict or replacement for review."""
import argparse,hashlib,json
from pathlib import Path
from pypdf import PdfReader

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def raster_pages(out,pdf_hash):
 """Render the actual saved PDF once; generated pixels do not constitute review."""
 import pypdfium2 as pdfium
 from PIL import Image,ImageDraw
 destination=out/'review-frames';destination.mkdir()
 document=pdfium.PdfDocument(out/'report.pdf');frames=[];contacts=[];group=[]
 try:
  for i in range(len(document)):
   page=document[i]
   try:
    bitmap=page.render(scale=1.75)
    try:image=bitmap.to_pil().convert('RGB')
    finally:bitmap.close()
   finally:page.close()
   file=destination/f'page-{i+1:03d}.png';image.save(file)
   frames.append({'page':i+1,'path':file.relative_to(out).as_posix(),'sha256':digest(file),'pdf_sha256':pdf_hash,'review_status':'unreviewed'})
   group.append((i+1,image))
   if len(group)==3 or i==len(document)-1:
    canvas=Image.new('RGB',(sum(im.width for _,im in group),max(im.height for _,im in group)+24),'white');draw=ImageDraw.Draw(canvas);x=0
    for number,im in group:
     draw.text((x+5,5),f'PDF page {number}',fill='black');canvas.paste(im,(x,24));x+=im.width
    file=destination/f'contact-{len(contacts)+1:03d}.png';canvas.save(file)
    contacts.append({'pages':[n for n,_ in group],'path':file.relative_to(out).as_posix(),'sha256':digest(file),'pdf_sha256':pdf_hash,'review_status':'unreviewed'})
    for _,im in group:im.close()
    canvas.close();group=[]
 finally:document.close()
 if digest(out/'report.pdf')!=pdf_hash:raise ValueError('PDF changed during rasterization')
 return {'source_pdf_sha256':pdf_hash,'scale':1.75,'pages':frames,'contacts':contacts,'visual_review':'not_performed'}
def protected_paths(out):
 """Exact approved snapshot locations; never search or infer evaluator versions."""
 snapshot=json.loads((out/'component-snapshot.json').read_text())
 entries={}
 for relative,expected in snapshot['components'].items():
  if not relative.startswith('protected/'):continue
  path=(out/'frozen-components'/relative).resolve()
  if not path.is_relative_to((out/'frozen-components').resolve()) or digest(path)!=expected:
   raise ValueError('Protected snapshot changed: '+relative)
  entries[relative]={'path':str(path),'sha256':expected}
 if not entries:raise ValueError('Protected evaluator snapshot required')
 return entries

def role_packet(out,role):
 """Read only current role targets, preserving navigation and all review duties."""
 out=Path(out).resolve()
 packet=json.loads((out/'review-navigation.json').read_text())
 if role not in ('visual-left','visual-right','reviewer'):raise ValueError('Unknown review role')
 if digest(out/'report.pdf')!=packet['input_artifacts']['report.pdf']:raise ValueError('PDF changed')
 profiles=protected_paths(out)
 if profiles!=packet['protected_profiles']:raise ValueError('Evaluator navigation changed')
 agent=json.loads((out/(role+'-spawn.json')).read_text())['response']['agent_id']
 assigned=packet['document_assignments'].get(role,[])
 images=[]
 for frame in packet['pdf_rasters']['contacts']:
  if not set(frame['pages']).intersection(assigned):continue
  path=(out/frame['path']).resolve()
  if not path.is_relative_to(out) or digest(path)!=frame['sha256']:raise ValueError('Page image changed')
  images.append({'pages':frame['pages'],'path':str(path),'sha256':frame['sha256']})
 return {'kind':'role_navigation_not_approval','financial_approval':False,'role':role,'agent_id':agent,
  'attempt_id':packet['attempt_id'],'navigation_sha256':digest(out/'review-navigation.json'),
  'pdf_sha256':packet['input_artifacts']['report.pdf'],'protected_profiles':profiles,
  'assigned_pages':assigned,'contact_images':images,
  'individual_page_pattern':str(out/'review-frames/page-{page:03d}.png'),
  'page_text_command':'Read only assigned pdf_pages fields from review-navigation.json; full evidence stays on disk.'}

def review_draft(out,role):
 """Unreviewed record scaffolding only; actual reviewer must inspect and judge."""
 if role not in ('visual-left','visual-right'):raise ValueError('Document role required')
 packet=role_packet(out,role);out=Path(out).resolve()
 d={'attempt_id':packet['attempt_id'],'reviewer_agent_id':packet['agent_id'],
    'navigation_sha256':packet['navigation_sha256'],'pdf_sha256':packet['pdf_sha256'],
    'status':'insufficient','document_quality_score':None,'findings':[],
    'pdf_page_reviews':[{'page':number,'pdf_sha256':packet['pdf_sha256'],'status':'unreviewed',
      'scope':'Not inspected','raster_paths_inspected':[]} for number in packet['assigned_pages']],
    'evaluation_profile_hashes':{path:meta['sha256'] for path,meta in packet['protected_profiles'].items()},
    'scaffold_only':True,'visual_review_performed':False}
 path=out/(role+'-review-draft.json')
 with path.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
 return {**packet,'unreviewed_draft_path':str(path),
  'draft_instructions':'Inspect every assigned page. Fill actual findings, score, status and actual inspected raster paths/scope. Save a separately named ROLE-review.json only after judgment. Unreviewed scaffold never grants a pass.'}

def build(out):
 out=Path(out).resolve()
 publication=json.loads((out/'publication-verification.json').read_text())
 if publication.get('status')!='published':raise ValueError('Published artifacts required')
 for name,h in publication['artifacts'].items():
  p=(out/name).resolve()
  if not p.is_relative_to(out) or digest(p)!=h:raise ValueError('Publication changed: '+name)
 result=json.loads((out/'model-result.json').read_text())
 pdf_hash=digest(out/'report.pdf');pages=[]
 rasters=raster_pages(out,pdf_hash)
 for i,page in enumerate(PdfReader(out/'report.pdf').pages,1):
  pages.append({'page':i,'pdf_sha256':pdf_hash,'text':page.extract_text() or '',
                'visual_review':'not_performed','review_status':'unreviewed'})
 sources={}
 for path,meta in result['input_metadata'].items():
  source=meta.get('source',{});key=json.dumps(source,sort_keys=True)
  entry=sources.setdefault(key,{'source':source,'paths':[],'review_status':'unreviewed'})
  entry['paths'].append(path)
 packet={'kind':'review_navigation_not_approval','attempt_id':json.loads((out/'mandate.json').read_text())['attempt_id'],
  'financial_approval':False,'input_artifacts':{n:digest(out/n) for n in ('valuation-input.json','model-result.json','model-verification.json','narrative.json','argument-record.json','report.pdf')},
  'protected_profiles':protected_paths(out),'sources':list(sources.values()),'pdf_pages':pages,'pdf_rasters':rasters,
  'document_assignments':{'visual-left':list(range(1,(len(pages)+1)//2+1)),'visual-right':list(range((len(pages)+1)//2+1,len(pages)+1))},
  'instructions':'Read protected criteria and actual originals. Independently test calculations and judgments. Page text does not prove visual legibility; inspect rendered pages. Record exact scope and unresolved findings. This packet grants no pass.'}
 with (out/'review-navigation.json').open('x') as f:json.dump(packet,f,ensure_ascii=False,indent=2)
 return {'status':'navigation_prepared','pages':len(pages),'source_groups':len(sources),'financial_approval':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--role',choices=['visual-left','visual-right','reviewer']);p.add_argument('--draft',action='store_true');a=p.parse_args();print(json.dumps(review_draft(a.out,a.role) if a.draft else role_packet(a.out,a.role) if a.role else build(a.out),ensure_ascii=False))
