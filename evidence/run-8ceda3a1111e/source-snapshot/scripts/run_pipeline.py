"""Real Docker/Flume E2E run with isolated directories and saved evidence."""
import argparse
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from common import sha256, utcnow, write_json
from validate_pipeline import validate

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILES = ['Dockerfile', 'compose.yaml', 'config/flume.conf', 'config/flume-env.sh',
                  'config/log4j2.xml', 'scripts/run_flume.sh', 'scripts/verify_archive.py',
                  'scripts/run_pipeline.py', 'scripts/validate_pipeline.py', 'scripts/movie_quality.py', 'scripts/common.py']


def pipeline_hashes():
    return {p: sha256(ROOT / p) for p in PIPELINE_FILES}


def run(input_file, timeout=300, demo_proof=None, movies='data/processed/movies.csv'):
    os.chdir(ROOT)
    input_file = Path(input_file).resolve()
    run_id = 'run-' + uuid.uuid4().hex[:12]
    evidence = ROOT / 'evidence' / run_id
    evidence.mkdir(parents=True)
    commands = []
    state = {'run_id': run_id, 'started_at_utc': utcnow(), 'status': 'NOT_RUN', 'input': str(input_file)}
    state['source_config_hashes'] = pipeline_hashes()
    state['movies'] = str(Path(movies).resolve())
    for name in PIPELINE_FILES:
        target = evidence / 'source-snapshot' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
    state['git_revision'] = revision.stdout.strip() if revision.returncode == 0 else None
    env = os.environ.copy()
    run_dir = ROOT / 'data' / 'runs' / run_id
    log_dir = ROOT / 'logs' / run_id
    env['RUN_DIR'], env['LOG_DIR'] = run_dir.as_posix(), log_dir.as_posix()
    base = ['docker', 'compose', '-p', 'movie-' + run_id]

    def command(args, filename, check=True):
        record = {'argv': args, 'cwd': str(ROOT), 'started_at_utc': utcnow(), 'log': filename}
        commands.append(record)
        with (evidence / filename).open('x', encoding='utf-8') as f:
            result = subprocess.run(args, env=env, stdout=f, stderr=subprocess.STDOUT, text=True)
        record.update({'exit_code': result.returncode, 'finished_at_utc': utcnow()})
        if check and result.returncode:
            raise RuntimeError(f'Command exited {result.returncode}; inspect {filename}')
        return result

    started = False
    try:
        initial = validate(input_file, movies, report=evidence / 'input_validation.json')
        if initial['status'] != 'INPUT_PASS':
            raise ValueError('Input validation failed')
        if initial['input']['total'] > 10000:
            if demo_proof is None:
                raise ValueError('Main input requires --demo-proof evidence/<demo-run>/status.json')
            proof_path = Path(demo_proof)
            proof = json.loads(proof_path.read_text(encoding='utf-8'))
            demo_result = json.loads((proof_path.parent / 'reconciliation.json').read_text(encoding='utf-8'))
            if proof['status'] != 'PASS' or demo_result['status'] != 'PASS' or not 1 <= demo_result['input']['total'] <= 10000:
                raise ValueError('Demo proof is not a successful small E2E run')
            if proof.get('config_sha256') != sha256('config/flume.conf'):
                raise ValueError('Config changed since demo; rerun demo')
            if proof.get('source_config_hashes') != state['source_config_hashes']:
                raise ValueError('Pipeline source/image configuration changed since demo; rerun demo')
        if shutil.which('docker') is None:
            state['status'] = 'BLOCKED_ENVIRONMENT'
            raise RuntimeError('Docker executable not found. Install/start Docker Desktop with Linux containers.')
        version = command(['docker', 'version'], 'docker-version.txt', check=False)
        if version.returncode:
            state['status'] = 'BLOCKED_ENVIRONMENT'
            raise RuntimeError('Docker Engine inaccessible; see docker-version.txt')
        command(['docker', 'compose', 'version'], 'compose-version.txt')
        for folder in ['spool', 'output', 'channel/checkpoint', 'channel/data']:
            (run_dir / folder).mkdir(parents=True)
        log_dir.mkdir(parents=True)
        command(base + ['config'], 'compose-resolved.yaml')
        command(base + ['build', 'flume'], 'build.log')
        started = True
        command(base + ['up', '-d'], 'up.log')
        command(base + ['images'], 'images.txt')
        command(['docker', 'image', 'inspect', 'movie-log-flume:1.11.0-local'], 'image-inspect.json')
        command(base + ['exec', '-T', 'flume', 'java', '-version'], 'java-version.txt')
        command(base + ['exec', '-T', 'flume', '/opt/flume/bin/flume-ng', 'version'], 'flume-version.txt')
        command(base + ['exec', '-T', 'flume', 'cat', '/opt/flume/bin/flume-ng'], 'launcher-snapshot.sh')
        command(base + ['exec', '-T', 'flume', 'sh', '-c', 'ps -eo pid,args | grep "org.apache.flume.node.Application" | grep -v grep'], 'jvm-process.txt')
        command(base + ['exec', '-T', 'flume', 'bash', '-c', 'source /opt/flume/conf/flume-env.sh; java $JAVA_OPTS -XX:+PrintFlagsFinal -version'], 'jvm-effective-flags.txt')
        command(base + ['exec', '-T', 'flume', 'sh', '-c', 'for i in $(seq 1 60); do curl -fsS http://127.0.0.1:41414/metrics && exit 0; sleep 1; done; exit 1'], 'metrics-start.json')
        # Copy completely to an ignored temporary name, then atomically rename in SAME directory.
        staged = run_dir / 'spool' / (uuid.uuid4().hex + '.jsonl')
        temporary = staged.with_suffix('.tmp')
        shutil.copyfile(input_file, temporary)
        temporary.rename(staged)
        state.update({'input_sha256': sha256(input_file), 'config_sha256': sha256('config/flume.conf'),
                      'spooled_file': str(staged), 'output_dir': str(run_dir / 'output')})
        deadline = time.monotonic() + timeout
        expected = initial['input']['total']
        drained = False
        positions = {}
        progress_at = 0
        while time.monotonic() < deadline:
            completed = staged.with_name(staged.name + '.COMPLETED').exists()
            count = 0
            for path in (run_dir / 'output').glob('*'):
                if path.is_file():
                    offset, lines = positions.get(path, (0, 0))
                    with path.open('rb') as f:
                        f.seek(offset)
                        for line in f:
                            if not line.endswith(b'\n'):
                                break
                            offset += len(line)
                            lines += 1
                    positions[path] = (offset, lines)
                    count += lines
            if time.monotonic() >= progress_at:
                with (evidence / 'progress.jsonl').open('a', encoding='utf-8') as f:
                    f.write(json.dumps({'at_utc': utcnow(), 'spool_completed': completed, 'observed_complete_lines': count, 'expected': expected}) + '\n')
                progress_at = time.monotonic() + 10
            if completed and count >= expected:
                drained = True
                break
            time.sleep(2)
        command(base + ['exec', '-T', 'flume', 'curl', '-fsS', 'http://127.0.0.1:41414/metrics'], 'metrics-final.json', check=False)
        command(base + ['stop'], 'stop.log')
        # Reconcile only after sink is stopped and file buffers closed.
        result = validate(input_file, movies, run_dir / 'output', evidence / 'reconciliation.json')
        state['spool_completed'] = staged.with_name(staged.name + '.COMPLETED').exists()
        state['status'] = 'PASS' if drained and state['spool_completed'] and result['status'] == 'PASS' else 'FAIL'
        if not drained:
            state['reason'] = 'Timeout waiting for ingestion/drain; reconciliation records actual output'
        for label, paths in [('input', [input_file]), ('output', sorted((run_dir / 'output').glob('*')))]:
            sample = []
            for path in paths:
                if path.is_file():
                    with path.open(encoding='utf-8') as f:
                        for line in f:
                            sample.append(line)
                            if len(sample) == 5:
                                break
                if len(sample) == 5:
                    break
            (evidence / (label + '-sample.jsonl')).write_text(''.join(sample), encoding='utf-8')
    except Exception as exc:
        if state['status'] != 'BLOCKED_ENVIRONMENT':
            state['status'] = 'FAIL'
        state['reason'] = str(exc)
    finally:
        if started:
            for args, filename in [(base + ['stop'], 'stop-final.log'),
                                   (base + ['logs', '--no-color', '--timestamps'], 'flume-operational.log'),
                                   (base + ['down'], 'down.log')]:
                try:
                    command(args, filename, check=False)
                except Exception as exc:
                    state['cleanup_error'] = str(exc)
        state['finished_at_utc'] = utcnow()
        write_json(evidence / 'commands.json', {'cwd': str(ROOT), 'environment': {'RUN_DIR': env['RUN_DIR'], 'LOG_DIR': env['LOG_DIR']}, 'commands': commands})
        write_json(evidence / 'status.json', state)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return state


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', default='data/generated/demo.jsonl')
    p.add_argument('--timeout', type=int, default=300)
    p.add_argument('--demo-proof')
    p.add_argument('--movies', default='data/processed/movies.csv')
    a = p.parse_args()
    result = run(a.input, a.timeout, a.demo_proof, a.movies)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
