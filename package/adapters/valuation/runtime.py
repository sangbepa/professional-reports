"""Read-only capability discovery; no installations and no author checkout paths."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys


def bundled(relative):
    path=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'/relative
    return str(path) if path.is_file() else None


def workbook_python():
    if importlib.util.find_spec('openpyxl') is not None:return sys.executable
    candidates=[os.environ.get('VALUATION_PYTHON'),bundled('python/bin/python3')]
    for candidate in candidates:
        if not candidate or Path(candidate).resolve()==Path(sys.executable).resolve():continue
        try:
            probe=subprocess.run([candidate,'-c','import openpyxl; print(openpyxl.__version__)'],
                                 capture_output=True,text=True,timeout=15)
            if probe.returncode==0 and probe.stdout.strip():return candidate
        except (OSError,subprocess.TimeoutExpired):continue
    return None


def node_executable(variable='VALUATION_NODE'):
    for candidate in [os.environ.get(variable),shutil.which('node'),bundled('node/bin/node')]:
        if candidate:
            try:
                probe=subprocess.run([candidate,'--version'],capture_output=True,text=True,timeout=10)
                if probe.returncode==0 and probe.stdout.strip().startswith('v'):return candidate
            except (OSError,subprocess.TimeoutExpired):pass
    return None
