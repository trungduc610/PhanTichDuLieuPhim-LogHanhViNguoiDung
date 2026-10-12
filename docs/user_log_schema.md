# Schema log hành vi

Sink thật hiện tại: `data/runs/run-aa6b9eb58dca/output/` (main) và `data/runs/run-aefc814b0b5f/output/` (demo). JSON Lines UTF-8/LF, 12 trường; không dùng generated input thay Sink. Tái sử dụng `from src.schemas import USER_LOG_SCHEMA`, không khai báo schema bản sao.

| Field | Spark type | Nullable | Ý nghĩa/ràng buộc |
|---|---|---|---|
| eventId | StringType | false | ID event; duy nhất trong lô, UUID v5 tái lập |
| userId | StringType | false | User synthetic, không liên quan ratings.userId |
| sessionId | StringType | false | Một user/phim/phiên |
| movieId | LongType | false | Khóa ngoại dương, <=2^63-1, tồn tại trong movies |
| action | StringType | false | view/play/pause/stop/complete |
| timestamp | StringType | false | ISO UTC YYYY-MM-DDTHH:MM:SSZ; parse sang TimestampType UTC |
| watchDuration | LongType | false | Giây mới phát sinh; view/play=0, pause/stop/complete>0 |
| sequenceNumber | LongType | false | Bắt đầu 0, tăng 1 trong phiên, <=2^63-1 |
| runId | StringType | false | ID lô mô phỏng; khác ID run vận chuyển Flume |
| isSynthetic | BooleanType | false | true |
| simulatedMovieDuration | LongType | false | 3600–10800 giây, cố định theo movieId+seed |
| durationSource | StringType | false | synthetic |

Các string định danh không rỗng. Nullable=false không tự cưỡng chế reader; kiểm null riêng. Timestamp ban đầu StringType, job dùng to_timestamp, kiểm thất bại parse và khoảng thời gian trên toàn lô. Thứ tự vật lý giữa phiên/file không bảo đảm; sort trong phiên bằng sequenceNumber. Quy tắc transition, thời lượng/completion và chống chồng giờ user trong `docs/log_schema.md`, generator và streaming validator. Spark đọc/quét mọi field, kiểm duplicate/conflict và left anti join toàn log. UUID lặp lại khi cùng seed/tham số; không mô tả duy nhất toàn cục qua nhiều lần nhập.

Ngày kiểm lại: 11/10/2026 (Asia/Saigon). Đây là sản phẩm thực thi mới tại checkout Windows hiện tại, độc lập bằng chứng lịch sử. Movies: 9.742 dòng, SHA256 `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536`. Demo/main Flume E2E và Spark kiểm toàn bộ Sink đều PASS.

| Lô mới | Run Flume | Events / unique | File / rỗng | Bytes Sink |
|---|---|---:|---:|---:|
| Demo | `run-aefc814b0b5f` | 10,000 / 10,000 | 3 / 1 | 3,433,123 |
| Main | `run-aa6b9eb58dca` | 1,000,000 / 1,000,000 | 15 / 0 | 343,339,148 |

Missing/unexpected/duplicate/conflicting ID/changed payload, UTF-8/JSON/type/provenance/action/duration, session/sequence và user overlap: đều 0 trên hai lô mới. File rỗng do rolling được giữ và thống kê, không có event; tất cả file không rỗng kết thúc bằng LF. Đối chiếu canonical payload không phụ thuộc thứ tự file/key JSON. Một lần đối chiếu thành công không chứng minh exactly-once hoặc phục hồi lỗi.

Bằng chứng: `evidence/run-aefc814b0b5f/`, `evidence/run-aa6b9eb58dca/`, `evidence/recheck-20261011-221710/spark-demo.json`, `evidence/recheck-20261011-221710/spark-main.json`, `evidence/recheck-20261011-221710/dataset_quality.json`. Audit đầy đủ: `audit/2026-10-11-221710-week1-recheck/bao-cao-nghiem-thu-tuan-1-recheck.md`. Manifest mới: `evidence/recheck-20261011-221710/delivery_manifest.json`.
