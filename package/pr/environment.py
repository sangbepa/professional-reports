"""Evidence-based environment readiness. No implied model/API capability parity."""
import importlib.metadata
import importlib.util
import platform
import shutil
import subprocess
import sys
from .util import hash_data, now


def doctor():
    probes={}
    for module in ('jsonschema','yaml','openpyxl','pypdf','pypdfium2','artifact_tool'):
        probes[module]=dict(available=importlib.util.find_spec(module) is not None)
        try:probes[module]['version']=importlib.metadata.version('PyYAML' if module=='yaml' else module)
        except importlib.metadata.PackageNotFoundError:probes[module]['version']=None
    for binary in ('node','soffice','pdftoppm','docker'):
        path=shutil.which(binary)
        if path:
            try:
                r=subprocess.run([path,'-v' if binary=='pdftoppm' else '--version'],capture_output=True,text=True,timeout=10)
                probes[binary]=dict(path=path,available=r.returncode==0,version=(r.stdout or r.stderr).strip()[:300])
            except (OSError,subprocess.TimeoutExpired) as exc:probes[binary]=dict(path=path,available=False,error=str(exc))
        else:probes[binary]=dict(available=False,path=None)
    result=dict(python=sys.executable,python_version=platform.python_version(),platform=platform.platform(),probes=probes,
                checked_at=now(),model_support='must be supplied by current native host tool metadata',
                observed_reasoning=None,observed_model=None,maximum_workers_requested=6)
    result['sha256']=hash_data(result)
    return result


def resolve(required,available):
    missing=sorted(set(required)-set(available))
    return dict(status='ready' if not missing else 'provisional-build-required',missing=missing,
                build_action='Select minimal suitable existing native tools before Docker or vector database',
                promotion='Smoke-tested run-local additions stay provisional until controlled evaluation')
