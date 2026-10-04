import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from common import bootstrap, DEFAULT_STATE, runtime_env


class ProfileLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pr-profile-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.run = self.base / 'synthetic-run'
        self.release = Path(bootstrap(DEFAULT_STATE)['root'])
        code = '''
import sys
sys.path.insert(0, sys.argv[1])
from pr.engine import Run
from pr.util import now
request = dict(id='synthetic-profile', text='Synthetic diagnostics only', audience='Developers',
    decision='Read-only behavior', scope='Synthetic empty run', information_cutoff=now(),
    requested_at=now(), language='en', mode='development')
Run.create(sys.argv[2], sys.argv[1], request)
'''
        proc = subprocess.run([sys.executable, '-I', '-B', '-c', code,
                               str(self.release), str(self.run)],
                              cwd=self.release, env=runtime_env(),
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def invoke(self, output):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/profile-run.py'),
                               '--run', str(self.run), '--out', str(output)],
                              env=runtime_env(), capture_output=True, text=True, timeout=120)

    def test_profile_records_run_pin_and_preserves_all_run_files(self):
        before = {p.relative_to(self.run): p.read_bytes()
                  for p in self.run.rglob('*') if p.is_file()}
        output = self.base / 'profile.json'
        proc = self.invoke(output)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(output.read_text())
        self.assertEqual(result['provenance']['package_root'], str(self.release))
        self.assertEqual(result['provenance']['release_id'], json.loads(
            (self.run / 'run.json').read_text())['release_sha256'])
        self.assertIsNone(result['actual_cost'])
        self.assertEqual(before, {p.relative_to(self.run): p.read_bytes()
                                  for p in self.run.rglob('*') if p.is_file()})

    def test_existing_output_is_never_overwritten(self):
        output = self.base / 'profile.json'
        output.write_text('Original evidence')
        proc = self.invoke(output)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('new output file', proc.stderr)
        self.assertEqual(output.read_text(), 'Original evidence')

    def test_output_inside_run_is_rejected(self):
        proc = self.invoke(self.run / 'profile.json')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('outside the run', proc.stderr)
        self.assertFalse((self.run / 'profile.json').exists())

    def test_output_inside_installed_release_is_rejected(self):
        output = self.release / 'profile-must-not-exist.json'
        proc = self.invoke(output)
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(output.exists())

    def test_missing_historical_release_is_not_replaced_by_active_release(self):
        header_path = self.run / 'run.json'
        header = json.loads(header_path.read_text())
        header['package_root'] = str(self.base / 'unavailable-old-release')
        header_path.write_text(json.dumps(header))
        proc = self.invoke(self.base / 'profile.json')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('do not substitute the active release', proc.stderr)
        self.assertFalse((self.base / 'profile.json').exists())


if __name__ == '__main__':
    unittest.main()
