"""Restore missing local Flume Sink files from an existing verified HDFS snapshot.

Never writes HDFS, overwrites local files, or changes historical evidence.
"""
import argparse
import json
import subprocess
from pathlib import Path

from common import sha256, utcnow
from hdfs_common import ROOT, new_json, snapshot_namespaces


def restore(source_manifest, container, report):
    report = Path(report)
    if report.exists():
        raise FileExistsError(report)
    source = json.loads(Path(source_manifest).read_text(encoding='utf-8'))
    snapshot_namespaces(source)
    result = {'status': 'FAIL', 'started_at_utc': utcnow(),
              'source_manifest_sha256': sha256(source_manifest),
              'hdfs_run_id': source['hdfs_run_id'], 'flume_run_id': source['flume_run_id'],
              'hdfs_mutated': False, 'files': []}
    try:
        for item in source['files']:
            relative = item['local_path'].replace('\\', '/')
            allowed = relative == 'data/processed/movies.csv' or relative.startswith(
                'data/runs/' + source['flume_run_id'] + '/output/')
            target = (ROOT / relative).resolve()
            if not allowed or not target.is_relative_to(ROOT / 'data'):
                raise ValueError('Unsafe restoration target: ' + relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            record = {'path': relative, 'hdfs_path': item['hdfs_path'],
                      'bytes': item['bytes'], 'sha256': item['sha256']}
            if target.exists():
                if target.stat().st_size != item['bytes'] or sha256(target) != item['sha256']:
                    raise ValueError('Existing local file differs; refusing overwrite: ' + relative)
                record['action'] = 'SKIP_VERIFIED_LOCAL'
            else:
                partial = target.with_name(target.name + '.restore.part')
                argv = ['docker', 'exec', container, 'hdfs', 'dfs', '-cat', item['hdfs_path']]
                with partial.open('xb') as output:
                    process = subprocess.run(argv, stdout=output, stderr=subprocess.PIPE, timeout=300)
                record.update(argv=argv, exit_code=process.returncode,
                              stderr=process.stderr.decode('utf-8', errors='replace'))
                if process.returncode:
                    raise RuntimeError('HDFS read failed; partial file preserved: ' + str(partial))
                if partial.stat().st_size != item['bytes'] or sha256(partial) != item['sha256']:
                    raise ValueError('Remote snapshot differs; partial file preserved: ' + str(partial))
                # Windows rename refuses an existing destination; no replacement.
                partial.rename(target)
                record['action'] = 'RESTORED_FROM_HDFS'
            result['files'].append(record)
            print(record['action'] + ' ' + relative, flush=True)
        result['status'] = 'PASS'
    except Exception as exc:
        result['error'] = str(exc)
    result['finished_at_utc'] = utcnow()
    new_json(report, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest', required=True)
    parser.add_argument('--container', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    result = restore(args.source_manifest, args.container, args.report)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
