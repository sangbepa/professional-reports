"""Safe, numerically bound author narrative and optional calculated-section order.

No prose is generated here. Semantic arguments belong to the report's authors;
this module never upgrades their review status.
"""
from collections import Counter
from html import escape
import re

TOKEN=re.compile(r'\{\{(model|input|context):([A-Za-z0-9_.-]+)(?:\|(amount|percent|integer|raw))?\}\}')
FORMATS={'amount':lambda x:f'{x:,.2f}','percent':lambda x:f'{x:.2%}',
         'integer':lambda x:f'{x:,.0f}','raw':str}


def compose(data,result,calculated,bindings):
    config=data.get('report',{})
    language=config.get('language','en' if data['synthetic'] else 'ko')
    provided=config.get('report_sections',[])
    registered={item['source']['id'] for item in result['input_metadata'].values()}
    context={k:result[k] for k in ('company','valuation_date','currency','amount_scale','horizon')}
    context['review_status']='재무 검토 미수행' if language=='ko' else 'Financial review unperformed'

    def substitute(text,html=True):
        # Literal digits (including Unicode digits) cannot bypass the numeric binding.
        rest=TOKEN.sub('',text)
        if '{{' in rest or '}}' in rest or any(c.isnumeric() for c in rest):
            raise ValueError('Narrative numbers require {{model:path|format}}, {{input:path|format}} or {{context:key}} placeholders')
        parts=[];position=0
        for match in TOKEN.finditer(text):
            namespace,path,fmt=match.groups();fmt=fmt or 'amount'
            if namespace=='model':
                if path not in result['values']:raise ValueError('Unknown narrative model path: '+path)
                value=result['values'][path];binding_path=path;unit=result['units'][path]
            elif namespace=='input':
                if path not in result['input_metadata']:raise ValueError('Unknown narrative input path: '+path)
                value=result['input_metadata'][path]['value'];binding_path='input.'+path;unit=result['input_metadata'][path]['unit']
            else:
                if path not in context:raise ValueError('Unknown narrative context: '+path)
                value=context[path];binding_path='context.'+path;unit='context'
            if fmt=='percent' and unit!='ratio':raise ValueError('Percent formatting requires a ratio-valued model/input path')
            display=FORMATS[fmt](value) if isinstance(value,(int,float)) else str(value)
            literal=text[position:match.start()]
            parts.append(escape(literal) if html else literal)
            if html:
                parts.append(f'<span data-result-path="{escape(binding_path)}">{escape(display)}</span>')
                bindings.append(dict(path=binding_path,value=value,display=display))
            else:
                # Headings are escaped by the native constructor and cannot carry spans.
                # Numeric claims belong in body blocks, where retention is auditable.
                if isinstance(value,(int,float)):raise ValueError('Numeric claims belong in body blocks, not narrative titles/leads')
                parts.append(display)
            position=match.end()
        parts.append(escape(text[position:]) if html else text[position:])
        return ''.join(parts)

    authored={}
    for section in provided:
        key='narrative:'+section['id']
        if key in authored:raise ValueError('Duplicate narrative section ID: '+section['id'])
        blocks=[]
        for block in section['blocks']:
            unknown=set(block['evidence_ids'])-registered
            if unknown:raise ValueError('Unknown evidence IDs in narrative: '+', '.join(sorted(unknown)))
            if block['kind']=='evidence' and not block['evidence_ids']:
                raise ValueError('Evidence blocks require registered input source IDs')
            body=substitute(block['text'])
            if block['evidence_ids']:
                label='근거' if language=='ko' else 'Evidence'
                body+=' <small>('+label+': '+escape(', '.join(block['evidence_ids']))+')</small>'
            kind={'argument':'paragraph','evidence':'source-note','condition':'finding','paragraph':'paragraph'}[block['kind']]
            blocks.append(dict(kind=kind,html=body))
        authored[key]=dict(id='narrative-'+section['id'],title=substitute(section['title'],False),
                           lead=substitute(section['lead'],False),blocks=blocks)
    generated={'calculated:'+section['id']:section for section in calculated}
    order=config.get('section_order')
    if order:
        if len(set(order))!=len(order):raise ValueError('Duplicate section in report.section_order')
        missing=set(authored)-set(order)
        if missing:raise ValueError('Supplied narrative sections omitted from order: '+', '.join(sorted(missing)))
        unknown=set(order)-(set(authored)|set(generated))
        if unknown:raise ValueError('Unknown section selection: '+', '.join(sorted(unknown)))
        combined=authored|generated;selected=[combined[key] for key in order]
    else:selected=list(authored.values())+calculated
    if provided or order:
        # Selection may omit the calculated conclusion; qualifications still travel.
        selected.append(dict(id='model-conditions',title='모형 적용 조건과 검토 상태' if language=='ko' else 'Model conditions and review status',
            lead='재무 검토 미수행' if language=='ko' else 'Financial review unperformed',
            blocks=[dict(kind='paragraph',html=escape(w)) for w in result['warnings']]))
    if language=='ko':
        titles={'conclusion':'조건부 평가 결과','timing':'평가기준일과 현금흐름 시점','bridge':'기업가치에서 지배주주 지분가치로',
                'consolidation':'연결 조정과 대사','rights':'주식 종류별 경제적 권리','sensitivity-industrial':'산업부문 민감도',
                'sensitivity-finance':'금융부문 민감도','reverse':'역산 진단','chart':'가치 구성요소'}
        for section in selected:
            if section['id'] in titles:section['title']=titles[section['id']]
    # Remove bindings belonging to deliberately unselected calculated sections.
    try:
        from .verify import BindingParser
    except ImportError:
        from verify import BindingParser
    parser=BindingParser()
    for section in selected:
        for block in section['blocks']:
            parser.feed(block.get('html',''))
            for row in block.get('rows',[]):
                for value in row:
                    if isinstance(value,dict):parser.feed(value.get('html',''))
    counts=Counter(parser.bindings);retained=[]
    for binding in bindings:
        key=binding['path'],binding['display']
        if counts[key]>0:retained.append(binding);counts[key]-=1
    if any(counts.values()):raise ValueError('Untracked narrative numeric binding')
    return selected,retained,language
