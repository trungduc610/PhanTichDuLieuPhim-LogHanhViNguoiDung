"""Stream complete, coherent sessions. Synthetic data, not real behavior."""
import argparse
import bisect
import csv
import hashlib
import itertools
import json
import random
import uuid
from collections import Counter
from datetime import timedelta, timezone
from pathlib import Path
from common import parse_time, sha256, write_json

LOCAL = timezone(timedelta(hours=7))


def cdf(weights):
    return list(itertools.accumulate(weights))


def pick(rng, cumulative):
    return bisect.bisect_right(cumulative, rng.random() * cumulative[-1])


def generate(movies, output, events=1000000, users=1000, start='2026-09-01T00:00:00+07:00',
             end='2026-10-01T00:00:00+07:00', seed=42, run_id=None):
    output = Path(output)
    start_dt, end_dt = parse_time(start), parse_time(end)
    if events < 1 or users < 1 or end_dt - start_dt < timedelta(hours=6):
        raise ValueError('events/users must be positive and time range must be at least 6 hours')
    if output.exists() or output.with_suffix(output.suffix + '.manifest.json').exists():
        raise FileExistsError(output)
    with open(movies, encoding='utf-8', newline='') as f:
        ids = [int(r['movieId']) for r in csv.DictReader(f)]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Movie IDs must be nonempty and unique')
    identity = {'movies_sha256': sha256(movies), 'events': events, 'users': users,
                'start': start_dt.isoformat(), 'end': end_dt.isoformat(), 'seed': seed,
                'generator_version': 1}
    run_id = run_id or hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'movie-log-bigdata:' + run_id)
    rng = random.Random(seed)
    rng.shuffle(ids)  # Popularity is synthetic, independent of ID/year and original ratings.
    movie_cdf = cdf([1 / (rank + 1) ** 0.85 for rank in range(len(ids))])
    user_order = list(range(1, users + 1))
    rng.shuffle(user_order)
    user_cdf = cdf([1 / (rank + 1) ** 0.65 for rank in range(users)])
    runtime = {mid: 3600 + (int(hashlib.sha256(f'{seed}:{mid}'.encode()).hexdigest()[:8], 16) % 121) * 60 for mid in ids}
    latest_start = end_dt - timedelta(hours=4)
    hours, weights = [], []
    cursor = start_dt.replace(minute=0, second=0, microsecond=0)
    while cursor <= latest_start:
        lo, hi = max(cursor, start_dt), min(cursor + timedelta(hours=1), latest_start)
        seconds = int((hi - lo).total_seconds())
        if seconds > 0:
            hour = cursor.astimezone(LOCAL).hour
            hours.append((lo, seconds))
            weights.append(seconds * (5 if 19 <= hour <= 23 else 0.5 if hour < 6 else 1.5))
        cursor += timedelta(hours=1)
    hour_cdf = cdf(weights)
    # Store occupied intervals per user; reject overlaps instead of inventing concurrent viewing.
    busy = {u: [] for u in user_order}
    counters, hour_counts, user_counts, movie_counts = Counter(), Counter(), Counter(), Counter()
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + '.part')
    written = sessions = 0
    with partial.open('x', encoding='utf-8', newline='\n') as f:
        while written < events:
            left = events - written
            mid = ids[pick(rng, movie_cdf)]
            duration = runtime[mid]
            if left < 3 or rng.random() < 0.15:
                actions = [('view', 0, 0)]
            else:
                complete = rng.random() < 0.55
                watched = duration if complete else rng.randint(30, duration - 1)
                delay = rng.randint(2, 15)
                terminal = 'complete' if complete else 'stop'
                if left >= 5 and rng.random() < 0.35:
                    first = rng.randint(1, watched - 1)
                    pause = rng.randint(10, 300)
                    actions = [('view', 0, 0), ('play', delay, 0), ('pause', delay + first, first),
                               ('play', delay + first + pause, 0), (terminal, delay + watched + pause, watched - first)]
                else:
                    actions = [('view', 0, 0), ('play', delay, 0), (terminal, delay + watched, watched)]
            span = actions[-1][1] + 1
            for attempt in range(5000):
                uid = user_order[pick(rng, user_cdf)]
                lo, seconds = hours[pick(rng, hour_cdf)]
                when = lo + timedelta(seconds=rng.randrange(seconds))
                until = when + timedelta(seconds=span)
                slots = busy[uid]
                pos = bisect.bisect_left(slots, (when, when))
                if (pos == 0 or slots[pos - 1][1] <= when) and (pos == len(slots) or until <= slots[pos][0]):
                    slots.insert(pos, (when, until))
                    break
            else:
                raise ValueError('Time range/user population too crowded; increase --users or time range. Partial file not published.')
            sessions += 1
            sid = str(uuid.uuid5(namespace, f'session:{sessions}'))
            user_counts[str(uid)] += 1
            movie_counts[str(mid)] += 1
            hour_counts[str(when.astimezone(LOCAL).hour)] += 1
            for seq, (action, offset, delta) in enumerate(actions):
                event = {'eventId': str(uuid.uuid5(namespace, f'{sessions}:{seq}')), 'userId': f'sim-user-{uid:06d}',
                         'sessionId': sid, 'movieId': mid, 'action': action,
                         'timestamp': (when + timedelta(seconds=offset)).isoformat().replace('+00:00', 'Z'),
                         'watchDuration': delta, 'sequenceNumber': seq, 'runId': run_id,
                         'isSynthetic': True, 'simulatedMovieDuration': duration, 'durationSource': 'synthetic'}
                f.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
                written += 1
                counters[action] += 1
    partial.rename(output)
    result = {**identity, 'runId': run_id, 'output': str(output), 'sha256': sha256(output),
              'bytes': output.stat().st_size, 'sessions': sessions, 'actions': dict(counters),
              'session_start_hour_Asia_Saigon': dict(sorted(hour_counts.items(), key=lambda x: int(x[0]))),
              'active_users': len(user_counts), 'unique_movies': len(movie_counts),
              'top_users_sessions': user_counts.most_common(10), 'top_movies_sessions': movie_counts.most_common(10),
              'status': 'GENERATED_NOT_FLUME_OUTPUT'}
    write_json(output.with_suffix(output.suffix + '.manifest.json'), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--movies', default='data/processed/movies.csv')
    p.add_argument('--mode', choices=['demo', 'main'], default='main')
    p.add_argument('--events', type=int)
    p.add_argument('--users', type=int, default=1000)
    p.add_argument('--start', default='2026-09-01T00:00:00+07:00')
    p.add_argument('--end', default='2026-10-01T00:00:00+07:00')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--run-id', help='Use a new value for an independent run; same parameters default to reproducible IDs')
    p.add_argument('--output')
    a = p.parse_args()
    generate(a.movies, a.output or f'data/generated/{a.mode}.jsonl',
             a.events if a.events is not None else (10000 if a.mode == 'demo' else 1000000),
             a.users, a.start, a.end, a.seed, a.run_id)
