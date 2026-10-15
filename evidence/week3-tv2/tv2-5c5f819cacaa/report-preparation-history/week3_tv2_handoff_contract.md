# Hợp đồng bàn giao TV2 Tuần 3 — chưa phát hành

**NOT_RELEASED. Không có final TV2 Week 3 run.** Tài liệu này chuẩn bị cấu trúc bàn giao, không chọn dữ liệu cho TV3 và không cấp phép thay Dashboard selection.

Sau khi runner, input QA, Spark fixtures, 7 independent analysis checks, result verifier, model reload và raw preservation đều PASS, phát hành `docs/week3_tv2_handoff.md` và `evidence/week3-tv2/<final-run>/handoff.json` mới.

Markdown bắt buộc có:

1. Exact final TV2 run ID và link run_status/verifier.
2. Hai input HDFS URI và Flume/HDFS IDs.
3. Exact processed root.
4. Exact results root.
5. Best K đo mới.
6. Silhouette đo mới.
7. Selected feature columns theo thứ tự, excluded columns và lý do.
8. Cluster profiles/size từ assignments thật.
9. Danh sách Dashboard datasets được chọn.
10. Format từng dataset và local JSON array/HDFS JSONL/CSV semantics.
11. Row count và read-back count từng dataset.
12. Calendar timezone Asia/Ho_Chi_Minh; session/source UTC.
13. Duration seconds/derived minutes; positive segment mean.
14. Synthetic limitation.
15. Commands kiểm tra và model reload.
16. Files TV3 nên dùng: handoff-selected exports của đúng run PASS.
17. Files không dùng: blocked/FAIL attempts, fixture/generated input, raw event streams cho UI, output khác run.
18. Không trộn result từ run cũ; không suy final từ tên thư mục hay receipt lịch sử.

Machine-readable handoff cần các key: status=PASS, tv2_run_id, hdfs_input (IDs/URIs/source_manifest_sha256), processed_root, results_root, best_k, silhouette, seed, feature_columns, excluded_features, cluster_profiles, timezone, duration_units, synthetic=true, dashboard_outputs và validation_receipts.

Mỗi dashboard_outputs entry cần name/format/HDFS URI/local relative path nếu có/rows/read_back_rows/SHA256 local. Lấy từ output_manifest của run đã verify, không điền từ baseline. Record model_uri và model_reload_assignments_match. Handoff không được phát hành nếu bất kỳ acceptance check nào chưa chạy hoặc FAIL.
