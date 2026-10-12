# Bàn giao dữ liệu cho Tuần 2

Ngày kiểm lại: 11/10/2026 (Asia/Saigon). Đây là sản phẩm thực thi mới tại checkout Windows hiện tại, độc lập bằng chứng lịch sử. Movies: 9.742 dòng, SHA256 `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536`. Demo/main Flume E2E và Spark kiểm toàn bộ Sink đều PASS.

| Lô mới | Run Flume | Events / unique | File / rỗng | Bytes Sink |
|---|---|---:|---:|---:|
| Demo | `run-aefc814b0b5f` | 10,000 / 10,000 | 3 / 1 | 3,433,123 |
| Main | `run-aa6b9eb58dca` | 1,000,000 / 1,000,000 | 15 / 0 | 343,339,148 |

Missing/unexpected/duplicate/conflicting ID/changed payload, UTF-8/JSON/type/provenance/action/duration, session/sequence và user overlap: đều 0 trên hai lô mới. File rỗng do rolling được giữ và thống kê, không có event; tất cả file không rỗng kết thúc bằng LF. Đối chiếu canonical payload không phụ thuộc thứ tự file/key JSON. Một lần đối chiếu thành công không chứng minh exactly-once hoặc phục hồi lỗi.

Bằng chứng: `evidence/run-aefc814b0b5f/`, `evidence/run-aa6b9eb58dca/`, `evidence/recheck-20261011-221710/spark-demo.json`, `evidence/recheck-20261011-221710/spark-main.json`, `evidence/recheck-20261011-221710/dataset_quality.json`. Audit đầy đủ: `audit/2026-10-11-221710-week1-recheck/bao-cao-nghiem-thu-tuan-1-recheck.md`. Manifest mới: `evidence/recheck-20261011-221710/delivery_manifest.json`.

Metadata: `data/processed/movies.csv`. Lô phân tích: `data/runs/run-aa6b9eb58dca/output/`; demo không gộp vào main. Dùng MOVIE_SCHEMA/USER_LOG_SCHEMA từ `src/schemas.py`: movieId hai bên LongType, sequenceNumber LongType, timestamp StringType chuyển TimestampType UTC, duration LongType đơn vị giây mới phát sinh. ReleaseYear IntegerType nullable; các field còn lại không null theo hợp đồng và được kiểm riêng.

```python
from src.schemas import MOVIE_SCHEMA, USER_LOG_SCHEMA
from pyspark.sql import functions as F
spark.conf.set('spark.sql.session.timeZone', 'UTC')
movies = spark.read.option('header', True).option('escape', '"').schema(MOVIE_SCHEMA).csv('data/processed/movies.csv')
events = spark.read.schema(USER_LOG_SCHEMA).json('data/runs/run-aa6b9eb58dca/output/*.jsonl')
events = events.withColumn('eventTime', F.to_timestamp('timestamp'))
# Kiểm null/orphan và eventId conflict trước dedup trong job downstream.
joined = events.join(movies, 'movieId', 'left')
```

Job QA đầy đủ `scripts/spark_smoke_test.py` đã đọc chính Sink này bằng Spark thật; mẫu trên không thay QA. Bàn giao raw/license, processed, generated manifests, Sink/log/evidence và source theo manifest; data Git ignore vẫn có local. SHA256 từng file Sink và bytes trong reconciliation/manifest. Spool copy, channel/checkpoint không dùng làm dataset cho Spark.

| Phân tích Tuần 2 | Định nghĩa |
|---|---|
| Lượt xem chi tiết | Đếm action=view |
| Phiên bắt đầu xem | Count distinct (runId,sessionId) có play; không đếm resume là lượt mới |
| Thời gian xem | SUM(watchDuration), không cộng runtime |
| Hoàn thành | Phiên complete / phiên có play, mẫu số 0 -> null |
| Phim phổ biến | Nhóm movieId rồi join title |
| Thể loại | Split genres theo `\|`, explode; nhiều thể loại có thể làm tổng tăng, ghi rõ cách tính |
| Giờ hoạt động | UTC -> Asia/Ho_Chi_Minh trước hour |

Timestamp/min/max/actions/users/movies/sessions/watch seconds và thống kê giờ bắt đầu trong manifest input và reconciliation. User/phim có trọng số; không suy chúng đại diện người dùng thật. HDFS, dashboard, job phân tích chuyên sâu và phục hồi lỗi chưa thực hiện, không thuộc nghiệm thu Tuần 1. Nhóm vẫn cần xác nhận kiến trúc theo `docs/architecture_decision_pending.md`.
