"""Append-only execution ledger. Host actions and judgments are explicitly attested.

This is a cooperating-local-process integrity boundary, not protection against a
host administrator forging receipts or replacing the complete state directory.
"""
from __future__ import annotations
import functools
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from .planning import impact, meta_check, plan_check
from .registry import Registry
from .schema import validate
from .util import (ContractError, canonical, digest, hash_data, identifier, immutable_json,
                   lock, members, now, read_json, timestamp, within, write_json)

LOADED_ENGINE_MEMBERS = members(Path(__file__).resolve().parent)


def copy_atomic(source,dest):
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(dir=dest.parent,prefix='.copy-');os.close(fd)
    try:
        shutil.copyfile(source,temp)
        if digest(source)!=digest(temp):raise ContractError('Source changed while freezing artifact')
        os.replace(temp,dest)
    finally:
        if os.path.exists(temp):os.unlink(temp)


@functools.lru_cache(maxsize=1)
def boot_id():
    linux = Path('/proc/sys/kernel/random/boot_id')
    if linux.exists():
        return linux.read_text().strip()
    try:
        return subprocess.check_output(['/usr/sbin/sysctl', '-n', 'kern.boottime'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def transaction(fn):
    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        with lock(self.path / '.ledger.lock'):
            self.events = self.read_events()
            self._assert_open(fn.__name__)
            self._check_pin()
            return fn(self, *args, **kwargs)
    return wrapped


class Run:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.header = read_json(self.path / 'run.json')
        self.registry = Registry(self.header['package_root'])
        self.events = self.read_events()

    @classmethod
    def create(cls, path, package_root, request):
        validate(package_root, 'request', request)
        timestamp(request['information_cutoff'])
        if timestamp(request['requested_at']) > timestamp(now()):
            raise ContractError('Request intake timestamp cannot be in the future')
        path = Path(path).resolve()
        path.mkdir(parents=True, exist_ok=False)
        reg = Registry(package_root)
        from .package import _files, verify
        released = verify(package_root) if (Path(package_root)/'release.json').exists() else None
        pin = dict(components=reg.catalog(), evaluations={p.name:digest(p) for p in
                   (Path(package_root)/'protected/evaluations').glob('*.json')},
                   members=released['members'] if released else _files(package_root),
                   membership_policy='release_manifest' if released else 'source_pack')
        immutable_json(path/'run.json', dict(schema_version='professional-run/1', request=request,
            package_root=str(Path(package_root).resolve()), release_pin=pin,
            executing_engine=LOADED_ENGINE_MEMBERS,
            release_sha256=released['release_id'] if released else hash_data(pin), created_at=now()))
        (path/'work').mkdir()
        obj = cls(path)
        with lock(path/'.ledger.lock'):
            obj._event('run_created', dict(request_id=request['id'], mode=request['mode']))
        return obj

    def read_events(self):
        p = self.path/'events.jsonl'
        if not p.exists():
            return []
        import json
        rows=[]
        previous='0'*64
        for line in p.read_text().splitlines():
            e=json.loads(line)
            h=e.pop('sha256')
            if e['seq'] != len(rows)+1 or e['previous'] != previous or hash_data(e) != h:
                raise ContractError('Event ledger integrity failure')
            e['sha256']=h
            rows.append(e)
            previous=h
        return rows

    def _event(self, kind, data):
        e=dict(seq=len(self.events)+1, previous=self.events[-1]['sha256'] if self.events else '0'*64,
               kind=kind, utc=now(), monotonic_ns=time.monotonic_ns(), boot_id=boot_id(), data=data)
        e['sha256']=hash_data(e)
        with (self.path/'events.jsonl').open('a',encoding='utf-8') as f:
            f.write(canonical(e)+'\n'); f.flush(); os.fsync(f.fileno())
        self.events.append(e)
        return e

    def _assert_open(self, method):
        if any(e['kind']=='run_finished' for e in self.events) and method not in {'export'}:
            raise ContractError('Run is sealed; start a new run instead of rewriting it')

    def _latest(self, kind):
        return next((e['data'] for e in reversed(self.events) if e['kind']==kind),None)

    def _object(self, relative):
        data=read_json(within(self.path, relative['path']))
        if hash_data(data)!=relative['sha256']:
            raise ContractError('Frozen record changed')
        return data

    def _store(self, folder, data):
        h=hash_data(data)
        relative=f'{folder}/{h}.json'
        p=self.path/relative
        if p.exists():
            if hash_data(read_json(p)) != h: raise ContractError('Snapshot collision/tamper')
        else:
            immutable_json(p,data)
        return dict(path=relative,sha256=h)

    @property
    def meta(self):
        r=self._latest('meta_registered')
        return self._object(r['object']) if r else None

    @property
    def plan(self):
        r=self._latest('plan_registered')
        return self._object(r['object']) if r else None

    def _check_pin(self):
        from .package import _files, verify
        if (self.registry.root/'release.json').exists():
            manifest=verify(self.registry.root)
            if manifest['release_id']!=self.header['release_sha256']:
                raise ContractError('Installed release differs from run pin: release identity changed')
            current_members=manifest['members']
        else:
            if self.header['release_pin'].get('membership_policy')=='release_manifest':
                raise ContractError('Pinned release manifest is missing')
            current_members=_files(self.registry.root)
        if current_members!=self.header['release_pin']['members']:
            raise ContractError('Pinned package code, schemas or resources changed during run')
        loaded=LOADED_ENGINE_MEMBERS
        if members(Path(__file__).resolve().parent)!=loaded:
            raise ContractError('Engine source changed after this interpreter loaded; restart with pinned release')
        if loaded!=self.header['executing_engine']:
            raise ContractError('Executing engine differs from pinned implementation; use the run release executable')
        declared=self.registry.root/'pr'
        if declared.exists() and loaded!=members(declared):
            raise ContractError('Executing engine differs from the pinned package code')
        actual={r['id']:r for r in self.registry.catalog()}
        for ref in self.header['release_pin']['components']:
            if actual.get(ref['id'])!=ref:
                raise ContractError(f"Pinned release changed: {ref['id']}")
        for name,h in self.header['release_pin']['evaluations'].items():
            if digest(self.registry.root/'protected/evaluations'/name)!=h:
                raise ContractError('Protected evaluation changed during run')

    @transaction
    def register_meta(self, meta):
        self._check_pin()
        meta_check(self.registry,self.header['request'],meta)
        prior=self.meta
        if prior and prior['evaluation']!=meta['evaluation']:
            approval=meta.get('evaluation_change_approval',{})
            if (approval.get('kind')!='human-approval' or approval.get('from')!=prior['evaluation']
                    or approval.get('to')!=meta['evaluation'] or not approval.get('user_message_reference')):
                raise ContractError('Protected evaluation change requires concrete human approval')
        if meta['previous'] != (hash_data(prior) if prior else None) or meta['revision'] != (prior['revision']+1 if prior else 1):
            raise ContractError('Meta revision does not extend latest record')
        if self.plan:
            self._invalidate([n['id'] for n in self.plan['nodes']], 'Meta mandate selection changed')
        self._event('meta_registered',dict(object=self._store('meta',meta)))
        return hash_data(meta)

    @transaction
    def register_plan(self, plan):
        self._check_pin()
        if not self.meta or self.meta['action'] not in {'reuse','compose','candidate'}:
            raise ContractError('Need executable or provisional meta decision before planning')
        checked=plan_check(self.registry,self.meta,plan)
        prior=self.plan
        if plan['previous'] != (hash_data(prior) if prior else None) or plan['revision'] != (prior['revision']+1 if prior else 1):
            raise ContractError('Plan revision does not extend latest record')
        changed=[]
        if prior:
            old={n['id']:n for n in prior['nodes']}; new={n['id']:n for n in plan['nodes']}
            changed=[i for i in set(old)|set(new) if old.get(i)!=new.get(i)]
            if prior['facts']!=plan['facts']: changed=list(new)
            for i in set(old)&set(new):
                if old[i]!=new[i] and new[i]['revision']!=old[i]['revision']+1:
                    raise ContractError('Changed task must increment its revision')
            self._invalidate(sorted(set(impact(prior['nodes'],seeds=changed))|set(impact(plan['nodes'],seeds=changed))), plan['reason'])
        self._event('plan_registered',dict(object=self._store('plans',plan),changed_nodes=changed,checks=checked))
        return checked

    def states(self):
        states={n['id']:dict(status='planned',attempt_id=None) for n in (self.plan or {}).get('nodes',[])}
        for e in self.events:
            d=e['data']; k=e['kind']
            if k=='invalidated':
                for i in d['nodes']:
                    if i in states: states[i]=dict(status='invalidated',attempt_id=None)
            elif k=='dispatched':
                if d['node_id'] in states: states[d['node_id']]=dict(status='running',attempt_id=d['attempt_id'])
            elif k in {'result_submitted','task_reviewed','attempt_failed'}:
                if d['node_id'] in states and states[d['node_id']]['attempt_id']==d['attempt_id']:
                    states[d['node_id']]['status']=d['status']
        return states

    @property
    def risk(self):
        record = self._latest('risk_registered')
        return self._object(record['object']) if record else None

    def _risk_checks(self, bundle, profile):
        from .risk import check_bundle
        checked=check_bundle(bundle,profile,self.plan,self.snapshots())
        for claim in bundle['claims']:
            for ref in claim['input_refs']:
                snapshot=self.snapshots()[ref['id']]
                if digest(within(self.path,snapshot['path']))!=ref['sha256']:
                    raise ContractError('Risk input original changed after snapshot')
            node=self.node(claim['node_id'])
            provisional=any(self.registry.resolve(ref)[0]['status']=='provisional'
                            for ref in [node['expert'],*node['skills'],node['runtime']])
            if provisional:
                minimum=set(profile['high_minimum'])|set(profile['all_minimum'])|set(profile['medium_minimum'])
                assessment=next(a for a in bundle['assessments'] if a['claim_id']==claim['id'])
                missing=minimum-set(assessment['procedures'])
                checked['required_procedures'][claim['id']]=sorted(minimum|set(checked['required_procedures'][claim['id']]))
                if missing:
                    checked['issues'].append(dict(code='pinned_provisional_component_floor',blocking=True,claim_id=claim['id'],missing=sorted(missing)))
        return checked

    def risk_status(self):
        """Current evidence only; a proposed policy never supplies authority."""
        self._check_pin()
        mode = self.header['request'].get('risk_mode', 'legacy')
        bundle = self.risk
        if not bundle:
            return dict(mode=mode, issues=['Missing risk assessment'] if mode == 'enforced' else [],
                        required_procedures={}, reduction_requested=False, independently_confirmed=False)
        event = self._latest('risk_registered')
        profile = self._object(event['profile'])
        checked = self._risk_checks(bundle, profile)
        checked['mode'] = mode
        confirmed = self._latest('risk_reviewed')
        confirmed = confirmed if confirmed and confirmed['risk_sha256'] == hash_data(bundle) else None
        valid = False
        if confirmed and confirmed['verdict'] == 'pass':
            state = self.states().get(self.attempt(confirmed['review_task_attempt'])['node_id'], {})
            valid = state.get('attempt_id') == confirmed['review_task_attempt'] and state.get('status') == 'verified'
            if valid:
                self._artifacts_intact(confirmed['review_task_attempt'])
        checked['independently_confirmed'] = valid
        if not valid:
            checked['issues'].append(dict(code='independent_risk_confirmation_missing',blocking=True,claim_id=None))
        return checked

    @transaction
    def register_risk(self, bundle, profile_path):
        if not self.plan:
            raise ContractError('Risk assessment needs a registered plan')
        profile_path = within(self.registry.root, profile_path)
        profile = read_json(profile_path)
        if digest(profile_path) != bundle['profile_sha256']:
            raise ContractError('Risk profile hash mismatch')
        if profile.get('status') == 'approved':
            if 'protected' not in profile_path.relative_to(self.registry.root).parts:
                raise ContractError('Approved risk profile must belong to pinned protected definitions')
            approval = profile.get('approval', {})
            reference=approval.get('user_message_reference')
            if approval.get('kind') != 'human-approval' or not isinstance(reference,str) or not reference.strip():
                raise ContractError('Risk profile requires concrete human adoption evidence')
        validate(self.registry.root, 'risk', bundle)
        checked = self._risk_checks(bundle, profile)
        prior = self.risk
        if bundle['previous'] != (hash_data(prior) if prior else None) or bundle['revision'] != (prior['revision'] + 1 if prior else 1):
            raise ContractError('Risk revision must extend the latest assessment')
        if prior:
            changed = {c['node_id'] for c in prior['claims']} | {c['node_id'] for c in bundle['claims']}
            self._invalidate(impact(self.plan['nodes'], seeds=sorted(changed)), 'Risk or control assessment changed')
        self._event('risk_registered', dict(object=self._store('risk', bundle),
                     profile=self._store('risk-profiles', profile), checks=checked))
        return checked

    @transaction
    def review_risk(self, record):
        bundle = self.risk
        if not bundle or record['risk_sha256'] != hash_data(bundle):
            raise ContractError('Risk confirmation targets a stale assessment')
        if (record.get('verdict') not in {'pass', 'revise', 'insufficient'} or not self._meaningful_evidence(record.get('evidence'))):
            raise ContractError('Risk confirmation requires a verdict and evidence')
        attempt_id = record['review_task_attempt']
        attempt = self._current(attempt_id, {'verified'})
        self._artifacts_intact(attempt_id)
        actor = self.binding(attempt_id)['agent_id']
        if actor != record['reviewer_agent_id'] or self.node(attempt['node_id']).get('review_role') != 'risk':
            raise ContractError('Independent risk-review execution is required')
        if attempt.get('risk_sha256') != hash_data(bundle):
            raise ContractError('Reviewer did not receive this risk assessment in its frozen brief')
        if actor in {c['producer_agent_id'] for c in bundle['claims']}:
            raise ContractError('Producer cannot confirm its own risk plan')
        if any(e['kind'] == 'risk_reviewed' and e['data']['review_task_attempt'] == attempt_id for e in self.events):
            raise ContractError('Risk reviewer execution already submitted a verdict')
        if record['verdict'] == 'pass':
            checked = self._risk_checks(bundle, self._object(self._latest('risk_registered')['profile']))
            if checked['issues']:
                raise ContractError('Risk reviewer cannot override unresolved risk requirements')
        self._event('risk_reviewed', record)
        return record

    @staticmethod
    def _meaningful_evidence(value):
        return isinstance(value,list) and bool(value) and all(isinstance(v,str) and v.strip() for v in value)

    @transaction
    def record_procedure(self, record):
        bundle = self.risk
        if not bundle or record['risk_sha256'] != hash_data(bundle):
            raise ContractError('Procedure targets a stale risk assessment')
        claim = next((c for c in bundle['claims'] if c['id'] == record['claim_id']), None)
        if not claim or record['procedure'] not in {'code', 'source', 'recalculate', 'judgment', 'document'}:
            raise ContractError('Unknown claim or procedure')
        if not self._meaningful_evidence(record.get('evidence')) or not record.get('targets'):
            raise ContractError('Procedure needs actual evidence and target hashes')
        if (not claim.get('artifact_name') or record.get('claim_locator')!=claim['locator']
                or any(t.get('name')!=claim['artifact_name'] for t in record['targets'])):
            raise ContractError('Procedure must bind the exact claim artifact and locator')
        examiner = self._current(record['task_attempt'], {'verified'})
        self._artifacts_intact(record['task_attempt'])
        if self.binding(record['task_attempt'])['agent_id'] != record['agent_id']:
            raise ContractError('Procedure actor differs from actual binding')
        state = self.states()[claim['node_id']]
        if not state['attempt_id'] or state['status'] not in {'verified', 'review_pending'}:
            raise ContractError('Procedure has no current producer result')
        target_attempt = state['attempt_id']
        target = self._artifacts_intact(target_attempt)
        actual = {(a['name'], a['sha256']) for a in target['artifacts']}
        if any((t['name'], t['sha256']) not in actual for t in record['targets']):
            raise ContractError('Procedure targets stale or foreign artifacts')
        if record['task_attempt']!=target_attempt:
            dependency=examiner['dependencies'].get(claim['node_id'],{})
            if dependency.get('attempt_id')!=target_attempt:
                raise ContractError('Procedure execution never received its actual target artifacts')
        check_id='risk/'+claim['id']+'/'+record['procedure']
        if not any(c['id']==check_id and c['passed'] and isinstance(c.get('evidence'),str) and c['evidence'].strip()
                   for c in self.result(record['task_attempt'])['checks']):
            raise ContractError('Procedure lacks an executed check bound to this claim and procedure')
        if record['procedure'] != 'code':
            role = {'source': 'source', 'recalculate': 'model', 'judgment': 'judgment', 'document': 'document'}[record['procedure']]
            if self.node(examiner['node_id']).get('review_role') != role:
                raise ContractError('Procedure requires the corresponding independent reviewer role')
            if self.binding(target_attempt)['agent_id'] == record['agent_id']:
                raise ContractError('Producer cannot perform its own independent procedure')
            dependency = examiner['dependencies'].get(claim['node_id'], {})
            if dependency.get('attempt_id') != target_attempt:
                raise ContractError('Procedure target was absent from actual reviewer dependencies')
        if examiner.get('risk_sha256') != hash_data(bundle):
            raise ContractError('Procedure execution did not receive this risk version')
        record = dict(record, target_attempt=target_attempt)
        self._event('risk_procedure_recorded', dict(object=self._store('risk-procedures', record)))
        return record

    @transaction
    def record_cost(self, record):
        from .cost import summarize
        if 'attempt_id' in record and not record['attempt_id']:
            raise ContractError('Explicit cost attempt binding must be nonempty')
        if not record.get('attempt_id') and not record.get('task_attempt') and 'owner' in record:
            if record['owner'] not in ('main','package-development','unattributed'):
                raise ContractError('Task cost owner requires an actual attempt binding')
        if 'task_attempt' in record:
            if not record['task_attempt'] or ('attempt_id' in record and record['attempt_id']!=record['task_attempt']):
                raise ContractError('Conflicting cost task attempt aliases')
            record=dict(record,attempt_id=record['task_attempt'])
        if any(k in record for k in ('node_id','task_revision','node_revision','plan_sha256')) and not record.get('attempt_id'):
            raise ContractError('Task-attributed cost requires an actual attempt binding')
        if record.get('attempt_id'):
            attempt=self.attempt(record['attempt_id'])
            for key,expected in [('node_id',attempt['node_id']),('task_revision',attempt['node']['revision']),
                                 ('node_revision',attempt['node']['revision']),('plan_sha256',attempt['plan_sha256'])]:
                if key in record and record[key]!=expected:
                    raise ContractError('Observed cost attribution differs from actual task execution')
            if 'agent_id' in record and record['agent_id']!=self.binding(record['attempt_id'])['agent_id']:
                raise ContractError('Observed cost actor differs from actual task binding')
            actual_owner=dict(attempt_id=attempt['attempt_id'],node_id=attempt['node_id'],
                              agent_id=self.binding(record['attempt_id'])['agent_id'],task_revision=attempt['node']['revision'])
            if 'owner' in record and record['owner'] not in (actual_owner,actual_owner['agent_id']):
                raise ContractError('Observed cost owner differs from actual task binding')
            if record.get('phase')=='setup' and attempt['node']['expert']['id']!='runtime-engineer':
                raise ContractError('Company task costs cannot be reclassified as environment setup')
        summarize([record])
        existing = [self._object(e['data']['object']) for e in self.events if e['kind'] == 'cost_observed']
        summarize(existing + [record])
        if record in existing:
            return dict(recorded=False, reason='Exact response receipt already recorded')
        self._event('cost_observed', dict(object=self._store('cost', record)))
        return dict(recorded=True, response_id=record.get('response_id'))

    def cost_status(self):
        from .cost import summarize
        return summarize([self._object(e['data']['object']) for e in self.events if e['kind'] == 'cost_observed'])

    def snapshots(self):
        return {e['data']['id']:e['data'] for e in self.events if e['kind']=='snapshot_registered'}

    def _invalidate(self,nodes,reason):
        if nodes: self._event('invalidated',dict(nodes=nodes,reason=reason))

    @transaction
    def invalidate(self,fields,reason):
        nodes=impact(self.plan['nodes'],fields=fields)
        self._invalidate(nodes,reason)
        return nodes

    @transaction
    def snapshot(self, identity, file, fields, kind='data', eligible=True, metadata=None):
        identifier(identity)
        if kind=='source': raise ContractError('Use source registration to enforce cutoff')
        return self._snapshot(identity,file,fields,kind,eligible,metadata or {})

    def _snapshot(self,identity,file,fields,kind,eligible,metadata):
        file=Path(file); h=digest(file); rel=f'snapshots/{h}/{file.name}'
        dest=self.path/rel
        if not dest.exists():
            copy_atomic(file,dest)
        elif digest(dest)!=h: raise ContractError('Snapshot tamper')
        prior=self.snapshots().get(identity)
        d=dict(id=identity,path=rel,sha256=h,fields=fields,kind=kind,eligible=eligible,metadata=metadata,
               version=(prior['version']+1 if prior else 1))
        if prior and (prior['sha256']!=h or prior['metadata']!=metadata or prior['eligible']!=eligible):
            self._invalidate(impact(self.plan['nodes'],fields=set(fields)|set(prior['fields']),
                seeds=[n['id'] for n in self.plan['nodes'] if identity in n['inputs']]) if self.plan else [],'Input snapshot changed')
        self._event('snapshot_registered',d)
        return d

    @transaction
    def source(self,source,fields):
        validate(self.registry.root,'source',source)
        eligible=False; reason='publication timing unverified'
        if source['published_at'] and source['publication_evidence']:
            eligible=timestamp(source['published_at'])<=timestamp(self.header['request']['information_cutoff'])
            reason='within information cutoff' if eligible else 'published after information cutoff'
        elif source.get('publication_window') and source['publication_evidence']:
            window=source['publication_window']
            if timestamp(window['not_before'])>timestamp(window['not_after']):raise ContractError('Invalid publication interval')
            eligible=timestamp(window['not_after'])<=timestamp(self.header['request']['information_cutoff'])
            reason='publication day/interval entirely before cutoff' if eligible else 'publication interval overlaps or exceeds cutoff'
        if timestamp(source['retrieved_at'])<timestamp(source['published_at']) if source['published_at'] else False:
            raise ContractError('Retrieval precedes claimed publication')
        meta={k:v for k,v in source.items() if k!='path'}
        meta['eligibility_reason']=reason
        return self._snapshot(source['id'],source['path'],fields,'source',eligible,meta)

    def node(self,identity):
        n=next((n for n in (self.plan or {}).get('nodes',[]) if n['id']==identity),None)
        if not n: raise ContractError(f'Unknown current task: {identity}')
        return n

    def attempt(self,identity):
        d=next((e['data'] for e in self.events if e['kind']=='dispatched' and e['data']['attempt_id']==identity),None)
        if not d: raise ContractError('Unknown attempt')
        return self._object(d['object'])

    def binding(self,identity):
        d=next((e['data'] for e in reversed(self.events) if e['kind']=='agent_bound' and e['data']['attempt_id']==identity),None)
        return self._object(d['object']) if d else None

    def result(self,identity):
        d=next((e['data'] for e in self.events if e['kind']=='result_submitted' and e['data']['attempt_id']==identity),None)
        return self._object(d['object']) if d else None

    def _current(self,attempt_id,statuses=None):
        a=self.attempt(attempt_id); state=self.states().get(a['node_id'])
        if not state or state['attempt_id']!=attempt_id:
            raise ContractError('Late response from an invalidated or replaced attempt')
        if statuses and state['status'] not in statuses:
            raise ContractError(f"Invalid task state: {state['status']}")
        return a

    def _artifacts_intact(self,attempt_id):
        r=self.result(attempt_id)
        if not r: raise ContractError('Dependency has no result')
        for a in r['artifacts']:
            if digest(within(self.path,a['path']))!=a['sha256']:
                raise ContractError('Output artifact tampered after submission')
        return r

    def _dependencies_current(self,a):
        states=self.states()
        allowed={'verified','review_pending','needs_revision'} if a['node'].get('review_role') else {'verified'}
        for node,saved in a['dependencies'].items():
            current=states.get(node,{})
            if current.get('attempt_id')!=saved['attempt_id'] or current.get('status') not in allowed:
                raise ContractError('Dependency result or acceptance changed since dispatch')
            if self._artifacts_intact(saved['attempt_id'])!=saved:raise ContractError('Dependency snapshot changed')
        for snapshot in a['inputs']:
            current=self.snapshots().get(snapshot['id'])
            if current!=snapshot or digest(within(self.path,snapshot['path']))!=snapshot['sha256']:
                raise ContractError('Bound input changed since dispatch')

    def _descendants(self,node,reason,exclude=()):
        affected=set(impact(self.plan['nodes'],seeds=[node]))-{node}-set(exclude)
        self._invalidate(sorted(affected),reason)

    def outstanding_attempts(self):
        issued={e['data']['attempt_id'] for e in self.events if e['kind']=='dispatched'}
        released={e['data']['attempt_id'] for e in self.events if e['kind']=='worker_released'}
        # Submitted work is terminal task execution; invalidation alone is not.
        terminal={e['data']['attempt_id'] for e in self.events if e['kind']=='result_submitted'}
        return issued-released-terminal

    @transaction
    def release_worker(self,attempt_id,receipt):
        self.attempt(attempt_id)
        if not receipt.get('tool') or not receipt.get('response'):
            raise ContractError('Need actual native close/cancel/terminal receipt')
        binding=self.binding(attempt_id)
        if binding and receipt.get('agent_id')!=binding['agent_id']:
            raise ContractError('Worker release receipt belongs to another agent')
        response=receipt['response']
        if response.get('success') is False or response.get('error') or response.get('timed_out'):
            raise ContractError('Failed or nonterminal host receipt does not release worker capacity')
        if receipt['tool'] not in {'multi_agent_v1.close_agent','multi_agent_v1.wait_agent'}:
            raise ContractError('Unrecognized native terminal receipt')
        status=response.get('previous_status',response.get('status'))
        if isinstance(status,dict) and receipt.get('agent_id') in status:status=status[receipt['agent_id']]
        terminal=(status in {'shutdown','completed','errored'} if isinstance(status,str) else
                  isinstance(status,dict) and bool({'completed','errored'}&set(status)))
        if not terminal:raise ContractError('Worker termination or completion has not been confirmed')
        self._event('worker_released',dict(attempt_id=attempt_id,receipt=receipt))

    def ready(self):
        if not self.plan or not self.meta or self.plan['meta_hash']!=hash_data(self.meta): return []
        states=self.states(); snapshots=self.snapshots()
        plan_record=self._latest('plan_registered')
        pending_rules=plan_record['checks']['pending_rules']
        permitted=None
        if pending_rules:
            permitted={self.plan['applicability_assessments'][r['rule']]['task_id'] for r in pending_rules}
            while True:
                upstream=permitted|{d for n in self.plan['nodes'] if n['id'] in permitted for d in n['depends_on']}
                if upstream==permitted:break
                permitted=upstream
        return [n['id'] for n in self.plan['nodes'] if (permitted is None or n['id'] in permitted)
                and states[n['id']]['status'] in {'planned','invalidated','needs_revision','missing_data','failed'}
                and all(states[d]['status'] in ({'verified','review_pending','needs_revision'} if n.get('review_role') else {'verified'}) for d in n['depends_on'])
                and all(i in snapshots and snapshots[i]['eligible'] for i in n['inputs'])]

    @transaction
    def dispatch(self,identity,support):
        self._check_pin()
        budget=self.budget()
        if budget['enforced'] and budget['stop_work']:
            raise ContractError('Report work budget exhausted before deadline; preserve results and deliver the current disposition')
        starts=[e['seq'] for e in self.events if e['kind']=='environment_wait_started']
        ends=[e['seq'] for e in self.events if e['kind']=='environment_wait_ended']
        if starts and max(starts)>max(ends,default=0):
            raise ContractError('Report globally waiting on environment')
        if identity not in self.ready(): raise ContractError('Task is not ready')
        if len(self.outstanding_attempts())>=6: raise ContractError('Concurrent task limit is six, including invalidated live attempts')
        n=self.node(identity)
        if self.header['request'].get('risk_mode') == 'enforced' and n.get('review_role') != 'risk':
            status = self.risk_status()
            if status['issues']:
                raise ContractError('Risk-plan gate: ' + '; '.join(i['code'] if isinstance(i,dict) else i for i in status['issues']))
        for cap in n.get('required_runtime_capabilities',[]):
            if cap not in support.get('capabilities',[]):
                self._event('environment_blocked',dict(node_id=identity,plan_sha256=hash_data(self.plan),missing=sorted(set(n.get('required_runtime_capabilities',[]))-set(support.get('capabilities',[]))),support=support))
                raise ContractError(f'Environment missing {cap}')
        requested=n['reasoning']
        if n['execution']=='agent' and requested not in support.get('reasoning_efforts',[]):
            raise ContractError('Requested reasoning is unsupported or unverified; revise plan explicitly')
        inputs=[]
        for i in n['inputs']:
            snapshot=self.snapshots()[i]
            if digest(within(self.path,snapshot['path']))!=snapshot['sha256']: raise ContractError('Input snapshot changed')
            inputs.append(snapshot)
        deps={d:self._artifacts_intact(self.states()[d]['attempt_id']) for d in n['depends_on']}
        if self.states()[identity]['attempt_id']:
            self._descendants(identity,'Upstream task retry replaces a previous result')
        aid=uuid.uuid4().hex
        instructions=[]
        for ref in [n['expert'],*n['skills'],n['runtime']]:
            data,path=self.registry.resolve(ref)
            instructions.append(dict(component=ref,path=str(path/data['entrypoint']),text=(path/data['entrypoint']).read_text()))
        brief=dict(attempt_id=aid,node_id=identity,node=n,plan_sha256=hash_data(self.plan),meta_sha256=hash_data(self.meta),
                   inputs=inputs,dependencies=deps,instructions=instructions,support=support,
                   request=self.header['request'],issued_at=now(),result_directory=str(self.path/'work'/aid),
                   report_budget=budget)
        if self.risk:
            brief['risk_sha256'] = hash_data(self.risk)
            brief['risk_record'] = self._latest('risk_registered')['object']
        (self.path/'work'/aid).mkdir()
        d=dict(attempt_id=aid,node_id=identity,object=self._store('attempts',brief))
        self._event('dispatched',d)
        return dict(brief,brief_sha256=hash_data(brief))

    @transaction
    def bind(self,binding):
        validate(self.registry.root,'binding',binding)
        a=self._current(binding['attempt_id'],{'running'})
        if self.binding(binding['attempt_id']): raise ContractError('Attempt already bound')
        if binding['instruction_sha256']!=hash_data(a): raise ContractError('Instruction hash differs from dispatch')
        if binding['reasoning']['requested']!=a['node']['reasoning']: raise ContractError('Reasoning request changed after dispatch')
        if binding['provider']=='codex-native':
            receipt=binding['host_receipt']
            if receipt['tool']!='multi_agent_v1.spawn_agent' or receipt['response'].get('agent_id')!=binding['agent_id']:
                raise ContractError('Native agent binding requires actual spawn response')
            request=receipt.get('request',{})
            if not isinstance(request,dict) or request.get('fork_context',False) is not False:
                raise ContractError('Native spawn requires fork_context=false')
            for event in self.events:
                if event['kind']=='agent_bound' and event['data']['attempt_id']!=binding['attempt_id']:
                    prior=self._object(event['data']['object'])
                    if prior['agent_id']==binding['agent_id']:
                        raise ContractError('Native actor cannot be reused across distinct attempts')
        if a['node']['execution']=='agent' and binding['provider']!='codex-native':
            raise ContractError('An agent task requires a native agent receipt')
        self._event('agent_bound',dict(attempt_id=binding['attempt_id'],object=self._store('bindings',binding)))
        return binding

    @transaction
    def submit(self,result):
        validate(self.registry.root,'result',result)
        a=self._current(result['attempt_id'],{'running'})
        self._check_pin()
        self._dependencies_current(a)
        b=self.binding(result['attempt_id'])
        if not b or b['agent_id']!=result['agent_id']: raise ContractError('Result author differs from bound executor')
        declared=a['node']; required=set(declared['required_checks']); checks={c['id']:c for c in result['checks']}
        if required-set(checks): raise ContractError('Result omits declared checks')
        if set(declared['outputs'])-{a['type'] for a in result['artifacts']}: raise ContractError('Result omits declared output types')
        names=[x['name'] for x in result['artifacts']]
        if len(names)!=len(set(names)): raise ContractError('Duplicate artifact names')
        frozen=[]
        for f in result['artifacts']:
            source=Path(f['path']).resolve()
            if not source.is_relative_to(self.path/'work'/result['attempt_id']):
                raise ContractError('Write results into the attempt work directory')
            actual_hash=digest(source)
            if f.get('sha256',actual_hash)!=actual_hash:
                raise ContractError('Submitted artifact hash differs from actual bytes')
            version=f.get('version',1)
            if isinstance(version,bool) or not isinstance(version,int) or version<1:
                raise ContractError('Artifact version must be a positive integer')
            rel=f"artifacts/{result['attempt_id']}/{f['name']}/{source.name}"
            dest=self.path/rel; dest.parent.mkdir(parents=True,exist_ok=True)
            existed=dest.exists()
            if existed:
                if digest(dest)!=digest(source):raise ContractError('Uncommitted artifact differs; use a fresh attempt')
            else:copy_atomic(source,dest)
            frozen_hash=digest(dest)
            if frozen_hash!=actual_hash:
                if not existed:dest.unlink()
                raise ContractError('Artifact changed during submission; frozen bytes differ from authorized hash')
            frozen.append(dict(f,path=rel,sha256=frozen_hash,version=version))
        saved=dict(result,artifacts=frozen)
        status='needs_revision' if not all(checks[k]['passed'] for k in required) else ('review_pending' if declared['review_required'] else 'verified')
        self._event('result_submitted',dict(node_id=a['node_id'],attempt_id=a['attempt_id'],status=status,object=self._store('results',saved)))
        return dict(status=status,result=saved)

    @transaction
    def fail(self,attempt_id,reason,kind='failed'):
        a=self._current(attempt_id,{'running','review_pending'})
        if kind not in {'failed','missing_data','needs_revision'}: raise ContractError('Unknown failure kind')
        self._event('attempt_failed',dict(node_id=a['node_id'],attempt_id=attempt_id,status=kind,reason=reason))
        self._descendants(a['node_id'],'Upstream attempt failed or needs revision')

    def _review_context(self,review):
        validate(self.registry.root,'review',review)
        target=self._current(review['attempt_id'],{'review_pending','verified','needs_revision'})
        reviewer=self._current(review['review_task_attempt'],{'review_pending','verified'})
        author=self.binding(review['attempt_id']); rb=self.binding(review['review_task_attempt'])
        if not author or not rb or rb['agent_id']!=review['reviewer_agent_id'] or rb['agent_id']==author['agent_id']:
            raise ContractError('Review must come from a separate actual bound executor')
        if reviewer['node'].get('review_role') not in {review['role'],'task'}:
            raise ContractError('Reviewer is not assigned this review role')
        self._dependencies_current(reviewer)
        self._artifacts_intact(review['review_task_attempt'])
        result=self._artifacts_intact(review['attempt_id'])
        executed_target=reviewer['dependencies'].get(target['node_id'])
        if not executed_target or executed_target['attempt_id']!=target['attempt_id'] or executed_target['artifacts']!=result['artifacts']:
            raise ContractError('Review target was not in the actual reviewer execution brief')
        if review['verdict']=='pass' and not all(c['passed'] for c in result['checks'] if c['id'] in target['node']['required_checks']):
            raise ContractError('Review cannot erase failed required checks')
        available={a['name']:a['sha256'] for a in result['artifacts']}
        if any(available.get(t['name'])!=t['sha256'] for t in review['targets']): raise ContractError('Review references stale artifact')
        if review['verdict']=='pass' and any(f['severity'] in {'major','critical'} for f in review['findings']):
            raise ContractError('Material finding cannot accompany pass')
        self._review_targets(review['targets'])
        if not review['scope'].strip() or any(not e.strip() for e in review['evidence']):
            raise ContractError('Review needs nonblank scope and evidence')
        if len(review['evidence'])!=len(set(review['evidence'])):
            raise ContractError('Duplicate review evidence')
        ids=[f['id'] for f in review['findings']]
        if len(ids)!=len(set(ids)):raise ContractError('Duplicate finding ids')
        return target

    @staticmethod
    def _review_targets(targets):
        names=[t['name'] for t in targets]
        if len(names)!=len(set(names)):raise ContractError('Duplicate review target names')
        return {t['name']:t['sha256'] for t in targets}

    def _finding_states(self):
        # Stable identity is always (original review id, original finding id).
        states={}
        for event in self.events:
            if event['kind'] in {'finding_closed','finding_reopened'}:
                d=event['data']
                states[d['review_id'],d['finding_id']]=event
        return states

    def _review_fresh_after(self,review,sequence):
        # Dispatch fixes the reviewer's task/context. A later result or review ID
        # cannot turn a task started before a finding transition into a new round.
        dispatched=next(e['seq'] for e in self.events if e['kind']=='dispatched'
                        and e['data']['attempt_id']==review['review_task_attempt'])
        if dispatched<=sequence:
            raise ContractError('Finding transition requires a fresh reviewer execution')

    def _review_continuity(self,review,closing=False):
        prior={r['id']:r for r in self.reviews() if r['id']!=review['id']}
        target=self.attempt(review['attempt_id'])
        available=self._review_targets(review['targets'])
        states=self._finding_states()

        def covered(item, original):
            actual=self._review_targets(item['targets'])
            expected=self._review_targets(original['targets'])
            if item['scope']!=original['scope']:
                raise ContractError('Continuity scope differs from original scope')
            if not set(expected)<=set(actual) or any(available.get(n)!=h for n,h in actual.items()):
                raise ContractError('Continuity must cover original artifacts with current reviewed hashes')

        def owner(item):
            old=prior.get(item['review_id'])
            if not old:raise ContractError('Unknown or self-referencing continuity review')
            if self.attempt(old['attempt_id'])['node_id']!=target['node_id'] or old['role']!=review['role']:
                raise ContractError('Continuity reference belongs to another task or review role')
            if self.binding(old['attempt_id'])['agent_id']==review['reviewer_agent_id']:
                raise ContractError('Original artifact author cannot resolve or reopen its review')
            return old

        seen=set()
        for kind in ('resolutions','reopenings'):
            for item in review.get(kind,[]):
                old=owner(item); key=(old['id'],item['finding_id'])
                if key in seen:raise ContractError('Duplicate or conflicting finding reference')
                seen.add(key)
                if sum(f['id']==item['finding_id'] for f in old['findings'])!=1:
                    raise ContractError('Unknown or ambiguous original finding reference')
                covered(item,old)
                last=states.get(key)
                closed=last and last['kind']=='finding_closed'
                already_closed_here=(closing and closed and
                                     last['data']['replacement_review_id']==review['id'])
                if last and not already_closed_here:
                    self._review_fresh_after(review,last['seq'])
                if kind=='resolutions':
                    if review['verdict']!='pass' or (closed and not (closing and
                            last['data']['replacement_review_id']==review['id'])):
                        raise ContractError('Resolution requires an open finding and passing review')
                elif not closed or item['replacement_review_id']!=last['data']['replacement_review_id']:
                    raise ContractError('Reopening must reference the current closure review')
                elif review['verdict']=='pass':
                    raise ContractError('Reopening requires a non-passing review')

        decisions=review.get('accepted_decisions',[])
        ids=[d['id'] for d in decisions]
        if len(ids)!=len(set(ids)):raise ContractError('Duplicate accepted decision ids')
        for decision in decisions:
            if review['verdict']!='pass':raise ContractError('Accepted decisions require a passing review')
            covered(decision,dict(scope=review['scope'],targets=decision['targets']))
        seen=set()
        for item in review.get('accepted_decision_refs',[]):
            old=owner(item); key=(old['id'],item['decision_id'])
            if key in seen:raise ContractError('Duplicate accepted decision reference')
            seen.add(key)
            decision=next((d for d in old.get('accepted_decisions',[]) if d['id']==item['decision_id']),None)
            if not decision or old['verdict']!='pass':raise ContractError('Unknown accepted decision reference')
            covered(item,decision)
            if item['disposition']=='challenged' and not item.get('reason'):
                raise ContractError('Challenging an accepted decision needs a justified reason')

    @transaction
    def review(self,review):
        target=self._review_context(review)
        reviewer=self.attempt(review['review_task_attempt'])
        for prior in self.reviews():
            if all(prior[key]==review[key] for key in ('review_task_attempt','attempt_id','role')):
                raise ContractError('Reviewer attempt already recorded a verdict for this target and role')
        self._review_continuity(review)
        if any(e['kind']=='review_recorded' and self._object(e['data']['object'])['id']==review['id'] for e in self.events):
            raise ContractError('Review id already exists')
        self._event('review_recorded',dict(object=self._store('reviews',review)))
        for item in review.get('reopenings',[]):
            self._event('finding_reopened',dict(item,reopening_review_id=review['id'],reviewer_agent_id=review['reviewer_agent_id']))
        status='verified' if review['verdict']=='pass' else 'needs_revision'
        self._event('task_reviewed',dict(node_id=target['node_id'],attempt_id=target['attempt_id'],status=status,review_id=review['id']))
        if status=='needs_revision':
            self._descendants(target['node_id'],'Upstream review requires revision',exclude=[reviewer['node_id']])
        return status

    def reviews(self):
        return [self._object(e['data']['object']) for e in self.events if e['kind']=='review_recorded']

    @transaction
    def close_finding(self,review_id,finding_id,reviewer_agent_id,replacement_review_id,explanation):
        reviews={r['id']:r for r in self.reviews()}
        old=reviews.get(review_id); new=reviews.get(replacement_review_id)
        if not old or not new:raise ContractError('Unknown closure review reference')
        if new['reviewer_agent_id']!=reviewer_agent_id:
            raise ContractError('Closure must be confirmed by the replacement bound reviewer')
        if not isinstance(explanation,str) or not explanation.strip():
            raise ContractError('Closure needs an explanation')
        order=list(reviews)
        if order.index(replacement_review_id)<=order.index(review_id):
            raise ContractError('Closure review must postdate and address the finding')
        self._review_context(new)
        self._current(new['attempt_id'],{'verified'})
        latest=next(r for r in reversed(list(reviews.values()))
                    if r['attempt_id']==new['attempt_id'] and r['role']==new['role'])
        if latest['id']!=new['id']:raise ContractError('Closure requires the latest current review')
        self._review_continuity(new,closing=True)
        resolution=next((r for r in new.get('resolutions',[])
                         if r['review_id']==review_id and r['finding_id']==finding_id),None)
        if not resolution:raise ContractError('Closure requires explicit per-finding resolution evidence')
        # Recheck execution freshness at closure, including already recorded passes.
        last=self._finding_states().get((review_id,finding_id))
        recorded=next(e['seq'] for e in self.events if e['kind']=='review_recorded'
                      and self._object(e['data']['object'])['id']==replacement_review_id)
        if last and last['seq']>=recorded:
            raise ContractError('Closure review must postdate the latest finding transition')
        self._event('finding_closed',dict(review_id=review_id,finding_id=finding_id,replacement_review_id=replacement_review_id,
                                         reviewer_agent_id=reviewer_agent_id,explanation=explanation,resolution=resolution))

    @transaction
    def environment_wait(self,capabilities,reason):
        last_start=next((e for e in reversed(self.events) if e['kind']=='environment_wait_started'),None)
        last_end=next((e for e in reversed(self.events) if e['kind']=='environment_wait_ended'),None)
        if last_start and (not last_end or last_start['seq']>last_end['seq']): raise ContractError('Environment wait already active')
        last_recovery=max((e['seq'] for e in self.events if e['kind']=='environment_wait_ended'),default=0)
        blocked={e['data']['node_id']:set(e['data']['missing']) for e in self.events if e['kind']=='environment_blocked' and e['seq']>last_recovery and e['data']['plan_sha256']==hash_data(self.plan)} if self.plan else {}
        runnable=[n for n in self.ready() if not blocked.get(n,set()).intersection(capabilities)]
        if self.outstanding_attempts() or runnable:
            raise ContractError('Exclude environment wait only when ALL report work is waiting')
        if not capabilities or not reason: raise ContractError('Need missing environment capabilities and cause')
        if any(c.startswith(('source:','company:','research:')) for c in capabilities):
            raise ContractError('Company research cannot be environment setup')
        self._event('environment_wait_started',dict(capabilities=capabilities,reason=reason))

    @transaction
    def environment_ready(self,checks):
        start=self._latest('environment_wait_started')
        starts=[e['seq'] for e in self.events if e['kind']=='environment_wait_started']
        ends=[e['seq'] for e in self.events if e['kind']=='environment_wait_ended']
        if not starts or max(starts)<=max(ends,default=0):raise ContractError('No active environment wait')
        if not start or not all(checks.get(c) is True for c in start['capabilities']):
            raise ContractError('Need successful smoke tests for missing capabilities')
        self._event('environment_wait_ended',dict(checks=checks))

    def timing(self):
        if not self.events:return {}
        end=next((e for e in reversed(self.events) if e['kind']=='run_finished'),None)
        end=end or dict(utc=now(),monotonic_ns=time.monotonic_ns(),boot_id=boot_id())
        anomalies=[];uncertain=False
        def delta(a,b):
            nonlocal uncertain
            monotonic=(b['monotonic_ns']-a['monotonic_ns'])/1e9
            wall=(timestamp(b['utc'])-timestamp(a['utc'])).total_seconds()
            if a['boot_id'] and a['boot_id']==b['boot_id']:
                if monotonic<0:uncertain=True;anomalies.append('Monotonic clock moved backwards')
                return max(0,monotonic)
            if not a['boot_id'] and not b['boot_id'] and monotonic>=0 and abs(wall-monotonic)<2:
                anomalies.append('Kernel boot identity unavailable; monotonic continuity cross-checked against UTC')
                return monotonic
            anomalies.append('UTC fallback after boot/clock identity changed')
            uncertain=True
            return max(0,wall)
        ledger_total=delta(self.events[0],end)
        intake=(timestamp(self.events[0]['utc'])-timestamp(self.header['request']['requested_at'])).total_seconds()
        if intake<0:
            uncertain=True;anomalies.append('Request timestamp is later than the ledger start')
        intake=max(0,intake)
        total=ledger_total+intake; excluded=0; waiting=None; active={}; durations={}
        for e in self.events:
            if e['kind']=='environment_wait_started':waiting=e
            elif e['kind']=='environment_wait_ended' and waiting:
                excluded+=delta(waiting,e);waiting=None
            elif e['kind']=='dispatched':active[e['data']['attempt_id']]=e
            elif e['kind'] in {'result_submitted','attempt_failed'}:
                aid=e['data']['attempt_id']
                if aid in active:durations[aid]=delta(active.pop(aid),e)
            elif e['kind']=='worker_released':
                aid=e['data']['attempt_id']
                if aid in active:durations[aid]=delta(active.pop(aid),e)
        if waiting:excluded+=delta(waiting,end)
        durations.update({aid:delta(a,end) for aid,a in active.items()})
        human_response=sum(value for aid,value in durations.items() if self.attempt(aid)['node']['execution']=='human-gate')
        usage=[self._object(e['data']['object']).get('usage') for e in self.events if e['kind']=='result_submitted']
        return dict(overall_seconds=total,environment_wait_seconds=excluded,report_seconds=max(0,total-excluded),
                    preledger_seconds=intake,ledger_seconds=ledger_total,
                    intake_basis='request.requested_at (host attestation; not inferred from task durations)',
                    task_active_seconds=durations,task_active_sum_seconds=sum(durations.values()),
                    human_active_seconds=None,human_response_seconds=human_response,actual_cost=None,observed_usage=usage,
                    anomalies=sorted(set(anomalies)),deadline_measurement_uncertain=uncertain)

    def budget(self):
        """Reserve delivery time without relaxing quality or hiding intake work."""
        request=self.header['request'];config=request.get('report_benchmark',{})
        enforced=request['mode']=='report' or config.get('enabled',False)
        profile=self.registry.evaluation(self.meta['evaluation']) if self.meta else {}
        deadline=min(600,profile.get('report_deadline_seconds',600))
        target=min(config.get('target_seconds',300),deadline)
        reserve=min(config.get('delivery_reserve_seconds',15),deadline)
        timing=self.timing();elapsed=timing['report_seconds']
        return dict(enforced=enforced,classification='report_execution' if enforced else 'package_development',
                    target_seconds=target,deadline_seconds=deadline,delivery_reserve_seconds=reserve,
                    elapsed_seconds=elapsed,remaining_seconds=max(0,deadline-elapsed),
                    work_remaining_seconds=max(0,deadline-reserve-elapsed),
                    target_met=elapsed<=target,deadline_exceeded=elapsed>deadline,
                    stop_work=enforced and (elapsed>=deadline-reserve or timing['deadline_measurement_uncertain']),
                    measurement_uncertain=timing['deadline_measurement_uncertain'],
                    task_elapsed_is_not_model_compute=True)

    @transaction
    def deadline_checkpoint(self):
        """Seal expired work; the host must cancel listed native agents and deliver.

        This engine cannot cancel a native call. Sealing is not delivery proof.
        Late results are rejected by the ordinary sealed-run transaction guard.
        """
        budget=self.budget()
        if not budget['enforced'] or not budget['stop_work']:
            return dict(action='continue',budget=budget)
        cancel=[]
        for attempt in sorted(self.outstanding_attempts()):
            binding=self.binding(attempt)
            cancel.append(dict(attempt_id=attempt,agent_id=binding['agent_id'] if binding else None))
        result=self.readiness()
        self._event('report_budget_exhausted',dict(budget=budget,cancel_agents=cancel))
        self._event('run_finished',dict(status='complete' if result['complete'] else 'incomplete',issues=result['issues'],
                                       reason='Report work cutoff reached; preserve time for delivery'))
        return dict(action='deliver',budget=budget,readiness=result,cancel_agents=cancel,
                    delivery_confirmed=False,worker_cancellation_confirmed=False)

    def readiness(self):
        issues=[]
        self._check_pin()
        if not self.meta or not self.plan: return dict(complete=False,issues=['Missing meta decision or plan'],timing=self.timing())
        checked=plan_check(self.registry,self.meta,self.plan)
        if self.header['request'].get('risk_mode') == 'enforced':
            risk = self.risk_status()
            issues.extend('Risk gate: ' + (i['code'] if isinstance(i,dict) else i) for i in risk['issues'])
            for claim_id, procedures in risk['required_procedures'].items():
                claim = next(c for c in self.risk['claims'] if c['id'] == claim_id)
                current_target = self.states()[claim['node_id']]['attempt_id']
                performed = set()
                for event in self.events:
                    if event['kind'] != 'risk_procedure_recorded':
                        continue
                    record = self._object(event['data']['object'])
                    examiner = self.attempt(record['task_attempt'])
                    state = self.states().get(examiner['node_id'], {})
                    if (record['risk_sha256'] == hash_data(self.risk) and record['claim_id'] == claim_id
                            and record['target_attempt'] == current_target
                            and state.get('attempt_id') == record['task_attempt'] and state.get('status') == 'verified'):
                        self._artifacts_intact(record['task_attempt'])
                        self._artifacts_intact(current_target)
                        performed.add(record['procedure'])
                issues.extend('Missing risk procedure: ' + claim_id + '/' + p for p in set(procedures) - performed)
        issues.extend('Unresolved rule: '+r['rule'] for r in checked['pending_rules'])
        if self.meta['mode']!='report' or self.header['request']['mode']!='report':issues.append('Development/planning/experiment run is not a released report')
        states=self.states()
        for node,state in states.items():
            if state['status']!='verified':issues.append(f'{node}: {state["status"]}')
            elif state['attempt_id']:self._artifacts_intact(state['attempt_id'])
        profile=self.registry.evaluation(self.meta['evaluation'])
        current={s['attempt_id'] for s in states.values() if s['status']=='verified'}
        latest_reviews={(r['attempt_id'],r['role']):r for r in self.reviews()}
        valid_reviews=[r for r in latest_reviews.values() if r['attempt_id'] in current and r['review_task_attempt'] in current and r['verdict']=='pass']
        for role in profile['required_review_roles']:
            if role not in {r['role'] for r in valid_reviews}:issues.append('Missing current independent '+role+' review')
            covered=set()
            for r in valid_reviews:
                if r['role']!=role:continue
                target_names={t['name'] for t in r['targets']}
                covered.update(a['type'] for a in self.result(r['attempt_id'])['artifacts'] if a['name'] in target_names)
            for artifact_type in profile.get('coverage',{}).get(role,[]):
                if artifact_type not in covered:issues.append(f'Missing {role} review coverage of {artifact_type}')
                for node,state in states.items():
                    if self.node(node).get('review_role') or state['attempt_id'] not in current:continue
                    for artifact in self.result(state['attempt_id'])['artifacts']:
                        if artifact['type']!=artifact_type:continue
                        if not any(r['role']==role and r['attempt_id']==state['attempt_id'] and
                                   {'name':artifact['name'],'sha256':artifact['sha256']} in r['targets'] for r in valid_reviews):
                            issues.append(f'Missing {role} review of exact artifact {node}/{artifact["name"]}')
        if profile.get('calibration_status') not in {None,'calibrated'}:
            issues.append('Evaluation anchors and grader configuration not yet calibrated')
        closed={key for key,event in self._finding_states().items() if event['kind']=='finding_closed'}
        for r in self.reviews():
            for f in r['findings']:
                if f['severity'] in {'major','critical'} and (r['id'],f['id']) not in closed:issues.append('Unclosed material finding: '+f['id'])
        latest_score=self._latest('quality_recorded')
        if not latest_score or latest_score['plan_sha256']!=hash_data(self.plan):issues.append('Missing current independent quality evaluation')
        else:
            scores=latest_score['scores']
            if set(scores)!=set(profile['axes']) or any(v<profile['minimum_axis'] for v in scores.values()) or sum(scores.values())<profile['minimum_total']:
                issues.append('Professional quality threshold not met')
            if latest_score['artifact_set_sha256']!=self.artifact_set_hash():issues.append('Quality evaluation targets changed artifacts')
        checks={c['id'] for s in states.values() if s['attempt_id'] in current for c in self.result(s['attempt_id'])['checks'] if c['passed']}
        for needed in profile['required_checks']:
            if needed not in checks:issues.append('Missing completed check: '+needed)
        output_types={a['type'] for s in states.values() if s['attempt_id'] in current for a in self.result(s['attempt_id'])['artifacts']}
        for needed in profile['required_artifacts']:
            if needed not in output_types:issues.append('Missing deliverable: '+needed)
        timing=self.timing()
        if timing['report_seconds']>profile['report_deadline_seconds']:issues.append('600 second report deadline exceeded')
        if timing.get('deadline_measurement_uncertain'):issues.append('Clock discontinuity prevents deadline certification')
        return dict(complete=not issues,issues=issues,timing=self.timing())

    def artifact_set_hash(self):
        return hash_data({n:self.result(s['attempt_id'])['artifacts'] for n,s in self.states().items() if s['attempt_id'] and self.result(s['attempt_id'])})

    @transaction
    def quality(self,review_task_attempt,scores,evidence):
        a=self._current(review_task_attempt,{'verified'})
        if a['node'].get('review_role')!='judgment':raise ContractError('Quality must be assigned to independent judgment reviewer')
        profile=self.registry.evaluation(self.meta['evaluation'])
        if set(scores)!=set(profile['axes']) or any(not isinstance(v,int) or not 0<=v<=4 for v in scores.values()) or not evidence:
            raise ContractError('Invalid quality score or absent evidence')
        binding=self.binding(review_task_attempt)
        if any(self.binding(s['attempt_id'])['agent_id']==binding['agent_id'] for n,s in self.states().items()
               if s['attempt_id'] and not self.node(n).get('review_role')):
            raise ContractError('Quality reviewer authored report work')
        self._event('quality_recorded',dict(review_task_attempt=review_task_attempt,scores=scores,evidence=evidence,
                    evaluation=self.meta['evaluation'],plan_sha256=hash_data(self.plan),artifact_set_sha256=self.artifact_set_hash()))

    @transaction
    def finish(self):
        result=self.readiness()
        self._event('run_finished',dict(status='complete' if result['complete'] else 'incomplete',issues=result['issues']))
        return result
