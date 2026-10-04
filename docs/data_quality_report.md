# Báo cáo đánh giá chất lượng dữ liệu (Data Quality Report) — Tuần 1

**Người thực hiện**: Thành viên 2 (Kỹ sư PySpark / Dữ liệu Downstream).  
**Phạm vi**: Đánh giá toàn diện chất lượng của Movie Dataset và User Behavior Log (sau khi đã đi qua Flume pipeline) để phục vụ cho giai đoạn phân tích Tuần 2. **Không thực hiện làm sạch hay biến đổi dữ liệu trước trong báo cáo này.**

---

## 1. Các kiểm tra đã thực hiện

### A. Movie Dataset (`data/processed/movies.csv`)
1. **Tổng số bản ghi**: Đếm dòng loại trừ header.
2. **Tính toàn vẹn của khóa chính (`movieId`)**: Kiểm tra null, rỗng, không phải số, duplicate.
3. **Chất lượng trường tiêu đề (`title`)**: Kiểm tra null, rỗng, khoảng trắng thừa, chuẩn hóa Unicode.
4. **Chất lượng trường thể loại (`genres`)**: Kiểm tra null, rỗng, danh sách nhãn.
5. **Chất lượng trường năm phát hành (`releaseYear`)**: Kiểm tra giá trị rỗng, giá trị ngoài biên (1870–2100).
6. **Mã hóa file**: Kiểm tra UTF-8 strict, byte order mark (BOM).

### B. User Behavior Log sau Flume (`data/runs/run-f63c810e9d8d/output/*.jsonl` & `run-a9b3a8a26afb/output/*.jsonl`)
1. **Tính hợp lệ định dạng JSON**: Kiểm tra từng dòng có parse được JSON hay không (malformed JSON).
2. **Tính đầy đủ của các trường bắt buộc**: Kiểm tra sự hiện diện và giá trị không null của 12 trường trong schema.
3. **Tính duy nhất của định danh (`eventId`)**: Kiểm tra duplicate ID hoặc ID xung đột payload.
4. **Hợp lệ của hành vi (`action`)**: Kiểm tra xem action có thuộc tập hợp hợp lệ `{view, play, pause, stop, complete}` hay không.
5. **Tính hợp lệ của thời lượng xem (`watchDuration`)**: Kiểm tra xem có giá trị âm không (`< 0`), kiểm tra tính nhất quán với action (0 với `view`/`play`, > 0 với `pause`/`stop`/`complete`).
6. **Tính hợp lệ của thời gian (`timestamp`)**: Kiểm tra định dạng chuỗi ISO 8601 UTC và tính tăng đơn điệu theo `sequenceNumber` trong cùng `sessionId`.
7. **Khóa liên kết (`movieId`)**: Đối chiếu 100% `movieId` trong log xem có tồn tại trong `movies.csv` hay không (orphan foreign keys).

---

## 2. Kết quả kiểm tra chi tiết

| Hạng mục kiểm tra | Tập dữ liệu | Kết quả thực tế | Trạng thái |
|---|---|---|---|
| Số lượng bản ghi | Movies CSV | 9.742 bản ghi | **PASS** |
| Null / Trùng lặp `movieId` | Movies CSV | 0 null, 0 duplicate (9.742 unique IDs) | **PASS** |
| Null `title` | Movies CSV | 0 null / 0 empty | **PASS** |
| Null `genres` | Movies CSV | 0 null / 0 empty | **PASS** |
| Phim thiếu năm phát hành | Movies CSV | 13 phim không có năm trong title (được để null) | **ACCEPTED** |
| Phim không có thể loại | Movies CSV | 34 phim mang nhãn `(no genres listed)` | **ACCEPTED** |
| Số lượng bản ghi log | Flume Main Output | 1.000.000 events (254 files) | **PASS** |
| Số lượng bản ghi log | Flume Demo Output | 10.000 events (4 files) | **PASS** |
| Malformed JSON Lines | Flume Output | 0 dòng lỗi cấu trúc JSON | **PASS** |
| Thiếu trường (Missing fields) | Flume Output | 0 bản ghi thiếu trường (12/12 fields có mặt 100%) | **PASS** |
| Duplicate `eventId` | Flume Output | 0 eventId trùng lặp trong đợt chạy | **PASS** |
| Giá trị `action` không hợp lệ | Flume Output | 0 action ngoài tập `{view, play, pause, stop, complete}` | **PASS** |
| `watchDuration` âm (< 0) | Flume Output | 0 bản ghi có thời lượng âm | **PASS** |
| Lỗi parse `timestamp` | Flume Output | 0 lỗi parse định dạng ISO 8601 UTC | **PASS** |
| Orphan `movieId` trong log | Flume Output | 0 orphan (100% movieId tồn tại trong `movies.csv`) | **PASS** |

---

## 3. Các vấn đề được chấp nhận (Accepted Issues)

1. **13 phim thiếu `releaseYear` trong `movies.csv`**:
   * *Nguyên nhân*: Tiêu đề gốc từ MovieLens (như `Babylon 5`, `Ready Player One`, `Nocturnal Animals`) không chứa thông tin năm dạng `(YYYY)`.
   * *Đánh giá*: Để giá trị `null` thay vì gán giá trị mặc định (như `0` hay năm hiện tại) là xử lý chính xác, bảo toàn tính trung thực của dữ liệu gốc.
2. **34 phim mang nhãn `(no genres listed)`**:
   * *Nguyên nhân*: Dữ liệu MovieLens nguyên bản chưa phân loại thể loại cho các phim này.
   * *Đánh giá*: Giữ nguyên chuỗi để tránh bịa đặt thể loại; khi phân tích thể loại ở Tuần 2 có thể lọc hoặc gán nhóm riêng.
3. **watchDuration không phải thời lượng lũy kế**:
   * *Nguyên nhân*: Thiết kế log ghi nhận thời lượng phát sinh từ lượt `play` gần nhất (phiên xem phân đoạn).
   * *Đánh giá*: Đúng với mô hình toán học đã định nghĩa tại `docs/log_schema.md`.

---

## 4. Các điểm cần xử lý ở Tuần 2 (Forward to Week 2 Processing)

*Trong phạm vi Tuần 1, nhóm dừng lại ở mức đánh giá và KHÔNG thực hiện làm sạch dữ liệu trước.* Các công việc sau đây sẽ được thực hiện bằng PySpark ở Tuần 2:
1. **Khử trùng lặp phòng ngừa (Idempotent Deduplication)**: Dùng `events.dropDuplicates(["eventId"])` để bảo đảm tính exactly-once nếu hệ thống có nạp lại dữ liệu.
2. **Chuyển đổi kiểu dữ liệu thời gian**: Dùng `to_timestamp("timestamp")` chuyển chuỗi ISO 8601 thành kiểu `TimestampType`, sau đó chuyển múi giờ sang `Asia/Ho_Chi_Minh` (UTC+7) để phân tích khung giờ cao điểm.
3. **Tách thể loại phim (Genres Explode)**: Tách chuỗi `genres` ngăn cách bởi `\|` thành mảng và explode để thống kê theo từng thể loại phim riêng lẻ.
4. **Xử lý `releaseYear` null**: Khi thống kê theo thập niên hoặc năm, lọc bỏ hoặc đưa các bản ghi `releaseYear IS NULL` vào nhóm `Unknown`.

---

## 5. Kết luận
Bộ dữ liệu Movie Metadata và User Behavior Log thu thập qua Apache Flume có chất lượng xuất sắc, tính nhất quán cao, không có lỗi cấu trúc và hoàn toàn sẵn sàng cho giai đoạn xử lý bằng PySpark ở Tuần 2.
