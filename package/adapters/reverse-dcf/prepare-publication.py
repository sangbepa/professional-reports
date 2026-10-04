import json,sys,hashlib,html
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve()
SCRIPTS=Path(__file__).resolve().parents[2]/"adapters/report-publication/vendor/report-design/scripts"
sys.path.insert(0,str(SCRIPTS))
import build,full_report,prepare_report
from html_dom import DOM
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
d=json.loads((ROOT/"input.json").read_text())
build.validate(d)
parts=[]
for s in d["report_sections"]:
 body="".join(full_report.emit(b,i+1) for i,b in enumerate(s["blocks"]))
 parts.append('<section class="page"><div class="pagebody"><h2>'+html.escape(s["title"])+'</h2>'+body+'</div></section>')
source=ROOT/"source-content.html"
source.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+html.escape(d["title"])+"</title><body>"+"".join(parts)+"</body></html>")
d["retention"]=prepare_report.retained(DOM(source.read_text()).root)
d["provenance"]={"source_report":str(source),"source_report_sha256":sha(source),"model_results":str(ROOT/"analysis/result.json"),"model_results_sha256":sha(ROOT/"analysis/result.json"),"previous_design_retained":False}
d["overview_mode"]="integrated"
(ROOT/"input.json").write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
manifest={"input_sha256":sha(ROOT/"input.json"),"source_sha256":sha(source),"result_sha256":sha(ROOT/"analysis/result.json"),"generator_sha256":sha(SCRIPTS/"build.py"),"renderer_sha256":sha(SCRIPTS/"render.mjs"),"native_profile":"executive","native_mode":"report","template":"valuation"}
(ROOT/"input-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({"sections":len(d["report_sections"]),"retention":{k:len(v) for k,v in d["retention"].items()}}))
