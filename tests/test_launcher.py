import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from common import PACKAGE,bootstrap,runtime_env

class LauncherTests(unittest.TestCase):
 def test_immutable_package_members_and_version(self):
  sys.path.insert(0,str(PACKAGE));from pr.package import verify
  m=verify(PACKAGE);self.assertEqual(m['version'],'0.4.0-dev.2');self.assertEqual(m['channel'],'development')
 def test_state_inside_package_rejected_before_install(self):
  p=subprocess.run([sys.executable,str(ROOT/'scripts/setup.py'),'--state',str(PACKAGE/'bad-state'),'--skip-dependencies'],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('outside immutable',p.stderr);self.assertFalse((PACKAGE/'bad-state').exists())
 def test_missing_state_is_not_silently_source(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(FileNotFoundError):bootstrap(Path(d)/'missing')
 def test_fixed_frozen_company_cases_not_published(self):
  self.assertEqual(json.loads((PACKAGE/'adapters/reverse-dcf/cases.json').read_text()),{});self.assertFalse((PACKAGE/'adapters/reverse-dcf/cases').exists())
 def test_output_directory_reuse_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=subprocess.run([sys.executable,str(ROOT/'scripts/smoke.py'),'--out',d],capture_output=True,text=True)
   self.assertNotEqual(p.returncode,0);self.assertIn('new output',p.stderr)
 def test_published_protected_materials_match_authorized_scope(self):
  m=json.loads((ROOT/'docs/publication-scope.json').read_text());self.assertEqual(len(m['files']),12)
  import hashlib
  for row in m['files']:self.assertEqual(hashlib.sha256((PACKAGE/row['path']).read_bytes()).hexdigest(),row['sha256'])
 def test_installed_release_current_hashes(self):
  from common import DEFAULT_STATE
  d=bootstrap(DEFAULT_STATE);self.assertTrue(d['verified']);self.assertEqual(d['version'],'0.4.0-dev.2');self.assertNotEqual(Path(d['root']),PACKAGE)
if __name__=='__main__':unittest.main()
