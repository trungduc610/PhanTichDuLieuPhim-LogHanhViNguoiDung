# Quyết định kiến trúc cần nhóm xác nhận

Chuẩn bị ngày 11/10/2026 cho đợt triển khai lại Tuần 1. Đây là đề xuất kỹ thuật; **chưa có xác nhận của các thành viên**.

- Metadata MovieLens được giữ raw, chuẩn hóa riêng và đưa trực tiếp vào Spark qua movieId.
- Behavior log là synthetic, timestamp UTC Z, watchDuration là giây phát sinh từ play gần nhất.
- Log qua Flume 1.11.0: spooldir → File Channel → File Roll Sink → filesystem local bind mount theo run.
- Spark dùng container `apache/spark:3.5.1`, schema trong `src/schemas.py`, kiểm toàn bộ Sink output.
- Dashboard và phân tích chuyên sâu thuộc giai đoạn tiếp theo; HDFS chưa nằm trong phạm vi nghiệm thu Tuần 1.
- Mỗi run có vùng spool/channel/output/log/evidence riêng; kiểm conflicts và dedup trước phân tích. Một lần PASS không bảo đảm exactly-once.

Điều kiện chốt: nhóm xác nhận vai trò công nghệ, đường dẫn bàn giao, schema/units, phiên bản runtime đã đo và phân công. Lưu ngày/người xác nhận hoặc liên kết bằng chứng họp/phê duyệt. Không điền thay nhóm hoặc suy diễn phê duyệt từ tài liệu này.
