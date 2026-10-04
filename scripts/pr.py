#!/usr/bin/env python3
"""Execute the CLI from the active, verified project-local release."""
import argparse,sys
from pathlib import Path
from common import DEFAULT_STATE,run
if sys.argv[1:]==['--help']:raise SystemExit(run(['-m','pr','--help']))
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,default=DEFAULT_STATE);p.add_argument('args',nargs=argparse.REMAINDER)
a=p.parse_args()
if not a.args:p.error('CLI arguments required, e.g. catalog or doctor')
raise SystemExit(run(['-m','pr',*a.args],a.state.expanduser().resolve()))
