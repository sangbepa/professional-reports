"""Preserve exact execution definitions; archive capture is not a release."""
import argparse,hashlib,json,time
from pathlib import Path

def archive(out):
 snapshot=json.loads((out/'component-snapshot.json').read_text());root=Path(snapshot['root']).resolve();targets=dict(snapshot['components']);extra={}
 for folder in (root/'adapters/valuation',root/'pr'):
  for path in folder.glob('*'):
   if path.is_file() and path.suffix in {'.py','.json','.js'}:
    relative=path.relative_to(root).as_posix()
    if relative not in targets:extra[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
 vendor=root/'adapters/valuation/vendor';manifest=json.loads((vendor/'manifest.json').read_text())
 for name,digest in manifest['files'].items():
  path=(vendor/name).resolve()
  if not path.is_relative_to(vendor):raise ValueError('Vendor path outside declared assets')
  relative=path.relative_to(root).as_posix()
  if relative in targets:
   if targets[relative]!=digest:raise ValueError('Design manifest and snapshot disagree')
  else:extra[relative]=digest
 # Validate the full set before creating an archive, so stale pins fail cleanly.
 materials=[]
 for group,entries in [('pre_dispatch_snapshot',targets),('additional_archive_at_capture',extra)]:
  for relative,expected in entries.items():
   path=(root/relative).resolve()
   if not path.is_relative_to(root):raise ValueError('Definition path outside package')
   raw=path.read_bytes()
   if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Changed definition: '+relative)
   materials.append((relative,expected,raw,group))
 folder=out/'frozen-components';folder.mkdir(exist_ok=False);records={}
 for relative,digest,raw,group in materials:
  target=folder/relative;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(raw)
  if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('Archive copy changed')
  records[relative]={'sha256':digest,'archive_path':target.relative_to(out).as_posix(),'scope':group}
 record={'status':'definition_bytes_archived','captured_epoch':time.time(),'components':records,'financial_approval':False,'installed_release_changed':False,'additional_assets_are_not_retroactively_claimed_as_predispatch_pins':True}
 with (out/'frozen-component-manifest.json').open('x') as f:json.dump(record,f,indent=2)
 return {'archived_files':len(records),'initially_pinned_definitions':len(targets),'additional_assets':len(extra),'financial_approval':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();print(json.dumps(archive(a.out.resolve())))
