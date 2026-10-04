# Tuần 1 — Movie dataset và pipeline log Apache Flume

**Người phụ trách: Nhan Tử Mạnh.** Đề tài: “Phân tích dữ liệu phim và log hành vi người dùng trên hệ thống xem phim”.

**Trạng thái nghiệm thu Tuần 1 (cập nhật 04/10/2026):** Đã hoàn thành 100% mục tiêu Tuần 1. Apache Flume là công nghệ trọng tâm của đồ án được triển khai thành công trên Docker. Dữ liệu phim MovieLens đã chuẩn hóa (9.742 phim). Bộ sinh log hành vi người dùng hoạt động chính xác (10.000 demo events và 1.000.000 main events). Pipeline Flume (`spooldir` Source → `file` Channel → `file_roll` Sink) đã build và chạy thực tế trên Docker thành công: demo 10.000 events đạt PASS E2E (`evidence/run-a9b3a8a26afb/`), main 1.000.000 events đạt PASS E2E (`evidence/run-f63c810e9d8d/`). Kết quả reconciliation chứng minh 0 missing, 0 duplicates, 0 payload changed. Toàn bộ 12 unit tests Python PASS. Sẵn sàng bàn giao cho Thành viên 2 xác thực downstream.

## 1. Mục tiêu và kiến trúc

Chuẩn bị metadata phim và log hành vi mô phỏng phục vụ học tập, thu thập qua Flume rồi bàn giao JSONL cho nhóm PySpark downstream. Apache Flume đóng vai trò công nghệ trung tâm trong việc thu thập và vận chuyển log. Không triển khai website, đăng nhập, dashboard hay phân tích sâu tuần 2.

```text
MovieLens ZIP → raw CSV → chuẩn hóa → processed/movies.csv
                                      ↓ chọn movieId hợp lệ
generate_logs.py → generated/demo.jsonl (đóng file hoàn toàn)
 → copy .tmp → rename nguyên tử .jsonl trong spool/
 → Spooling Directory Source → File Channel → File Roll Sink
 → filesystem cục bộ: data/runs/<run-id>/output/*.jsonl
```

Đây là filesystem cục bộ được bind mount từ container, **không phải HDFS**. Không có yêu cầu bắt buộc HDFS trong đầu bài nên chọn cách triển khai đơn giản. Một triệu event mô phỏng không tự chứng minh hệ thống đạt quy mô Big Data.

## 2. Môi trường và phiên bản

| Thành phần | Lựa chọn | Kiểm chứng hiện tại |
|---|---|---|
| Python | >=3.10, thư viện chuẩn, không cần pip | Đã chạy bằng Python 3.11/3.12 đi kèm môi trường |
| Apache Flume | 1.11.0, binary chính thức, kiểm SHA512 lúc build | Đã build image và chạy thành công trên Docker (`movie-log-flume:1.11.0-local`) |
| Java trong container | Eclipse Temurin 8 JRE, `eclipse-temurin:8-jre-jammy` | Đã kiểm chứng runtime: OpenJDK 1.8.0_504 trong container Flume |
| Docker | Docker Engine + Compose v2, Linux containers | Đã kiểm chứng: Docker Engine 29.8.1 + Compose v5.5.1 hoạt động tốt |
| Hệ điều hành khảo sát | Windows 10 build 19045 / Windows 11 | `evidence/environment.json` |

Chọn Docker để cố định đường dẫn Linux và tránh cài Flume trực tiếp trên Windows. Docker Desktop cung cấp môi trường Linux containers ổn định cho pipeline Flume. Xem [yêu cầu cài Docker Desktop chính thức](https://docs.docker.com/desktop/setup/install/windows-install/).

Flume yêu cầu Java từ 8 theo [User Guide](https://flume.apache.org/FlumeUserGuide). Nguồn binary ở [Apache Downloads](https://flume.apache.org/download.html); base image ở [Docker Official Images](https://hub.docker.com/_/eclipse-temurin). Runner lưu image ID sau build để truy vết.

## 3. Cài đặt và thư mục chạy lệnh

Giải nén/chuyển cả thư mục `movie-log-bigdata` sang vị trí làm bài. **Mọi lệnh dưới đây chạy tại thư mục gốc `movie-log-bigdata`.** Mã không dùng gói Python bên ngoài; `requirements.txt` cố ý chỉ có chú thích.

**PowerShell trên Windows:** cài Python >=3.10 và Docker Desktop theo tài liệu chính thức, chọn Linux containers, mở Docker Desktop. Chạy:

```powershell
cd C:\duong-dan\movie-log-bigdata
python --version
docker version
docker compose version
python scripts/check_environment.py
```

`C:\duong-dan` là vị trí bạn đặt dự án. Nếu `python` là Windows App execution alias, dùng `py -3` hoặc đường dẫn tuyệt đối tới Python thật. Không cần cài Java trên host vì Java nằm trong image.

**Terminal Linux:** vào thư mục đã chép dự án, dùng `python3` thay `python`; kiểm tra Docker/Compose như trên. Không chạy `run_flume.sh` trực tiếp trên host: script này được Docker entrypoint gọi với đường dẫn trong container.

Gợi ý tài nguyên cho đồ án: RAM máy 8 GB trở lên, cấp khoảng 2 GB cho Docker, chừa ít nhất 5 GB đĩa. Đây là ngân sách dự kiến, chưa phải benchmark. JVM cấu hình 512 MB heap; file channel cũng dùng đĩa và bộ nhớ ngoài heap.

## 4. Dataset: tải và chuẩn hóa

Bản bàn giao đã có dữ liệu. Có thể kiểm lại snapshot mà không tải lại:

```powershell
python scripts/download_dataset.py
```

Nếu chạy từ bản mã nguồn Git sạch chưa có data:

```powershell
python scripts/download_dataset.py
python scripts/prepare_movies.py
```

Downloader giữ ZIP, README điều kiện sử dụng và CSV nguyên bản; ghi thời gian UTC, hash SHA256. Snapshot hiện có chỉ được tái sử dụng khi hash còn đúng. `prepare_movies.py` không ghi đè output đang có. Muốn chuẩn hóa lại để so sánh:

```powershell
python scripts/prepare_movies.py --output data/processed/movies-check.csv --report evidence/dataset-quality-check.json
```

Muốn tải snapshot khác: `--raw data/raw-new`, rồi truyền `--source data/raw-new/ml-latest-small/movies.csv` và một `--output` mới. Không thay raw cũ.

Nếu lỗi chứng thư TLS, cấu hình CA tin cậy của máy hoặc dùng `--ca-file C:\duong-dan\trusted-ca.pem`; không tắt kiểm chứng HTTPS. Trong phiên bàn giao, đã dùng CA gốc từ runtime Node để Python tải HTTPS có kiểm chứng; chi tiết ở `evidence/execution_commands.md`.

## 5. Sinh và kiểm tra log demo

Demo đã có sẵn `data/generated/demo.jsonl`. Lệnh tái tạo tại đường dẫn mới:

```powershell
python scripts/generate_logs.py --mode demo --output data/generated/demo-repeat.jsonl
python scripts/validate_pipeline.py --input data/generated/demo-repeat.jsonl --input-only --report evidence/demo-repeat-validation.json
python -m unittest discover -s tests -v
```

Trên bản Git sạch dùng `python scripts/generate_logs.py --mode demo` để tạo đường dẫn mặc định. Cùng seed, tham số và dataset tạo cùng nội dung/eventId. Chỉ dùng `--run-id` mới nếu muốn mô phỏng một lô độc lập; không đổi ID khi thử lại cùng một lô thất bại.

Có thể đổi `--events`, `--users`, `--start`, `--end`, `--seed`, `--output`. Timestamp bắt buộc có timezone; khoảng thời gian ít nhất 6 giờ. Mặc định mô phỏng tháng 09/2026 giờ Việt Nam, xuất UTC `Z`.

## 6. Chạy Flume và thu bằng chứng E2E

**PowerShell hoặc Terminal Linux (đổi `python` thành `python3`):**

```powershell
python scripts/run_pipeline.py --input data/generated/demo.jsonl --timeout 300
```

Runner kiểm input, build image, bật agent, đưa file đã ghi xong vào spool, chờ `.COMPLETED` và lượng output, dừng agent để đóng file, rồi đối chiếu payload/eventId. Mỗi lần chạy tạo `data/runs/run-...`, `logs/run-...`, `evidence/run-...` riêng; không xóa lần chạy trước. Có thể tăng `--timeout 900` nếu máy chậm. Thời gian build không tính trong timeout chờ dữ liệu.

Chỉ khi `evidence/<run-id>/status.json` và `reconciliation.json` cùng ghi `PASS` mới coi demo E2E đạt. Xem thêm log vận hành để xác nhận agent không lỗi cấu hình. `INPUT_PASS` chỉ xác nhận dữ liệu trước Flume.

Runner lưu: lệnh + cwd + biến mount, phiên bản Docker/Java/Flume, build log, resolved Compose, image ID, stdout/stderr container có timestamp, mẫu input/output và báo cáo đối chiếu. Sau chạy, container được dừng và gỡ; thư mục dữ liệu/channel/log/evidence giữ lại.

Nếu cần kiểm lại output, thay `run-...` bằng mã thực tế runner in ra:

```powershell
python scripts/validate_pipeline.py --input data/generated/demo.jsonl --output-dir data/runs/run-.../output --report evidence/recheck-demo.json
```

Không trộn output nhiều lần chạy khi đối chiếu một input. Source hoàn tất không có nghĩa sink đã xả hết channel; vì vậy phải chờ/dừng có kiểm soát rồi kiểm tra.

## 7. Dữ liệu chính — chỉ sau khi demo E2E đạt

```powershell
python scripts/generate_logs.py --mode main --events 1000000 --users 1000 --start 2026-09-01T00:00:00+07:00 --end 2026-10-01T00:00:00+07:00 --seed 42 --output data/generated/main.jsonl
python scripts/validate_pipeline.py --input data/generated/main.jsonl --input-only --report evidence/main-input-validation.json
python scripts/run_pipeline.py --input data/generated/main.jsonl --timeout 1800 --demo-proof evidence/run-DEMO-THUC-TE/status.json
```

Thay `run-DEMO-THUC-TE` bằng lần demo PASS thật (ví dụ `evidence/run-a9b3a8a26afb/status.json`). Thực tế lô main 1.000.000 events đã được thực thi và xác thực PASS tại `evidence/run-f63c810e9d8d/status.json`. Runner từ chối input >10.000 event nếu thiếu chứng cứ demo hợp lệ với cùng hash cấu hình. Một triệu event chiếm ~343 MB JSONL, sinh ra 254 file output qua File Roll Sink. Đổi `--events 100000` nếu tài nguyên ít; tăng số user/khoảng thời gian nếu mô phỏng quá dày. Không dùng seed khác để che lỗi kiểm thử.

## 8. Vị trí sản phẩm và xử lý lỗi

| Vị trí | Nội dung |
|---|---|
| `data/raw/` | ZIP, CSV gốc, giấy phép và manifest |
| `data/processed/movies.csv` | Metadata chuẩn hóa, thêm releaseYear |
| `data/generated/` | Input JSONL và manifest; không phải sink output |
| `data/runs/<run-id>/spool/` | File đã nạp, `.COMPLETED`, tracker |
| `data/runs/<run-id>/channel/` | File Channel, không phải dữ liệu cho Spark |
| `data/runs/<run-id>/output/` | JSONL thực tế do sink tạo |
| `logs/<run-id>/` và `evidence/<run-id>/flume-operational.log` | Log vận hành, tách khỏi event |
| `evidence/` | Kiểm tra môi trường, QA dataset/input, kiểm thử và lần chạy |
| `docs/` | Mô tả dữ liệu, schema, pipeline, báo cáo, thuyết trình, bàn giao |

| Lỗi | Cách xử lý |
|---|---|
| Docker not found / cannot connect | Cài/mở Docker, kiểm `docker version` phải thấy Server; xác nhận Linux containers |
| WSL E_ACCESSDENIED / virtualization | Kiểm tra quyền và khả năng ảo hóa với người quản trị; có thể chuyển sang máy Linux có Docker |
| Build tải Flume/CA thất bại | Xem build.log, kiểm HTTPS/CA/proxy; không bỏ kiểm hash |
| FileExistsError | Chọn output mới; không sửa file đã vào spool |
| Source không nhận file | Kiểm tên `.jsonl`, quyền mount, agent log và regex; `.tmp` cố ý bị bỏ qua |
| File channel hết đĩa/khóa | Chừa trên 100 MB, không cho hai agent dùng chung channel; không xóa checkpoint khi còn dữ liệu |
| Timeout/output thiếu | Xem log, capacity/quyền đĩa; giữ run dir để điều tra; chạy lại runner tạo vùng mới |
| Event trùng | Xem số duplicates và payload conflicts; khử trùng eventId ở Spark sau khi kiểm xung đột |
| JSON bị tách dòng | Không đưa JSON pretty-print nhiều dòng vào spool; event phải dưới giới hạn 16.384 ký tự |
| Mô phỏng quá dày | Tăng `--users` hoặc thời gian; file `.part` không được publish |

Chi tiết: [dataset](docs/dataset_description.md), [schema](docs/log_schema.md), [pipeline](docs/flume_pipeline.md), [báo cáo tuần 1](docs/week1_report.md), [thuyết trình](docs/presentation_script.md), [bàn giao PySpark](docs/week2_handoff.md).
