#!/usr/bin/env python3
"""Generate a synthetic fixture only; no company research or financial approval."""
import argparse
from pathlib import Path
from common import ROOT,DEFAULT_STATE,run
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--state',type=Path,default=DEFAULT_STATE);p.add_argument('--render',action='store_true');a=p.parse_args()
out=a.out.expanduser().resolve()
if out.exists():p.error('Use a new output directory')
raise SystemExit(run(['adapters/valuation/build.py','--input','adapters/valuation/examples/synthetic-stub.json','--out',str(out),'--xlsx-engine','openpyxl','--recalc','required' if a.render else 'skip','--pdf','required' if a.render else 'skip','--design','executive'],a.state.expanduser().resolve()))
