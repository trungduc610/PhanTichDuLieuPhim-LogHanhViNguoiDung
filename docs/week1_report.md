# Báo cáo Tuần 1 cập nhật sau thực thi

Ngày kiểm lại: 11/10/2026 (Asia/Saigon). Đây là sản phẩm thực thi mới tại checkout Windows hiện tại, độc lập bằng chứng lịch sử. Movies: 9.742 dòng, SHA256 `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536`. Demo/main Flume E2E và Spark kiểm toàn bộ Sink đều PASS.

| Lô mới | Run Flume | Events / unique | File / rỗng | Bytes Sink |
|---|---|---:|---:|---:|
| Demo | `run-aefc814b0b5f` | 10,000 / 10,000 | 3 / 1 | 3,433,123 |
| Main | `run-aa6b9eb58dca` | 1,000,000 / 1,000,000 | 15 / 0 | 343,339,148 |

Missing/unexpected/duplicate/conflicting ID/changed payload, UTF-8/JSON/type/provenance/action/duration, session/sequence và user overlap: đều 0 trên hai lô mới. File rỗng do rolling được giữ và thống kê, không có event; tất cả file không rỗng kết thúc bằng LF. Đối chiếu canonical payload không phụ thuộc thứ tự file/key JSON. Một lần đối chiếu thành công không chứng minh exactly-once hoặc phục hồi lỗi.

Bằng chứng: `evidence/run-aefc814b0b5f/`, `evidence/run-aa6b9eb58dca/`, `evidence/recheck-20261011-221710/spark-demo.json`, `evidence/recheck-20261011-221710/spark-main.json`, `evidence/recheck-20261011-221710/dataset_quality.json`. Audit đầy đủ: `audit/2026-10-11-221710-week1-recheck/bao-cao-nghiem-thu-tuan-1-recheck.md`. Manifest mới: `evidence/recheck-20261011-221710/delivery_manifest.json`.

Host Windows 10 build 19045 dùng Python 3.12.14 thật tại `C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`; alias WindowsApps không dùng. Docker Desktop 4.88.1, Client/Engine 29.7.2, Compose v5.4.0, context desktop-linux, Linux containers, 4 CPU / 7,486 GiB Docker memory. Flume 1.11.0 chạy Temurin Java 1.8.0_504; agent thực ghi InitialHeapSize 134.217.728 và MaxHeapSize 536.870.912 byte. Spark/PySpark 3.5.1, Python 3.8.10, Java 11.0.22, master local[2], driver 2 GiB trong `apache/spark:3.5.1`. Host không cần PySpark/Java; scripts host dùng stdlib. Phiên bản/digest thực đo nằm trong execution logs và image-inspect; tag có thể thay đổi nên giữ image ID/digest khi bàn giao.

18 unit tests host và 9 kiểm thử Spark fixture đạt. Fixture không phải Sink evidence. Toàn bộ source/config/tests/docs cuối được đọc lại, dữ liệu toàn lô được đối chiếu độc lập, manifest kiểm bytes/SHA256. Xác nhận kiến trúc nhóm vẫn thiếu: TV2-06 ĐẠT MỘT PHẦN. Báo cáo này ghi kết quả tự động kiểm lại, không xác nhận thay đóng góp hoặc phê duyệt của cá nhân.
