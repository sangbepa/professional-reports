"""Field units from the fixed model contract, never inferred source conversion."""
RATIO_FIELDS=frozenset(('opening_nwc_rate','growth','margin','da_rate','capex_rate','nwc_rate','parent_ownership','wacc',
 'terminal_growth','terminal_margin','terminal_roic','tax_rate','roe','payout','cost_equity','terminal_roe','pb_multiple',
 'participation_weight','discount_step','growth_step','roe_step'))

def canonical_unit(path,value):
 if not isinstance(value,(int,float)) or isinstance(value,bool):return 'text'
 key=path.split('.')[-1]
 if path.startswith('timing.time_to_cashflow.') or path=='timing.terminal_time':return 'years'
 if path.startswith('class_cashflows.') and key in ('time','terminal_time'):return 'years'
 if key in RATIO_FIELDS:return 'ratio'
 if key in ('issued','treasury'):return 'shares'
 if key in ('fixed_claim_per_share','market_price'):return 'currency_per_share'
 if key=='amount_scale':return 'currency_per_amount'
 return 'amount'

def describe_units():
 return {'numeric_ratio_fields':sorted(RATIO_FIELDS),'shares':['issued','treasury'],
  'currency_per_share':['fixed_claim_per_share','market_price'],'currency_per_amount':['amount_scale'],
  'years':['timing.time_to_cashflow.*','timing.terminal_time','class_cashflows.terminal_time','class_cashflows.parent_events.*.time','class_cashflows.classes.*.events.*.time'],'other_numeric':'amount','text':'text',
  'scope':'Canonical model field units only; original observation units/scales remain explicit and separately normalized.'}
