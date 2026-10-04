"""Preserve DART's mixed HTML/XML cells without requiring well-formed XML."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from html.parser import HTMLParser

class Tables(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.tables=[];self.stack=[];self.cells=[];self.context=[];self.count=0
 def handle_starttag(self,tag,attrs):
  if tag=='table':
   self.count+=1;self.stack.append({'table_index':self.count,'line':self.getpos()[0],'attributes':dict(attrs),'context':' '.join(self.context[-16:])[-1200:],'rows':[]})
  elif tag=='tr' and self.stack:self.stack[-1]['rows'].append([])
  elif tag in {'td','th','te','tu'} and self.stack:
   if not self.stack[-1]['rows']:self.stack[-1]['rows'].append([])
   c={'text':'','attributes':dict(attrs)};self.stack[-1]['rows'][-1].append(c);self.cells.append((tag,c))
 def handle_endtag(self,tag):
  if tag in {'td','th','te','tu'}:
   for i in range(len(self.cells)-1,-1,-1):
    if self.cells[i][0]==tag:self.cells.pop(i);break
  elif tag=='table' and self.stack:
   table=self.stack.pop()
   for row in table['rows']:
    for cell in row:cell['text']=' '.join(cell['text'].split())
   self.tables.append(table)
 def handle_data(self,data):
  if self.cells:
   for _,cell in self.cells:cell['text']+=' '+data
  elif not self.stack and data.strip():self.context.append(' '.join(data.split()))

def extract(archive,out):
 with zipfile.ZipFile(archive) as z:
  members=[n for n in z.namelist() if n.lower().endswith('.xml')]
  if len(members)!=1:raise ValueError('Select exactly one original filing XML')
  raw=z.read(members[0])
 try:text=raw.decode('utf-8');encoding='utf-8'
 except UnicodeDecodeError:text=raw.decode('euc-kr');encoding='euc-kr'
 parser=Tables();parser.feed(text);parser.close()
 data={'original_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'member':members[0],'xml_sha256':hashlib.sha256(raw).hexdigest(),'encoding':encoding,'scope':'faithful table cells, not normalized financial or valuation approval','tables':sorted(parser.tables,key=lambda t:t['table_index'])}
 with out.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2)
 return {'tables':len(data['tables']),'source_member':members[0],'out':str(out)}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('out',type=Path);a=p.parse_args();print(json.dumps(extract(a.archive,a.out),ensure_ascii=False))
