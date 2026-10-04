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


def run(input_file, timeout=300, demo_proof=None):
    os.chdir(ROOT)
    input_file = Path(input_file).resolve()
    run_id = 'run-' + uuid.uuid4().hex[:12]
    evidence = ROOT / 'evidence' / run_id
    evidence.mkdir(parents=True)
    commands = []
    state = {'run_id': run_id, 'started_at_utc': utcnow(), 'status': 'NOT_RUN', 'input': str(input_file)}
    env = os.environ.copy()
    run_dir = ROOT / 'data' / 'runs' / run_id
    log_dir = ROOT / 'logs' / run_id
    env['RUN_DIR'], env['LOG_DIR'] = run_dir.as_posix(), log_dir.as_posix()
    base = ['docker', 'compose', '-p', 'movie-' + run_id]

    def command(args, filename, check=True):
        commands.append(args)
        with (evidence / filename).open('w', encoding='utf-8') as f:
            result = subprocess.run(args, env=env, stdout=f, stderr=subprocess.STDOUT, text=True)
        if check and result.returncode:
            raise RuntimeError(f'Command exited {result.returncode}; inspect {filename}')
        return result

    started = False
    try:
        initial = validate(input_file, 'data/processed/movies.csv', report=evidence / 'input_validation.json')
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
        if shutil.which('docker') is None:
            state['status'] = 'BLOCKED_ENVIRONMENT'
            raise RuntimeError('Docker executable not found. Install/start Docker Desktop with Linux containers.')
        command(['docker', 'version'], 'docker-version.txt')
        command(['docker', 'compose', 'version'], 'compose-version.txt')
        for folder in ['spool', 'output', 'channel/checkpoint', 'channel/data']:
            (run_dir / folder).mkdir(parents=True)
        log_dir.mkdir(parents=True)
        command(base + ['config'], 'compose-resolved.yaml')
        command(base + ['build'], 'build.log')
        started = True
        command(base + ['up', '-d'], 'up.log')
        command(base + ['images'], 'images.txt')
        command(base + ['exec', '-T', 'flume', 'java', '-version'], 'java-version.txt')
        command(base + ['exec', '-T', 'flume', '/opt/flume/bin/flume-ng', 'version'], 'flume-version.txt')
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
        while time.monotonic() < deadline:
            completed = staged.with_name(staged.name + '.COMPLETED').exists()
            count = 0
            for path in (run_dir / 'output').glob('*'):
                if path.is_file():
                    with path.open('rb') as f:
                        count += sum(1 for line in f if line.endswith(b'\n'))
            if completed and count >= expected:
                drained = True
                break
            time.sleep(2)
        command(base + ['stop'], 'stop.log')
        # Reconcile only after sink is stopped and file buffers closed.
        result = validate(input_file, 'data/processed/movies.csv', run_dir / 'output', evidence / 'reconciliation.json')
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
    a = p.parse_args()
    result = run(a.input, a.timeout, a.demo_proof)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
