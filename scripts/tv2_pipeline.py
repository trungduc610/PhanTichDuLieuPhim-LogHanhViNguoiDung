"""Run TV2 processing/analysis/ML only against real HDFS input."""
import argparse
import csv
import datetime
import json
import platform
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json,snapshot_namespaces,snapshot_file_diff
from tv2_common import output_roots,safe_output_uri
from src.schemas import MOVIE_SCHEMA
from src.tv2_processing import validate_movies,clean_lines,transform_logs,join_movies
from src.tv2_analytics import build_statistics,build_user_features,FEATURE_COLUMNS
from src.tv2_clustering import cluster_users
from pyspark import StorageLevel
from pyspark.sql import SparkSession,functions as F
from pyspark.sql.types import StructType,StructField,StringType


def json_safe(value):
    if isinstance(value,(datetime.datetime,datetime.date)):return value.isoformat()
    if isinstance(value,dict):return {key:json_safe(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):return [json_safe(item) for item in value]
    return value


class Exporter:
    def __init__(self,spark,fs,run_id,roots,evidence):
        self.spark,self.fs,self.run_id,self.roots,self.evidence=spark,fs,run_id,roots,evidence
        self.artifacts=[];self.small_results={}
    def dataset(self,frame,name,kind='processed',small=False,formats=('parquet',)):
        rows=frame.count();base=safe_output_uri(self.roots[kind]+'/'+name,self.run_id)
        if small and rows>5000:raise ValueError('Refuses driver/dashboard export of a large dataset: '+name)
        for fmt in formats:
            uri=base if formats==('parquet',) else base+'/'+fmt
            safe_output_uri(uri,self.run_id)
            writer_frame=frame.coalesce(1) if small else frame.repartition(8)
            if fmt=='csv':
                writer_frame=writer_frame.select(*[F.to_json(F.col(field.name)).alias(field.name)
                  if field.dataType.typeName() in ['array','map','struct'] else F.col(field.name) for field in frame.schema])
                writer_frame.write.mode('errorifexists').option('header','true').option('encoding','UTF-8').option('escape','"').csv(uri)
                back=self.spark.read.option('header','true').option('escape','"').csv(uri).count()
            elif fmt=='json':
                writer_frame.write.mode('errorifexists').json(uri);back=self.spark.read.json(uri).count()
            else:
                writer_frame.write.mode('errorifexists').parquet(uri);back=self.spark.read.parquet(uri).count()
            if back!=rows:raise ValueError('Read-back row count mismatch: '+uri)
            self.artifacts.append({'name':name,'format':fmt,'uri':uri,'rows':rows,'read_back_rows':back,
                                   'schema':frame.schema.jsonValue()})
        if small:
            values=[json_safe(row.asDict(recursive=True)) for row in frame.collect()]
            folder=self.evidence/'dashboard';folder.mkdir(exist_ok=True)
            local_name=name.replace('/','_')
            new_json(folder/(local_name+'.json'),values)
            with (folder/(local_name+'.csv')).open('x',encoding='utf-8',newline='') as output:
                writer=csv.DictWriter(output,fieldnames=frame.columns);writer.writeheader()
                for row in values:writer.writerow({key:json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else value for key,value in row.items()})
            self.small_results[name]=values
        return rows
    def document(self,name,value):
        value=json_safe(value);new_json(self.evidence/(name+'.json'),value)
        uri=safe_output_uri(self.roots['results']+'/reports/'+name,self.run_id)
        self.spark.createDataFrame([(json.dumps(value,ensure_ascii=False),)],'value string').coalesce(1).write.mode('errorifexists').text(uri)
        if self.spark.read.text(uri).count()!=1:raise ValueError('Report read-back failed')
        self.artifacts.append({'name':name,'format':'json','uri':uri,'rows':1,'read_back_rows':1})
    def manifest(self):
        jvm=self.spark._jvm
        for record in self.artifacts:
            iterator=self.fs.listFiles(jvm.org.apache.hadoop.fs.Path(record['uri']),True);files=[]
            while iterator.hasNext():
                item=iterator.next();files.append({'uri':item.getPath().toString(),'bytes':item.getLen()})
            record['files']=files
        return {'status':'PASS','run_id':self.run_id,'artifacts':self.artifacts,
                'local_dashboard_files':[str(p.relative_to(ROOT)) for p in sorted((self.evidence/'dashboard').glob('*'))],
                'dashboard_files':{p.name:{'bytes':p.stat().st_size,'sha256':sha256(p)}
                    for p in sorted((self.evidence/'dashboard').glob('*'))}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-context',required=True)
    args=parser.parse_args();context=json.loads(Path(args.run_context).read_text(encoding='utf-8'))
    evidence=ROOT/context['evidence'];source_path=ROOT/context['source_manifest']
    source=json.loads(source_path.read_text(encoding='utf-8'));snapshot_namespaces(source)
    before=json.loads((evidence/'raw-before.json').read_text(encoding='utf-8'))
    if before['status']!='PASS' or before['source_manifest_sha256']!=sha256(source_path):raise ValueError('Requires actual current raw byte verification')
    roots=output_roots(source['authority'],context['run_id'])
    summary={'status':'FAIL','run_id':context['run_id'],'started_at_utc':utcnow(),'local_fallback':False,
             'source_manifest_sha256':sha256(source_path),'movies_uri':source['movies_uri'],'logs_uri':source['logs_uri']}
    spark=None;cached=[]
    try:
        spark=(SparkSession.builder.master('local[2]').appName('TV2-Week2-Spark-Analysis-KMeans')
          .config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','8')
          .config('spark.sql.legacy.timeParserPolicy','CORRECTED').config('spark.sql.ansi.enabled','false')
          .config('spark.sql.csv.parser.columnPruning.enabled','false')
          .config('spark.hadoop.fs.defaultFS',source['authority']).config('spark.hadoop.dfs.client.use.datanode.hostname','true').getOrCreate())
        spark.sparkContext.setLogLevel('WARN');jvm=spark._jvm
        fs=jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI(source['authority']),spark.sparkContext._jsc.hadoopConfiguration())
        if fs.getClass().getName()!='org.apache.hadoop.hdfs.DistributedFileSystem':raise ValueError('Refuses non-HDFS input')
        environment={'spark':spark.version,'python':sys.version,'java':jvm.System.getProperty('java.version'),
          'hadoop_client':jvm.org.apache.hadoop.util.VersionInfo.getVersion(),'filesystem':fs.getClass().getName(),
          'actual_filesystem_uri':fs.getUri().toString(),'session_timezone':'UTC','calendar_timezone':'Asia/Ho_Chi_Minh',
          'master':spark.sparkContext.master,'os':platform.platform(),'local_fallback':False}
        new_json(evidence/'spark_environment.json',environment)
        for uri in roots.values():
            if fs.exists(jvm.org.apache.hadoop.fs.Path(uri)):raise FileExistsError('TV2 output namespace exists: '+uri)
        listed=set()
        for namespace in snapshot_namespaces(source):
            iterator=fs.listFiles(jvm.org.apache.hadoop.fs.Path(namespace),True)
            while iterator.hasNext():listed.add(iterator.next().getPath().toUri().getPath())
        if any(snapshot_file_diff(source,listed)):raise ValueError('Raw input namespace differs from verified source')
        print('TV2_READ_HDFS '+source['movies_uri']+' '+source['logs_uri'],flush=True)
        schema=StructType(list(MOVIE_SCHEMA.fields)+[StructField('_corrupt_record',StringType(),True)])
        movies=(spark.read.schema(schema).option('header','true').option('encoding','UTF-8').option('escape','"')
          .option('mode','PERMISSIVE').option('columnNameOfCorruptRecord','_corrupt_record').csv(source['movies_uri'])
          .persist(StorageLevel.MEMORY_AND_DISK));cached.append(movies)
        movie_info=validate_movies(movies)
        if movie_info['rows']!=source['expected_movies']:raise ValueError('Observed movie count differs from expected')
        log_uris=sorted(source['authority']+item['hdfs_path'] for item in source['files'] if item['kind']=='logs')
        raw=spark.read.text(log_uris)
        observed={row[0] for row in raw.select(F.input_file_name()).distinct().collect()}
        expected_nonempty={source['authority']+item['hdfs_path'] for item in source['files'] if item['kind']=='logs' and item['bytes']>0}
        if observed!=expected_nonempty:raise ValueError('Observed input files are not the actual Flume HDFS Sink parts')
        exporter=Exporter(spark,fs,context['run_id'],roots,evidence)
        print('TV2_CLEAN',flush=True)
        event_manifest=source['event_manifest']
        clean,rejected,cleaning,buffers=clean_lines(raw,movies,event_manifest['start'],event_manifest['end'],event_manifest['runId'])
        cached.extend(buffers);cached.append(clean)
        if cleaning['raw_log_count']!=source['expected_logs']:raise ValueError('Observed raw event count differs from expected')
        exporter.document('input_counts',{'movie_rows':movie_info['rows'],'raw_log_rows':cleaning['raw_log_count'],
          'parsed_log_rows':cleaning['parsed_log_count'],'log_files':len(log_uris),'observed_log_files':sorted(observed),
          'movies_uri':source['movies_uri'],'logs_uri':source['logs_uri'],'filesystem':environment['filesystem'],'local_fallback':False})
        exporter.document('cleaning_summary',cleaning)
        exporter.dataset(clean,'cleaned_logs');exporter.dataset(rejected,'rejected_logs')
        for frame in buffers:frame.unpersist()
        transformed=transform_logs(clean);transformed_count=transformed.count()
        joined=join_movies(transformed,movies).persist(StorageLevel.MEMORY_AND_DISK);cached.append(joined)
        joined_count=joined.count()
        if transformed_count!=cleaning['clean_log_count'] or joined_count!=transformed_count:raise ValueError('Transformation/join changed clean row count')
        exporter.dataset(joined,'joined_events')
        exporter.document('transformation_summary',{'rows':transformed_count,'event_timestamp_timezone':'UTC',
           'calendar_timezone':'Asia/Ho_Chi_Minh','dayOfWeek_convention':'Spark 1=Sunday,7=Saturday',
           'watchDuration_unit':'seconds, incremental watch segments','derived_columns':['eventTimestamp','eventLocalTimestamp','date','hour','dayOfWeek','watchDurationMinutes','genresArray']})
        exporter.document('join_summary',{'pre_join_clean_log_count':cleaning['pre_join_clean_log_count'],
           'clean_log_count':cleaning['clean_log_count'],'joined_count':joined_count,'orphan_count':cleaning['orphan_movie_id_count'],
           'count_identity':'pre_join_clean_log_count = joined_count + orphan_count; clean_log_count excludes quarantined orphans',
           'key':'movieId','type':'bigint','join':'inner'})
        clean.unpersist();movies.unpersist()
        print('TV2_STATISTICS',flush=True)
        statistics=build_statistics(joined,joined_count)
        for name,frame in statistics.items():exporter.dataset(frame,'stats/'+name,'results',True,('parquet','csv','json'))
        exporter.document('statistics_summary',exporter.small_results.copy())
        print('TV2_FEATURES_KMEANS',flush=True)
        features=build_user_features(joined).persist(StorageLevel.MEMORY_AND_DISK);cached.append(features)
        feature_count=features.count()
        if feature_count!=joined.select('userId').distinct().count():raise ValueError('User feature count differs from analytical users')
        exporter.dataset(features,'user_features')
        clustered=cluster_users(features,seed=context['seed'])
        cached.extend([clustered['prepared'],clustered['assignments']])
        exporter.dataset(clustered['prepared'],'kmeans/features_prepared','results')
        exporter.dataset(features,'kmeans/user_features','results',True,('parquet','csv','json'))
        search_frame=spark.createDataFrame(clustered['search']).orderBy('k')
        exporter.dataset(search_frame,'kmeans/k_search','results',True,('parquet','csv','json'))
        exporter.dataset(clustered['assignments'].orderBy('userId'),'kmeans/assignments','results',True,('parquet','csv','json'))
        exporter.dataset(clustered['profiles'],'kmeans/cluster_profiles','results',True,('parquet','csv','json'))
        model_uri=safe_output_uri(roots['results']+'/kmeans/model',context['run_id'])
        clustered['model'].write().save(model_uri)
        from pyspark.ml import PipelineModel
        restored=PipelineModel.load(model_uri).transform(features).select('userId',F.col('prediction').alias('_restored'))
        if restored.count()!=feature_count:raise ValueError('Reloaded model changed user count')
        if restored.join(clustered['assignments'].select('userId','cluster'),'userId').filter(F.col('_restored')!=F.col('cluster')).count():
            raise ValueError('Saved model does not reproduce assignments')
        exporter.artifacts.append({'name':'kmeans/model','format':'spark_ml_pipeline','uri':model_uri,
           'rows':feature_count,'read_back_rows':feature_count,'validation':'Reloaded model reproduces all assignments'})
        metadata=clustered['metadata'];metadata.update(model_uri=model_uri,user_features_uri=roots['processed']+'/user_features')
        exporter.document('kmeans_search',clustered['search']);exporter.document('selected_k',metadata)
        exporter.document('cluster_profiles',clustered['profile_rows']);exporter.document('feature_validation',clustered['validation'])
        exporter.document('model_metadata',metadata)
        flat=spark.createDataFrame([(metadata['best_k'],metadata['silhouette'],metadata['seed'],feature_count,
                                    json.dumps(metadata['feature_columns']))],
                                  'bestK int, silhouette double, seed int, users long, featureColumnsJson string')
        exporter.dataset(flat,'kmeans/model_metadata','results',True,('parquet','csv','json'))
        manifest=exporter.manifest();new_json(evidence/'output_manifest.json',manifest)
        summary.update(status='PASS',environment=environment,movies=movie_info['rows'],raw_events=cleaning['raw_log_count'],
           clean_events=cleaning['clean_log_count'],joined_events=joined_count,user_count=feature_count,best_k=metadata['best_k'],
           silhouette=metadata['silhouette'],processed_root=roots['processed'],results_root=roots['results'],
           artifacts=len(manifest['artifacts']),model_reload_assignments_match=True)
    except Exception as exc:
        summary['error']=str(exc);raise
    finally:
        for frame in cached:frame.unpersist()
        if spark is not None:spark.stop()
        summary['finished_at_utc']=utcnow();new_json(evidence/'pipeline_summary.json',json_safe(summary))
        print(json.dumps(summary,ensure_ascii=True,indent=2),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
