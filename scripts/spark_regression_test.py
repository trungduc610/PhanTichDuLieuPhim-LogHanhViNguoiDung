"""Spark regression fixtures, never Flume output evidence."""
import argparse
import copy
import json
from pathlib import Path
from spark_smoke_test import validate_frames, MOVIE_SCHEMA, USER_LOG_SCHEMA, SparkSession
from pyspark.sql import functions as F


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',required=True)
    a=p.parse_args()
    target=Path(a.report)
    if target.exists():
        raise FileExistsError(target)
    spark=(SparkSession.builder.master('local[2]').appName('Week1-Spark-Regression-Fixtures').config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','2').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    tests=[]
    movies=[{'movieId':1,'title':'Fixture (2001)','genres':'Drama','releaseYear':2001}]
    events=[{'eventId':f'fixture-{i}','userId':f'user-{i}','sessionId':f'session-{i}','movieId':1,'action':'view','timestamp':'2026-09-01T00:00:00Z','watchDuration':0,'sequenceNumber':0,'runId':'fixture','isSynthetic':True,'simulatedMovieDuration':3600,'durationSource':'synthetic'} for i in range(6)]
    def run(name, ms, es, expected_error=None, null_schema=False):
        from pyspark.sql.types import StructType,StructField
        schema=StructType([StructField(f.name,f.dataType,True) for f in USER_LOG_SCHEMA]) if null_schema else USER_LOG_SCHEMA
        result=validate_frames(spark,spark.createDataFrame(ms,MOVIE_SCHEMA),spark.createDataFrame(es,schema),len(ms),len(es),'2026-09-01T00:00:00Z','2026-10-01T00:00:00Z')
        passed=result['status']=='PASS' if expected_error is None else result['status']=='FAIL' and result['errors'][expected_error]>0
        tests.append({'name':name,'passed':passed,'result':result})
        if not passed:
            raise AssertionError(name)
    try:
        run('valid_fixture',movies,events)
        bad=copy.deepcopy(events); bad[5]['movieId']=999
        run('orphan_beyond_first_five',movies,bad,'orphan_movie_events')
        bad=copy.deepcopy(events); bad[5]['timestamp']='invalid'
        run('invalid_timestamp',movies,bad,'log_timestamp_parse')
        bad=copy.deepcopy(events); bad[5]['userId']=None
        run('required_null',movies,bad,'log_required_null',True)
        run('duplicate_movie_metadata',movies+movies,events,'movie_duplicate_ids')
        bad=copy.deepcopy(events); bad[5]['eventId']=bad[0]['eventId']
        run('conflicting_event_id',movies,bad,'log_conflicting_ids')
        bad=copy.deepcopy(events); bad[5]['watchDuration']=-1
        run('negative_duration',movies,bad,'log_duration')
    finally:
        spark.stop()
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps({'fixture_only':True,'never_flume_evidence':True,'tests':tests,'status':'PASS' if len(tests)==7 and all(x['passed'] for x in tests) else 'FAIL'},ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print('Spark regression fixtures:',len(tests),'PASS')


if __name__=='__main__':
    main()
