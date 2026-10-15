import json,math,re,sys
from pathlib import Path
sys.path.insert(0,'scripts')
from common import sha256,utcnow
from hdfs_common import Ledger,new_json
from create_delivery_manifest import verify
root=Path.cwd();run='tv2-aae83326c1ab';prefix='evidence/week3-tv2/'+run;folder=root/prefix
load=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
c=load('run_context.json');s=load('pipeline_summary.json');m=load('model_metadata.json');v=load('runtime-verification.json');manifest=load('output_manifest.json');stats=load('statistics_summary.json');clean=load('cleaning_summary.json');j=load('join_summary.json');qa=load('input-hdfs-qa.json');profiles=load('cluster_profiles.json');search=load('kmeans_search.json');features=load('feature_validation.json');raw=load('raw-preservation.json');tests=load('host-tests-final.json');result=load('result-verification.json')
receipts=['run_status.json','pipeline_summary.json','input-hdfs-qa.json','spark-fixture-tests.json','runtime-verification.json','result-verification.json','raw-preservation.json','host-tests-final.json','historical-preservation-after.json']
assert all(load(name)['status']=='PASS' for name in receipts)
assert all(v['checks'].values()) and all(result['checks'].values()) and all(x==0 for x in qa['errors'].values())
assert m['seed']==42 and {x['k'] for x in search}=={2,3,4,5,6}
assert all(math.isfinite(x['silhouette']) and math.isfinite(x['training_cost']) and x['training_cost']>=0 for x in search)
assert m['best_k']==max(search,key=lambda x:(x['silhouette'],-x['k']))['k']
assert all(sha256(root/name)==digest for name,digest in c['code_hashes'].items())
assert all(sha256(root/name)==digest for name,digest in c['protected_tv1_hashes'].items())
old=load('historical-preservation-before.json')['files']
assert all((root/name).is_file() and (root/name).stat().st_size==proof['bytes'] and sha256(root/name)==proof['sha256'] for name,proof in old.items())
p=s['processed_root'];r=s['results_root']
small=[x for x in manifest['artifacts'] if x['name'].startswith(('stats/','kmeans/')) and x['format'] in ['parquet','csv','json'] and 'schema' in x and x['name']!='kmeans/features_prepared']
assert len(small)==36
outputs=[]
for item in small:
 entry={key:item[key] for key in ['name','format','uri','rows','read_back_rows','schema']};entry['hdfs_path']=entry.pop('uri')
 if item['format'] in ['csv','json']:
  local=folder/'dashboard'/(item['name'].replace('/','_')+'.'+item['format']);assert local.is_file()
  entry.update(local_path=local.relative_to(root).as_posix(),local_bytes=local.stat().st_size,local_sha256=sha256(local))
 outputs.append(entry)
handoff={'status':'PASS','released_at_utc':utcnow(),'tv2_run_id':run,'tv1_flume_run':c['flume_run_id'],'tv1_hdfs_run':c['hdfs_run_id'],'compose_project':c['project'],
 'hdfs_input':{'movies_uri':s['movies_uri'],'logs_uri':s['logs_uri'],'source_manifest':c['source_manifest'],'source_manifest_sha256':c['source_manifest_sha256'],'movies':s['movies'],'events':s['raw_events'],'files':raw['files_before'],'bytes':raw['bytes_before'],'filesystem':s['environment']['filesystem'],'local_fallback':False},
 'processed_root':p,'results_root':r,'best_k':m['best_k'],'silhouette':m['silhouette'],'seed':m['seed'],'max_iter':m['max_iter'],'feature_columns':m['feature_columns'],'excluded_features':m['excluded_features'],'feature_variances':m['feature_variances'],'cluster_profiles':profiles,
 'model':{'uri':m['model_uri'],'format':'spark_ml_pipeline','reload_assignments':v['model_reload']['actual_rows'],'reload_mismatches':v['model_reload']['mismatched_rows'],'scaler_vectors_match':v['prepared_vectors']['pass']},
 'processed_outputs':[{key:x[key] for key in ['name','format','uri','rows','read_back_rows']} for x in manifest['artifacts'] if x['name'] in ['cleaned_logs','joined_events','rejected_logs','user_features','kmeans/features_prepared']],
 'dashboard_outputs':outputs,'timezone':{'source':'UTC Z','spark_session':'UTC','calendar':'Asia/Ho_Chi_Minh'},'duration_units':{'watchDuration':'seconds, incremental segments','watchDurationMinutes':'derived minutes','avgWatchDuration':'mean positive segment, seconds'},'synthetic':True,
 'limitations':['Synthetic users, behavior and movie runtime','Spark local[2], one host','Correlated features','Internal silhouette, no external behavioral validation','Neutral cluster IDs'],
 'dataset_selection_rule':'Use only this exact run. Local JSON is an array; HDFS JSON is JSON Lines. CSV has a UTF-8 header and nested arrays encoded as JSON.',
 'do_not_mix_tv2_runs':['tv2-4ed70c10cd84','tv2-0523e144a808','tv2-63c6eba4e8e4','tv2-5c5f819cacaa','tv2-56569b78b4e1'],
 'validation_receipts':{name:{'path':prefix+'/'+name,'sha256':sha256(folder/name)} for name in receipts}}
assert all(run in x['hdfs_path'] for x in outputs)
assert len({(x['name'],x['format']) for x in outputs})==36

def table(headers,rows):
 val=lambda x:str(x).replace('|','\\|').replace('\n',' ')
 return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(val(x) for x in row)+' |' for row in rows])
def fmt(x,d=3):
 if isinstance(x,float):return f'{x:,.{d}f}'
 if isinstance(x,int):return f'{x:,}'
 return str(x)
def write_doc(name,text,new=False):
 with (root/'docs'/name).open('x' if new else 'w',encoding='utf-8',newline='\n') as f:f.write(text)
groups={}
for x in manifest['artifacts']:
 if x['name'] in ['cleaned_logs','joined_events','rejected_logs','user_features','kmeans/features_prepared','kmeans/model'] or any(x['name']==row['name'] for row in small):groups.setdefault(x['name'],[]).append(x)
output_rows=[]
for name,items in groups.items():
 base=items[0]['uri'].rsplit('/',1)[0] if len(items)>1 else items[0]['uri']
 rows='1 PipelineModel; 1,000 assignments verified' if name=='kmeans/model' else fmt(items[0]['rows'])
 output_rows.append([name,', '.join(x['format'] for x in items),'`'+base+'`',rows])
output_table=table(['Dataset','Format','HDFS base path','Rows'],output_rows)
profile_a=table(['Cluster','Users','avgPlayCount','avgCompleteCount','avgSessionCount','avgDistinctMovies','avgDistinctGenres'],[[x['cluster'],x['userCount'],fmt(x['avgPlayCount']),fmt(x['avgCompleteCount']),fmt(x['avgSessionCount']),fmt(x['avgDistinctMovies']),fmt(x['avgDistinctGenres'])] for x in profiles])
profile_b=table(['Cluster','avgTotalWatchDuration (s)','avgWatchDuration (s)','avgCompletionRate','avgActiveDays','avgEventCount'],[[x['cluster'],fmt(x['avgTotalWatchDuration']),fmt(x['avgWatchDuration']),fmt(x['avgCompletionRate'],6),fmt(x['avgActiveDays']),fmt(x['avgEventCount'])] for x in profiles])
k_table=table(['K','Silhouette','Cluster sizes','Training cost'],[[x['k'],f"{x['silhouette']:.15f}",str(x['cluster_sizes']),f"{x['training_cost']:.6f}"] for x in search])
variance_table=table(['Feature','Variance measured','ML selection'],[[name,str(value),m['excluded_features'].get(name,'SELECTED')] for name,value in m['feature_variances'].items()])
metric_keys=[('raw','raw_log_count'),('parsed','parsed_log_count'),('malformed','malformed_json_count'),('required_null','null_count'),('exact_duplicates','exact_duplicate_count'),('conflicting_eventId groups','conflicting_event_id_groups'),('conflicting rows','conflicting_event_rows'),('duplicate removals','duplicate_count'),('invalid_action','invalid_action_count'),('invalid_timestamp','invalid_timestamp_count'),('invalid_watchDuration','invalid_watch_duration_count'),('invalid_integer','invalid_integer_count'),('invalid_provenance','invalid_provenance_count'),('orphan','orphan_movie_id_count'),('rejected','rejected_record_count'),('pre_join_clean','pre_join_clean_log_count'),('clean','clean_log_count')]
pre_table=table(['Metric','Count'],[[name,fmt(clean[key])] for name,key in metric_keys])
get=lambda name:stats['stats/'+name]
movie=get('top_movies_by_play')[0];genre=get('top_genres')[0];dau=get('daily_active_users');hourly=get('hourly_activity');peak=max(hourly,key=lambda x:x['eventCount']);duration=get('watch_duration_summary');all_d=next(x for x in duration if x['scope']=='all_events');positive=next(x for x in duration if x['scope']=='watch_segments')
analysis_table=table(['Analysis','Result','Cross-check','Status'],[
 ['Top movies',f"20 rows; {movie['title']}: {fmt(movie['playCount'])} play",'Independent SQL filter/group/order/top 20','PASS'],
 ['Top genres',f"20 rows; {genre['genre']}: {fmt(genre['playCount'])}",'Independent explode/count, multi-label','PASS'],
 ['DAU',f"{len(dau)} dates; DAU={min(x['activeUsers'] for x in dau)} to {max(x['activeUsers'] for x in dau)} users/day",'Distinct users by local date','PASS'],
 ['Hourly',f"24 hours; sum={fmt(sum(x['eventCount'] for x in hourly))}; peak={peak['hour']}",'Local-hour event/play/distinct users','PASS'],
 ['Action distribution','5 actions; total 1,000,000 and 100%','Independent counts and percentages','PASS'],
 ['Watch duration',f"all mean={all_d['mean']:.6f}s; positive mean={positive['mean']:.6f}s",'Aggregates plus approximate median rank bounds','PASS'],
 ['User-movie-time',f"{v['analyses']['user_movie_time']['actual_rows']} rows measured",'Independent counts/distinct users/dynamic top-3 ranking','PASS']])
high=max(profiles,key=lambda x:x['avgPlayCount']);low=min(profiles,key=lambda x:x['avgPlayCount'])
interpretation=f"Cluster {high['cluster']} ({high['userCount']} users) has {high['avgPlayCount']:.3f} play and {high['avgSessionCount']:.3f} sessions/user, versus Cluster {low['cluster']} ({low['avgPlayCount']:.3f} play, {low['avgSessionCount']:.3f} sessions). Total watch seconds average {high['avgTotalWatchDuration']:.3f} versus {low['avgTotalWatchDuration']:.3f}; positive segments are shorter ({high['avgWatchDuration']:.3f}s versus {low['avgWatchDuration']:.3f}s) and completion rate lower ({100*high['avgCompletionRate']:.3f}% versus {100*low['avgCompletionRate']:.3f}%)."
correlations=sorted([x for x in v['feature_correlations'] if x['left'] in m['feature_columns'] and x['right'] in m['feature_columns']],key=lambda x:abs(x['pearson']),reverse=True)[:3]
corr_text='; '.join(f"{x['left']}/{x['right']}: r={x['pearson']:.6f}" for x in correlations)
commands=[]
for path in sorted((folder/'commands').glob('*/finished.json')):
 x=json.loads(path.read_text());commands.append({'label':path.parent.name,'argv':x['argv'],'exit_code':x['exit_code'],'record':path.relative_to(root).as_posix()})
assert all(x['exit_code']==0 for x in commands)
command_table=table(['Command / step','Exit code','Result'],[[x['label'],x['exit_code'],'PASS'] for x in commands])
interpretation=f"Cluster {high['cluster']} ({high['userCount']} users) có trung bình {high['avgPlayCount']:.3f} play và {high['avgSessionCount']:.3f} session/user, cao hơn Cluster {low['cluster']} ({low['avgPlayCount']:.3f} play, {low['avgSessionCount']:.3f} session). Tổng giây xem trung bình là {high['avgTotalWatchDuration']:.3f} so với {low['avgTotalWatchDuration']:.3f}; nhưng đoạn xem dương trung bình ngắn hơn ({high['avgWatchDuration']:.3f}s so với {low['avgWatchDuration']:.3f}s), completion rate thấp hơn ({100*high['avgCompletionRate']:.3f}% so với {100*low['avgCompletionRate']:.3f}%)."
report=f'''# WEEK 3 TV2 FINAL RUNTIME REPORT

TV2: **Bùi Trung Đức**. Nghiệm thu ngày **15/10/2026 (Asia/Saigon)**. Số liệu lấy từ run mới `{run}`; JSON giữ precision đầy đủ. Bằng chứng: [run_status](../{prefix}/run_status.json), [independent verification](../{prefix}/runtime-verification.json), [result verifier](../{prefix}/result-verification.json).

## 1. Overall status

**PASS.** Full runtime, tests, independent recomputation cả 7 analysis, format/schema/value read-back, model/scaler reload, raw preservation và historical preservation đều đạt. Không dùng output Tuần 2 hoặc các attempt trước làm kết quả cuối.

## 2. Run identity

- TV2 Week 3 run: `{run}`.
- Flume run: `{c['flume_run_id']}`.
- HDFS run/project: `{c['hdfs_run_id']}` / `{c['project']}`.
- Movies: `{s['movies_uri']}`.
- Logs: `{s['logs_uri']}`.
- Processed root: `{p}`.
- Results root: `{r}`.
- Pipeline: {s['started_at_utc']} tới {s['finished_at_utc']} (UTC).
- Spark {s['environment']['spark']}, Java {s['environment']['java']}, Hadoop client {s['environment']['hadoop_client']}, local[2], driver 1536m.

Lịch sử được giữ nguyên: `tv2-0523e144a808` BLOCKED; `tv2-63c6eba4e8e4` FAIL tại fixture vì import kéo theo Pandas; `tv2-5c5f819cacaa` FAIL khi mở validator vì đường dẫn Windows. Đã bỏ dependency ngoài ý muốn, chuẩn hóa đường dẫn, thêm regression test, thử validator chỉ đọc trong diagnostics riêng rồi chạy lại toàn bộ run mới. Không sửa các attempt cũ thành PASS. Tài liệu chuẩn bị cũ nằm trong report-preparation-history/.

## 3. Input verification

- Movies: {fmt(s['movies'])}; events / unique eventId: {fmt(s['raw_events'])} / {fmt(qa['logs']['unique_event_ids'])}.
- 1 movie file + 254 Flume Sink log files = {raw['files_before']} raw files; {fmt(raw['bytes_before'])} byte.
- Filesystem: `{s['environment']['filesystem']}`; actual URI `{s['environment']['actual_filesystem_uri']}`; local_fallback=false.
- Raw-before: toàn bộ size/SHA256 khớp manifest; missing/extra=0.
- HDFS QA: {len(qa['errors'])} nhóm, tất cả lỗi=0; đọc đúng 254 log source files.

## 4. Tests before pipeline

Unit/regression TV2 {tests['tv2_tests']}/{tests['tv2_tests']} PASS; Spark fixtures 4/4 PASS. Tests chạy lại trong run mới trước full pipeline. Fixture mới phát hiện missing row, duplicate key và wrong value. HDFS byte/schema/count QA cũng chạy mới; không suy PASS từ receipt cũ.

## 5. Preprocessing

{pre_table}

Basic-rule categories độc lập trên raw và có thể overlap; steps là các lượt loại tuần tự không overlap. Tổng removed={sum(x['removed'] for x in clean['steps'])}, khớp rejected. Exact duplicate giữ một payload; conflicting ID loại tất cả biến thể; orphan quarantine. Rejected giữ sourceFile/rawJson/reason. Input sạch nên không tạo lỗi giả.

## 6. Transformation

Đủ eventTimestamp, eventLocalTimestamp, date, hour, dayOfWeek, watchDurationMinutes, genresArray. Source UTC Z; session UTC; calendar Asia/Ho_Chi_Minh. dayOfWeek: 1=Sunday, 7=Saturday. watchDuration giữ giây incremental segment; minutes=seconds/60. Genres split |, trim, distinct, giữ (no genres listed). Independent verifier phát hiện **{v['transformation_bad_rows']} dòng sai** trên toàn joined dataset.

## 7. Join

movieId hai phía bigint; metadata movieId unique; inner join. pre_join_clean={fmt(j['pre_join_clean_log_count'])}; orphan={j['orphan_count']}; joined={fmt(j['joined_count'])}; clean={fmt(j['clean_log_count'])}.

pre_join_clean_log_count = joined_count + orphan_count và clean_log_count = joined_count đều đạt. Independent full keyed comparison giữ nguyên payload clean: {fmt(v['clean_join_payload']['actual_rows'])} rows, {v['clean_join_payload']['mismatched_rows']} mismatch và 0 duplicate keys. Không row multiplication.

## 8. Analysis validation

{analysis_table}

SQL độc lập với hàm aggregation production, đọc joined Parquet HDFS cùng run và so keys/counts/tất cả values. Float dùng tolerance nhỏ. Approximate median kiểm bằng rank bounds với accuracy=10000; không ép kết quả giữa các partition phải bằng nhau tuyệt đối. Cả 7 nhóm có 0 mismatch.

Một play của phim đa thể loại có thể đóng góp nhiều genre; tổng genre counts có thể lớn hơn tổng play. Play gồm cả resume. Tổng watchDuration={fmt(result['total_watch_seconds'])} giây; all_events gồm view/play=0, positive watch segments có {fmt(positive['count'])} dòng. Median là {all_d['median']}s và {positive['median']}s. DAU 1.000/ngày phản ánh synthetic cohort, không phải người dùng thật.

## 9. Feature engineering

{fmt(features['users'])} rows và {fmt(features['unique_users'])} unique users; duplicate userId=0. Cả 10 feature có union null/NaN/Infinity=0, nên từng loại lỗi đều 0. Independent SQL tái tạo features có 0 mismatch. Completion rate trong [0,1]; fixture kiểm denominator zero trả 0 và defined=false.

Dataset giữ 10 feature: playCount, completeCount, totalWatchDuration, avgWatchDuration, distinctMovies, distinctGenres, sessionCount, completionRate, activeDays, eventCount; thêm userId và 3 cột giải thích playedSessionCount/completedSessionCount/completionRateDefined. Avg duration là mean positive segment; completion rate dùng distinct (runId,sessionId), không chia completeCount cho playCount có resume.

{variance_table}

Selected ML features: `{', '.join(m['feature_columns'])}`. activeDays đo lại variance=0. eventCount được kiểm lại với **{v['event_count_redundancy_bad_users']} user vi phạm** identity eventCount=sessionCount+2*playCount. Chỉ bỏ khỏi ML vector, vẫn giữ trong feature dataset/profile. Không loại vì Tuần 2 từng loại. Pearson trên các feature được chọn: {corr_text}. Các tương quan còn lại là hạn chế khi diễn giải khoảng cách.

## 10. K-Means

VectorAssembler → fitted StandardScaler(withMean=true, withStd=true) → pyspark.ml.clustering.KMeans. Fit mới K=2..6, seed={m['seed']}, maxIter={m['max_iter']}. Evaluator silhouette/squaredEuclidean, training Euclidean; không sklearn.

{k_table}

## 11. Final model

Best K=**{m['best_k']}**, Silhouette=**{m['silhouette']}**, seed={m['seed']}, maxIter={m['max_iter']}. Score gap tới runner-up={m['score_gap_to_runner_up']}. Chọn score cao nhất; chỉ ưu tiên K nhỏ khi score bằng nhau chính xác. K/Silhouette trùng Tuần 2 nhưng được fit/đo mới; baseline không làm điều kiện ép PASS.

Features: `{', '.join(m['feature_columns'])}`.

Model: `{m['model_uri']}`. Lưu assembler + fitted scaler + selected model. Reload độc lập transform {v['model_reload']['actual_rows']} users, 0 mismatch/duplicate keys; prepared vectors khớp saved scaler, 0 mismatch.

## 12. Cluster profiles

{profile_a}

{profile_b}

{interpretation}

Cluster sizes={m['cluster_sizes']}, tương ứng {', '.join(f"{100*x['userCount']/features['users']:.1f}%" for x in profiles)}. Host verifier tính lại cả 10 profile means từ assignments; tổng users khớp 1.000. Giữ nhãn Cluster 0/1 trung tính, không gán nhãn VIP/trung thành hay suy thành hành vi người thật.

## 13. Evaluation / limitations

K-Means phân cụm không giám sát: khởi tạo K centroid (Spark hỗ trợ k-means||), gán vector vào tâm gần nhất, tính lại tâm bằng trung bình các vector trong nhóm, lặp đến điều kiện dừng hoặc maxIter. Mục tiêu là sum_i ||x_i-centroid[c_i]||^2. [Apache Spark clustering](https://spark.apache.org/docs/3.5.7/ml-clustering.html#k-means).

Bài toán cần grouping user bằng numeric features và không có label. Spark MLlib tích hợp DataFrame/pipeline; profile giúp diễn giải theo đơn vị gốc. StandardScaler hạn chế feature thang đo lớn chi phối khoảng cách. [StandardScaler](https://spark.apache.org/docs/3.5.7/ml-features.html#standardscaler).

Silhouette đo gắn kết/phân tách theo khoảng cách đã chọn. So đủ K, sizes, training cost và profiles; không gọi score là accuracy. K=2 có score cao nhất; tăng K giảm cost nhưng silhouette thấp hơn, có nhóm nhỏ ở K cao. [ClusteringEvaluator](https://spark.apache.org/docs/3.5.7/api/python/reference/api/pyspark.ml.evaluation.ClusteringEvaluator.html).

Giới hạn: logs/user/movie runtime synthetic; feature set hạn chế và tương quan; cần chọn K; nhạy scaling/outliers; Euclidean geometry; cluster IDs không tự có semantic; evaluation trên cohort fit, chưa chứng minh ổn định ngoài cohort; local[2] một host, HDFS một DataNode/replication=1; Silhouette không là tiêu chí duy nhất. K-Means không phải recommender. Tham khảo docs nhánh 3.5.7; runtime giữ nguyên 3.5.1.

## 14. Final Dashboard outputs

Bảng ghi base path. Với ba format, đọc /parquet, /csv hoặc /json bên dưới base; exact URI từng format có trong handoff.json/output_manifest.json.

{output_table}

52 artifacts gồm 41 dataset format variants, 10 report documents và 1 model; đều được đọc lại, gồm model reload. 36 Dashboard variants thuộc 12 bảng nhỏ. Local JSON là array; HDFS JSON là JSON Lines; CSV header UTF-8, nested array encode JSON. Dataset lớn giữ Parquet/repartition 8; chỉ coalesce(1)/collect exports nhỏ <=5.000 rows. Không collect/toPandas 1M events.

## 15. Raw preservation

{table(['Metric','Before','After'],[['Files',raw['files_before'],raw['files_after']],['Bytes',raw['bytes_before'],raw['bytes_after']],['Unchanged files',raw['unchanged_files'],raw['unchanged_files']]])}

Missing=0, extra=0, size/hash mismatch=0. Hai phép full HDFS byte verification trước/sau khớp; nếu khác runner FAIL. Không upload/overwrite raw. {len(old)} file lịch sử local còn nguyên; source TV1/schema/config cũng khớp hash.

## 16. TV3 handoff

Đã phát hành [week3_tv2_handoff.md](week3_tv2_handoff.md) và [handoff.json](../{prefix}/handoff.json). Exact final run `{run}`; exact results root `{r}`. TV3 dùng đúng outputs trong handoff, không trộn Week 2/blocked/FAIL/recovery. Task này không đổi Dashboard UI/data-source selection.

## 17. Evidence

[Evidence folder](../{prefix}/) gồm context/source manifest, input QA/counts, cleaning/transformation/join/statistics, features, K search/model/profiles, output manifest, independent verification, result verifier, raw-before/after, preservation, tests, source snapshots, commands/logs và handoff. Timestamps UTC/argv/cwd/exit/stdout/stderr đầy đủ. Diagnostics là integration test chỉ đọc, không thay kết quả final.

## 18. Screenshot checklist

[15 ảnh cần chụp](week3_tv2_screenshots.md) đã trỏ đúng final run. Chưa capture ảnh mới; không dựng screenshot giả.

## 19. Demo readiness

[Demo 4–6 phút](week3_tv2_demo.md) sẵn sàng với số liệu mới. Full job chuẩn bị trước demo; trình bày bằng reports/commands cùng run, không demo sâu lại TV1.

## 20. Tests

{command_table}

Host tests {tests['tests']}/{tests['tests']}, TV2/regression {tests['tv2_tests']}/{tests['tv2_tests']}, Spark fixtures 4/4 PASS. HDFS QA 23 nhóm lỗi=0; independent checks {len(v['checks'])}/{len(v['checks'])}; result verifier {len(result['checks'])}/{len(result['checks'])}. Git diff --check được lưu thêm sau cập nhật docs.

## 21. Remaining issues

**NONE về runtime và bàn giao dữ liệu.** Người dùng còn cần capture ảnh theo checklist và diễn tập bài nói. Không sửa TV1/raw, rerun Flume/regenerate data, ALS/recommender, TV3/UI hoặc commit/push.

## 22. Final decision

- TV2 Week 3 complete? **YES**.
- Preprocessing final? **YES**.
- Analysis final? **YES**.
- K-Means final? **YES**.
- Raw preserved? **YES**.
- Dashboard outputs final? **YES**.
- TV3 handoff released? **YES**.
- TV3 can proceed? **YES**, dùng đúng `{run}`.
'''
# Publish only after all guards above have passed.
new_json(folder/'handoff.json',handoff)
write_doc('week3_tv2_processing_report.md',report)
handoff_md=f'''# TV2 Tuần 3 — final handoff cho TV3/Cowork

**PASS — final run `{run}`.** Ngày 15/10/2026. [Machine-readable handoff](../{prefix}/handoff.json) là danh sách chọn dữ liệu chính xác; [report](week3_tv2_processing_report.md) có validation đầy đủ.

## Identity và input

- Final TV2 run: `{run}`.
- TV1 Flume: `{c['flume_run_id']}`.
- TV1 HDFS/project: `{c['hdfs_run_id']}` / `{c['project']}`.
- Movies URI: `{s['movies_uri']}`.
- Logs URI: `{s['logs_uri']}`.
- Processed root: `{p}`.
- Results root: `{r}`.

9.742 movies; 1M events; raw 255 files/343.872.495 byte; 255/255 size/SHA256 unchanged. DistributedFileSystem, local_fallback=false.

## Model, selected features và cluster profiles

Best K={m['best_k']}; Silhouette={m['silhouette']}; seed={m['seed']}; maxIter={m['max_iter']}. Selected vector theo thứ tự: `{', '.join(m['feature_columns'])}`. activeDays variance=0; eventCount exact redundancy được đo lại, chỉ loại khỏi ML vector. Dataset/profile giữ đủ 10 features.

Model: `{m['model_uri']}`, gồm assembler/scaler/selected model; reload tái tạo đúng 1.000 assignments.

{profile_a}

{profile_b}

{interpretation}

## Dataset list, formats và row counts

{output_table}

Ba format nằm trong subdirectory parquet/csv/json của base; exact URI/rows/schema/local hash của từng format nằm trong handoff.json. TV3 **phải dùng** 7 stats và 5 bảng kmeans được liệt kê trong dashboard_outputs của đúng run này. Local exports: `../{prefix}/dashboard/`. Local JSON là array; HDFS JSON là JSON Lines; CSV header UTF-8, nested arrays encode JSON. Không hard-code part filenames; đọc đúng format directory, bỏ _SUCCESS.

Không dùng generated input, fixtures, raw event streams làm UI input hoặc results/model khác run. Không trộn `tv2-4ed70c10cd84`, `tv2-0523e144a808`, `tv2-63c6eba4e8e4`, `tv2-5c5f819cacaa`, `tv2-56569b78b4e1`. Chúng chỉ là lịch sử/baseline/attempt khác, không phải final dataset mới.

## Timezone, units và limitation

Source UTC Z, session UTC, calendar Asia/Ho_Chi_Minh. watchDuration là giây incremental segment; minutes là derived. avgWatchDuration là mean positive segment. Completion rate dùng distinct completed sessions / sessions có play; denominator zero=>0 và defined=false. Genres multi-label. Logs/users/movie runtime synthetic; không suy thành hành vi người thật. Cluster IDs trung tính, không recommendation.

## Commands verify

Từ repo root, chọn Python thật theo run guide và đặt $py:

```powershell
$run = '{run}'
Get-Content "evidence/week3-tv2/$run/handoff.json" -Raw
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
& $py -B scripts/verify_tv2_results.py --run-id $run --evidence-root evidence/week3-tv2 --report "evidence/week3-tv2/$run/reverify-$stamp.json"
$env:HDFS_RUN_ID = '{c['hdfs_run_id']}'
docker compose -f compose.hdfs.yaml -p {c['project']} exec -T namenode hdfs dfs -ls {p.replace('hdfs://namenode:9000','')}
docker compose -f compose.hdfs.yaml -p {c['project']} exec -T namenode hdfs dfs -ls {r.replace('hdfs://namenode:9000','')}
```

HDFS formats/values/7 analyses/model reload: runtime-verification.json. Cross-export checks: result-verification.json. Raw preservation: raw-preservation.json. Đây là bàn giao dữ liệu; task không đổi Dashboard UI/selection.
'''
write_doc('week3_tv2_handoff.md',handoff_md,new=True)
write_doc('week3_tv2_demo.md',f'''# TV2 Tuần 3 — demo 4–6 phút

Final **{run}**, PASS. Mở [handoff](week3_tv2_handoff.md) và `../{prefix}/`. Full job đã chạy thật trước buổi demo; trình bày reports/commands cùng run. Không demo sâu lại Flume/HDFS của TV1.

| Thời gian | Nội dung | Evidence |
|---|---|---|
| 0:00–0:35 | HDFS URI, 9742 movies/1M events, synthetic limitation | run_context/input_counts/spark_environment |
| 0:35–1:00 | Schema, movieId bigint, explicit validation | input-hdfs-qa |
| 1:00–1:35 | Raw/clean/joined=1M, rejected=0, counting semantics | cleaning_summary/join_summary |
| 1:35–2:00 | UTC/local calendar, seconds/minutes, genres | transformation_summary/runtime-verification |
| 2:00–2:45 | Top movie {movie['movieId']}: {movie['playCount']} play; {genre['genre']}: {genre['playCount']}; DAU/hour/action và cross-check | statistics_summary/dashboard |
| 2:45–3:20 | 1000 users/10 features, variance/redundancy | feature_validation/model_metadata |
| 3:20–4:05 | Assembler/scaler, K=2..6, final K={m['best_k']}, silhouette={m['silhouette']:.6f} | kmeans_search/selected_k |
| 4:05–4:45 | Sizes {m['cluster_sizes']}, raw-unit profiles, neutral labels | cluster_profiles |
| 4:45–5:30 | Reload 1000 assignments, raw 255/255 unchanged, exact exports | runtime-verification/raw-preservation/handoff |

Kết thúc với giới hạn synthetic/local[2]/correlated features/internal Silhouette. Không gọi K-Means là recommender. [Run guide](week3_tv2_run_guide.md) có lệnh kiểm tra; mọi report path phải mới.
''')
shots=['Spark đọc đúng HDFS URI, DistributedFileSystem và local_fallback=false','Input schema/DataFrame, movieId bigint','Cleaning summary raw/parsed/clean=1M, rejected=0','Transformation UTC/local columns và duration units','Join pre-join/orphan/joined/clean identity','Top movies by play','Top genres và multi-label counting','DAU theo local date','Hourly activity theo Asia/Ho_Chi_Minh','Action distribution và tổng 100%','1000 user feature rows, QA, variance/exclusions','K=2..6: Silhouette/sizes/training cost','Final K/model metadata/seed/maxIter','Cluster profiles định lượng, neutral labels','HDFS processed/results đúng run, final PASS và raw preservation']
write_doc('week3_tv2_screenshots.md',f'# TV2 Tuần 3 — checklist ảnh final\n\nRun **{run}**. Chưa capture ảnh mới. Người dùng chụp terminal/DataFrame/report thật và ghi run ID trong caption.\n\n'+'\n'.join(f'- [ ] {i}. {text}.' for i,text in enumerate(shots,1))+f'\n\nNguồn: `../{prefix}/`, [report](week3_tv2_processing_report.md), [handoff](week3_tv2_handoff.md). Không dùng ảnh run cũ làm ảnh final hoặc dựng/sửa số liệu trong screenshot.\n')
write_doc('week3_tv2_run_guide.md',f'''# TV2 Tuần 3 — final run và kiểm tra

Final **{run}**, PASS. Baseline `{c['flume_run_id']}` / `{c['hdfs_run_id']}`; project `{c['project']}`. Xem [handoff](week3_tv2_handoff.md), [report](week3_tv2_processing_report.md).

Python >=3.10 thật trên host và Docker Linux containers. Đặt TV1_PYTHON nếu Python chưa ở PATH; không copy đường dẫn executable cá nhân từ docs cũ.

```powershell
$py = $env:TV1_PYTHON
if (-not $py) {{
  $py = (Get-Command python -All | Where-Object Source -NotMatch 'WindowsApps' | Select-Object -First 1).Source
}}
if (-not $py) {{ throw 'Cần Python thật; đặt TV1_PYTHON.' }}
$run = '{run}'
Get-Content "evidence/week3-tv2/$run/handoff.json" -Raw
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
& $py -B scripts/verify_tv2_results.py --run-id $run --evidence-root evidence/week3-tv2 --report "evidence/week3-tv2/$run/reverify-$stamp.json"
```

Nếu cần chạy toàn bộ lần mới sau khi kiểm tài nguyên/không có job khác, runner tạo UUID/namespace mới, không resume/overwrite final hoặc blocked/FAIL attempts:

```powershell
& $py -B -m unittest discover -s tests -p 'test_tv2*.py' -v
& $py -B scripts/run_tv2.py --hdfs-context evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json --evidence-root evidence/week3-tv2 --seed 42 --driver-memory 1536m
```

Runner chạy raw-before/HDFS QA, unit/Spark fixtures, pipeline, independent verification và raw-after. Sau runner PASS chạy host result verifier và chỉ phát hành handoff khi nghiệm thu đủ. Validator tính lại 7 analysis/features từ joined HDFS, kiểm formats/schema/count/values, reload model/scaler. Không fallback local, start/format cluster hoặc upload raw. Context paths dùng repo-relative với dấu / để chạy trong Linux container.

Mọi report path phải mới. Không trộn Week 2/recovery/blocked/FAIL outputs; không rerun Flume/regenerate data hay sửa Dashboard selection/UI. Các receipts final được niêm phong bằng delivery-manifest.json; chỉ append report mới khi kiểm lại, không sửa receipts đã đo.
''')
write_doc('week3_tv2_handoff_contract.md',f'''# Hợp đồng bàn giao TV2 Tuần 3

Đã áp dụng cho final **{run}**, PASS. Hợp đồng chuẩn bị trước runtime được giữ ở `../{prefix}/report-preparation-history/week3_tv2_handoff_contract.md`.

Đã phát hành [Markdown](week3_tv2_handoff.md) và [machine-readable JSON](../{prefix}/handoff.json): identity/input/roots, K/Silhouette/seed/features/profiles, 36 Dashboard format variants với exact URI/rows/schema/local hash, timezone/units/synthetic limitation, commands verify và danh sách run không được trộn.

Điều kiện phát hành: runner/pipeline/input QA/fixtures/7 analysis/output verification/model reload/result verifier/raw preservation/historical preservation đều PASS. Chỉ chọn outputs được liệt kê trong handoff của đúng run.
''')
base_meta=json.loads((root/'evidence/week2-tv2/tv2-4ed70c10cd84/model_metadata.json').read_text())
new_json(folder/'baseline-comparison.json',{'status':'COMPARISON_ONLY','historical_run':'tv2-4ed70c10cd84','new_run':run,'historical_best_k':base_meta['best_k'],'historical_silhouette':base_meta['silhouette'],'new_best_k':m['best_k'],'new_silhouette':m['silhouette'],'silhouette_delta':m['silhouette']-base_meta['silhouette'],'not_used_to_force_acceptance':True})
logs=folder/'logs';logs.mkdir(exist_ok=True);new_json(logs/'index.json',{'source':'Original command stdout/stderr, not reconstructed logs','commands':commands})
ledger=Ledger(folder,{'HDFS_RUN_ID':c['hdfs_run_id']});ledger.command(['git','diff','--check'],'git-diff-check-final')
for path in (root/'docs').glob('week3_tv2*.md'):
 text=path.read_text(encoding='utf-8');assert '\ufffd' not in text and 'NOT_RUN' not in text,path.name
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith('http'):continue
  rel=target.split('#')[0]
  if rel:assert (path.parent/rel).exists(),(path,target)
required=['tv2_run_id','hdfs_input','processed_root','results_root','best_k','silhouette','feature_columns','cluster_profiles','dashboard_outputs','timezone','duration_units','synthetic','validation_receipts']
assert all(name in handoff for name in required)
final={'status':'PASS','run_id':run,'checked_at_utc':utcnow(),'checks':{name:True for name in ['runner','pipeline','input_hdfs_qa','host_tests','spark_fixtures','seven_independent_analyses','output_schemas_formats_values','model_scaler_reload','result_verifier','raw_preserved','historical_files_preserved','tv1_preserved','documentation_links','handoff_contract','git_diff_check']},'input':handoff['hdfs_input'],'best_k':m['best_k'],'silhouette':m['silhouette'],'cluster_sizes':m['cluster_sizes'],'host_tests':tests['tests'],'tv2_tests':tests['tv2_tests'],'spark_fixtures':4,'artifacts':len(manifest['artifacts']),'dashboard_format_variants':len(outputs),'historical_files_checked':len(old),'handoff':prefix+'/handoff.json','tv3_can_proceed':True,'safety':{'no_flume_rerun':True,'no_regeneration':True,'raw_unmodified':True,'old_runs_unmodified':True,'tv1_unchanged':True,'no_dashboard_ui_or_selection_changes':True,'no_als_recommender':True,'no_commit_push':True}}
new_json(folder/'final-acceptance.json',final)
selected=[path for path in folder.rglob('*') if path.is_file()]+list((root/'docs').glob('week3_tv2*.md'))
new_json(folder/'delivery-manifest.json',{'created_at_utc':utcnow(),'run_id':run,'scope':[prefix,'docs/week3_tv2*.md'],'exclusions':['manifest itself and later delivery-verification receipt','HDFS blocks; verified via runtime receipts'],'files':{path.relative_to(root).as_posix():{'bytes':path.stat().st_size,'sha256':sha256(path)} for path in sorted(selected)}})
verified=verify(folder/'delivery-manifest.json');new_json(folder/'delivery-verification.json',verified);assert verified['status']=='PASS'
print(json.dumps({'status':'PASS','run':run,'handoff':prefix+'/handoff.json','report':'docs/week3_tv2_processing_report.md','delivery_files':verified['files_checked'],'dashboard_variants':len(outputs),'raw_unchanged':raw['unchanged_files'],'final_decisions':'ALL YES'},ensure_ascii=True))
