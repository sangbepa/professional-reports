"""Reusable allocated-equity residual income and independent dividend replay.

Inputs are analyst choices, not approved source facts or fair-value guarantees.
All income/distributions use the same already-attributable ownership perimeter.
"""
import math

def value_claim(*,book,stub_income,stub_dividend,stub_time,roe,payout,ke,g,terminal_roe):
 numbers=[book,stub_income,stub_dividend,stub_time,payout,ke,g,terminal_roe,*roe]
 if not roe or any(not math.isfinite(x) for x in numbers):raise ValueError('Finite explicit claim inputs required')
 if book<=0 or not 0<stub_time<=1 or not 0<=payout<=1 or ke<=0 or g>=ke or terminal_roe<=g or stub_dividend<0:
  raise ValueError('Unsupported equity claim assumptions')
 opening=book;closing=book+stub_income-stub_dividend
 if closing<=0:raise ValueError('Negative-book distress requires another method')
 schedule=[{'time':stub_time,'opening_book':opening,'income':stub_income,'dividend':stub_dividend,'closing_book':closing,'capital_charge':opening*((1+ke)**stub_time-1)}]
 for year,rate in enumerate(roe,1):
  opening=closing;income=opening*rate;dividend=max(income,0)*payout;closing=opening+income-dividend
  if closing<=0:raise ValueError('Negative-book distress requires another method')
  schedule.append({'time':stub_time+year,'opening_book':opening,'income':income,'dividend':dividend,'closing_book':closing,'capital_charge':opening*ke})
 pv_ri=sum((r['income']-r['capital_charge'])/(1+ke)**r['time'] for r in schedule)
 horizon=schedule[-1]['time'];terminal_ri=closing*(terminal_roe-ke)/(ke-g)/(1+ke)**horizon
 intrinsic=book+pv_ri+terminal_ri
 # Independently telescope actual distributions plus terminal equity, without
 # treating a negative residual-income term as a negative cash distribution.
 dividends=sum(r['dividend']/(1+ke)**r['time'] for r in schedule)
 terminal_dividend_equity=closing*(terminal_roe-g)/(ke-g)/(1+ke)**horizon
 ddm=dividends+terminal_dividend_equity
 return {'equity_value':intrinsic,'ddm_equity_value':ddm,'ri_ddm_difference':intrinsic-ddm,'schedule':schedule,'terminal_ri_pv':terminal_ri,'terminal_payout':1-g/terminal_roe,'scope':'Arithmetic only; attribution, clean-surplus, distribution/capital-call rights and forecasts need independent judgment'}
