#!/usr/bin/env python3
"""Fresh-call valuation adapter; never imports or modifies the parent engine."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
if __package__:
    from .model import calculate
    from .report import prepare
    from .workbook import export,audit,recalculate,write_json
    from .render import render_pdf
    from .verify import verify_html
else:
    from model import calculate
    from report import prepare
    from workbook import export,audit,recalculate,write_json
    from render import render_pdf
    from verify import verify_html


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_vendor():
    manifest=json.loads((HERE/'vendor/manifest.json').read_text())
    for relative,expected in manifest['files'].items():
        path=HERE/'vendor'/relative
        if not path.is_file() or digest(path)!=expected:
            raise ValueError('Vendored native renderer integrity mismatch: '+relative)


def run(input_path,out,design='transaction',xlsx_engine='auto',recalc='auto',pdf='auto'):
    verify_vendor()
    input_path=Path(input_path).resolve();out=Path(out).resolve()
    # Parse and validate before creating any output. JSON duplicate keys are rejected.
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON key '+key)
            result[key]=value
        return result
    data=json.loads(input_path.read_text(),object_pairs_hook=unique)
    result,graph=calculate(data)
    if out.exists() and any(out.iterdir()):raise FileExistsError('Use a fresh --out directory; prior artifacts are preserved')
    frozen_input=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    result['input_sha256']=hashlib.sha256(frozen_input.encode()).hexdigest()
    report,bindings=prepare(data,result)
    charts=[block['chart'] for section in report['report_sections'] for block in section['blocks'] if block['kind']=='chart']
    out.mkdir(parents=True,exist_ok=True)
    (out/'input.json').write_text(frozen_input)
    write_json(out/'model-result.json',result)
    write_json(out/'calculation-graph.json',graph.serializable())
    write_json(out/'report-input.json',report)
    write_json(out/'report-bindings.json',dict(model_sha256=digest(out/'model-result.json'),cells=bindings,
                                              chart=charts,scope='Generated numeric binding, not independent financial review'))
    status=dict(schema_version='0.1.0-dev.1',status='in_progress',financial_review='not_performed',
                independent_design_selection='not_performed',professional_quality='not_assessed',
                input_sha256=result['input_sha256'],original_input_sha256=digest(input_path),model_sha256=digest(out/'model-result.json'),
                schema_sha256=digest(HERE/'input.schema.json'),design=design,model='deterministic_segmented_dcf_residual_income',warnings=result['warnings'])
    write_json(out/'manifest.json',status)
    try:
        status['workbook']=export(data,graph,out,xlsx_engine)
        status['recalculation']=recalculate(out,graph,recalc)
        status['workbook']['audit']=audit(out/'valuation.xlsx',graph,require_cached=status['recalculation']['status']=='passed')
        native=HERE/'vendor/report_outfit/build.py'
        proc=subprocess.run([sys.executable,str(native),'--input',str(out/'report-input.json'),'--mode','report',
                             '--template','valuation','--design',design,'--out',str(out/'report'),'--html-only'],
                            capture_output=True,text=True,timeout=60)
        (out/'native-build.log').write_text(proc.stdout+'\n'+proc.stderr)
        if proc.returncode:raise RuntimeError('Native report constructor failed; see native-build.log')
        status['html_bindings']=verify_html(out/'report/report.html',bindings,charts)
        status['pdf']=render_pdf(out/'report',pdf)
        if (out/'report/rendered.html').exists():
            status['rendered_bindings']=verify_html(out/'report/rendered.html',bindings,charts)
        status['native_constructor_sha256']=digest(native)
        status['native_full_report_sha256']=digest(native.with_name('full_report.py'))
        status['vendor_manifest_sha256']=digest(HERE/'vendor/manifest.json')
        failed=(not status['html_bindings']['passed'] or not status.get('rendered_bindings',{'passed':True})['passed'] or not status['workbook']['audit']['passed'] or status['recalculation']['status']=='failed' or status['pdf']['status']=='failed')
        if recalc=='required' and status['recalculation']['status']!='passed':failed=True
        if pdf=='required' and status['pdf']['status']!='rendered':failed=True
        status['status']='failed' if failed else 'completed_conditional'
    except Exception as exc:
        status['status']='failed';status['error']=str(exc)
        write_json(out/'manifest.json',status)
        raise
    status['artifacts']={str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    write_json(out/'manifest.json',status)
    return status


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--design',choices=['transaction','executive','editorial'],default='transaction')
    parser.add_argument('--xlsx-engine',choices=['auto','artifact','openpyxl'],default='auto')
    parser.add_argument('--recalc',choices=['auto','required','skip'],default='auto')
    parser.add_argument('--pdf',choices=['auto','required','skip'],default='auto')
    args=parser.parse_args()
    # Fresh CLI calls may originate in the parent engine's lean Python runtime.
    # Re-exec only a capability-probed runtime, without changing any dependencies.
    try:
        from .runtime import workbook_python
    except ImportError:
        from runtime import workbook_python
    python=workbook_python()
    if python and Path(python).resolve()!=Path(sys.executable).resolve():
        return subprocess.run([python,str(HERE/'build.py'),*sys.argv[1:]]).returncode
    try:
        status=run(args.input,args.out,args.design,args.xlsx_engine,args.recalc,args.pdf)
        print(json.dumps({'status':status['status'],'manifest':str(args.out/'manifest.json')}))
        return 1 if status['status']=='failed' else 0
    except Exception as exc:
        print(str(exc),file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
