"""Map the common result to native full-report blocks, without revaluation."""
from html import escape
import copy
import json
import re
try:
    from .narrative import compose
except ImportError:
    from narrative import compose


def input_label(data,path):
    """Display actual entity/period identities, retaining raw paths in model ledgers."""
    parts=path.split('.')
    labels={'growth':'매출 성장률','margin':'영업이익률','da_rate':'감가상각률','capex_rate':'설비투자율','nwc_rate':'운전자본율','issued':'발행주식 수','treasury':'자기주식 수','market_price':'시장가격','time_to_cashflow':'현금흐름 시점','parent_ownership':'모회사 지분율','revenue':'매출','wacc':'WACC','terminal_growth':'영구성장률'}
    if parts[0] in ('industrial','finance') and len(parts)>2:
        segment=data[parts[0]][int(parts[1])]
        prefix=f"{segment['name']} ({segment['id']})"
        rest=parts[2:]
        if rest[0]=='forecast':
            year=data['base_year']+1+int('timing' in data)+int(rest[1])
            rest=[f'FY{year}',*rest[2:]]
        elif rest[0]=='stub':rest=[f"FY{data['base_year']+1} 잔여기간",*rest[1:]]
        return ' / '.join([prefix,*[labels.get(x,x.replace('_',' ')) for x in rest]])
    if parts[0]=='share_classes' and len(parts)>2:
        cls=data['share_classes'][int(parts[1])];name={'common':'보통주','preferred':'우선주'}.get(cls['id'],cls.get('name',cls['id']))
        return ' / '.join([name,*[labels.get(x,x.replace('_',' ')) for x in parts[2:]]])
    if parts[:2]==['timing','time_to_cashflow']:
        i=int(parts[2]);suffix=' 잔여기간' if i==0 and 'timing' in data else ''
        return f"FY{data['base_year']+1+i}{suffix} / 현금흐름 시점 (평가기준일 이후 연수)"
    return ' / '.join(labels.get(x,x.replace('_',' ')) for x in parts)

def input_register(data,items):
    """Collapse only consecutive forecast periods with identical full metadata."""
    candidates={};groups={};skipped=set()
    for position,(path,item) in enumerate(items):
        match=re.fullmatch(r'(industrial|finance)\.(\d+)\.forecast\.(\d+)\.(.+)',path)
        if match:
            key=(match[1],match[2],match[4])
            candidates.setdefault(key,[]).append((int(match[3]),position,path,item))
    for entries in candidates.values():
        entries.sort();runs=[];run=[];fingerprint=None
        for entry in entries:
            current=json.dumps(entry[3],sort_keys=True,ensure_ascii=False,allow_nan=False)
            if run and (entry[0]!=run[-1][0]+1 or current!=fingerprint):runs.append(run);run=[]
            run.append(entry);fingerprint=current
        if run:runs.append(run)
        for run in runs:
            if len(run)<2:continue
            first=run[0];paths=[e[2] for e in run]
            start=data['base_year']+1+int('timing' in data)+run[0][0]
            end=data['base_year']+1+int('timing' in data)+run[-1][0]
            label=input_label(data,first[2]).replace(f'FY{start} /',f'FY{start}–FY{end} /',1)
            groups[first[1]]={'label':label,'paths':paths,'item':first[3]}
            skipped.update(e[1] for e in run[1:])
    return [groups.get(i,{'label':input_label(data,path),'paths':[path],'item':item})
            for i,(path,item) in enumerate(items) if i not in skipped]

def input_basis(item):
    kind={'evidence':'공시 원문','observed':'관측','assumption':'가정','calculated':'계산','derived':'산출'}.get(item['kind'],item['kind'])
    if item['kind']=='assumption' and item.get('rationale','').startswith('[Calculated derivation, not an observed original; unreviewed]'):kind='산술 산출 (미검토)'
    return kind+' 근거일: '+item['as_of']+'; 출처: '+item['source']['id']

def input_unit(data,unit):
    if unit=='amount':return f"{data['currency']} / {data['amount_scale']['value']:g}"
    return {'currency_per_share':data['currency']+'/주','shares':'주','ratio':'비율 (소수)','years':'년','currency_per_amount':data['currency']+'/모형금액 단위'}.get(unit,unit)

def prepare(data,result):
    values=result['values'];bindings=[]
    explicit_classes=data['class_rights']['value']=='explicit_distribution_streams'
    diagnostics=result.get('market_diagnostics',{})
    # Only known optional quote-dependent paths may become unavailable text.
    optional={'diagnostics.market_equity','diagnostics.equity_gap',
              'diagnostics.margin_slope','diagnostics.implied_margin_shift',
              'diagnostics.reverse_repriced_equity'}
    optional.update(s['path']+'.market_equity' for s in result['classes'])
    optional.update(s['path']+'.implied_terminal_margin' for s in result['industrial'])
    optional_inputs={f'share_classes.{j}.market_price' for j in range(len(data['share_classes']))}
    unavailable='Diagnostic unavailable'
    def missing(path):
        return (path in optional and path not in values) or (
            path.startswith('input.') and path[6:] in optional_inputs and path[6:] not in result['input_metadata'])
    config=data.get('report',{})
    authored=[text for section in config.get('report_sections',[]) for text in
              [section['title'],section['lead']]+[b['text'] for b in section['blocks']]]
    def market_recommendation(text):
        # Legal rights and statements about existing ownership are not ratings.
        # The independent claim reviewer remains responsible for semantic scope.
        text=re.sub(r'매수\s*청구권|매수\s*선택권|보유\s*(?:지분|주식수|주식\s*수|현금|자산)', '', text)
        return re.search(r'\b(?:buy|undervalu(?:ed|ation))\b|\bhold\b(?=\s*(?:[.!?]|$)|\s+(?:rating|recommendation|shares|position)\b)|\b(?:rating|recommend(?:ation|ed)?)\b[^.!?]*\bhold\b|매수|보유\s*(?:추천|의견|등급|권고)|저평가',text,re.I)
    if not diagnostics.get('recommendation_eligible',False) and any(market_recommendation(text) for text in authored):
        raise ValueError('Market recommendations require same-date eligible sourced quotes for every class')
    if config:
        data=copy.deepcopy(data)
        token=re.compile(r'\{\{(model|input):([A-Za-z0-9_.-]+)(?:\|(?:amount|percent|integer|raw))?\}\}')
        def reconcile(text):
            return token.sub(lambda m:unavailable if missing(('input.' if m[1]=='input' else '')+m[2]) else m[0],text)
        for section in data['report'].get('report_sections',[]):
            for key in ('title','lead'):section[key]=reconcile(section[key])
            for block in section['blocks']:block['text']=reconcile(block['text'])
    def cell(path,percent=False):
        if missing(path):return {'text':unavailable,'html':escape(unavailable)}
        value=(result['input_metadata'][path.removeprefix('input.')]['value'] if path.startswith('input.') else values[path]);shown=f'{value:.2%}' if percent else f'{value:,.2f}'
        bindings.append(dict(path=path,value=value,display=shown))
        return {'text':shown,'html':f'<span data-result-path="{escape(path)}">{shown}</span>'}
    def table(headers,rows,caption=''):
        return dict(kind='table',headers=[escape(x) for x in headers],rows=rows,caption_html=escape(caption))
    def paragraph(text):return dict(kind='paragraph',html=escape(text))
    def section(id,title,blocks,lead=''):
        return dict(id=id,title=title,lead=lead,blocks=blocks)
    units=f"{data['currency']}; amounts in units of {data['amount_scale']['value']:g}; share prices in {data['currency']} per share"
    status='SYNTHETIC TEST / UNREVIEWED' if data['synthetic'] else 'CONDITIONAL / UNREVIEWED'
    sections=[section('conclusion','Conditional model results',[
        paragraph(result['warnings'][0]),
        table(['Class','Outstanding shares','Allocated equity','Per share'],
              [[s['id'],cell(s['path']+'.outstanding'),cell(s['path']+'.equity_value'),cell(s['path']+'.per_share')] for s in result['classes']],units),
        *[paragraph(x) for x in result['warnings'][1:]]],status)]
    sections.append(section('timing','Valuation date and cash-flow timing',[
        paragraph('Valuation date: '+result['valuation_date']+'. Mode: '+result['timing_mode']+'. No annual cash flow is automatically scaled into a stub.'),
        table(['Period end','Cash-flow basis','Discount time (years)'],
              [[str(row['year'])+'-12-31',row['period'],f"{row['time']:.6f}"] for row in result['industrial'][0]['rows']]),
        paragraph('Terminal discount time: '+str(result['terminal_time'])+' years. Terminal value is located at the final forecast cash-flow date. Explicit-mode finance capital charges use the declared effective-rate compounding convention.')]))
    for j,s in enumerate(result['industrial']):
        p=s['path'];inp=data['industrial'][j]
        rows=[]
        for row in s['rows']:
            q=row['path'];rows.append([str(row['year'])+(' stub' if row['period']=='explicit stub' else '')]+[cell(q+'.'+key) for key in ['revenue','ebit','nopat','da','capex','delta_nwc','fcff']])
        blocks=[paragraph(f"{inp['lease_policy']['value']}: {inp['lease_basis']['value']}"),
                table(['Year','Sales','EBIT','NOPAT','D&A','Capex','Delta NWC','FCFF'],rows,units),
                table(['Terminal / value','Amount'],[[label,cell(p+'.'+key)] for label,key in [
                    ('Terminal NOPAT','terminal_nopat'),('Sustainable reinvestment','terminal_reinvestment'),('Terminal FCFF','terminal_fcff'),
                    ('Terminal value','terminal_value'),('Terminal present value','terminal_pv'),('Enterprise value','enterprise_value'),
                    ('Equity value','equity_value'),('Segment proportional NCI','nci'),('Equity after segment NCI, before group adjustments','parent_equity')]],units),
                paragraph('Segment equity attribution excludes separately valued group-level NCI and other parent adjustments. See the enterprise-to-parent bridge for the final parent equity.'),
                paragraph('FCFF = EBIT x (1 - tax) + depreciation - capex - change in working-capital stock. Terminal FCFF = terminal NOPAT x (1 - g / ROIC).')]
        sections.append(section('industrial-'+str(j),s['name']+' - industrial DCF',blocks,'Explicit stub and annual cash flows; assumptions unreviewed.' if result['timing_mode']=='explicit_stub' else 'Annual year-end cash flows; assumptions remain unreviewed.'))
    for j,s in enumerate(result['finance']):
        p=s['path'];rows=[]
        for row in s['rows']:
            q=row['path'];rows.append([str(row['year'])+(' stub' if row['period']=='explicit stub' else '')]+[cell(q+'.'+key) for key in ['opening_book','income','dividend','closing_book','residual_income','pv']])
        sections.append(section('finance-'+str(j),s['name']+' - equity valuation',[
            paragraph(data['finance'][j]['finance_basis']['value']),
            table(['Year','Open book','Income','Dividend','Close book','RI','PV of RI'],rows,units),
            table(['Method / component','Value'],[[label,cell(p+'.'+key)] for label,key in [
                ('Terminal residual income','terminal_residual_income'),('Terminal RI present value','terminal_pv'),
                ('Residual income equity','equity_value'),('Supplied P/B crosscheck','pb_crosscheck'),('RI less P/B','pb_difference'),
                ('NCI equity','nci'),('Parent equity','parent_equity')]],units),
            paragraph('Equity = opening book + discounted residual income + discounted terminal residual income. Clean surplus excludes OCI, issuance and acquisitions. P/B is an independent supplied assumption, not a selected valuation or review pass.')],status))
    bridge=[('Industrial enterprise value','industrial_enterprise_value'),('Finance equity','finance_equity'),('Industrial cash','industrial_cash'),
            ('Less industrial debt','industrial_debt'),('Less debt-like leases','industrial_leases'),('Equity before NCI','pre_nci_equity'),
            *([('Segment proportional NCI','segment_nci'),('Additional separately valued NCI','separately_valued_nci')] if 'bridge.separately_valued_nci' in result['values'] else []),
            ('Less total valued NCI','nci'),('Parent equity','parent_equity'),('Finance funding debt: excluded from bridge deduction','finance_funding_debt_excluded')]
    sections.append(section('bridge','Enterprise to parent equity',[
        table(['Bridge component','Value'],[[label,cell('bridge.'+key)] for label,key in bridge],units),
        table(['Explicit parent-level adjustment','Amount'],[[key.replace('_',' '),cell('input.bridge.'+key)] for key in data['bridge'] if key!='separately_valued_nci'],units),
        paragraph('The before-NCI subtotal includes parent assets, liabilities and elimination adjustments; total NCI is then deducted once. Separately valued NCI is an equity claim, not parent debt, and includes only claims not already attributed through segment ownership.'),
        table(['Segment','Equity base','Valued NCI','Parent value'],[[s['name'],cell(s['path']+'.equity_value'),cell(s['path']+'.nci'),cell(s['path']+'.parent_equity')] for s in result['industrial']+result['finance']],units)]))
    sections.append(section('consolidation','Historical consolidation controls',[
        table(['Control','Residual'],[[key.replace('_',' '),cell('checks.'+key)] for key in ['revenue','ebit','debt','cash','finance_book']],units),
        paragraph('Residual = segment total + signed consolidation adjustments - supplied consolidated control. Debt controls exclude industrial lease liabilities, which are treated separately. Zero residual checks arithmetic only; it does not verify source attribution.'),
        table(['Supplied control / elimination','Amount'],[[key.replace('_',' ')+' / '+input_basis(result['input_metadata']['consolidation.'+key]),cell('input.consolidation.'+key)] for key in data['consolidation']],units)]))
    if explicit_classes:
        rights_headers=['Class','Cost of equity','Terminal claim','Terminal PV','Market equity','Implied price']
        rights_caption='Explicit dated owner streams; existing cutoff holders. Amounts use the model scale; discount rates are ratios and prices are currency per share.'
        sections.append(section('rights','Share classes - explicit distribution streams',[
            paragraph(data['class_rights']['value']+': '+data['class_rights']['rationale']),
            dict(table(rights_headers,[[s['id'],cell(s['path']+'.cost_equity',True),cell(s['path']+'.terminal_claim'),cell(s['path']+'.terminal_pv'),cell(s['path']+'.market_equity'),cell(s['path']+'.per_share')] for s in result['classes']],rights_caption),title='Explicit class rates and continuing terminal claims'),
            table(['Class','Time (years)','Distribution','Capital contribution','Net owner flow','PV'],
                  [[s['id'],*[cell(row['path']+'.'+k) for k in ('time','distribution','capital_contribution','net','pv')]] for s in result['classes'] for row in s['events']],units),
            table(['Terminal time (years)','Terminal total claim'],[[cell('classes.terminal_time'),cell('classes.terminal_total_claim')]],units),
            table(['Reconciliation','Residual','Unit'],[[p.removeprefix('checks.'),cell(p),input_unit(data,result['units'][p])] for p in values if p.startswith('checks.class_') or p.startswith('checks.class_event')],units),
            *[paragraph(s['id']+' / rights reference: '+s['rights_reference']+' / terminal reference: '+s['terminal_reference']) for s in result['classes']],
            paragraph('Outstanding = issued less treasury at cutoff. Class value = discounted distributions less owner capital contributions plus discounted continuing terminal claim. Each class explicitly supplies every parent event, including zero. Distributions and contributions reconcile separately; terminal claims and present values reconcile to parent controls. Source truth, legal entitlement, funding, class rates and terminal assumptions require independent review.')]))
    else:
        sections.append(section('rights','Share classes and economic rights',[
        paragraph(data['class_rights']['value']+': '+data['class_rights']['rationale']),
        table(['Class','Fixed claim','Participation weight','Market equity','Implied price'],[[s['id'],cell(s['path']+'.fixed_claim'),cell(s['path']+'.weight'),cell(s['path']+'.market_equity'),cell(s['path']+'.per_share')] for s in result['classes']],units),
            paragraph('Outstanding = issued less treasury. Available equity is floored at zero. Fixed claims recover pari passu up to available equity; residual is allocated by outstanding shares times the supplied economic participation weight. Share-class rights need independent legal verification.')]))
    for name,grid in result['sensitivities'].items():
        step=data['sensitivity']['growth_step' if name=='industrial' else 'roe_step']['value']
        ds=data['sensitivity']['discount_step']['value']
        sections.append(section('sensitivity-'+name,name.title()+' sensitivities',[
            table(['Discount shift / '+('g shift' if name=='industrial' else 'terminal ROE shift')]+[f'{b*step:+.2%}' for b in range(-2,3)],
                  [[f'{a*ds:+.2%}']+[cell(path) for path in grid[a+2]] for a in range(-2,3)],units+'; parent equity'),
            paragraph('Each cell fully recalculates the selected parent valuation method using shifted inputs, including changing proportional NCI. Frozen explicit class streams do not automatically reprice or reconcile under these shifts; revised streams require fresh parent-value reconciliation.' if explicit_classes else 'Each cell fully recalculates the selected method using shifted inputs, including changing proportional NCI. Other segments and parent adjustments stay at base. The center cell equals base parent equity. These are conditional sensitivities, not probabilities.')]))
    reverse=[table(['Diagnostic','Value'],[['Supplied market capitalization',cell('diagnostics.market_equity')],['Modeled equity less market',cell('diagnostics.equity_gap')]],units)]
    if result['reverse_available']:
        reverse.extend([table(['Reverse diagnostic','Value'],[['Implied uniform EBIT margin shift',cell('diagnostics.implied_margin_shift',True)],['Repriced equity',cell('diagnostics.reverse_repriced_equity')]]),
                        paragraph('Solve one additive change in all industrial annual forecast and terminal EBIT margins; supplied stub cash flows stay fixed to match the supplied aggregate class market capitalization. Hold sales, investment drivers, ROIC, tax, discount rates, finance values and parent adjustments fixed. This is an arithmetic diagnostic, not an achievable business plan.')])
    else:
        reason=('missing market_price for '+', '.join(diagnostics.get('missing_classes',[])) if not diagnostics.get('available',True) else 'no parent industrial margin exposure')
        reverse.append(paragraph('Market/reverse diagnostic unavailable: '+reason+'.'))
    sections.append(section('reverse','Reverse valuation diagnostics',reverse))
    if explicit_classes:
        reverse.append(paragraph('Reverse repricing is a parent-equity diagnostic only; it does not reprice frozen explicit class streams or establish class entitlements.'))
    # Bar chart handles negative and zero values using the native generic constructor.
    paths=['bridge.industrial_enterprise_value','bridge.finance_equity','bridge.nci','bridge.parent_equity']
    chart=dict(type='bars',title='Value components',unit=data['currency']+' model amount',
               categories=['Industrial EV','Finance equity','Valued NCI','Parent equity'],
               series=[dict(name='Conditional value',values=[values[p] for p in paths],result_paths=['values.'+p for p in paths])],
               note='Components have different valuation bases; NCI is deducted in the bridge.')
    sections.append(section('chart','Value components',[dict(kind='chart',chart=chart)],units))
    # Every input's full evidence is frozen in JSON and workbook; print a readable register.
    groups={}
    for path,item in result['input_metadata'].items():
        groups.setdefault(path.split('.')[0],[]).append((path,item))
    for idx,(group,items) in enumerate(groups.items()):
        rows=[]
        for entry in input_register(data,items):
            item=entry['item'];label=entry['label']
            label=label+' / '+input_basis(item).split('; 출처:')[0]
            label={'text':label,'html':f'<span data-input-paths="{escape(" ".join(entry["paths"]))}">{escape(label)}</span>'}
            value=item['value']
            display=f'{value:g}' if isinstance(value,(int,float)) else str(value)
            basis={'evidence':'공시 원문','observed':'관측','assumption':'가정','calculated':'계산','derived':'산출'}.get(item['kind'],item['kind'])
            review={'unreviewed':'미검토','reviewed':'검토 기록 있음'}.get(item['review']['status'],item['review']['status'])
            rows.append([label,display,input_unit(data,item['unit']),basis+' / '+review,item['source']['id']])
        sections.append(section('sources-'+str(idx),group.replace('_',' ').title()+' - historical inputs and valuation assumptions',[
            table(['입력·적용기간·근거일','값','단위','근거 / 검토상태','출처 ID'],rows,units+'; source/assumption as-of dates are distinguished from forecast calendar ranges'),
            paragraph('Consecutive forecast years share a row only when value and all provenance/review metadata match exactly; the explicit year range applies to every year. Every original path is retained in HTML data-input-paths and the full model/Excel evidence. Per-input dates, exact locators, source URI/hash, rationale and declared reviewer/reference are retained in valuation-input.json (delivered valuation inputs), input.json (publication copy), model-result.json and the workbook Evidence tab. Declared reviewed inputs do not constitute review of this model or report.')]))
    sections,bindings,language=compose(data,result,sections,bindings)
    d=dict(schema_version=2,key='valuation',id='1',audience='Model users and reviewers; conditional adapter output',title=data['company']+' scenario',
           subtitle='Conditional valuation.\nFinancial review unperformed.',language=language,overview_mode='integrated',comparison_href=None,
           scope=f"{data['valuation_date']} | {units}",status=status,conclusion='Conditional, unreviewed valuation from supplied inputs.',
           headers=['Component','Value'],rows=[[label,f"{values['bridge.'+key]:,.2f}"] for label,key in bridge[:4]],
           findings=result['warnings'][:3],needs=['Verify source snapshots and consolidation attribution.','Review valuation assumptions and lease treatment.','Verify class rights and NCI ownership.'],
           hero=[f"{values['bridge.parent_equity']:,.2f}",data['currency']+' model amount','Conditional parent equity'],kpis=[],chart=chart,
           formula='Industrial FCFF DCF plus finance residual-income equity, adjusted to parent equity and class rights.',unit_note=units,sources=[dict(id='INPUT',display_name='Supplied input snapshot',locator='input.json; full per-input provenance',url='')],
           design_boundary='Native report-outfit design application only; not a firm-issued opinion, professional-quality certification, financial review or approved assumptions.',
           report_footer=status+' | Native design application; no financial review',report_sections=sections)
    if language=='ko':
        d['title']=data['company']+' 평가 시나리오'
        d['subtitle']='조건부 기업가치 평가\n재무 검토 미수행'
        d['status']=('합성 시험 시나리오' if data['synthetic'] else '조건부 시나리오')+' / 재무 검토 미수행'
        d['report_footer']=d['status']+' | 독립 검토 및 승인 미수행'
    try:
        from .presentation import refine
    except ImportError:
        from presentation import refine
    document=refine(d,data,result,bindings)
    if explicit_classes:
        # The shared formatter has legacy rights headings. Restore the selected
        # contract here without changing its behavior for any legacy report.
        for selected in document['report_sections']:
            if selected['id']=='rights':
                first=next(b for b in selected['blocks'] if b['kind']=='table')
                first['headers']=rights_headers
                first['caption_html']=escape(rights_caption)
            elif selected['id']=='conclusion':
                first=next(b for b in selected['blocks'] if b['kind']=='table')
                first['title']='Conditional share-class owner cashflow values'
                first['headers']=['Class','Outstanding (shares)','Owner cashflow value','Price ('+data['currency']+'/share)']
    return document,bindings
