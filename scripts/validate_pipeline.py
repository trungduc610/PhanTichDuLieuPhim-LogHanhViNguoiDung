"""Streaming JSONL checks + on-disk SQLite reconciliation. Never simulates Flume."""
import argparse
import csv
import hashlib
import json
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from common import parse_time, sha256, utcnow, write_json

REQUIRED = {'eventId', 'userId', 'sessionId', 'movieId', 'action', 'timestamp', 'watchDuration',
            'sequenceNumber', 'isSynthetic', 'simulatedMovieDuration', 'durationSource', 'runId'}


def validate(input_path, movies, output_dir=None, report='evidence/validation.json'):
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    with open(movies, encoding='utf-8', newline='') as f:
        mids = {int(r['movieId']) for r in csv.DictReader(f)}
    stats = {'checked_at_utc': utcnow(), 'mode': 'input_only' if output_dir is None else 'pipeline_reconciliation',
             'input_sha256': sha256(input_path), 'movies_sha256': sha256(movies), 'errors_sample': []}
    with tempfile.TemporaryDirectory(prefix='movie-validate-') as tmp:
        db = sqlite3.connect(str(Path(tmp) / 'validation.sqlite'))
        db.execute('PRAGMA cache_size=-16384')
        db.execute('CREATE TABLE events (side TEXT, id TEXT, payload TEXT, sid TEXT, seq INT, PRIMARY KEY(side,id))')
        db.execute('CREATE TABLE sessions (uid TEXT, start TEXT, end TEXT)')
        counts = {s: Counter() for s in ['input', 'output']}

        def error(side, location, message):
            counts[side]['invalid'] += 1
            if len(stats['errors_sample']) < 20:
                stats['errors_sample'].append({'side': side, 'location': location, 'error': str(message)})

        def ingest(path, side):
            with path.open('rb') as f:
                for number, line in enumerate(f, 1):
                    counts[side]['total'] += 1
                    try:
                        if not line.endswith(b'\n'):
                            raise ValueError('Missing newline / potentially truncated event')
                        decoded = line.decode('utf-8', errors='strict')
                        if len(decoded.rstrip('\r\n')) > 16384:
                            raise ValueError('Event exceeds Flume LINE maxLineLength')
                        e = json.loads(decoded)
                        if not isinstance(e, dict) or not REQUIRED.issubset(e):
                            raise ValueError('Missing required fields')
                        for k in ['eventId', 'sessionId', 'userId', 'runId']:
                            if not isinstance(e[k], str) or not e[k]:
                                raise ValueError('Invalid ' + k)
                        for k in ['movieId', 'watchDuration', 'sequenceNumber', 'simulatedMovieDuration']:
                            if type(e[k]) is not int or e[k] < 0:
                                raise ValueError('Invalid integer ' + k)
                        if e['movieId'] not in mids:
                            raise ValueError('Unknown movieId')
                        if e['action'] not in ['view', 'play', 'pause', 'stop', 'complete']:
                            raise ValueError('Unknown action')
                        if e['action'] in ['view', 'play'] and e['watchDuration'] != 0:
                            raise ValueError('view/play must have zero watchDuration')
                        if not e['timestamp'].endswith('Z'):
                            raise ValueError('Timestamp must use UTC Z')
                        parse_time(e['timestamp'])
                        if e['isSynthetic'] is not True or e['durationSource'] != 'synthetic' or e['simulatedMovieDuration'] <= 0:
                            raise ValueError('Missing synthetic provenance')
                        payload = json.dumps(e, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
                        previous = db.execute('SELECT payload FROM events WHERE side=? AND id=?', (side, e['eventId'])).fetchone()
                        if previous:
                            counts[side]['duplicates'] += 1
                            if previous[0] != payload:
                                counts[side]['conflicting_ids'] += 1
                        else:
                            db.execute('INSERT INTO events VALUES(?,?,?,?,?)', (side, e['eventId'], payload, e['sessionId'], e['sequenceNumber']))
                            counts[side]['unique'] += 1
                    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError) as exc:
                        error(side, f'{path}:{number}', exc)
                    if number % 10000 == 0:
                        db.commit()

        ingest(input_path, 'input')
        paths = [] if output_dir is None else sorted(p for p in Path(output_dir).glob('*') if p.is_file() and not p.name.startswith('.'))
        for path in paths:
            ingest(path, 'output')
        db.commit()
        db.execute('CREATE INDEX session_order ON events(side,sid,seq)')
        # Validate input session semantics independent of physical order of the JSONL.
        # Output is checked for identical canonical payload by eventId below.
        prior_sid, group = None, []
        session_errors, valid_sessions = 0, 0
        def check_session(g):
            nonlocal session_errors, valid_sessions
            try:
                first = g[0]
                if first['action'] != 'view':
                    raise ValueError('Session must begin with view')
                expected, playing, watched, previous_time = 0, False, 0, None
                previous_action = None
                for e in g:
                    if any(e[k] != first[k] for k in ['movieId', 'userId', 'runId', 'simulatedMovieDuration']):
                        raise ValueError('Session identity/runtime changed')
                    if e['sequenceNumber'] != expected:
                        raise ValueError('Missing/duplicate sequenceNumber')
                    t = parse_time(e['timestamp'])
                    if previous_time is not None and t <= previous_time:
                        raise ValueError('Non-increasing session timestamp')
                    action = e['action']
                    if expected == 0:
                        if action != 'view':
                            raise ValueError('Missing initial view')
                    elif action == 'play':
                        if playing or previous_action not in ['view', 'pause']:
                            raise ValueError('Invalid play transition')
                        playing = True
                    elif action in ['pause', 'stop', 'complete']:
                        if not playing or e['watchDuration'] != int((t - previous_time).total_seconds()):
                            raise ValueError('Invalid duration/transition from play')
                        playing = False
                        if action in ['stop', 'complete'] and expected != len(g) - 1:
                            raise ValueError('Events after terminal action')
                    else:
                        raise ValueError('Repeated view')
                    watched += e['watchDuration']
                    expected += 1
                    previous_time, previous_action = t, action
                if len(g) != 1 and g[-1]['action'] not in ['stop', 'complete']:
                    raise ValueError('Unfinished session')
                if watched > first['simulatedMovieDuration'] or (g[-1]['action'] == 'complete' and watched != first['simulatedMovieDuration']):
                    raise ValueError('Invalid completion/runtime total')
                if g[-1]['action'] == 'stop' and watched >= first['simulatedMovieDuration']:
                    raise ValueError('stop must occur before complete')
                db.execute('INSERT INTO sessions VALUES(?,?,?)', (first['userId'], first['timestamp'], g[-1]['timestamp']))
                valid_sessions += 1
            except ValueError as exc:
                session_errors += 1
                if len(stats['errors_sample']) < 20:
                    stats['errors_sample'].append({'sessionId': g[0]['sessionId'], 'error': str(exc)})
        for sid, payload in db.execute("SELECT sid,payload FROM events WHERE side='input' ORDER BY sid,seq"):
            if prior_sid is not None and sid != prior_sid:
                check_session(group)
                group = []
            group.append(json.loads(payload))
            prior_sid = sid
        if group:
            check_session(group)
        overlap, previous_uid, previous_end = 0, None, None
        for uid, start, end in db.execute('SELECT uid,start,end FROM sessions ORDER BY uid,start'):
            if uid == previous_uid and start <= previous_end:
                overlap += 1
            previous_end = max(end, previous_end) if uid == previous_uid else end
            previous_uid = uid
        stats.update({'session_errors': session_errors, 'valid_sessions': valid_sessions, 'user_overlap_errors': overlap})
        for side in counts:
            stats[side] = {k: counts[side][k] for k in ['total', 'unique', 'duplicates', 'conflicting_ids', 'invalid']}
        stats['output_files'] = [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in paths]
        missing = db.execute("SELECT count(*) FROM events i LEFT JOIN events o ON o.side='output' AND i.id=o.id WHERE i.side='input' AND o.id IS NULL").fetchone()[0]
        extra = db.execute("SELECT count(*) FROM events o LEFT JOIN events i ON i.side='input' AND i.id=o.id WHERE o.side='output' AND i.id IS NULL").fetchone()[0]
        changed = db.execute("SELECT count(*) FROM events i JOIN events o ON i.id=o.id AND o.side='output' WHERE i.side='input' AND i.payload<>o.payload").fetchone()[0]
        stats.update({'missing_event_ids': missing if output_dir is not None else None,
                      'unexpected_event_ids': extra if output_dir is not None else None,
                      'changed_payloads': changed if output_dir is not None else None})
        manifest_path = input_path.with_suffix(input_path.suffix + '.manifest.json')
        manifest_errors = []
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if manifest['events'] != stats['input']['total'] or manifest['sha256'] != stats['input_sha256']:
                manifest_errors.append('Input count/hash differs from manifest')
            for (payload,) in db.execute("SELECT payload FROM events WHERE side='input'"):
                e = json.loads(payload)
                if not parse_time(manifest['start']) <= parse_time(e['timestamp']) < parse_time(manifest['end']):
                    manifest_errors.append('Timestamp outside requested range')
                    break
        stats['manifest_errors'] = manifest_errors
        failed = not stats['input']['total'] or session_errors or overlap or manifest_errors or any(sum(counts[s][k] for k in ['invalid', 'duplicates', 'conflicting_ids']) for s in counts)
        if output_dir is not None:
            failed = failed or not paths or missing or extra or changed
        stats['status'] = 'FAIL' if failed else ('INPUT_PASS' if output_dir is None else 'PASS')
        stats['semantics'] = 'Observed reconciliation only; not an exactly-once guarantee. Duplicates are reported as FAIL for review.'
        db.close()
    write_json(report, stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True)
    p.add_argument('--movies', default='data/processed/movies.csv')
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--output-dir')
    group.add_argument('--input-only', action='store_true')
    p.add_argument('--report', default='evidence/validation.json')
    a = p.parse_args()
    result = validate(a.input, a.movies, a.output_dir, a.report)
    raise SystemExit(1 if result['status'] == 'FAIL' else 0)
