#!/usr/bin/env python3
"""Read an existing run through its own pinned release; never activate or migrate it."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from common import PACKAGE, runtime_env, runtime_python


PROFILE = r'''
from dataclasses import asdict
import json
from pathlib import Path
import sys
root, directory = map(Path, sys.argv[1:3])
sys.path.insert(0, str(root))
from pr.engine import Run
from pr.package import verify
from pr.performance import profile_run
from pr.util import digest
manifest = verify(root)
before = {name: digest(directory / name) for name in ('run.json', 'events.jsonl')}
run = Run(directory)
run._check_pin()
if run.registry.root != root or manifest['release_id'] != run.header['release_sha256']:
    raise ValueError('Pinned release identity mismatch')
result = profile_run(run)
result['snapshot'] = asdict(result['snapshot'])
after = {name: digest(directory / name) for name in before}
if after != before:
    raise ValueError('Run header or ledger changed during profiling; retry on a stable snapshot')
result['provenance'] = dict(run=str(directory), package_root=str(root),
    release_id=manifest['release_id'], version=manifest['version'],
    header_sha256=before['run.json'], ledger_sha256=before['events.jsonl'],
    classification='read-only diagnostics; not full-report acceptance')
print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='New JSON file outside the run and package')
    args = parser.parse_args(argv)
    try:
        directory = args.run.expanduser().resolve()
        header = json.loads((directory / 'run.json').read_text(encoding='utf-8'))
        root = Path(header['package_root'])
        if not root.is_absolute():
            raise ValueError('Run must identify an absolute pinned installed root')
        root = root.resolve()
        if root == PACKAGE or root.is_relative_to(PACKAGE):
            raise ValueError('Refuse checkout package as an installed run release')
        if not (root / 'release.json').is_file():
            raise ValueError('Pinned immutable release unavailable; do not substitute the active release')
        output = args.out.expanduser().resolve()
        if any(output == p or output.is_relative_to(p) for p in (directory, root, PACKAGE)):
            raise ValueError('Output must be outside the run and immutable package/release')
        if output.exists():
            raise ValueError('Use a new output file')
        python = runtime_python()
        if not python.is_file():
            raise ValueError('Project runtime unavailable; run existing setup first')
        proc = subprocess.run([str(python), '-I', '-B', '-c', PROFILE,
                               str(root), str(directory)], cwd=root,
                              env=runtime_env(), capture_output=True, text=True,
                              timeout=120)
        if proc.returncode:
            raise ValueError('Pinned profiler failed: ' + proc.stderr.strip())
        result = json.loads(proc.stdout)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as handle:
            json.dump(result, handle, ensure_ascii=False, allow_nan=False, indent=2)
            handle.write('\n')
        print(json.dumps(dict(output=str(output), release_id=result['provenance']['release_id'],
                              attempts=len(result['attempts']), classification='read-only diagnostics')))
        return 0
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(error=type(exc).__name__, message=str(exc))), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
