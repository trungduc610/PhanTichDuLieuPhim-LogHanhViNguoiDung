# TV2 Tuần 3 — checklist ảnh thực tế

Chỉ capture sau khi có run mới, ghi cùng run ID trong caption. Hiện chưa có ảnh kết quả Tuần 3.

- [ ] 1. Spark đọc đúng hai HDFS URI, DistributedFileSystem và local_fallback=false.
- [ ] 2. Input DataFrame/schema, movieId bigint hai phía.
- [ ] 3. Cleaning counts raw/parsed/rejected/clean và counting semantics.
- [ ] 4. Transformation columns, UTC và Asia/Ho_Chi_Minh, seconds/minutes.
- [ ] 5. Join counts, orphan quarantine và không row multiplication.
- [ ] 6. Top movies by play và cross-check.
- [ ] 7. Top genres, ghi rõ multi-genre counting.
- [ ] 8. Action distribution và tổng events đối chiếu.
- [ ] 9. Hourly activity/DAU theo lịch địa phương.
- [ ] 10. User feature dataset, một dòng/user và QA null/NaN/Infinity.
- [ ] 11. Bảng K=2..6, Silhouette, cluster sizes, training cost.
- [ ] 12. Best K/seed/selected features và lý do chọn.
- [ ] 13. Cluster profiles định lượng, neutral labels.
- [ ] 14. HDFS processed/results đúng run, output formats/counts và model reload.
- [ ] 15. Final runner/verifier/analysis checks PASS, raw-before/after và handoff.

Không dựng ảnh từ log, không sửa số liệu trong ảnh, không dùng ảnh run khác làm ảnh final. Ưu tiên terminal thật và file report của cùng run; các ảnh cluster TV1 thuộc phần TV1.
