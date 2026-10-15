# TV2 Tuần 3 — final handoff cho TV3/Cowork

**PASS — final run `tv2-aae83326c1ab`.** Ngày 15/10/2026. [Machine-readable handoff](../evidence/week3-tv2/tv2-aae83326c1ab/handoff.json) là danh sách chọn dữ liệu chính xác; [report](week3_tv2_processing_report.md) có validation đầy đủ.

## Identity và input

- Final TV2 run: `tv2-aae83326c1ab`.
- TV1 Flume: `run-f63c810e9d8d`.
- TV1 HDFS/project: `hdfs-124cbf30bda7` / `movie-hdfs-124cbf30bda7`.
- Movies URI: `hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-124cbf30bda7/movies.csv`.
- Logs URI: `hdfs://namenode:9000/movie-log/raw/user_logs/run-f63c810e9d8d/hdfs-124cbf30bda7`.
- Processed root: `hdfs://namenode:9000/movie-log/processed/tv2/tv2-aae83326c1ab`.
- Results root: `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab`.

9.742 movies; 1M events; raw 255 files/343.872.495 byte; 255/255 size/SHA256 unchanged. DistributedFileSystem, local_fallback=false.

## Model, selected features và cluster profiles

Best K=2; Silhouette=0.6707563871905433; seed=42; maxIter=50. Selected vector theo thứ tự: `playCount, completeCount, totalWatchDuration, avgWatchDuration, distinctMovies, distinctGenres, sessionCount, completionRate`. activeDays variance=0; eventCount exact redundancy được đo lại, chỉ loại khỏi ML vector. Dataset/profile giữ đủ 10 features.

Model: `hdfs://namenode:9000/movie-log/results/tv2/tv2-aae83326c1ab/kmeans/model`, gồm assembler/scaler/selected model; reload tái tạo đúng 1.000 assignments.

| Cluster | Users | avgPlayCount | avgCompleteCount | avgSessionCount | avgDistinctMovies | avgDistinctGenres |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 237 | 436.527 | 154.203 | 417.000 | 317.084 | 19.772 |
| 1 | 763 | 321.123 | 138.088 | 267.658 | 213.092 | 19.562 |

| Cluster | avgTotalWatchDuration (s) | avgWatchDuration (s) | avgCompletionRate | avgActiveDays | avgEventCount |
| --- | --- | --- | --- | --- | --- |
| 0 | 1,612,246.895 | 3,743.761 | 0.486215 | 30.000 | 1,290.055 |
| 1 | 1,411,117.750 | 4,406.714 | 0.582218 | 30.000 | 909.904 |

Cluster 0 (237 users) có trung bình 436.527 play và 417.000 session/user, cao hơn Cluster 1 (321.123 play, 267.658 session). Tổng giây xem trung bình là 1612246.895 so với 1411117.750; nhưng đoạn xem dương trung bình ngắn hơn (3743.761s so với 4406.714s), completion rate thấp hơn (48.621% so với 58.222%).

## Dataset list, formats và row counts

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

Ba format nằm trong subdirectory parquet/csv/json của base; exact URI/rows/schema/local hash của từng format nằm trong handoff.json. TV3 **phải dùng** 7 stats và 5 bảng kmeans được liệt kê trong dashboard_outputs của đúng run này. Local exports: `../evidence/week3-tv2/tv2-aae83326c1ab/dashboard/`. Local JSON là array; HDFS JSON là JSON Lines; CSV header UTF-8, nested arrays encode JSON. Không hard-code part filenames; đọc đúng format directory, bỏ _SUCCESS.

Không dùng generated input, fixtures, raw event streams làm UI input hoặc results/model khác run. Không trộn `tv2-4ed70c10cd84`, `tv2-0523e144a808`, `tv2-63c6eba4e8e4`, `tv2-5c5f819cacaa`, `tv2-56569b78b4e1`. Chúng chỉ là lịch sử/baseline/attempt khác, không phải final dataset mới.

## Timezone, units và limitation

Source UTC Z, session UTC, calendar Asia/Ho_Chi_Minh. watchDuration là giây incremental segment; minutes là derived. avgWatchDuration là mean positive segment. Completion rate dùng distinct completed sessions / sessions có play; denominator zero=>0 và defined=false. Genres multi-label. Logs/users/movie runtime synthetic; không suy thành hành vi người thật. Cluster IDs trung tính, không recommendation.

## Commands verify

Từ repo root, chọn Python thật theo run guide và đặt $py:

```powershell
$run = 'tv2-aae83326c1ab'
Get-Content "evidence/week3-tv2/$run/handoff.json" -Raw
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
& $py -B scripts/verify_tv2_results.py --run-id $run --evidence-root evidence/week3-tv2 --report "evidence/week3-tv2/$run/reverify-$stamp.json"
$env:HDFS_RUN_ID = 'hdfs-124cbf30bda7'
docker compose -f compose.hdfs.yaml -p movie-hdfs-124cbf30bda7 exec -T namenode hdfs dfs -ls /movie-log/processed/tv2/tv2-aae83326c1ab
docker compose -f compose.hdfs.yaml -p movie-hdfs-124cbf30bda7 exec -T namenode hdfs dfs -ls /movie-log/results/tv2/tv2-aae83326c1ab
```

HDFS formats/values/7 analyses/model reload: runtime-verification.json. Cross-export checks: result-verification.json. Raw preservation: raw-preservation.json. Đây là bàn giao dữ liệu; task không đổi Dashboard UI/selection.
