# WEEK 3 TV2 FINAL RUNTIME REPORT

TV2: **Bùi Trung Đức**. Nghiệm thu ngày **15/10/2026 (Asia/Saigon)**. Số liệu lấy từ run mới `tv2-aae83326c1ab`; JSON giữ precision đầy đủ. Bằng chứng: [run_status](../evidence/week3-tv2/tv2-aae83326c1ab/run_status.json), [independent verification](../evidence/week3-tv2/tv2-aae83326c1ab/runtime-verification.json), [result verifier](../evidence/week3-tv2/tv2-aae83326c1ab/result-verification.json).

## 1. Overall status

**PASS.** Full runtime, tests, independent recomputation cả 7 analysis, format/schema/value read-back, model/scaler reload, raw preservation và historical preservation đều đạt. Không dùng output Tuần 2 hoặc các attempt trước làm kết quả cuối.

## 2. Run identity

- TV2 Week 3 run: `tv2-aae83326c1ab`.
- Flume run: `run-f63c810e9d8d`.
- HDFS run/project: `hdfs-124cbf30bda7` / `movie-hdfs-124cbf30bda7`.
- Movies: `hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-124cbf30bda7/movies.csv`.
- Logs: `hdfs://namenode:9000/movie-log/raw/user_logs/run-f63c810e9d8d/hdfs-124cbf30bda7`.
- Processed root: `hdfs://namenode:9000/movie-log/processed/tv2/tv2-aae83326c1ab`.
- Results root: `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab`.
- Pipeline: 2026-10-15T06:51:36.881562+00:00 tới 2026-10-15T06:55:43.712288+00:00 (UTC).
- Spark 3.5.1, Java 11.0.22, Hadoop client 3.3.4, local[2], driver 1536m.

Lịch sử được giữ nguyên: `tv2-0523e144a808` BLOCKED; `tv2-63c6eba4e8e4` FAIL tại fixture vì import kéo theo Pandas; `tv2-5c5f819cacaa` FAIL khi mở validator vì đường dẫn Windows. Đã bỏ dependency ngoài ý muốn, chuẩn hóa đường dẫn, thêm regression test, thử validator chỉ đọc trong diagnostics riêng rồi chạy lại toàn bộ run mới. Không sửa các attempt cũ thành PASS. Tài liệu chuẩn bị cũ nằm trong report-preparation-history/.

## 3. Input verification

- Movies: 9,742; events / unique eventId: 1,000,000 / 1,000,000.
- 1 movie file + 254 Flume Sink log files = 255 raw files; 343,872,495 byte.
- Filesystem: `org.apache.hadoop.hdfs.DistributedFileSystem`; actual URI `hdfs://namenode:9000`; local_fallback=false.
- Raw-before: toàn bộ size/SHA256 khớp manifest; missing/extra=0.
- HDFS QA: 23 nhóm, tất cả lỗi=0; đọc đúng 254 log source files.

## 4. Tests before pipeline

Unit/regression TV2 13/13 PASS; Spark fixtures 4/4 PASS. Tests chạy lại trong run mới trước full pipeline. Fixture mới phát hiện missing row, duplicate key và wrong value. HDFS byte/schema/count QA cũng chạy mới; không suy PASS từ receipt cũ.

## 5. Preprocessing

| Metric | Count |
| --- | --- |
| raw | 1,000,000 |
| parsed | 1,000,000 |
| malformed | 0 |
| required_null | 0 |
| exact_duplicates | 0 |
| conflicting_eventId groups | 0 |
| conflicting rows | 0 |
| duplicate removals | 0 |
| invalid_action | 0 |
| invalid_timestamp | 0 |
| invalid_watchDuration | 0 |
| invalid_integer | 0 |
| invalid_provenance | 0 |
| orphan | 0 |
| rejected | 0 |
| pre_join_clean | 1,000,000 |
| clean | 1,000,000 |

Basic-rule categories độc lập trên raw và có thể overlap; steps là các lượt loại tuần tự không overlap. Tổng removed=0, khớp rejected. Exact duplicate giữ một payload; conflicting ID loại tất cả biến thể; orphan quarantine. Rejected giữ sourceFile/rawJson/reason. Input sạch nên không tạo lỗi giả.

## 6. Transformation

Đủ eventTimestamp, eventLocalTimestamp, date, hour, dayOfWeek, watchDurationMinutes, genresArray. Source UTC Z; session UTC; calendar Asia/Ho_Chi_Minh. dayOfWeek: 1=Sunday, 7=Saturday. watchDuration giữ giây incremental segment; minutes=seconds/60. Genres split |, trim, distinct, giữ (no genres listed). Independent verifier phát hiện **0 dòng sai** trên toàn joined dataset.

## 7. Join

movieId hai phía bigint; metadata movieId unique; inner join. pre_join_clean=1,000,000; orphan=0; joined=1,000,000; clean=1,000,000.

pre_join_clean_log_count = joined_count + orphan_count và clean_log_count = joined_count đều đạt. Independent full keyed comparison giữ nguyên payload clean: 1,000,000 rows, 0 mismatch và 0 duplicate keys. Không row multiplication.

## 8. Analysis validation

| Analysis | Result | Cross-check | Status |
| --- | --- | --- | --- |
| Top movies | 20 rows; Catch That Kid (2004): 17,064 play | Independent SQL filter/group/order/top 20 | PASS |
| Top genres | 20 rows; Comedy: 144,882 | Independent explode/count, multi-label | PASS |
| DAU | 30 dates; DAU=1000 to 1000 users/day | Distinct users by local date | PASS |
| Hourly | 24 hours; sum=1,000,000; peak=23 | Local-hour event/play/distinct users | PASS |
| Action distribution | 5 actions; total 1,000,000 and 100% | Independent counts and percentages | PASS |
| Watch duration | all mean=1458.785357s; positive mean=4186.210039s | Aggregates plus approximate median rank bounds | PASS |
| User-movie-time | 72 rows measured | Independent counts/distinct users/dynamic top-3 ranking | PASS |

SQL độc lập với hàm aggregation production, đọc joined Parquet HDFS cùng run và so keys/counts/tất cả values. Float dùng tolerance nhỏ. Approximate median kiểm bằng rank bounds với accuracy=10000; không ép kết quả giữa các partition phải bằng nhau tuyệt đối. Cả 7 nhóm có 0 mismatch.

Một play của phim đa thể loại có thể đóng góp nhiều genre; tổng genre counts có thể lớn hơn tổng play. Play gồm cả resume. Tổng watchDuration=1,458,785,357 giây; all_events gồm view/play=0, positive watch segments có 348,474 dòng. Median là 0.0s và 3833.0s. DAU 1.000/ngày phản ánh synthetic cohort, không phải người dùng thật.

## 9. Feature engineering

1,000 rows và 1,000 unique users; duplicate userId=0. Cả 10 feature có union null/NaN/Infinity=0, nên từng loại lỗi đều 0. Independent SQL tái tạo features có 0 mismatch. Completion rate trong [0,1]; fixture kiểm denominator zero trả 0 và defined=false.

Dataset giữ 10 feature: playCount, completeCount, totalWatchDuration, avgWatchDuration, distinctMovies, distinctGenres, sessionCount, completionRate, activeDays, eventCount; thêm userId và 3 cột giải thích playedSessionCount/completedSessionCount/completionRateDefined. Avg duration là mean positive segment; completion rate dùng distinct (runId,sessionId), không chia completeCount cho playCount có resume.

| Feature | Variance measured | ML selection |
| --- | --- | --- |
| playCount | 3892.001325325325 | SELECTED |
| completeCount | 123.44379479479471 | SELECTED |
| totalWatchDuration | 12401886805.673231 | SELECTED |
| avgWatchDuration | 141364.01119699475 | SELECTED |
| distinctMovies | 4016.9783343343333 | SELECTED |
| distinctGenres | 0.335791791791792 | SELECTED |
| sessionCount | 8975.340636636636 | SELECTED |
| completionRate | 0.0034972103341199268 | SELECTED |
| activeDays | 0.0 | zero_variance |
| eventCount | 46756.66466466464 | exactly sessionCount + 2*playCount; retain in dataset, exclude redundant ML dimension |

Selected ML features: `playCount, completeCount, totalWatchDuration, avgWatchDuration, distinctMovies, distinctGenres, sessionCount, completionRate`. activeDays đo lại variance=0. eventCount được kiểm lại với **0 user vi phạm** identity eventCount=sessionCount+2*playCount. Chỉ bỏ khỏi ML vector, vẫn giữ trong feature dataset/profile. Không loại vì Tuần 2 từng loại. Pearson trên các feature được chọn: distinctMovies/sessionCount: r=0.991245; playCount/distinctMovies: r=0.949817; playCount/avgWatchDuration: r=-0.942606. Các tương quan còn lại là hạn chế khi diễn giải khoảng cách.

## 10. K-Means

VectorAssembler → fitted StandardScaler(withMean=true, withStd=true) → pyspark.ml.clustering.KMeans. Fit mới K=2..6, seed=42, maxIter=50. Evaluator silhouette/squaredEuclidean, training Euclidean; không sklearn.

| K | Silhouette | Cluster sizes | Training cost |
| --- | --- | --- | --- |
| 2 | 0.670756387190543 | [237, 763] | 4404.271452 |
| 3 | 0.572440045122613 | [634, 316, 50] | 3237.212599 |
| 4 | 0.514174155228576 | [11, 307, 588, 94] | 2713.561620 |
| 5 | 0.469237495967179 | [252, 265, 27, 142, 314] | 2169.264233 |
| 6 | 0.466004696998637 | [252, 42, 6, 254, 142, 304] | 1878.776954 |

## 11. Final model

Best K=**2**, Silhouette=**0.6707563871905433**, seed=42, maxIter=50. Score gap tới runner-up=0.09831634206793005. Chọn score cao nhất; chỉ ưu tiên K nhỏ khi score bằng nhau chính xác. K/Silhouette trùng Tuần 2 nhưng được fit/đo mới; baseline không làm điều kiện ép PASS.

Features: `playCount, completeCount, totalWatchDuration, avgWatchDuration, distinctMovies, distinctGenres, sessionCount, completionRate`.

Model: `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/kmeans/model`. Lưu assembler + fitted scaler + selected model. Reload độc lập transform 1000 users, 0 mismatch/duplicate keys; prepared vectors khớp saved scaler, 0 mismatch.

## 12. Cluster profiles

| Cluster | Users | avgPlayCount | avgCompleteCount | avgSessionCount | avgDistinctMovies | avgDistinctGenres |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 237 | 436.527 | 154.203 | 417.000 | 317.084 | 19.772 |
| 1 | 763 | 321.123 | 138.088 | 267.658 | 213.092 | 19.562 |

| Cluster | avgTotalWatchDuration (s) | avgWatchDuration (s) | avgCompletionRate | avgActiveDays | avgEventCount |
| --- | --- | --- | --- | --- | --- |
| 0 | 1,612,246.895 | 3,743.761 | 0.486215 | 30.000 | 1,290.055 |
| 1 | 1,411,117.750 | 4,406.714 | 0.582218 | 30.000 | 909.904 |

Cluster 0 (237 users) có trung bình 436.527 play và 417.000 session/user, cao hơn Cluster 1 (321.123 play, 267.658 session). Tổng giây xem trung bình là 1612246.895 so với 1411117.750; nhưng đoạn xem dương trung bình ngắn hơn (3743.761s so với 4406.714s), completion rate thấp hơn (48.621% so với 58.222%).

Cluster sizes=[237, 763], tương ứng 23.7%, 76.3%. Host verifier tính lại cả 10 profile means từ assignments; tổng users khớp 1.000. Giữ nhãn Cluster 0/1 trung tính, không gán nhãn VIP/trung thành hay suy thành hành vi người thật.

## 13. Evaluation / limitations

K-Means phân cụm không giám sát: khởi tạo K centroid (Spark hỗ trợ k-means||), gán vector vào tâm gần nhất, tính lại tâm bằng trung bình các vector trong nhóm, lặp đến điều kiện dừng hoặc maxIter. Mục tiêu là sum_i ||x_i-centroid[c_i]||^2. [Apache Spark clustering](https://spark.apache.org/docs/3.5.7/ml-clustering.html#k-means).

Bài toán cần grouping user bằng numeric features và không có label. Spark MLlib tích hợp DataFrame/pipeline; profile giúp diễn giải theo đơn vị gốc. StandardScaler hạn chế feature thang đo lớn chi phối khoảng cách. [StandardScaler](https://spark.apache.org/docs/3.5.7/ml-features.html#standardscaler).

Silhouette đo gắn kết/phân tách theo khoảng cách đã chọn. So đủ K, sizes, training cost và profiles; không gọi score là accuracy. K=2 có score cao nhất; tăng K giảm cost nhưng silhouette thấp hơn, có nhóm nhỏ ở K cao. [ClusteringEvaluator](https://spark.apache.org/docs/3.5.7/api/python/reference/api/pyspark.ml.evaluation.ClusteringEvaluator.html).

Giới hạn: logs/user/movie runtime synthetic; feature set hạn chế và tương quan; cần chọn K; nhạy scaling/outliers; Euclidean geometry; cluster IDs không tự có semantic; evaluation trên cohort fit, chưa chứng minh ổn định ngoài cohort; local[2] một host, HDFS một DataNode/replication=1; Silhouette không là tiêu chí duy nhất. K-Means không phải recommender. Tham khảo docs nhánh 3.5.7; runtime giữ nguyên 3.5.1.

## 14. Final Dashboard outputs

Bảng ghi base path. Với ba format, đọc /parquet, /csv hoặc /json bên dưới base; exact URI từng format có trong handoff.json/output_manifest.json.

| Dataset | Format | HDFS base path | Rows |
| --- | --- | --- | --- |
| cleaned_logs | parquet | `hdfs://namenode:9000/movie-log/processed/tv2/tv2-aae83326c1ab/cleaned_logs` | 1,000,000 |
| rejected_logs | parquet | `hdfs://namenode:9000/movie-log/processed/tv2/tv2-aae83326c1ab/rejected_logs` | 0 |
| joined_events | parquet | `hdfs://namenode:9000/movie-log/processed/tv2/tv2-aae83326c1ab/joined_events` | 1,000,000 |
| stats/top_movies_by_play | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/stats/top_movies_by_play` | 20 |
| stats/top_genres | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/stats/top_genres` | 20 |
| stats/daily_active_users | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/stats/daily_active_users` | 30 |
| stats/hourly_activity | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/stats/hourly_activity` | 24 |
| stats/action_distribution | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/stats/action_distribution` | 5 |
| stats/watch_duration_summary | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/stats/watch_duration_summary` | 2 |
| stats/user_movie_time | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/stats/user_movie_time` | 72 |
| user_features | parquet | `hdfs://namenode:9000/movie-log/processed/tv2/tv2-aae83326c1ab/user_features` | 1,000 |
| kmeans/features_prepared | parquet | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/kmeans/features_prepared` | 1,000 |
| kmeans/user_features | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/kmeans/user_features` | 1,000 |
| kmeans/k_search | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/kmeans/k_search` | 5 |
| kmeans/assignments | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/kmeans/assignments` | 1,000 |
| kmeans/cluster_profiles | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/kmeans/cluster_profiles` | 2 |
| kmeans/model | spark_ml_pipeline | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/kmeans/model` | 1 PipelineModel; 1,000 assignments verified |
| kmeans/model_metadata | parquet, csv, json | `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/kmeans/model_metadata` | 1 |

52 artifacts gồm 41 dataset format variants, 10 report documents và 1 model; đều được đọc lại, gồm model reload. 36 Dashboard variants thuộc 12 bảng nhỏ. Local JSON là array; HDFS JSON là JSON Lines; CSV header UTF-8, nested array encode JSON. Dataset lớn giữ Parquet/repartition 8; chỉ coalesce(1)/collect exports nhỏ <=5.000 rows. Không collect/toPandas 1M events.

## 15. Raw preservation

| Metric | Before | After |
| --- | --- | --- |
| Files | 255 | 255 |
| Bytes | 343872495 | 343872495 |
| Unchanged files | 255 | 255 |

Missing=0, extra=0, size/hash mismatch=0. Hai phép full HDFS byte verification trước/sau khớp; nếu khác runner FAIL. Không upload/overwrite raw. 459 file lịch sử local còn nguyên; source TV1/schema/config cũng khớp hash.

## 16. TV3 handoff

Đã phát hành [week3_tv2_handoff.md](week3_tv2_handoff.md) và [handoff.json](../evidence/week3-tv2/tv2-aae83326c1ab/handoff.json). Exact final run `tv2-aae83326c1ab`; exact results root `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab`. TV3 dùng đúng outputs trong handoff, không trộn Week 2/blocked/FAIL/recovery. Task này không đổi Dashboard UI/data-source selection.

## 17. Evidence

[Evidence folder](../evidence/week3-tv2/tv2-aae83326c1ab/) gồm context/source manifest, input QA/counts, cleaning/transformation/join/statistics, features, K search/model/profiles, output manifest, independent verification, result verifier, raw-before/after, preservation, tests, source snapshots, commands/logs và handoff. Timestamps UTC/argv/cwd/exit/stdout/stderr đầy đủ. Diagnostics là integration test chỉ đọc, không thay kết quả final.

## 18. Screenshot checklist

[15 ảnh cần chụp](week3_tv2_screenshots.md) đã trỏ đúng final run. Chưa capture ảnh mới; không dựng screenshot giả.

## 19. Demo readiness

[Demo 4–6 phút](week3_tv2_demo.md) sẵn sàng với số liệu mới. Full job chuẩn bị trước demo; trình bày bằng reports/commands cùng run, không demo sâu lại TV1.

## 20. Tests

| Command / step | Exit code | Result |
| --- | --- | --- |
| all-host-tests-final-e8f95540 | 0 | PASS |
| compose-tv2-config-13c539fc | 0 | PASS |
| docker-info-45bac107 | 0 | PASS |
| docker-version-001fc90a | 0 | PASS |
| hdfs-datanodes-a9bdb7db | 0 | PASS |
| hdfs-fsck-0-3dc0fc47 | 0 | PASS |
| hdfs-fsck-1-b335df11 | 0 | PASS |
| hdfs-input-full-qa-afceb6f5 | 0 | PASS |
| hdfs-raw-count-5991d423 | 0 | PASS |
| hdfs-safe-mode-56d8c986 | 0 | PASS |
| hdfs-services-6743d0bf | 0 | PASS |
| raw-hashes-after-2b400935 | 0 | PASS |
| raw-hashes-before-95b8ba5b | 0 | PASS |
| result-verifier-591705b2 | 0 | PASS |
| tv2-full-pipeline-d2099148 | 0 | PASS |
| tv2-host-tests-70b78dc9 | 0 | PASS |
| tv2-image-1cb0bc2e | 0 | PASS |
| tv2-independent-verification-39e5f45f | 0 | PASS |
| tv2-spark-fixtures-448822c0 | 0 | PASS |

Host tests 65/65, TV2/regression 13/13, Spark fixtures 4/4 PASS. HDFS QA 23 nhóm lỗi=0; independent checks 11/11; result verifier 34/34. Git diff --check được lưu thêm sau cập nhật docs.

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
- TV3 can proceed? **YES**, dùng đúng `tv2-aae83326c1ab`.
