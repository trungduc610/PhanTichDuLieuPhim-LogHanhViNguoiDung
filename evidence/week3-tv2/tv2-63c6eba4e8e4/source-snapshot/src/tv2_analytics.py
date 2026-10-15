"""TV2 statistics and per-user features; aggregation stays in Spark."""
from pyspark.sql import functions as F,Window

FEATURE_COLUMNS=['playCount','completeCount','totalWatchDuration','avgWatchDuration',
                 'distinctMovies','distinctGenres','sessionCount','completionRate','activeDays','eventCount']


def build_statistics(events,event_count,top_n=20):
    plays=events.filter(F.col('action')=='play')
    top_movies=(plays.groupBy('movieId','title').agg(F.count('*').alias('playCount'))
                .orderBy(F.desc('playCount'),F.asc('movieId')).limit(top_n))
    top_genres=(plays.select(F.explode('genresArray').alias('genre')).groupBy('genre')
                .agg(F.count('*').alias('playCount')).orderBy(F.desc('playCount'),F.asc('genre')))
    daily=(events.groupBy('date').agg(F.countDistinct('userId').alias('activeUsers')).orderBy('date'))
    hourly=(events.groupBy('hour').agg(F.count('*').alias('eventCount'),F.countDistinct('userId').alias('distinctUsers'),
             F.sum(F.when(F.col('action')=='play',1).otherwise(0)).alias('playCount')).orderBy('hour'))
    actions=(events.groupBy('action').agg(F.count('*').alias('count'))
             .withColumn('percentage',F.col('count')*F.lit(100.0)/F.lit(event_count)).orderBy('action'))
    def duration(frame,label):
        return frame.agg(F.count('*').alias('count'),F.avg('watchDuration').alias('mean'),
           F.percentile_approx('watchDuration',0.5,10000).cast('double').alias('median'),
           F.min('watchDuration').alias('min'),F.max('watchDuration').alias('max'),
           F.stddev_samp('watchDuration').alias('stddev')).withColumn('scope',F.lit(label)).withColumn('unit',F.lit('seconds'))
    watch=duration(events,'all_events').unionByName(duration(events.filter(F.col('watchDuration')>0),'watch_segments'))
    combined=(plays.groupBy('hour','movieId','title').agg(F.count('*').alias('playCount'),
               F.countDistinct('userId').alias('distinctUsers'))
              .withColumn('rank',F.row_number().over(Window.partitionBy('hour').orderBy(F.desc('playCount'),F.asc('movieId'))))
              .filter(F.col('rank')<=3).orderBy('hour','rank'))
    return {'top_movies_by_play':top_movies,'top_genres':top_genres,'daily_active_users':daily,
            'hourly_activity':hourly,'action_distribution':actions,'watch_duration_summary':watch,
            'user_movie_time':combined}


def build_user_features(events):
    session=F.struct('runId','sessionId')
    def action_count(action):return F.sum(F.when(F.col('action')==action,1).otherwise(0))
    users=events.groupBy('userId').agg(action_count('play').alias('playCount'),action_count('complete').alias('completeCount'),
       F.sum('watchDuration').alias('totalWatchDuration'),
       F.avg(F.when(F.col('watchDuration')>0,F.col('watchDuration'))).alias('avgWatchDuration'),
       F.countDistinct('movieId').alias('distinctMovies'),F.countDistinct(session).alias('sessionCount'),
       F.countDistinct(F.when(F.col('action')=='play',session)).alias('playedSessionCount'),
       F.countDistinct(F.when(F.col('action')=='complete',session)).alias('completedSessionCount'),
       F.countDistinct('date').alias('activeDays'),F.count('*').alias('eventCount'))
    genres=(events.select('userId',F.explode('genresArray').alias('genre')).groupBy('userId')
            .agg(F.countDistinct('genre').alias('distinctGenres')))
    users=(users.join(genres,'userId','left').fillna({'avgWatchDuration':0.0,'distinctGenres':0})
           .withColumn('completionRateDefined',F.col('playedSessionCount')>0)
           .withColumn('completionRate',F.when(F.col('playedSessionCount')>0,
               F.col('completedSessionCount')/F.col('playedSessionCount')).otherwise(F.lit(0.0))))
    return users.select('userId',*FEATURE_COLUMNS,'playedSessionCount','completedSessionCount','completionRateDefined')


def validate_features(features):
    metrics=[F.count('*').alias('users'),F.countDistinct('userId').alias('unique_users')]
    for name in FEATURE_COLUMNS:
        value=F.col(name).cast('double')
        bad=value.isNull() | F.isnan(value) | (F.abs(value)==F.lit(float('inf')))
        metrics.append(F.sum(F.when(bad,1).otherwise(0)).alias(name+'_invalid'))
    summary=features.agg(*metrics).first().asDict()
    if not summary['users'] or summary['users']!=summary['unique_users'] or any(summary[name+'_invalid'] for name in FEATURE_COLUMNS):
        raise ValueError('Null/NaN/Infinity or duplicate users in features: '+str(summary))
    if features.filter((F.col('completionRate')<0)|(F.col('completionRate')>1)).count():
        raise ValueError('Completion rate is outside [0,1]')
    return summary
