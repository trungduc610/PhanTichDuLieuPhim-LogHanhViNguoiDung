# TV2 WEEK 2 SPARK ANALYSIS + KMEANS REPORT

TV2 — Bùi Trung Đức. Kết quả: **PASS**, run **tv2-4ed70c10cd84**, ngày 12/10/2026. Runner bắt đầu 2026-10-12T15:59:51.787417+00:00, hoàn tất 2026-10-12T16:06:15.001115+00:00. Mọi số liệu bên dưới lấy từ evidence của run này; metric được làm tròn trong bảng, JSON giữ độ chính xác đầy đủ.

## 1. Files changed

| File | Mục đích |
|---|---|
| [Dockerfile.tv2](../Dockerfile.tv2) | Image Spark TV2 bổ sung NumPy 1.24.4 cho MLlib. |
| [compose.tv2.yaml](../compose.tv2.yaml) | Overlay Spark riêng, dùng cùng network HDFS; không recreate NameNode/DataNode. |
| [scripts/run_tv2.py](../scripts/run_tv2.py) | Runner fail-fast, evidence mới, fixture tests, hash raw trước/sau, kiểm file TV1. |
| [scripts/tv2_pipeline.py](../scripts/tv2_pipeline.py) | HDFS read → cleaning → join → exports → stats → ML; read-back và model reload. |
| [scripts/tv2_common.py](../scripts/tv2_common.py) | Chặn output ra ngoài namespace TV2; chọn K từ metric đã đo. |
| [src/tv2_processing.py](../src/tv2_processing.py) | Schema gốc, rule validation, duplicate/conflict/orphan quarantine, transformation. |
| [src/tv2_analytics.py](../src/tv2_analytics.py) | 7 nhóm thống kê và 10 user features. |
| [src/tv2_clustering.py](../src/tv2_clustering.py) | Scale, K=2..6, silhouette, assignments, model và profiles. |
| [scripts/tv2_spark_tests.py](../scripts/tv2_spark_tests.py) | 3 integration fixture tests trên Spark thật, không sửa raw. |
| [tests/test_tv2_contract.py](../tests/test_tv2_contract.py) | 5 host tests về namespace và quy tắc chọn K. |
| [docs/week2_tv2_processing_report.md](../docs/week2_tv2_processing_report.md) | Báo cáo kết quả thực thi này. |
| [docs/week2_tv2_run_guide.md](../docs/week2_tv2_run_guide.md) | Lệnh chạy, semantics, đọc Dashboard exports và giới hạn diễn giải. |
| [README.md](../README.md) | Thêm liên kết và tóm tắt TV2 PASS. |

Code TV1/schema/config/source manifest và raw snapshot giữ nguyên hash. Overlay TV2 chỉ thêm dependency MLlib cần thiết. Lần đầu thiếu NumPy ở base image; Dockerfile TV2 bổ sung NumPy 1.24.4. Không chạy lại Flume, không regenerate dataset.

## 2. HDFS input

- Movies URI: `hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-124cbf30bda7/movies.csv`.
- Logs URI: `hdfs://namenode:9000/movie-log/raw/user_logs/run-f63c810e9d8d/hdfs-124cbf30bda7`.
- Source: Flume `run-f63c810e9d8d`, HDFS `hdfs-124cbf30bda7`; 254 log parts, 1 movie file.
- Filesystem: `org.apache.hadoop.hdfs.DistributedFileSystem`.
- Local fallback: **false**.
- Movie rows: **9,742**; raw log rows: **1,000,000**.
- Spark 3.5.1, Python 3.8.10, Java 11.0.22, Hadoop client 3.3.4; master local[2], driver heap 1536m.
- Source manifest SHA-256: `fdb4c551c34b412a5af3480191d0fb975c64fd43b5a5b80401ea0b0fabd959de`.

Schema được import trực tiếp từ [src/schemas.py](../src/schemas.py), không tạo bản schema nghiệp vụ thứ hai.

| Movie field | Spark type | Required |
|---|---|---|
| movieId | LongType | yes |
| title | StringType | yes |
| genres | StringType | yes |
| releaseYear | IntegerType | no |

| User log fields | Spark type | Required |
|---|---|---|
| eventId, userId, sessionId, action, timestamp, runId, durationSource | StringType | yes |
| movieId, watchDuration, sequenceNumber, simulatedMovieDuration | LongType | yes |
| isSynthetic | BooleanType | yes |

HDFS reader dùng explicit schema và PERMISSIVE kèm corrupt-record diagnostic. nullable=false được kiểm tra bằng rule riêng. Expected counts lấy từ source manifest và chỉ dùng để đối chiếu observed counts.

## 3. Cleaning result

| Metric | Count |
|---|---|
| raw | 1,000,000 |
| parsed | 1,000,000 |
| malformed JSON/structure | 0 |
| required null | 0 |
| required string rỗng | 0 |
| duplicate rows bị loại | 0 |
| exact duplicates | 0 |
| conflicting eventId groups | 0 |
| invalid action | 0 |
| invalid timestamp | 0 |
| invalid watchDuration | 0 |
| invalid integer | 0 |
| invalid provenance | 0 |
| orphan movieId | 0 |
| rejected records | 0 |
| clean | 1,000,000 |

Các basic-rule counts độc lập trên raw và có thể overlap. Steps trong cleaning_summary.json ghi before/removed/after theo thứ tự loại, nên tổng removed đối chiếu với rejected_record_count. Trong run này mọi rule đều có before=after=1,000,000; removed=0.

Quy tắc:

- JSON phải parse được và có đúng bộ 12 field. Kiểm null tất cả field bắt buộc, string bắt buộc không rỗng.
- Action chỉ có view/play/pause/stop/complete.
- Timestamp đúng yyyy-MM-dd'T'HH:mm:ss'Z', parse được và nằm trong khoảng [start,end) của event manifest.
- watchDuration phải là integer không âm, không vượt simulatedMovieDuration. view/play=0; pause/stop/complete>0 theo contract.
- movieId>0, sequenceNumber>=0, simulatedMovieDuration trong 3600–10800 giây. isSynthetic=true, durationSource=synthetic và payload runId khớp manifest.
- Duplicate được xét sau basic rules. Giữ một bản của eventId có payload nghiệp vụ giống nhau; loại tất cả dòng thuộc eventId có payload xung đột. Canonical payload dùng field schema, không phụ thuộc thứ tự key JSON.
- Orphan movieId được đếm sau dedup bằng left anti join rồi đưa vào rejected_logs. Dữ liệu bị loại giữ rawJson/sourceFile/rejected_reason.

Các fixture đã chứng minh những rule này bắt được dữ liệu lỗi; 0 lỗi trên run thật không chỉ là kiểm tra với dữ liệu sạch.

## 4. Transformation + Join

Transformed rows = joined rows = **1,000,000**. movieId hai phía đều LongType; broadcast inner join với movie metadata.

Derived columns: eventTimestamp, eventLocalTimestamp, date, hour, dayOfWeek, watchDurationMinutes, genresArray. eventTimestamp là UTC; calendar fields dùng Asia/Ho_Chi_Minh. dayOfWeek theo Spark: 1=Chủ nhật, 7=Thứ bảy. watchDuration vẫn là giây incremental; watchDurationMinutes=watchDuration/60. Genres tách |, trim, loại trùng và giữ nhóm (no genres listed).

Reconciliation: pre_join_clean_log_count = joined_count + orphan_count = 1,000,000 + 0. clean_log_count đã loại orphan trước khi inner join.

Processed root P = `hdfs://namenode:9000/movie-log/processed/tv2/tv2-4ed70c10cd84`.

| Dataset | HDFS path | Format | Rows |
|---|---|---|---|
| cleaned_logs | P/cleaned_logs | Parquet | 1,000,000 |
| rejected_logs | P/rejected_logs | Parquet | 0 |
| joined_events | P/joined_events | Parquet | 1,000,000 |
| user_features | P/user_features | Parquet | 1,000 |

Các dataset lớn ghi 8 partitions, errorifexists; sau ghi đọc lại số dòng từ HDFS và đối chiếu. Không overwrite output của run trước.

## 5. Statistical analysis

Top movies theo số event play, xuất đủ top 20:

| movieId | title | playCount |
|---|---|---|
| 7262 | Catch That Kid (2004) | 17,064 |
| 100044 | Human Planet (2011) | 9,546 |
| 45720 | Devil Wears Prada, The (2006) | 6,728 |
| 52281 | Grindhouse (2007) | 5,297 |
| 7074 | Navigator, The (1924) | 4,390 |

Top genres theo play (một play tính vào từng genre của phim):

| genre | playCount |
|---|---|
| Comedy | 144,882 |
| Drama | 143,222 |
| Action | 77,406 |
| Thriller | 66,163 |
| Romance | 53,795 |

DAU: 30 ngày, từ 2026-09-01 đến 2026-09-30; min=max=1,000 users/ngày.

Giờ địa phương có nhiều events nhất:

| hour | eventCount | distinctUsers | playCount |
|---|---|---|---|
| 23 | 64,062 | 1,000 | 23,750 |
| 19 | 62,592 | 1,000 | 22,592 |
| 22 | 55,419 | 1,000 | 18,494 |

Action distribution:

| action | count | percentage |
|---|---|---|
| complete | 141,907 | 14.1907% |
| pause | 90,546 | 9.0546% |
| play | 348,474 | 34.8474% |
| stop | 116,021 | 11.6021% |
| view | 303,052 | 30.3052% |

Watch duration, đơn vị giây:

| scope | count | mean | median (approx) | min | max | sample stddev |
|---|---|---|---|---|---|---|
| all_events | 1,000,000 | 1458.785 | 0.000 | 0 | 10,800 | 2654.320 |
| watch_segments | 348,474 | 4186.210 | 3833.000 | 1 | 10,800 | 2966.537 |

Median tính bằng percentile_approx, accuracy=10000. Median toàn events=0 do view/play có duration=0; nhóm watch_segments chỉ gồm duration>0.

User–movie–time: top 3 phim mỗi giờ theo play, có distinctUsers, tổng 72 dòng. Ví dụ:

| hour | movie | playCount | distinctUsers |
|---|---|---|---|
| 19 | Catch That Kid (2004) | 922 | 576 |
| 23 | Catch That Kid (2004) | 1,274 | 687 |

## 6. User feature dataset

Có **1,000 users**, unique_users=1,000. Cả 10 feature đều có 0 null/NaN/Infinity. HDFS: `hdfs://namenode:9000/movie-log/processed/tv2/tv2-4ed70c10cd84/user_features`.

| Feature | Định nghĩa |
|---|---|
| playCount | Số event action=play, gồm cả resume. |
| completeCount | Số event action=complete. |
| totalWatchDuration | Tổng giây mới phát sinh của các đoạn xem. |
| avgWatchDuration | Mean watchDuration>0; 0 nếu không có đoạn xem. |
| distinctMovies | countDistinct(movieId) trên mọi event hợp lệ. |
| distinctGenres | countDistinct thể loại từ genresArray trên mọi event hợp lệ. |
| sessionCount | countDistinct(runId,sessionId). |
| completionRate | Session có complete / session có play; 0 khi mẫu số=0. |
| activeDays | countDistinct(date), theo Asia/Ho_Chi_Minh. |
| eventCount | Tổng event hợp lệ của user. |

completionRate dùng session hoàn thành / session có play để resume không tăng mẫu số. playedSessionCount, completedSessionCount và completionRateDefined được giữ để kiểm tra; mẫu số 0 → completionRate=0, defined=false. avgWatchDuration là mean đoạn xem dương, không phải mean trên các event view/play bằng 0.

VectorAssembler dùng 8 feature: `playCount, completeCount, totalWatchDuration, avgWatchDuration, distinctMovies, distinctGenres, sessionCount, completionRate`. StandardScaler withMean=true, withStd=true.

Loại khỏi ML vector nhưng giữ trong dataset/profile:

- activeDays: variance=0; mọi user có hoạt động đủ 30 ngày.
- eventCount: đã xác minh trên toàn bộ users rằng eventCount=sessionCount+2*playCount; loại chiều trùng thông tin.

## 7. K-Means search

KMeans của pyspark.ml, distance=euclidean, seed=42, maxIter=50; evaluator silhouette dùng squaredEuclidean. Tham chiếu: [Spark ClusteringEvaluator](https://spark.apache.org/docs/3.5.6/api/python/reference/api/pyspark.ml.evaluation.ClusteringEvaluator.html). Runtime thực thi là Spark 3.5.1.

| K | Silhouette | Cluster sizes (ID order) | Training cost |
|---|---|---|---|
| 2 | 0.670756387191 | 237, 763 | 4404.271452 |
| 3 | 0.572440045123 | 634, 316, 50 | 3237.212599 |
| 4 | 0.514174155229 | 11, 307, 588, 94 | 2713.561620 |
| 5 | 0.469237495967 | 252, 265, 27, 142, 314 | 2169.264233 |
| 6 | 0.466004696999 | 252, 42, 6, 254, 142, 304 | 1878.776954 |

Mỗi K có cluster sizes dương, tổng=1,000, khớp observed assignment counts và model.summary.clusterSizes. Không chọn K trước hoặc tạo metric giả.

## 8. Selected model

Best K = **2**, silhouette = **0.670756387191**, seed=42. Điểm cao hơn runner-up K=3 là 0.098316342068; không có tie.

Feature vector theo đúng thứ tự ở mục 6. Model: `hdfs://namenode:9000/movie-log/results/tv2/tv2-4ed70c10cd84/kmeans/model`. Model lưu cả VectorAssembler, fitted StandardScaler và selected KMeans. Reload từ HDFS cho 1,000 assignments giống hoàn toàn với model trong bộ nhớ.

Metadata: selected_k.json/model_metadata.json và HDFS results_root/reports/. features_prepared Parquet giữ rawFeatures và features đã scale.

## 9. Cluster profiles

Các mean giữ đơn vị gốc; completionRate là ratio [0,1]. avgWatchDuration trong profile là mean của feature avgWatchDuration theo user, khác mean tất cả watch segments của mục 5.

| cluster | userCount | avgPlayCount | avgCompleteCount | avgTotalWatchDuration | avgWatchDuration | avgDistinctMovies | avgDistinctGenres | avgSessionCount | avgCompletionRate | avgActiveDays | avgEventCount |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 237 | 436.527 | 154.203 | 1612246.895 | 3743.761 | 317.084 | 19.772 | 417.000 | 0.486215 | 30.000 | 1290.055 |
| 1 | 763 | 321.123 | 138.088 | 1411117.750 | 4406.714 | 213.092 | 19.562 | 267.658 | 0.582218 | 30.000 | 909.904 |

- Cluster 0: 237 users; mean 436.527 play, 417 session, 317.084 phim khác nhau; tổng duration mean 1,612,246.895 giây. Đoạn xem mean 3,743.761 giây; completionRate mean 48.6215%.
- Cluster 1: 763 users; mean 321.123 play, 267.658 session, 213.092 phim khác nhau; tổng duration mean 1,411,117.750 giây. Đoạn xem mean 4,406.714 giây; completionRate mean 58.2218%.

Cluster 0 có nhiều play/session/phim và tổng watch time hơn; Cluster 1 có đoạn xem trung bình dài hơn và completionRate cao hơn. Cả hai có 30 activeDays. Giữ label trung tính Cluster 0/1; không suy diễn thành nhóm hành vi người xem thật.

Ngoài bảng còn export min/max playCount, min/max/median totalWatchDuration theo cluster.

## 10. Dashboard result files

Results root R = `hdfs://namenode:9000/movie-log/results/tv2/tv2-4ed70c10cd84`. P là processed root ở mục 4. {parquet,csv,json} là 3 thư mục con thật, mỗi định dạng có cùng số dòng.

| Result | Formats | HDFS path (P/R dưới đây) | Rows |
|---|---|---|---|
| stats/top_movies_by_play | parquet, csv, json | R/stats/top_movies_by_play/{parquet,csv,json} | 20 |
| stats/top_genres | parquet, csv, json | R/stats/top_genres/{parquet,csv,json} | 20 |
| stats/daily_active_users | parquet, csv, json | R/stats/daily_active_users/{parquet,csv,json} | 30 |
| stats/hourly_activity | parquet, csv, json | R/stats/hourly_activity/{parquet,csv,json} | 24 |
| stats/action_distribution | parquet, csv, json | R/stats/action_distribution/{parquet,csv,json} | 5 |
| stats/watch_duration_summary | parquet, csv, json | R/stats/watch_duration_summary/{parquet,csv,json} | 2 |
| stats/user_movie_time | parquet, csv, json | R/stats/user_movie_time/{parquet,csv,json} | 72 |
| kmeans/features_prepared | parquet | R/kmeans/features_prepared | 1,000 |
| kmeans/user_features | parquet, csv, json | R/kmeans/user_features/{parquet,csv,json} | 1,000 |
| kmeans/k_search | parquet, csv, json | R/kmeans/k_search/{parquet,csv,json} | 5 |
| kmeans/assignments | parquet, csv, json | R/kmeans/assignments/{parquet,csv,json} | 1,000 |
| kmeans/cluster_profiles | parquet, csv, json | R/kmeans/cluster_profiles/{parquet,csv,json} | 2 |
| kmeans/model | spark_ml_pipeline | R/kmeans/model | Model; reload 1,000 users |
| kmeans/model_metadata | parquet, csv, json | R/kmeans/model_metadata/{parquet,csv,json} | 1 |

Có 52 artifact trong output_manifest.json và 24 file CSV/JSON nhỏ tại `evidence/week2-tv2/tv2-4ed70c10cd84/dashboard/`. HDFS JSON là newline-delimited; JSON local là array. CSV UTF-8 có header, array được encode JSON. Chỉ collect output nhỏ <=5,000 rows; không collect 1,000,000 events.

Full selected-model metadata còn ở reports/selected_k và reports/model_metadata; bảng kmeans/model_metadata là bản index 1 dòng. Model rows=1,000 trong manifest biểu thị số users được reload/predict để validate, không phải 1,000 model records.

## 11. Evidence

Thư mục: [evidence/week2-tv2/tv2-4ed70c10cd84/](../evidence/week2-tv2/tv2-4ed70c10cd84/).

- [run_context.json](../evidence/week2-tv2/tv2-4ed70c10cd84/run_context.json)
- [source_manifest.json](../evidence/week2-tv2/tv2-4ed70c10cd84/source_manifest.json)
- [input_counts.json](../evidence/week2-tv2/tv2-4ed70c10cd84/input_counts.json)
- [cleaning_summary.json](../evidence/week2-tv2/tv2-4ed70c10cd84/cleaning_summary.json)
- [transformation_summary.json](../evidence/week2-tv2/tv2-4ed70c10cd84/transformation_summary.json)
- [join_summary.json](../evidence/week2-tv2/tv2-4ed70c10cd84/join_summary.json)
- [statistics_summary.json](../evidence/week2-tv2/tv2-4ed70c10cd84/statistics_summary.json)
- [feature_validation.json](../evidence/week2-tv2/tv2-4ed70c10cd84/feature_validation.json)
- [kmeans_search.json](../evidence/week2-tv2/tv2-4ed70c10cd84/kmeans_search.json)
- [selected_k.json](../evidence/week2-tv2/tv2-4ed70c10cd84/selected_k.json)
- [cluster_profiles.json](../evidence/week2-tv2/tv2-4ed70c10cd84/cluster_profiles.json)
- [model_metadata.json](../evidence/week2-tv2/tv2-4ed70c10cd84/model_metadata.json)
- [output_manifest.json](../evidence/week2-tv2/tv2-4ed70c10cd84/output_manifest.json)
- [spark_environment.json](../evidence/week2-tv2/tv2-4ed70c10cd84/spark_environment.json)
- [pipeline_summary.json](../evidence/week2-tv2/tv2-4ed70c10cd84/pipeline_summary.json)
- [raw-before.json](../evidence/week2-tv2/tv2-4ed70c10cd84/raw-before.json)
- [raw-after.json](../evidence/week2-tv2/tv2-4ed70c10cd84/raw-after.json)
- [run_status.json](../evidence/week2-tv2/tv2-4ed70c10cd84/run_status.json)
- [handoff_validation.json](../evidence/week2-tv2/tv2-4ed70c10cd84/handoff_validation.json)
- [delivery_manifest.json](../evidence/week2-tv2/tv2-4ed70c10cd84/delivery_manifest.json)
- [commands/](../evidence/week2-tv2/tv2-4ed70c10cd84/commands/)
- [logs/index.json](../evidence/week2-tv2/tv2-4ed70c10cd84/logs/index.json)
- [dashboard/](../evidence/week2-tv2/tv2-4ed70c10cd84/dashboard/)

commands/<step-id>/ lưu started.json/finished.json/stdout.txt/stderr.txt. logs/index.json dẫn đến các log này, dùng lại evidence framework TV1. Raw trước/sau: 255 file, 343,872,495 bytes; toàn bộ SHA-256, byte counts và file list giống nhau. 13 file TV1/schema/config/movie/source-manifest được bảo vệ giữ nguyên hash.

## 12. Tests executed

| Command/check | Result |
|---|---|
| python -B -m unittest discover -s tests -p test_tv2*.py -v | PASS — 5 tests |
| Spark: --driver-memory 1g scripts/tv2_spark_tests.py --report <evidence>/spark-fixture-tests.json | PASS — 3 tests |
| Spark: scripts/hdfs_hash_verify.py --source-manifest <source> --report <evidence>/raw-before.json | PASS — 255 files, 343,872,495 bytes |
| Spark: --driver-memory 1536m scripts/tv2_pipeline.py --run-context evidence/week2-tv2/tv2-4ed70c10cd84/run_context.json | PASS — 52 artifacts; read-back; model reload |
| Spark: scripts/hdfs_hash_verify.py --source-manifest <source> --report <evidence>/raw-after.json | PASS — 255 files unchanged |
| python -B scripts/run_tv2.py --hdfs-context evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json | PASS — all 5 final acceptance checks |
| Initial run tv2-5d9d17b3e866, driver-memory 3g | FAIL — Docker OOM / exit 137; fixed in TV2, retained evidence |

Lệnh Docker đầy đủ của từng bước nằm ở commands/<step-id>/started.json. HDFS import/output dùng Compose project movie-hdfs-124cbf30bda7, --profile spark run --rm --no-deps; không khởi động lại HDFS services. Fixture là DataFrame tạm, có lỗi JSON/null/action/timestamp/duration/integer/provenance, duplicate exact/conflict, orphan, timezone, genres, zero denominator, NaN/Infinity và movie duplicate.

Lần đầu 3g heap bị Docker OOM vì Docker có 3.682 GiB RAM. TV2 đã giảm xuống 1536m và tối ưu duplicate/cache; final run PASS. Evidence lỗi vẫn giữ ở evidence/week2-tv2/tv2-5d9d17b3e866/.

## 13. Remaining issues

Không còn lỗi chặn nghiệm thu TV2 trên runtime hiện tại.

Giới hạn phân tích: log/runtime phim synthetic; dữ liệu chỉ là cohort tháng 9/2026. Silhouette đánh giá phân tách trong vector đã scale, không chứng minh hành vi thật hoặc recommendation quality. Các feature hoạt động vẫn có tương quan. Median là xấp xỉ. Spark chạy local[2] trong Docker, không dùng kết quả này để kết luận khả năng scale của cluster phân tán. Các giới hạn này không phải lỗi pipeline.

## 14. Final decision

| Decision | YES/NO |
|---|---|
| TV2 Week 2 hoàn thành đầy đủ? | YES |
| Spark preprocessing PASS? | YES |
| Statistical analysis PASS? | YES |
| K-Means PASS? | YES |
| Dashboard result files ready? | YES |
| Có thể bàn giao sang TV3/Week 3? | YES |

Hướng dẫn chạy: [week2_tv2_run_guide.md](week2_tv2_run_guide.md). Dừng ở bàn giao kết quả TV2; không làm Dashboard UI/TV3/Week 3, không commit/push.
