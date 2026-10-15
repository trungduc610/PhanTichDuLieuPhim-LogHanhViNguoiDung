"""TV2 cleaning/transformation using the existing business schemas."""
from functools import reduce
from pyspark import StorageLevel
from pyspark.sql import functions as F,Window
from pyspark.sql.types import StructType,StructField,StringType
from src.schemas import MOVIE_SCHEMA,USER_LOG_SCHEMA

ACTIONS=('view','play','pause','stop','complete')
BUSINESS_FIELDS=[field.name for field in USER_LOG_SCHEMA]
RULES=[('malformed_json_count','_bad_json'),('null_count','_bad_null'),
       ('empty_required_string_count','_bad_empty'),('invalid_action_count','_bad_action'),
       ('invalid_timestamp_count','_bad_timestamp'),('invalid_watch_duration_count','_bad_duration'),
       ('invalid_integer_count','_bad_integer'),('invalid_provenance_count','_bad_provenance')]


def validate_movies(movies):
    required=[field.name for field in MOVIE_SCHEMA if not field.nullable]
    invalid=(reduce(lambda a,b:a|b,[F.col(name).isNull() for name in required]) |
             (F.trim('title')=='') | (F.trim('genres')=='') | (F.col('movieId')<=0) |
             (F.col('releaseYear').isNotNull() & ~F.col('releaseYear').between(1870,2100)) |
             F.col('_corrupt_record').isNotNull())
    info=movies.agg(F.count('*').alias('rows'),F.countDistinct('movieId').alias('unique_ids'),
                   F.sum(F.when(invalid,1).otherwise(0)).alias('invalid_rows'),
                   F.sum(F.col('releaseYear').isNull().cast('long')).alias('releaseYear_null')).first().asDict()
    if not info['rows'] or info['rows']!=info['unique_ids'] or info['invalid_rows']:
        raise ValueError('Invalid/duplicate movie metadata: '+str(info))
    return info


def genres_array(column='genres'):
    parts=F.transform(F.split(F.col(column),r'\|'),lambda item:F.trim(item))
    return F.array_distinct(F.filter(parts,lambda item:F.length(item)>0))


def parse_lines(lines,start,end,event_run_id):
    schema=StructType(list(USER_LOG_SCHEMA.fields)+[StructField('_corrupt_record',StringType(),True)])
    frame=(lines.select(F.col('value').alias('_raw_json'),F.input_file_name().alias('_source_file'))
           .withColumn('_keys',F.json_object_keys('_raw_json'))
           .withColumn('_record',F.from_json('_raw_json',schema,{'mode':'PERMISSIVE','columnNameOfCorruptRecord':'_corrupt_record'})))
    frame=frame.select('_raw_json','_source_file','_keys','_record.*')
    frame=frame.withColumn('eventTimestamp',F.to_timestamp('timestamp',"yyyy-MM-dd'T'HH:mm:ss'Z'"))
    required=[field.name for field in USER_LOG_SCHEMA if not field.nullable]
    required_strings=[field.name for field in USER_LOG_SCHEMA if isinstance(field.dataType,StringType) and not field.nullable]
    conditions={
      '_bad_json':F.col('_corrupt_record').isNotNull() | F.col('_keys').isNull() |
                  (F.array_sort('_keys')!=F.array(*[F.lit(name) for name in sorted(BUSINESS_FIELDS)])),
      '_bad_null':reduce(lambda a,b:a|b,[F.col(name).isNull() for name in required]),
      '_bad_empty':reduce(lambda a,b:a|b,[F.length(F.trim(F.col(name)))==0 for name in required_strings]),
      '_bad_action':F.col('action').isNull() | ~F.col('action').isin(*ACTIONS),
      '_bad_timestamp':F.col('eventTimestamp').isNull() |
          ~F.col('timestamp').rlike(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$') |
          (F.col('eventTimestamp')<F.to_timestamp(F.lit(start))) |
          (F.col('eventTimestamp')>=F.to_timestamp(F.lit(end))),
      '_bad_duration':F.col('watchDuration').isNull() | (F.col('watchDuration')<0) |
          (F.col('watchDuration')>F.col('simulatedMovieDuration')) |
          (F.col('action').isin('view','play') & (F.col('watchDuration')!=0)) |
          (F.col('action').isin('pause','stop','complete') & (F.col('watchDuration')<=0)),
      '_bad_integer':(F.col('movieId')<=0) | (F.col('sequenceNumber')<0) |
          ~F.col('simulatedMovieDuration').between(3600,10800),
      '_bad_provenance':(F.col('isSynthetic')!=True) | (F.col('durationSource')!='synthetic') |
          (F.col('runId')!=event_run_id)}
    for name,condition in conditions.items():frame=frame.withColumn(name,F.coalesce(condition,F.lit(False)))
    reasons=F.array(*[F.when(F.col(flag),F.lit(metric)) for metric,flag in RULES])
    return frame.withColumn('rejected_reason',F.filter(reasons,lambda item:item.isNotNull()))


def rejection(frame,reason=None):
    reasons=F.array(F.lit(reason)) if reason else F.col('rejected_reason')
    return frame.select(*BUSINESS_FIELDS,F.col('_source_file').alias('sourceFile'),
                        F.col('_raw_json').alias('rawJson'),reasons.alias('rejected_reason'))


def clean_lines(lines,movies,start,end,event_run_id):
    flagged=parse_lines(lines,start,end,event_run_id).persist(StorageLevel.DISK_ONLY)
    expressions=[F.count('*').alias('raw_log_count')]+[F.sum(F.col(flag).cast('long')).alias(metric) for metric,flag in RULES]
    report={key:(value or 0) for key,value in flagged.agg(*expressions).first().asDict().items()}
    report['parsed_log_count']=report['raw_log_count']-report['malformed_json_count']
    remaining=flagged;before=report['raw_log_count'];steps=[]
    for metric,flag in RULES:
        remaining=remaining.filter(~F.col(flag))
        after=remaining.count() if report[metric] else before
        steps.append({'rule':metric,'before':before,'removed':before-after,'after':after});before=after
    print('TV2_BASIC_RULES '+str({key:value for key,value in report.items() if key!='steps'}),flush=True)
    eligible=remaining.select(*BUSINESS_FIELDS,'eventTimestamp','_source_file','_raw_json').persist(StorageLevel.DISK_ONLY)
    id_counts=eligible.groupBy('eventId').agg(F.count('*').alias('_id_rows')).persist(StorageLevel.MEMORY_AND_DISK)
    duplicate_ids=id_counts.filter(F.col('_id_rows')>1)
    duplicate_groups=duplicate_ids.count()
    # Only repeated IDs need full-payload distinct aggregation. Unique IDs have one variant.
    if duplicate_groups:
        payload=F.to_json(F.struct(*[F.col(name) for name in BUSINESS_FIELDS]))
        variants=(eligible.join(duplicate_ids.select('eventId'),'eventId','inner').groupBy('eventId')
                  .agg(F.countDistinct(payload).alias('_payload_variants')))
        groups=id_counts.join(variants,'eventId','left').fillna({'_payload_variants':1})
    else:
        groups=id_counts.withColumn('_payload_variants',F.lit(1).cast('long'))
    groups=groups.persist(StorageLevel.MEMORY_AND_DISK)
    dup=groups.agg(F.sum(F.when(F.col('_id_rows')>1,1).otherwise(0)).alias('duplicate_event_id_groups'),
        F.sum(F.col('_id_rows')-F.col('_payload_variants')).alias('exact_duplicate_count'),
        F.sum(F.when(F.col('_payload_variants')>1,1).otherwise(0)).alias('conflicting_event_id_groups'),
        F.sum(F.when(F.col('_payload_variants')>1,F.col('_id_rows')).otherwise(0)).alias('conflicting_event_rows'),
        F.sum(F.when(F.col('_payload_variants')>1,F.col('_id_rows')).otherwise(F.col('_id_rows')-1)).alias('duplicate_count')).first().asDict()
    report.update({key:value or 0 for key,value in dup.items()})
    if duplicate_groups:
        ranked=(eligible.join(groups,'eventId').withColumn('_rank',F.row_number().over(
                Window.partitionBy('eventId').orderBy('_source_file','_raw_json'))))
    else:
        ranked=eligible.withColumn('_payload_variants',F.lit(1)).withColumn('_rank',F.lit(1))
    dedup=(ranked.filter((F.col('_payload_variants')==1)&(F.col('_rank')==1))
           .select(*BUSINESS_FIELDS,'eventTimestamp','_source_file','_raw_json').persist(StorageLevel.DISK_ONLY))
    dedup_count=dedup.count()
    if dedup_count!=before-report['duplicate_count']:raise ValueError('Duplicate reconciliation mismatch')
    steps.append({'rule':'duplicate_count','before':before,'removed':report['duplicate_count'],'after':dedup_count})
    ids=F.broadcast(movies.select('movieId'))
    orphan=dedup.join(ids,'movieId','left_anti')
    orphan_count=orphan.count()
    clean=(dedup.join(ids,'movieId','left_semi').select(*BUSINESS_FIELDS,'eventTimestamp',
           F.col('_source_file').alias('sourceFile')).persist(StorageLevel.MEMORY_AND_DISK))
    clean_count=clean.count()
    if dedup_count!=clean_count+orphan_count:raise ValueError('Orphan reconciliation mismatch')
    steps.append({'rule':'orphan_movie_id_count','before':dedup_count,'removed':orphan_count,'after':clean_count})
    base_bad=rejection(flagged.filter(F.size('rejected_reason')>0))
    duplicate_bad=ranked.filter((F.col('_payload_variants')>1)|(F.col('_rank')>1))
    duplicate_bad=duplicate_bad.withColumn('rejected_reason',F.array(F.when(F.col('_payload_variants')>1,
                    F.lit('conflicting_event_id')).otherwise(F.lit('exact_duplicate'))))
    rejected=base_bad.unionByName(rejection(duplicate_bad)).unionByName(rejection(orphan,'orphan_movie_id'))
    report.update(orphan_movie_id_count=orphan_count,pre_join_clean_log_count=dedup_count,
                  clean_log_count=clean_count,rejected_record_count=report['raw_log_count']-clean_count,
                  steps=steps,counting_semantics='Basic rule counts are independent on raw rows and may overlap. Duplicate metrics apply after basic rules; conflicting IDs reject all variants. Orphans are counted after deduplication. Steps are disjoint removals.',
                  duplicate_policy='Canonical business fields; keep one identical eventId payload, reject every row of conflicting eventIds.')
    rejected_count=rejected.count()
    if rejected_count!=report['rejected_record_count']:raise ValueError('Rejected record reconciliation mismatch')
    # Rejected output retains its source lineage until written by the caller.
    return clean,rejected,report,[flagged,eligible,id_counts,groups,dedup]


def transform_logs(clean,timezone='Asia/Ho_Chi_Minh'):
    return (clean.withColumn('eventLocalTimestamp',F.from_utc_timestamp('eventTimestamp',timezone))
            .withColumn('date',F.to_date('eventLocalTimestamp')).withColumn('hour',F.hour('eventLocalTimestamp'))
            .withColumn('dayOfWeek',F.dayofweek('eventLocalTimestamp'))
            .withColumn('watchDurationMinutes',F.col('watchDuration')/F.lit(60.0)))


def join_movies(transformed,movies):
    metadata=movies.select('movieId','title','genres','releaseYear').withColumn('genresArray',genres_array())
    return transformed.join(F.broadcast(metadata),'movieId','inner')
