"""Independent scalar replay of the canonical valuation model.

No producer graph/calculator imports. Chosen assumptions are not validated as
fair values. Core schedules, bridges, class allocation and sensitivity cells
are independently calculated; diagnostics are questions, never approval.
"""
import argparse,hashlib,json,math
from pathlib import Path

def number(atom):
 x=atom['value']
 if type(x) not in (float,int) or not math.isfinite(x):raise ValueError('Finite numeric atom required')
 return x
def atoms(x,path=''):
 if isinstance(x,dict):
  if all(k in x for k in ('value','kind','unit','source','as_of')):yield path,x
  else:
   for k,v in x.items():yield from atoms(v,(path+'.'+k).strip('.'))
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from atoms(v,path+'.'+str(i))

def audit_math(data,result):
 expected={};units={};issues=[];diagnostics=[]
 explicit_classes=data['class_rights']['value']=='explicit_distribution_streams'
 if data['class_rights']['value'] not in ('explicit_distribution_streams','pari_passu_fixed_then_weighted_residual'):raise ValueError('Unsupported class rights method')
 if explicit_classes:
  # Schema/provenance checks are shared contracts; cashflow arithmetic below
  # is independently implemented and imports neither producer nor class helper.
  try:
   from .schema_tools import validate_schema
   from .input_units import canonical_unit
  except ImportError:
   from schema_tools import validate_schema
   from input_units import canonical_unit
  validate_schema(data)
  if 'class_cashflows' not in data:raise ValueError('Explicit class cashflows required')
  for path,atom in atoms(data):
   if not path.startswith('class_cashflows.'):continue
   if atom['as_of']>data['valuation_date'] or atom['review']['status']=='rejected':raise ValueError('Invalid cashflow cutoff or review: '+path)
   if atom['review']['status']=='reviewed' and not all(atom['review'][k] for k in ('reviewer','reference')):raise ValueError('Incomplete reviewed metadata: '+path)
   if atom['kind']=='synthetic' and not data['synthetic']:raise ValueError('Synthetic cashflow needs synthetic engagement')
   if atom['kind']=='evidence' and not all(atom['source'][k] for k in ('uri','sha256')):raise ValueError('Cashflow evidence needs frozen source')
   if atom['unit']!=canonical_unit(path,atom['value']):raise ValueError('Invalid cashflow unit: '+path)
 elif 'class_cashflows' in data:raise ValueError('Class cashflows require explicit method selection')
 def put(path,value,unit='amount'):
  if not math.isfinite(value):raise ValueError('Nonfinite independent result: '+path)
  expected[path]=value;units[path]=unit;return value
 def value(s,k):return number(s[k])
 def check(path,v,unit='amount'):
  put('checks.'+path,v,unit)
  if not math.isclose(v,0,abs_tol=1e-7,rel_tol=0):issues.append({'code':'input_invariant','path':path,'difference':v})
 horizon=data['horizon'];stub=data['discount_timing']['value']=='explicit_stub'
 if type(horizon) is not int or horizon<1:raise ValueError('Explicit positive horizon required')
 times=[number(a) for a in data['timing']['time_to_cashflow']] if stub else list(range(1,horizon+1))
 terminal_time=number(data['timing']['terminal_time']) if stub else horizon
 if len(times)!=horizon or any(t<=0 for t in times) or any(b<=a for a,b in zip(times,times[1:])) or not math.isclose(terminal_time,times[-1],abs_tol=1e-12,rel_tol=0):raise ValueError('Explicit consistent cash-flow times required')
 industrial=data['industrial'];finance=data['finance'];c=data['consolidation']
 segment_ids=[s['id'] for s in industrial+finance];class_ids=[s['id'] for s in data['share_classes']]
 if len(segment_ids)!=len(set(segment_ids)) or len(class_ids)!=len(set(class_ids)):raise ValueError('Duplicate segment or class ID')
 for name,ik,fk,elim,control in [('revenue','revenue','revenue','revenue_eliminations','consolidated_revenue'),('ebit','reported_ebit','reported_ebit','ebit_eliminations','consolidated_ebit'),('debt','debt','funding_debt','debt_eliminations','consolidated_debt'),('cash','cash','cash','cash_eliminations','consolidated_cash')]:
  check(name,sum(value(s,ik) for s in industrial)+sum(value(s,fk) for s in finance)+value(c,elim)-value(c,control))
 check('finance_book',sum(value(s,'book_equity') for s in finance)+value(c,'finance_book_adjustment')-value(c,'consolidated_finance_book'))
 ischedules=[];fschedules=[]
 for s in industrial:
  q='industrial.'+s['id'];w=value(s,'wacc');growth=value(s,'terminal_growth');tax=value(s,'tax_rate');roic=value(s,'terminal_roic')
  if w<=growth or roic<=0:raise ValueError('Unsupported terminal denominator')
  rev=value(s,'revenue');nwc=rev*value(s,'opening_nwc_rate');flows=[];pvsum=0
  if len(s['forecast'])!=horizon-int(stub):raise ValueError('Forecast count mismatch')
  for i,t in enumerate(times):
   row=q+'.year'+str(i+1)
   if stub and i==0:
    st=s['stub'];rev=value(st,'revenue');ebit=value(st,'ebit');nopat=ebit-value(st,'cash_tax');da=value(st,'da');capex=value(st,'capex');dnwc=value(st,'delta_nwc');fcff=value(st,'fcff');check(s['id']+'_stub_fcff',fcff-(nopat+da-capex-dnwc));check(s['id']+'_stub_nwc',value(st,'closing_nwc')-value(st,'opening_nwc')-dnwc);nwc=value(st,'closing_nwc')
   else:
    f=s['forecast'][i-int(stub)];base=value(s['stub'],'full_year_revenue_anchor') if stub and i==1 else rev;rev=base*(1+value(f,'growth'));ebit=rev*value(f,'margin');nopat=ebit*(1-tax);da=rev*value(f,'da_rate');capex=rev*value(f,'capex_rate');close=rev*value(f,'nwc_rate');dnwc=close-nwc;nwc=close;fcff=nopat+da-capex-dnwc
   for k,v in [('revenue',rev),('ebit',ebit),('nopat',nopat),('da',da),('capex',capex),('delta_nwc',dnwc),('fcff',fcff)]:put(row+'.'+k,v)
   df=put(row+'.discount_factor',(1+w)**(-t),'ratio');pvsum+=put(row+'.pv',fcff*df);flows.append(fcff)
  tn=put(q+'.terminal_nopat',rev*(1+growth)*value(s,'terminal_margin')*(1-tax));reinvest=put(q+'.terminal_reinvestment',tn*growth/roic);terminal_fcff=put(q+'.terminal_fcff',tn-reinvest);tv=put(q+'.terminal_value',terminal_fcff/(w-growth));tpv=put(q+'.terminal_pv',tv/(1+w)**terminal_time);ev=put(q+'.enterprise_value',pvsum+tpv);lease=put(q+'.lease_deduction',value(s,'lease_liability') if s['lease_policy']['value']=='debt_like' else 0);eq=put(q+'.equity_value',ev+value(s,'cash')-value(s,'debt')-lease);nci=put(q+'.nci',eq*(1-value(s,'parent_ownership')));put(q+'.parent_equity',eq-nci)
  ischedules.append({'segment':s,'q':q,'flows':flows,'last_revenue':rev,'ev':ev})
  last=s['forecast'][-1] if s['forecast'] else None
  alternative=None
  if last:
   capital=rev*(1+growth)*(value(last,'capex_rate')-value(last,'da_rate'))+rev*value(last,'nwc_rate')*growth
   alternative={'reinvestment':capital,'terminal_pv':(tn-capital)/(w-growth)/(1+w)**terminal_time,'parent_equity_delta':((tn-capital)/(w-growth)/(1+w)**terminal_time-tpv)*value(s,'parent_ownership'),'adopted_forecast':False}
  diagnostics.append({'segment_id':s['id'],'terminal_pv_share_ev':tpv/ev if ev else None,'chosen_terminal_reinvestment':reinvest,'last_annual_reinvestment':capex-da+dnwc,'continued_selected_capital_intensity':alternative,'economic_judgment':'unreviewed; changed capital intensity is a diagnostic, not proof of error'})
 for s in finance:
  q='finance.'+s['id'];ke=value(s,'cost_equity');growth=value(s,'terminal_growth');book=value(s,'book_equity');pvsum=0;divpv=0;schedule=[]
  if ke<=growth or len(s['forecast'])!=horizon-int(stub):raise ValueError('Unsupported finance terminal or forecast count')
  for i,t in enumerate(times):
   row=q+'.year'+str(i+1);opening=book
   if stub and i==0:income=value(s['stub'],'income');div=value(s['stub'],'dividends')
   else:f=s['forecast'][i-int(stub)];income=opening*value(f,'roe');div=income*value(f,'payout')
   book=opening+income-div;charge=(1+ke)**(t-(times[i-1] if i else 0))-1 if stub else ke;ri=income-opening*charge
   for k,v in [('opening_book',opening),('income',income),('dividend',div),('closing_book',book),('residual_income',ri)]:put(row+'.'+k,v)
   pvsum+=put(row+'.pv',ri/(1+ke)**t);divpv+=div/(1+ke)**t;schedule.append((opening,income,div,book))
  tri=put(q+'.terminal_residual_income',book*(value(s,'terminal_roe')-ke));tv=put(q+'.terminal_value',tri/(ke-growth));tpv=put(q+'.terminal_pv',tv/(1+ke)**terminal_time);eq=put(q+'.equity_value',value(s,'book_equity')+pvsum+tpv);put(q+'.justified_terminal_pb',(value(s,'terminal_roe')-growth)/(ke-growth),'ratio');pb=put(q+'.pb_crosscheck',value(s,'book_equity')*value(s,'pb_multiple'));put(q+'.pb_difference',eq-pb);nci=put(q+'.nci',eq*(1-value(s,'parent_ownership')));put(q+'.parent_equity',eq-nci);fschedules.append({'segment':s,'q':q,'schedule':schedule,'book':book,'equity':eq})
  ddm=divpv+book*(value(s,'terminal_roe')-growth)/(ke-growth)/(1+ke)**terminal_time
  if not math.isclose(eq,ddm,abs_tol=1e-7,rel_tol=1e-10):issues.append({'code':'ri_dividend_roundtrip','segment':s['id'],'difference':eq-ddm})
 def sum_groups(groups,k):return sum(expected[z['q']+'.'+k] for z in groups)
 b=data['bridge'];ev=put('bridge.industrial_enterprise_value',sum_groups(ischedules,'enterprise_value'));feq=put('bridge.finance_equity',sum_groups(fschedules,'equity_value'));debt=put('bridge.industrial_debt',sum(value(s,'debt') for s in industrial));cash=put('bridge.industrial_cash',sum(value(s,'cash') for s in industrial));lease=put('bridge.industrial_leases',sum_groups(ischedules,'lease_deduction'));put('bridge.finance_funding_debt_excluded',sum(value(s,'funding_debt') for s in finance));nci=sum_groups(ischedules,'nci')+sum_groups(fschedules,'nci');extra=0
 if 'separately_valued_nci' in b:put('bridge.segment_nci',nci);extra=put('bridge.separately_valued_nci',value(b,'separately_valued_nci'));nci+=extra
 put('bridge.nci',nci);adj=value(b,'nonoperating_assets')-value(b,'parent_liabilities')+value(b,'industrial_ev_adjustment')+value(b,'finance_equity_adjustment');gross=put('bridge.pre_nci_equity',ev+feq+cash-debt-lease+adj);parent=put('bridge.parent_equity',gross-nci);check('bridge',parent-sum_groups(ischedules,'parent_equity')-sum_groups(fschedules,'parent_equity')-adj+extra)
 shares=[];claims=[];weights=[];scale=number(data['amount_scale']);market=[];all_quotes=True
 if scale<=0:raise ValueError('Positive amount scale required')
 for s in data['share_classes']:
  q='classes.'+s['id'];outstanding=value(s,'issued')-value(s,'treasury')
  if outstanding<=0:raise ValueError('Positive outstanding shares required')
  shares.append(put(q+'.outstanding',outstanding,'shares'))
  if not explicit_classes:claims.append(put(q+'.fixed_claim',outstanding*value(s,'fixed_claim_per_share')/scale));weights.append(put(q+'.weight',outstanding*value(s,'participation_weight'),'weighted_shares'))
  if 'market_price' in s:market.append(put(q+'.market_equity',outstanding*value(s,'market_price')/scale))
  else:all_quotes=False
 if explicit_classes:
  streams=data['class_cashflows'];end=put('classes.terminal_time',value(streams,'terminal_time'),'years');total=put('classes.terminal_total_claim',value(streams,'terminal_total_claim'))
  ids=[s['id'] for s in streams['classes']]
  if len(ids)!=len(set(ids)) or set(ids)!=set(class_ids):raise ValueError('Cashflow IDs must equal share class IDs')
  def read_events(rows):
   events={}
   for event in rows:
    t=value(event,'time');d=value(event,'distribution');c=value(event,'capital_contribution')
    if not 0<t<=end or t in events or min(d,c)<0:raise ValueError('Invalid or duplicate cashflow event')
    events[t]=(d,c)
   return events
  parent_events=read_events(streams['parent_events']);totals={t:[0.,0.] for t in parent_events};allocations=[];terminal_sum=0.
  parent_indices={value(e,'time'):j for j,e in enumerate(streams['parent_events'])}
  indexed={s['id']:s for s in streams['classes']}
  for i,share in enumerate(data['share_classes']):
   s=indexed[share['id']];q='classes.'+share['id'];rate=put(q+'.cost_equity',value(s,'cost_equity'),'ratio')
   if s['perimeter']!='existing_cutoff_holders' or rate<=0 or not s['rights_reference']['value'].strip() or not s['terminal_reference']['value'].strip():raise ValueError('Supported explicit rights and existing-holder scope required')
   own=read_events(s['events'])
   if set(own)!=set(parent_events):raise ValueError('Every class must supply every parent event')
   pv=0.
   for j,event in enumerate(s['events']):
    row=q+f'.event{j+1}';t=put(row+'.time',value(event,'time'),'years');d,c=own[t]
    parent_index=parent_indices[t];check(f'class_{share["id"]}_event{parent_index+1}_time',t-value(streams['parent_events'][parent_index],'time'),'years')
    put(row+'.distribution',d);put(row+'.capital_contribution',c);net=put(row+'.net',d-c);df=put(row+'.discount_factor',math.pow(1+rate,-t),'ratio');pv+=put(row+'.pv',net*df)
    totals[t][0]+=d;totals[t][1]+=c
   terminal=put(q+'.terminal_claim',value(s,'terminal_claim'));terminal_sum+=terminal
   tpv=put(q+'.terminal_pv',terminal*math.pow(1+rate,-end));eq=put(q+'.equity_value',pv+tpv);allocations.append(eq);put(q+'.per_share',eq*scale/shares[i],'currency_per_share')
  for j,event in enumerate(streams['parent_events']):
   t=value(event,'time')
   for k,metric in enumerate(('distribution','capital_contribution')):check(f'class_event{j+1}_{metric}',totals[t][k]-value(event,metric))
  check('class_terminal',terminal_sum-total);check('class_allocation',sum(allocations)-parent)
  for key,wanted in [('class_method','explicit_distribution_streams'),('class_cashflow_status','reconciled_unreviewed'),('sensitivity_scope','parent_equity_diagnostics_only_frozen_class_streams')]:
   if result.get(key)!=wanted:issues.append({'code':'result_header_mismatch','field':key})
 else:
  claim=put('classes.total_fixed_claim',sum(claims));available=put('classes.available_equity',max(parent,0));recovery=put('classes.fixed_recovery',min(available,claim));residual=put('classes.residual',max(available-claim,0));weight=put('classes.total_weight',sum(weights),'weighted_shares')
  if weight<=0 or claim<0:raise ValueError('Unsupported class weighting or fixed claim')
  allocations=[]
  for i,s in enumerate(data['share_classes']):
   q='classes.'+s['id'];eq=(recovery*claims[i]/claim if claim else 0)+residual*weights[i]/weight;allocations.append(put(q+'.equity_value',eq));put(q+'.per_share',eq*scale/shares[i],'currency_per_share')
  check('class_allocation',sum(allocations)-available)
 if all_quotes:
  market_eq=put('diagnostics.market_equity',sum(market));put('diagnostics.equity_gap',parent-market_eq);slope=0
  for z in ischedules:
   s=z['segment'];w=value(s,'wacc');g=value(s,'terminal_growth');revenues=[expected[z['q']+'.year'+str(i+1)+'.revenue'] for i in range(horizon)]
   slope+=value(s,'parent_ownership')*(1-value(s,'tax_rate'))*(sum(revenues[i]/(1+w)**times[i] for i in range(int(stub),horizon))+z['last_revenue']*(1+g)*(1-g/value(s,'terminal_roic'))/(w-g)/(1+w)**terminal_time)
  put('diagnostics.margin_slope',slope)
  if slope>0:
   shift=put('diagnostics.implied_margin_shift',(market_eq-parent)/slope,'ratio');put('diagnostics.reverse_repriced_equity',parent+shift*slope)
   for z in ischedules:put(z['q']+'.implied_terminal_margin',value(z['segment'],'terminal_margin')+shift,'ratio')
 for group,segments in [('industrial',ischedules),('finance',fschedules)]:
  if group=='finance' and not segments:continue
  for a in range(-2,3):
   for delta in range(-2,3):
    total=parent
    for z in segments:
     s=z['segment'];r=value(s,'wacc' if group=='industrial' else 'cost_equity')+a*value(data['sensitivity'],'discount_step')
     if group=='industrial':
      g=value(s,'terminal_growth')+delta*value(data['sensitivity'],'growth_step');cf=z['last_revenue']*(1+g)*value(s,'terminal_margin')*(1-value(s,'tax_rate'))*(1-g/value(s,'terminal_roic'));new=sum(flow/(1+r)**t for flow,t in zip(z['flows'],times))+cf/(r-g)/(1+r)**terminal_time;old=z['ev']
     else:
      g=value(s,'terminal_growth');roe=value(s,'terminal_roe')+delta*value(data['sensitivity'],'roe_step');new=value(s,'book_equity')
      for i,(opening,income,div,closing) in enumerate(z['schedule']):
       charge=(1+r)**(times[i]-(times[i-1] if i else 0))-1 if stub else r;new+=(income-opening*charge)/(1+r)**times[i]
      new+=z['book']*(roe-r)/(r-g)/(1+r)**terminal_time;old=z['equity']
     total+=(new-old)*value(s,'parent_ownership')
    put(f'sensitivity.{group}.r{a+2}c{delta+2}',total)
  check(group+'_sensitivity_center',expected[f'sensitivity.{group}.r2c2']-parent)
 if abs(parent)>1e-12:put('diagnostics.industrial_terminal_to_parent_equity',sum(expected[z['q']+'.terminal_pv']*value(z['segment'],'parent_ownership') for z in ischedules)/parent,'ratio')
 checks=[];reported=result.get('values',{})
 for p,v in expected.items():
  r=reported.get(p);ok=type(r) in (int,float) and math.isfinite(r) and math.isclose(v,r,rel_tol=1e-10,abs_tol=1e-7)
  safe_r=r if not isinstance(r,float) or math.isfinite(r) else repr(r)
  unit_ok=result.get('units',{}).get(p)==units[p];checks.append({'path':p,'expected':v,'reported':safe_r,'difference':r-v if type(r) in (int,float) and math.isfinite(r) else None,'status':'passed' if ok and unit_ok else 'failed','unit_matches':unit_ok})
  if not ok or not unit_ok:issues.append({'code':'result_mismatch','path':p,'expected':v,'reported':safe_r,'unit_matches':unit_ok})
 input_meta=dict(atoms(data));meta_ok=result.get('input_metadata')==input_meta
 if not meta_ok:issues.append({'code':'input_metadata_changed_or_incomplete'})
 headers={k:data[k] for k in ('company','synthetic','currency','valuation_date','horizon')}
 headers.update(amount_scale=scale,timing_mode=data['discount_timing']['value'],cashflow_times=times,terminal_time=terminal_time)
 for k,v in headers.items():
  if result.get(k)!=v:issues.append({'code':'result_header_mismatch','field':k})
 extras=sorted(set(reported)-set(expected))
 if extras:issues.append({'code':'unsupported_result_paths','paths':extras})
 return {'status':'failed' if issues else 'passed','scope':'Independent scalar arithmetic, not assumption plausibility, legal class rights or financial approval','checks':checks,'issues':issues,'input_metadata_matches':meta_ok,'checked_paths':len(checks),'reported_paths':len(reported),'unsupported_paths':extras,'terminal_diagnostics':diagnostics,'financial_approval':False,'economic_approval':False}

def audit_files(out,destination=None):
 out=Path(out).resolve();paths=[out/'valuation-input.json',out/'model-result.json']
 if any(not p.resolve().is_relative_to(out) for p in paths):raise ValueError('Audit input escaped attempt')
 raw=[p.read_bytes() for p in paths];data,result=[json.loads(r) for r in raw];receipt=audit_math(data,result);receipt['input_sha256']={p.name:hashlib.sha256(r).hexdigest() for p,r in zip(paths,raw)}
 if any(p.read_bytes()!=r for p,r in zip(paths,raw)):raise ValueError('Audit inputs changed during replay')
 if destination:
  with Path(destination).open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2,allow_nan=False)
 return receipt

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();r=audit_files(a.out,a.output);print(json.dumps({'status':r['status'],'checked_paths':r['checked_paths'],'issues':r['issues'][:8],'financial_approval':False},ensure_ascii=False));raise SystemExit(0 if r['status']=='passed' else 1)
