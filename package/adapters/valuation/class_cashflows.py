"""Dated distributions to the existing valuation-date share-holder cohort.

No dividend, probability, terminal entitlement or discount rate is inferred
from liquidation rights or market discounts. Mismatches never become weights.
"""
import math

def finite(value,label):
 if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite '+label+' required')
 return value

def value_classes(*,classes,parent_events,parent_terminal_time,parent_terminal_claim,
 parent_equity_target,absolute_tolerance):
 target=finite(parent_equity_target,'parent target');tol=finite(absolute_tolerance,'explicit tolerance')
 terminal_time=finite(parent_terminal_time,'terminal time');terminal_total=finite(parent_terminal_claim,'parent terminal claim')
 if tol<0 or terminal_time<=0 or terminal_total<0:raise ValueError('Unsupported terminal claim or tolerance')
 if not isinstance(classes,list) or not classes:raise ValueError('Explicit dated class cashflows required')
 if not isinstance(parent_events,list):raise ValueError('Explicit parent owner-flow events required')
 def events(rows):
  result={}
  for r in rows:
   t=finite(r['time'],'event time');distribution=finite(r['distribution'],'distribution');capital=finite(r['capital_contribution'],'owner capital')
   if not 0<t<=terminal_time or t in result or min(distribution,capital)<0:raise ValueError('Duplicate/invalid owner-flow time or negative amount')
   result[t]={'distribution':distribution,'capital_contribution':capital,'net':distribution-capital}
  return result
 parent=events(parent_events);totals={t:{'distribution':0.,'capital_contribution':0.} for t in parent};seen=set();output=[];terminal_sum=0.
 for c in classes:
  identity=c['id'];issued=finite(c['issued'],'issued shares');treasury=finite(c['treasury'],'treasury shares');ke=finite(c['cost_equity'],'class discount rate');terminal=finite(c['terminal_claim'],'class terminal claim')
  if not isinstance(identity,str) or not identity or identity in seen:raise ValueError('Distinct explicit class identity required')
  seen.add(identity)
  if issued<=treasury or treasury<0 or ke<=0 or terminal<0:raise ValueError('Positive outstanding shares/rate and nonnegative claim required')
  if c.get('perimeter')!='existing_cutoff_holders' or not c.get('rights_reference') or not c.get('terminal_reference'):raise ValueError('Current-holder perimeter and going-concern rights/terminal references required')
  own=events(c['events'])
  if set(own)!=set(parent):raise ValueError('Every parent event needs explicit class flows, including zero')
  schedule=[];pv=0.
  for t,e in own.items():
   for key in ('distribution','capital_contribution'):totals[t][key]+=e[key]
   p=e['net']/(1+ke)**t;pv+=p;schedule.append(dict(time=t,**e,pv=p))
  terminal_pv=terminal/(1+ke)**terminal_time;value=pv+terminal_pv;terminal_sum+=terminal
  output.append({'id':identity,'outstanding':issued-treasury,'schedule':sorted(schedule,key=lambda r:r['time']),
   'terminal_claim':terminal,'terminal_pv':terminal_pv,'equity_value':value,'per_share':value/(issued-treasury),
   'rights_reference':c['rights_reference'],'terminal_reference':c['terminal_reference'],'cost_equity':ke})
 checks=[]
 for t,e in parent.items():
  for key in ('distribution','capital_contribution'):
   diff=totals[t][key]-e[key];checks.append({'time':t,'metric':key,'difference':diff,'passed':abs(diff)<=tol})
 diff=terminal_sum-terminal_total;checks.append({'metric':'terminal_claim','difference':diff,'passed':abs(diff)<=tol})
 aggregate=sum(c['equity_value'] for c in output);difference=aggregate-target
 checks.append({'metric':'parent_equity_target','difference':difference,'passed':abs(difference)<=tol})
 return {'kind':'explicit_class_cashflows_not_approval','status':'reconciled_unreviewed' if all(c['passed'] for c in checks) else 'unreconciled',
  'classes':output,'aggregate_class_equity':aggregate,'parent_equity_target':target,'absolute_tolerance':tol,'checks':checks,
  'financial_approval':False,'economic_approval':False,'inferred_participation_weights':False,
  'limitations':'Caller must substantiate declaration contingencies, probability-weighted owner flows, dividend capacity, funding, terminal continuing rights, class rates and dilution. Cashflow arithmetic does not establish legal rights or a fair value. Unreconciled classes cannot authorize a completed report.'}
