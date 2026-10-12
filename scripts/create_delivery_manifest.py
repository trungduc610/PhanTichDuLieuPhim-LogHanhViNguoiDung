"""Create or verify a scoped immutable handoff manifest (no data regeneration)."""
import argparse
import json
from pathlib import Path
from common import sha256, utcnow, write_json

ROOT=Path(__file__).resolve().parents[1]


def verify(manifest_path):
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    issues=[]
    for rel, expected in manifest['files'].items():
        p=ROOT/rel
        if not p.is_file():
            issues.append({'path':rel,'error':'missing'})
        elif p.stat().st_size!=expected['bytes'] or sha256(p)!=expected['sha256']:
            issues.append({'path':rel,'error':'bytes/hash mismatch'})
    return {'status':'PASS' if not issues else 'FAIL','files_checked':len(manifest['files']),'issues':issues,'checked_at_utc':utcnow()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output')
    p.add_argument('--verify')
    p.add_argument('--audit-dir')
    p.add_argument('--run',action='append',default=[])
    p.add_argument('--extra-evidence',action='append',default=[])
    a=p.parse_args()
    if a.verify:
        result=verify(a.verify)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result['status']=='PASS' else 1
    if not a.output or Path(a.output).exists():
        raise ValueError('--output must be a NEW file')
    scopes=['scripts','src','tests','config','docs','data/raw','data/processed','data/generated']
    scopes += [f'evidence/{x}' for x in a.run]+[f'data/runs/{x}/output' for x in a.run]+[f'logs/{x}' for x in a.run]+a.extra_evidence
    if a.audit_dir:
        scopes.append(a.audit_dir)
    files=set(ROOT/name for name in ['README.md','Dockerfile','compose.yaml','requirements.txt','.gitignore','.gitattributes','.dockerignore'])
    output=Path(a.output).resolve()
    for scope in scopes:
        folder=(ROOT/scope).resolve()
        if not folder.is_relative_to(ROOT):
            raise ValueError('Scope outside project')
        files.update(p for p in folder.rglob('*') if p.is_file())
    entries={}
    for file in sorted(files):
        rel=file.relative_to(ROOT).as_posix()
        if file.resolve()==output or any(x in file.parts for x in ['__pycache__','temporary','fixtures']) or file.suffix in ['.pyc','.part'] or file.name.endswith('.pem'):
            continue
        if 'execution' in file.parts:
            command_path = next((parent/'command.json' for parent in file.parents if (parent/'command.json').is_file()), None)
            if command_path and 'finished_at_utc' not in json.loads(command_path.read_text(encoding='utf-8')):
                continue  # The currently recording manifest step is not yet immutable.
        entries[rel]={'bytes':file.stat().st_size,'sha256':sha256(file)}
    write_json(output,{'created_at_utc':utcnow(),'root':str(ROOT),'scope':scopes,'exclusions':['.git','historical evidence/audit unless explicitly selected','channel checkpoints/data','spool copy/tracker','temporary/fixtures','pycache/part','public temporary CA bundle','active execution step','manifest itself and later verification reports'],'files':entries})
    result=verify(output)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
