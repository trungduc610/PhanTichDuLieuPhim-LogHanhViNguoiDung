"""Independent HDFS read-back and SQL recomputation for TV2 Week 3.

Never writes HDFS; only creates the requested new local evidence report.
Does not call the production aggregation or feature-building functions.
"""
import argparse
import functools
import json
import math
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json
from tv2_common import safe_output_uri,validate_week3_baseline
from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession,functions as F
from pyspark.sql.types import StructType,StructField,StringType,ArrayType,DoubleType


def compare_frames(expected,actual,keys):
    """Compare all keyed values with floating tolerance; detect duplicate keys."""
    if set(expected.columns)!=set(actual.columns):
        return {'pass':False,'error':'Column set differs','expected':expected.columns,'actual':actual.columns}
    columns=expected.columns
    e_count=expected.count();a_count=actual.count()
    e_duplicates=expected.groupBy(*keys).count().filter('count > 1').count()
    a_duplicates=actual.groupBy(*keys).count().filter('count > 1').count()
    e=expected.withColumn('_expected_present',F.lit(True)).alias('e')
    a=actual.withColumn('_actual_present',F.lit(True)).alias('a')
    same=[]
    for field in expected.schema:
        left=F.col('e.`'+field.name+'`');right=F.col('a.`'+field.name+'`')
        equal=left.eqNullSafe(right)
        if field.dataType.typeName() in ['double','float','decimal']:
            close=(left.isNotNull() & right.isNotNull() & ~F.isnan(left.cast('double')) & ~F.isnan(right.cast('double')) &
                (F.abs(left-right)<=F.lit(1e-8)+F.lit(1e-10)*F.greatest(F.abs(left),F.abs(right))))
            equal=equal|F.coalesce(close,F.lit(False))
        same.append(equal)
    condition=functools.reduce(lambda x,y:x&y,same)
    mismatches=e.join(a,keys,'full_outer').filter(F.col('_expected_present').isNull()|F.col('_actual_present').isNull()|~condition).count()
    return {'pass':e_count==a_count and e_duplicates==a_duplicates==mismatches==0,
            'expected_rows':e_count,'actual_rows':a_count,'expected_duplicate_keys':e_duplicates,
            'actual_duplicate_keys':a_duplicates,'mismatched_rows':mismatches}


def shape(schema):
    # File readers widen nullability; compare names/order/logical types.
    return [(field.name,field.dataType.simpleString()) for field in schema]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-context',required=True);parser.add_argument('--report',required=True)
    args=parser.parse_args()
    if Path(args.report).exists():raise FileExistsError(args.report)
    context=json.loads(Path(args.run_context).read_text(encoding='utf-8'))
    folder=ROOT/context['evidence'];source=json.loads((ROOT/context['source_manifest']).read_text(encoding='utf-8'))
    tv1=json.loads((ROOT/context['hdfs_context'].replace(chr(92),'/')).read_text(encoding='utf-8'));validate_week3_baseline(tv1,source)
    load=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
    manifest=load('output_manifest.json');pipeline=load('pipeline_summary.json');metadata=load('model_metadata.json')
    report={'status':'FAIL','run_id':context['run_id'],'started_at_utc':utcnow(),'checks':{},'analyses':{},'outputs':[],
            'source_sha256':sha256(__file__),'method':'Independent SQL on HDFS joined Parquet, keyed full-value comparisons, format read-back and model reload'}
    spark=None;cached=[]
    try:
        spark=(SparkSession.builder.master('local[2]').appName('TV2-Week3-Independent-Verification')
               .config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','8')
               .config('spark.hadoop.fs.defaultFS',source['authority'])
               .config('spark.hadoop.dfs.client.use.datanode.hostname','true').getOrCreate())
        spark.sparkContext.setLogLevel('WARN');jvm=spark._jvm
        fs=jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI(source['authority']),spark.sparkContext._jsc.hadoopConfiguration())
        report['filesystem']=fs.getClass().getName();report['local_fallback']=False
        if report['filesystem']!='org.apache.hadoop.hdfs.DistributedFileSystem':raise ValueError('Not real HDFS')
        roots=context['output_roots'];p=roots['processed'];r=roots['results']
        joined=spark.read.parquet(p+'/joined_events').persist(StorageLevel.DISK_ONLY);cached.append(joined)
        clean=spark.read.parquet(p+'/cleaned_logs');features=spark.read.parquet(p+'/user_features').persist(StorageLevel.MEMORY_AND_DISK);cached.append(features)
        n=joined.count();report['joined_events']=n
        if joined.schema['movieId'].dataType.simpleString()!='bigint' or clean.schema['movieId'].dataType.simpleString()!='bigint':raise ValueError('Join key is not bigint')
        cleaning=load('cleaning_summary.json');join=load('join_summary.json')
        report['checks']['cleaning_and_join_identity']=(cleaning['pre_join_clean_log_count']==n+cleaning['orphan_movie_id_count'] and cleaning['clean_log_count']==n==clean.count() and cleaning['raw_log_count']==n+cleaning['rejected_record_count'] and sum(row['removed'] for row in cleaning['steps'])==cleaning['rejected_record_count'])
        report['clean_join_payload']=compare_frames(clean.select(*clean.columns),joined.select(*clean.columns),['eventId'])
        report['checks']['clean_join_payload_preserved']=report['clean_join_payload']['pass']
        timestamp=F.to_timestamp('timestamp');local=F.from_utc_timestamp(timestamp,'Asia/Ho_Chi_Minh')
        genres=F.array_distinct(F.filter(F.transform(F.split('genres','[|]'),lambda x:F.trim(x)),lambda x:F.length(x)>0))
        conditions=[F.col('eventTimestamp').eqNullSafe(timestamp),F.col('eventLocalTimestamp').eqNullSafe(local),
                    F.col('date').eqNullSafe(F.to_date(local)),F.col('hour').eqNullSafe(F.hour(local)),
                    F.col('dayOfWeek').eqNullSafe(F.dayofweek(local)),
                    (F.abs(F.col('watchDurationMinutes')-F.col('watchDuration')/60.0)<1e-10),F.col('genresArray').eqNullSafe(genres)]
        report['transformation_bad_rows']=joined.filter(~functools.reduce(lambda a,b:a&b,conditions)).count()
        report['checks']['transformation_values']=report['transformation_bad_rows']==0
        joined.withColumn('_calendarDate',F.to_date(local)).withColumn('_calendarHour',F.hour(local)).createOrReplaceTempView('v_joined')
        # SQL is intentionally independent of src.tv2_analytics.
        queries={
          'top_movies_by_play':("SELECT movieId,title,COUNT(*) playCount FROM v_joined WHERE action='play' GROUP BY movieId,title ORDER BY playCount DESC,movieId ASC LIMIT 20",['movieId']),
          'top_genres':("SELECT genre,COUNT(*) playCount FROM (SELECT explode(genresArray) genre FROM v_joined WHERE action='play') g GROUP BY genre",['genre']),
          'daily_active_users':("SELECT _calendarDate date,COUNT(DISTINCT userId) activeUsers FROM v_joined GROUP BY _calendarDate",['date']),
          'hourly_activity':("SELECT _calendarHour hour,COUNT(*) eventCount,COUNT(DISTINCT userId) distinctUsers,SUM(CASE WHEN action='play' THEN 1 ELSE 0 END) playCount FROM v_joined GROUP BY _calendarHour",['hour']),
          'action_distribution':(f"SELECT action,COUNT(*) count,COUNT(*)*100.0/{n} percentage FROM v_joined GROUP BY action",['action']),
          'user_movie_time':("SELECT hour,movieId,title,playCount,distinctUsers,rank FROM (SELECT *,row_number() OVER(PARTITION BY hour ORDER BY playCount DESC,movieId ASC) rank FROM (SELECT _calendarHour hour,movieId,title,COUNT(*) playCount,COUNT(DISTINCT userId) distinctUsers FROM v_joined WHERE action='play' GROUP BY _calendarHour,movieId,title) counts) ranked WHERE rank<=3",['hour','movieId'])}
        for name,(query,keys) in queries.items():
            expected=spark.sql(query);actual=spark.read.parquet(r+'/stats/'+name+'/parquet')
            report['analyses'][name]=compare_frames(expected,actual,keys)
            print('VERIFY_ANALYSIS '+name+' '+str(report['analyses'][name]['pass']),flush=True)
        def duration(where,label):
            return spark.sql("SELECT COUNT(*) count,AVG(watchDuration) mean,MIN(watchDuration) min,MAX(watchDuration) max,stddev_samp(watchDuration) stddev,'"+label+"' scope,'seconds' unit FROM v_joined "+where)
        expected=duration('','all_events').unionByName(duration('WHERE watchDuration>0','watch_segments'))
        actual=spark.read.parquet(r+'/stats/watch_duration_summary/parquet')
        duration_result=compare_frames(expected,actual.drop('median'),['scope'])
        quantiles=[]
        for row in actual.select('scope','count','median').collect():
            frame=joined if row['scope']=='all_events' else joined.filter('watchDuration>0')
            if row['count']==0:ok=row['median'] is None;counts={}
            else:
                counts=frame.agg(F.sum((F.col('watchDuration')<row['median']).cast('long')).alias('less'),F.sum((F.col('watchDuration')<=row['median']).cast('long')).alias('less_equal')).first().asDict()
                tolerance=max(1,math.ceil(row['count']/10000))+1
                ok=counts['less']<=row['count']*.5+tolerance and counts['less_equal']>=row['count']*.5-tolerance
            quantiles.append({'scope':row['scope'],'median':row['median'],'pass':ok,**counts})
        duration_result['approximate_median_rank_checks']=quantiles;duration_result['pass'] &= all(x['pass'] for x in quantiles)
        report['analyses']['watch_duration_summary']=duration_result
        actions=spark.read.parquet(r+'/stats/action_distribution/parquet').agg(F.sum('count').alias('count'),F.sum('percentage').alias('percentage')).first()
        hourly=spark.read.parquet(r+'/stats/hourly_activity/parquet').agg(F.sum('eventCount')).first()[0]
        report['checks']['analysis_totals']=actions['count']==hourly==n and abs(actions['percentage']-100)<1e-8
        report['checks']['all_seven_analyses']=len(report['analyses'])==7 and all(x['pass'] for x in report['analyses'].values())
        # Independently reconstruct user features from joined data.
        expected=spark.sql("""SELECT userId,
          SUM(CASE WHEN action='play' THEN 1 ELSE 0 END) playCount,
          SUM(CASE WHEN action='complete' THEN 1 ELSE 0 END) completeCount,
          SUM(watchDuration) totalWatchDuration,
          COALESCE(AVG(CASE WHEN watchDuration>0 THEN watchDuration END),0D) avgWatchDuration,
          COUNT(DISTINCT movieId) distinctMovies,COUNT(DISTINCT struct(runId,sessionId)) sessionCount,
          COUNT(DISTINCT CASE WHEN action='play' THEN struct(runId,sessionId) END) playedSessionCount,
          COUNT(DISTINCT CASE WHEN action='complete' THEN struct(runId,sessionId) END) completedSessionCount,
          COUNT(DISTINCT _calendarDate) activeDays,COUNT(*) eventCount FROM v_joined GROUP BY userId""")
        genre_counts=spark.sql("SELECT userId,COUNT(DISTINCT genre) distinctGenres FROM (SELECT userId,explode(genresArray) genre FROM v_joined) g GROUP BY userId")
        expected=(expected.join(genre_counts,'userId','left').fillna({'distinctGenres':0})
                  .withColumn('completionRateDefined',F.col('playedSessionCount')>0)
                  .withColumn('completionRate',F.when(F.col('playedSessionCount')>0,F.col('completedSessionCount')/F.col('playedSessionCount')).otherwise(F.lit(0.0))))
        report['features']=compare_frames(expected.select(*features.columns),features,['userId'])
        report['checks']['independent_features']=report['features']['pass']
        feature_columns=[name for name in features.columns if name not in ['userId','playedSessionCount','completedSessionCount','completionRateDefined']]
        variances=features.agg(*[F.var_samp(name).alias(name) for name in feature_columns]).first().asDict()
        report['feature_variances']=variances
        report['checks']['variance_and_exclusion_remeasured']=all(math.isclose(value,metadata['feature_variances'][name],rel_tol=1e-10,abs_tol=1e-8) for name,value in variances.items())
        pairs=[(a,b) for i,a in enumerate(feature_columns) for b in feature_columns[i+1:] if variances[a]>0 and variances[b]>0]
        correlations=features.agg(*[F.corr(a,b).alias('c'+str(i)) for i,(a,b) in enumerate(pairs)]).first().asDict()
        report['feature_correlations']=[{'left':a,'right':b,'pearson':correlations['c'+str(i)]} for i,(a,b) in enumerate(pairs)]
        report['event_count_redundancy_bad_users']=features.filter('eventCount != sessionCount + 2*playCount').count()
        report['checks']['excluded_features_justified']=all((reason=='zero_variance' and variances[name]==0) or (name=='eventCount' and report['event_count_redundancy_bad_users']==0) for name,reason in metadata['excluded_features'].items())
        # Read every output from HDFS with its declared format and schema.
        by_name={row['name']:row for row in manifest['artifacts'] if row['format']=='parquet'}
        key_map={name:keys for name,(_,keys) in queries.items()};key_map['watch_duration_summary']=['scope']
        key_map.update({'user_features':['userId'],'k_search':['k'],'assignments':['userId'],'cluster_profiles':['cluster'],'model_metadata':['bestK']})
        for item in manifest['artifacts']:
            uri=safe_output_uri(item['uri'],context['run_id']);fmt=item['format']
            entry={'name':item['name'],'format':fmt,'uri':uri,'expected_rows':item['rows']}
            if fmt=='spark_ml_pipeline':continue
            if 'schema' not in item:
                text=spark.read.text(uri);count=text.count()
                values=json.loads(text.first()[0]) if count==1 else None
                entry.update(rows=count,schema_valid=True,values_valid=count==1 and values==load(item['name']+'.json'))
            else:
                declared=StructType.fromJson(item['schema']);reader=spark.read
                if fmt=='parquet':frame=reader.parquet(uri);expected_schema=declared
                elif fmt=='json':frame=reader.schema(declared).option('mode','FAILFAST').json(uri);expected_schema=declared
                else:
                    expected_schema=StructType([StructField(field.name,StringType(),True) if field.dataType.typeName() in ['array','map','struct'] else field for field in declared])
                    frame=reader.schema(expected_schema).option('header','true').option('escape','"').option('mode','FAILFAST').csv(uri)
                count=frame.count();schema_ok=shape(frame.schema)==shape(expected_schema);value_ok=True
                if fmt!='parquet':
                    reference=spark.read.parquet(by_name[item['name']]['uri'])
                    if fmt=='csv':reference=reference.select(*[F.to_json(F.col(field.name)).alias(field.name) if field.dataType.typeName() in ['array','map','struct'] else F.col(field.name) for field in reference.schema])
                    keys=key_map[item['name'].split('/')[-1]]
                    detail=compare_frames(reference,frame,keys);value_ok=detail['pass'];entry['value_comparison']=detail
                entry.update(rows=count,schema_valid=schema_ok,values_valid=value_ok)
            entry['pass']=entry['rows']==entry['expected_rows'] and entry['schema_valid'] and entry['values_valid']
            report['outputs'].append(entry)
        report['checks']['all_output_formats_schemas_counts_values']=all(row['pass'] for row in report['outputs'])
        model=PipelineModel.load(metadata['model_uri']);predicted=model.transform(features)
        assignments=spark.read.parquet(r+'/kmeans/assignments/parquet')
        report['model_reload']=compare_frames(assignments.select('userId','cluster'),predicted.select('userId',F.col('prediction').alias('cluster')),['userId'])
        report['checks']['independent_model_reload']=report['model_reload']['pass']
        prepared=spark.read.parquet(r+'/kmeans/features_prepared')
        to_array=F.udf(lambda vector:[float(value) for value in vector],ArrayType(DoubleType(),False))
        vectors=lambda frame:frame.select('userId',to_array('rawFeatures').alias('rawFeatures'),to_array('features').alias('features'))
        report['prepared_vectors']=compare_frames(vectors(predicted),vectors(prepared),['userId'])
        report['checks']['prepared_vectors_match_saved_scaler']=report['prepared_vectors']['pass']
        if not all(report['checks'].values()):raise ValueError('Independent verification checks failed: '+str([name for name,ok in report['checks'].items() if not ok]))
        report['status']='PASS'
    except Exception as exc:
        report['error']=str(exc)
    finally:
        for frame in cached:frame.unpersist()
        if spark is not None:spark.stop()
        report['finished_at_utc']=utcnow();new_json(args.report,report)
    print(json.dumps({key:value for key,value in report.items() if key not in ['outputs','feature_correlations']},ensure_ascii=True,indent=2))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
