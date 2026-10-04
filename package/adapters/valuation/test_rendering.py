"""Rendering-only regression tests, independent of model calculation."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from collections import Counter

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from report import prepare
from verify import BindingParser
sys.path.insert(0,str(HERE/'vendor/report_outfit'))
spec=importlib.util.spec_from_file_location('build',HERE/'vendor/report_outfit/build.py')
native=importlib.util.module_from_spec(spec);sys.modules['build']=native;spec.loader.exec_module(native)
from full_report import document

class RenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frozen=HERE/'.validation/final-synthetic-cross-company'
        cls.data=json.loads((frozen/'input.json').read_text())
        cls.result=json.loads((frozen/'model-result.json').read_text())
        cls.old=json.loads((frozen/'report-bindings.json').read_text())['cells']

    def test_frozen_inputs_and_original_numeric_occurrences_survive(self):
        data,result=copy.deepcopy(self.data),copy.deepcopy(self.result)
        report,bindings=prepare(data,result)
        self.assertEqual(data,self.data);self.assertEqual(result,self.result)
        key=lambda b:(b['path'],str(b['value']))
        self.assertFalse(Counter(map(key,self.old))-Counter(map(key,bindings)))
        for design in native.DESIGNS:
            html,_=document(report,design);parsed=BindingParser();parsed.feed(html)
            self.assertEqual(Counter(parsed.bindings),Counter((b['path'],b['display'])for b in bindings))
            self.assertEqual(parsed.charts,[self.result['values'][p] for p in ('bridge.industrial_enterprise_value','bridge.finance_equity','bridge.nci','bridge.parent_equity')])

    def test_summary_metadata_preserves_authored_blocks_order_and_escaping(self):
        frozen=json.loads((HERE/'.validation/final-synthetic-cross-company/report-input.json').read_text())
        report,_=prepare(self.data,self.result)
        for old,new in zip(frozen['report_sections'][:2],report['report_sections'][:2]):
            self.assertEqual(old['blocks'],new['blocks'])
        self.assertIn('summary',report['report_sections'][0])
        data=copy.deepcopy(self.data)
        data['report']['report_sections'][0]['blocks'][0]['text']='<script>alert("x")</script> debt_like: supplied prose'
        report,_=prepare(data,self.result)
        body=report['report_sections'][0]['blocks'][0]['html']
        self.assertEqual(body,'&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; debt_like: supplied prose')
        html,_=document(report,'transaction')
        self.assertIn(body,html)
        self.assertNotIn('<script>alert',html)

    def test_bridge_operations_and_memo_are_not_ambiguous(self):
        report,_=prepare(self.data,self.result)
        s=next(s for s in report['report_sections'] if s['id']=='bridge')
        main,memo=s['blocks'][:2]
        self.assertEqual(len(main['rows']),12)
        self.assertEqual(main['row_roles'][-3:],['subtotal','deduction','result'])
        paths=[row[1]['html'] for row in main['rows']]
        self.assertTrue(any('input.bridge.parent_liabilities' in p for p in paths))
        self.assertIn('Less parent liabilities',[r[0]for r in main['rows']])
        self.assertIn('finance_funding_debt_excluded',memo['rows'][0][1]['html'])
        self.assertFalse(any('finance_funding_debt_excluded' in p for p in paths))

    def test_every_sensitivity_segment_has_bound_baselines_and_base_marker(self):
        report,_=prepare(self.data,self.result)
        for name in ('industrial','finance'):
            section=next(s for s in report['report_sections'] if s['id']=='sensitivity-'+name)
            baseline,context,grid=section['blocks'][:3]
            self.assertEqual(len(baseline['rows']),len(self.data[name]))
            self.assertIn('all '+name,context['html'])
            self.assertEqual(grid['base_cell'],[2,3])
            html=native.table(dict(key='financial_detail',rich=True,**grid))
            self.assertEqual(html.count('base-marker'),1)
            self.assertIn('percentage points',baseline['caption_html'])

    def test_role_chart_uses_each_native_palette_and_handles_negative_values(self):
        report,_=prepare(self.data,self.result);chart=copy.deepcopy(report['chart'])
        chart['series'][0]['values']=[-200,0,30,100]
        rendered=[native.chart({'chart':chart,'key':'financial_detail'},design) for design in native.DESIGNS]
        self.assertEqual(len(set(rendered)),3)
        for html in rendered:
            self.assertIn('DEDUCTION / magnitude shown',html);self.assertIn('RESULT / after bridge adjustments',html)
            self.assertIn('USD million',html)
            parsed=BindingParser();parsed.feed(html);self.assertEqual(parsed.charts,[-200,0,30,100])
            self.assertNotIn('="nan',html.lower())

    def test_reader_labels_and_pp_diagnostic(self):
        report,bindings=prepare(self.data,self.result)
        html,_=document(report,'transaction')
        for internal in ('explicit_stub','debt_like','pari_passu_fixed_then_weighted_residual','분석을 지지하는 재무정보'):
            self.assertNotIn(internal,html)
        self.assertIn('Participation (weighted shares)',html)
        self.assertIn('USD/share',html)
        self.assertIn('-5.05 pp',html)
        self.assertIn('summary-result',html)
        self.assertEqual([b['value']for b in bindings if b['path']=='diagnostics.implied_margin_shift'],[self.result['values']['diagnostics.implied_margin_shift']])

if __name__=='__main__':unittest.main()
