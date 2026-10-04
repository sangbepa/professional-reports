"""Portable release bundles and explicit source/release/activation separation."""
import os
import json
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path
from .registry import Registry
from .util import ContractError, digest, hash_data, identifier, lock, members, now, read_json, within, write_json

INCLUDE = ('pr','schemas','libraries','skills','protected','adapters')
TOP = ('plugin.json','AGENTS.md','requirements.txt','requirements-runtime.lock.txt','professional-reports','README.md')
PACKAGE_DOCS = ('installation.md','evaluation.md','library-guide.md','native-handoff.md',
                'session-workflow.md','report-speed.md','performance-profiler.md','risk-workflow.md',
                'esg-learning.md','esg-system.md','package-status.md','package-status.json',
                'valuation-quickstart.md')


def candidate_identity(root,version):
    root=Path(root);files=_files(root)
    plugin=read_json(root/'plugin.json');plugin['version']=version
    encoded=(json.dumps(plugin,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    files=[dict(path=f['path'],sha256=hashlib.sha256(encoded).hexdigest()) if f['path']=='plugin.json' else f for f in files]
    return dict(content_sha256=hash_data(files),protected_sha256=hash_data([f for f in files if f['path'].startswith('protected/')]))


def _files(root):
    root=Path(root)
    files=[]
    for directory in INCLUDE:
        if (root/directory).exists():
            files.extend(dict(path=directory+'/'+m['path'],sha256=m['sha256']) for m in members(root/directory))
    files.extend(dict(path=p,sha256=digest(root/p)) for p in TOP if (root/p).is_file())
    files.extend(dict(path='docs/'+p,sha256=digest(root/'docs'/p)) for p in PACKAGE_DOCS if (root/'docs'/p).is_file())
    return sorted(files,key=lambda f:f['path'])


def pack(root,out,version,channel='development',acceptance=None):
    root=Path(root).resolve(); out=Path(out).resolve(); identifier(version)
    if out.exists():raise ContractError('Pack destination must be new')
    if channel not in {'development','validated'}:raise ContractError('Unknown release channel')
    identity=candidate_identity(root,version)
    if channel=='validated':validate_acceptance(acceptance,identity)
    out.mkdir(parents=True)
    for f in _files(root):
        src=within(root,f['path']); dst=within(out,f['path']); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
    plugin=read_json(out/'plugin.json');plugin['version']=version;write_json(out/'plugin.json',plugin)
    reg=Registry(out)
    manifest=dict(schema_version='professional-release/1',name='professional-reports',version=version,channel=channel,
                  created_at=now(),compatibility=dict(python='>=3.11',host='Codex native tool bridge v1'),
                  components=reg.catalog(),members=_files(out),acceptance=acceptance,**identity)
    manifest['release_id']=hash_data(manifest)
    write_json(out/'release.json',manifest)
    verify(out)
    return manifest


def verify(root):
    root=Path(root).resolve(); manifest=read_json(root/'release.json')
    unsigned={k:v for k,v in manifest.items() if k!='release_id'}
    if hash_data(unsigned)!=manifest['release_id']:raise ContractError('Release manifest hash mismatch')
    # Verify the immutable bundle's actual contents, not today's source packing
    # allowlist. Older valid releases may carry a different documentation set.
    actual=sorted([m for m in members(root) if m['path']!='release.json'],key=lambda m:m['path'])
    if actual!=manifest['members']:raise ContractError('Release members changed, missing, or added')
    if Registry(root).catalog()!=manifest['components']:raise ContractError('Component manifest mismatch')
    identity=dict(content_sha256=hash_data(actual),protected_sha256=hash_data([f for f in actual if f['path'].startswith('protected/')]))
    if read_json(root/'plugin.json').get('version')!=manifest['version']:
        raise ContractError('Plugin version differs from release manifest')
    if any(manifest.get(k)!=v for k,v in identity.items()):raise ContractError('Release content identity mismatch')
    if manifest['channel']=='validated':validate_acceptance(manifest.get('acceptance'),identity)
    return manifest


def validate_acceptance(evidence,identity):
    required={'hyundai_cold_runs','samsung_regression','lg_holdout','meta_holdout','independent_review',
              'comparison_experiment','grader_calibration','new_context_install','rollback'}
    if not evidence or required-set(evidence):raise ContractError('Validated release requires complete acceptance evidence')
    if evidence.get('approved_content_sha256')!=identity['content_sha256'] or evidence.get('approved_protected_sha256')!=identity['protected_sha256']:
        raise ContractError('Acceptance does not approve this exact candidate content and protected definitions')
    runs=evidence['hyundai_cold_runs']
    if len(runs)!=3 or len({r['run_id'] for r in runs})!=3:
        raise ContractError('Need three distinct cold report runs')
    for r in runs:
        if r.get('status')!='complete' or r.get('report_seconds',float('inf'))>600 or r.get('reused_report_or_calculation') is not False:
            raise ContractError('Cold report quality and deadline both required')
        if r.get('evaluated_content_sha256')!=identity['content_sha256']:
            raise ContractError('Cold report evaluated another package content version')
    for k in required-{'hyundai_cold_runs'}:
        if evidence[k].get('status')!='pass' or not evidence[k].get('evidence_sha256'):
            raise ContractError(f'Missing acceptance evidence: {k}')
        if evidence[k].get('evaluated_content_sha256')!=identity['content_sha256']:
            raise ContractError(f'Acceptance evidence belongs to another candidate: {k}')
    # Host signs off the evidence manifest; its identity is recorded, never synthesized.
    if not evidence.get('approved_by') or not evidence.get('approval_receipt_sha256'):
        raise ContractError('Release approval must be separately attested')


def install(release,state):
    release=Path(release).resolve(); state=Path(state).resolve(); m=verify(release)
    with lock(state/'.package.lock'):
        target=state/'releases'/m['release_id']
        if target.exists():verify(target)
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            temp=Path(tempfile.mkdtemp(dir=target.parent,prefix='.install-'))
            try:
                shutil.copytree(release,temp,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
                verify(temp);os.replace(temp,target)
            finally:
                if temp.exists():shutil.rmtree(temp)
        for folder in ('runs','raw','experiments','candidates','maintenance'):(state/folder).mkdir(exist_ok=True)
    return dict(release_id=m['release_id'],path=str(target),channel=m['channel'],activated=False)


def activate(state,release_id,allow_development=False):
    state=Path(state).resolve();identifier(release_id)
    with lock(state/'.package.lock'):
        target=within(state/'releases',release_id);m=verify(target)
        if m['channel']!='validated' and not allow_development:
            raise ContractError('Development activation requires explicit --development')
        prior=read_json(state/'active.json') if (state/'active.json').exists() else None
        active=dict(release_id=release_id,path=str(target),channel=m['channel'],previous=prior,activated_at=now())
        write_json(state/'active.json',active)
    return active


def load_active(state):
    state=Path(state).resolve();active=read_json(state/'active.json')
    target=within(state/'releases',active['release_id']);m=verify(target)
    if m['release_id']!=active['release_id']:raise ContractError('Active release mismatch')
    return dict(active,path=str(target),version=m['version'])


def rollback(state):
    state=Path(state).resolve()
    # Recovery must not need to execute or validate corrupt current code.
    active=read_json(state/'active.json')
    if not active.get('previous'):raise ContractError('No previous active release')
    prior=active['previous']
    return activate(state,prior['release_id'],allow_development=prior['channel']=='development')


def archive(release,path):
    release=Path(release);verify(release)
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for f in members(release):z.write(release/f['path'],f['path'])
    return dict(path=str(Path(path).resolve()),sha256=digest(path))
