# Lệnh thực tế trong phiên bàn giao

Thời điểm: 03/10/2026, giờ Việt Nam. Shell: PowerShell. Tất cả dữ liệu được tạo trong thư mục outputs của cuộc trò chuyện.

## Khảo sát

Tại `C:\Users\User\Documents\Codex\2026-10-03\files-pasted-by-the-user-b` đã liệt kê file và `Get-Command python,python3,java,docker,wsl,git`; thử `python --version`, `java -version`, `docker version`, `wsl --status`. Kết quả: Python App alias không mở được, không thấy Java/Docker, WSL từ chối truy cập. Chỉ có thư mục outputs/work, không có dự án cần bảo toàn bên trong outputs/movie-log-bigdata trước khi tạo.

## Runtime và tải HTTPS

Python thực dùng trong phiên này:

```powershell
$py = 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$node = 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
cd C:\Users\User\Documents\Codex\2026-10-03\files-pasted-by-the-user-b\outputs\movie-log-bigdata
```

Lần tải ban đầu bằng PowerShell bị chặn socket. Sau khi quyền mạng được cấp, PowerShell/curl gặp lỗi cơ chế chứng thư Windows và Python mặc định thiếu CA tin cậy. Node fetch HTTPS có xác thực thành công. Đã xuất CA gốc công khai đi kèm Node (không phải chứng thư riêng/khóa bí mật) và **chạy downloader thật**:

```powershell
& $node -e "require('fs').writeFileSync('../../work/trusted-ca.pem',require('tls').rootCertificates.join('\n'))"
& $py scripts/download_dataset.py --ca-file ../../work/trusted-ca.pem
```

TLS được kiểm chứng; không dùng verify=false. CA tạm nằm trong work của cuộc trò chuyện, không phải sản phẩm dữ liệu. Trên máy thông thường `python scripts/download_dataset.py` dùng CA hệ thống. Manifest ghi lần tải Python chính thức và hash từng file.

## Xử lý và kiểm thử

```powershell
& $py scripts/prepare_movies.py
& $py scripts/generate_logs.py --mode demo
& $py scripts/validate_pipeline.py --input data/generated/demo.jsonl --input-only --report evidence/demo_input_validation.json
& $py scripts/check_environment.py
& $py -m unittest discover -s tests -v 2>&1 | Tee-Object -FilePath evidence/tests.txt
& $py scripts/run_pipeline.py 2>&1 | Tee-Object -FilePath evidence/pipeline_attempt.txt
```

Các lệnh dữ liệu và unit test đạt; run_pipeline trả exit code 1 với BLOCKED_ENVIRONMENT. Không có Docker command nào đã chạy trong lần này. `commands.json` của run có danh sách rỗng là đúng: runner dừng tại kiểm tra executable.

Sau bổ sung kiểm tra giới hạn chiều dài dòng cho validator, đã chạy lại suite và kiểm tra input; `tests.txt` và `demo_input_validation.json` lưu kết quả bản cuối. Không chạy main một triệu event vì chưa qua demo E2E.
