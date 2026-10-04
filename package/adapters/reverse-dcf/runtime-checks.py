"""Extract this registered model's literal inputs for common regression guards."""
import datetime
import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pr.report_checks import check_value_components, check_equity_bridge

out=Path(sys.argv[1]).resolve()
case=json.loads((ROOT/'adapters/reverse-dcf/cases.json').read_text())
audit=next((out/'analysis/frozen').glob('*calculation-check.py'))
book=next((out/'analysis/frozen').glob('*.xlsx'))
spec=importlib.util.spec_from_file_location('literal_model',audit)
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);a.BOOK=book
cells,_=a.load_xml()
raw=lambda addr:float(cells['DCF',addr]['value'])
result=json.loads((out/'analysis/result.json').read_text())
values=json.loads((out/'analysis/value-components.json').read_text())['values']
valuation=(datetime.date(1899,12,30)+datetime.timedelta(days=int(raw('G4')))).isoformat()
literals={'valuation_date':valuation,'first_year':int(raw('D44')),
    'half_year_revenue':[raw('D200'),raw('D201')],
    'stub_operating_profit':[raw('D217'),raw('D218')],
    'stub_da_rate':raw('J74'),'stub_capex_rate':raw('J75'),'stub_nwc':raw('J76'),
    'tax_rate':raw('D92'),'wacc':result['wacc'],'terminal_growth':raw('D77'),
    'annual':[{'growth':result['growth'],'margin':raw(c+'52'),'da_rate':raw(c+'57'),
               'capex_rate':raw(c+'62'),'nwc_rate':raw(c+'67')} for c in 'DEFGHIJ']}
expected=check_value_components(literals,values,result['forecast'])
bridge_inputs={'consolidated_assets':[raw('D'+str(i)) for i in range(204,207)],
    'consolidated_liabilities':[raw('D'+str(i)) for i in range(207,211)],
    'finance_nfa_assets':[raw('D211'),raw('D212')],
    'finance_nfa_liabilities':[raw('D213'),raw('D214')],
    'finance_assets':raw('D202'),'finance_liabilities':raw('D203'),'finance_factor':raw('D82'),
    'associate_assets':raw('D215'),'associate_liabilities':raw('D216'),'associate_factor':raw('D87'),
    'nci':raw('D35'),'share_classes':[{'issued':raw('D'+str(i)),'treasury':raw('E'+str(i))} for i in range(235,239)]}
check_equity_bridge(result['bridge_trillion_krw'],result['shares_million'],bridge_inputs,
                   operating_ev=expected['operating_ev'],forward_price=result['forward_price'])
data={'scope':'Developer deterministic defenses; original twelve checks remain required.',
      'literals':literals,'bridge_inputs':bridge_inputs,
      'checks':{'three_way_pv_independent_recalculation':True,'nci_bridge_shares_independent_recalculation':True},
      'limitations':'Literal arithmetic from frozen model; WACC is already independently checked by original twelve checks. No economic source assurance.'}
(out/'analysis/regression-checks.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(data['checks']))
