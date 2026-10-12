"""Freeze an explicitly selected, reconciled Flume Sink run for HDFS."""
import argparse
import json
import re
from pathlib import Path, PurePosixPath
from common import sha256, utcnow
from movie_quality import inspect_movies
from hdfs_common import ROOT, new_json
from validate_pipeline import REQUIRED

LOG4J2_SHA256 = 'f7f47e1246016eaa5bfaa0a65a8c66be712baac931e05ce30adfd694625b277b'


def input_path_from_evidence(recorded):
    """Relocate a recorded path; never silently choose a different input."""
    normalized = str(recorded).replace('\\', '/')
    offset = normalized.find('data/generated/')
    if offset < 0:
        raise ValueError('Recorded Flume input is not under data/generated')
    path = (ROOT / normalized[offset:]).resolve()
    if not path.is_relative_to((ROOT / 'data/generated').resolve()) or not path.is_file():
        raise ValueError('Recorded Flume input is missing or outside data/generated')
    return path


def source_manifest(run_id, evidence, flume_run_id):
    if not re.fullmatch(r'hdfs-[a-f0-9]{12}', run_id) or not re.fullmatch(r'run-[a-f0-9]{12}', flume_run_id):
        raise ValueError('Invalid HDFS or Flume run ID')
    old = ROOT / 'evidence' / flume_run_id
    status = json.loads((old / 'status.json').read_text(encoding='utf-8'))
    rec = json.loads((old / 'reconciliation.json').read_text(encoding='utf-8'))
    if status.get('run_id') != flume_run_id or status.get('status') != 'PASS' or rec.get('status') != 'PASS':
        raise ValueError('Selected Flume run requires PASS status and reconciliation')
    if rec.get('mode') != 'pipeline_reconciliation':
        raise ValueError('Input-only validation is not Flume reconciliation')
    if sha256(ROOT / 'config/flume.conf') != status.get('config_sha256'):
        raise ValueError('Flume configuration hash differs from selected run')
    if sha256(ROOT / 'config/log4j2.xml') != LOG4J2_SHA256:
        raise ValueError('Required config/log4j2.xml SHA256 mismatch')
    config_hashes = status.get('source_config_hashes', {})
    for name, expected_hash in config_hashes.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha256(path) != expected_hash:
            raise ValueError('Flume source/config changed: ' + name)
    expected_events = rec['input']['total']
    if type(expected_events) is not int or expected_events <= 0:
        raise ValueError('Reconciliation requires a positive event count')
    for side in ['input', 'output']:
        stats = rec[side]
        if stats['total'] != expected_events or stats['unique'] != expected_events:
            raise ValueError('Input/output total or unique count mismatch')
        if any(stats[key] != 0 for key in ['invalid', 'duplicates', 'conflicting_ids']):
            raise ValueError('Run has invalid, duplicate, or conflicting events')
    if any(rec[key] != 0 for key in ['missing_event_ids', 'unexpected_event_ids', 'changed_payloads',
                                    'session_errors', 'user_overlap_errors']) or rec.get('manifest_errors'):
        raise ValueError('Reconciliation has missing, unexpected, changed, or invalid events/sessions')
    generated = input_path_from_evidence(status['input'])
    manifest = json.loads(generated.with_suffix(generated.suffix + '.manifest.json').read_text(encoding='utf-8'))
    input_hash = sha256(generated)
    if input_hash != status['input_sha256'] or input_hash != rec['input_sha256'] or input_hash != manifest['sha256']:
        raise ValueError('Flume input provenance changed')
    if manifest['events'] != expected_events:
        raise ValueError('Input manifest and reconciliation count mismatch')
    movies = ROOT / 'data/processed/movies.csv'
    _, qa = inspect_movies(movies)
    if qa['status'] != 'PASS' or qa['sha256'] != rec['movies_sha256'] or qa['sha256'] != manifest['movies_sha256']:
        raise ValueError('Movie snapshot changed or is invalid')
    sink = ROOT / 'data/runs' / flume_run_id / 'output'
    expected = {}
    for proof in rec['output_files']:
        recorded = str(proof['path']).replace('\\', '/')
        name = PurePosixPath(recorded).name
        suffix = 'data/runs/' + flume_run_id + '/output/' + name
        if not recorded.endswith(suffix) or not name.endswith('.jsonl') or name in expected:
            raise ValueError('Invalid or duplicate Sink path in reconciliation')
        expected[name] = proof
    actual = {p.name: p for p in sink.iterdir() if p.is_file()}
    if not expected or set(actual) != set(expected):
        raise ValueError('Sink file list differs from reconciliation')
    snapshot = 'mls-' + qa['sha256'][:12] + '-' + run_id
    movies_dir = '/movie-log/raw/movies/' + snapshot
    logs_dir = '/movie-log/raw/user_logs/' + flume_run_id + '/' + run_id
    files = [{'kind': 'movies', 'local_path': movies.relative_to(ROOT).as_posix(), 'bytes': qa['bytes'],
              'sha256': qa['sha256'], 'expected_records': qa['rows'], 'hdfs_path': movies_dir + '/movies.csv'}]
    event_ids = set()
    for name, path in sorted(actual.items()):
        proof = expected[name]
        if path.stat().st_size != proof['bytes'] or sha256(path) != proof['sha256']:
            raise ValueError('Sink bytes/hash changed: ' + name)
        records = 0
        with path.open('rb') as stream:
            for line in stream:
                if not line.endswith(b'\n'):
                    raise ValueError('Truncated Sink part: ' + name)
                event = json.loads(line.decode('utf-8', errors='strict'))
                if not isinstance(event, dict) or set(event) != REQUIRED or event['runId'] != manifest['runId']:
                    raise ValueError('Invalid Sink structure or event runId: ' + name)
                identity = event['eventId']
                if not isinstance(identity, str) or not identity.strip() or identity in event_ids:
                    raise ValueError('Invalid or duplicate Sink eventId: ' + name)
                event_ids.add(identity)
                records += 1
        if 'expected_records' in proof and records != proof['expected_records']:
            raise ValueError('Sink part count differs from reconciliation: ' + name)
        files.append({'kind': 'logs', 'local_path': path.relative_to(ROOT).as_posix(), 'bytes': proof['bytes'],
                      'sha256': proof['sha256'], 'expected_records': records, 'empty': proof['bytes'] == 0,
                      'hdfs_path': logs_dir + '/' + name})
    if sum(item['expected_records'] for item in files if item['kind'] == 'logs') != expected_events:
        raise ValueError('Full Sink parsing count differs from reconciliation')
    result = {'status': 'PASS', 'created_at_utc': utcnow(), 'hdfs_run_id': run_id, 'flume_run_id': flume_run_id,
              'selected_run_id': flume_run_id, 'flume_input_sha256': input_hash,
              'flume_status_sha256': sha256(old / 'status.json'),
              'flume_reconciliation_sha256': sha256(old / 'reconciliation.json'),
              'provenance': {'flume_config_sha256': status['config_sha256'], 'log4j2_sha256': LOG4J2_SHA256,
                             'source_config_hashes': config_hashes,
                             'evidence_format': 'source_config_hashes' if config_hashes else 'legacy_config_sha256'},
              'movies_qa': qa, 'expected_movies': qa['rows'], 'expected_logs': expected_events,
              'expected_log_bytes': sum(proof['bytes'] for proof in expected.values()),
              'event_manifest': manifest, 'flume_stats': rec['output'], 'authority': 'hdfs://namenode:9000',
              'movies_uri': 'hdfs://namenode:9000' + movies_dir + '/movies.csv',
              'logs_uri': 'hdfs://namenode:9000' + logs_dir, 'raw_namespaces': [movies_dir, logs_dir],
              'directories': ['/movie-log/raw/movies', '/movie-log/raw/user_logs', '/movie-log/processed',
                              '/movie-log/results', movies_dir, logs_dir], 'files': files,
              'note': 'Input is checked only for lineage; uploaded logs are exclusively selected Flume Sink parts.'}
    new_json(Path(evidence) / 'source_manifest.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hdfs-run-id', required=True)
    p.add_argument('--flume-run-id', required=True)
    p.add_argument('--evidence-dir', required=True)
    args = p.parse_args()
    result = source_manifest(args.hdfs_run_id, args.evidence_dir, args.flume_run_id)
    print(json.dumps({key: result[key] for key in ['status', 'hdfs_run_id', 'flume_run_id', 'expected_movies',
                                                  'expected_logs', 'expected_log_bytes', 'movies_uri', 'logs_uri']}, indent=2))
