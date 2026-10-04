#!/usr/bin/env python3
"""Standalone launcher; supports an explicit installed release from any cwd."""
import os
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[3]
for i, value in enumerate(sys.argv[1:], 1):
    if value == '--release':
        root = Path(sys.argv[i + 1]).expanduser().resolve()
        break
    if value.startswith('--release='):
        root = Path(value.split('=', 1)[1]).expanduser().resolve()
        break
os.execv(sys.executable, [sys.executable, str(root / 'pr/report_path.py'), *sys.argv[1:]])
