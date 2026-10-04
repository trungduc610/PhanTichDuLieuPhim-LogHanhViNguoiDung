# Bằng chứng và cách hoàn tất

Các file hiện có là dữ liệu/đầu ra kiểm tra thực tế, không phải ảnh hay log Flume dựng lại:

- `environment.json`: công cụ và exit code khảo sát.
- `dataset_quality.json`: thống kê từ CSV tải thật.
- `demo_input_validation.json`: kiểm input, không đối chiếu sink.
- `tests.txt`: 12 test Python; mock-sink là fixture tạm, không nằm trong data/output.
- `input-sample.jsonl`: năm dòng đầu input thực tế.
- `pipeline_attempt.txt`, `run-62b191534ce6/status.json`: E2E bị chặn vì không thấy Docker.
- `execution_commands.md`: lệnh đã dùng trong phiên bàn giao.

Không có `flume-operational.log`, sample output hay ảnh thành công ở lần bị chặn. Không coi output=0 trong chế độ input_only là mất 10.000 event; chưa đo đầu ra.

Trên máy có Docker, runner tạo bằng chứng tại một thư mục run mới. Giữ nguyên bằng chứng cũ, không thay nội dung BLOCKED bằng PASS. Sau khi chạy, chụp các màn hình thật bằng Snipping Tool/Print Screen:

1. Terminal hiển thị phiên bản Docker, Java, Flume đã ghi trong evidence.
2. Mở `flume-operational.log`, vùng agent/source/channel/sink khởi động; xem toàn log để không bỏ sót lỗi.
3. Thư mục spool có file `.COMPLETED` và thư mục output có các part do Flume tạo.
4. Mở input-sample/output-sample của run và `reconciliation.json`: số input/output/unique/missing/duplicates/invalid, cùng status PASS.

Đặt ảnh `evidence/<run-id>/screenshots/01-runtime.png`… Không vẽ lại terminal, sửa số liệu hoặc dùng ảnh fixture làm bằng chứng.
