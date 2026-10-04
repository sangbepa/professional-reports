"""Probe by actually launching the PDF engine, then render the native HTML."""
import json
import os
from pathlib import Path
import shutil
import subprocess

try:
    from .runtime import node_executable
except ImportError:
    from runtime import node_executable

HERE=Path(__file__).parent

def render_pdf(out,mode='auto'):
    if mode=='skip':return {'status':'not_requested','financial_review':'not_performed'}
    node=node_executable('REPORT_OUTFIT_NODE')
    if not node:return {'status':'unavailable','reason':'Node executable unavailable'}
    env=os.environ.copy()
    if not env.get('REPORT_OUTFIT_PLAYWRIGHT'):
        runtime=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
        if runtime.exists():env['REPORT_OUTFIT_PLAYWRIGHT']=str(runtime)
    try:
        probe=subprocess.run([node,str(HERE/'pdf_probe.mjs')],env=env,capture_output=True,text=True,timeout=30)
        if probe.returncode:return {'status':'unavailable','reason':probe.stderr.strip(),'probe_executed':True}
        capability=json.loads(probe.stdout)
        proc=subprocess.run([node,str(HERE/'vendor/report_outfit/render.mjs'),str(out)],env=env,
                            capture_output=True,text=True,timeout=180)
        (out/'pdf-render.log').write_text(proc.stdout+'\n'+proc.stderr)
        pdf=out/'report.pdf'
        exists=pdf.exists() and pdf.read_bytes().startswith(b'%PDF-')
        layout=json.loads((out/'layout-checks.json').read_text()) if (out/'layout-checks.json').exists() else None
        return dict(status='rendered' if proc.returncode==0 and exists else 'failed',
                    engine=capability,pdf_exists=exists,layout_passed=layout.get('passed') if layout else False,
                    page_count=len(layout['pages']) if layout else None,
                    log='pdf-render.log',visual_review='not_performed',financial_review='not_performed')
    except (OSError,subprocess.TimeoutExpired,ValueError) as exc:
        return dict(status='failed',reason=str(exc),financial_review='not_performed')


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',required=True,type=Path,help='Native report output directory containing report.html/input.json/specification.json')
    parser.add_argument('--mode',choices=['auto','required'],default='auto')
    args=parser.parse_args()
    if not (args.report/'report.html').is_file():parser.error('report.html does not exist')
    status=render_pdf(args.report.resolve(),args.mode)
    (args.report/'render-status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status))
    return int(status['status']=='failed' or (args.mode=='required' and status['status']!='rendered'))


if __name__=='__main__':
    raise SystemExit(main())
