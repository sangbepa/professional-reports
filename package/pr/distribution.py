"""Stage a portable thin plugin; Codex CLI owns its installed cache."""
import shutil
from pathlib import Path
from .package import verify
from .util import ContractError,identifier,members,write_json


def marketplace(release,destination,name='professional-reports-local'):
    release=Path(release).resolve();destination=Path(destination).resolve()
    identifier(name);manifest=verify(release)
    if destination.exists():raise ContractError('Marketplace staging destination must be new')
    target=destination/'plugins/professional-reports';target.mkdir(parents=True)
    shutil.copyfile(release/'plugin.json',target/'plugin.json')
    shutil.copytree(release/'skills/professional-reports',target/'skills/professional-reports')
    write_json(destination/'.agents/plugins/marketplace.json',{
        'name':name,'interface':{'displayName':'Professional Reports'},
        'plugins':[{'name':'professional-reports','source':{'source':'local','path':'./plugins/professional-reports'}}]})
    return dict(path=str(destination),name=name,plugin_id='professional-reports@'+name,
                bootstrap_members=members(target),release_id=manifest['release_id'],
                installed=False,commands=[['codex','plugin','marketplace','add',str(destination),'--json'],
                                           ['codex','plugin','add','professional-reports@'+name,'--json']])
