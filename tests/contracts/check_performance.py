from dataclasses import asdict
import unittest

from fixture import RunCase, Run, ContractError
from pr.performance import analyze_plan, interval_summary, profile_run


class PerformanceContracts(RunCase):
    def test_unknown_estimate_prevents_aggregate_projection(self):
        result = analyze_plan(self.run.plan, {'writer': 10}, workers=2)
        self.assertEqual(result['missing_estimates'], ['reviewer'])
        self.assertIsNone(result['projected_seconds'])
        self.assertIsNone(result['slack_seconds']['600'])

    def test_measured_estimate_requires_provenance(self):
        with self.assertRaisesRegex(ContractError, 'require provenance'):
            analyze_plan(self.run.plan, {'writer': {'seconds': 10, 'kind': 'measured'}})

    def test_serial_dependencies_and_worker_bound_are_preserved(self):
        result = analyze_plan(self.run.plan, {'writer': 10, 'reviewer': 5}, workers=2)
        self.assertEqual(result['critical_path'], ['writer', 'reviewer'])
        self.assertEqual(result['projected_seconds'], 15)
        for workers in (0, 7, True):
            with self.subTest(workers=workers), self.assertRaises(ContractError):
                analyze_plan(self.run.plan, {}, workers=workers)

    def test_interval_union_is_not_summed_work(self):
        result = interval_summary([(0, 10), (5, 15)])
        self.assertEqual(result['union_seconds'], 15)
        self.assertEqual(result['overlap_seconds'], 5)
        self.assertEqual(result['summed_interval_seconds'], 20)

    def test_profile_is_read_only_and_snapshot_is_detached(self):
        self.execute()
        self.execute('reviewer', 'synthetic-reviewer')
        paths = [p for p in self.run.path.rglob('*') if p.is_file()]
        before = {str(p): p.read_bytes() for p in paths}
        restored = Run(self.run.path)
        result = profile_run(restored)
        self.assertEqual(before, {str(p): p.read_bytes() for p in paths})
        self.assertEqual(set(before), {str(p) for p in self.run.path.rglob('*') if p.is_file()})
        self.assertIsNone(result['true_compute_seconds'])
        self.assertIsNone(result['actual_cost'])
        self.assertEqual(result['snapshot'].count, len(restored.events))
        snapshot = asdict(result['snapshot'])
        restored.events[0]['data']['request_id'] = 'changed-in-memory'
        self.assertEqual(asdict(result['snapshot']), snapshot)
        self.assertEqual({a['review_role'] for a in result['attempts']}, {None, 'document'})

    def test_unbound_failed_retry_remains_unknown_execution(self):
        first = self.dispatch()
        self.run.fail(first['attempt_id'], 'Synthetic failure without binding')
        self.execute(actor='synthetic-retry')
        result = profile_run(Run(self.run.path))
        self.assertEqual(len(result['attempts']), 2)
        first_row = next(a for a in result['attempts'] if a['attempt_id'] == first['attempt_id'])
        self.assertIsNone(first_row['execution_interval'])
        self.assertEqual(first_row['failures'][0]['reason'], 'Synthetic failure without binding')


if __name__ == '__main__':
    unittest.main(verbosity=2)
