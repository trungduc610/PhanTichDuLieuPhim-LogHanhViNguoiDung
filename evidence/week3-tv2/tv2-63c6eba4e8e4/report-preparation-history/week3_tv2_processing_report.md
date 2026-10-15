# WEEK 3 TV2 FINAL REPORT

TV2: Bùi Trung Đức. Ngày audit: 15/10/2026 (Asia/Saigon). Đây là báo cáo tiến độ và chuẩn bị Tuần 3; chưa phải nghiệm thu kết quả xử lý mới.

## 1. Overall status

**PARTIAL — BLOCKED_BY_TV1_RUNTIME.** Run thử Tuần 3: `tv2-0523e144a808`. Cả hai container baseline đang dừng, nên runner dừng trước build image và trước Spark. Không start cluster, không local fallback, không ghi HDFS. Không dùng release phục hồi khác.

## 2. Baseline / TV1 handoff

- Flume run: `run-f63c810e9d8d`.
- HDFS run/project: `hdfs-124cbf30bda7` / `movie-hdfs-124cbf30bda7`.
- Context: `evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json`.
- Movies: `hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-124cbf30bda7/movies.csv`.
- Logs: `hdfs://namenode:9000/movie-log/raw/user_logs/run-f63c810e9d8d/hdfs-124cbf30bda7`.
- HDFS runtime: NameNode/DataNode `exited`, exit 143. Raw verification hiện tại: **NOT_RUN**.
- Expected input theo manifest: 9.742 movies, 1.000.000 events, 254 Sink parts, 255 raw files, 343.872.495 byte. Đây là điều kiện đối chiếu input, không phải kết quả Week 3 đã đo.
- TV2 baseline lịch sử: `tv2-4ed70c10cd84`; clean/join 1.000.000, 1.000 users, K=2, silhouette 0.6707563871905433. Chỉ dùng so sánh; không đưa vào bảng kết quả mới.

## 3. Source audit

Đã đọc runner, pipeline, common, processing, analytics, clustering, Spark fixtures, host tests, verifier, schema, Dockerfile/Compose TV2, docs Tuần 2 và context/source manifest TV1. Danh sách/hash đầy đủ: [source-audit.json](../evidence/week3-tv2/tv2-0523e144a808/source-audit.json).

Không thấy local input fallback, generated input thay Sink, sklearn KMeans, best K cố định, silhouette giả hoặc ép output count. Expected raw counts lấy từ manifest; writers chỉ ghi processed/results của run mới bằng errorifexists. Full dataset được xử lý trong Spark; collect chỉ dùng metadata/danh sách file, cluster aggregates và exports nhỏ có giới hạn 5.000 dòng.

Sửa đã làm:

1. Runner/verifier hỗ trợ `--evidence-root evidence/week3-tv2`; mặc định Tuần 2 được giữ.
2. Week 3 từ chối context/release khác baseline user chọn. Kiểm services trước build; ghi `BLOCKED_BY_TV1_RUNTIME` nếu preflight chưa đạt.
3. Bổ sung preflight DataNode, safe mode, fsck từng raw namespace, file count/bytes, full HDFS byte hash và Spark input QA trước preprocessing. Nhánh services-running chưa kiểm chứng trong lần này.
4. Bỏ giả định 72 dòng user-movie-time; kiểm giờ/rank, top tối đa 3, thứ tự count giảm dần/movieId tăng dần và không trùng phim.
5. Thêm 7 regression tests TV2. Thuật toán cleaning/features/K-Means giữ nguyên.

Điểm còn mở: verifier exports kiểm nhiều invariant nhưng chưa chứng minh cả bảy analysis từ joined dataset. Cần phép recomputation độc lập sau khi runtime sẵn sàng. Chưa tạo final handoff vì chưa có output Tuần 3.

## 4. Preprocessing

| Metric | Count |
|---|---|
| raw | NOT_RUN |
| parsed | NOT_RUN |
| malformed JSON/structure | NOT_RUN |
| required null | NOT_RUN |
| duplicate / exact duplicate | NOT_RUN |
| conflicting eventId groups/rows | NOT_RUN |
| invalid action | NOT_RUN |
| invalid timestamp | NOT_RUN |
| invalid watchDuration | NOT_RUN |
| orphan movieId | NOT_RUN |
| rejected | NOT_RUN |
| clean | NOT_RUN |

Code kiểm cấu trúc/field, null/empty, action, timestamp UTC và range, integer/duration/provenance; sau đó xử lý exact duplicate/conflicting eventId và orphan. Basic-rule counts độc lập trên raw và có thể overlap. `steps` ghi số loại tuần tự không overlap; tổng removed phải bằng rejected. Các conflicting ID loại tất cả biến thể, exact duplicate giữ một bản. Rejected giữ rawJson/sourceFile/reason. Không tạo lỗi giả nếu input sạch.

## 5. Transformation / Join

Các cột: `eventTimestamp`, `eventLocalTimestamp`, `date`, `hour`, `dayOfWeek`, `watchDurationMinutes`, `genresArray`. Calendar dùng Asia/Ho_Chi_Minh trong Spark session UTC; source timestamp UTC Z. `watchDuration` giữ giây theo segment; minutes là cột suy ra. `movieId` hai phía bigint. Genres split dấu |, trim và distinct.

Counts: **NOT_RUN**. Theo implementation, orphan được quarantine trước clean cuối: `pre_join_clean_log_count = joined_count + orphan_count`; `clean_log_count = joined_count`. Không dùng nhầm clean sau quarantine làm vế trái có thêm orphan. Movie metadata phải unique để ngăn row multiplication.

Processed root dự kiến: `hdfs://namenode:9000/movie-log/processed/tv2/tv2-0523e144a808`. **Chưa tạo HDFS output**; lần chạy sau dùng run ID mới.

## 6. Analysis validation

| Analysis | Result mới | Cross-check phải chạy | Status |
|---|---|---|---|
| Top movies by play | Chưa có | Recompute play theo movieId/title, sort và top 20 từ joined | NOT_RUN |
| Top genres | Chưa có | Explode genre distinct/phim trên play; đối chiếu toàn bộ counts, multi-genre có thể vượt tổng play | NOT_RUN |
| Daily active users | Chưa có | countDistinct(userId) theo ngày địa phương từ joined, so từng ngày | NOT_RUN |
| Hourly activity | Chưa có | Recompute event/play/distinct users theo giờ địa phương; tổng events phải khớp joined | NOT_RUN |
| Action distribution | Chưa có | Recompute count/action và percentage; tổng counts khớp joined | NOT_RUN |
| Watch duration | Chưa có | So sum/count/mean/min/max, approximate median/sample stddev trên all_events và positive segments; giây | NOT_RUN |
| User-movie-time | Chưa có | Recompute hour/movie play counts/distinct users và top 3 bằng ranking độc lập; đối chiếu cả keys/values | NOT_RUN |

Bảy phép trên phải đọc joined dataset HDFS của cùng run. Không chỉ nhìn output hoặc dựa vào range/count. Local verifier hiện kiểm tổng action/hour/play, feature duration và profile means; các kiểm đó bổ trợ, không thay cross-check đầy đủ.

## 7. Feature engineering

Users mới: **NOT_RUN**. Dataset giữ `playCount`, `completeCount`, `totalWatchDuration`, `avgWatchDuration`, `distinctMovies`, `distinctGenres`, `sessionCount`, `completionRate`, `activeDays`, `eventCount`.

Completion rate dùng số distinct (runId,sessionId) có complete / số session có play; mẫu số 0 => 0 và `completionRateDefined=false`. Avg watch duration là mean positive segment, 0 nếu không có segment. Phải kiểm một dòng/user, null/NaN/Infinity=0, completionRate trong [0,1], users khớp joined distinct users.

Feature loại khỏi ML mới: **NOT_RUN**, không suy từ baseline. Code đo variance và loại variance=0; chỉ loại eventCount khi xác minh đúng `eventCount=sessionCount+2*playCount` trên mọi user. Vẫn giữ các cột này trong feature dataset/profile.

## 8. K-Means comparison

| K | Silhouette | Cluster sizes | Training cost |
|---|---|---|---|
| 2 | NOT_RUN | NOT_RUN | NOT_RUN |
| 3 | NOT_RUN | NOT_RUN | NOT_RUN |
| 4 | NOT_RUN | NOT_RUN | NOT_RUN |
| 5 | NOT_RUN | NOT_RUN | NOT_RUN |
| 6 | NOT_RUN | NOT_RUN | NOT_RUN |

## 9. Final model

Best K, silhouette, selected features và model path: **NOT_AVAILABLE**. Seed dự kiến lấy từ manifest (=42 trong context hiện tại), maxIter=50; chưa có model được fit trong run này. Cần fit đủ năm K bằng pyspark.ml.clustering.KMeans, đo thật bằng ClusteringEvaluator(silhouette, squaredEuclidean), chọn score cao nhất; chỉ ưu tiên K nhỏ khi score bằng nhau chính xác. Model save phải gồm assembler, fitted scaler và selected model, rồi load lại để so toàn bộ assignments.

## 10. Cluster profiles

Chưa có cluster mới để diễn giải. Chỉ lập bảng sau runtime với cluster ID, userCount và mean của cả 10 feature; thêm min/max/median playCount/totalWatchDuration nếu có. Tổng userCount phải bằng users và khớp assignments. Dùng Cluster 0, Cluster 1,...; mô tả định lượng từ raw-unit metrics, không đặt semantic label trước.

## 11. Model evaluation and limitations

### Lý thuyết K-Means

K-Means phân cụm không giám sát các vector số thành K nhóm. Hàm mục tiêu là tổng bình phương khoảng cách đến centroid: `J = sum_i ||x_i - mu[c_i]||^2`. Khởi tạo K tâm, gán từng điểm vào tâm gần nhất, tính lại tâm bằng trung bình các điểm trong nhóm, rồi lặp đến điều kiện dừng hoặc maxIter. Spark MLlib triển khai Estimator và hỗ trợ khởi tạo k-means||. [Apache Spark clustering](https://spark.apache.org/docs/3.5.7/ml-clustering.html#k-means).

Trong đề tài, mỗi vector đại diện một user qua các feature số về hoạt động và thời lượng. Không có nhãn hành vi để huấn luyện supervised; phân cụm giúp so sánh các nhóm qua profile. Pipeline DataFrame giữ phép xử lý trong Spark. Đây là phân cụm hành vi mô phỏng, không phải recommendation.

VectorAssembler ghép feature theo thứ tự metadata; StandardScaler(withMean=true, withStd=true) dùng fitted mean/std để tránh cột đơn vị lớn chi phối khoảng cách. KMeans dùng Euclidean; evaluator dùng squaredEuclidean. [Apache Spark StandardScaler](https://spark.apache.org/docs/3.5.7/ml-features.html#standardscaler).

### Đánh giá cần hoàn thành

Silhouette so mức gần các điểm cùng nhóm với nhóm lân cận; giá trị cao hơn thường cho phân tách tốt hơn theo khoảng cách đã chọn. So cả K=2..6, score gap, training cost, balance/imbalance và profile. Không dùng score làm tiêu chí duy nhất. [ClusteringEvaluator](https://spark.apache.org/docs/3.5.7/api/python/reference/api/pyspark.ml.evaluation.ClusteringEvaluator.html).

Chưa có kết quả Tuần 3 để đánh giá. Giới hạn phải nêu: log/runtime phim synthetic; feature còn hạn chế và tương quan; cần chọn K; nhạy scaling/outliers và hình học Euclidean; cluster ID không tự mang nhãn ngữ nghĩa; Spark local[2] trên một host chưa phải nhiều worker; silhouette không chứng minh giá trị ngoài đời. Tài liệu tham khảo API thuộc nhánh 3.5.7; runtime project vẫn giữ 3.5.1, chưa nâng phiên bản.

## 12. Final Dashboard outputs

**Chưa có final outputs Tuần 3.** Bảng sau là hợp đồng dự kiến, không phải output đã xuất. Gọi P/R là processed/results root của run PASS tương lai.

| Dataset | Format dự kiến | HDFS path dự kiến | Rows mới |
|---|---|---|---|
| cleaned_logs, joined_events, rejected_logs, user_features | Parquet | P/<dataset> | NOT_RUN |
| features_prepared | Parquet | R/kmeans/features_prepared | NOT_RUN |
| 7 nhóm stats tại mục 6 | Parquet, CSV, JSON | R/stats/<name>/<format> | NOT_RUN |
| kmeans user_features, k_search, assignments, cluster_profiles, model_metadata | Parquet, CSV, JSON | R/kmeans/<name>/<format> | NOT_RUN |
| model | Spark ML PipelineModel | R/kmeans/model | NOT_RUN |

CSV/JSON nhỏ mới coalesce(1), chỉ collect nếu <=5.000 dòng; dataset lớn repartition 8 và giữ Parquet. Local Dashboard JSON là array, HDFS JSON là JSON Lines; CSV có header UTF-8, nested array được encode JSON. Không sửa Dashboard selection/UI.

## 13. TV3 handoff

- `docs/week3_tv2_handoff.md`: **chưa phát hành**.
- `evidence/week3-tv2/<final-run>/handoff.json`: **chưa phát hành**.
- Exact final run/result root: **NONE**; `tv2-0523e144a808` là blocked attempt, không phải final.
- [Hợp đồng handoff](week3_tv2_handoff_contract.md) ghi đủ 18 nội dung cần phát hành sau PASS; không dùng làm nguồn dữ liệu hiện tại.

## 14. Evidence

[evidence/week3-tv2/tv2-0523e144a808](../evidence/week3-tv2/tv2-0523e144a808/) có context, source manifest sao chép nguyên byte, run_status, source-audit, host-tests, stage-status, TV1 local preservation, commands và logs. Commands lưu argv/cwd/UTC/exit/stdout/stderr.

Các receipt input_counts/cleaning/transformation/join/statistics/features/K-search/profiles/output-manifest/raw-before/raw-after và dashboard exports mới chưa có vì các bước đó NOT_RUN. Không tạo placeholder metric files giả.

## 15. Screenshot checklist

Xem [checklist 15 ảnh](week3_tv2_screenshots.md). Hiện chưa capture ảnh Spark/results mới; không dùng ảnh Tuần 2 làm ảnh Tuần 3.

## 16. Demo script

Xem [demo 4–6 phút](week3_tv2_demo.md). Hiện chỉ có thể trình bày audit/gate và lý thuyết; chưa trình diễn kết quả xử lý Tuần 3.

## 17. Tests

| Command/check | Kết quả |
|---|---|
| python -B -m unittest discover -s tests -p test_tv2*.py -v | PASS, 12 tests |
| python -B -m unittest discover -s tests -v | PASS, 64 tests |
| git diff --check | PASS |
| Runner Week 3 trên context baseline | BLOCKED_BY_TV1_RUNTIME; exit 1 là gate được ghi nhận, không phải pipeline PASS |
| Spark fixtures / HDFS input verification | NOT_RUN |
| Full pipeline / result verifier / model reload | NOT_RUN |
| Raw-before/raw-after HDFS hash compare | NOT_RUN |

Host tests dùng fixture tạm; không chứng minh Spark hoặc dữ liệu HDFS hiện tại.

## 18. Remaining issues

1. TV1 cần chuẩn bị runtime đúng baseline và hoàn tất handoff health/data hiện tại. TV2 không tự start/format cluster.
2. Sau gate, chạy toàn bộ fixtures/input QA/pipeline vào run mới, full independent cross-check 7 analysis, verifier/model reload/raw-before-after.
3. Bổ sung bảng feature exclusion, K search, profiles và outputs bằng số đo thật; viết diễn giải định lượng.
4. Chỉ sau acceptance mới phát hành hai handoff files, capture ảnh và nghiệm thu demo. Không sửa evidence blocked này thành PASS.

## 19. Final decision

- TV2 Week 3 complete? **NO**.
- Preprocessing final? **NO**.
- Analysis final? **NO**.
- K-Means final? **NO**.
- Final results ready for TV3? **NO**.
- TV3 can proceed using Week 3 output? **NO**.

Tiếp tục source/report prep đã hoàn thành trong phạm vi runtime bị chặn. Không ALS/recommender, không TV3/UI, không regenerate/Flume rerun, không sửa TV1/raw/volume, không commit/push.
