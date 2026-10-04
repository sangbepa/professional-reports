#!/usr/bin/env python3
"""Verify and display the exact project-local installed release, without activation."""
import argparse,json
from pathlib import Path
from common import DEFAULT_STATE,bootstrap
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,default=DEFAULT_STATE);a=p.parse_args()
print(json.dumps(bootstrap(a.state.expanduser().resolve()),ensure_ascii=False,indent=2))
