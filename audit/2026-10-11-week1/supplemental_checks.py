"""Supplemental audit of small samples and validator limitations; fixtures only."""
import collections
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_pipeline import validate

def save(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

all_rows, samples, types = [], [], collections.defaultdict(set)
for p in sorted((ROOT/'evidence').rglob('*.jsonl')):
    raw = p.read_bytes()
    lines = raw.decode('utf-8', errors='strict').splitlines()
    rows = [json.loads(x) for x in lines]
    all_rows.extend(rows)
    for row in rows:
        for key, val in row.items():
            types[key].add(type(val).__name__)
    samples.append({'path': p.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'rows': len(rows), 'unique_event_ids': len({x['eventId'] for x in rows}), 'users': len({x['userId'] for x in rows}), 'movies': len({x['movieId'] for x in rows}), 'sessions': len({x['sessionId'] for x in rows}), 'actions': dict(collections.Counter(x['action'] for x in rows)), 'timestamp_min': min(x['timestamp'] for x in rows), 'timestamp_max': max(x['timestamp'] for x in rows), 'final_newline': raw.endswith(b'\n'), 'all_synthetic': all(x['isSynthetic'] is True and x['durationSource']=='synthetic' for x in rows), 'all_required_present': all(len(x)==12 for x in rows)})
save('sample-measurements.json', {'warning': 'Small historical samples only; not delivered datasets, not new Flume output.', 'files': samples, 'physical_rows': len(all_rows), 'distinct_event_ids_across_files': len({x['eventId'] for x in all_rows}), 'observed_json_types': {k: sorted(v) for k,v in types.items()}})

fix = OUT/'fixtures'/'validator-probes'
fix.mkdir(parents=True, exist_ok=True)
movies = fix/'movies.csv'
movies.write_text('movieId,title,genres\n1,Fixture (2001),Drama\n1,Duplicate (2002),Comedy\n', encoding='utf-8')
event = {'eventId':'fixture-event-1','userId':'fixture-user-1','sessionId':'fixture-session-1','movieId':1,'action':'view','timestamp':'2026-09-01T00:00:00Z','watchDuration':0,'sequenceNumber':0,'runId':'audit-fixture','isSynthetic':True,'simulatedMovieDuration':3600,'durationSource':'synthetic'}
input_path = fix/'input.jsonl'
input_path.write_text(json.dumps(event)+'\n', encoding='utf-8')
sink = fix/'mock-sink'
sink.mkdir(exist_ok=True)
(sink/'copied-fixture.jsonl').write_bytes(input_path.read_bytes())
(sink/'empty.jsonl').write_bytes(b'')
with contextlib.redirect_stdout(io.StringIO()):
    result = validate(input_path, movies, sink, fix/'validator-report.json')
save('validator-probes.json', {'fixture_only': True, 'never_flume_evidence': True, 'source': 'supplemental_checks.py', 'movies_rows': 2, 'movies_unique_ids': 1, 'empty_sink_files': 1, 'validator_status': result['status'], 'validator_output': result['output'], 'observation': 'Validator collapses movieIds into a set and does not reject/report empty sink files separately. Separate movie quality checks are necessary; empty roll files can be normal but should be inventoried.'})

review = json.loads((OUT/'historical-evidence-review.json').read_text(encoding='utf-8'))
concise = []
for run in review:
    r = run.get('reconciliation', {})
    concise.append({'run': run['run'], 'status': run['status'], 'input': r.get('input'), 'output': r.get('output'), 'missing': r.get('missing_event_ids'), 'extra': r.get('unexpected_event_ids'), 'changed': r.get('changed_payloads'), 'files': run.get('output_file_count_reported'), 'bytes': run.get('output_bytes_reported'), 'operational_log': run.get('log_markers',{}).get('flume-operational.log'), 'samples_equal': run.get('samples_equal')})
save('historical-summary.json', concise)
tracked = json.loads((OUT/'git-tracked.json').read_text(encoding='utf-8'))['output'].splitlines()
manifest = json.loads((ROOT/'evidence/delivery_manifest.json').read_text(encoding='utf-8'))
config = (ROOT/'config/flume.conf').read_bytes()
hashes = {'current_config_sha256': hashlib.sha256(config).hexdigest(), 'historical_config_hashes': sorted({r['status']['config_sha256'] for r in review if r.get('status') and 'config_sha256' in r['status']}), 'manifest_exact_source_matches': [k for k,v in manifest.items() if k.startswith(('scripts/','tests/','config/')) and (ROOT/k).is_file() and hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v['sha256']], 'git_tracked_files': len(tracked)}
save('source-history-links.json', hashes)
print(json.dumps({'samples':len(samples),'sample_rows':len(all_rows),'sample_distinct_events':len({x['eventId'] for x in all_rows}),'fixture_probe_status':result['status'],'source_hashes':hashes},ensure_ascii=False,indent=2))
