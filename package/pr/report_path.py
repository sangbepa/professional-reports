"""Portable diagnostic lifecycle; supplied native receipts, never model emulation."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from pr.registry import Registry

AXES = {'evidence', 'economics', 'calculation', 'decision_usefulness', 'document_quality'}
ROLES = ('coordinator', 'author', 'reviewer')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_digest(data):
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def within(root, relative):
    path = Path(relative)
    resolved = (root / path).resolve()
    if path.is_absolute() or '..' in path.parts or not resolved.is_relative_to(root.resolve()):
        raise ValueError('Reference escapes installed root: ' + str(relative))
    return resolved


def files(root):
    result = {}
    for p in sorted(root.rglob('*')):
        if '__pycache__' in p.parts or p.suffix == '.pyc':
            continue
        if p.is_symlink():
            raise ValueError('Component symlinks are unsupported: ' + str(p))
        if p.is_file():
            result[p.relative_to(ROOT).as_posix()] = sha(p)
    return result


def environment():
    value = os.environ.get('PROFESSIONAL_REPORTS_ENV')
    if not value:
        raise ValueError('PROFESSIONAL_REPORTS_ENV must name an external host-runtime JSON file')
    path = Path(value).expanduser().resolve()
    data = read(path)
    for key in ('python', 'node', 'playwright'):
        if not isinstance(data.get(key), str) or not Path(data[key]).is_absolute() or not Path(data[key]).exists():
            raise ValueError('Host runtime must supply an existing absolute ' + key)
    if data.get('marker') and (not Path(data['marker']).is_absolute() or not Path(data['marker']).is_file()):
        raise ValueError('Configured marker is missing')
    return data, {'path': str(path), 'sha256': sha(path), 'configuration': data}


def configuration(case_id):
    adapter = ROOT / 'adapters/reverse-dcf'
    registered = read(adapter / 'cases.json')
    if case_id not in registered:
        raise ValueError('Unregistered case: ' + case_id)
    contract_path = within(adapter, registered[case_id])
    case = read(contract_path)
    if case.get('schema') != 'reverse-dcf-case/1' or case.get('case_id') != case_id:
        raise ValueError('Invalid case contract')
    for name, expected in case['originals'].items():
        if sha(within(contract_path.parent / 'original', name)) != expected:
            raise ValueError('Immutable original evidence changed: ' + name)
    registry = Registry(ROOT)
    ref = registry.reference('reverse-dcf-diagnostic')
    component, directory = registry.resolve(ref, 'orchestration')
    diagnostic = read(directory / component['entrypoint'])
    if diagnostic['supported_case'] != case_id:
        raise ValueError('Diagnostic contract does not support case')
    refs = {'diagnostic': ref, 'skill': registry.reference(diagnostic['entry_skill'])}
    paths = {}
    for role in ROLES:
        refs[role] = registry.reference(diagnostic['roles'][role])
        data, path = registry.resolve(refs[role], 'persona')
        paths[role] = path / data['entrypoint']
    profile = ROOT / 'protected/reviewer-profiles' / diagnostic['protected_profile']
    criterion = profile / 'candidate-five-axis-anchors.md'
    components = {p: h for tree in (adapter, ROOT / 'adapters/report-publication/vendor',
                  ROOT / 'libraries/skills/financial-report-writing', profile,
                  ROOT / 'skills/reverse-dcf-report') for p, h in files(tree).items()}
    components['adapters/reverse-dcf/coordinator.js'] = sha(ROOT / 'adapters/reverse-dcf/coordinator.js')
    components['pr/report_path.py'] = sha(Path(__file__))
    components['pr/reverse_dcf.py'] = sha(ROOT / 'pr/reverse_dcf.py')
    # Bind the exact Registry implementation and its imported validation helpers.
    for name in ('registry.py', 'util.py', 'schema.py', 'report_checks.py', 'report_metrics.py'):
        components['pr/' + name] = sha(ROOT / 'pr' / name)
    components.update(files(ROOT / 'schemas'))
    for identity in refs.values():
        _, path = registry.resolve(identity)
        components.update(files(path))
    components.update(files(directory))
    release = None
    if (ROOT / 'release.json').exists():
        release = {'path': str(ROOT / 'release.json'), 'sha256': sha(ROOT / 'release.json'),
                   'manifest': read(ROOT / 'release.json')}
        manifest = release['manifest']
        unsigned = {k: v for k, v in manifest.items() if k != 'release_id'}
        encoded = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if hashlib.sha256(encoded.encode()).hexdigest() != manifest['release_id']:
            raise ValueError('Invalid installed release identity')
        for member in manifest['members']:
            if sha(within(ROOT, member['path'])) != member['sha256']:
                raise ValueError('Installed release member changed: ' + member['path'])
    return case, contract_path.parent, diagnostic, refs, paths, criterion, components, release


def current(out):
    attempt = read(out / 'attempt.json')
    cfg = configuration(attempt['case_id'])
    if str(ROOT) != attempt['installed_root'] or cfg[6] != attempt['component_sha256'] or cfg[7] != attempt['release'] or cfg[3] != attempt['registry_references']:
        raise ValueError('Pinned installed release/components/Registry references changed')
    env, recorded = environment()
    if recorded != attempt['environment']:
        raise ValueError('Host runtime changed during attempt')
    for name, field in [('author-packet.json','writer_packet_sha256'),('writer-scaffold.json','writer_scaffold_sha256')]:
        if sha(out/name) != attempt[field]:
            raise ValueError('Pinned writer input changed: '+name)
    if sha(out / 'dispatch.json') != attempt['dispatch_sha256']:
        raise ValueError('Dispatched prompts changed')
    if sha(out / 'coordinator-exec.js') != attempt['coordinator_exec_sha256']:
        raise ValueError('Generated coordinator execution harness changed')
    for relative, expected in attempt['analysis_sha256'].items():
        if sha(within(out, relative)) != expected:
            raise ValueError('Frozen calculation artifacts changed: ' + relative)
    return attempt, cfg, env


def execute(cmd, out, log, env):
    with (out / log).open('x', encoding='utf-8') as stream:
        subprocess.run(cmd, cwd=out, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)


def init(out, requested, case_id):
    requested = float(requested)
    if not math.isfinite(requested) or requested > time.time():
        raise ValueError('Request epoch must be finite and not in the future')
    if out.exists():
        raise ValueError('Output must be new; prior attempts cannot be reused')
    cfg = configuration(case_id)
    case, case_dir, diagnostic, refs, roles, criterion, components, release = cfg
    env, recorded = environment()
    started = time.time()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'analysis').mkdir()
    attempt = {'schema': 'reverse-dcf-attempt/1', 'candidate': read(ROOT/'plugin.json')['version'], 'attempt_id': str(uuid.uuid4()),
        'requested_epoch': requested, 'created_epoch': started, 'installed_root': str(ROOT),
        'case_id': case_id, 'release': release, 'component_sha256': components,
        'registry_references': refs, 'role_entrypoints': {k: str(v) for k, v in roles.items()},
        'criterion': {'path': str(criterion), 'sha256': sha(criterion)}, 'environment': recorded,
        'purpose': diagnostic['mandate'], 'full_valuation_checks_claimed_passed': False,
        'deadline_seconds': 600, 'work_cutoff_seconds': 585, 'environment_wait_excluded': 0}
    # Record failures before calculation, with no existing analysis/body/results reads.
    write(out / 'initial-attempt.json', attempt)
    if env.get('marker'):
        execute([env['node'], env['marker'], '--operation-kind', 'create', '--expected-output-count', '1', '--output-format', 'pdf'], out, 'marker.log', dict(os.environ))
    spec = importlib.util.spec_from_file_location('fresh_case_calculation', within(ROOT, case['calculator']))
    calc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calc)
    calc.OUT = out / 'analysis'
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        calc.main()
    (out / 'calculation.log').write_text(capture.getvalue(), encoding='utf-8')
    shutil.copyfile(within(ROOT, case['evidence']), out / 'analysis/comparison-evidence.json')
    # Original research documents are inputs, never prior report/results.
    sources = case_dir / 'source-originals'
    if sources.exists():
        validation = read(sources/'validation.json')
        for name, expected in validation['source_members'].items():
            if sha(within(sources,name)) != expected:
                raise ValueError('Frozen source-original changed: '+name)
        shutil.copytree(sources,out/'analysis/source-originals')
    execute([env['python'], str(within(ROOT, case['stress_calculator'])), str(out)], out, 'stress.log', dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    execute([env['python'], str(ROOT / 'adapters/reverse-dcf/runtime-checks.py'), str(out)], out, 'regression-checks.log', dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    result = read(out / 'analysis/result.json')
    if set(result['checks']) != set(case['expected_checks']) or not all(v is True for v in result['checks'].values()):
        raise ValueError('Original twelve checks failed')
    attempt['analysis_sha256'] = {p.relative_to(out).as_posix(): sha(p) for p in sorted((out / 'analysis').rglob('*')) if p.is_file() and p.suffix != '.pyc' and '__pycache__' not in p.parts}
    execute([env['python'], str(ROOT/'adapters/reverse-dcf/writer_builder.py'), 'prepare', str(out)], out, 'writer-packet.log', dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    attempt['writer_packet_sha256'] = sha(out/'author-packet.json')
    attempt['writer_scaffold_sha256'] = sha(out/'writer-scaffold.json')
    harness = (ROOT / 'adapters/reverse-dcf/coordinator.js').read_text(encoding='utf-8')
    executable = harness.replace('@OUT@', json.dumps(str(out))).replace('@ROOT@', json.dumps(str(ROOT))).replace("'@PY@'", json.dumps(env['python'])).replace("'@ENV@'", json.dumps(recorded['path']))
    if any(token in executable for token in ('@OUT@', '@ROOT@', '@PY@', '@ENV@')):
        raise ValueError('Coordinator harness contains unresolved template bindings')
    (out / 'coordinator-exec.js').write_text(executable, encoding='utf-8')
    attempt['coordinator_exec_sha256'] = sha(out / 'coordinator-exec.js')
    prompts = {}
    for role in ('author', 'reviewer'):
        prompt = (case_dir / (role + '-prompt.txt')).read_text(encoding='utf-8').replace('$ROOT', str(ROOT)).replace('$OUT', str(out))
        prompt += (f' Pinned report-writer reference is recorded in attempt.json; bounded persona/policy excerpts in author-packet.json. Do not read full libraries.' if role=='author' else f' Relevant persona: {roles[role]}; Registry reference {json.dumps(refs[role], sort_keys=True)}. Read only relevant persona if needed.')+(f' Narrow mandate: {diagnostic["mandate"]} Full-valuation checks not claimed passed.' if role=='reviewer' else ' Scope is in the packet; full valuation checks not claimed passed.')
        prompts[role + '_prompt'] = prompt
    prompts['coordinator_prompt'] = (f'Run the exact saved JavaScript in {out}/coordinator-exec.js via functions.exec immediately. That script loads the scoped dispatch and emits actual native author/build/reviewer receipts; do not read attempt.json or whole libraries yourself, reimplement, or add supervisor layers. Native spawn must be available; if absent preserve capability failure. Parent captures your result, closes you and invokes finish. Fresh fork_context=false actors, inherit model/high, current report only, no prior report or results. 585s work/600s overall; no exclusions or criteria changes. Return ready-for-parent-finish or preserve incomplete. Role {json.dumps(refs["coordinator"],sort_keys=True)}; installed release {ROOT}.')
    if len(prompts['author_prompt'])+len((out/'author-packet.json').read_text()) > 8000:
        raise ValueError('Combined author task and handoff exceeds 8000 characters')
    write(out / 'dispatch.json', prompts)
    attempt['dispatch_sha256'] = sha(out / 'dispatch.json')
    write(out / 'attempt.json', attempt)
    return prompts


def receipt(out, name, data):
    if not re.fullmatch(r'(coordinator|author|reviewer)-(spawn|result|close)', name):
        raise ValueError('Receipt name must be ROLE-spawn/result/close')
    if not isinstance(data, dict):
        raise ValueError('Actual native receipt envelope required')
    write(out / (name + '.json'), data)
    return {'saved': str(out / (name + '.json'))}


def captured(data):
    from datetime import datetime
    value = data.get('captured_at')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Receipt capture timestamp needs timezone')
    return dt.timestamp()


def envelope(out, role, kind, attempt):
    data = read(out / f'{role}-{kind}.json')
    expected = {'spawn': 'spawn_agent', 'result': 'wait_agent', 'close': 'close_agent'}[kind]
    if data.get('tool') not in ('multi_agent_v1.' + expected, 'multi_agent_v1__' + expected):
        raise ValueError('Unsupported actual native receipt tool')
    response = data['response']
    if not isinstance(response, dict) or any(response.get(k) for k in ('error', 'errors', 'isError', 'timed_out')):
        raise ValueError('Failed or timed-out native receipt')
    if not attempt['requested_epoch'] <= captured(data) <= time.time():
        raise ValueError('Stale or future receipt')
    return data


def actor(out, role, attempt):
    spawn = envelope(out, role, 'spawn', attempt)
    request = spawn['request']
    if request.get('fork_context') is not False or request.get('model', 'inherit') != 'inherit' or request.get('message') != read(out / 'dispatch.json')[role + '_prompt']:
        raise ValueError('Fresh exact task-scoped native spawn required')
    identity = spawn['response'].get('agent_id')
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError('Actual native actor identity missing')
    result = envelope(out, role, 'result', attempt)
    close = envelope(out, role, 'close', attempt)
    status = result['response'].get('status', {}).get(identity)
    previous = close['response'].get('previous_status')
    if identity not in result['request'].get('targets', []) or close['request'].get('target') != identity or not isinstance(status, dict) or not isinstance(previous, dict) or 'completed' not in status or previous != status or not status['completed']:
        raise ValueError('Completed result and actual matching close receipt required')
    if not captured(spawn) <= captured(result) <= captured(close):
        raise ValueError('Native receipt ordering invalid')
    if result.get('attempt_id') != attempt['attempt_id']:
        raise ValueError('Result receipt belongs to a different attempt')
    return identity, spawn, result, close


def build(out):
    attempt, cfg, runtime = current(out)
    if (out / 'author-input.json').exists() or (out / 'native').exists():
        raise ValueError('One fresh build only; preserve failed attempt and obtain new actors')
    _, _, author_result, _ = actor(out, 'author', attempt)
    author_hashes = {name: sha(out / name) for name in ('input.json', 'argument-record.json')}
    if author_result.get('artifacts') != author_hashes or author_result.get('fresh_generation') is not True or author_result.get('no_previous_report_read') is not True:
        raise ValueError('Supplied author result must bind exact fresh output hashes and read-scope attestation')
    d = read(out / 'input.json')
    write(out / 'author-input.json', d)
    for key, value in cfg[0].get('defaults', {}).items():
        d.setdefault(key, value)
    d.pop('comparison_href', None)
    for section in d['report_sections']:
        blocks = []
        for original in section['blocks']:
            block = dict(original)
            if block['kind'] == 'source-note':
                block['kind'] = 'paragraph'
            text = block.get('html', '')
            if block['kind'] == 'paragraph' and '<' not in text and len(text) > 180:
                chunks, chunk = [], ''
                for piece in re.split(r'(?<=[.!?。])\s+', text):
                    if chunk and len(chunk) + len(piece) > 180:
                        chunks.append(chunk)
                        chunk = ''
                    chunk = (chunk + ' ' + piece).strip()
                if chunk:
                    chunks.append(chunk)
                if ''.join(''.join(chunks).split()) != ''.join(text.split()):
                    raise ValueError('Paragraph normalization changed semantics')
                blocks.extend(dict(block, html=x) for x in chunks)
            else:
                blocks.append(block)
        section['blocks'] = blocks
    (out / 'input.json').write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    env = dict(os.environ, REPORT_OUTFIT_NODE=runtime['node'], REPORT_OUTFIT_PLAYWRIGHT=runtime['playwright'], PYTHONDONTWRITEBYTECODE='1')
    scripts = ROOT / 'adapters/report-publication/vendor/report-design/scripts'
    commands = [[runtime['python'], str(ROOT / 'adapters/reverse-dcf/prepare-publication.py'), str(out)],
        [runtime['python'], str(scripts / 'build.py'), '--mode', 'report', '--template', 'valuation', '--input', str(out / 'input.json'), '--design', 'executive', '--out', str(out / 'native'), '--html-only'],
        [runtime['node'], str(scripts / 'render.mjs'), str(out / 'native')]]
    for i, cmd in enumerate(commands):
        execute(cmd, out, f'publish-{i}.log', env)
    shutil.copytree(out / 'analysis', out / 'native/analysis')
    (out / 'index.html').write_text('<!doctype html><meta charset="utf-8"><a href="native/report.html">HTML</a> · <a href="native/report.pdf">PDF</a>', encoding='utf-8')
    execute([runtime['python'], str(scripts / 'verify_report.py'), '--root', str(out / 'native'), '--input', str(out / 'input.json'), '--render'], out, 'verify.log', env)
    current(out)
    hashes = {p.relative_to(out).as_posix(): sha(p) for p in sorted(out.rglob('*')) if p.is_file() and (p.is_relative_to(out / 'native') or p.name in {'input.json', 'author-input.json', 'argument-record.json', 'source-content.html', 'input-manifest.json'}) and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    hashes.update(attempt['analysis_sha256'])
    write(out / 'reviewed-target.json', {'attempt_id': attempt['attempt_id'], 'artifacts': hashes,
        'component_sha256': attempt['component_sha256'], 'criterion_sha256': attempt['criterion']['sha256'],
        'author_result_sha256': sha(out / 'author-result.json'), 'built_epoch': time.time()})
    return {'pdf': str(out / 'native/report.pdf'), 'html': str(out / 'native/report.html'), 'technical_pass': read(out / 'native/verification.json')['passed'], 'review_target': str(out / 'reviewed-target.json')}


def finish(out):
    if (out / 'completion.json').exists():
        raise ValueError('Attempt already completed')
    attempt, cfg, _ = current(out)
    target = read(out / 'reviewed-target.json')
    if target['component_sha256'] != attempt['component_sha256'] or target['criterion_sha256'] != attempt['criterion']['sha256'] or target['author_result_sha256'] != sha(out / 'author-result.json'):
        raise ValueError('Review target component or author binding changed')
    for name, expected in target['artifacts'].items():
        if sha(within(out, name)) != expected:
            raise ValueError('Exact reviewed artifact changed: ' + name)
    actors = {role: actor(out, role, attempt) for role in ROLES}
    if len({v[0] for v in actors.values()}) != 3:
        raise ValueError('Three actual fresh independent actors required')
    if captured(actors['author'][3]) > target['built_epoch'] or captured(actors['reviewer'][1]) < target['built_epoch']:
        raise ValueError('Reviewer must be spawned fresh after author closure and final build')
    review = read(out / 'review.json')
    reviewer_result = actors['reviewer'][2]
    if reviewer_result.get('artifacts') != {'review.json': sha(out / 'review.json')}:
        raise ValueError('Supplied reviewer result does not bind actual review output')
    if review.get('reviewer_agent_id') != actors['reviewer'][0] or review.get('attempt_id') != attempt['attempt_id']:
        raise ValueError('Independent reviewer output identity mismatch')
    target_seal = sha(out / 'reviewed-target.json')
    if review.get('reviewed_target_sha256') != target_seal or review.get('component_manifest_sha256') != canonical_digest(target['component_sha256']) or review.get('criterion_sha256') != target['criterion_sha256']:
        raise ValueError('Review must bind exact target seal, canonical component manifest and independent criterion')
    for field, name in {'input_sha256': 'input.json', 'author_input_sha256': 'author-input.json', 'argument_sha256': 'argument-record.json', 'result_sha256': 'analysis/result.json', 'evidence_sha256': 'analysis/comparison-evidence.json', 'stress_sha256': 'analysis/stress.json', 'components_sha256': 'analysis/value-components.json', 'pdf_sha256': 'native/report.pdf'}.items():
        if review.get(field) != sha(out / name):
            raise ValueError('Review target hash mismatch: ' + field)
    scores = review.get('axis_scores', {})
    if set(scores) != AXES or any(type(v) is not int or not 3 <= v <= 4 for v in scores.values()) or sum(scores.values()) < 17 or review.get('total') != sum(scores.values()):
        raise ValueError('Protected min3/sum17 five-axis gate unmet')
    if review.get('status') != 'pass' or not isinstance(review.get('findings'), list) or any(f.get('severity') in {'material', 'critical', 'major', 'high'} for f in review['findings']):
        raise ValueError('Independent review not passed')
    for finding in review['findings']:
        if not finding.get('id') or finding.get('severity') not in {'info', 'minor', 'low', 'material', 'critical', 'major', 'high'} or not finding.get('locations') or finding.get('reviewed_target_sha256') != target_seal:
            raise ValueError('Findings must bind IDs, locations and the exact reviewed target seal')
        affected = finding.get('artifact_hashes', {})
        if not isinstance(affected, dict) or any(target['artifacts'].get(k) != h for k, h in affected.items()):
            raise ValueError('Affected finding artifact hashes must match the sealed target')
    numeric = review.get('numerical_checks', {})
    required = set(cfg[0]['expected_checks']) | {'stress_roots', 'three_way_pv_bridge'}
    if not required <= set(numeric) or any(not isinstance(numeric[k], dict) or numeric[k].get('passed') is not True or not numeric[k].get('evidence') for k in required) or not review.get('scope') or not review.get('limits'):
        raise ValueError('Independent numerical checks/scope/limits unverified')
    verify = read(out / 'native/verification.json')
    calc = read(out / 'analysis/result.json')
    if verify.get('passed') is not True or not all(v is True for v in verify['checks'].values()) or set(calc['checks']) != set(cfg[0]['expected_checks']) or not all(v is True for v in calc['checks'].values()):
        raise ValueError('Native verification or original twelve checks failed')
    pages = read(out / 'native/renders/manifest.json')['pages']
    if review.get('pages_read') != list(range(1, verify['counts']['pages'] + 1)) or len(pages) != len(review['pages_read']):
        raise ValueError('Every final PDF page must be extracted and reviewed')
    inspections = review.get('page_inspections', [])
    if len(inspections) != len(pages) or any(i.get('page') != p['page'] or i.get('sha256') != p['sha256'] or not i.get('extracted_text_evidence') or not isinstance(i.get('automated_content_evidence'), dict) or i['automated_content_evidence'].get('verification_sha256') != sha(out / 'native/verification.json') or not i['automated_content_evidence'].get('checks') or any(verify['checks'].get(k) is not True for k in i['automated_content_evidence']['checks']) for i, p in zip(inspections, pages)):
        raise ValueError('Every final page needs extracted text and hash-bound automated native-check evidence')
    elapsed = time.time() - attempt['requested_epoch']
    if captured(actors['reviewer'][2]) - attempt['requested_epoch'] > 585 or elapsed > 600:
        raise ValueError('585-second work or 600-second delivery target failed; preserve attempt')
    completion = {'quality_pass': True, 'total_score': sum(scores.values()), 'elapsed_seconds_to_delivery': elapsed,
        'within_600_seconds': True, 'attempt_id': attempt['attempt_id'], 'release': attempt['release'],
        'registry_references': attempt['registry_references'], 'component_sha256': attempt['component_sha256'],
        'artifacts': target['artifacts'], 'actors': {k: v[0] for k, v in actors.items()},
        'receipt_sha256': {f'{r}-{k}.json': sha(out / f'{r}-{k}.json') for r in ROLES for k in ('spawn', 'result', 'close')},
        'review_sha256': sha(out / 'review.json'), 'reviewed_target_sha256': target_seal,
        'component_manifest_sha256': canonical_digest(target['component_sha256']), 'html': str(out / 'native/report.html'), 'pdf': str(out / 'native/report.pdf'),
        'scope': cfg[2]['mandate'], 'full_valuation_checks_claimed_passed': False,
        'receipt_validation_limit': 'Supplied host receipt envelopes and read-scope attestations checked; no cryptographic host authentication or global actor history.'}
    write(out / 'completion.json', completion)
    return completion


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('init', 'build', 'finish', 'receipt'):
        command = sub.add_parser(action)
        command.add_argument('out', type=Path)
        command.add_argument('--release', type=Path, default=argparse.SUPPRESS)
        if action == 'init':
            command.add_argument('request_epoch', type=float)
            command.add_argument('--case', required=True)
        if action == 'receipt':
            command.add_argument('name')
            command.add_argument('json')
    args = parser.parse_args(argv)
    root = args.release.expanduser().resolve()
    if root != ROOT:
        target = root / 'pr/report_path.py'
        if not target.is_file():
            parser.error('Selected release lacks report_path.py')
        os.execv(sys.executable, [sys.executable, str(target)] + (list(argv) if argv is not None else sys.argv[1:]))
    out = args.out.expanduser().resolve()
    try:
        if args.action == 'init':
            result = init(out, args.request_epoch, args.case)
        elif args.action == 'receipt':
            result = receipt(out, args.name, json.loads(args.json))
        else:
            result = {'build': build, 'finish': finish}[args.action](out)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, subprocess.CalledProcessError) as exc:
        failure = {'action': args.action, 'error': type(exc).__name__, 'message': str(exc), 'elapsed_epoch': time.time()}
        if args.action in ('init', 'build', 'finish') and out.is_dir():
            write(out / ('failure-' + str(time.time_ns()) + '.json'), failure)
        print(json.dumps(failure), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
