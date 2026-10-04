# Schema dữ liệu User Behavior Log (Log hành vi người dùng)

## 1. Nguồn dữ liệu
* **File nguồn**: Output thực tế được sinh ra bởi Apache Flume Sink:
  * Run Main (chính thức): [`data/runs/run-f63c810e9d8d/output/*.jsonl`](file:///d:/Code/Bigdata/movie-log-bigdata-week1/movie-log-bigdata/data/runs/run-f63c810e9d8d/output) (1.000.000 bản ghi trên 254 files)
  * Run Demo (kiểm thử nhanh): [`data/runs/run-a9b3a8a26afb/output/*.jsonl`](file:///d:/Code/Bigdata/movie-log-bigdata-week1/movie-log-bigdata/data/runs/run-a9b3a8a26afb/output) (10.000 bản ghi trên 4 files)
* **Định dạng**: JSON Lines (UTF-8, mỗi dòng một JSON object hợp lệ kết thúc bằng `\n`).
* **Vai trò trong hệ thống**: Đây là luồng dữ liệu trung tâm của đồ án, được thu thập và vận chuyển bền vững qua **Apache Flume** (`spooldir` Source → `file` Channel → `file_roll` Sink) trước khi lưu vào filesystem để Spark/PySpark đọc.

## 2. Bảng đặc tả Schema

| Field | Spark Type | Nullable | Ý nghĩa | Ràng buộc nghiệp vụ |
|---|---|---|---|---|
| `eventId` | `StringType` | `false` | Khóa định danh duy nhất của event | UUID v5 từ run + session + sequence; duy nhất toàn cục. |
| `userId` | `StringType` | `false` | Mã định danh người dùng mô phỏng | Định dạng `sim-user-XXXXXX` (tập 1.000 user). |
| `sessionId` | `StringType` | `false` | Mã định danh phiên xem của người dùng | UUID v5 đại diện 1 user xem 1 phim trong 1 chuỗi hành vi liên tục. |
| `movieId` | `LongType` | `false` | Mã định danh phim được tương tác | Khóa ngoại kết nối với `movies.csv` (`join key`). 100% khớp danh sách phim hợp lệ. |
| `action` | `StringType` | `false` | Hành vi của người dùng trên phim | 5 hành vi hợp lệ: `view`, `play`, `pause`, `stop`, `complete`. |
| `timestamp` | `StringType` | `false` | Thời điểm phát sinh sự kiện | Chuỗi chuẩn ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`), tăng đơn điệu trong phiên. Đọc ban đầu dạng String rồi chuyển `TimestampType`. |
| `watchDuration` | `LongType` | `false` | Số giây xem phát sinh từ lượt `play` gần nhất | Giá trị nguyên `>= 0`. Bằng 0 với `view`/`play`; > 0 với `pause`/`stop`/`complete`. Không phải thời lượng lũy kế. |
| `sequenceNumber` | `LongType` | `false` | Thứ tự bước thực hiện trong phiên | Bắt đầu từ 0, tăng 1 theo từng hành vi trong cùng `sessionId`. |
| `runId` | `StringType` | `false` | Mã định danh lần sinh dữ liệu | Định danh lô mô phỏng. |
| `isSynthetic` | `BooleanType` | `false` | Cờ đánh dấu dữ liệu mô phỏng | Luôn mang giá trị `true`. |
| `simulatedMovieDuration` | `LongType` | `false` | Thời lượng phim giả lập | Cố định theo `movieId` (từ 3.600 đến 10.800 giây = 1 đến 3 tiếng). |
| `durationSource` | `StringType` | `false` | Nguồn thời lượng phim | Luôn mang giá trị `"synthetic"`. |

## 3. Khai báo Schema bằng PySpark (StructType)

```python
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    LongType,
    BooleanType,
)

USER_LOG_SCHEMA = StructType([
    StructField("eventId", StringType(), nullable=False),
    StructField("userId", StringType(), nullable=False),
    StructField("sessionId", StringType(), nullable=False),
    StructField("movieId", LongType(), nullable=False),
    StructField("action", StringType(), nullable=False),
    StructField("timestamp", StringType(), nullable=False),
    StructField("watchDuration", LongType(), nullable=False),
    StructField("sequenceNumber", LongType(), nullable=False),
    StructField("runId", StringType(), nullable=False),
    StructField("isSynthetic", BooleanType(), nullable=False),
    StructField("simulatedMovieDuration", LongType(), nullable=False),
    StructField("durationSource", StringType(), nullable=False),
])
```

## 4. Hướng dẫn đọc bằng PySpark

```python
from pyspark.sql import functions as F

logs_df = (
    spark.read
    .option("mode", "FAILFAST")
    .schema(USER_LOG_SCHEMA)
    .json("data/runs/run-f63c810e9d8d/output/*.jsonl")
)

# Chuyển đổi timestamp sang TimestampType chuẩn UTC
logs_df = logs_df.withColumn("eventTime", F.to_timestamp("timestamp"))
```
