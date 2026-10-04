"""Numeric retention checks; deliberately no source or financial review claim."""
from collections import Counter
from html.parser import HTMLParser
import math


class BindingParser(HTMLParser):
    def __init__(self):
        super().__init__();self.bindings=[];self.charts=[];self.active=None;self.text=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'data-result-path' in attrs:
            self.active=attrs['data-result-path'];self.text=[]
        if 'data-chart-value' in attrs:self.charts.append(float(attrs['data-chart-value']))
    def handle_data(self,data):
        if self.active:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='span' and self.active:
            self.bindings.append((self.active,''.join(self.text)));self.active=None


def verify_html(path,bindings,chart):
    parser=BindingParser();parser.feed(path.read_text())
    wanted=Counter((b['path'],b['display']) for b in bindings)
    got=Counter(parser.bindings)
    charts=chart if isinstance(chart,list) else [chart]
    expected=[v for item in charts for s in item['series'] for v in s['values']]
    chart_ok=len(expected)==len(parser.charts) and all(math.isclose(a,b,abs_tol=1e-9) for a,b in zip(expected,parser.charts))
    return dict(passed=wanted==got and chart_ok,expected_bindings=sum(wanted.values()),
                actual_bindings=sum(got.values()),missing=list((wanted-got).elements()),
                unexpected=list((got-wanted).elements()),chart_matches=chart_ok,
                scope='Exact generated binding multiplicities and chart values only; no independent source or financial review.')
