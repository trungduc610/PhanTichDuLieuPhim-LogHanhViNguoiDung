"""Freeze verified Week 1 Sink provenance for a NEW HDFS import."""
import json
from pathlib import Path
from common import sha256,utcnow
from movie_quality import inspect_movies
from hdfs_common import ROOT,new_json

FLUME_RUN='run-aa6b9eb58dca'

def source_manifest(run_id,evidence):
    old=ROOT/'evidence'/FLUME_RUN
    status=json.loads((old/'status.json').read_text(encoding='utf-8'))
    rec=json.loads((old/'reconciliation.json').read_text(encoding='utf-8'))
    spark=json.loads((ROOT/'evidence/recheck-20261011-221710/spark-main.json').read_text(encoding='utf-8'))
    if not (status['run_id']==FLUME_RUN and status['status']==rec['status']==spark['status']=='PASS' and spark['run_id']==FLUME_RUN):
        raise ValueError('Week 1 lineage is not the expected PASS run')
    for name,h in status['source_config_hashes'].items():
        if sha256(ROOT/name)!=h:raise ValueError('Flume source/config changed: '+name)
    generated=ROOT/'data/generated/main.jsonl'
    generated_manifest=json.loads(generated.with_suffix('.jsonl.manifest.json').read_text(encoding='utf-8'))
    if sha256(generated)!=status['input_sha256'] or rec['input_sha256']!=status['input_sha256'] or generated_manifest['sha256']!=status['input_sha256']:
        raise ValueError('Flume input provenance changed')
    for side in ['input','output']:
        if rec[side]['total']!=1000000 or rec[side]['unique']!=1000000 or any(rec[side][k] for k in ['invalid','duplicates','conflicting_ids']):
            raise ValueError('Unexpected Week 1 count/quality')
    if any(rec[k] for k in ['missing_event_ids','unexpected_event_ids','changed_payloads','session_errors','user_overlap_errors']):
        raise ValueError('Week 1 reconciliation has errors')
    movies=ROOT/'data/processed/movies.csv'
    _,qa=inspect_movies(movies)
    if qa['status']!='PASS' or qa['rows']!=9742 or sha256(movies)!=rec['movies_sha256']:
        raise ValueError('Movie snapshot changed')
    sink=ROOT/'data/runs'/FLUME_RUN/'output'
    expected={Path(f['path']).name:f for f in rec['output_files']}
    actual={p.name:p for p in sink.iterdir() if p.is_file()}
    if set(actual)!=set(expected):raise ValueError('Sink file list differs from reconciliation')
    if len(actual)!=15 or sum(p.stat().st_size for p in actual.values())!=343339148:
        raise ValueError('Sink declared scale changed')
    snapshot='mls-'+rec['movies_sha256'][:12]+'-'+run_id
    movies_dir='/movie-log/raw/movies/'+snapshot
    logs_dir='/movie-log/raw/user_logs/'+FLUME_RUN+'/'+run_id
    files=[{'kind':'movies','local_path':movies.relative_to(ROOT).as_posix(),'bytes':movies.stat().st_size,
            'sha256':sha256(movies),'expected_records':9742,'hdfs_path':movies_dir+'/movies.csv'}]
    for name,path in sorted(actual.items()):
        proof=expected[name]
        if path.stat().st_size!=proof['bytes'] or sha256(path)!=proof['sha256']:
            raise ValueError('Sink bytes/hash changed: '+name)
        records=0
        with path.open('rb') as f:
            for row in f:
                if not row.endswith(b'\n'):raise ValueError('Truncated Sink part: '+name)
                event=json.loads(row.decode('utf-8',errors='strict'))
                if not isinstance(event,dict) or len(event)!=12:raise ValueError('Invalid event structure')
                records+=1
        files.append({'kind':'logs','local_path':path.relative_to(ROOT).as_posix(),'bytes':proof['bytes'],
            'sha256':proof['sha256'],'expected_records':records,'empty':proof['empty'],'hdfs_path':logs_dir+'/'+name})
    if sum(f['expected_records'] for f in files if f['kind']=='logs')!=1000000:
        raise ValueError('Full JSON parsing count differs from verified run')
    result={'status':'PASS','created_at_utc':utcnow(),'hdfs_run_id':run_id,'flume_run_id':FLUME_RUN,
        'flume_input_sha256':status['input_sha256'],'flume_reconciliation_sha256':sha256(old/'reconciliation.json'),
        'movies_qa':qa,'expected_movies':9742,'expected_logs':1000000,'expected_log_bytes':343339148,
        'event_manifest':generated_manifest,'flume_stats':rec['output'],'authority':'hdfs://namenode:9000',
        'movies_uri':'hdfs://namenode:9000'+movies_dir+'/movies.csv','logs_uri':'hdfs://namenode:9000'+logs_dir,
        'directories':['/movie-log/raw/movies','/movie-log/raw/user_logs','/movie-log/processed','/movie-log/results',movies_dir,logs_dir],
        'files':files,'note':'Generated file is checked only for lineage; upload uses movies.csv and actual Sink parts exclusively.'}
    new_json(Path(evidence)/'source_manifest.json',result)
    return result
