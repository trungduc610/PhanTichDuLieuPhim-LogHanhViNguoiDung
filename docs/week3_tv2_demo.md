# TV2 Tuần 3 — demo 4–6 phút

Final **tv2-aae83326c1ab**, PASS. Mở [handoff](week3_tv2_handoff.md) và `../evidence/week3-tv2/tv2-aae83326c1ab/`. Full job đã chạy thật trước buổi demo; trình bày reports/commands cùng run. Không demo sâu lại Flume/HDFS của TV1.

| Thời gian | Nội dung | Evidence |
|---|---|---|
| 0:00–0:35 | HDFS URI, 9742 movies/1M events, synthetic limitation | run_context/input_counts/spark_environment |
| 0:35–1:00 | Schema, movieId bigint, explicit validation | input-hdfs-qa |
| 1:00–1:35 | Raw/clean/joined=1M, rejected=0, counting semantics | cleaning_summary/join_summary |
| 1:35–2:00 | UTC/local calendar, seconds/minutes, genres | transformation_summary/runtime-verification |
| 2:00–2:45 | Top movie 7262: 17064 play; Comedy: 144882; DAU/hour/action và cross-check | statistics_summary/dashboard |
| 2:45–3:20 | 1000 users/10 features, variance/redundancy | feature_validation/model_metadata |
| 3:20–4:05 | Assembler/scaler, K=2..6, final K=2, silhouette=0.670756 | kmeans_search/selected_k |
| 4:05–4:45 | Sizes [237, 763], raw-unit profiles, neutral labels | cluster_profiles |
| 4:45–5:30 | Reload 1000 assignments, raw 255/255 unchanged, exact exports | runtime-verification/raw-preservation/handoff |

Kết thúc với giới hạn synthetic/local[2]/correlated features/internal Silhouette. Không gọi K-Means là recommender. [Run guide](week3_tv2_run_guide.md) có lệnh kiểm tra; mọi report path phải mới.
