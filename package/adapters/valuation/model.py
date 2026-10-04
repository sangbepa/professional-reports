"""Deterministic expression graph shared by result JSON and editable XLSX.

Annual year-end FCFF; sustainable terminal reinvestment g/ROIC. Finance is
valued directly to equity under clean surplus, with an independent supplied P/B
crosscheck. All group adjustments are explicit parent-attributable inputs.
"""
from dataclasses import dataclass
import math
try:from .input_units import canonical_unit
except ImportError:from input_units import canonical_unit

try:
    from .schema_tools import validate_schema, leaves
except ImportError:
    from schema_tools import validate_schema, leaves


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple
    def __add__(self, other): return Expr('+', (self, expr(other)))
    def __radd__(self, other): return expr(other) + self
    def __sub__(self, other): return Expr('-', (self, expr(other)))
    def __rsub__(self, other): return expr(other) - self
    def __mul__(self, other): return Expr('*', (self, expr(other)))
    def __rmul__(self, other): return expr(other) * self
    def __truediv__(self, other): return Expr('/', (self, expr(other)))
    def __rtruediv__(self, other): return expr(other) / self
    def __pow__(self, other): return Expr('^', (self, expr(other)))
    def __neg__(self): return 0-self


def expr(value):
    return value if isinstance(value, Expr) else Expr('literal', (value,))


def maximum(a,b): return Expr('MAX', (expr(a),expr(b)))
def minimum(a,b): return Expr('MIN', (expr(a),expr(b)))


class Graph:
    def __init__(self, data):
        self.nodes = {}
        self.sheets = {}
        for path, item in leaves(data):
            if isinstance(item['value'], (int,float)):
                self.add('input.'+path, item['value'], 'Inputs', item['unit'], path, metadata=item)

    def ref(self, path):
        if path not in self.nodes: raise KeyError(path)
        return Expr('ref',(path,))

    def evaluate(self, expression):
        if expression.op=='literal': return expression.args[0]
        if expression.op=='ref': return self.nodes[expression.args[0]]['value']
        a,b=(self.evaluate(x) for x in expression.args)
        return {'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:a/b,
                '^':lambda:a**b,'MAX':lambda:max(a,b),'MIN':lambda:min(a,b)}[expression.op]()

    def add(self, path, expression, sheet, unit='amount', label=None, metadata=None):
        if path in self.nodes: raise ValueError('Duplicate calculation path '+path)
        expression=expr(expression)
        value=self.evaluate(expression)
        if not math.isfinite(value): raise ValueError('Non-finite calculation '+path)
        row=len(self.sheets.setdefault(sheet,[]))+5
        node=dict(path=path,value=value,expression=expression,sheet=sheet,cell=f'B{row}',
                  unit=unit,label=label or path,metadata=metadata)
        self.nodes[path]=node
        self.sheets[sheet].append(path)
        return self.ref(path)

    def formula(self, expression):
        if expression.op=='literal': return str(expression.args[0])
        if expression.op=='ref':
            node=self.nodes[expression.args[0]]
            return f"'{node['sheet']}'!{node['cell']}"
        a,b=(self.formula(x) for x in expression.args)
        if expression.op in ('MAX','MIN'): return f'{expression.op}({a},{b})'
        return f'({a}{expression.op}{b})'

    def value(self, path): return self.nodes[path]['value']

    def serializable(self):
        return {path:{k:v for k,v in node.items() if k!='expression'} |
                {'formula':None if node['metadata'] else '='+self.formula(node['expression'])}
                for path,node in self.nodes.items()}


def validate(data):
    validate_schema(data)
    explicit_classes=data['class_rights']['value']=='explicit_distribution_streams'
    if explicit_classes:
        if 'class_cashflows' not in data:
            raise ValueError('Explicit class_cashflows required for explicit_distribution_streams')
        streams=data['class_cashflows']
        identities=[c['id'] for c in streams['classes']]
        if len(identities)!=len(set(identities)) or set(identities)!={c['id'] for c in data['share_classes']}:
            raise ValueError('Explicit cashflow class IDs must match share_classes exactly')
        end=streams['terminal_time']['value']
        def event_times(rows):
            times=[e['time']['value'] for e in rows]
            if len(times)!=len(set(times)) or any(not 0<t<=end for t in times):
                raise ValueError('Duplicate or invalid class owner event time')
            return set(times)
        parent_times=event_times(streams['parent_events'])
        for c in streams['classes']:
            if event_times(c['events'])!=parent_times:
                raise ValueError('Every parent event needs explicit class flows, including zero')
    else:
        if 'class_cashflows' in data:
            raise ValueError('class_cashflows requires explicit_distribution_streams selection')
        if any(not all(k in c for k in ('participation_weight','fixed_claim_per_share')) for c in data['share_classes']):
            raise ValueError('Legacy class rights require participation_weight and fixed_claim_per_share')
    stub=data['discount_timing']['value']=='explicit_stub'
    if stub:
        if not f"{data['base_year']}-12-31" < data['valuation_date'] < f"{data['base_year']+1}-12-31":
            raise ValueError('Explicit stub cutoff must fall inside the first forecast fiscal year')
        if data['horizon']<2 or 'timing' not in data:
            raise ValueError('Explicit stub needs timing and at least one subsequent full annual forecast')
        times=[x['value'] for x in data['timing']['time_to_cashflow']]
        if len(times)!=data['horizon'] or not 0<times[0]<1 or any(b<=a for a,b in zip(times,times[1:])):
            raise ValueError('Explicit times must match horizon, start within one year, and increase strictly')
        if not math.isclose(data['timing']['terminal_time']['value'],times[-1],abs_tol=1e-12,rel_tol=0):
            raise ValueError('Terminal time must equal the last forecast cash-flow time')
    elif data['valuation_date'] != f"{data['base_year']}-12-31" or 'timing' in data:
        raise ValueError('Non-year-end cutoffs require explicit_stub and explicit cash flows/times')
    for path,item in leaves(data):
        if item['as_of']>data['valuation_date']: raise ValueError(path+': input after cutoff')
        if item['review']['status']=='rejected': raise ValueError(path+': rejected input')
        if item['review']['status']=='reviewed' and not all(item['review'][x] for x in ('reviewer','reference')):
            raise ValueError(path+': reviewed metadata needs reviewer and reference')
        if item['kind']=='evidence' and (not item['source']['sha256'] or not item['source']['uri']):
            raise ValueError(path+': evidence needs frozen source hash and URI')
        if item['kind']=='synthetic' and not data['synthetic']:
            raise ValueError(path+': synthetic input requires synthetic engagement label')
        if isinstance(item['value'],(int,float)):
            expected=canonical_unit(path,item['value'])
            if item['unit']!=expected: raise ValueError(f'{path}: unit must be {expected}')
    ids=[s['id'] for s in data['industrial']+data['finance']]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate segment ID')
    ids=[s['id'] for s in data['share_classes']]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate class ID')
    v=lambda obj,key:obj[key]['value']
    ds=v(data['sensitivity'],'discount_step')*2
    gs=v(data['sensitivity'],'growth_step')*2
    rs=v(data['sensitivity'],'roe_step')*2
    for group in ('industrial','finance'):
        for seg in data[group]:
            if len(seg['forecast'])!=data['horizon']-int(stub):
                raise ValueError('Annual forecast count must equal horizon minus explicit stub period')
            if stub and 'stub' not in seg:raise ValueError('Each segment requires explicit stub inputs')
            if not stub and 'stub' in seg:raise ValueError('Stub inputs require explicit_stub mode')
            if stub:
                if group=='industrial' and any(v(seg['stub'],k)<0 for k in ('revenue','da','capex')):
                    raise ValueError('Stub revenue, D&A and capex must be nonnegative')
                if group=='finance' and v(seg,'book_equity')+v(seg['stub'],'income')-v(seg['stub'],'dividends')<=0:
                    raise ValueError('Finance stub must leave positive book equity')
            discount=v(seg,'wacc' if group=='industrial' else 'cost_equity')
            growth=v(seg,'terminal_growth')
            if discount-ds<=0 or discount-ds<=growth+(gs if group=='industrial' else 0):
                raise ValueError('Discount must exceed terminal growth throughout sensitivity grid')
            if growth<0: raise ValueError('Negative perpetual growth unsupported by sustainable reinvestment model')
            if group=='industrial':
                if v(seg,'terminal_margin')<0:
                    raise ValueError('Normalized terminal EBIT margin must be nonnegative')
                if growth+gs>v(seg,'terminal_roic') or growth-gs<0:
                    raise ValueError('Terminal growth sensitivity must be within [0, ROIC]')
                for f in seg['forecast']:
                    if v(f,'growth')<=-1 or any(v(f,k)<0 for k in ('da_rate','capex_rate')):
                        raise ValueError('Invalid operating drivers')
            elif growth>v(seg,'terminal_roe')-rs:
                raise ValueError('Terminal ROE must support growth throughout sensitivity grid')
    for cls in data['share_classes']:
        if v(cls,'issued')<=v(cls,'treasury'): raise ValueError('Outstanding shares must be positive')
    if not explicit_classes and sum((v(c,'issued')-v(c,'treasury'))*v(c,'participation_weight') for c in data['share_classes'])<=0:
        raise ValueError('At least one outstanding class must participate in residual equity')
    if v(data['bridge'],'nonoperating_assets')<0 or v(data['bridge'],'parent_liabilities')<0:
        raise ValueError('Assets and liabilities are positive balances, not signed adjustments')
    if 'separately_valued_nci' in data['bridge'] and v(data['bridge'],'separately_valued_nci')<0:
        raise ValueError('Separately valued NCI is a positive equity deduction')


def _class_stream_graph(data,g,parent,classes):
    """Bind declared existing-holder streams to Inputs, with no allocation plug."""
    I=lambda path:g.ref('input.class_cashflows.'+path)
    C=g.add
    end=C('classes.terminal_time',I('terminal_time'),'Classes','years')
    terminal_total=C('classes.terminal_total_claim',I('terminal_total_claim'),'Classes')
    stream_indices={c['id']:j for j,c in enumerate(data['class_cashflows']['classes'])}
    parent_indices={e['time']['value']:j for j,e in enumerate(data['class_cashflows']['parent_events'])}
    def reconcile(path,expression,unit='amount'):
        diff=C('checks.'+path,expression,'Checks',unit)
        if not math.isclose(g.evaluate(diff),0,abs_tol=1e-7,rel_tol=0):
            raise ValueError('Unreconciled explicit class cashflows '+path+': '+str(g.evaluate(diff)))
    terminal_claims=[];values=[];flow_totals={}
    for cls in classes:
        j=stream_indices[cls['id']];stream=data['class_cashflows']['classes'][j]
        p=f'classes.{j}';q=cls['path'];present=[];rows=[]
        rate=C(q+'.cost_equity',I(p+'.cost_equity'),'Classes','ratio')
        for k,event in enumerate(stream['events']):
            row=q+f'.event{k+1}';base=p+f'.events.{k}'
            t=C(row+'.time',I(base+'.time'),'Classes','years')
            parent_index=parent_indices[event['time']['value']]
            reconcile(f'class_{cls["id"]}_event{parent_index+1}_time',t-I(f'parent_events.{parent_index}.time'),'years')
            distribution=C(row+'.distribution',I(base+'.distribution'),'Classes')
            capital=C(row+'.capital_contribution',I(base+'.capital_contribution'),'Classes')
            net=C(row+'.net',distribution-capital,'Classes')
            df=C(row+'.discount_factor',1/(1+rate)**t,'Classes','ratio')
            present.append(C(row+'.pv',net*df,'Classes'))
            flow_totals.setdefault(event['time']['value'],{'distribution':[],'capital_contribution':[]})
            flow_totals[event['time']['value']]['distribution'].append(distribution)
            flow_totals[event['time']['value']]['capital_contribution'].append(capital)
            rows.append(dict(path=row))
        claim=C(q+'.terminal_claim',I(p+'.terminal_claim'),'Classes')
        terminal_claims.append(claim)
        terminal_pv=C(q+'.terminal_pv',claim/(1+rate)**end,'Classes')
        equity=C(q+'.equity_value',sum(present,expr(0))+terminal_pv,'Classes')
        values.append(equity)
        C(q+'.per_share',equity*g.ref('input.amount_scale')/g.ref(q+'.outstanding'),'Classes','currency_per_share')
        cls.update(events=rows,rights_reference=stream['rights_reference']['value'],
                   terminal_reference=stream['terminal_reference']['value'],perimeter=stream['perimeter'])
    for j,event in enumerate(data['class_cashflows']['parent_events']):
        for metric in ('distribution','capital_contribution'):
            reconcile(f'class_event{j+1}_{metric}',sum(flow_totals[event['time']['value']][metric],expr(0))-I(f'parent_events.{j}.{metric}'))
    reconcile('class_terminal',sum(terminal_claims,expr(0))-terminal_total)
    reconcile('class_allocation',sum(values,expr(0))-parent)


def calculate(data):
    validate(data)
    g=Graph(data)
    I=lambda path:g.ref('input.'+path)
    C=g.add
    n=data['horizon']
    stub=data['discount_timing']['value']=='explicit_stub'
    time=lambda t:I(f'timing.time_to_cashflow.{t-1}') if stub else expr(t)
    terminal_time=I('timing.terminal_time') if stub else expr(n)
    # Declared effective compounding; supplied cash flows are never prorated.
    charge=lambda rate,t:(1+rate)**(time(t)-(time(t-1) if t>1 else 0))-1 if stub else rate
    industrial=[]; finance=[]
    # Reconciliations are checks against supplied consolidated controls, never plugs.
    for metric,ik,fk,ek,control in [
        ('revenue','revenue','revenue','revenue_eliminations','consolidated_revenue'),
        ('ebit','reported_ebit','reported_ebit','ebit_eliminations','consolidated_ebit'),
        ('debt','debt','funding_debt','debt_eliminations','consolidated_debt'),
        ('cash','cash','cash','cash_eliminations','consolidated_cash')]:
        total=sum((I(f'industrial.{j}.{ik}') for j in range(len(data['industrial']))),expr(0))
        total+=sum((I(f'finance.{j}.{fk}') for j in range(len(data['finance']))),expr(0))
        diff=C('checks.'+metric,total+I('consolidation.'+ek)-I('consolidation.'+control),'Checks')
        if not math.isclose(g.evaluate(diff),0,abs_tol=1e-7): raise ValueError(f'Unreconciled consolidated {metric}: {g.evaluate(diff)}')
    book=sum((I(f'finance.{j}.book_equity') for j in range(len(data['finance']))),expr(0))
    diff=C('checks.finance_book',book+I('consolidation.finance_book_adjustment')-I('consolidation.consolidated_finance_book'),'Checks')
    if not math.isclose(g.evaluate(diff),0,abs_tol=1e-7): raise ValueError('Unreconciled finance book equity')

    for j,s in enumerate(data['industrial']):
        p=f'industrial.{j}'; q=f'industrial.{s["id"]}'; at=lambda k:I(p+'.'+k)
        revenue=at('revenue'); pv=[]; rows=[]
        previous_nwc=revenue*at('opening_nwc_rate')
        for t in range(1,n+1):
            row=f'{q}.year{t}'
            if stub and t==1:
                revenue=C(row+'.revenue',at('stub.revenue'),'Industrial')
                ebit=C(row+'.ebit',at('stub.ebit'),'Industrial')
                nopat=C(row+'.nopat',ebit-at('stub.cash_tax'),'Industrial')
                da=C(row+'.da',at('stub.da'),'Industrial')
                capex=C(row+'.capex',at('stub.capex'),'Industrial')
                dnwc=C(row+'.delta_nwc',at('stub.delta_nwc'),'Industrial')
                fcff=C(row+'.fcff',at('stub.fcff'),'Industrial')
                diff=C('checks.'+s['id']+'_stub_fcff',fcff-(nopat+da-capex-dnwc),'Checks')
                if not math.isclose(g.evaluate(diff),0,abs_tol=1e-7):raise ValueError('Unreconciled explicit stub FCFF: '+s['id'])
                diff=C('checks.'+s['id']+'_stub_nwc',at('stub.closing_nwc')-at('stub.opening_nwc')-dnwc,'Checks')
                if not math.isclose(g.evaluate(diff),0,abs_tol=1e-7):raise ValueError('Unreconciled explicit stub NWC: '+s['id'])
                previous_nwc=at('stub.closing_nwc')
            else:
                base=f'{p}.forecast.{t-1-int(stub)}'
                old_rev=at('stub.full_year_revenue_anchor') if stub and t==2 else revenue
                revenue=C(row+'.revenue',old_rev*(1+I(base+'.growth')),'Industrial')
                ebit=C(row+'.ebit',revenue*I(base+'.margin'),'Industrial')
                nopat=C(row+'.nopat',ebit*(1-at('tax_rate')),'Industrial')
                da=C(row+'.da',revenue*I(base+'.da_rate'),'Industrial')
                capex=C(row+'.capex',revenue*I(base+'.capex_rate'),'Industrial')
                closing_nwc=revenue*I(base+'.nwc_rate')
                dnwc=C(row+'.delta_nwc',closing_nwc-previous_nwc,'Industrial')
                previous_nwc=closing_nwc
                fcff=C(row+'.fcff',nopat+da-capex-dnwc,'Industrial')
            df=C(row+'.discount_factor',1/(1+at('wacc'))**time(t),'Industrial','ratio')
            pv.append(C(row+'.pv',fcff*df,'Industrial'))
            rows.append(dict(year=data['base_year']+t,period='explicit stub' if stub and t==1 else 'annual',
                             time=g.evaluate(time(t)),path=row))
        terminal_nopat=C(q+'.terminal_nopat',revenue*(1+at('terminal_growth'))*at('terminal_margin')*(1-at('tax_rate')),'Industrial')
        terminal_reinvestment=C(q+'.terminal_reinvestment',terminal_nopat*at('terminal_growth')/at('terminal_roic'),'Industrial')
        terminal_fcff=C(q+'.terminal_fcff',terminal_nopat-terminal_reinvestment,'Industrial')
        tv=C(q+'.terminal_value',terminal_fcff/(at('wacc')-at('terminal_growth')),'Industrial')
        tpv=C(q+'.terminal_pv',tv/(1+at('wacc'))**terminal_time,'Industrial')
        ev=C(q+'.enterprise_value',sum(pv,expr(0))+tpv,'Industrial')
        lease=C(q+'.lease_deduction',at('lease_liability') if s['lease_policy']['value']=='debt_like' else expr(0),'Industrial')
        eq=C(q+'.equity_value',ev+at('cash')-at('debt')-lease,'Industrial')
        nci=C(q+'.nci',eq*(1-at('parent_ownership')),'Industrial')
        C(q+'.parent_equity',eq-nci,'Industrial')
        industrial.append(dict(id=s['id'],name=s['name'],path=q,rows=rows,lease_policy=s['lease_policy']['value']))

    for j,s in enumerate(data['finance']):
        p=f'finance.{j}'; q=f'finance.{s["id"]}'; at=lambda k:I(p+'.'+k)
        book=at('book_equity'); pv=[]; rows=[]
        for t in range(1,n+1):
            row=f'{q}.year{t}'
            start=C(row+'.opening_book',book,'Finance')
            if stub and t==1:
                income=C(row+'.income',at('stub.income'),'Finance')
                div=C(row+'.dividend',at('stub.dividends'),'Finance')
            else:
                base=f'{p}.forecast.{t-1-int(stub)}'
                income=C(row+'.income',start*I(base+'.roe'),'Finance')
                div=C(row+'.dividend',income*I(base+'.payout'),'Finance')
            book=C(row+'.closing_book',start+income-div,'Finance')
            ri=C(row+'.residual_income',income-start*charge(at('cost_equity'),t),'Finance')
            pv.append(C(row+'.pv',ri/(1+at('cost_equity'))**time(t),'Finance'))
            rows.append(dict(year=data['base_year']+t,period='explicit stub' if stub and t==1 else 'annual',
                             time=g.evaluate(time(t)),path=row))
        tri=C(q+'.terminal_residual_income',book*(at('terminal_roe')-at('cost_equity')),'Finance')
        tv=C(q+'.terminal_value',tri/(at('cost_equity')-at('terminal_growth')),'Finance')
        tpv=C(q+'.terminal_pv',tv/(1+at('cost_equity'))**terminal_time,'Finance')
        equity=C(q+'.equity_value',at('book_equity')+sum(pv,expr(0))+tpv,'Finance')
        C(q+'.justified_terminal_pb',(at('terminal_roe')-at('terminal_growth'))/(at('cost_equity')-at('terminal_growth')),'Finance','ratio')
        pb=C(q+'.pb_crosscheck',at('book_equity')*at('pb_multiple'),'Finance')
        C(q+'.pb_difference',equity-pb,'Finance')
        nci=C(q+'.nci',equity*(1-at('parent_ownership')),'Finance')
        C(q+'.parent_equity',equity-nci,'Finance')
        finance.append(dict(id=s['id'],name=s['name'],path=q,rows=rows))

    S=lambda group,metric:sum((g.ref(x['path']+'.'+metric) for x in group),expr(0))
    ev=C('bridge.industrial_enterprise_value',S(industrial,'enterprise_value'),'Bridge')
    feq=C('bridge.finance_equity',S(finance,'equity_value'),'Bridge')
    debt=C('bridge.industrial_debt',sum((I(f'industrial.{j}.debt') for j in range(len(industrial))),expr(0)),'Bridge')
    cash=C('bridge.industrial_cash',sum((I(f'industrial.{j}.cash') for j in range(len(industrial))),expr(0)),'Bridge')
    lease=C('bridge.industrial_leases',S(industrial,'lease_deduction'),'Bridge')
    C('bridge.finance_funding_debt_excluded',sum((I(f'finance.{j}.funding_debt') for j in range(len(finance))),expr(0)),'Bridge')
    has_separate_nci='separately_valued_nci' in data['bridge']
    if has_separate_nci:
        segment_nci=C('bridge.segment_nci',S(industrial,'nci')+S(finance,'nci'),'Bridge')
        separate_nci=C('bridge.separately_valued_nci',I('bridge.separately_valued_nci'),'Bridge')
        nci=C('bridge.nci',segment_nci+separate_nci,'Bridge')
    else:
        # Preserve the exact legacy graph/cell/formula contract when this method
        # is absent; absence does not create a new valuation assumption.
        nci=C('bridge.nci',S(industrial,'nci')+S(finance,'nci'),'Bridge')
    adj=I('bridge.nonoperating_assets')-I('bridge.parent_liabilities')+I('bridge.industrial_ev_adjustment')+I('bridge.finance_equity_adjustment')
    gross=C('bridge.pre_nci_equity',ev+feq+cash-debt-lease+adj,'Bridge')
    parent=C('bridge.parent_equity',gross-nci,'Bridge')
    check=parent-S(industrial,'parent_equity')-S(finance,'parent_equity')-adj
    C('checks.bridge',check+separate_nci if has_separate_nci else check,'Checks')

    classes=[]; claims=[]; weights=[]; market=[]
    explicit_classes=data['class_rights']['value']=='explicit_distribution_streams'
    for j,s in enumerate(data['share_classes']):
        p=f'share_classes.{j}'; q='classes.'+s['id']
        shares=C(q+'.outstanding',I(p+'.issued')-I(p+'.treasury'),'Classes','shares')
        if not explicit_classes:
            claims.append(C(q+'.fixed_claim',shares*I(p+'.fixed_claim_per_share')/I('amount_scale'),'Classes'))
            weights.append(C(q+'.weight',shares*I(p+'.participation_weight'),'Classes','weighted_shares'))
        if 'market_price' in s:
            market.append(C(q+'.market_equity',shares*I(p+'.market_price')/I('amount_scale'),'Classes'))
        classes.append(dict(id=s['id'],path=q))
    if explicit_classes:
        _class_stream_graph(data,g,parent,classes)
    else:
        claim=C('classes.total_fixed_claim',sum(claims,expr(0)),'Classes')
        available=C('classes.available_equity',maximum(parent,0),'Classes')
        recovery=C('classes.fixed_recovery',minimum(available,claim),'Classes')
        residual=C('classes.residual',maximum(available-claim,0),'Classes')
        weight=C('classes.total_weight',sum(weights,expr(0)),'Classes','weighted_shares')
        for j,s in enumerate(classes):
            q=s['path']
            # MAX denominator avoids a zero-claims branch; all fixed claims are nonnegative.
            fixed=recovery*claims[j]/maximum(claim,1e-100)
            eq=C(q+'.equity_value',fixed+residual*weights[j]/weight,'Classes')
            C(q+'.per_share',eq*I('amount_scale')/g.ref(q+'.outstanding'),'Classes','currency_per_share')
        C('checks.class_allocation',S(classes,'equity_value')-available,'Checks')
    missing_quotes=[s['id'] for s in data['share_classes'] if 'market_price' not in s]
    market_available=not missing_quotes
    quote_reasons=[]
    for s in data['share_classes']:
        quote=s.get('market_price')
        if quote is None:
            quote_reasons.append(s['id']+': missing market_price')
        elif quote['as_of']!=data['valuation_date']:
            quote_reasons.append(s['id']+': quote date differs from valuation date')
        elif quote['value']<=0:
            quote_reasons.append(s['id']+': quote is not a positive market price')
        elif quote['kind']!='evidence' or data['synthetic']:
            quote_reasons.append(s['id']+': quote is not actual sourced market evidence')
    reverse_available=False
    if market_available:
        target=C('diagnostics.market_equity',sum(market,expr(0)),'Diagnostics')
        C('diagnostics.equity_gap',parent-target,'Diagnostics')
        # Exact additive change in EVERY industrial forecast and terminal EBIT margin.
        slope=expr(0)
        for j,s in enumerate(industrial):
            p=f'industrial.{j}'; q=s['path']
            slope+=I(p+'.parent_ownership')*(1-I(p+'.tax_rate'))*(
                sum((g.ref(f'{q}.year{t}.revenue')/(1+I(p+'.wacc'))**time(t) for t in range(2 if stub else 1,n+1)),expr(0))+
                g.ref(f'{q}.year{n}.revenue')*(1+I(p+'.terminal_growth'))*(1-I(p+'.terminal_growth')/I(p+'.terminal_roic'))/
                (I(p+'.wacc')-I(p+'.terminal_growth'))/(1+I(p+'.wacc'))**terminal_time)
        slope=C('diagnostics.margin_slope',slope,'Diagnostics')
        reverse_available=g.evaluate(slope)>0
        if reverse_available:
            shift=C('diagnostics.implied_margin_shift',(target-parent)/slope,'Diagnostics','ratio')
            C('diagnostics.reverse_repriced_equity',parent+shift*slope,'Diagnostics')
            for j,s in enumerate(industrial):
                C(s['path']+'.implied_terminal_margin',I(f'industrial.{j}.terminal_margin')+shift,'Diagnostics','ratio')
    # 5x5 full formula recalculations, centered on unchanged base assumptions.
    grids={}
    for grid in ['industrial','finance']:
        if grid=='finance' and not finance: continue
        rows=[]
        for a in range(-2,3):
            row=[]
            for b in range(-2,3):
                value=parent
                for j,s in enumerate(industrial if grid=='industrial' else finance):
                    p=f'{grid}.{j}'; q=s['path']
                    r=I(p+('.wacc' if grid=='industrial' else '.cost_equity'))+a*I('sensitivity.discount_step')
                    if grid=='industrial':
                        growth=I(p+'.terminal_growth')+b*I('sensitivity.growth_step')
                        fcff=g.ref(f'{q}.year{n}.revenue')*(1+growth)*I(p+'.terminal_margin')*(1-I(p+'.tax_rate'))*(1-growth/I(p+'.terminal_roic'))
                        value_change=sum((g.ref(f'{q}.year{t}.fcff')/(1+r)**time(t) for t in range(1,n+1)),expr(0))+fcff/(r-growth)/(1+r)**terminal_time-g.ref(q+'.enterprise_value')
                    else:
                        roe=I(p+'.terminal_roe')+b*I('sensitivity.roe_step')
                        equity=I(p+'.book_equity')+sum(((g.ref(f'{q}.year{t}.income')-g.ref(f'{q}.year{t}.opening_book')*charge(r,t))/(1+r)**time(t) for t in range(1,n+1)),expr(0))
                        equity+=g.ref(f'{q}.year{n}.closing_book')*(roe-r)/(r-I(p+'.terminal_growth'))/(1+r)**terminal_time
                        value_change=equity-g.ref(q+'.equity_value')
                    value+=value_change*I(p+'.parent_ownership')
                path=f'sensitivity.{grid}.r{a+2}c{b+2}'
                C(path,value,'Sensitivity')
                row.append(path)
            rows.append(row)
        grids[grid]=rows
        C('checks.'+grid+'_sensitivity_center',g.ref(rows[2][2])-parent,'Checks')
    if abs(g.evaluate(parent))>1e-12:
        terminal=sum((g.ref(s['path']+'.terminal_pv')*I(f'industrial.{j}.parent_ownership') for j,s in enumerate(industrial)),expr(0))
        C('diagnostics.industrial_terminal_to_parent_equity',terminal/parent,'Diagnostics','ratio')
    warnings=[
        'Conditional model only. Source truth, financial methods, legal class rights and assumptions are not independently reviewed.',
        'Historical consolidation controls do not prove attribution of forecast eliminations; parent-level valuation adjustments require evidence.',
        'Terminal industrial reinvestment equals g/ROIC times NOPAT; terminal finance book grows at g with ROE applied to opening book.',
        'Finance funding debt and cash remain inside book equity and ROE; never deducted again from industrial enterprise value.',
        'Annual forecast tax losses receive immediate modeled tax benefits; explicit stubs use supplied cash taxes. No tax-loss carryforward, capital adequacy or regulatory payout schedule is modeled.',
        'Class allocation supports pari passu fixed claims then weighted residual only; no seniority, conversion, cumulative dividends or options.']
    if explicit_classes:
        warnings[-1]='Explicit distribution streams value dated distributions less owner capital contributions and continuing terminal claims for existing cutoff holders. Supplied rights, funding, rates and terminal entitlements remain unreviewed; no entitlement or participation weight is inferred.'
        warnings.append('Sensitivities and reverse repricing are parent-equity diagnostics only. Frozen class streams do not automatically reprice under parent assumption changes; resupplied streams must reconcile to the changed parent value.')
    if stub: warnings.append('Explicit stub FCFF and finance income/dividends are supplied, not annual prorations. Discount times are supplied; finance capital charges use declared effective-rate compounding. Stub flows stay fixed in reverse-margin diagnostics.')
    if data['synthetic']: warnings.insert(0,'SYNTHETIC TEST INPUTS - not Hyundai results or any actual company valuation.')
    if not market_available:
        warnings.append('Market capitalization, equity gap and reverse diagnostics unavailable: missing market_price for '+', '.join(missing_quotes)+'.')
    elif not reverse_available: warnings.append('Reverse margin diagnostic unavailable: parent has no industrial margin exposure.')
    elif any(not -1<=g.value(s['path']+'.implied_terminal_margin')<=1 for s in industrial):
        warnings.append('Reverse margin diagnostic lies outside feasible terminal margin bounds; arithmetic solution only.')
    if g.evaluate(parent)<0: warnings.append('Negative parent equity: explicit owner capital flows can imply negative class values.' if explicit_classes else 'Negative parent equity: class recoveries floored at zero; no negative share price implied.')
    for s in industrial+finance:
        if g.value(s['path']+'.equity_value')<0: warnings.append(s['id']+': negative segment equity; proportional NCI includes loss sharing and requires challenge.')
    result=dict(schema_version='0.1.0-dev.1',company=data['company'],synthetic=data['synthetic'],currency=data['currency'],
                amount_scale=data['amount_scale']['value'],valuation_date=data['valuation_date'],horizon=n,timing_mode=data['discount_timing']['value'],
                cashflow_times=[g.evaluate(time(t)) for t in range(1,n+1)],terminal_time=g.evaluate(terminal_time),
                review_status='unreviewed_conditional',financial_review='not_performed',warnings=warnings,
                input_metadata={p:m for p,m in leaves(data)},industrial=industrial,finance=finance,classes=classes,
                sensitivities=grids,reverse_available=reverse_available,
                market_diagnostics=dict(available=market_available,missing_classes=missing_quotes,
                    recommendation_eligible=not quote_reasons,reasons=quote_reasons),
                values={p:v['value'] for p,v in g.nodes.items() if not p.startswith('input.')},
                units={p:v['unit'] for p,v in g.nodes.items() if not p.startswith('input.')})
    if explicit_classes:
        result['class_method']='explicit_distribution_streams'
        result['class_cashflow_status']='reconciled_unreviewed'
        result['sensitivity_scope']='parent_equity_diagnostics_only_frozen_class_streams'
    return result,g
