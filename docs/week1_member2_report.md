# Báo cáo Tuần 1 — Thành viên 2

**Người thực hiện**: Thành viên 2 (Kỹ sư Dữ liệu PySpark Downstream).  
**Đề tài**: “Phân tích dữ liệu phim và log hành vi người dùng trên hệ thống xem phim”.  
**Trọng tâm công nghệ của đồ án**: **Apache Flume** là công nghệ cốt lõi của luồng thu thập log; Spark/PySpark đóng vai trò hạ tầng hỗ trợ phía sau (downstream) để kiểm tra, làm sạch và phân tích dữ liệu sau khi Flume đã kết xuất thành công.

---

## 1. Dữ liệu đầu vào

### Movie Dataset (Metadata phim):
* **Đường dẫn**: `data/processed/movies.csv`
* **Nguồn**: MovieLens Latest Small (GroupLens, Đại học Minnesota).
* **Số lượng bản ghi**: 9.742 phim.
* **Định dạng**: CSV (UTF-8, delimiter `,`).
* **Đặc điểm**: Dữ liệu metadata tĩnh, độc lập và **không đi qua Apache Flume**.

### User Behavior Log (Log hành vi người dùng):
* **Đường dẫn chính thức**: `data/runs/run-f63c810e9d8d/output/*.jsonl` (254 files) và tập demo `data/runs/run-a9b3a8a26afb/output/*.jsonl` (4 files).
* **Trạng thái thu thập**: Đã đi qua trọn vẹn pipeline Apache Flume (`spooldir` Source → `file` Channel → `file_roll` Sink).
* **Số lượng bản ghi**: 1.000.000 events (tập chính) và 10.000 events (tập demo).
* **Định dạng**: JSON Lines (UTF-8, mỗi dòng một JSON object hợp lệ kết thúc bằng `\n`).

---

## 2. Schema Movie (Đặc tả PySpark)

File đặc tả chi tiết: `docs/movie_schema.md` và mã nguồn tái sử dụng: `src/schemas.py`.

| Field | Spark Type | Nullable | Ý nghĩa |
|---|---|---|---|
| `movieId` | `LongType` | `false` | Khóa chính của phim (Primary Key, dùng làm join key) |
| `title` | `StringType` | `false` | Tên phim kèm năm phát hành nếu có |
| `genres` | `StringType` | `false` | Danh sách thể loại phim ngăn cách bằng `\|` |
| `releaseYear` | `IntegerType` | `true` | Năm phát hành trích xuất từ tiêu đề (13 phim để null hợp lệ) |

---

## 3. Schema User Behavior Log (Đặc tả PySpark)

File đặc tả chi tiết: `docs/user_log_schema.md` và mã nguồn tái sử dụng: `src/schemas.py`.

| Field | Spark Type | Nullable | Ý nghĩa |
|---|---|---|---|
| `eventId` | `StringType` | `false` | Định danh duy nhất toàn cục của sự kiện (UUID v5) |
| `userId` | `StringType` | `false` | Mã người dùng (`sim-user-XXXXXX`) |
| `sessionId` | `StringType` | `false` | Mã phiên xem phim (UUID v5) |
| `movieId` | `LongType` | `false` | Mã phim tương tác (khóa ngoại liên kết với `movies.csv`) |
| `action` | `StringType` | `false` | Hành vi (`view`, `play`, `pause`, `stop`, `complete`) |
| `timestamp` | `StringType` | `false` | Thời điểm phát sinh sự kiện ISO 8601 UTC (`...Z`) |
| `watchDuration` | `LongType` | `false` | Số giây xem mới phát sinh từ lượt play gần nhất (nguyên `>= 0`) |
| `sequenceNumber` | `LongType` | `false` | Thứ tự bước thực hiện trong phiên (tăng từ 0) |
| `runId` | `StringType` | `false` | Mã định danh lô mô phỏng |
| `isSynthetic` | `BooleanType` | `false` | Cờ dữ liệu mô phỏng (`true`) |
| `simulatedMovieDuration` | `LongType` | `false` | Thời lượng phim giả lập (3.600 - 10.800 giây) |
| `durationSource` | `StringType` | `false` | Nguồn thời lượng (`"synthetic"`) |

---

## 4. Khóa liên kết (Join Key)

* **Join Key**: `movieId` (`movies.movieId = user_log.movieId`).
* **Kiểu dữ liệu**: Cùng kiểu `LongType` (64-bit signed integer).
* **Tính toàn vẹn**:
  * `movies.movieId`: 100% Unique (9.742 giá trị phân biệt, 0 null).
  * `user_log.movieId`: 100% giá trị trong log đều tồn tại trong `movies.csv` (0 orphan records).
* **Bản số quan hệ (Cardinality)**:
  * Movie Dataset: **1**
  * User Behavior Log: **N**
  * Quan hệ **1 → N** (Một phim có thể có nhiều lượt tương tác hành vi từ người dùng).

---

## 5. Data Quality (Chất lượng dữ liệu)

Báo cáo đầy đủ: `docs/data_quality_report.md`.

* **Kiểm tra cấu trúc CSV & JSON**: 100% hợp lệ, không có malformed JSON, không lỗi UTF-8/BOM.
* **Missing & Null Values**: 0 null ở các trường bắt buộc; 13 giá trị null ở `releaseYear` được ghi nhận đúng theo dữ liệu gốc.
* **Duplicates**: 0 duplicate ở `movieId`, 0 duplicate `eventId` trong lô chạy Flume.
* **Logic nghiệp vụ**: `watchDuration >= 0` (0 âm), phân bố action hợp lý, timestamp tăng đơn điệu theo sequence trong phiên.
* **Chuyển tiếp Tuần 2**: Dữ liệu sẵn sàng để Tuần 2 thực hiện idempotent deduplication, convert timezone và explode genres.

---

## 6. Kiến trúc hệ thống

```text
MovieLens Dataset ──> prepare_movies.py ──> movies.csv (Metadata tĩnh)
                                                 │
                                                 ▼
User Log Gen ──> Flume (Source -> Channel -> Sink) ──> Storage Output JSONL
                                                           │
                                                           ▼
                                                Spark / PySpark (Docker)
                                                           │
                                                           ▼
                                                Cleaning & Analysis (Tuần 2)
                                                           │
                                                           ▼
                                                Dashboard (Trực quan hóa)
```

---

## 7. Môi trường Spark/PySpark

* **Docker Engine**: Docker Desktop 4.93.0 / Docker Engine 29.8.1
* **Docker Compose**: v5.5.1
* **Spark Service**: `apache/spark:3.5.1` (tích hợp trong `compose.yaml` qua profile `spark`)
* **Spark Version**: Apache Spark 3.5.1
* **PySpark Version**: 3.5.1
* **Java Version trong Spark Container**: Eclipse Temurin OpenJDK 11.0.22 (độc lập với Java 8 của Flume)
* **Python Version trong Spark Container**: Python 3.8.10

---

## 8. Kiểm thử Spark (Smoke Test)

Lệnh thực thi:
```bash
docker compose run --rm spark scripts/spark_smoke_test.py
```

Kết quả kiểm thử thực tế:
* **SparkSession**: **PASS** (khởi tạo thành công local master với 1GB driver memory).
* **spark.range(5)**: **PASS** (thực thi DataFrame cơ bản thành công).
* **movies.csv Read**: **PASS** (đọc đủ 9.742 bản ghi, áp dụng thành công `MOVIE_SCHEMA`).
* **Flume Output Read**: **PASS** (đọc đủ 1.000.000 bản ghi từ 254 files JSONL qua `USER_LOG_SCHEMA`).
* **Schema Validation**: **PASS** (12 trường khớp chính xác kiểu dữ liệu).
* **movieId Join Validation**: **PASS** (thực hiện phép nối mẫu 5 dòng giữa log và movies thành công, khớp chính xác tên phim và thể loại).

---

## 9. Kết luận

Môi trường Spark/PySpark đã sẵn sàng cho Tuần 2. Movie dataset và output Flume có schema rõ ràng, khóa `movieId` tương thích 100% và có thể sử dụng cho Data Cleaning, Transformation và Analysis ở giai đoạn tiếp theo.
