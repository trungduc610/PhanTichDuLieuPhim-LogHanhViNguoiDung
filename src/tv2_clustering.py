"""Measured Spark MLlib K=2..6 search and quantitative cluster profiles."""
import math
from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import VectorAssembler,StandardScaler
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.sql import functions as F
from src.tv2_analytics import FEATURE_COLUMNS,validate_features
from tv2_common import select_best_k

PROFILE_NAMES={'playCount':'avgPlayCount','completeCount':'avgCompleteCount',
 'totalWatchDuration':'avgTotalWatchDuration','avgWatchDuration':'avgWatchDuration',
 'distinctMovies':'avgDistinctMovies','distinctGenres':'avgDistinctGenres','sessionCount':'avgSessionCount',
 'completionRate':'avgCompletionRate','activeDays':'avgActiveDays','eventCount':'avgEventCount'}


def cluster_users(features,seed=42,max_iter=50):
    validation=validate_features(features)
    variances=features.agg(*[F.var_samp(name).alias(name) for name in FEATURE_COLUMNS]).first().asDict()
    excluded={name:'zero_variance' for name,value in variances.items() if value is None or value==0}
    if any(value is not None and (not math.isfinite(value) or value<0) for value in variances.values()):
        raise ValueError('Invalid feature variance')
    redundant=features.filter(F.col('eventCount')!=F.col('sessionCount')+2*F.col('playCount')).count()==0
    if redundant:excluded['eventCount']='exactly sessionCount + 2*playCount; retain in dataset, exclude redundant ML dimension'
    selected=[name for name in FEATURE_COLUMNS if name not in excluded]
    if not selected or validation['users']<6 or features.select(*selected).distinct().count()<6:
        raise ValueError('K=2..6 needs at least six users and six distinct nonconstant feature vectors')
    assembler=VectorAssembler(inputCols=selected,outputCol='rawFeatures',handleInvalid='error')
    assembled=assembler.transform(features.orderBy('userId'))
    scaler=StandardScaler(inputCol='rawFeatures',outputCol='features',withMean=True,withStd=True).fit(assembled)
    prepared=scaler.transform(assembled).persist(StorageLevel.MEMORY_AND_DISK)
    if prepared.count()!=validation['users']:raise ValueError('Feature preparation changed user count')
    evaluator=ClusteringEvaluator(featuresCol='features',predictionCol='prediction',metricName='silhouette',distanceMeasure='squaredEuclidean')
    records=[];models={}
    for k in range(2,7):
        model=KMeans(k=k,seed=seed,maxIter=max_iter,featuresCol='features',predictionCol='prediction',distanceMeasure='euclidean').fit(prepared)
        predicted=model.transform(prepared)
        observed={row['prediction']:row['count'] for row in predicted.groupBy('prediction').count().collect()}
        sizes=[int(observed.get(index,0)) for index in range(k)]
        if sizes!=list(model.summary.clusterSizes) or sum(sizes)!=validation['users']:
            raise ValueError('Model summary and observed cluster sizes disagree')
        records.append({'k':k,'silhouette':float(evaluator.evaluate(predicted)),
                        'cluster_sizes':sizes,'training_cost':float(model.summary.trainingCost),'users':validation['users']})
        models[k]=model
    best=select_best_k(records);model=models[best['k']]
    assignments=(model.transform(prepared).select('userId',*FEATURE_COLUMNS,'playedSessionCount',
                  'completedSessionCount','completionRateDefined',F.col('prediction').cast('int').alias('cluster'))
                 .persist(StorageLevel.MEMORY_AND_DISK))
    counts=assignments.agg(F.count('*').alias('rows'),F.countDistinct('userId').alias('unique_users')).first().asDict()
    if counts['rows']!=validation['users'] or counts['rows']!=counts['unique_users']:
        raise ValueError('Assignment count/unique users mismatch')
    profiles=assignments.groupBy('cluster').agg(F.count('*').alias('userCount'),
        *[F.avg(name).alias(PROFILE_NAMES[name]) for name in FEATURE_COLUMNS],
        F.min('playCount').alias('minPlayCount'),F.max('playCount').alias('maxPlayCount'),
        F.min('totalWatchDuration').alias('minTotalWatchDuration'),F.max('totalWatchDuration').alias('maxTotalWatchDuration'),
        F.percentile_approx('totalWatchDuration',0.5,10000).alias('medianTotalWatchDuration'))
    profiles=profiles.withColumn('label',F.concat(F.lit('Cluster '),F.col('cluster'))).orderBy('cluster')
    rows=[row.asDict() for row in profiles.collect()]
    if sum(row['userCount'] for row in rows)!=validation['users']:raise ValueError('Profile cluster sizes do not sum to users')
    scores=sorted(records,key=lambda row:row['silhouette'],reverse=True)
    metadata={'best_k':best['k'],'silhouette':best['silhouette'],'seed':seed,'max_iter':max_iter,
       'feature_columns':selected,'excluded_features':excluded,'feature_variances':variances,
       'scaling':{'withMean':True,'withStd':True},'evaluator_distance':'squaredEuclidean',
       'training_distance':'euclidean','users':validation['users'],'cluster_sizes':best['cluster_sizes'],
       'training_cost':best['training_cost'],'score_gap_to_runner_up':scores[0]['silhouette']-scores[1]['silhouette'],
       'centers_scaled':[center.tolist() for center in model.clusterCenters()],
       'selection_rule':'Greatest measured silhouette; lower K only for an exact tie.',
       'completion_rate':'completed distinct (runId,sessionId) / sessions with play; zero if denominator is zero',
       'avg_watch_duration':'Mean positive watch segment duration, seconds; zero for users with no watch segments',
       'labels':'Neutral cluster IDs; interpret from measured raw-unit profile metrics, not predefined behavior labels.'}
    return {'prepared':prepared,'assignments':assignments,'profiles':profiles,'profile_rows':rows,
            'search':records,'metadata':metadata,'validation':validation,
            'model':PipelineModel(stages=[assembler,scaler,model])}
