# Báo cáo tuần 1 — Nhan Tử Mạnh

Đề tài: Phân tích dữ liệu phim và log hành vi người dùng trên hệ thống xem phim.

Ngày cập nhật nghiệm thu: 04/10/2026, múi giờ Asia/Saigon.

## Công việc và kết quả

Đã khảo sát môi trường và chọn Docker/Linux containers cho toàn bộ pipeline để đảm bảo khả năng tái lập. Ngày 04/10/2026, trên môi trường Docker hoạt động ổn định, Apache Flume 1.11.0 (công nghệ trọng tâm của đồ án) đã được build và chạy thành công trên container. Toàn bộ luồng Source → Channel → Sink hoạt động ổn định, xử lý thành công cả tập log demo (10.000 events) và tập log chính (1.000.000 events).

Đã tải MovieLens latest-small từ GroupLens qua HTTPS có kiểm chứng. ZIP được giữ nguyên cùng README nguồn. CSV thực tế có 9.742 phim, 100.836 rating, 3.683 tag, 9.742 liên kết. Chuẩn hóa metadata riêng, không sửa raw; bổ sung releaseYear từ hậu tố năm hợp lệ, để null cho 13 phim không khớp. 34 phim không có thể loại được khai báo, 0 ID trùng, không thấy lỗi giải mã/cấu trúc CSV. Có 11 dòng thay đổi bởi chuẩn hóa.

Đã xây dựng bộ sinh JSONL với eventId, userId, sessionId, movieId, action, timestamp UTC và watchDuration dạng thời lượng phát sinh. Trạng thái phiên hợp lý, không xem chồng giờ cùng user, runtime ghi rõ synthetic. Có trọng số phim phổ biến, mức độ hoạt động user, khung giờ cao điểm. Ghi từng phiên ra file nên không giữ toàn bộ JSONL trong RAM. Metadata/rating gốc khác với log mô phỏng.

Đã tạo cấu hình Source spooldir, File Channel, File Roll Sink, Dockerfile kiểm SHA512, Compose và runner đầu cuối. Sink mục tiêu là filesystem cục bộ lưu trữ các file JSONL. Có script kiểm schema, khóa phim, trình tự phiên, thời lượng, eventId và đối chiếu payload với output. Runner lưu log và bằng chứng tự động.

## Kiểm thử thực tế

| Hạng mục | Kết quả thực tế | Bằng chứng |
|---|---|---|
| Dataset tải/chuẩn hóa | PASS, 9.742 phim | download_manifest.json, dataset_quality.json |
| Input demo | INPUT_PASS | demo_input_validation.json |
| Event input / ID duy nhất | 10.000 / 10.000 | demo_input_validation.json |
| Event input trùng / sai | 0 / 0 | demo_input_validation.json |
| Phiên hợp lệ / sai / chồng | 3.058 / 0 / 0 | demo_input_validation.json |
| Bộ kiểm thử Python | 12 test PASS | evidence/tests.txt |
| Flume E2E Demo | PASS (10.000 events) | evidence/run-a9b3a8a26afb/status.json, reconciliation.json |
| Output sink / ID duy nhất (Demo) | 10.000 / 10.000 | 4 files jsonl tại data/runs/run-a9b3a8a26afb/output/ |
| Event thiếu/trùng/sai tại sink | 0 thiếu / 0 trùng / 0 sai | Khớp 100% payload input, không mất mát |
| Log khởi động Flume / container | Đã ghi nhận | evidence/run-a9b3a8a26afb/flume-operational.log |
| Main 1.000.000 event Flume E2E | PASS (1.000.000 events) | evidence/run-f63c810e9d8d/status.json, reconciliation.json (254 files) |

Demo có 861 user hoạt động trong tập 1.000 user, 1.664 phim xuất hiện. Action: 3.058 view, 3.471 play (gồm resume), 904 pause, 1.177 stop, 1.390 complete. Số phiên đã bắt đầu xem là 2.567; không dùng số play để thay cho số phiên bắt đầu.

Kiểm thử gồm số event biên, tính lặp lại theo seed, UTF-8 sai, movieId trùng/không tồn tại, duration bị sửa, event thiếu/trùng/payload thay đổi, output rỗng và việc không ghi đè file. Toàn bộ 12 unit tests PASS. Pipeline E2E chạy thực tế trên Docker đã đối chiếu thành công 100% payload từng eventId giữa input và output.

Không phát hiện eventId trùng trong cả input và output của đợt chạy. eventId được dùng để nhận diện và phục vụ downstream khử trùng nếu hệ thống có chạy lại.

## Đánh giá và bàn giao tuần 1

1. Môi trường Docker Desktop / Linux containers đã đáp ứng hoàn toàn yêu cầu chạy Flume.
2. Pipeline thu thập log Apache Flume hoạt động ổn định, tin cậy, lưu trữ bền vững với File Channel và xuất file JSONL chuẩn qua File Roll Sink.
3. Dữ liệu output Flume thực tế đạt 10.000 events (demo) và 1.000.000 events (main), sẵn sàng cho Thành viên 2 và Thành viên 3 tiếp nhận xử lý ở Tuần 2.
4. Mọi bằng chứng status, reconciliation, logs và container images được lưu vết đầy đủ trong thư mục `evidence/`.

## Danh sách bàn giao

- README.md, requirements.txt, .gitignore, .gitattributes, .dockerignore.
- Dockerfile, compose.yaml, config/flume.conf.
- scripts/: common.py, download_dataset.py, prepare_movies.py, generate_logs.py, validate_pipeline.py, run_pipeline.py, run_flume.sh, verify_archive.py, check_environment.py.
- tests/test_project.py và evidence/tests.txt.
- data/raw/: ZIP, manifest, README và bốn CSV gốc; data/processed/movies.csv.
- data/generated/demo.jsonl và manifest; evidence/input-sample.jsonl.
- data/runs/run-a9b3a8a26afb/output/: 4 file JSONL output demo Flume thật.
- data/runs/run-f63c810e9d8d/output/: 254 file JSONL output main Flume thật (1M events).
- evidence/: môi trường, QA, bằng chứng E2E PASS, log container và reconciliation.
- docs/: dataset_description.md, log_schema.md, flume_pipeline.md, week1_report.md, presentation_script.md, week2_handoff.md.

Thư mục output chứa dữ liệu Flume thực tế đã qua xử lý của Sink. Bàn giao đầy đủ cho Thành viên 2 theo hợp đồng dữ liệu tại `docs/week2_handoff.md`.
