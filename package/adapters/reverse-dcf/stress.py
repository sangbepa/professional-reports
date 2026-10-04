import sys,json,importlib.util
from pathlib import Path
P=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pr.reverse_dcf import solve
s=importlib.util.spec_from_file_location('audit',P/'analysis/frozen/audit-2026-09-23-calculation-check.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a);a.BOOK=P/'analysis/frozen/Hyundai-Motor-DCF-2026-09-22.xlsx'
cells,meta=a.load_xml();asts={k:a.Parser(v['formula'],k[0]).parse() for k,v in cells.items() if v['formula'] is not None}
r=json.loads((P/'analysis/result.json').read_text());target=r['target_price'];rows=[]
def overrides(g,h):return {**{('DCF',c+'47'):g for c in 'DEFGHIJ'},('DCF','D82'):float(cells['DCF','D82']['value'])*(1-h),('DCF','D87'):float(cells['DCF','D87']['value'])*(1-h)}
for h in [0,.25,.5]:
 f=lambda g:a.Engine(cells,asts,overrides(g,h)).cell('DCF','D126')
 solved=solve(f,target,-.3,.3);g=solved['roots'][0]
 decimal=float(a.independent(cells,overrides=overrides(g,h))['price'])
 assert abs(decimal/target-1)<.001
 rows.append({'haircut':h,'growth':g,'forward_price':f(g),'independent_decimal_price':decimal,'bridge_reduction':(r['bridge_trillion_krw']['finance_equity']+r['bridge_trillion_krw']['associates'])*h,'fixed_growth_price':f(r['growth']),'roundtrip_pass':True})
price0=a.Engine(cells,asts,overrides(0,0)).cell('DCF','D126')
threshold=(price0-target)*r['shares_million']['outstanding']/1e6/(r['bridge_trillion_krw']['finance_equity']+r['bridge_trillion_krw']['associates'])
stress={'scope':'Mechanical value-haircut scenarios, not impairment forecasts or valuation recommendations','rows':rows,'zero_growth_price':price0,'zero_growth_haircut_threshold':threshold,'other_assumptions_fixed':True};(P/'analysis/stress.json').write_text(json.dumps(stress,ensure_ascii=False,indent=2))

s=stress
full=s['zero_growth_price']-(s['rows'][1]['bridge_reduction']/.25)*1e6/r['shares_million']['outstanding']
s['zero_growth_haircut_feasible_with_nonnegative_values']=s['zero_growth_haircut_threshold']<=1
s['zero_growth_price_after_full_haircut']=full
(P/'analysis/stress.json').write_text(json.dumps(s,ensure_ascii=False,indent=2))
components=a.independent(cells,overrides=overrides(r['growth'],0))
keys=['stub_days','stub_years','stub_fcff','stub_period','stub_pv','explicit_pv','terminal_period','terminal_fcff','terminal_value','terminal_pv','terminal_share','operating_ev']
values={k:float(components[k]) for k in keys}
assert abs(values['stub_pv']+values['explicit_pv']+values['terminal_pv']-values['operating_ev'])<1e-9
(P/'analysis/value-components.json').write_text(json.dumps({'values':values,'units':'cash/values trillion KRW; stub_days days; other time periods years; terminal_share fraction','source':'unchanged frozen audit independent(cells) from literal workbook inputs','three_way_pv_bridge_pass':True},ensure_ascii=False,indent=2))
