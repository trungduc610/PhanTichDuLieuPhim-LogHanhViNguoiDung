"""Host-safe TV2 namespace and model-selection checks; no Spark dependency."""
import math
import re
from pathlib import PurePosixPath
from urllib.parse import urlsplit


def output_roots(authority,run_id):
    if authority!='hdfs://namenode:9000' or not re.fullmatch(r'tv2-[a-f0-9]{12}',run_id):
        raise ValueError('Requires HDFS authority and a new TV2 run ID')
    return {kind:authority+'/movie-log/'+kind+'/tv2/'+run_id for kind in ['processed','results']}


def safe_output_uri(uri,run_id):
    roots=output_roots('hdfs://namenode:9000',run_id)
    parsed=urlsplit(uri)
    if parsed.scheme!='hdfs' or parsed.netloc!='namenode:9000' or parsed.query or parsed.fragment:
        raise ValueError('Output must be a real HDFS URI')
    if '..' in PurePosixPath(parsed.path).parts or str(PurePosixPath(parsed.path))!=parsed.path:
        raise ValueError('Unsafe output path')
    if not any(uri==root or uri.startswith(root+'/') for root in roots.values()):
        raise ValueError('Output must belong to this TV2 namespace, never raw')
    return uri


def select_best_k(records):
    if len(records)!=5 or {row['k'] for row in records}!={2,3,4,5,6}:
        raise ValueError('Requires all five measured K candidates')
    for row in records:
        score=row['silhouette']
        if not math.isfinite(score) or not -1<=score<=1:
            raise ValueError('Invalid measured silhouette')
        sizes=row['cluster_sizes']
        if len(sizes)!=row['k'] or any(size<=0 for size in sizes) or sum(sizes)!=row['users']:
            raise ValueError('Invalid cluster size consistency')
    return max(records,key=lambda row:(row['silhouette'],-row['k']))


EVIDENCE_ROOTS = ('evidence/week2-tv2', 'evidence/week3-tv2')


def evidence_folder(root, run_id, evidence_root=EVIDENCE_ROOTS[0]):
    output_roots('hdfs://namenode:9000', run_id)
    if evidence_root not in EVIDENCE_ROOTS:
        raise ValueError('Evidence must use the explicit Week 2 or Week 3 TV2 scope')
    return root / evidence_root / run_id


def validate_week3_baseline(context, source):
    expected = ('run-f63c810e9d8d', 'hdfs-124cbf30bda7', 'movie-hdfs-124cbf30bda7')
    if (context.get('flume_run_id'), context.get('run_id'), context.get('project')) != expected:
        raise ValueError('Week 3 requires the user-selected TV1 baseline; other releases refused')
    if (source.get('flume_run_id'), source.get('hdfs_run_id')) != expected[:2]:
        raise ValueError('Week 3 source/context baseline mismatch')
    movies = 'hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-124cbf30bda7/movies.csv'
    logs = 'hdfs://namenode:9000/movie-log/raw/user_logs/run-f63c810e9d8d/hdfs-124cbf30bda7'
    if source.get('movies_uri') != movies or source.get('logs_uri') != logs:
        raise ValueError('Week 3 requires the exact baseline HDFS input URIs')
    files = source['files']
    if (source['expected_movies'], source['expected_logs'], len(files),
        sum(row['kind'] == 'logs' for row in files), sum(row['bytes'] for row in files)) != (9742, 1000000, 255, 254, 343872495):
        raise ValueError('Week 3 baseline manifest counts/bytes disagree; these are input expectations, not output results')


def valid_hourly_ranks(rows, limit=3):
    # Only hours observed in data need rows; an hour may have fewer than 3 movies.
    groups = {}
    for row in rows:
        hour, rank = row['hour'], row['rank']
        if type(hour) is not int or not 0 <= hour < 24 or type(rank) is not int:
            return False
        if type(row['playCount']) is not int or row['playCount'] <= 0:
            return False
        groups.setdefault(hour, []).append(row)
    for group in groups.values():
        ranked = sorted(group, key=lambda row: row['rank'])
        if not 1 <= len(ranked) <= limit or [row['rank'] for row in ranked] != list(range(1, len(ranked) + 1)):
            return False
        if len({row['movieId'] for row in ranked}) != len(ranked):
            return False
        if ranked != sorted(ranked, key=lambda row: (-row['playCount'], row['movieId'])):
            return False
    return True
