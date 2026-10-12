"""Freeze a scoped HDFS handoff; local byte verification is separate from remote.

Only creates NEW manifests/receipts. Never changes the Week 1 manifest.
"""
import argparse
import json
from pathlib import Path
from common import sha256, utcnow
from hdfs_common import ROOT, new_json


def verify(path):
    manifest=json.loads(Path(path).read_text(encoding='utf-8'))
    issues=[]
    for rel,expected in manifest['files'].items():
        file=(ROOT/rel).resolve()
        if not file.is_relative_to(ROOT) or not file.is_file():
            issues.append({'path':rel,'error':'missing or outside project'})
        elif file.stat().st_size!=expected['bytes'] or sha256(file)!=expected['sha256']:
            issues.append({'path':rel,'error':'bytes/SHA256 mismatch'})
    return {'status':'PASS' if not issues else 'FAIL','checked_at_utc':utcnow(),
            'manifest_sha256':sha256(path),'files_checked':len(manifest['files']),
            'total_bytes':sum(f['bytes'] for f in manifest['files'].values()),'issues':issues,
            'remote_note':'This verifies local files only. Re-run hdfs_hash_verify.py for current HDFS bytes; the immutable recorded remote receipt is included in the manifest.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context')
    parser.add_argument('--output')
    parser.add_argument('--verify')
    parser.add_argument('--receipt')
    args=parser.parse_args()
    if args.verify:
        result=verify(args.verify)
        if args.receipt:new_json(args.receipt,result)
        print(json.dumps(result,ensure_ascii=True,indent=2))
        return 0 if result['status']=='PASS' else 1
    if not args.context or not args.output:parser.error('--context and --output required')
    output=Path(args.output).resolve()
    if output.exists() or not output.is_relative_to(ROOT):raise ValueError('Output must be NEW within project')
    context=json.loads(Path(args.context).read_text(encoding='utf-8'))
    evidence=ROOT/context['evidence']
    remote=json.loads((evidence/'final-hdfs-hashes.json').read_text(encoding='utf-8'))
    source=json.loads((evidence/'source_manifest.json').read_text(encoding='utf-8'))
    acceptance=json.loads((evidence/'acceptance_status.json').read_text(encoding='utf-8'))
    if remote['status']!='PASS' or remote['source_manifest_sha256']!=sha256(evidence/'source_manifest.json') or any(v!='ĐẠT' for v in acceptance['stages'].values()):
        raise ValueError('Requires verified remote bytes and five completed stages')
    scopes=['scripts','src','tests','config','docs','data/raw','data/processed','data/generated',
            'data/runs/run-aa6b9eb58dca/output','evidence/run-aa6b9eb58dca',
            'evidence/recheck-20261011-221710',context['evidence'],context['audit']]
    selected={ROOT/n for n in ['README.md','Dockerfile','compose.yaml','compose.hdfs.yaml',
                  'requirements.txt','.gitignore','.gitattributes','.dockerignore',
                  'audit/2026-10-11-221710-week1-recheck/bao-cao-nghiem-thu-tuan-1-recheck.md']}
    for scope in scopes:selected.update(p for p in (ROOT/scope).rglob('*') if p.is_file())
    entries={}
    omitted=[]
    for file in sorted(selected):
        rel=file.relative_to(ROOT).as_posix()
        if file==output or any(part in file.parts for part in ['.git','__pycache__','temporary','fixtures']) or file.suffix in ['.pyc','.part'] or file.name.endswith('.pem'):
            omitted.append(rel);continue
        if 'execution' in file.parts:
            owner=next((parent/'command.json' for parent in file.parents if (parent/'command.json').is_file()),None)
            if owner and 'finished_at_utc' not in json.loads(owner.read_text(encoding='utf-8')):
                omitted.append(rel);continue
        entries[rel]={'bytes':file.stat().st_size,'sha256':sha256(file)}
    new_json(output,{'created_at_utc':utcnow(),'root':str(ROOT),'run_id':context['run_id'],
                    'scope':scopes,'selected_root_files':'see exact files keys',
                    'exclusions':['.git','other run outputs/channel/spool','unselected historical audits/evidence',
                                  'Docker image layers and live HDFS named-volume metadata/blocks (not a portable volume export)',
                                  'temporary/fixtures/pycache/part/public temporary CA bundles',
                                  'active manifest execution step','manifest itself and later verification receipts/commands'],
                    'omitted_selected_files':omitted,'files':entries,
                    'remote_hdfs':{'authority':source['authority'],'run_id':source['hdfs_run_id'],
                                   'verified_at_utc':remote['finished_at_utc'],'method':remote['method'],
                                   'receipt':context['evidence']+'/final-hdfs-hashes.json',
                                   'receipt_sha256':sha256(evidence/'final-hdfs-hashes.json'),
                                   'files':[{**r,'expected_records':s['expected_records']} for r,s in zip(remote['files'],source['files'])]}})
    result=verify(output)
    print(json.dumps(result,ensure_ascii=True,indent=2))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
