"""Presentation metadata only; consumes frozen results and never evaluates a model."""
from html import escape
import re


def refine(document, data, result, bindings):
    currency = data['currency']
    scale = data['amount_scale']['value']
    unit = currency + {1: '', 1000: ' thousand', 1000000: ' million', 1000000000: ' billion'}.get(scale, f' / {scale:g}')
    sections = {s['id']: s for s in document['report_sections']}

    def bound(path, percent=False):
        value = result['input_metadata'][path[6:]]['value'] if path.startswith('input.') else result['values'][path]
        shown = f'{value:.2%}' if percent else f'{value:,.2f}'
        bindings.append(dict(path=path, value=value, display=shown))
        return dict(text=shown, html=f'<span data-result-path="{escape(path)}">{shown}</span>')

    def table(title, headers, rows, **metadata):
        return dict(kind='table', title=title, headers=headers, rows=rows, caption_html=unit, **metadata)

    # Present all signed adjustments inside the bridge, without duplicating bindings.
    if 'bridge' in sections:
        s = sections['bridge']; main, adjustments, explanation, segments = s['blocks']
        labels = {'nonoperating assets': 'Add parent nonoperating assets', 'parent liabilities': 'Less parent liabilities',
                  'industrial ev adjustment': 'Signed industrial EV adjustment', 'finance equity adjustment': 'Signed finance equity adjustment'}
        adjustment_rows = [[labels.get(row[0], row[0]), row[1]] for row in adjustments['rows']]
        memo = main['rows'][-1:]
        main['rows'] = main['rows'][:5] + adjustment_rows + main['rows'][5:-1]
        main.update(title='Operating values to conditional parent equity', row_roles=['component']*5+['adjustment']*len(adjustment_rows)+['subtotal']+(['memo','memo'] if 'bridge.separately_valued_nci' in result['values'] else [])+['deduction','result'])
        main['rows'][0][0] = 'Industrial enterprise value'
        main['rows'][1][0] = 'Add finance equity'
        main['rows'][2][0] = 'Add industrial cash'
        for row in main['rows']:
            if row[0] in ('Segment proportional NCI','Additional separately valued NCI'):row[0]='Memo only: '+row[0]+' (included in total NCI; not additive)'

        main['caption_html'] = escape(unit + ' | Add / Less denotes operation; signed adjustments enter as displayed.')
        memo_table = table('Memorandum - already reflected in finance equity', ['Not deducted again', unit], memo, row_roles=['memo'])
        memo_table['kind']='memo'
        segments['title'] = 'Segment equity attribution before parent-level adjustments'
        s['blocks'] = [main, memo_table, explanation, segments]

    titles = {
        'timing': ['Forecast dates and discount periods'],
        'rights': ['Class claims, weighted participation and market comparison'],
        'consolidation': ['Historical reconciliation residuals', 'Signed eliminations and supplied controls'],
        'reverse': ['Model versus supplied market capitalization', 'Uniform margin change required to match market'],
        'conclusion': ['Conditional equity allocation by share class'],
    }
    for key, s in sections.items():
        tables = [b for b in s['blocks'] if b['kind']=='table']
        for i, b in enumerate(tables):
            b.setdefault('title', s['title']+' - input evidence register' if key.startswith('sources-') else titles.get(key, [])[i] if i < len(titles.get(key, [])) else s['title'] + (' - forecast' if i==0 else ' - valuation'))
            if b.get('caption_html') and 'amounts in units' in b['caption_html']:
                b['caption_html'] = escape(unit)
            roles = b.setdefault('row_roles', [])
            if not roles:
                for row in b['rows']:
                    label = str(row[0]).lower()
                    roles.append('result' if label=='parent equity' else 'crosscheck' if any(x in label for x in ['crosscheck','less p/b','less market']) else 'deduction' if 'nci' in label or 'noncontrolling' in label else 'subtotal' if label in ['enterprise value','equity value','residual income equity'] else 'detail')
        if key.startswith('industrial-') and len(tables)==2:
            tables[0]['title']='Forecast operating cash flows by period'
            tables[1]['title']='Terminal value, enterprise value and equity attribution'
        if key.startswith('finance-') and len(tables)==2:
            tables[0]['title']='Book equity roll-forward and residual income'
            tables[1]['title']='Residual-income valuation and supplied P/B crosscheck'
        for b in s['blocks']:
            if 'html' in b and not key.startswith('narrative-'):
                b['html'] = b['html'].replace('Mode: explicit_stub.', 'Timing: explicitly supplied remaining-period cash flows.').replace('debt_like:', 'Leases treated as debt:').replace('operating_expense:', 'Leases treated as operating expense:').replace('pari_passu_fixed_then_weighted_residual:', 'Equal-ranking fixed claims, then weighted residual allocation:')
        s['category'] = 'ANALYSIS' if key.startswith('narrative-') else 'METHOD' if key=='timing' else 'NOTES' if key=='model-conditions' or key.startswith('sources') else 'FIGURE' if key=='chart' else 'EXHIBITS'

    if 'rights' in sections:
        b = next(b for b in sections['rights']['blocks'] if b['kind']=='table')
        b['headers'] = ['Class', f'Fixed claim ({unit})', 'Participation (weighted shares)', f'Market equity ({unit})', f'Implied price ({currency}/share)']
        b['caption_html'] = 'Weighted shares = outstanding shares × supplied participation factor (dimensionless).'
    if 'conclusion' in sections:
        b = next(b for b in sections['conclusion']['blocks'] if b['kind']=='table')
        b['headers'] = ['Class','Outstanding (shares)',f'Allocated equity ({unit})',f'Price ({currency}/share)']

    for name in ('industrial','finance'):
        key='sensitivity-'+name
        if key not in sections: continue
        s=sections[key];grid=s['blocks'][0]
        first, second = ('wacc','terminal_growth') if name=='industrial' else ('cost_equity','terminal_roe')
        baseline = table('Supplied base rates - all '+name+' segments', ['Segment', 'WACC' if name=='industrial' else 'Cost of equity', 'Terminal growth (g)' if name=='industrial' else 'Terminal ROE'],
                         [[segment['name'],bound(f'input.{name}.{j}.{first}',True),bound(f'input.{name}.{j}.{second}',True)] for j,segment in enumerate(data[name])])
        baseline['caption_html']='Rates in percent. Shifts below are additive percentage points (pp).'
        grid['title']='Conditional parent equity - joint shifts within the selected method'
        grid['headers']=['WACC shift ↓ / g shift → (pp)' if name=='industrial' else 'Cost of equity shift ↓ / ROE shift → (pp)']+[h.replace('%',' pp') for h in grid['headers'][1:]]
        for row in grid['rows']: row[0]=row[0].replace('%',' pp')
        grid['base_cell']=[2,3]
        grid['caption_html']=escape(unit+' | BASE = zero shifts; outlined and labeled.')
        context = dict(kind='paragraph',html=escape('Shift scope: all '+name+' segments listed above move together. '+('Finance' if name=='industrial' else 'Industrial')+' segments and parent-level adjustments remain fixed.'))
        s['blocks']=[baseline,context]+s['blocks']
    if 'reverse' in sections:
        for b in sections['reverse']['blocks']:
            if b['kind']=='table':
                for row in b['rows']:
                    if row[0]=='Implied uniform EBIT margin shift':
                        row[0]='Additive EBIT margin change (pp)'
                        cell=row[1];old=cell['text'];new=old.replace('%',' pp')
                        cell['text']=new;cell['html']=cell['html'].replace(old,new)
                        for binding in bindings:
                            if binding['path']=='diagnostics.implied_margin_shift':binding['display']=new
                        b['caption_html']=escape('Margin change in percentage points; repriced equity in '+unit+'.')

    if 'chart' in sections:
        s=sections['chart'];s['title']='가치 규모 비교 - 합산 불가' if document['language']=='ko' else 'Value magnitudes - not additive'
        s['lead']='Enterprise value, equity and NCI have separate roles. All amounts in '+unit+'.'
        chart=s['blocks'][0]['chart'];chart.update(type='role-bars',title='Non-additive comparison: EV, equity and deduction magnitude',unit=unit,
            categories=['Industrial EV','Finance equity','Valued NCI','Parent equity'],
            roles=['Operating EV / cash-flow valuation','Finance equity / input to bridge','DEDUCTION / magnitude shown','RESULT / after bridge adjustments'])
        document['chart']=chart

    if 'consolidation' in sections:
        for b in sections['consolidation']['blocks']:
            if b['kind']=='table':
                for row in b['rows']:
                    row[0]=row[0].capitalize().replace('Ebit','EBIT').replace('ebit','EBIT').replace('Finance book','Finance book equity').replace('finance book','finance book equity')

    # Compact summary retains the authored argument and its adjacent qualification.
    summary=sections.get('narrative-decision',sections.get('conclusion'))
    if summary:
        summary['category']='CONDITIONAL RESULT'
        summary['summary']=dict(kind='summary-result',html=bound('bridge.parent_equity')['html'],label='조건부 지배주주 지분가치' if document['language']=='ko' else 'Conditional parent equity',unit=unit,qualification=document['status'])
    if 'narrative-argument' in sections and summary:
        sections['narrative-argument']['join_previous']=True
    if 'sensitivity-finance' in sections and 'sensitivity-industrial' in sections:
        sections['sensitivity-finance']['join_previous']=True
    if 'chart' in sections and 'reverse' in sections:
        sections['chart']['join_previous']=True
    document['scope']=data['valuation_date']+' | '+unit+'; share prices in '+currency+'/share'
    notes=sections.get('model-conditions')
    if notes:
        notes['blocks'].insert(0,dict(kind='source-note',html=escape('Reading conventions: Korean section navigation and supplied narrative; English financial exhibit labels. EV = enterprise value; NCI = noncontrolling interests; RI = residual income; P/B = price/book; pp = percentage points.')))
    return document
