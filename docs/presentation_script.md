# Bài nói về kết quả kiểm lại 11/10/2026

Project dùng MovieLens latest-small của GroupLens: parser đếm 9.742 phim, metadata gồm movieId/title/genres, thêm releaseYear từ hậu tố năm; 13 phim để null vì không xác định được. ZIP, CSV gốc và giấy phép được giữ nguyên, bản chuẩn hóa riêng có SHA256.

Log là synthetic, không phải hành vi thu từ người dùng thật. Bộ main có một triệu sự kiện, 303,052 phiên, 1,000 user và 9,740 phim. watchDuration ghi giây mới phát sinh từ play; xem 120 giây, pause, xem 180 giây thì tổng là 300 giây. Runtime phim cũng được ghi rõ mô phỏng.

Flume 1.11.0 chạy trên Docker: spooldir Source nhận file đã đóng, File Channel đệm trên volume Linux riêng, File Roll Sink ghi JSONL ra filesystem local. Demo run-aefc814b0b5f đã đạt trước khi chạy main run-aa6b9eb58dca. Đối chiếu toàn bộ eventId và canonical payload cho main thấy đủ một triệu sự kiện, không mất/thừa/trùng/xung đột/đổi payload. JVM agent ghi heap tối đa 512 MiB, log thể hiện đầy đủ thành phần/counter.

Spark/PySpark 3.5.1 đã tạo SparkSession và action thật, đọc metadata cùng chính Sink main, kiểm mọi field, timestamp UTC, null/duplicate và full orphan join. Các bộ kiểm đều đạt; file rolling rỗng được đo riêng. Không suy exactly-once hoặc phục hồi lỗi từ lần chạy này.

Dữ liệu đủ để Tuần 2 phân tích lượt xem, thời gian xem, phim/thể loại và giờ hoạt động; dashboard chưa triển khai. Về nghiệm thu nhóm, vẫn thiếu xác nhận kiến trúc TV2-06 nên chưa tuyên bố hoàn thành đầy đủ Tuần 1. Tất cả kết luận liên kết tới audit và bằng chứng mới; lịch sử FAIL/BLOCKED được giữ nguyên.
