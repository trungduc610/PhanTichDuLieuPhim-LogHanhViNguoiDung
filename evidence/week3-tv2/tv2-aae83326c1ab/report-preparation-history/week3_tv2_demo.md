# TV2 Tuần 3 — kịch bản demo 4–6 phút

Trạng thái chuẩn bị: BLOCKED_BY_TV1_RUNTIME. Các mục kết quả chỉ thực hiện khi đã có run PASS mới, không dùng số Tuần 2 như kết quả mới. Không cần trình bày sâu ingestion/HDFS của TV1.

| Thời gian | Trình bày | Bằng chứng cần mở |
|---|---|---|
| 0:00–0:35 | Hai URI HDFS của baseline, lineage Flume Sink và synthetic limitation | run_context/source_manifest/input_counts/spark_environment |
| 0:35–1:00 | Schema, movieId bigint, explicit null validation | DataFrame printSchema/input QA |
| 1:00–1:40 | Cleaning raw→parsed→rejected→clean, overlap categories và disjoint removal | cleaning_summary/rejected samples |
| 1:40–2:10 | UTC→Asia/Ho_Chi_Minh, giây/phút, genres và join identity | transformation_summary/join_summary |
| 2:10–2:55 | Top movies/genres, action/hour/DAU; giải thích cross-check từ joined | statistics_summary/analysis verification |
| 2:55–3:30 | Một dòng/user, 10 features, denominator zero, variance/redundancy | user_features/feature_validation |
| 3:30–4:15 | VectorAssembler/scaling; K=2..6 và Silhouette thực | kmeans_search/model_metadata |
| 4:15–4:50 | Best K, score gap, sizes và raw-unit cluster profiles | selected_k/cluster_profiles |
| 4:50–5:30 | Model reload, exports, raw preservation và final handoff | output_manifest/raw-before/raw-after/handoff |

Không chạy lại Flume, không toPandas/collect dataset lớn. Full job có thể dài hơn demo: chuẩn bị report đo thật, lệnh và logs cùng run. Nếu gate vẫn chặn, chỉ trình bày lý do và công việc chuẩn bị; không gọi demo kết quả là hoàn tất.

Lệnh chạy sau khi TV1 thông báo runtime sẵn sàng: xem [run guide](week3_tv2_run_guide.md). Mỗi lần tạo run ID mới; blocked attempt không được resume bằng cách sửa receipt.
