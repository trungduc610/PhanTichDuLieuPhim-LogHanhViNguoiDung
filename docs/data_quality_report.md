# Chất lượng dữ liệu sau lượt kiểm lại

Ngày kiểm lại: 11/10/2026 (Asia/Saigon). Đây là sản phẩm thực thi mới tại checkout Windows hiện tại, độc lập bằng chứng lịch sử. Movies: 9.742 dòng, SHA256 `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536`. Demo/main Flume E2E và Spark kiểm toàn bộ Sink đều PASS.

| Lô mới | Run Flume | Events / unique | File / rỗng | Bytes Sink |
|---|---|---:|---:|---:|
| Demo | `run-aefc814b0b5f` | 10,000 / 10,000 | 3 / 1 | 3,433,123 |
| Main | `run-aa6b9eb58dca` | 1,000,000 / 1,000,000 | 15 / 0 | 343,339,148 |

Missing/unexpected/duplicate/conflicting ID/changed payload, UTF-8/JSON/type/provenance/action/duration, session/sequence và user overlap: đều 0 trên hai lô mới. File rỗng do rolling được giữ và thống kê, không có event; tất cả file không rỗng kết thúc bằng LF. Đối chiếu canonical payload không phụ thuộc thứ tự file/key JSON. Một lần đối chiếu thành công không chứng minh exactly-once hoặc phục hồi lỗi.

Bằng chứng: `evidence/run-aefc814b0b5f/`, `evidence/run-aa6b9eb58dca/`, `evidence/recheck-20261011-221710/spark-demo.json`, `evidence/recheck-20261011-221710/spark-main.json`, `evidence/recheck-20261011-221710/dataset_quality.json`. Audit đầy đủ: `audit/2026-10-11-221710-week1-recheck/bao-cao-nghiem-thu-tuan-1-recheck.md`. Manifest mới: `evidence/recheck-20261011-221710/delivery_manifest.json`.

Movies được đọc bằng CSV parser UTF-8 strict, header/field count/positive signed long ID/title/genres/year/NFC kiểm toàn bộ. 9.742 ID phân biệt, 0 lỗi; 13 năm null và 34 nhãn `(no genres listed)` giữ nguyên; 11 dòng được chuẩn hóa trong file riêng, raw không sửa. Ratings 100.836, tags 3.683, links 9.742 đo bằng CSV parser, chưa phân tích ratings/tags.

Spark báo cáo từng loại lỗi và ví dụ eventId/_file khi lỗi; streaming validator có path:dòng. Không có ví dụ lỗi trong lô PASS vì mọi counter bằng 0, không tạo ví dụ giả. Trên fixture có lỗi, assertions yêu cầu phát hiện orphan ngoài 5 dòng đầu, parse timestamp/null, metadata trùng, eventId xung đột, duration âm, malformed CSV/JSON/type; các fixture luôn được ghi rõ không phải Flume.

Watch duration main: 1,458,785,357 giây; 303,052 phiên, 1,000 user, 9,740 phim. UTC từ 2026-08-31T17:00:04Z đến 2026-09-30T15:58:22Z. Không có lỗi phiên, sequence, completion hoặc overlap trên full reconciliation độc lập. File rolling rỗng không là event lỗi; tất cả file có bytes được parse và kiểm newline.

Tuần 2: kiểm eventId conflict trước dedup (không coi dropDuplicates bảo đảm exactly-once), xử lý year null thành nhóm unknown, split/explode genres, chuyển UTC sang Asia/Ho_Chi_Minh để thống kê giờ. Các thống kê phản ánh mô phỏng, không phải sở thích người xem thật.
