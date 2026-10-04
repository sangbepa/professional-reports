"""Local development checks for skills only; never reads protected evaluations."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

sys.dont_write_bytecode = True
SCOPE = Path(__file__).resolve().parent
ROOT = SCOPE.parents[1]
REPOSITORY = ROOT.parent
sys.path.insert(0, str(ROOT))
from pr.registry import Registry
from pr.planning import plan_check
from pr.util import ContractError, hash_data


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    registry = Registry(ROOT)
    components = []
    caps = {}
    links = 0
    clauses = 0
    for manifest in sorted(SCOPE.glob('*/component.json')):
        folder = manifest.parent
        data = read(manifest)
        identity = data['id']
        assert identity == folder.name and re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', identity)
        assert set(data) == {'id','kind','version','status','description','capabilities','requires','entrypoint'}
        assert data['kind'] == 'skill' and data['version'] == '0.1.0-dev.1' and data['status'] == 'provisional'
        assert data['description'] and 'pending' not in data['description'].lower()
        assert data['entrypoint'] == 'SKILL.md'
        assert isinstance(data['requires'], list) and all(isinstance(x, str) and x in registry.entries for x in data['requires'])
        assert len(data['requires']) == len(set(data['requires']))
        assert data['capabilities'] and len(set(data['capabilities'])) == len(data['capabilities'])
        ref = registry.reference(identity)
        assert set(ref) == {'id','version','sha256'}
        registry.resolve(ref, 'skill')
        wrong = dict(ref, sha256='0'*64)
        try:
            registry.resolve(wrong, 'skill')
        except ContractError:
            pass
        else:
            raise AssertionError('Changed hash accepted: '+identity)
        contract = read(folder/'contract.json')
        assert contract['id'] == identity
        assert all(contract.get(k) for k in ('inputs','outputs','acceptance','failure','consumes','procedure'))
        assert all(x in contract['outputs'] for x in ('operation_record','failure_records'))
        text = (folder/'SKILL.md').read_text()
        assert len(text.split()) >= 180, identity
        clause_ids = [identity+'-'+suffix for suffix in ('method','acceptance','failure')]
        assert all('### '+key in text for key in clause_ids)
        clauses += len(clause_ids)
        provenance = read(folder/'provenance.json')
        assert provenance['component_id'] == identity and provenance['source_files']
        assert (folder/provenance['license']['file']).is_file() and (folder/'NOTICE').is_file()
        for source in provenance['source_files']:
            assert re.fullmatch(r'[0-9a-f]{64}', source['sha256'])
            if source['origin'] == 'repository':
                assert digest(REPOSITORY/source['repository_relative_path']) == source['sha256'], source['repository_relative_path']
        for cap in data['capabilities']:
            caps.setdefault(cap, []).append(identity)
        components.append({'reference':ref,'requires':data['requires'],'capabilities':data['capabilities'],
                           'basis_clause_ids':clause_ids,'domain_artifact_aliases':contract.get('domain_artifact_aliases',{}),
                           'files':[str(f.relative_to(SCOPE)) for f in sorted(folder.rglob('*')) if f.is_file()]})
    # Dependency closure is acyclic; routing/failure returns are not execution edges.
    pending = {c['reference']['id']:set(c['requires']) for c in components}
    while pending:
        ready = {k for k,v in pending.items() if not (v & set(pending))}
        assert ready, 'Cyclic skill package dependencies'
        pending = {k:v-ready for k,v in pending.items() if k not in ready}
    for file in SCOPE.rglob('*'):
        assert not file.is_symlink()
        if not file.is_file():
            continue
        text = file.read_text()
        # Escape strings in this checker do not themselves match author paths.
        assert not re.search('/'+'Users/|/'+'home/[A-Za-z]|/'+'mnt/data', text), str(file.relative_to(SCOPE))
        if file.suffix == '.json':
            json.loads(text)
        if file.suffix != '.md':
            continue
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            if re.match(r'^[a-z][a-z0-9+.-]*:', link):
                continue
            path, _, anchor = link.partition('#')
            target = (file.parent/unquote(path.strip('<>'))).resolve() if path else file
            assert target.is_file(), (str(file.relative_to(SCOPE)), link)
            assert target.is_relative_to(SCOPE), 'Nonportable local Markdown dependency: '+link
            if anchor:
                headings = re.findall(r'^#+\s+(.+)$', target.read_text(), re.M)
                slugs = {re.sub(r'[^\w\s-]', '', h.lower()).replace(' ','-') for h in headings}
                assert anchor in slugs or f'id="{anchor}"' in target.read_text(), link
            links += 1
    design = read(SCOPE/'report-design/references/approved-design.json')
    for key in ('artifact','historical_review'):
        ref = design[key]
        assert digest(REPOSITORY/ref['repository_relative_path']) == ref['sha256']
    domain = ROOT/'libraries/orchestrations/valuation/plan-rules.json'
    rules = read(domain)['rules']
    needed = {cap for rule in rules for cap in rule.get('require_capabilities', [])}
    assert not needed-set(caps), 'Missing domain caps: '+str(needed-set(caps))
    output_names = {out for rule in rules for out in rule.get('require_artifacts', [])}
    aliases = {a for c in components for a in c['domain_artifact_aliases']}
    assert not output_names-aliases, 'Unmapped domain outputs: '+str(output_names-aliases)
    # In-memory schema/rule compatibility specimen, not a report plan or review result.
    meta = {'selected':[registry.reference('valuation')]}
    nodes=[]
    for c in components:
        identity=c['reference']['id']
        method=read(SCOPE/identity/'contract.json')
        nodes.append(dict(id='check-'+identity,revision=1,goal='Check local component binding',
            question='Does the declared method bind under the current engine schema?',
            basis=[dict(component=c['reference'],clause=identity+'-method',facts=['Visible synthetic compatibility check only'],reason='Test actual component clause and declared capabilities')],
            expert=registry.reference('finance-analyst'),runtime=registry.reference('codex-native'),
            skills=[c['reference']],capabilities=c['capabilities'],execution='agent',reasoning='high',
            inputs=method['inputs'],consumes=method['consumes'],outputs=sorted(set(method['outputs']) | set(c['domain_artifact_aliases'])),
            required_checks=[v['id'] for v in method['acceptance']],depends_on=[],review_required=False,review_role=None))
    for role,identity in [('source','report-source-assess'),('model','audit-xls'),('judgment','valuation-challenge'),('document','report-claim-check')]:
        next(n for n in nodes if n['id']=='check-'+identity)['review_role']=role
    plan=dict(id='visible-skills-compatibility-check',revision=1,previous=None,meta_hash=hash_data(meta),
        reason='Schema and declared-capability compatibility only; no dispatch or review occurred',
        actor='local-development-check',facts={r['when']['fact']:True for r in rules if 'when' in r},nodes=nodes)
    plan_check(registry,meta,plan)
    wrong=copy.deepcopy(plan);wrong['nodes'][0]['capabilities'].append('unimplemented-renderer-test')
    try:
        plan_check(registry,meta,wrong)
    except ContractError:
        pass
    else:
        raise AssertionError('Undeclared node capability accepted')
    result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(SCOPE/'valuation-wacc/tests'),'-v'],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    tests=int(re.search(r'Ran (\d+) tests',result.stderr).group(1))
    inventory={'schema_version':'professional-reports/skill-inventory/1','status':'provisional','scope':'professional-reports/libraries/skills',
       'reference_authority':'pr.registry.Registry.reference; hashes change on any component file edit',
       'components':components,'capability_providers':caps,
       'domain_rule_binding':{'repository_relative_path':str(domain.relative_to(REPOSITORY)),'sha256':digest(domain)},
       'files_written':[str(f.relative_to(SCOPE)) for f in sorted(SCOPE.rglob('*')) if f.is_file() and f.name not in ('library.json','inventory.json','validation.json')]+['inventory.json','validation.json']}
    report={'schema_version':'professional-reports/skill-validation/1','status':'passed-local-checks','component_count':len(components),
       'exact_registry_roundtrips':len(components),'stale_reference_rejections':len(components),'local_markdown_links_checked':links,
       'stable_markdown_clauses_checked':clauses,'dependency_closure':'passed','required_domain_capabilities':sorted(needed),
       'domain_artifact_aliases_covered':sorted(output_names),'all_true_domain_rule_compatibility':'passed-in-memory-only',
       'undeclared_capability_rejection':'passed','wacc_tests_passed':tests,
       'design_reference_hashes':'matched-current-reference-files','provenance_repository_hashes':'matched',
       'independent_review':'not_performed','report_execution':'not_performed','production_verification':False,
       'unresolved':['source-tool and authenticated data access','spreadsheet native recalculation and rendering',
                     'native report-outfit build/render bundle','per-run independent review',
                     'external-reference/third-party license rights beyond supplied local licenses'],
       'registry_components_observed':len(registry.entries)}
    (SCOPE/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    (SCOPE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
