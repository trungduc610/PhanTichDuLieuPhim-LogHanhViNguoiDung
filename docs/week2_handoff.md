# Bàn giao cho thành viên PySpark — Hợp đồng dữ liệu

Đưa `data/processed/movies.csv` và **output thực tế đã qua Flume pipeline** cho Thành viên 2 và Thành viên 3, kèm theo biên bản đối chiếu (reconciliation.json) và manifest.

### Dữ liệu chính thức bàn giao:

1. **Movie Dataset (Metadata phim)**:
   * Đường dẫn: `data/processed/movies.csv`
   * Định dạng: CSV (UTF-8, delimiter `,`, quote chuẩn)
   * Số lượng: 9.742 bản ghi
   * Vai trò: Cung cấp metadata (tên phim, thể loại, năm phát hành). Không đi qua Flume.

2. **User Behavior Log (Log hành vi người dùng)**:
   * Đường dẫn run main (1.000.000 events): `data/runs/run-f63c810e9d8d/output/*.jsonl` (254 files)
   * Đường dẫn run demo (10.000 events): `data/runs/run-a9b3a8a26afb/output/*.jsonl` (4 files)
   * Định dạng: JSON Lines (mỗi dòng một JSON object UTF-8 kết thúc bằng `\n`)
   * Trạng thái thu thập: Đã qua trọn vẹn pipeline Apache Flume (Spooling Directory Source → File Channel → File Roll Sink).
   * Khóa liên kết: `movieId` (kiểu Long/Integer, khớp 100% với `movies.csv`).
   * Timestamp: Chuỗi ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).
   * watchDuration: Số nguyên `>= 0` (thời lượng giây xem phát sinh từ lượt play gần nhất).
   * Tính toàn vẹn: Output Flume giữ nguyên 100% payload từ input (0 mất mát, 0 trùng lặp, 0 payload thay đổi).

### Ready for Spark/PySpark Week 1 validation:
Dữ liệu đã sẵn sàng để Thành viên 2 tiến hành khởi tạo SparkSession, kiểm tra schema (`StructType`), đọc thử nghiệm `movies.csv` và output JSONL của Flume, cũng như xác nhận tính tương thích của khóa liên kết `movieId`. Các bài toán làm sạch dữ liệu, aggregation và phân tích chuyên sâu sẽ được thực hiện ở Tuần 2.

```python
from pyspark.sql import functions as F

spark.conf.set("spark.sql.session.timeZone", "UTC")
movies = (spark.read.option("header", True).option("encoding", "UTF-8")
          .schema("movieId LONG, title STRING, genres STRING, releaseYear INT")
          .csv("data/processed/movies.csv"))
event_schema = """eventId STRING, userId STRING, sessionId STRING, movieId LONG,
action STRING, timestamp STRING, watchDuration LONG, sequenceNumber INT,
runId STRING, isSynthetic BOOLEAN, simulatedMovieDuration LONG, durationSource STRING"""
events = (spark.read.option("mode", "FAILFAST").schema(event_schema)
          .json("data/runs/run-f63c810e9d8d/output/*.jsonl"))
events = events.withColumn("eventTime", F.to_timestamp("timestamp"))
# Kiểm tra cùng eventId có payload khác nhau trước bước này; cách ly nếu có.
clean = events.dropDuplicates(["eventId"])
joined = clean.join(movies, "movieId", "left")
```

Đây chỉ là mẫu đọc/join; chưa có job phân tích hoàn chỉnh. `movieId` hai bên cùng long. Giữ title nguyên vì một số title có dấu phẩy/ngoặc. Năm trống đọc thành null; không thay bằng 0. Kiểm tra orphan movieId và trường null sau đọc; `FAILFAST` JSON không thay thế kiểm tra ràng buộc nghiệp vụ.

Quy tắc dedup: nhóm theo eventId, so sánh các trường có ý nghĩa; cùng payload thì giữ một, payload khác nhau thì cách ly/điều tra thay vì tùy ý `dropDuplicates`. Giữ báo cáo số ID trùng. Có thể đọc output nhiều part của **một run**; không gom demo và main như dữ liệu độc lập nếu cùng thời gian/user.

| Chỉ số | Định nghĩa sau dedup |
|---|---|
| Lượt xem chi tiết | Đếm event action=view; đây không đồng nghĩa đã xem video |
| Lượt bắt đầu xem | Đếm sessionId có ít nhất một play; không đếm mọi play vì có resume |
| Tổng thời gian xem | SUM(watchDuration); giây phát sinh, không cộng runtime mô phỏng |
| Thời gian xem một phiên | SUM(watchDuration) GROUP BY runId, sessionId |
| Tỷ lệ hoàn thành | Số phiên có complete / số phiên đã play; mẫu số 0 → null |
| Giờ hoạt động | Chuyển UTC sang Asia/Ho_Chi_Minh (UTC+7) trước khi trích hour |

Sắp xếp trong phiên bằng sequenceNumber/timestamp khi cần. Phim phổ biến có thể đo riêng view và phiên play; thể loại cần split `genres` theo `|` và explode. Một phim nhiều thể loại đóng góp cho nhiều nhóm, nên tổng theo thể loại có thể lớn hơn tổng toàn bộ; nếu muốn tổng bảo toàn thì chia trọng số 1/số thể loại. Nhãn `(no genres listed)` là chưa biết, không phải một thể loại thật.

Thời gian xem, giờ cao điểm, tỷ lệ hoàn thành phản ánh **tham số mô phỏng**, không dùng để kết luận sở thích thật của người xem. Runtime cũng giả lập, không dùng đánh giá phim dài/ngắn thực tế. Chưa triển khai Spark, dashboard hay trực quan hóa.
