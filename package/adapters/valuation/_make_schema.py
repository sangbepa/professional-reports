"""Maintainer utility: writes the explicit schema and synthetic test fixture."""
import json
from pathlib import Path

HERE = Path(__file__).parent

def obj(props):
    return dict(type='object', properties=props, required=list(props), additionalProperties=False)

def arr(items, minimum=1, maximum=20):
    return dict(type='array', items=items, minItems=minimum, maxItems=maximum)

def text():
    return dict(type='string', minLength=1)

def ref(name):
    return {'$ref': '#/$defs/'+name}

def atom(value):
    return obj(dict(value=value, kind={'enum':['evidence','assumption','synthetic']},
                    source=obj(dict(id=text(), locator=text(), uri={'type':'string'},
                                    sha256={'type':'string','pattern':'(?:[0-9a-f]{64})?'})),
                    as_of={'type':'string','format':'date'}, unit=text(), rationale=text(),
                    review=obj(dict(status={'enum':['unreviewed','reviewed','rejected']},
                                    reviewer={'type':'string'}, reference={'type':'string'}))))

number={'type':'number'}
num=ref('number'); rate=ref('rate'); pos=ref('positive'); nonneg=ref('nonnegative')
def fields(names, schema=num):return {key:schema for key in names.split()}
forecast=obj(dict(**fields('growth margin da_rate capex_rate nwc_rate',rate)))
industrial=obj(dict(id={'type':'string','pattern':'[A-Za-z][A-Za-z0-9_-]{0,30}'},name=text(),
                    **fields('revenue',pos),**fields('reported_ebit'),
                    **fields('debt cash lease_liability',nonneg),
                    parent_ownership=ref('fraction'),nci_method=ref('nci_method'),
                    lease_policy=ref('lease_policy'),lease_basis=ref('text_atom'),
                    opening_nwc_rate=rate,forecast=arr(forecast),wacc=pos,terminal_growth=rate,
                    terminal_margin=rate,terminal_roic=pos,tax_rate=ref('fraction')))
finance=obj(dict(id={'type':'string','pattern':'[A-Za-z][A-Za-z0-9_-]{0,30}'},name=text(),
                 **fields('revenue reported_ebit'),**fields('book_equity',pos),
                 **fields('funding_debt cash',nonneg),parent_ownership=ref('fraction'),
                 nci_method=ref('finance_nci_method'),finance_basis=ref('text_atom'),
                 forecast=arr(obj(dict(roe=rate,payout=ref('fraction')))),
                 cost_equity=pos,terminal_growth=rate,terminal_roe=pos,pb_multiple=nonneg))
props=dict(schema_version={'enum':['0.1.0-dev.1']},company=text(),synthetic={'type':'boolean'},
           currency={'type':'string','pattern':'[A-Z]{3}'},amount_scale=pos,
           valuation_date={'type':'string','format':'date'},base_year={'type':'integer','minimum':1900,'maximum':9990},
           horizon={'type':'integer','minimum':1,'maximum':20},discount_timing=ref('timing'),
           industrial=arr(industrial),finance=arr(finance,0),
           consolidation=obj(fields('revenue_eliminations ebit_eliminations debt_eliminations cash_eliminations '
                                    'consolidated_revenue consolidated_ebit consolidated_debt consolidated_cash '
                                    'finance_book_adjustment consolidated_finance_book')),
           bridge=obj(fields('nonoperating_assets parent_liabilities industrial_ev_adjustment finance_equity_adjustment')),
           class_rights=ref('rights'),
           share_classes=arr(obj(dict(id={'type':'string','pattern':'[A-Za-z][A-Za-z0-9_-]{0,30}'},
                   **fields('issued treasury',nonneg),**fields('participation_weight',nonneg),
                   **fields('fixed_claim_per_share market_price',nonneg))),1,10),
           sensitivity=obj(dict(discount_step=pos,growth_step=pos,roe_step=pos)))
schema=dict(**{'$schema':'https://json-schema.org/draft/2020-12/schema'},title='Conditional segmented valuation input',
            **obj(props))
schema['$defs']={
    'number':atom(number), 'rate':atom(dict(type='number',minimum=-1,maximum=1)),
    'positive':atom(dict(type='number',exclusiveMinimum=0)),
    'nonnegative':atom(dict(type='number',minimum=0)),
    'fraction':atom(dict(type='number',minimum=0,maximum=1)),
    'timing':atom({'enum':['year_end','explicit_stub']}),
    'lease_policy':atom({'enum':['operating_expense','debt_like']}),
    'nci_method':atom({'enum':['proportionate_segment_equity']}),
    'finance_nci_method':atom({'enum':['proportionate_residual_income_equity']}),
    'rights':atom({'enum':['pari_passu_fixed_then_weighted_residual']}),
    'text_atom':atom(text())}

# Optional fields are required exactly when explicit_stub is selected.
industrial['properties']['stub']=obj(dict(**fields('revenue ebit cash_tax da capex delta_nwc opening_nwc closing_nwc fcff'),full_year_revenue_anchor=pos))
finance['properties']['stub']=obj(dict(income=num,dividends=nonneg))
schema['properties']['timing']=obj(dict(time_to_cashflow=arr(pos),terminal_time=pos,
    finance_stub_charge=atom({'enum':['compound_effective_rate']})))
schema['properties']['report']=obj(dict(
    language={'type':'string','enum':['ko','en']},
    report_sections=arr(obj(dict(id={'type':'string','pattern':'[A-Za-z][A-Za-z0-9_-]{0,60}'},
        title=text(),lead={'type':'string'},blocks=arr(obj(dict(
            kind={'type':'string','enum':['argument','evidence','condition','paragraph']},
            text=text(),evidence_ids=arr(text(),0,50))),1,100))),0,100),
    section_order=arr(text(),0,200)))
# All report options are optional; semantic validation resolves section references.
schema['properties']['report']['required']=[]
schema['allOf']=[{'if':{'properties':{'discount_timing':{'properties':{'value':{'const':'explicit_stub'}}}}},
                  'then':{'required':['timing'],'properties':{'industrial':{'items':{'required':['stub']}},
                                                             'finance':{'items':{'required':['stub']}}}}}]

def a(value,unit='ratio' ,reason='Fixed synthetic test assumption; no company or market evidence.'):
    return dict(value=value,kind='synthetic',source=dict(id='SYNTHETIC',locator='Fixed test fixture',uri='',sha256=''),
                as_of='2025-12-31',unit=unit,rationale=reason,
                review=dict(status='unreviewed',reviewer='',reference=''))
def money(value):return a(value,'amount')
def ind(id,rev,ebit,debt,cash,ownership):
    return dict(id=id,name='Synthetic '+id, revenue=money(rev),reported_ebit=money(ebit),debt=money(debt),cash=money(cash),
                lease_liability=money(5),parent_ownership=a(ownership),nci_method=a('proportionate_segment_equity','policy'),
                lease_policy=a('debt_like','policy'),lease_basis=a('EBIT excludes lease interest; D&A and capex include ROU depreciation and additions.','policy'),
                forecast=[dict(growth=a(.04),margin=a(.15),da_rate=a(.03),capex_rate=a(.05),nwc_rate=a(.12)) for _ in range(5)],
                opening_nwc_rate=a(.12),wacc=a(.1),terminal_growth=a(.02),terminal_margin=a(.15),terminal_roic=a(.12),tax_rate=a(.25))
fixture=dict(schema_version='0.1.0-dev.1',company='SYNTHETIC Example Group',synthetic=True,currency='USD',
             amount_scale=a(1000000,'currency_per_amount'),valuation_date='2025-12-31',base_year=2025,horizon=5,
             discount_timing=a('year_end','policy'),industrial=[ind('Products',1000,150,100,40,.8),ind('Services',500,75,30,10,1)],
             finance=[dict(id='Finance',name='Synthetic Finance',revenue=money(100),reported_ebit=money(20),book_equity=money(200),
                 funding_debt=money(800),cash=money(30),parent_ownership=a(.9),nci_method=a('proportionate_residual_income_equity','policy'),finance_basis=a('Book equity, ROE and payouts include funding debt and finance leases.','policy'),
                 forecast=[dict(roe=a(.12),payout=a(.5)) for _ in range(5)],cost_equity=a(.11),
                 terminal_growth=a(.02),terminal_roe=a(.12),pb_multiple=a(1.1))],
             consolidation={k:money(v) for k,v in dict(revenue_eliminations=-50,ebit_eliminations=-5,debt_eliminations=0,cash_eliminations=0,
                 consolidated_revenue=1550,consolidated_ebit=240,consolidated_debt=930,consolidated_cash=80,
                 finance_book_adjustment=0,consolidated_finance_book=200).items()},
             bridge={k:money(v) for k,v in dict(nonoperating_assets=20,parent_liabilities=10,industrial_ev_adjustment=-40,finance_equity_adjustment=0).items()},
             class_rights=a('pari_passu_fixed_then_weighted_residual','policy'),
             share_classes=[dict(id='Common',issued=a(10000000,'shares'),treasury=a(1000000,'shares'),participation_weight=a(1),
                     fixed_claim_per_share=a(0,'currency_per_share'),market_price=a(120,'currency_per_share')),
                 dict(id='ClassB',issued=a(1000000,'shares'),treasury=a(0,'shares'),participation_weight=a(.8),
                     fixed_claim_per_share=a(10,'currency_per_share'),market_price=a(105,'currency_per_share'))],
             sensitivity=dict(discount_step=a(.005),growth_step=a(.005),roe_step=a(.01)))
def stub_fixture():
    import copy
    d=copy.deepcopy(fixture)
    d['company']='SYNTHETIC Cross-Company Scenario'
    d['valuation_date']='2026-10-03'
    d['discount_timing']=a('explicit_stub','policy','Explicit stub flows; no annual proration.')
    d['timing']=dict(time_to_cashflow=[a(x,'years','Fixed explicit discount time; not inferred from dates.') for x in [.25,1.25,2.25,3.25,4.25]],
                     terminal_time=a(4.25,'years','Terminal value at the last forecast cash-flow date.'),
                     finance_stub_charge=a('compound_effective_rate','policy','Effective annual cost of equity compounded over the explicit first-period time.'))
    for j,seg in enumerate(d['industrial']):
        # Fixed synthetic amounts independent of the annual forecasts.
        factor=1 if j==0 else .5
        seg['stub']={k:money(v*factor) for k,v in dict(revenue=260,ebit=36,cash_tax=9,da=8,capex=13,delta_nwc=2,
                      opening_nwc=120,closing_nwc=122,fcff=20,full_year_revenue_anchor=1040).items()}
        seg['forecast']=seg['forecast'][1:]
    for seg in d['finance']:
        seg['stub']=dict(income=money(7),dividends=money(3))
        seg['forecast']=seg['forecast'][1:]
    d['report']=dict(language='ko',report_sections=[
        dict(id='decision',title='검토 목적과 조건부 결론',lead='실제 기업 평가가 아닌 공통 모형 실행 사례',blocks=[
            dict(kind='argument',text='평가기준일 {{context:valuation_date}}의 합성 시나리오다. 지배주주 지분가치는 {{model:bridge.parent_equity|amount}} 모형 단위이며, 실제 기업의 투자 판단이나 목표주가가 아니다.',evidence_ids=[]),
            dict(kind='condition',text='{{context:review_status}} 상태다. 입력 출처, 연결 범위, 가정과 종류주 권리에 대한 독립 검토를 완료해야 실제 보고서의 결론으로 사용할 수 있다.',evidence_ids=[])]),
        dict(id='argument',title='산업부문과 금융부문을 구분하는 이유',lead='중복 차감 방지와 지분 귀속',blocks=[
            dict(kind='argument',text='금융부문의 조달부채 {{model:bridge.finance_funding_debt_excluded|amount}}는 장부자본과 수익성에 반영되는 항목이다. 산업부문 기업가치에서 다시 차감하지 않는다. 비지배지분은 기업가치가 아닌 부문별 지분가치에서 산정한다.',evidence_ids=[]),
            dict(kind='evidence',text='합성 입력으로 직접 공급한 첫 산업부문 잔여기간 FCFF는 {{input:industrial.0.stub.fcff|amount}}이고, 금융부문 잔여기간 이익은 {{input:finance.0.stub.income|amount}}이다. 연간 전망을 비례 축소한 값이 아니다.',evidence_ids=['SYNTHETIC']),
            dict(kind='condition',text='첫 산업부문 영구성장률 {{input:industrial.0.terminal_growth|percent}}와 ROIC {{input:industrial.0.terminal_roic|percent}}는 시험용 가정이다. 재무적 타당성이나 승인된 가정으로 해석해서는 안 된다.',evidence_ids=['SYNTHETIC'])])],
        section_order=['narrative:decision','narrative:argument','calculated:timing','calculated:bridge',
                       'calculated:industrial-0','calculated:industrial-1','calculated:finance-0',
                       'calculated:rights','calculated:sensitivity-industrial','calculated:sensitivity-finance',
                       'calculated:reverse','calculated:chart','calculated:consolidation'])
    return d

if __name__=='__main__':
    (HERE/'input.schema.json').write_text(json.dumps(schema,indent=2)+'\n')
    (HERE/'examples'/'synthetic.json').write_text(json.dumps(fixture,indent=2)+'\n')
    (HERE/'examples'/'synthetic-stub.json').write_text(json.dumps(stub_fixture(),indent=2)+'\n')
