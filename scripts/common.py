"""Project-local launcher; state and dependencies never enter the immutable package."""
import importlib.util,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'package'
DEFAULT_STATE=ROOT/'.state'

def runtime_python():
    return ROOT/'.runtime/python'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')

def bootstrap(state):
    spec=importlib.util.spec_from_file_location('professional_reports_bootstrap',PACKAGE/'skills/professional-reports/scripts/bootstrap.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.load(state)

def runtime_env():
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env.pop('PYTHONPATH',None)
    playwright=ROOT/'.runtime/node/node_modules/playwright'
    if playwright.is_dir():
        env['REPORT_OUTFIT_PLAYWRIGHT']=str(playwright)
        env['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'.runtime/browsers')
        node=__import__('shutil').which('node')
        if node:
            probe=subprocess.run([node,'-e','const{chromium}=require(process.argv[1]);process.stdout.write(chromium.executablePath())',str(playwright)],env=env,capture_output=True,text=True,timeout=15,check=True)
            browser=Path(probe.stdout)
            if browser.is_file():env['REPORT_OUTFIT_CHROME']=str(browser)
    return env

def run(args,state=DEFAULT_STATE):
    installed=bootstrap(state);python=runtime_python()
    if not python.is_file():raise RuntimeError('Run python3 scripts/setup.py first')
    return subprocess.run([str(python),*args],cwd=installed['root'],env=runtime_env()).returncode
