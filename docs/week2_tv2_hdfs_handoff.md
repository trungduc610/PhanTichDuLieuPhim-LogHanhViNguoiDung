# Hợp đồng tích hợp HDFS cho TV2

TV1 bàn giao kỹ thuật ngày 12/10/2026, chưa nhận xác nhận từ TV2. Scope là đọc HDFS và QA; không có sản phẩm tiền xử lý/phân tích/K-Means/dashboard trong lượt này.

## 1. Snapshot chính xác

- Cluster/import ID: `hdfs-385a18d3f03a`.
- Compose project: `movie-hdfs-385a18d3f03a`.
- Flume run: `run-aa6b9eb58dca` (event payload runId: `f93ca6901f8554ae127a`).
- Movies: `hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-385a18d3f03a/movies.csv`.
- Logs: `hdfs://namenode:9000/movie-log/raw/user_logs/run-aa6b9eb58dca/hdfs-385a18d3f03a`.
- Source manifest: `evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json`; SHA256 `ab6e60dfd5185229f7244cfcd581d868d3b128c5c68150a393b5b7ca249119d7`.
- 16 files, 343.872.495 bytes: metadata 9.742 rows/533.347 bytes, logs 15 parts/1.000.000 events/343.339.148 bytes. Tên/hash/expected_records từng tệp nằm trong manifest; cả 15 part đều không rỗng.
- Metadata SHA256: `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536`.

Các thư mục `/movie-log/processed`, `/movie-log/results` đã tồn tại, chưa có output phân tích. TV2 nên ghi output vào namespace theo run mới; không sửa raw snapshot đã nghiệm thu. Không đổi expected count theo count quan sát.

## 2. Schema và ý nghĩa dữ liệu

Import trực tiếp `MOVIE_SCHEMA`, `USER_LOG_SCHEMA` từ `src/schemas.py`. Không tự suy schema từ mẫu JSON. Schema đầy đủ đã lưu cả contract và schema thực đọc trong `spark-hdfs.json`.

| Dataset | Fields/type |
|---|---|
| Movies | movieId long; title string; genres string; releaseYear integer nullable |
| Logs | eventId/userId/sessionId/action/timestamp/runId/durationSource string; movieId/watchDuration/sequenceNumber/simulatedMovieDuration long; isSynthetic boolean |

13 releaseYear null hợp lệ; 34 genre `(no genres listed)` giữ nguyên upstream. CSV UTF-8, header=true, quote/escape `"`, hỗ trợ title có dấu phẩy/quote. JSONL một object mỗi dòng. Timestamp UTC Z; parse sang TimestampType với Spark session timezone UTC. `watchDuration` là số giây phát sinh từ play gần nhất, không cộng dồn trong record; các action view/play có duration 0. `isSynthetic=true`, `durationSource=synthetic`; runtime phim synthetic từ 3.600 tới 10.800 giây. Khoảng thời gian event thực: `2026-08-31T17:00:04Z`–`2026-09-30T15:58:22Z`.

Required fields phải kiểm bằng action dữ liệu, không dựa `nullable=False`. movieId hai phía phải cùng LongType; kiểm malformed CSV/JSON, null/type, IDs trùng/conflict, orphan join, timestamp/action/duration/provenance và sessions. Job TV1 đã kiểm toàn lô, 23 nhóm lỗi đều 0; không fallback file local/generated.

## 3. Chạy trong PowerShell tại root project

Docker Desktop/Engine phải hoạt động ở `desktop-linux`; không sửa WSL hay cấu hình bảo mật. Giữ ID đúng để dùng lại cluster và hai named volume đã kiểm. Lệnh dưới chỉ bật NameNode/DataNode, không bật Flume.

```powershell
$env:HDFS_RUN_ID='hdfs-385a18d3f03a'
docker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a up -d namenode datanode
docker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a ps
docker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a exec -T namenode hdfs dfsadmin -report
docker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a exec -T namenode hdfs dfsadmin -safemode get
```

Kiểm Live datanodes (1), safe mode OFF trước đọc. Không chạy `namenode -format`, `down -v` hoặc `-put -f`. Script service tự từ chối nonempty unformatted volume/cluster khác. ID mới chỉ dành cho triển khai mới bằng `scripts/run_hdfs.py`, không thay ID của cluster hiện hữu.

Mỗi QA report phải có tên mới. Ví dụ (UUID không chứa dữ liệu cá nhân):

```powershell
$qaId=[guid]::NewGuid().ToString('N')
docker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a --profile spark run --rm --no-deps spark --driver-memory 2g scripts/spark_hdfs_validate.py --source-manifest evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json --hdfs-verification evidence/week2-hdfs/hdfs-385a18d3f03a/content-after-restart.json --report "evidence/week2-hdfs/hdfs-385a18d3f03a/spark-tv2-$qaId.json"
```

Job dùng manifest và PASS content report đúng hash, truy cập HDFS thật; metadata thay đổi sẽ bị bytes/list/QA kiểm. Trước nghiệm thu snapshot mới hoặc khi nghi dữ liệu thay đổi, đọc toàn bộ byte lại:

```powershell
$hashId=[guid]::NewGuid().ToString('N')
docker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a --profile spark run --rm --no-deps spark --driver-memory 1g scripts/hdfs_hash_verify.py --source-manifest evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json --report "evidence/week2-hdfs/hdfs-385a18d3f03a/hashes-tv2-$hashId.json"
```

Không dùng `localhost:9000` từ Spark để chỉ container NameNode khác. Host chỉ có UI loopback 19870; RPC 9000 và DataNode transfer 9866 liên lạc qua Docker network cùng project. Spark container bên ngoài cần join network này, dùng XML config hiện tại và có Hadoop client tương thích; không tự coi chỉ nối RPC là đọc block được.

## 4. Bằng chứng và giới hạn

- `content-import.json`: toàn lô được cat binary, SHA256, CSV/JSON parser kiểm sau upload.
- `content-after-restart.json`: cùng phép kiểm toàn lô sau restart.
- `persistence-reviewed.json`: mọi Java metadata properties không đổi; FAIL so comment lịch sử được giữ tại `persistence.json`.
- `spark-hdfs.json`: Spark 3.5.1/Hadoop client 3.3.4/Java 11.0.22/Python 3.8.10, actual filesystem HDFS, `input_file_name`, full fields và 23 nhóm lỗi 0.
- `final-hdfs-hashes.json`: kiểm byte/hash độc lập bằng Java Hadoop client trước đóng gói.
- `screenshots/namenode-full-page.jpg`: screenshot UI thực.
- `delivery_manifest.json`: scope/exclusions và bytes/SHA256 của tệp local; remote HDFS kiểm riêng bằng job nêu trên. Volumes không nằm trong gói portable.

HDFS server 3.3.6/Java 1.8.0_212, một DataNode và replication 1, simple authentication, root trong container; môi trường demo một máy, không HA/chịu lỗi hoặc endpoint công khai. Named volumes đang được giữ. Chưa có TV2 xác nhận đã đọc/tích hợp và chưa có phê duyệt nhóm cho kiến trúc hoặc giới thiệu/cơ sở lý thuyết Tuần 1. Những xác nhận đó không được thay bằng QA kỹ thuật của TV1.
