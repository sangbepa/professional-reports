"""Run public contract suites in fresh interpreters from a clean installed release."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from common import PACKAGE, runtime_env


class InstalledContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='pr-contracts-')
        cls.addClassCleanup(cls.temp.cleanup)
        env = dict(runtime_env(), PYTHONDONTWRITEBYTECODE='1')
        # Installation does not activate or alter the project's existing state.
        proc = subprocess.run(
            [sys.executable, '-m', 'pr', 'install', '--release', str(PACKAGE),
             '--state', cls.temp.name], cwd=PACKAGE, env=env,
            capture_output=True, text=True, timeout=120)
        if proc.returncode:
            raise RuntimeError(proc.stdout + proc.stderr)
        import json
        cls.release = json.loads(proc.stdout)['path']

    def run_suite(self, name):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'tests' / 'contracts' / name)],
            cwd=self.release, env=dict(runtime_env(), PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True, text=True, timeout=120)
        if proc.returncode == 0:
            sys.stderr.write(proc.stderr)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('OK', proc.stderr)

    def test_engine_contracts(self):
        self.run_suite('check_engine.py')

    def test_native_contracts(self):
        self.run_suite('check_native.py')

    def test_session_contracts(self):
        self.run_suite('check_sessions.py')

    def test_performance_contracts(self):
        self.run_suite('check_performance.py')


if __name__ == '__main__':
    unittest.main()
