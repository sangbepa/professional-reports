import copy
from datetime import datetime, timedelta, timezone
import json
import unittest

from fixture import RunCase, Run, RELEASE, ContractError, hash_data
from pr.native import submit_template


class EngineContracts(RunCase):
    def test_reload_restores_review_pending_and_frozen_result(self):
        brief = self.execute()
        restored = Run(self.run.path)
        self.assertEqual(restored.states(), self.run.states())
        self.assertEqual(restored.result(brief['attempt_id']), self.run.result(brief['attempt_id']))
        self.assertEqual(restored.states()['writer']['status'], 'review_pending')

    def test_ledger_content_tamper_is_rejected(self):
        path = self.run.path / 'events.jsonl'
        rows = path.read_text().splitlines()
        event = json.loads(rows[0])
        event['data']['request_id'] = 'tampered'
        rows[0] = json.dumps(event)
        path.write_text('\n'.join(rows) + '\n')
        with self.assertRaisesRegex(ContractError, 'ledger integrity'):
            Run(self.run.path)

    def test_missing_middle_event_is_rejected(self):
        path = self.run.path / 'events.jsonl'
        rows = path.read_text().splitlines()
        path.write_text('\n'.join(rows[:1] + rows[2:]) + '\n')
        with self.assertRaisesRegex(ContractError, 'ledger integrity'):
            Run(self.run.path)

    def test_changed_input_invalidates_writer_and_reviewer(self):
        target = self.execute()
        reviewer = self.execute('reviewer', 'synthetic-reviewer')
        self.run.review(self.review(target, reviewer))
        self.source.write_text('Synthetic evidence v2\n')
        self.run.snapshot('input', self.source, ['domain_analysis'])
        self.assertEqual({s['status'] for s in self.run.states().values()}, {'invalidated'})
        with self.assertRaisesRegex(ContractError, 'invalidated or replaced'):
            self.run.review(self.review(target, reviewer, identity='stale'))
        self.assertEqual(len(self.run.reviews()), 1)

    def test_snapshot_change_rejects_late_submission(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        template = self.template(brief)
        self.source.write_text('Changed synthetic bytes\n')
        self.run.snapshot('input', self.source, ['domain_analysis'])
        with self.assertRaisesRegex(ContractError, 'invalidated or replaced'):
            submit_template(self.run, brief['attempt_id'], template)
        self.assertIn(brief['attempt_id'], self.run.outstanding_attempts())

    def test_failed_attempt_remains_outstanding_until_terminal_receipt(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        self.run.fail(brief['attempt_id'], 'Synthetic timeout')
        self.assertIn(brief['attempt_id'], self.run.outstanding_attempts())
        bad = dict(tool='multi_agent_v1.wait_agent', agent_id='synthetic-writer',
                   response={'timed_out': True})
        with self.assertRaisesRegex(ContractError, 'does not release'):
            self.run.release_worker(brief['attempt_id'], bad)
        self.assertIn(brief['attempt_id'], self.run.outstanding_attempts())
        self.run.release_worker(brief['attempt_id'], dict(bad, response={'status': 'completed'}))
        self.assertNotIn(brief['attempt_id'], self.run.outstanding_attempts())

    def test_wrong_release_actor_is_rejected(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        with self.assertRaisesRegex(ContractError, 'another agent'):
            self.run.release_worker(brief['attempt_id'], dict(
                tool='multi_agent_v1.close_agent', agent_id='different',
                response={'status': 'shutdown'}))

    def test_stale_review_hash_is_rejected_without_ledger_write(self):
        target = self.execute()
        reviewer = self.execute('reviewer', 'synthetic-reviewer')
        review = self.review(target, reviewer)
        review['targets'][0]['sha256'] = '0' * 64
        before = (self.run.path / 'events.jsonl').read_bytes()
        with self.assertRaisesRegex(ContractError, 'stale artifact'):
            self.run.review(review)
        self.assertEqual(before, (self.run.path / 'events.jsonl').read_bytes())

    def test_author_cannot_approve_own_result(self):
        target = self.execute()
        reviewer = self.execute('reviewer', 'synthetic-reviewer')
        with self.assertRaisesRegex(ContractError, 'separate actual bound'):
            self.run.review(self.review(target, reviewer, reviewer_agent_id='synthetic-writer'))

    def test_reviewer_must_submit_before_review(self):
        target = self.execute()
        reviewer = self.dispatch('reviewer')
        self.bind(reviewer, 'synthetic-reviewer')
        with self.assertRaisesRegex(ContractError, 'Invalid task state'):
            self.run.review(self.review(target, reviewer))

    def test_material_finding_cannot_accompany_pass(self):
        target = self.execute()
        reviewer = self.execute('reviewer', 'synthetic-reviewer')
        with self.assertRaisesRegex(ContractError, 'Material finding'):
            self.run.review(self.review(target, reviewer, findings=[dict(
                id='major-1', severity='major', description='Synthetic unresolved issue')]))

    def test_general_pass_does_not_close_material_finding(self):
        target = self.execute()
        first = self.execute('reviewer', 'synthetic-reviewer-1')
        self.run.review(self.review(target, first, identity='review-1', verdict='revise',
                                   findings=[dict(id='major-1', severity='major',
                                                  description='Synthetic unresolved issue')]))
        second = self.fresh_reviewer('synthetic-reviewer-2')
        self.run.review(self.review(target, second, identity='review-2'))
        with self.assertRaisesRegex(ContractError, 'per-finding resolution'):
            self.run.close_finding('review-1', 'major-1', 'synthetic-reviewer-2',
                                   'review-2', 'General pass is not sufficient')
        self.assertNotIn(('review-1', 'major-1'), self.run._finding_states())
        self.assertFalse(self.run.readiness()['complete'])

    def test_explicit_resolution_and_fresh_reopening_keep_original_identity(self):
        target = self.execute()
        first = self.execute('reviewer', 'synthetic-reviewer-1')
        old = self.review(target, first, identity='review-1', verdict='revise',
                          findings=[dict(id='major-1', severity='major',
                                         description='Synthetic finding')])
        self.run.review(old)
        second = self.fresh_reviewer('synthetic-reviewer-2')
        resolution = dict(review_id='review-1', finding_id='major-1',
                          scope=old['scope'], targets=copy.deepcopy(old['targets']),
                          evidence=['Synthetic resolution evidence'],
                          explanation='Fresh synthetic reviewer rechecked exact bytes')
        self.run.review(self.review(target, second, identity='review-2', resolutions=[resolution]))
        self.run.close_finding('review-1', 'major-1', 'synthetic-reviewer-2',
                               'review-2', 'Explicit synthetic resolution')
        self.assertEqual(self.run._finding_states()['review-1', 'major-1']['kind'], 'finding_closed')
        third = self.fresh_reviewer('synthetic-reviewer-3')
        reopening = dict(resolution, replacement_review_id='review-2', reason='counterevidence',
                         evidence=['Synthetic counterevidence'], explanation='New counterexample')
        self.run.review(self.review(target, third, identity='review-3', verdict='revise',
                                    reopenings=[reopening]))
        self.assertEqual(self.run._finding_states()['review-1', 'major-1']['kind'], 'finding_reopened')

    def test_duplicate_review_verdict_is_rejected(self):
        target = self.execute()
        reviewer = self.execute('reviewer', 'synthetic-reviewer')
        self.run.review(self.review(target, reviewer))
        with self.assertRaisesRegex(ContractError, 'already recorded a verdict'):
            self.run.review(self.review(target, reviewer, identity='duplicate'))

    def test_frozen_artifact_tamper_is_rejected(self):
        target = self.execute()
        saved = self.run.result(target['attempt_id'])
        (self.run.path / saved['artifacts'][0]['path']).write_text('Tampered')
        with self.assertRaisesRegex(ContractError, 'tampered after submission'):
            self.dispatch('reviewer')

    def test_required_skill_checks_cannot_be_removed(self):
        plan = copy.deepcopy(self.run.plan)
        plan.update(previous=hash_data(self.run.plan), revision=2)
        plan['nodes'][0]['revision'] = 2
        plan['nodes'][0]['required_checks'] = ['irrelevant']
        with self.assertRaisesRegex(ContractError, 'weakens skill acceptance'):
            self.run.register_plan(plan)

    def test_six_invalidated_live_attempts_block_seventh(self):
        for index in range(6):
            self.dispatch()
            self.source.write_text('Synthetic change ' + str(index))
            self.run.snapshot('input', self.source, ['domain_analysis'])
        self.assertEqual(len(self.run.outstanding_attempts()), 6)
        with self.assertRaisesRegex(ContractError, 'including invalidated live attempts'):
            self.dispatch()


class DeadlineContracts(RunCase):
    def request(self):
        request = super().request()
        request['report_benchmark'] = {'enabled': True}
        return request

    def test_budget_is_600_with_585_work_cutoff_and_15_delivery(self):
        budget = self.run.budget()
        self.assertTrue(budget['enforced'])
        self.assertEqual(budget['deadline_seconds'], 600)
        self.assertEqual(budget['delivery_reserve_seconds'], 15)
        self.assertAlmostEqual(budget['work_remaining_seconds'] + budget['elapsed_seconds'], 585)

    def test_expired_run_seals_incomplete_and_rejects_late_submission(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        template = self.template(brief)
        # A clock observation is advanced; immutable intake/ledger bytes are not rewritten.
        from unittest.mock import patch
        actual = self.run.budget()
        expired = dict(actual, elapsed_seconds=586, stop_work=True,
                       work_remaining_seconds=0, remaining_seconds=14)
        with patch.object(Run, 'budget', return_value=expired):
            outcome = self.run.deadline_checkpoint()
        self.assertEqual(outcome['action'], 'deliver')
        self.assertFalse(outcome['delivery_confirmed'])
        self.assertFalse(outcome['worker_cancellation_confirmed'])
        self.assertEqual(outcome['cancel_agents'][0]['agent_id'], 'synthetic-writer')
        self.assertEqual(self.run._latest('run_finished')['status'], 'incomplete')
        with self.assertRaisesRegex(ContractError, 'sealed'):
            submit_template(self.run, brief['attempt_id'], template)

    def test_original_preledger_intake_counts_against_budget(self):
        request = self.request()
        request['requested_at'] = (datetime.now(timezone.utc) - timedelta(seconds=590)).isoformat()
        expired = Run.create(self.base / 'expired', RELEASE, request)
        self.assertGreaterEqual(expired.timing()['preledger_seconds'], 590)
        self.assertTrue(expired.budget()['stop_work'])
        outcome = expired.deadline_checkpoint()
        self.assertEqual(outcome['action'], 'deliver')
        self.assertEqual(expired._latest('run_finished')['status'], 'incomplete')


if __name__ == '__main__':
    unittest.main(verbosity=2)
