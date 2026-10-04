import unittest

from fixture import RunCase, ContractError
from pr.sessions import (file_reference, safe_read, persist_output, build_handoff,
                         record_session, close_session, read_closure, spawn_request)
from pr.util import now


class SessionContracts(RunCase):
    def test_safe_read_uses_explicit_ranges_and_rejects_stale_hash(self):
        self.source.write_text('first\nsecond\nthird\n')
        ref = file_reference(self.base, 'input.txt', version='v1',
                             read_ranges=[dict(start=2, end=2)])
        self.assertEqual(safe_read(self.base, ref)['text'], 'second\n')
        self.source.write_text('first\nchanged\nthird\n')
        with self.assertRaisesRegex(ContractError, 'hash or path mismatch'):
            safe_read(self.base, ref)

    def test_no_ranges_overlap_and_outward_symlink_are_rejected(self):
        self.source.write_text('one\ntwo\nthree\n')
        ref = file_reference(self.base, 'input.txt', version='v1')
        with self.assertRaisesRegex(ContractError, 'Explicit read ranges'):
            safe_read(self.base, ref)
        with self.assertRaisesRegex(ContractError, 'overlapping'):
            file_reference(self.base, 'input.txt', version='v1',
                           read_ranges=[dict(start=1, end=2), dict(start=2, end=3)])
        (self.base / 'link.txt').symlink_to(self.source)
        with self.assertRaisesRegex(ContractError, 'Redirected evidence'):
            file_reference(self.base, 'link.txt', version='v1')

    def test_raw_output_survives_invalid_compact_view_without_overwrite(self):
        raw = '{"synthetic": "full raw evidence"}\n'
        with self.assertRaises(ContractError):
            persist_output(self.base, 'raw.txt', raw, version='v1', summary='x' * 4001)
        self.assertEqual((self.base / 'raw.txt').read_text(), raw)
        with self.assertRaises(FileExistsError):
            persist_output(self.base, 'raw.txt', 'replacement', version='v1', summary='short')
        self.assertEqual((self.base / 'raw.txt').read_text(), raw)

    def test_handoff_rejects_changed_scope_and_missing_evidence(self):
        ref = file_reference(self.base, 'input.txt', version='v1',
                             read_ranges=[dict(start=1, end=1)])
        packet = dict(task_id='writer', scope=['text'], from_session='session-1',
                      to_attempt='attempt-2', summary='Synthetic scoped handoff',
                      inputs=[ref], no_reread_refs=[ref])
        self.assertEqual(build_handoff(self.base, **packet)['inputs'], [ref])
        with self.assertRaisesRegex(ContractError, 'outside handoff scope'):
            build_handoff(self.base, **packet, open_findings=[dict(
                id='finding-1', scope=['unrelated'], text='Synthetic', evidence=[ref])])
        with self.assertRaisesRegex(ContractError, 'already read packet'):
            build_handoff(self.base, **dict(packet, inputs=[]))

    def test_wait_completion_and_close_failure_do_not_confirm_session_closure(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        record_session(self.run, 'session-1', brief['attempt_id'])
        base = dict(agent_id='synthetic-writer', captured_at=now(),
                    request={'agent_id': 'synthetic-writer'}, synthetic_fixture=True)
        for receipt in (dict(base, tool='multi_agent_v1.wait_agent', response={'status': 'completed'}),
                        dict(base, tool='multi_agent_v1.close_agent', response={'success': False}),
                        dict(base, tool='multi_agent_v1.close_agent', response={'timed_out': True}),
                        dict(base, tool='multi_agent_v1.close_agent', response={})):
            with self.subTest(receipt=receipt), self.assertRaises(ContractError):
                close_session(self.run, 'session-1', receipt)
        self.assertFalse((self.run.path / 'session-closures' / 'session-1.json').exists())
        receipt = dict(base, tool='multi_agent_v1.close_agent', response={'status': 'shutdown'})
        closed = close_session(self.run, 'session-1', receipt)
        self.assertTrue(closed['observed_closed'])
        self.assertEqual(read_closure(self.run, 'session-1'), closed)

    def test_close_receipt_actor_mismatch_is_rejected(self):
        brief = self.dispatch()
        self.bind(brief, 'synthetic-writer')
        record_session(self.run, 'session-1', brief['attempt_id'])
        with self.assertRaisesRegex(ContractError, 'identity mismatch'):
            close_session(self.run, 'session-1', dict(
                tool='multi_agent_v1.close_agent', captured_at=now(),
                agent_id='other-actor', response={'success': True}))

    def test_spawn_request_is_only_a_request_with_explicit_isolation(self):
        request = spawn_request('Synthetic prompt', reasoning_effort='high')
        self.assertEqual(request, dict(message='Synthetic prompt', fork_context=False,
                                       reasoning_effort='high'))
        self.assertNotIn('agent_id', request)


if __name__ == '__main__':
    unittest.main(verbosity=2)
