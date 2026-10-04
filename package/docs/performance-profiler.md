# Focused performance profiler

`pr.performance` provides read-only diagnostics. It does not enforce deadlines,
change quality requirements, combine review roles, select a workflow, or mutate
plans or old ledgers. Package development/setup can be unlimited; the separate
intake/deadline owner determines which time counts toward an actual full report.
The reference report target is 300 seconds and ceiling is 600 seconds. A positive
estimated slack is not evidence that either goal has been achieved.

## Plan estimates

```python
from pr.performance import analyze_plan
analysis = analyze_plan(pm_plan, {
    'task-id': {'seconds': 40, 'kind': 'hypothetical',
                'provenance': 'Planner assumption; not a benchmark'},
}, workers=3)
```

Supply every node's duration explicitly, in seconds. Node IDs and `depends_on`
are read from the arbitrary PM plan. Estimates may be numeric (marked
hypothetical with unknown provenance), or records containing `seconds`, `kind`
(`measured`, `hypothetical`, `unknown`) and `provenance`. Measured inputs require
provenance but still represent estimates for a future run. `None`, missing
entries, and unknown-kind entries prevent all aggregate projections; no guessed
replacement durations are used. Invalid numbers, duplicate nodes, unknown
dependencies, cycles and unknown estimate IDs raise `ContractError`.

The worker limit is an integer from 1 to 6; pass any lower host limit explicitly.
The output contains a critical path and its length, total work, work divided by
workers, their combined lower bound, and a deterministic non-preemptive lexical
ready-list schedule. Negative slack means the estimate exceeds the stated
budget. All bounds are conditional on supplied durations and graph completeness.
The model assumes interchangeable workers, no resource conflicts beyond worker
count, and no extra scheduling/communication latency. Include needed overhead
and review nodes in the PM plan. Real retries, model latency and missing work can
invalidate the projection. The profiler never removes dependencies or reviews.

## Existing run observations

```python
from pr.performance import profile_run
profile = profile_run(existing_run)
```

Prefer a supplied Run loaded by its pinned installed version. For historical
runs, obtain that Run in a separate interpreter using its installed package;
do not construct it with a newly edited engine, reactivate a package, migrate the
ledger, or write profiling events. This module deliberately has no path loader.
It reads the supplied in-memory event prefix and immutable attempt/binding/result
objects through Run's read helpers. It does not refresh the Run. Supply a freshly
loaded, validated Run when a current snapshot is required.

`timing` is the unmodified result of that Run's `timing()` on a detached event
copy; deadline slack uses its `report_seconds`. Thus pinned versions retain their
own intake/environment-wait rules. The profiler does not retroactively apply a
new deadline policy. Consult timing anomalies/uncertainty before interpreting
slack. The live timing horizon can be later than the captured event tail.

Every dispatch retains its actual attempt ID, including failed and retried
attempts sharing a node ID. Attempted intervals run from dispatch to the first
result, failure or release. Execution intervals run from binding to that endpoint
for agent nodes only; they are **observed bound-agent elapsed**, not true compute
time or proof of continuous activity. Unbound agents are unknown, not assigned
execution time. Review-worker execution is kept distinct from target review wait
(submission pending review through first decision/failure). Further decisions
remain in the immutable event snapshot; this wait metric does not infer new
execution periods between decisions. Open intervals are marked censored at the
event tail. Failures retain their event data, including post-submission failures.

Each interval category reports union walltime, walltime with at least two
concurrent intervals, summed durations, and excess concurrency. Categories can
overlap and must not be added together. The observation window starts at the
first captured event and ends at the tail. Non-task gaps are its complement of
attempted intervals; unobserved-agent gaps are its complement of bound-agent
intervals. Neither proves idle time. Preledger intake and post-tail activity are
outside these gap metrics and remain visible through authoritative Run timing.

Same-boot observations use monotonic timestamps. Other cases explicitly use
uncertain UTC fallback; backward clocks raise rather than fabricate walltime.
Model fields are copied as recorded, without promoting requested/resolved models
to observed identity. Missing models, actual cost and true compute time remain
unknown (`None`); usage is available only as recorded by Run.timing.

`EventSnapshot` is frozen and contains detached canonical event JSON, its SHA-256,
event count and the exact tail sequence/hash. This fingerprints the captured
prefix, not the later live ledger or independent validation of its hash chain.
It performs no writes and makes no cryptographic claim about the original host.

## Validation

Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_performance.py -v`.
The tests use synthetic clocks, parallelism, retries, review waits, unknown
estimates, invalid DAGs, zero-duration tasks and snapshot isolation. They exercise
real Run.timing on a synthetic read-only Run and mock it for open-tail tests.
They do not execute reports, read holdouts, benchmark models or demonstrate
unchanged report quality or a 300/600-second production result.
