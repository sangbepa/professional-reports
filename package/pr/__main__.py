import argparse
import json
import sys
from pathlib import Path
from .engine import Run
from .registry import Registry
from .util import ContractError, read_json, write_json
from . import package, environment, evaluation, export, distribution


def main(argv=None):
    parser=argparse.ArgumentParser(description='professional-reports: deterministic package and native-host bridge')
    parser.add_argument('--root',default=str(Path(__file__).resolve().parent.parent))
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('catalog');sub.add_parser('doctor')
    p=sub.add_parser('load');p.add_argument('--state',required=True)
    p=sub.add_parser('pack');p.add_argument('--out',required=True);p.add_argument('--version',required=True);p.add_argument('--channel',choices=['development','validated'],default='development');p.add_argument('--acceptance')
    p=sub.add_parser('verify');p.add_argument('--release',required=True)
    p=sub.add_parser('install');p.add_argument('--release',required=True);p.add_argument('--state',required=True)
    p=sub.add_parser('activate');p.add_argument('--state',required=True);p.add_argument('--release-id',required=True);p.add_argument('--development',action='store_true')
    p=sub.add_parser('rollback');p.add_argument('--state',required=True)
    p=sub.add_parser('archive');p.add_argument('--release',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('marketplace');p.add_argument('--release',required=True);p.add_argument('--out',required=True);p.add_argument('--name',default='professional-reports-local')
    p=sub.add_parser('run');p.add_argument('--path',required=True);p.add_argument('--request',required=True)
    for name in ('meta','plan','bind','submit','review'):
        p=sub.add_parser(name);p.add_argument('--run',required=True);p.add_argument('--file',required=True)
    for name in ('status','next','export','finish'):
        p=sub.add_parser(name);p.add_argument('--run',required=True)
    p=sub.add_parser('dispatch');p.add_argument('--run',required=True);p.add_argument('--node',required=True);p.add_argument('--support',required=True);p.add_argument('--out')
    p=sub.add_parser('snapshot');p.add_argument('--run',required=True);p.add_argument('--id',required=True);p.add_argument('--file',required=True);p.add_argument('--fields',nargs='+',required=True);p.add_argument('--kind',default='data')
    p=sub.add_parser('source');p.add_argument('--run',required=True);p.add_argument('--file',required=True);p.add_argument('--fields',nargs='+',required=True)
    p=sub.add_parser('invalidate');p.add_argument('--run',required=True);p.add_argument('--fields',nargs='+',required=True);p.add_argument('--reason',required=True)
    p=sub.add_parser('fail');p.add_argument('--run',required=True);p.add_argument('--attempt',required=True);p.add_argument('--reason',required=True);p.add_argument('--kind',default='failed')
    p=sub.add_parser('quality');p.add_argument('--run',required=True);p.add_argument('--file',required=True)
    p=sub.add_parser('release-worker');p.add_argument('--run',required=True);p.add_argument('--attempt',required=True);p.add_argument('--receipt',required=True)
    p=sub.add_parser('close-finding');p.add_argument('--run',required=True);p.add_argument('--file',required=True)
    p=sub.add_parser('environment-wait');p.add_argument('--run',required=True);p.add_argument('--capabilities',nargs='+',required=True);p.add_argument('--reason',required=True)
    p=sub.add_parser('environment-ready');p.add_argument('--run',required=True);p.add_argument('--file',required=True)
    p=sub.add_parser('experiment');p.add_argument('--folder',required=True);p.add_argument('--spec',required=True)
    p=sub.add_parser('pair');p.add_argument('--folder',required=True);p.add_argument('--file',required=True)
    p=sub.add_parser('experiment-verdict');p.add_argument('--folder',required=True);p.add_argument('--holdout',required=True)
    p=sub.add_parser('risk-register');p.add_argument('--run',required=True);p.add_argument('--file',required=True);p.add_argument('--profile',required=True)
    for name in ('risk-review','risk-procedure','cost-observe'):
        p=sub.add_parser(name);p.add_argument('--run',required=True);p.add_argument('--file',required=True)
    for name in ('risk-status','cost-status'):
        p=sub.add_parser(name);p.add_argument('--run',required=True)
    for name in ('sensitivity','valuation-sensitivity','cost'):
        p=sub.add_parser(name);p.add_argument('--file',required=True);p.add_argument('--out',required=True)
    for name in ('esg-prepare','esg-build','esg-check'):
        p=sub.add_parser(name,help='Standalone ESG learning adapter; no production ESG completion',
                         description='Delegate to pr.esg for a public-source learning report, outside Run.finish.')
        p.add_argument('--input',required=True,help='Learning-report request JSON')
        p.add_argument('--out',required=True,help='Adapter output directory')
    p=sub.add_parser('esg-system',help='Reusable public-source ESG corpus, DuckDB and report workflow')
    p.add_argument('args',nargs=argparse.REMAINDER,help='Arguments forwarded to pr.esg_system')
    for name in ('risk-experiment','risk-experiment-adopt','risk-pair'):
        p=sub.add_parser(name);p.add_argument('--folder',required=True);p.add_argument('--file',required=True)
    p=sub.add_parser('risk-verdict');p.add_argument('--folder',required=True)
    a=parser.parse_args(argv);c=a.command
    try:
        if c=='catalog':result=Registry(a.root).catalog()
        elif c=='doctor':result=environment.doctor()
        elif c=='load':result=package.load_active(a.state)
        elif c=='pack':result=package.pack(a.root,a.out,a.version,a.channel,read_json(a.acceptance) if a.acceptance else None)
        elif c=='verify':result=package.verify(a.release)
        elif c=='install':result=package.install(a.release,a.state)
        elif c=='activate':result=package.activate(a.state,a.release_id,a.development)
        elif c=='rollback':result=package.rollback(a.state)
        elif c=='archive':result=package.archive(a.release,a.out)
        elif c=='marketplace':result=distribution.marketplace(a.release,a.out,a.name)
        elif c=='run':result=Run.create(a.path,a.root,read_json(a.request)).header
        elif c=='experiment':result=evaluation.preregister(a.root,a.folder,read_json(a.spec))
        elif c=='pair':result=evaluation.record_pair(a.folder,read_json(a.file))
        elif c=='experiment-verdict':result=evaluation.verdict(a.folder,read_json(a.holdout))
        elif c in {'esg-prepare','esg-build','esg-check'}:
            try:
                from . import esg
            except ImportError as exc:
                raise ContractError('ESG learning adapter unavailable; install a release containing pr.esg and its documented dependencies') from exc
            # The standalone adapter owns validation, output and its exit status.
            # --root selects engine definitions; it never switches imported code.
            return esg.main([c.removeprefix('esg-'),'--input',a.input,'--out',a.out])
        elif c=='esg-system':
            from . import esg_system
            return esg_system.main(a.args)
        elif c in {'sensitivity','valuation-sensitivity','cost'}:
            from . import sensitivity, valuation_sensitivity, cost
            operation={'sensitivity':sensitivity.analyze,'valuation-sensitivity':valuation_sensitivity.analyze,'cost':cost.summarize}[c]
            value = operation(read_json(a.file))
            write_json(a.out,value)
            from .util import digest
            result = dict(path=a.out,sha256=digest(a.out))
        elif c in {'risk-experiment','risk-experiment-adopt','risk-pair','risk-verdict'}:
            from . import risk_experiment
            if c=='risk-verdict':result=risk_experiment.verdict(a.folder)
            else:
                operation={'risk-experiment':risk_experiment.preregister,'risk-experiment-adopt':risk_experiment.adopt,'risk-pair':risk_experiment.record_pair}[c]
                result=operation(a.folder,read_json(a.file))
        else:
            run=Run(a.run)
            if c=='meta':result=run.register_meta(read_json(a.file))
            elif c=='plan':result=run.register_plan(read_json(a.file))
            elif c in {'bind','submit','review'}:result=getattr(run,c)(read_json(a.file))
            elif c=='next':result=run.ready()
            elif c=='status':result=dict(states=run.states(),readiness=run.readiness())
            elif c=='export':result=export.export(run)
            elif c=='finish':result=run.finish()
            elif c=='dispatch':
                result=run.dispatch(a.node,read_json(a.support))
                if a.out:write_json(a.out,result)
            elif c=='snapshot':result=run.snapshot(a.id,a.file,a.fields,a.kind)
            elif c=='source':result=run.source(read_json(a.file),a.fields)
            elif c=='invalidate':result=run.invalidate(a.fields,a.reason)
            elif c=='fail':result=run.fail(a.attempt,a.reason,a.kind)
            elif c=='quality':result=run.quality(**read_json(a.file))
            elif c=='release-worker':result=run.release_worker(a.attempt,read_json(a.receipt))
            elif c=='close-finding':result=run.close_finding(**read_json(a.file))
            elif c=='environment-wait':result=run.environment_wait(a.capabilities,a.reason)
            elif c=='environment-ready':result=run.environment_ready(read_json(a.file))
            elif c=='risk-register':result=run.register_risk(read_json(a.file),a.profile)
            elif c=='risk-review':result=run.review_risk(read_json(a.file))
            elif c=='risk-procedure':result=run.record_procedure(read_json(a.file))
            elif c=='risk-status':result=run.risk_status()
            elif c=='cost-observe':result=run.record_cost(read_json(a.file))
            elif c=='cost-status':result=run.cost_status()
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 0
    except (ContractError,FileNotFoundError,KeyError) as exc:
        print(json.dumps(dict(error=type(exc).__name__,message=str(exc)),ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
