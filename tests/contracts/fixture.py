"""Synthetic local fixtures. No model calls, authentic host receipts, or quality claims.

These suites must run with cwd set to a verified, installed release. They use its
real schemas, components and protected profile unchanged. The deliberately
incomplete development plan is not a report plan or evaluator calibration.
"""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

RELEASE = Path.cwd().resolve()
sys.path.insert(0, str(RELEASE))
from pr.engine import Run
from pr.native import bind_spawn, submit_template
from pr.package import verify
from pr.util import ContractError, hash_data, now, read_json


class RunCase(unittest.TestCase):
    def setUp(self):
        verify(RELEASE)
        self.temp = tempfile.TemporaryDirectory(prefix='pr-synthetic-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.run = Run.create(self.base / 'run', RELEASE, self.request())
        reg = self.run.registry
        meta = dict(id='synthetic-meta', revision=1, previous=None,
                    request_id='synthetic-contract', action='candidate',
                    mode='development', selected=[], alternatives=[],
                    rationale=['Synthetic mechanical contract test only'],
                    gaps=['No professional report or native inference attempted'],
                    evaluation=reg.evaluation_ref('valuation-v1'),
                    case_ids=[], actor='synthetic-controller')
        self.run.register_meta(meta)
        skill, folder = reg.resolve(reg.reference('report-argument'))
        contract = read_json(folder / 'contract.json')
        checks = [x['id'] for x in contract['acceptance']]
        node = dict(id='writer', revision=1, goal='Synthetic text packet',
                    question='Does the contract enforce its frozen inputs?',
                    basis=[dict(component=reg.reference('codex-native'),
                                clause='Native Codex runtime',
                                facts=['Synthetic text-only development task'],
                                reason='Exercise the installed native contract')],
                    expert=reg.reference('report-writer'),
                    skills=[reg.reference(skill['id'])],
                    runtime=reg.reference('codex-native'), capabilities=[],
                    execution='agent', reasoning='high', inputs=['input'],
                    consumes=contract['consumes'], outputs=contract['outputs'],
                    required_checks=checks, depends_on=[],
                    review_required=True, review_role=None)
        reviewer = dict(copy.deepcopy(node), id='reviewer', inputs=[],
                        depends_on=['writer'], review_required=False,
                        review_role='document')
        plan = dict(id='synthetic-plan', revision=1, previous=None,
                    meta_hash=hash_data(meta), actor='synthetic-controller',
                    reason='Exercise contracts without full-report acceptance',
                    facts={}, nodes=[node, reviewer])
        self.run.register_plan(plan)
        self.source = self.base / 'input.txt'
        self.source.write_text('Synthetic evidence v1\n', encoding='utf-8')
        self.run.snapshot('input', self.source, ['domain_analysis'])

    def request(self):
        return dict(id='synthetic-contract', text='Synthetic regression fixture',
                    audience='Developers', decision='Contract behavior only',
                    scope='Synthetic text artifact', information_cutoff=now(),
                    language='en', requested_at=now(), mode='development')

    def dispatch(self, node='writer'):
        return self.run.dispatch(node, {'capabilities': [], 'reasoning_efforts': ['high']})

    def receipt(self, actor, prompt='Synthetic prompt'):
        return dict(tool='multi_agent_v1.spawn_agent', captured_at=now(),
                    request=dict(message=prompt, fork_context=False,
                                 reasoning_effort='high'),
                    response=dict(agent_id=actor, nickname=None),
                    synthetic_fixture=True)

    def bind(self, brief, actor):
        binding = bind_spawn(self.run, brief['attempt_id'], self.receipt(actor),
                             'Synthetic prompt', requested_effort='high')
        self.run = Run(self.run.path)
        return binding

    def template(self, brief, *, passed=True):
        work = Path(brief['result_directory'])
        (work / 'packet.txt').write_text('Synthetic text result\n', encoding='utf-8')
        return dict(artifacts=[dict(name='artifact-' + str(i), type=kind,
                                   path='packet.txt')
                               for i, kind in enumerate(brief['node']['outputs'])],
                    checks=[dict(id=check, passed=passed,
                                 evidence='Synthetic contract fixture, not semantic review')
                            for check in brief['node']['required_checks']],
                    summary='Synthetic fixture only', usage=None)

    def execute(self, node='writer', actor='synthetic-writer'):
        brief = self.dispatch(node)
        self.bind(brief, actor)
        submit_template(self.run, brief['attempt_id'], self.template(brief))
        self.run = Run(self.run.path)
        return brief

    def review(self, target, reviewer, identity='synthetic-review', **changes):
        result = self.run.result(target['attempt_id'])
        data = dict(id=identity, attempt_id=target['attempt_id'],
                    review_task_attempt=reviewer['attempt_id'],
                    reviewer_agent_id=self.run.binding(reviewer['attempt_id'])['agent_id'],
                    role='document',
                    targets=[dict(name=a['name'], sha256=a['sha256'])
                             for a in result['artifacts']],
                    verdict='pass', scope='Synthetic text packet',
                    evidence=['Synthetic artifact byte comparison'], findings=[])
        return dict(data, **changes)

    def fresh_reviewer(self, actor):
        plan = copy.deepcopy(self.run.plan)
        plan['previous'] = hash_data(self.run.plan)
        plan['revision'] += 1
        plan['reason'] = 'Fresh independent synthetic review round'
        plan['nodes'][1]['revision'] += 1
        plan['nodes'][1]['goal'] = 'Synthetic reviewer round ' + str(plan['revision'])
        self.run.register_plan(plan)
        return self.execute('reviewer', actor)
