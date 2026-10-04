"""Explicit maintenance/growth/working-capital bridge to terminal cash flow.

All rates are supplied choices. D&A is not assumed to equal maintenance capex.
The implied incremental return is an algebraic equivalent, not an observed ROIC.
"""
import argparse,hashlib,json,math
from pathlib import Path

def capital_bridge(*,last_revenue,terminal_margin,tax_rate,growth,da_rate,
 maintenance_capex_rate,growth_capex_rate,nwc_rate,wacc,terminal_time):
 values=locals().copy()
 if any(type(v) not in (int,float) or not math.isfinite(v) for v in values.values()):raise ValueError('Finite explicit capital assumptions required')
 if last_revenue<=0 or growth<=-1 or not 0<=tax_rate<=1 or min(da_rate,maintenance_capex_rate,growth_capex_rate)<0 or wacc<=growth or wacc<=-1 or terminal_time<=0:raise ValueError('Unsupported explicit capital or discount inputs')
 revenue=last_revenue*(1+growth);nopat=revenue*terminal_margin*(1-tax_rate)
 da=revenue*da_rate;maintenance=revenue*maintenance_capex_rate;expansion=revenue*growth_capex_rate
 delta_nwc=last_revenue*growth*nwc_rate;reinvestment=maintenance+expansion-da+delta_nwc
 fcff=nopat-reinvestment;terminal_value=fcff/(wacc-growth);pv=terminal_value/(1+wacc)**terminal_time
 implied=nopat*growth/reinvestment if reinvestment and growth else None
 eligible=implied is not None and implied>0
 roic_reinvestment=nopat*growth/implied if eligible else None
 result={'kind':'explicit_capital_bridge_not_approval','inputs':values,'terminal_revenue':revenue,
  'terminal_nopat':nopat,'da':da,'maintenance_capex':maintenance,'growth_capex':expansion,
  'delta_nwc':delta_nwc,'reinvestment':reinvestment,'terminal_fcff':fcff,'terminal_value':terminal_value,
  'terminal_pv':pv,'implied_incremental_return':implied,'positive_roic_method_equivalent':eligible,
  'equivalence_error':None if not eligible else roic_reinvestment-reinvestment,
  'maintenance_da_difference':maintenance-da,'financial_approval':False,'forecast_adopted':False,
  'scope':'Analyst must evidence physical rates, asset productivity, transition and uncertainty. Implied incremental return is not historical average ROIC or proof of economics; no input or base valuation is modified.'}
 if any(not math.isfinite(x) for x in [revenue,nopat,reinvestment,fcff,terminal_value,pv]):raise ValueError('Nonfinite terminal calculation')
 return result

def run(out):
 out=Path(out).resolve();source=(out/'terminal-capital-cases.json').resolve();dest=out/'terminal-capital-analysis.json'
 if not source.is_relative_to(out):raise ValueError('Capital case source escaped attempt')
 if dest.exists():raise FileExistsError('Capital analysis is append-only')
 raw=source.read_bytes();cases=json.loads(raw)
 if not isinstance(cases,list) or not cases:raise ValueError('Explicit capital cases required')
 seen=set();results=[]
 for c in cases:
  if not isinstance(c.get('id'),str) or not c['id'] or c['id'] in seen or not isinstance(c.get('rationale'),str) or not c['rationale'].strip():raise ValueError('Unique capital case and rationale required')
  seen.add(c['id']);result=capital_bridge(**c['inputs']);result.update(id=c['id'],rationale=c['rationale'],support_refs=c.get('support_refs',[]));results.append(result)
 if source.read_bytes()!=raw:raise ValueError('Capital cases changed during calculation')
 receipt={'kind':'chosen_terminal_capital_cases_not_approval','source_sha256':hashlib.sha256(raw).hexdigest(),'cases':results,'financial_approval':False,'forecast_adopted':False}
 with dest.open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2,allow_nan=False)
 return {'status':'computed_unreviewed','cases':len(results),'path':str(dest),'financial_approval':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();print(json.dumps(run(a.out)))
