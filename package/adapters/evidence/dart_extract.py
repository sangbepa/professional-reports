#!/usr/bin/env python3
"""Preserve DART document text and ordered tables with byte-bound locators."""
import argparse,hashlib,json,re
from html.parser import HTMLParser
from pathlib import Path

class Document(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.text=[];self.tables=[];self.stack=[];self.ordinal=0
 def handle_starttag(self,tag,attrs):
  tag=tag.lower()
  if tag=='table':
   self.ordinal+=1;table={'id':'table-'+str(self.ordinal),'attributes':dict(attrs),'context':' '.join(self.text[-15:]),'rows':[]};self.tables.append(table);self.stack.append({'table':table,'cell':None})
  elif tag=='tr' and self.stack:
   self.stack[-1]['table']['rows'].append([]);self.stack[-1]['cell']=None
  elif tag in ('td','th','te','tu') and self.stack:
   frame=self.stack[-1]
   if not frame['table']['rows']:frame['table']['rows'].append([])
   frame['cell']={'tag':tag,'attributes':dict(attrs),'text':''};frame['table']['rows'][-1].append(frame['cell'])
 def handle_endtag(self,tag):
  tag=tag.lower()
  if tag=='table' and self.stack:self.stack.pop()
  elif tag in ('td','th','te','tu','tr') and self.stack:self.stack[-1]['cell']=None
 def handle_data(self,value):
  value=' '.join(value.split())
  if not value:return
  self.text.append(value)
  for frame in self.stack:
   cell=frame['cell']
   if cell is not None:cell['text']+=((' ' if cell['text'] else '')+value)

def extract(source,out):
 source=Path(source);raw=source.read_bytes();encoding=re.search(br'encoding=["\']([^"\']+)',raw[:200]);encoding=encoding.group(1).decode() if encoding else 'utf-8'
 d=Document();d.feed(raw.decode(encoding));d.close();out=Path(out);out.mkdir(parents=True,exist_ok=False)
 (out/'document.txt').write_text('\n'.join(d.text)+'\n')
 result={'source_sha256':hashlib.sha256(raw).hexdigest(),'extractor':'dart-htmlparser-v2','source_encoding':encoding,'table_count':len(d.tables),'tables':d.tables,'financial_normalization':'not_performed','publication_validation':'separate metadata manifest','locators':'original ordered table ordinal and row/cell index; retain raw XML for verification','nested_tables':'Nested content retained in both containing cell and its own table; do not sum duplicate presentations.'}
 (out/'tables.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args();r=extract(a.input,a.out);print(json.dumps({'tables':r['table_count'],'source_sha256':r['source_sha256']}))
