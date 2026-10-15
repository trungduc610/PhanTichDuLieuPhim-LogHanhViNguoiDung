"""Member 1 operations on an explicitly selected, existing HDFS cluster.

Never creates/formats a cluster, overwrites a snapshot or selects Dashboard data.
Reports are exclusive; run again with a new label/context directory.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

from common import sha256, utcnow
from create_delivery_manifest import verify
from hdfs_common import ROOT, Ledger, compose, new_json, snapshot_namespaces
from hdfs_restart_verify import properties
from hdfs_source import source_manifest, input_path_from_evidence
from run_pipeline import pipeline_hashes


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def runner_status(text):
    """The ingestion CLI prints input QA, reconciliation and final status JSON."""
    decoder = json.JSONDecoder()
    values = []
    remaining = text.strip()
    while remaining:
        value, end = decoder.raw_decode(remaining)
        values.append(value)
        remaining = remaining[end:].lstrip()
    result = values[-1]
    if not isinstance(result, dict) or not re.fullmatch(r'run-[a-f0-9]{12}', result.get('run_id', '')):
        raise ValueError('Missing final Flume runner status')
    return result


def relative(path):
    return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()


def official_selection(context, acceptance, selected=None):
    """The acknowledged official release, not a small test, selects ingestion."""
    if acceptance.get('status') != 'PASS' or not acceptance.get('checks') or not all(v is True or v == 'PASS' for v in acceptance['checks'].values()):
        raise ValueError('Requires a PASS official system acceptance')
    run = selected or context['flume_run_id']
    if run != context['flume_run_id'] or run != acceptance['flume_run_id'] or context['run_id'] != acceptance['hdfs_run_id']:
        raise ValueError('Selected run is not the acknowledged official snapshot; demo/fixture refused')
    if acceptance['events'] <= 10000:
        raise ValueError('Small stability/demo proof cannot select the official main dataset')
    status = load(ROOT / 'evidence' / run / 'status.json')
    if status['status'] != 'PASS' or status.get('source_config_hashes') != pipeline_hashes():
        raise ValueError('Official ingestion source/config changed; rerun demo then main')
    return run


def runtime(context, ledger, start=False):
    """Validate mounts/identity BEFORE starting existing containers."""
    project = context['project']
    _, text, _ = ledger.command(['docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=' + project], 'cluster-ids')
    ids = text.split()
    if not ids:
        raise ValueError('Existing cluster missing; refuses creation/format')
    _, text, _ = ledger.command(['docker', 'inspect', *ids], 'cluster-inspect')
    nodes = {}
    for item in json.loads(text):
        labels = item['Config']['Labels']
        role = labels.get('com.docker.compose.service')
        if role not in ('namenode', 'datanode'):
            continue
        if role in nodes:
            raise ValueError('Ambiguous HDFS service')
        env = dict(pair.split('=', 1) for pair in item['Config']['Env'])
        if env.get('HDFS_RUN_ID') != context['run_id']:
            raise ValueError('Container cluster ID mismatch')
        store = '/hdfs/' + ('name' if role == 'namenode' else 'data')
        volumes = [m for m in item['Mounts'] if m['Destination'] == store and m['Type'] == 'volume']
        binds = [m for m in item['Mounts'] if m['Destination'] == '/project' and m['Type'] == 'bind']
        if len(volumes) != 1 or len(binds) != 1 or Path(binds[0]['Source']).resolve() != ROOT.resolve():
            raise ValueError('Unexpected persistent volume or repository mount')
        nodes[role] = {'id': item['Id'], 'name': item['Name'].lstrip('/'), 'volume': volumes[0]['Name'],
                       'image': item['Image'], 'image_reference': item['Config']['Image'],
                       'running': item['State']['Running'], 'store': store}
    if set(nodes) != {'namenode', 'datanode'}:
        raise ValueError('Requires exactly the existing NameNode and DataNode')
    ledger.command(['docker', 'volume', 'inspect', *[n['volume'] for n in nodes.values()]], 'volume-inspect')
    for node in nodes.values():
        if not node['running']:
            if not start:
                raise ValueError('Service stopped; use start with the saved context')
            # Read VERSION from a read-only helper before the service entrypoint can run.
            _, version, _ = ledger.command(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'cat',
                '-v', node['volume'] + ':/existing:ro', node['image'], '/existing/current/VERSION'], 'stopped-volume-version')
            if properties(version).get('clusterID') != context['run_id']:
                raise ValueError('Unformatted/wrong volume; refusing service start')
            ledger.command(['docker', 'start', node['id']], 'start-existing')
    base = compose(project) + ['exec', '-T', 'namenode', 'hdfs']
    for attempt in range(24 if start else 1):
        code, report, _ = ledger.command(base + ['dfsadmin', '-report'], 'datanode-health', False)
        safe_code, safe, _ = ledger.command(base + ['dfsadmin', '-safemode', 'get'], 'safe-mode', False)
        if code == safe_code == 0 and 'Live datanodes (1)' in report and 'Safe mode is OFF' in safe:
            break
        if attempt == (23 if start else 0):
            raise ValueError('One live DataNode and Safe Mode OFF required')
        time.sleep(5)
    ledger.command(base + ['dfs', '-df', '-h', '/'], 'hdfs-capacity')
    return nodes


def prepare(args):
    folder = (ROOT / args.evidence_dir).resolve()
    relative(folder)
    if folder.exists():
        raise FileExistsError('Acceptance folder must be new')
    old = load(args.source_context)
    acceptance = load(args.official_acceptance)
    run = official_selection(old, acceptance, args.flume_run_id)
    folder.mkdir(parents=True)
    context = {'run_id': old['run_id'], 'project': old['project'], 'flume_run_id': run,
               'evidence': relative(folder), 'role': 'official-main', 'created_at_utc': utcnow(),
               'inherited_context': relative(args.source_context), 'official_acceptance': relative(args.official_acceptance)}
    if acceptance.get('historical_source_manifest'):
        context['historical_source_manifest'] = acceptance['historical_source_manifest']
    new_json(folder / 'run-context.json', context)
    # Preserve every pre-existing evidence byte and the already accepted TV2/UI source.
    paths = list((ROOT / 'evidence').rglob('*')) + list((ROOT / 'dashboard').rglob('*'))
    paths += [ROOT / name for name in ['scripts/tv2_pipeline.py', 'scripts/run_tv2.py', 'src/schemas.py', 'Dockerfile.tv2', 'compose.tv2.yaml']]
    baseline = {}
    for path in paths:
        if not path.is_file() or path.is_relative_to(folder) or any(part in path.parts for part in ['node_modules', 'dist', '.browser-check', '__pycache__']):
            continue
        baseline[relative(path)] = {'bytes': path.stat().st_size, 'sha256': sha256(path)}
    new_json(folder / 'preservation-baseline.json', {'files': baseline, 'created_at_utc': utcnow()})
    inherited_manifest = Path(args.official_acceptance).parent / 'delivery-manifest.json'
    if not inherited_manifest.exists():
        inherited_manifest = Path(args.official_acceptance).parent / 'system-delivery-manifest.json'
    check = verify(inherited_manifest)
    new_json(folder / 'inherited-delivery-verification.json', check)
    if check['status'] != 'PASS':
        raise ValueError('Inherited delivery manifest changed; inspect issues before reuse')
    source = source_manifest(context['run_id'], folder, run)
    if source['expected_movies'] != acceptance['movies'] or source['expected_logs'] != acceptance['events']:
        raise ValueError('Selected source counts disagree with official acceptance')
    new_json(folder / 'official-ingestion-inherited.json', {'status': 'PASS', 'checked_at_utc': utcnow(),
        'flume_run_id': run, 'ingestion_execution': 'historical, byte/source/config reverified now',
        'source_manifest_sha256': sha256(folder / 'source_manifest.json'),
        'events': source['expected_logs'], 'movies': source['expected_movies'], 'parts': len(source['files']) - 1,
        'input_sha256': source['flume_input_sha256'], 'source_config_hashes': pipeline_hashes(),
        'reconciliation': 'evidence/' + run + '/reconciliation.json'})
    ledger = Ledger(folder, {'HDFS_RUN_ID': context['run_id']})
    ledger.command(['docker', 'context', 'show'], 'docker-context')
    ledger.command(['docker', 'version'], 'docker-version')
    ledger.command(['docker', 'compose', 'version'], 'compose-version')
    ledger.command(['docker', 'volume', 'ls', '--format', '{{.Name}}'], 'all-volumes-before')
    nodes = runtime(context, ledger)
    new_json(folder / 'runtime-before.json', {'status': 'PASS', 'nodes': nodes, 'checked_at_utc': utcnow()})
    print(relative(folder / 'run-context.json'))


def command_context(args):
    context = load(args.context)
    if context.get('role') != 'official-main':
        raise ValueError('Requires prepared official-main context')
    official_selection(context, load(ROOT / context['official_acceptance']))
    folder = ROOT / context['evidence']
    source = load(folder / 'source_manifest.json')
    snapshot_namespaces(source)
    if (source['flume_run_id'], source['hdfs_run_id']) != (context['flume_run_id'], context['run_id']):
        raise ValueError('Context/source IDs disagree')
    return context, folder, source, Ledger(folder, {'HDFS_RUN_ID': context['run_id']})


def io(context, folder, ledger, label, upload=False):
    argv = [sys.executable, '-B', 'scripts/hdfs_io.py', '--context', relative(folder / 'run-context.json'),
            '--client', 'spark', '--label', label]
    if upload:
        argv.append('--upload')
    ledger.command(argv, label)
    return load(folder / (label + '.json'))


def no_jobs(ledger):
    _, text, _ = ledger.command(['docker', 'ps', '--format', '{{json .}}'], 'running-jobs-check')
    for line in text.splitlines():
        item = json.loads(line)
        if any(word in (item['Image'] + ' ' + item['Names']).lower() for word in ['spark', 'flume', 'tv2']):
            raise ValueError('Active Spark/Flume container; postpone restart/stop')


def persistence(context, folder, ledger):
    target = folder / 'persistence.json'
    if target.exists():
        raise FileExistsError(target)
    no_jobs(ledger)
    nodes = runtime(context, ledger)
    before_content = io(context, folder, ledger, 'persistence-before')
    base = compose(context['project'])
    versions = {}
    for role, node in nodes.items():
        _, text, _ = ledger.command(['docker', 'exec', node['id'], 'cat', node['store'] + '/current/VERSION'], 'version-before-' + role)
        versions[role] = properties(text)
        if versions[role]['clusterID'] != context['run_id']:
            raise ValueError('Wrong storage cluster')
    _, previous_logs, _ = ledger.command(base + ['logs', '--no-color'], 'logs-before-restart')
    no_jobs(ledger)
    ledger.command(base + ['restart', 'namenode', 'datanode'], 'restart-existing-services')
    after_nodes = runtime(context, ledger, start=True)
    after_versions = {}
    for role, node in after_nodes.items():
        _, text, _ = ledger.command(['docker', 'exec', node['id'], 'cat', node['store'] + '/current/VERSION'], 'version-after-' + role)
        after_versions[role] = properties(text)
    _, after_logs, _ = ledger.command(base + ['logs', '--no-color'], 'logs-after-restart')
    after_content = io(context, folder, ledger, 'persistence-after')
    def fingerprints(report):
        return [(f['uri'], f['bytes'], f['sha256']) for f in report['files']]
    checks = {'versions_unchanged': versions == after_versions,
              'same_containers_volumes': nodes == after_nodes,
              'full_content_unchanged': fingerprints(before_content) == fingerprints(after_content),
              'no_additional_format': after_logs.count('FORMAT_NEW_EMPTY_VOLUME') == previous_logs.count('FORMAT_NEW_EMPTY_VOLUME'),
              'verified_reuse': after_logs.count('REUSE_VERIFIED_VOLUME') - previous_logs.count('REUSE_VERIFIED_VOLUME') == 2,
              'before_after_pass': before_content['status'] == after_content['status'] == 'PASS'}
    result = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
              'checked_at_utc': utcnow(), 'before_properties': versions, 'after_properties': after_versions,
              'note': 'One NameNode/one DataNode; persistence only, no HA or production fault-tolerance claim.'}
    new_json(target, result)
    if result['status'] != 'PASS':
        raise ValueError('Persistence verification failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check', 'start', 'stop', 'stability', 'import', 'spark', 'persistence', 'history', 'seal'])
    parser.add_argument('--context')
    parser.add_argument('--source-context')
    parser.add_argument('--official-acceptance')
    parser.add_argument('--source-manifest', help='Additional historical snapshot to preserve, read-only')
    parser.add_argument('--flume-run-id')
    parser.add_argument('--evidence-dir')
    parser.add_argument('--input', help='Small stability input, never imported as official data')
    parser.add_argument('--label', default='import')
    parser.add_argument('--verification', default='import-repeat')
    args = parser.parse_args()
    if args.action == 'prepare':
        if not all([args.source_context, args.official_acceptance, args.evidence_dir]):
            parser.error('prepare requires --source-context --official-acceptance --evidence-dir')
        prepare(args)
        return 0
    if not args.context:
        parser.error('--context required')
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.label) or not re.fullmatch(r'[a-zA-Z0-9_-]+', args.verification):
        parser.error('Report labels must be simple names')
    context, folder, source, ledger = command_context(args)
    if args.action in ('check', 'start'):
        nodes = runtime(context, ledger, start=args.action == 'start')
        ledger.command(compose(context['project']) + ['exec', '-T', 'namenode', 'hdfs', 'dfs', '-ls', '-R', *snapshot_namespaces(source)], 'list-selected-snapshot')
        print(json.dumps({'status': 'PASS', 'nodes': nodes, 'movies_uri': source['movies_uri'], 'logs_uri': source['logs_uri']}, indent=2))
    elif args.action == 'stop':
        no_jobs(ledger)
        runtime(context, ledger)
        ledger.command(compose(context['project']) + ['stop', 'datanode', 'namenode'], 'stop-existing-services')
    elif args.action == 'stability':
        if (folder / 'stability.json').exists():
            raise FileExistsError('Stability proof exists; prepare a new acceptance or use the standalone batch runner')
        if not args.input:
            parser.error('--input required')
        path = (ROOT / args.input).resolve()
        relative(path)
        manifest = load(str(path) + '.manifest.json')
        if not path.is_relative_to(ROOT / 'data/generated') or not 1 <= manifest['events'] <= 10000 or sha256(path) != manifest['sha256']:
            raise ValueError('Stability input must be a verified small generated log')
        _, text, _ = ledger.command([sys.executable, '-B', 'scripts/run_pipeline.py', '--input', relative(path), '--timeout', '600'], 'current-flume-stability')
        state = runner_status(text)
        rec = load(ROOT / 'evidence' / state['run_id'] / 'reconciliation.json')
        if state['status'] != rec['status'] or state['status'] != 'PASS' or state['source_config_hashes'] != source['provenance']['source_config_hashes']:
            raise ValueError('Current stability ingestion differs/fails')
        new_json(folder / 'stability.json', {'status': 'PASS', 'run_id': state['run_id'], 'role': 'stability-only-never-official',
            'events': rec['output']['total'], 'parts': len(rec['output_files']), 'bytes': sum(f['bytes'] for f in rec['output_files']),
            'reconciliation_sha256': sha256(ROOT / 'evidence' / state['run_id'] / 'reconciliation.json')})
    elif args.action == 'import':
        runtime(context, ledger)
        io(context, folder, ledger, args.label, upload=True)
    elif args.action == 'spark':
        runtime(context, ledger)
        ledger.command(compose(context['project']) + ['--profile', 'spark', 'run', '--rm', '--no-deps', 'spark',
            '--driver-memory', '2g', 'scripts/spark_hdfs_validate.py', '--source-manifest', relative(folder / 'source_manifest.json'),
            '--hdfs-verification', relative(folder / (args.verification + '.json')), '--report', relative(folder / (args.label + '.json'))], 'spark-full-input-qa')
    elif args.action == 'persistence':
        persistence(context, folder, ledger)
    elif args.action == 'history':
        manifest_path = args.source_manifest or context.get('historical_source_manifest')
        if not manifest_path:
            parser.error('history requires --source-manifest or an inherited historical selection')
        manifest_path = relative(manifest_path)
        historical = load(ROOT / manifest_path)
        snapshot_namespaces(historical)
        if historical['hdfs_run_id'] != context['run_id']:
            raise ValueError('Historical snapshot belongs to a different cluster')
        ledger.command(compose(context['project']) + ['--profile', 'spark', 'run', '--rm', '--no-deps', 'spark',
            '--driver-memory', '1g', 'scripts/hdfs_hash_verify.py', '--source-manifest', manifest_path,
            '--report', relative(folder / 'historical-hdfs-after.json')], 'preserve-historical-hdfs')
        new_json(folder / 'historical-source-selection.json', {'source_manifest': manifest_path, 'sha256': sha256(ROOT / manifest_path)})
    elif args.action == 'seal':
        if (folder / 'acceptance.json').exists():
            raise FileExistsError('Acceptance already sealed; prepare a new folder')
        # Reports alone are insufficient if selected bytes/code changed afterwards.
        official_state = load(ROOT / 'evidence' / context['flume_run_id'] / 'status.json')
        if sha256(input_path_from_evidence(official_state['input'])) != source['flume_input_sha256']:
            raise ValueError('Official generated lineage changed before sealing')
        for item in source['files']:
            path = ROOT / item['local_path']
            if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
                raise ValueError('Selected local snapshot changed before sealing')
        if source['provenance']['source_config_hashes'] != pipeline_hashes():
            raise ValueError('Ingestion configuration changed before sealing')
        runtime_after = runtime(context, ledger)
        before_nodes = load(folder / 'runtime-before.json')['nodes']
        if runtime_after != before_nodes:
            raise ValueError('Original cluster/container/volume identity changed')
        _, volume_text, _ = ledger.command(['docker', 'volume', 'ls', '--format', '{{.Name}}'], 'all-volumes-after')
        before_volume_files = list((folder / 'commands').glob('all-volumes-before-*/stdout.txt'))
        original_volumes = set(before_volume_files[0].read_text(encoding='utf-8').split())
        if not original_volumes.issubset(set(volume_text.split())):
            raise ValueError('An original Docker volume is missing')
        new_json(folder / 'volumes-preserved.json', {'status': 'PASS', 'checked_at_utc': utcnow(),
            'original_volumes': sorted(original_volumes), 'current_volumes': sorted(volume_text.split()), 'nodes': runtime_after})
        preservation = verify(folder / 'preservation-baseline.json')
        new_json(folder / 'preservation-check.json', preservation)
        required = ['official-ingestion-inherited', 'stability', 'import-first', 'import-repeat', 'persistence', 'spark-full',
                    'preservation-check', 'volumes-preserved']
        for optional in ['demo-rejection', 'python-tests-counted', 'historical-hdfs-after']:
            if (folder / (optional + '.json')).exists():
                required.append(optional)
        if context.get('historical_source_manifest') and 'historical-hdfs-after' not in required:
            raise ValueError('Inherited historical HDFS preservation has not been reverified')
        reports = {name: load(folder / (name + '.json')) for name in required}
        if not all(r['status'] == 'PASS' for r in reports.values()):
            raise ValueError('Required acceptance evidence fails')
        imports = [reports[name] for name in ['import-first', 'import-repeat']]
        if any(r['source_manifest_sha256'] != sha256(folder / 'source_manifest.json') or len(r['files']) != len(source['files']) for r in imports):
            raise ValueError('Import reports have different source')
        if reports['import-repeat']['uploaded'] or reports['import-repeat']['skipped_verified'] != len(source['files']):
            raise ValueError('Repeat import must verify/skip all selected files')
        spark_report = reports['spark-full']
        if spark_report['source_manifest_sha256'] != sha256(folder / 'source_manifest.json') or spark_report['local_fallback'] or any(spark_report['errors'].values()):
            raise ValueError('Spark input QA does not attest this full HDFS snapshot')
        if spark_report['movies']['rows'] != source['expected_movies'] or spark_report['logs']['rows'] != source['expected_logs']:
            raise ValueError('Spark observed counts differ from official manifest')
        related = [spark_report, *imports]
        for report in related:
            for name, expected in report['source_hashes'].items():
                if sha256(ROOT / name) != expected:
                    raise ValueError('Executed HDFS/Spark code changed: ' + name)
        result = {'status': 'PASS', 'checked_at_utc': utcnow(), 'flume_run_id': context['flume_run_id'], 'hdfs_run_id': context['run_id'],
            'movies_uri': source['movies_uri'], 'logs_uri': source['logs_uri'], 'movies': reports['spark-full']['movies']['rows'],
            'events': reports['spark-full']['logs']['rows'], 'users': reports['spark-full']['logs']['users'],
            'files': len(source['files']), 'sink_parts': len(source['files']) - 1, 'bytes': reports['import-repeat']['total_bytes'],
            'checks': {name: r['status'] for name, r in reports.items()}, 'official_execution': 'inherited; content/source reverified',
            'current_stability_run': reports['stability']['run_id'], 'preserved_files': preservation['files_checked'],
            'python_unit_tests': reports.get('python-tests-counted', {}).get('tests'),
            'source_manifest_sha256': sha256(folder / 'source_manifest.json')}
        if (folder / 'historical-source-selection.json').exists():
            result['historical_source_manifest'] = load(folder / 'historical-source-selection.json')['source_manifest']
        new_json(folder / 'acceptance.json', result)
        # Same scoped manifest format and verifier as existing delivery tooling.
        scopes = ['scripts', 'src', 'config', 'tests', 'data/raw', 'data/processed', relative(folder),
                  'evidence/' + context['flume_run_id'], 'data/runs/' + context['flume_run_id'] + '/output',
                  'evidence/' + reports['stability']['run_id'], 'data/runs/' + reports['stability']['run_id'] + '/output']
        files = {ROOT / name for name in ['README.md', 'docs/week3_tv1_demo.md', 'docs/week3_tv1_architecture.md',
            'Dockerfile', 'compose.yaml', 'compose.hdfs.yaml', '.gitattributes', '.gitignore', 'requirements.txt']}
        state = load(ROOT / 'evidence' / context['flume_run_id'] / 'status.json')
        generated = input_path_from_evidence(state['input'])
        files.update([generated, Path(str(generated) + '.manifest.json')])
        small_state = load(ROOT / 'evidence' / reports['stability']['run_id'] / 'status.json')
        small_input = input_path_from_evidence(small_state['input'])
        files.update([small_input, Path(str(small_input) + '.manifest.json')])
        # Retain all current ingestion attempts, including a successful batch
        # whose first wrapper aggregation failed. No earlier run is rewritten.
        for output in (folder / 'commands').glob('current-flume-stability-*/stdout.txt'):
            attempted = runner_status(output.read_text(encoding='utf-8'))['run_id']
            for scope in ['evidence/' + attempted, 'data/runs/' + attempted + '/output']:
                if scope not in scopes:
                    scopes.append(scope)
        for scope in scopes:
            files.update(p for p in (ROOT / scope).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc', '.part'])
        entries = {relative(p): {'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in sorted(files)}
        new_json(folder / 'delivery-manifest.json', {'created_at_utc': utcnow(), 'scope': scopes, 'files': entries,
            'exclusions': ['volume/channel/spool state', 'historical snapshots not selected', 'Dashboard/ML outputs', 'manifest and subsequent verifier reports']})
        verified = verify(folder / 'delivery-manifest.json')
        new_json(folder / 'delivery-verification.json', verified)
        print(json.dumps({'acceptance': result, 'delivery': verified}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
