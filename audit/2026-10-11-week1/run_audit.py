"""Read-only project audit; new results and isolated fixtures stay in this folder."""
import ast
import collections
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
os.chdir(ROOT)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
FIX = OUT / 'fixtures'
FIX.mkdir(exist_ok=True)
env = os.environ.copy()
for key in ['TMP', 'TEMP', 'TMPDIR']:
    env[key] = str(FIX)
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['PYTHONIOENCODING'] = 'utf-8'

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

commands = []
def command(args, name, timeout=30):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec = {'argv': args, 'cwd': str(ROOT), 'started_at_utc': started}
    try:
        p = subprocess.run(args, capture_output=True, timeout=timeout, env=env)
        raw = p.stdout + p.stderr
        rec.update(exit_code=p.returncode, output=raw.decode('utf-16-le' if b'\x00' in raw else 'utf-8', errors='replace'))
    except FileNotFoundError as e:
        rec.update(exit_code=None, error=str(e), reason='executable_not_found')
    except subprocess.TimeoutExpired as e:
        rec.update(exit_code=None, reason='timeout', timeout_seconds=timeout, output=((e.stdout or b'') + (e.stderr or b'')).decode('utf-8', errors='replace'))
    (OUT / name).write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    commands.append(rec)
    save('commands.json', commands)
    print(name, rec.get('exit_code'), rec.get('reason', ''), flush=True)
    return rec

git = shutil.which('git') or r'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
revision = command([git, 'rev-parse', 'HEAD'], 'git-revision.json')
before = command([git, 'status', '--porcelain=v1', '--untracked-files=all'], 'git-before.json')
tracked = command([git, 'ls-files'], 'git-tracked.json')['output'].splitlines()
files = sorted(p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts and 'audit' not in p.relative_to(ROOT).parts)
inventory, contents, parsed, syntax = [], {}, {}, []
with (OUT / 'numbered-project-files.txt').open('w', encoding='utf-8') as transcript:
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        raw = p.read_bytes()
        item = {'path': rel, 'bytes': len(raw), 'sha256': digest(raw), 'sha256_lf': digest(raw.replace(b'\r\n', b'\n')), 'tracked': rel in tracked}
        try:
            text = raw.decode('utf-8', errors='strict')
            contents[rel] = text
            numbered_lines = text.split('\n')
            if numbered_lines and numbered_lines[-1] == '':
                numbered_lines.pop()
            item.update(lines=len(numbered_lines), utf8='valid', bom=text.startswith('\ufeff'))
            transcript.write('\nFILE: ' + rel + '\n')
            for number, line in enumerate(numbered_lines, 1):
                transcript.write(f'{number:5}: {line.rstrip(chr(13)).replace(chr(13), "<CR>")}\n')
            if p.suffix == '.json':
                parsed[rel] = json.loads(text)
            if p.suffix == '.py':
                ast.parse(text, filename=rel)
                syntax.append({'path': rel, 'status': 'PARSE_OK'})
        except (UnicodeError, ValueError, SyntaxError) as e:
            item['read_error'] = str(e)
        inventory.append(item)
save('inventory.json', inventory)
save('syntax.json', syntax)
ancestors = [ROOT, *ROOT.parents]
save('repository-instructions.json', {'checked': [str(p / 'AGENTS.md') for p in ancestors], 'found': [str(p / 'AGENTS.md') for p in ancestors if (p / 'AGENTS.md').exists()], 'nested': [x['path'] for x in inventory if x['path'].endswith('AGENTS.md')]})
manifest = parsed['evidence/delivery_manifest.json']
by_path = {x['path']: x for x in inventory}
matches, changed, missing = [], [], []
for rel, expected in manifest.items():
    actual = by_path.get(rel)
    if actual is None:
        missing.append(rel)
    elif actual['sha256'] == expected['sha256'] and actual['bytes'] == expected['bytes']:
        matches.append(rel)
    else:
        changed.append({'path': rel, 'expected': expected, 'actual': actual, 'matches_after_lf_normalization': actual['sha256_lf'] == expected['sha256']})
save('manifest-comparison.json', {'entries': len(manifest), 'matched': matches, 'changed': changed, 'missing': missing, 'not_covered': sorted(set(by_path) - set(manifest))})

runs = []
for d in sorted((ROOT / 'evidence').glob('run-*')):
    prefix = d.relative_to(ROOT).as_posix() + '/'
    status = parsed.get(prefix + 'status.json')
    rec = parsed.get(prefix + 'reconciliation.json')
    state = {'run': d.name, 'status': status, 'commands': parsed.get(prefix + 'commands.json'), 'input_validation': parsed.get(prefix + 'input_validation.json')}
    if rec:
        state['reconciliation'] = {k: v for k, v in rec.items() if k != 'output_files'}
        refs = rec.get('output_files', [])
        state['output_file_count_reported'] = len(refs)
        state['output_bytes_reported'] = sum(x['bytes'] for x in refs)
        state['empty_output_files_reported'] = sum(x['bytes'] == 0 for x in refs)
        state['output_files_present_at_saved_paths'] = sum(Path(x['path']).exists() for x in refs)
        state['output_files_present_in_current_run'] = sum(1 for p in (ROOT / 'data/runs' / d.name / 'output').glob('*') if p.is_file())
    state['log_markers'] = {}
    for p in sorted(d.iterdir()):
        if p.suffix in ['.log', '.txt', '.yaml']:
            lines = contents[p.relative_to(ROOT).as_posix()].split('\n')
            if lines and lines[-1] == '':
                lines.pop()
            marker = ['ERROR', 'Exception', 'WARN', 'Starting', 'started', 'Spooling', 'FileChannel', 'RollingFile', 'COMPLETE', 'Flume 1.', 'openjdk', 'version', 'DONE', 'CACHED', 'permission', 'denied']
            state['log_markers'][p.name] = {'lines': len(lines), 'selected': [{'line': i, 'text': line} for i, line in enumerate(lines, 1) if any(m.lower() in line.lower() for m in marker)]}
    state['samples'] = {}
    for label in ['input', 'output']:
        file = prefix + label + '-sample.jsonl'
        if file in contents:
            rows = [json.loads(line) for line in contents[file].splitlines()]
            state['samples'][label] = {'rows': len(rows), 'event_ids': [x['eventId'] for x in rows], 'canonical_sha256': digest(json.dumps(rows, sort_keys=True).encode()), 'fields': sorted(rows[0]) if rows else []}
    if len(state['samples']) == 2:
        state['samples_equal'] = state['samples']['input']['canonical_sha256'] == state['samples']['output']['canonical_sha256']
    runs.append(state)
save('historical-evidence-review.json', runs)
save('artifact-presence.json', {'data': [x for x in inventory if x['path'].startswith('data/')], 'logs': [x for x in inventory if x['path'].startswith('logs/')], 'required': {x: (ROOT/x).exists() for x in ['data/raw/ml-latest-small.zip','data/raw/download_manifest.json','data/raw/ml-latest-small/README.txt','data/raw/ml-latest-small/movies.csv','data/processed/movies.csv','data/generated/demo.jsonl','data/generated/main.jsonl','data/runs/run-a9b3a8a26afb/output','data/runs/run-f63c810e9d8d/output']}})
save('environment-current.json', {'audit_date_local': '2026-10-11', 'timezone': 'Asia/Saigon', 'os': platform.platform(), 'python': sys.version, 'python_executable': sys.executable, 'tools_in_path': {k: shutil.which(k) for k in ['python','py','java','docker','spark-submit','git']}, 'pyspark_spec': str(importlib.util.find_spec('pyspark')), 'source_config_hash': by_path['config/flume.conf']})

command([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], 'tests-current.json', 60)
command([sys.executable, '-B', 'scripts/spark_smoke_test.py'], 'spark-host-attempt.json', 40)
command([sys.executable, '-B', 'scripts/validate_pipeline.py', '--input', 'data/generated/demo.jsonl', '--input-only', '--report', str(OUT/'demo-recheck.json')], 'dataset-validation-attempt.json')
command(['java', '-version'], 'java-host.json')
command(['docker', 'version'], 'docker-version-current.json', 25)
command(['docker', 'compose', 'version'], 'compose-version-current.json', 25)
command(['docker', 'compose', 'config'], 'compose-config-current.json', 25)
command(['docker', 'image', 'ls', '--no-trunc'], 'docker-images-current.json', 25)
command(['docker', 'ps', '-a', '--no-trunc'], 'docker-containers-current.json', 25)
after = command([git, 'status', '--porcelain=v1', '--untracked-files=all'], 'git-after.json')
preserved = [{'path': x['path'], 'same': digest((ROOT/x['path']).read_bytes()) == x['sha256']} for x in inventory]
save('preservation.json', {'project_files': len(preserved), 'changed': [x for x in preserved if not x['same']], 'all_preserved': all(x['same'] for x in preserved)})
print(json.dumps({'files': len(inventory), 'manifest_matches': len(matches), 'manifest_changed': len(changed), 'manifest_missing': len(missing), 'manifest_uncovered': len(set(by_path)-set(manifest)), 'python_sources': len(syntax)}, ensure_ascii=False), flush=True)
