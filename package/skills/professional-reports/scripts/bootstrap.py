#!/usr/bin/env python3
"""Resolve and verify the active immutable release using only the standard library."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def load(state):
    state=Path(state).expanduser().resolve()
    active=json.loads((state/'active.json').read_text())
    release=(state/'releases'/active['release_id']).resolve()
    if not release.is_relative_to(state/'releases'):raise ValueError('Active release escapes state root')
    manifest=json.loads((release/'release.json').read_text())
    unsigned={k:v for k,v in manifest.items() if k!='release_id'}
    actual_hash=hashlib.sha256(canonical(unsigned).encode()).hexdigest()
    if actual_hash!=active['release_id'] or manifest['release_id']!=actual_hash:raise ValueError('Release identity mismatch')
    expected={m['path']:m['sha256'] for m in manifest['members']}
    observed={}
    for p in sorted(release.rglob('*')):
        rel=p.relative_to(release)
        if any(x in {'__pycache__','.DS_Store'} for x in rel.parts) or p.suffix=='.pyc':continue
        if p.is_symlink():raise ValueError('Symlink in immutable release')
        if p.is_file() and rel.as_posix()!='release.json':
            observed[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    if observed!=expected:raise ValueError('Installed release files differ from manifest')
    return dict(package='professional-reports',version=manifest['version'],release_id=actual_hash,
                channel=manifest['channel'],root=str(release),state=str(state),verified=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',default=os.environ.get('PROFESSIONAL_REPORTS_STATE',str(Path.home()/'.local/share/professional-reports')))
    args=parser.parse_args()
    print(json.dumps(load(args.state),ensure_ascii=False,indent=2))
