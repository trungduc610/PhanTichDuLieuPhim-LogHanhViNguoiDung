"""Validate every field of actual Flume Sink output with reusable Spark schemas."""
import argparse
import json
import platform
import sys
from functools import reduce
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.schemas import MOVIE_SCHEMA, USER_LOG_SCHEMA
from pyspark import __version__ as pyspark_version
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import StructField, StringType, LongType


def validate_frames(spark, movies, logs, expected_movies, expected_logs, start, end):
    """Actions touch every field. Fixture calls do not claim Flume provenance."""
    movies = movies.withColumn('_file', F.input_file_name()).cache()
    logs = logs.withColumn('_file', F.input_file_name()).withColumn('eventTime', F.to_timestamp('timestamp')).cache()
    errors, examples = {}, {}
    def check(name, frame, condition):
        bad = frame.filter(condition)
        errors[name] = bad.count()
        if errors[name]:
            examples[name] = [r.asDict(recursive=True) for r in bad.limit(10).collect()]
    movie_counts = movies.agg(F.count('*').alias('rows'), F.countDistinct('movieId').alias('unique_ids'), F.sum(F.col('releaseYear').isNull().cast('long')).alias('releaseYear_null_allowed')).first().asDict()
    required_movies = [f.name for f in MOVIE_SCHEMA if not f.nullable]
    check('movie_required_null', movies, reduce(lambda a,b:a|b, [F.col(k).isNull() for k in required_movies]))
    check('movie_empty_title_or_genres', movies, (F.trim('title')=='') | (F.trim('genres')==''))
    check('movie_invalid_id_or_year', movies, (F.col('movieId')<=0) | (F.col('releaseYear').isNotNull() & ~F.col('releaseYear').between(1870,2100)))
    if '_corrupt_record' in movies.columns:
        check('movie_malformed_csv', movies, F.col('_corrupt_record').isNotNull())
    duplicates = movies.groupBy('movieId').count().filter(F.col('count')>1)
    errors['movie_duplicate_ids'] = duplicates.count()
    if errors['movie_duplicate_ids']:
        examples['movie_duplicate_ids'] = [r.asDict() for r in duplicates.limit(10).collect()]
    required_logs = [f.name for f in USER_LOG_SCHEMA if not f.nullable]
    check('log_required_null', logs, reduce(lambda a,b:a|b,[F.col(k).isNull() for k in required_logs]))
    check('log_empty_identity', logs, reduce(lambda a,b:a|b,[F.trim(k)=='' for k in ['eventId','sessionId','userId','runId']]))
    if '_corrupt_record' in logs.columns:
        check('log_malformed_json', logs, F.col('_corrupt_record').isNotNull())
    check('log_timestamp_parse', logs, F.col('eventTime').isNull() | ~F.col('timestamp').rlike(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'))
    check('log_timestamp_range', logs, (F.col('eventTime')<F.to_timestamp(F.lit(start))) | (F.col('eventTime')>=F.to_timestamp(F.lit(end))))
    check('log_action', logs, ~F.col('action').isin('view','play','pause','stop','complete'))
    check('log_duration', logs, (F.col('watchDuration')<0) | (F.col('watchDuration')>F.col('simulatedMovieDuration')) | (F.col('action').isin('view','play') & (F.col('watchDuration')!=0)) | (F.col('action').isin('pause','stop','complete') & (F.col('watchDuration')<=0)))
    check('log_integer_ranges', logs, (F.col('movieId')<=0) | (F.col('sequenceNumber')<0) | ~F.col('simulatedMovieDuration').between(3600,10800))
    check('log_provenance', logs, (F.col('isSynthetic')!=True) | (F.col('durationSource')!='synthetic'))
    payload = F.to_json(F.struct(*[F.col(f.name) for f in USER_LOG_SCHEMA]))
    duplicate_ids = logs.groupBy('eventId').agg(F.count('*').alias('rows'), F.countDistinct(payload).alias('payloads')).filter(F.col('rows')>1)
    errors['log_duplicate_ids'] = duplicate_ids.count()
    errors['log_conflicting_ids'] = duplicate_ids.filter(F.col('payloads')>1).count()
    if errors['log_duplicate_ids']:
        examples['log_duplicate_ids'] = [r.asDict() for r in duplicate_ids.limit(10).collect()]
    orphan = logs.join(movies.select('movieId').distinct(), 'movieId', 'left_anti')
    errors['orphan_movie_events'] = orphan.count()
    if errors['orphan_movie_events']:
        examples['orphan_movie_events'] = [r.asDict() for r in orphan.limit(10).collect()]
    errors['movie_count_mismatch'] = int(movie_counts['rows']!=expected_movies)
    log_counts = logs.agg(F.count('*').alias('rows'), F.countDistinct('eventId').alias('unique_event_ids'), F.countDistinct('userId').alias('users'), F.countDistinct('movieId').alias('movies'), F.countDistinct('sessionId').alias('sessions'), F.min('timestamp').alias('timestamp_min'), F.max('timestamp').alias('timestamp_max'), F.sum('watchDuration').alias('watch_seconds'), F.sum(F.length(payload)).alias('materialized_payload_characters')).first().asDict()
    errors['log_count_mismatch'] = int(log_counts['rows']!=expected_logs)
    errors['join_key_type_mismatch'] = int(not isinstance(movies.schema['movieId'].dataType,LongType) or not isinstance(logs.schema['movieId'].dataType,LongType))
    actions = {r['action']:r['count'] for r in logs.groupBy('action').count().collect()}
    win = Window.partitionBy('runId','sessionId').orderBy('sequenceNumber')
    ordered = logs.withColumn('_seq',F.row_number().over(win)-1).withColumn('_previousTime',F.lag('eventTime').over(win)).withColumn('_previousAction',F.lag('action').over(win))
    check('session_sequence_or_time',ordered,(F.col('sequenceNumber')!=F.col('_seq')) | (F.col('_previousTime').isNotNull() & (F.col('eventTime')<=F.col('_previousTime'))))
    check('session_segment_duration',ordered,F.col('action').isin('pause','stop','complete') & ((F.col('_previousAction')!='play') | (F.col('watchDuration') != (F.col('eventTime').cast('long')-F.col('_previousTime').cast('long')))))
    sessions = logs.groupBy('runId','sessionId').agg(F.countDistinct('userId').alias('users'),F.countDistinct('movieId').alias('movies'),F.countDistinct('simulatedMovieDuration').alias('runtimes'))
    errors['session_identity'] = sessions.filter((F.col('users')!=1)|(F.col('movies')!=1)|(F.col('runtimes')!=1)).count()
    movies.unpersist()
    logs.unpersist()
    return {'status':'PASS' if not any(errors.values()) else 'FAIL','expected_movies':expected_movies,'expected_logs':expected_logs,'movies':movie_counts,'logs':log_counts,'actions':actions,'errors':errors,'examples':examples,'timestamp_timezone':'UTC'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--movies-path',default='data/processed/movies.csv')
    p.add_argument('--movie-report',required=True,help='Measured prepare_movies QA JSON')
    p.add_argument('--run-evidence',required=True,help='Evidence directory of actual PASS Flume run')
    p.add_argument('--report',required=True,help='NEW JSON report path')
    args=p.parse_args()
    report_path=Path(args.report)
    if report_path.exists():
        raise FileExistsError(report_path)
    evidence=Path(args.run_evidence)
    status=json.loads((evidence/'status.json').read_text(encoding='utf-8'))
    rec=json.loads((evidence/'reconciliation.json').read_text(encoding='utf-8'))
    movie_qa=json.loads(Path(args.movie_report).read_text(encoding='utf-8'))
    if status['status']!='PASS' or rec['status']!='PASS' or movie_qa['status']!='PASS':
        raise ValueError('Requires verified movies and actual PASS Flume run')
    sys.path.insert(0,str(ROOT/'scripts'))
    from common import sha256,utcnow
    if sha256(args.movies_path)!=rec['movies_sha256'] or movie_qa['output_sha256']!=rec['movies_sha256']:
        raise ValueError('Movie snapshot differs from reconciliation')
    sink=ROOT/'data'/'runs'/status['run_id']/'output'
    actual=[]
    for file in rec['output_files']:
        filename=file['path'].replace('\\','/').rsplit('/',1)[-1]
        path=sink/filename
        if path.stat().st_size!=file['bytes'] or sha256(path)!=file['sha256']:
            raise ValueError('Sink file changed: '+str(path))
        actual.append(path)
    if {p.name for p in sink.iterdir() if p.is_file() and not p.name.startswith('.')}!={p.name for p in actual}:
        raise ValueError('Sink directory contains unreported files')
    manifest_path=ROOT/'data'/'generated'/(status['input'].replace('\\','/').rsplit('/',1)[-1]+'.manifest.json')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['sha256']!=rec['input_sha256'] or manifest['events']!=rec['input']['total']:
        raise ValueError('Input manifest differs from reconciliation')
    spark=None
    result={'status':'FAIL','started_at_utc':utcnow(),'run_id':status['run_id'],'sink_files':len(actual),'sink_bytes':sum(x.stat().st_size for x in actual),'source_hashes':{'schema':sha256(ROOT/'src/schemas.py'),'smoke':sha256(__file__)}}
    try:
        spark=(SparkSession.builder.appName('MovieLog-Week1-FullValidation').master('local[2]').config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','8').config('spark.sql.csv.parser.columnPruning.enabled','false').getOrCreate())
        spark.sparkContext.setLogLevel('WARN')
        result['runtime']={'spark':spark.version,'pyspark':pyspark_version,'python':sys.version,'python_executable':sys.executable,'java':spark._jvm.System.getProperty('java.version'),'os':platform.platform(),'host_or_container':'Docker Spark container','master':spark.sparkContext.master}
        result['basic_action_count']=spark.range(5).count()
        if result['basic_action_count']!=5:
            raise ValueError('Spark basic action failed')
        # Copy the reusable schemas; do not mutate module globals with StructType.add.
        from pyspark.sql.types import StructType
        movie_schema=StructType(list(MOVIE_SCHEMA.fields)+[StructField('_corrupt_record',StringType(),True)])
        log_schema=StructType(list(USER_LOG_SCHEMA.fields)+[StructField('_corrupt_record',StringType(),True)])
        movies=spark.read.option('header','true').option('encoding','UTF-8').option('escape','"').option('mode','PERMISSIVE').option('columnNameOfCorruptRecord','_corrupt_record').schema(movie_schema).csv(args.movies_path)
        logs=spark.read.option('encoding','UTF-8').option('mode','PERMISSIVE').option('columnNameOfCorruptRecord','_corrupt_record').schema(log_schema).json([str(p) for p in actual if p.stat().st_size])
        result.update(validate_frames(spark,movies,logs,movie_qa['output_rows'],rec['output']['total'],manifest['start'],manifest['end']))
    except Exception as exc:
        result.update(status='FAIL',error=str(exc))
        raise
    finally:
        if spark is not None:
            spark.stop()
        result['finished_at_utc']=utcnow()
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True,indent=2,default=str))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
