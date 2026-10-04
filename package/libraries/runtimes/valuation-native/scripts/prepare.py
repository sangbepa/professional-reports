#!/usr/bin/env python3
"""Optional explicit native venv build, then actual import/file smoke tests."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import subprocess
import sys
import venv
from pathlib import Path


def probe(out):
    modules={}
    for module,dist in [('jsonschema','jsonschema'),('yaml','PyYAML'),('openpyxl','openpyxl'),('pypdf','pypdf'),('pypdfium2','pypdfium2')]:
        present=importlib.util.find_spec(module) is not None
        modules[module]={'available':present,'version':importlib.metadata.version(dist) if present else None}
    checks={}
    if modules['openpyxl']['available']:
        import openpyxl
        wb=openpyxl.Workbook();wb.active['A1']=2;wb.active['B1']='=A1*3';p=out/'smoke.xlsx';wb.save(p)
        reopened=openpyxl.load_workbook(p,data_only=False)
        checks['xlsx_formula_save_reopen']=reopened.active['B1'].value=='=A1*3'
        checks['xlsx_native_recalculation']=None
    record=dict(python=sys.executable,python_version=platform.python_version(),modules=modules,checks=checks,
                status='provisional',native_recalculation='separate actual engine test required',pdf_visual_review='not_performed')
    (out/'environment.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--build',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    if a.build:
        target=a.out/'venv';venv.EnvBuilder(with_pip=True).create(target);python=target/'bin/python'
        lock=Path(__file__).resolve().parents[1]/'requirements.lock'
        r=subprocess.run([str(python),'-m','pip','install','-r',str(lock)],capture_output=True,text=True)
        (a.out/'build.log').write_text(r.stdout+'\n'+r.stderr)
        if r.returncode:raise SystemExit(r.returncode)
        r=subprocess.run([str(python),str(Path(__file__).resolve()),'--out',str(a.out/'smoke')],capture_output=True,text=True)
        (a.out/'probe.log').write_text(r.stdout+'\n'+r.stderr)
        print(json.dumps({'status':'provisional','returncode':r.returncode,'requirements_sha256':hashlib.sha256(lock.read_bytes()).hexdigest()}))
        return r.returncode
    print(json.dumps(probe(a.out),indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
