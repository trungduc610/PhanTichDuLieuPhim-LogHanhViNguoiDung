# Phân tích dữ liệu phim và log hành vi người dùng

Apache Flume thu thập log; HDFS lưu snapshot để Spark/PySpark đọc ở Tuần 2.

## Pipeline HDFS Tuần 2

```text
Movies metadata ------------------------------> HDFS raw/movies ---+
User Log -> Flume -> local File Roll Sink -> HDFS raw/user_logs ----+-> Spark/PySpark
```

Run nguồn đang chọn: **run-f63c810e9d8d**, reconciliation PASS, 254 Sink parts,
1.000.000 events. Generated input chỉ đối chiếu lineage; user log upload luôn là
Flume Sink output. Số parts lấy từ reconciliation, không cố định trong code.

[Hướng dẫn HDFS hiện tại](docs/week2_tv2_hdfs_handoff.md),
[kiến trúc Tuần 2](docs/week2_system_architecture.md),
[cơ sở HDFS và lần nghiệm thu trước](docs/week2_tv1_hdfs_report.md).
Chỉ kết luận HDFS/Spark PASS khi report của cluster hiện tại xác minh thành công;
receipt từ máy trước không chứng minh runtime đang chạy ở checkout này.

```powershell
python -B scripts/run_hdfs.py --flume-run-id run-f63c810e9d8d --audit-dir evidence/week2-hdfs/check-new
```

Dùng Python >=3.10 và audit-dir mới. Runner tạo cluster/project/volumes riêng và
source manifest mới. Import và Spark QA theo context: xem hướng dẫn HDFS ở trên.
Các phần/local Spark smoke test phía dưới thuộc **Tuần 1 và snapshot lịch sử**.

## Kết quả thực thi Tuần 1 đã lưu

Ngày kiểm lại: 11/10/2026 (Asia/Saigon). Đây là sản phẩm thực thi mới tại checkout Windows hiện tại, độc lập bằng chứng lịch sử. Movies: 9.742 dòng, SHA256 `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536`. Demo/main Flume E2E và Spark kiểm toàn bộ Sink đều PASS.

| Lô mới | Run Flume | Events / unique | File / rỗng | Bytes Sink |
|---|---|---:|---:|---:|
| Demo | `run-aefc814b0b5f` | 10,000 / 10,000 | 3 / 1 | 3,433,123 |
| Main | `run-aa6b9eb58dca` | 1,000,000 / 1,000,000 | 15 / 0 | 343,339,148 |

Missing/unexpected/duplicate/conflicting ID/changed payload, UTF-8/JSON/type/provenance/action/duration, session/sequence và user overlap: đều 0 trên hai lô mới. File rỗng do rolling được giữ và thống kê, không có event; tất cả file không rỗng kết thúc bằng LF. Đối chiếu canonical payload không phụ thuộc thứ tự file/key JSON. Một lần đối chiếu thành công không chứng minh exactly-once hoặc phục hồi lỗi.

Bằng chứng: `evidence/run-aefc814b0b5f/`, `evidence/run-aa6b9eb58dca/`, `evidence/recheck-20261011-221710/spark-demo.json`, `evidence/recheck-20261011-221710/spark-main.json`, `evidence/recheck-20261011-221710/dataset_quality.json`. Audit đầy đủ: `audit/2026-10-11-221710-week1-recheck/bao-cao-nghiem-thu-tuan-1-recheck.md`. Manifest mới: `evidence/recheck-20261011-221710/delivery_manifest.json`.

MovieLens là metadata/rating nguồn GroupLens; log `sim-user-*` là synthetic do generator tạo. `watchDuration` là giây mới phát sinh từ play gần nhất; runtime phim cũng synthetic. Không kết luận về người xem thật.

## Luồng và runtime Tuần 1

```text
MovieLens -> prepare_movies -> movies.csv -----------------------+
                                                               v
Generator -> spooldir Source -> File Channel -> File Roll Sink -> Spark QA
                                                               |
                                             Tuần 2: phân tích -> Dashboard
```

Host Windows 10 build 19045 dùng Python 3.12.14 thật tại `C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`; alias WindowsApps không dùng. Docker Desktop 4.88.1, Client/Engine 29.7.2, Compose v5.4.0, context desktop-linux, Linux containers, 4 CPU / 7,486 GiB Docker memory. Flume 1.11.0 chạy Temurin Java 1.8.0_504; agent thực ghi InitialHeapSize 134.217.728 và MaxHeapSize 536.870.912 byte. Spark/PySpark 3.5.1, Python 3.8.10, Java 11.0.22, master local[2], driver 2 GiB trong `apache/spark:3.5.1`. Host không cần PySpark/Java; scripts host dùng stdlib. Phiên bản/digest thực đo nằm trong execution logs và image-inspect; tag có thể thay đổi nên giữ image ID/digest khi bàn giao.

File Channel dùng volume Linux riêng theo Compose project; runner xuất checkpoint/data về `data/runs/<run-id>/channel/` sau khi dừng. Volume được giữ lại. Sink/spool bind vào thư mục run trên host; Storage là filesystem local, không HDFS. Không chạy hai lần trong cùng Compose project/channel.

## Chạy và kiểm lại Tuần 1

Trong PowerShell đặt `$py` là executable Python thật ở trên (hoặc Python >=3.10 có sẵn). Chạy ở thư mục project; Linux dùng `python3`. Không cần pip cho scripts host; Spark chạy từ service container có sẵn dependency.

```powershell
& $py scripts/check_environment.py --report evidence/environment-new.json
& $py scripts/download_dataset.py
& $py scripts/prepare_movies.py --output data/processed/movies-repeat.csv --report evidence/movies-repeat.json
& $py -m unittest discover -s tests -v
& $py scripts/generate_logs.py --mode demo --output data/generated/demo-repeat.jsonl
& $py scripts/run_pipeline.py --input data/generated/demo-repeat.jsonl --timeout 600
```

Downloader tái sử dụng snapshot đã có sau kiểm hash; không ghi đè raw. Mọi output/report phải là đường dẫn mới chưa tồn tại. Nếu cần CA, truyền `--ca-file` với bundle tin cậy; giữ HTTPS verification. Bản tải mới 11/10 đã dùng root CA public từ runtime Node, không tắt TLS.

Chỉ sinh/chạy main sau demo E2E PASS với cùng source/config. Trong checkout này main đã có; chọn tên khác nếu sinh lại. Thay `run-DEMO-MOI` bằng run thực sự mới vừa PASS; bằng chứng lịch sử thiếu hash snapshot không được runner chấp nhận.

```powershell
& $py scripts/generate_logs.py --mode main --events 1000000 --output data/generated/main-repeat.jsonl
& $py scripts/run_pipeline.py --input data/generated/main-repeat.jsonl --timeout 1800 --demo-proof evidence/run-DEMO-MOI/status.json
& $py scripts/validate_pipeline.py --input data/generated/main.jsonl --output-dir data/runs/run-aa6b9eb58dca/output --report evidence/main-recheck-new.json
docker compose -p movie-spark-recheck run --rm spark --driver-memory 2g scripts/spark_smoke_test.py --movie-report evidence/recheck-20261011-221710/dataset_quality.json --run-evidence evidence/run-aa6b9eb58dca --report evidence/spark-recheck-new.json
& $py scripts/create_delivery_manifest.py --verify evidence/recheck-20261011-221710/delivery_manifest.json
```

Lệnh Spark kiểm hash và file list của đúng Sink run PASS, dùng schema từ `src/schemas.py`, action đọc tất cả fields, parse timestamp UTC, kiểm null/type/duplicate/full left anti join/session. Expected count lấy từ manifest/reconciliation đã xác minh, không lấy count quan sát để tạo PASS. `INPUT_PASS`, `.COMPLETED`, count và mẫu join không thay E2E reconciliation.

Runner tạo run/project/output/evidence riêng, publish `.tmp` đóng xong rồi rename cùng spool, lưu argv/cwd/UTC/exit/logs/source hashes/launcher/heap/counters/images/Compose. Dừng và gỡ container/network của chính run; giữ volume/channel/data. Build không tính vào timeout drain. Khoảng 12 GB đĩa dự kiến cho images, generated/spool/Sink, channel/export và SQLite; máy thực đo có 16 GB RAM và trên 60 GB đĩa trống. Không dùng `docker system prune`.

## Bàn giao Tuần 1 (lịch sử)

`data/raw/` có ZIP/CSV/README license/manifest; `data/processed/` có movies; `data/generated/` có input/manifest. Dữ liệu phân tích là `data/runs/run-aa6b9eb58dca/output/`; demo `run-aefc814b0b5f` chỉ dùng kiểm thử. `logs/<run>/` và `evidence/<run>/` là log/bằng chứng, không phải event input. Không gộp demo/main như hai lịch sử người dùng độc lập.

Data/logs bị Git ignore nhưng thực sự tồn tại local, phải chép cùng source và evidence theo manifest khi bàn giao. Manifest loại spool bản copy, channel, temporary/fixtures, CA public tạm, history không được chọn và chính manifest; scope/exclusions được lưu trong JSON. Bằng chứng FAIL/BLOCKED/PASS cũ và audit cũ giữ nguyên, không dùng thay kết quả hiện tại.

Tài liệu: [dataset](docs/dataset_description.md), [log](docs/log_schema.md), [movie schema](docs/movie_schema.md), [log schema](docs/user_log_schema.md), [Flume](docs/flume_pipeline.md), [kiến trúc](docs/system_architecture.md), [quyết định chờ nhóm](docs/architecture_decision_pending.md), [chất lượng](docs/data_quality_report.md), [bàn giao Tuần 2](docs/week2_handoff.md).

## TV2 Tuần 2 — Spark analysis và K-Means

Run thực thi **tv2-4ed70c10cd84**: **PASS**, đọc HDFS thật; 9.742 movies,
1.000.000 raw/clean/joined events, 1.000 users. K=2..6 được đo bằng Spark MLlib;
chọn **K=2**, silhouette **0.6707563871905433**, cluster sizes **237 / 763**.
Raw snapshot và file TV1 được bảo vệ giữ nguyên hash.

[Báo cáo TV2](docs/week2_tv2_processing_report.md) ·
[Hướng dẫn chạy TV2](docs/week2_tv2_run_guide.md) ·
[Evidence PASS](evidence/week2-tv2/tv2-4ed70c10cd84/run_status.json).
Output Parquet và CSV/JSON đã sẵn sàng cho Dashboard; namespace run và manifest
được ghi trong evidence. Model đã save/reload trên HDFS và kiểm assignment.

```powershell
python -B scripts/run_tv2.py --hdfs-context evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json
```

Runner tạo TV2 run mới; default driver heap 1536m, seed lấy từ event manifest.
Dùng Python executable thật nếu WindowsApps alias không hoạt động.
