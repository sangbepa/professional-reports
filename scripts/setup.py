#!/usr/bin/env python3
"""Prepare a local Codex package. Activation requires an explicit development flag."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from common import ROOT,PACKAGE,DEFAULT_STATE,runtime_python,runtime_env

def execute(args,**kwargs):
    subprocess.run([str(x) for x in args],check=True,**kwargs)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path,default=DEFAULT_STATE)
    p.add_argument('--activate-development',action='store_true')
    p.add_argument('--with-browser',action='store_true')
    p.add_argument('--with-system-deps',action='store_true')
    p.add_argument('--skip-dependencies',action='store_true',help='Reuse a prepared Python environment; missing packages fail normally')
    a=p.parse_args()
    if sys.version_info<(3,11):p.error('Python 3.11+ required')
    state=a.state.expanduser().resolve()
    if state==PACKAGE or state.is_relative_to(PACKAGE):p.error('State must be outside immutable package/')
    if a.with_system_deps and not a.with_browser:p.error('--with-system-deps requires --with-browser')
    python=runtime_python()
    if not python.exists():execute([sys.executable,'-m','venv',python.parent.parent])
    if not a.skip_dependencies:execute([python,'-m','pip','install','-r',PACKAGE/'requirements-runtime.lock.txt'])
    if a.with_browser:
        node=shutil.which('node');npm=shutil.which('npm')
        if not node or not npm:p.error('Node.js 20+ and npm required for --with-browser')
        version=subprocess.check_output([node,'--version'],text=True).strip()
        if int(version.lstrip('v').split('.')[0])<20:p.error('Node.js 20+ required')
        target=ROOT/'.runtime/node';target.mkdir(parents=True,exist_ok=True)
        for name in ('package.json','package-lock.json'):shutil.copyfile(ROOT/'runtime-node'/name,target/name)
        execute([npm,'ci','--prefix',target])
        env=runtime_env();env['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'.runtime/browsers')
        args=[node,target/'node_modules/playwright/cli.js','install']
        if a.with_system_deps:args.append('--with-deps')
        execute([*args,'chromium'],env=env)
    execute([python,'-m','pr','verify','--release',PACKAGE],cwd=PACKAGE,stdout=subprocess.DEVNULL)
    install=subprocess.run([str(python),'-m','pr','install','--release',str(PACKAGE),'--state',str(state)],cwd=PACKAGE,capture_output=True,text=True,check=True)
    installed=json.loads(install.stdout)
    if a.activate_development:execute([python,'-m','pr','activate','--state',state,'--release-id',installed['release_id'],'--development'],cwd=PACKAGE,stdout=subprocess.DEVNULL)
    print(json.dumps({'installed':True,'activated':a.activate_development,'state':str(state),'release_id':installed['release_id'],'python':str(python),'browser_prepared':a.with_browser,'professional_quality_accepted':False},ensure_ascii=False))
    return 0
if __name__=='__main__':raise SystemExit(main())
