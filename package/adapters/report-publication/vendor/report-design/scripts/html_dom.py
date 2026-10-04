"""Lossless entity handling for reviewed financial content, without importing its design."""
import html,re
from html.parser import HTMLParser
VOID={'br','meta','link','img','hr','input','area','base','source','wbr','embed','param'}
class Node:
 def __init__(self,tag='root',attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
 def walk(self):
  yield self
  for c in self.children:
   if isinstance(c,Node):yield from c.walk()
 def find(self,tag=None,cls=None):
  return next((n for n in self.walk()if(tag is None or n.tag==tag)and(cls is None or cls in n.attrs.get('class','').split())),None)
 def text(self):return ''.join(n.text()if isinstance(n,Node)else html.unescape(n)for n in self.children)
 def inner(self):return ''.join(n.outer()if isinstance(n,Node)else n for n in self.children)
 def outer(self):
  a=''.join(' '+k+('="'+html.escape(str(v),quote=True)+'"'if v is not None else'')for k,v in self.attrs.items())
  return '<'+self.tag+a+'>'+(''if self.tag in VOID else self.inner()+'</'+self.tag+'>')
class DOM(HTMLParser):
 def __init__(self,s):
  super().__init__(convert_charrefs=False);self.root=Node();self.stack=[self.root];self.source=s;self.starts=[0]+[m.end()for m in re.finditer('\n',s)];self.feed(s)
 def handle_starttag(self,t,a):
  n=Node(t,a);self.stack[-1].children.append(n)
  if t not in VOID:self.stack.append(n)
 def handle_startendtag(self,t,a):self.stack[-1].children.append(Node(t,a))
 def handle_endtag(self,t):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==t:self.stack=self.stack[:i];break
 def handle_data(self,d):self.stack[-1].children.append(d)
 def ref(self,p,n):
  l,c=self.getpos();off=self.starts[l-1]+c;raw=p+n;self.handle_data(raw+(';'if self.source[off+len(raw):off+len(raw)+1]==';'else''))
 def handle_entityref(self,n):self.ref('&',n)
 def handle_charref(self,n):self.ref('&#',n)
