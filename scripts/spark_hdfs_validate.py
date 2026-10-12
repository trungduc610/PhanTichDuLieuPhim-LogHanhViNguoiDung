"""Full Spark QA reads HDFS URIs only; no local/generated fallback."""
import argparse
import json
import platform
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT))
from common import sha256,utcnow
from hdfs_common import new_json
from src.schemas import MOVIE_SCHEMA,USER_LOG_SCHEMA
from spark_smoke_test import validate_frames
from pyspark import __version__ as pyspark_version
from pyspark.sql import SparkSession,functions as F
from pyspark.sql.types import StructType,StructField,StringType

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-manifest',required=True)
    p.add_argument('--hdfs-verification',required=True)
    p.add_argument('--report',required=True)
    a=p.parse_args()
    if Path(a.report).exists():raise FileExistsError(a.report)
    source=json.loads(Path(a.source_manifest).read_text(encoding='utf-8'))
    verified=json.loads(Path(a.hdfs_verification).read_text(encoding='utf-8'))
    if source['status']!='PASS' or verified['status']!='PASS' or verified['source_manifest_sha256']!=sha256(a.source_manifest):
        raise ValueError('Requires current PASS HDFS content verification')
    for uri in [source['movies_uri'],source['logs_uri']]:
        if not uri.startswith(source['authority']+'/movie-log/raw/'):
            raise ValueError('Must read the verified HDFS namespace, never local files')
    spark=None
    result={'status':'FAIL','started_at_utc':utcnow(),'hdfs_run_id':source['hdfs_run_id'],
       'flume_run_id':source['flume_run_id'],'movies_uri':source['movies_uri'],'logs_uri':source['logs_uri'],
       'source_manifest_sha256':sha256(a.source_manifest),'verification_sha256':sha256(a.hdfs_verification),
       'source_hashes':{name:sha256(ROOT/name) for name in ['scripts/spark_hdfs_validate.py','scripts/spark_smoke_test.py','src/schemas.py','config/hdfs/core-site.xml','config/hdfs/hdfs-site.xml']}}
    try:
        spark=(SparkSession.builder.master('local[2]').appName('Week2-TV1-HDFS-FullValidation')
            .config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','8')
            .config('spark.sql.csv.parser.columnPruning.enabled','false')
            .config('spark.hadoop.fs.defaultFS',source['authority'])
            .config('spark.hadoop.dfs.client.use.datanode.hostname','true').getOrCreate())
        spark.sparkContext.setLogLevel('WARN')
        jvm=spark._jvm
        conf=spark.sparkContext._jsc.hadoopConfiguration()
        fs=jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI(source['authority']),conf)
        result['runtime']={'spark':spark.version,'pyspark':pyspark_version,'python':sys.version,
            'python_executable':sys.executable,'java':jvm.System.getProperty('java.version'),
            'hadoop_client':jvm.org.apache.hadoop.util.VersionInfo.getVersion(),'os':platform.platform(),
            'master':spark.sparkContext.master,'fs_defaultFS':conf.get('fs.defaultFS'),
            'actual_filesystem_uri':fs.getUri().toString(),'filesystem_class':fs.getClass().getName(),
            'timestamp_timezone':spark.conf.get('spark.sql.session.timeZone')}
        result['basic_action_count']=spark.range(5).count()
        if result['basic_action_count']!=5:raise ValueError('Basic Spark action failed')
        # JVM HDFS status is also checked; input list excludes no files, even empty parts.
        seen=[]
        for record in source['files']:
            path=jvm.org.apache.hadoop.fs.Path(source['authority']+record['hdfs_path'])
            status=fs.getFileStatus(path)
            if not status.isFile() or status.getLen()!=record['bytes']:
                raise ValueError('HDFS file status changed: '+record['hdfs_path'])
            seen.append({'uri':status.getPath().toString(),'bytes':status.getLen(),'replication':status.getReplication()})
        statuses=fs.listStatus(jvm.org.apache.hadoop.fs.Path(source['logs_uri']))
        expected={source['authority']+f['hdfs_path'] for f in source['files'] if f['kind']=='logs'}
        actual={s.getPath().toString() for s in statuses if s.isFile()}
        if actual!=expected:raise ValueError('HDFS log directory file list changed')
        result['hdfs_status_files']=seen
        movie_schema=StructType(list(MOVIE_SCHEMA.fields)+[StructField('_corrupt_record',StringType(),True)])
        log_schema=StructType(list(USER_LOG_SCHEMA.fields)+[StructField('_corrupt_record',StringType(),True)])
        movies=(spark.read.option('header','true').option('encoding','UTF-8').option('escape','"')
            .option('mode','PERMISSIVE').option('columnNameOfCorruptRecord','_corrupt_record')
            .schema(movie_schema).csv(source['movies_uri']))
        logs=(spark.read.option('encoding','UTF-8').option('mode','PERMISSIVE')
            .option('columnNameOfCorruptRecord','_corrupt_record').schema(log_schema).json(sorted(expected)))
        result['schemas']={'movie_contract':MOVIE_SCHEMA.jsonValue(),'log_contract':USER_LOG_SCHEMA.jsonValue(),
            'movies_read':movies.schema.jsonValue(),'logs_read':logs.schema.jsonValue(),
            'eventTime_type':logs.withColumn('eventTime',F.to_timestamp('timestamp')).schema['eventTime'].dataType.simpleString()}
        result['observed_movies_files']=[r[0] for r in movies.select(F.input_file_name()).distinct().collect()]
        result['observed_log_files']=[r[0] for r in logs.select(F.input_file_name()).distinct().collect()]
        expected_nonempty={source['authority']+f['hdfs_path'] for f in source['files'] if f['kind']=='logs' and f['bytes']>0}
        if set(result['observed_movies_files'])!={source['movies_uri']} or set(result['observed_log_files'])!=expected_nonempty:
            raise ValueError('Actual input_file_name differs from HDFS source manifest')
        manifest=source['event_manifest']
        result.update(validate_frames(spark,movies,logs,source['expected_movies'],source['expected_logs'],manifest['start'],manifest['end']))
        result['local_fallback']=False
    except Exception as exc:
        result.update(status='FAIL',error=str(exc))
    finally:
        if spark is not None:spark.stop()
        result['finished_at_utc']=utcnow()
        new_json(a.report,result)
    print(json.dumps({key:value for key,value in result.items() if key!='schemas'},ensure_ascii=True,indent=2,default=str))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
