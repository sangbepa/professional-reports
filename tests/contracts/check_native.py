import copy
from pathlib import Path
import unittest

from fixture import RunCase, ContractError
from pr.native import prepare_binding, prepare_submission, prepare_review, submit_template


class NativeContracts(RunCase):
    def test_binding_preserves_exact_prompt_receipt_and_unknown_settings(self):
        brief = self.dispatch()
        prompt = 'Synthetic exact prompt\r\n'
        receipt = self.receipt('synthetic-writer', prompt)
        original = copy.deepcopy(receipt)
        before = (self.run.path / 'events.jsonl').read_bytes()
        prepared = prepare_binding(self.run, brief['attempt_id'], receipt, prompt,
                                   requested_effort='high')
        self.assertEqual(receipt, original)
        self.assertEqual(prepared['delivered_prompt'], prompt)
        self.assertEqual(prepared['instruction_sha256'], brief['brief_sha256'])
        self.assertIsNone(prepared['model']['observed'])
        self.assertIsNone(prepared['reasoning']['resolved'])
        self.assertEqual(before, (self.run.path / 'events.jsonl').read_bytes())

    def test_spawn_error_timeout_and_missing_actor_are_rejected(self):
        brief = self.dispatch()
        for response in ({'error': 'synthetic'}, {'timed_out': True}, {},
                         {'agent_id': '${BOUND_AGENT_ID}'}, {'agent_id': 'a', 'success': False}):
            with self.subTest(response=response), self.assertRaises(ContractError):
                receipt = dict(self.receipt('synthetic-writer'), response=response)
                prepare_binding(self.run, brief['attempt_id'], receipt, 'Synthetic prompt')
        self.assertIsNone(self.run.binding(brief['attempt_id']))

    def test_unsupported_host_transport_is_rejected_without_normalizing_it(self):
        brief = self.dispatch()
        receipt = dict(self.receipt('synthetic-writer'), tool='collaboration.spawn_agent')
        with self.assertRaisesRegex(ContractError, 'Unsupported native spawn receipt'):
            prepare_binding(self.run, brief['attempt_id'], receipt, 'Synthetic prompt')

    def test_prompt_effort_and_context_mismatch_are_rejected(self):
        brief = self.dispatch()
        for update in ({'message': 'different'}, {'fork_context': True},
                       {'reasoning_effort': 'low'}, {'model': 'another-model'}):
            with self.subTest(update=update):
                receipt = self.receipt('synthetic-writer')
                receipt['request'].update(update)
                with self.assertRaises(ContractError):
                    prepare_binding(self.run, brief['attempt_id'], receipt, 'Synthetic prompt')

    def test_completed_actor_cannot_be_reused(self):
        self.execute()
        brief = self.dispatch('reviewer')
        with self.assertRaisesRegex(ContractError, 'cannot be reused'):
            self.bind(brief, 'synthetic-writer')

    def test_missing_checks_and_output_types_cannot_be_submitted(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        good = self.template(brief)
        for bad in (dict(good, checks=good['checks'][:1]),
                    dict(good, artifacts=good['artifacts'][:1])):
            with self.subTest(bad=bad), self.assertRaisesRegex(ContractError, 'omits declared'):
                submit_template(self.run, brief['attempt_id'], bad)
        self.assertIsNone(self.run.result(brief['attempt_id']))

    def test_wrong_artifact_hash_and_author_are_rejected(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        for kind in ('hash', 'actor'):
            with self.subTest(kind=kind):
                data = self.template(brief)
                if kind == 'hash':
                    data['artifacts'][0]['sha256'] = '0' * 64
                else:
                    data['agent_id'] = 'other-author'
                with self.assertRaises(ContractError):
                    prepare_submission(self.run, brief['attempt_id'], data)

    def test_traversal_and_outward_symlink_are_rejected(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        work = Path(brief['result_directory'])
        (work / 'outward.txt').symlink_to(self.source)
        for path in ('../input.txt', str(self.source), 'outward.txt'):
            with self.subTest(path=path):
                data = self.template(brief)
                data['artifacts'][0]['path'] = path
                with self.assertRaisesRegex(ContractError, 'inside the attempt'):
                    prepare_submission(self.run, brief['attempt_id'], data)

    def test_preparation_does_not_mutate_worker_template_or_ledger(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        template = self.template(brief)
        original = copy.deepcopy(template)
        before = (self.run.path / 'events.jsonl').read_bytes()
        prepared = prepare_submission(self.run, brief['attempt_id'], template)
        self.assertEqual(template, original)
        self.assertEqual(prepared['agent_id'], 'synthetic-writer')
        self.assertEqual(before, (self.run.path / 'events.jsonl').read_bytes())

    def test_duplicate_submission_is_rejected(self):
        brief = self.execute()
        with self.assertRaisesRegex(ContractError, 'Invalid task state'):
            submit_template(self.run, brief['attempt_id'], self.template(brief))

    def test_failed_required_check_survives_submission_and_blocks_pass(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        submitted = submit_template(self.run, brief['attempt_id'], self.template(brief, passed=False))
        self.assertEqual(submitted['status'], 'needs_revision')
        reviewer = self.execute('reviewer', 'synthetic-reviewer')
        with self.assertRaisesRegex(ContractError, 'cannot erase failed required checks'):
            self.run.review(self.review(brief, reviewer))

    def test_review_preparation_retains_current_targets(self):
        target = self.execute()
        reviewer = self.execute('reviewer', 'synthetic-reviewer')
        template = self.review(target, reviewer)
        del template['review_task_attempt']
        del template['reviewer_agent_id']
        before = copy.deepcopy(template)
        prepared = prepare_review(self.run, reviewer['attempt_id'], template)
        self.assertEqual(template, before)
        self.assertEqual(prepared['targets'], before['targets'])
        self.assertEqual(prepared['reviewer_agent_id'], 'synthetic-reviewer')


if __name__ == '__main__':
    unittest.main(verbosity=2)
