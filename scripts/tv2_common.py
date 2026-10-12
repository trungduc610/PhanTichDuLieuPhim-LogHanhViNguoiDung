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
