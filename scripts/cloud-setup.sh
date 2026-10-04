#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v soffice >/dev/null 2>&1; then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo 'Install LibreOffice with your operating-system package manager.' >&2
    exit 1
  fi
  if [ "$(id -u)" = 0 ]; then
    apt-get update
    apt-get install -y --no-install-recommends libreoffice-calc
  else
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends libreoffice-calc
  fi
fi
python3 scripts/setup.py --activate-development --with-browser --with-system-deps
python3 scripts/verify.py
