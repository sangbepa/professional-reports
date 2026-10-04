"""Render-only comparison from a frozen adapter run; no calculation/workbook calls."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PROFILES=('transaction','executive','editorial')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--fixture',type=Path,required=True)
    args=parser.parse_args(); source=args.source.resolve();out=args.out.resolve()
    if (out/'report-input.json').exists():parser.error('Use a fresh revision output; prior artifacts are preserved.')
    out.mkdir(parents=True,exist_ok=True); frozen=out/'frozen';frozen.mkdir()
    names=('input.json','model-result.json','calculation-graph.json','report-input.json','report-bindings.json')
    for name in names:shutil.copy2(source/name,frozen/name)
    shutil.copy2(args.fixture,frozen/args.fixture.name)
    data=json.loads((frozen/'input.json').read_text());result=json.loads((frozen/'model-result.json').read_text())
    from report import prepare
    from verify import verify_html,BindingParser
    report,bindings=prepare(data,result)
    if result['synthetic']:
        note={'kind':'source-note','html':f'SYNTHETIC fixture: {args.fixture.name} | input schema {data["schema_version"]}. Fixed test assumptions; no actual-company evidence. Frozen input and model identifiers are supplied in the comparison manifest.'}
        notes=next((s for s in report['report_sections'] if s['id']=='model-conditions'),report['report_sections'][-1])
        notes['blocks'].insert(0,note)
    write(out/'report-input.json',report);write(out/'report-bindings.json',bindings)
    commands=[];checks={}
    for profile in PROFILES:
        command=[sys.executable,str(HERE/'vendor/report_outfit/build.py'),'--mode','report','--template','valuation','--design',profile,'--input',str(out/'report-input.json'),'--out',str(out/profile),'--html-only']
        process=subprocess.run(command,capture_output=True,text=True)
        commands.append({'argv':command,'returncode':process.returncode});(out/(profile+'-build.log')).write_text(process.stdout+process.stderr)
        if process.returncode:raise RuntimeError(process.stderr)
        charts=[b['chart'] for s in report['report_sections'] for b in s['blocks'] if b['kind']=='chart']
        checks[profile]=verify_html(out/profile/'report.html',bindings,charts)
        if not checks[profile]['passed']:raise RuntimeError(checks[profile])
    old=json.loads((frozen/'report-bindings.json').read_text())
    old=old['cells'] if isinstance(old,dict) else old
    old_counter=Counter((b['path'],str(b['value'])) for b in old)
    new_counter=Counter((b['path'],str(b['value'])) for b in bindings)
    missing=old_counter-new_counter
    write(out/'build-checks.json',{'profiles':checks,'original_numeric_bindings_preserved':not missing,'missing_original_values':list(missing.elements()),'original_occurrences':len(old),'new_occurrences':len(bindings),'added_binding_paths':list((new_counter-old_counter).elements()),'recalculation':'skipped; frozen model and graph reused byte-for-byte','financial_review':'not performed','independent_review':'not performed; original reviewer closure pending'})
    write(out/'commands.json',commands)
    write(out/'frozen-hashes.json',{name:sha(frozen/name) for name in names+(args.fixture.name,)})
    if missing:raise RuntimeError('Original numeric bindings lost')
    print(json.dumps({'out':str(out),'profiles':list(PROFILES),'binding_count':len(bindings),'original_values_preserved':not missing}))

if __name__=='__main__':main()
