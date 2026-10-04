"""Discover exact local evidence/calibration inputs declared by model atoms.

This binds supplied records; it neither supplies assumptions nor approves them.
"""
import hashlib,json
from pathlib import Path
from urllib.parse import urlsplit

def local_support(out,model=None):
 out=Path(out).resolve()
 if model is None:model=json.loads((out/'valuation-input.json').read_text())
 files={}
 def visit(value):
  if isinstance(value,dict):
   if value.get('kind') in ('evidence','assumption','synthetic') and isinstance(value.get('source'),dict):
    source=value['source'];uri=source.get('uri','')
    if not isinstance(uri,str):raise ValueError('Model source URI must be text')
    parsed=urlsplit(uri)
    if parsed.scheme or parsed.netloc:return
    if not uri:raise ValueError('Local model support path missing')
    p=Path(uri);p=(p if p.is_absolute() else out/p).resolve()
    if not p.is_relative_to(out):raise ValueError('Model support escaped current attempt')
    if not p.is_file():raise ValueError('Declared model support is missing')
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if source.get('sha256')!=digest:raise ValueError('Declared model support hash changed')
    files[p.relative_to(out).as_posix()]=digest
   else:
    for child in value.values():visit(child)
  elif isinstance(value,list):
   for child in value:visit(child)
 visit(model);return files

def validate_judgments(record):
 """Do not hand an explicitly unfinished or empty judgment register to review."""
 if not isinstance(record,dict) or record.get('status') not in ('ready','complete','completed','prepared'):
  raise ValueError('Judgment register must be finalized, still unreviewed')
 entries=record.get('judgments')
 if not isinstance(entries,list) or not entries or any(not isinstance(x,dict) or not x for x in entries):
  raise ValueError('Nonempty actual judgment records required')
 return {'status':'present_unreviewed','judgments':len(entries),'financial_approval':False}
