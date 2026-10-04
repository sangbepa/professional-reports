"""Report deadline monitor. Native cancellation and user delivery remain host work."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from .engine import Run
from .util import ContractError, write_json


def inspect(run):
    run = Run(run.path if isinstance(run, Run) else run)
    run._check_pin()
    finished = run._latest('run_finished')
    exhaustion = run._latest('report_budget_exhausted')
    return dict(run=str(run.path), budget=run.budget(), finished=finished,
                cancel_agents=(exhaustion or {}).get('cancel_agents', []),
                event_tail=run.events[-1]['sha256'],
                delivery_confirmed=False, worker_cancellation_confirmed=False)


def watch(run_path, poll_seconds=0.5, receipt_out=None):
    if not 0.05 <= poll_seconds <= 5:
        raise ContractError('Poll interval must be between 0.05 and 5 seconds')
    while True:
        state = inspect(run_path)
        if state['finished']:
            state['action'] = 'already_finished'
            break
        if not state['budget']['enforced']:
            state['action'] = 'package_development_unbounded'
            break
        if state['budget']['stop_work']:
            try:
                state.update(Run(run_path).deadline_checkpoint())
            except ContractError:
                # Another monitor/host may seal the same run under its lock.
                current = inspect(run_path)
                if not current['finished']:
                    raise
                state = dict(current, action='already_finished')
            state['event_tail'] = Run(run_path).events[-1]['sha256']
            break
        time.sleep(min(poll_seconds, state['budget']['work_remaining_seconds']))
    if receipt_out:
        write_json(receipt_out, state)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'watch', 'checkpoint'])
    parser.add_argument('--run', required=True)
    parser.add_argument('--poll-seconds', type=float, default=0.5)
    parser.add_argument('--receipt-out', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == 'watch':
            result = watch(args.run, args.poll_seconds, args.receipt_out)
        else:
            result = inspect(args.run)
            if args.action == 'checkpoint' and not result['finished']:
                result.update(Run(args.run).deadline_checkpoint())
                result['event_tail'] = Run(args.run).events[-1]['sha256']
            if args.receipt_out:
                write_json(args.receipt_out, result)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ContractError, OSError, KeyError) as exc:
        print(json.dumps(dict(error=type(exc).__name__, message=str(exc))), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
