# Bài nói 2–3 phút

Em là Nhan Tử Mạnh, phụ trách chuẩn bị dữ liệu và phần thu thập log trong tuần một của đề tài phân tích phim và hành vi người dùng.

Về dữ liệu phim, em chọn MovieLens latest-small của GroupLens vì có nguồn công khai, tải lại được và có điều kiện sử dụng rõ ràng. Sau khi tải, em đếm trực tiếp được 9.742 phim. Mỗi phim có movieId, title và genres. Em giữ nguyên dữ liệu gốc và tạo một bản chuẩn hóa riêng. Năm phát hành được lấy từ hậu tố trong tên phim; 13 phim không có định dạng năm phù hợp được để trống, không tự đoán. Rating có sẵn là đánh giá người dùng, khác với log hành vi em tạo.

Log của em là dữ liệu mô phỏng phục vụ học tập, mỗi dòng là một sự kiện JSON. Sự kiện có người dùng, phiên, mã phim, hành động và thời gian UTC. Các hành động đi theo diễn biến: mở thông tin, bắt đầu xem, có thể tạm dừng rồi tiếp tục, cuối cùng dừng hoặc xem hết. Em dùng trọng số để một số phim phổ biến hơn và buổi tối có nhiều phiên hơn. Thời lượng phim được giả lập và có trường đánh dấu rõ.

Điểm cần chú ý là watchDuration ghi số giây xem mới phát sinh, không phải tổng thời gian lũy kế. Ví dụ xem 120 giây rồi tạm dừng, sau đó xem thêm 180 giây thì hai event ghi 120 và 180. Sau khi loại bản ghi trùng theo eventId, tổng là 300 giây.

Pipeline được cấu hình gồm Source, Channel và Sink. Source đọc các file log đã ghi hoàn tất trong thư mục spool. File Channel đệm event trên đĩa. File Roll Sink ghi từng JSON event ra filesystem cục bộ để nhóm PySpark đọc ở tuần sau. Đây chưa phải HDFS. Em chỉ chuyển file vào spool sau khi đóng xong và không sửa file đã được Flume nhận.

Kết quả em đã kiểm chứng là demo 10.000 event, 3.058 phiên, không phát hiện ID trùng hay lỗi logic phiên; 12 kiểm thử Python đều đạt. Tuy nhiên, máy thực nghiệm hiện thiếu Docker và Java, WSL báo lỗi quyền, nên em chưa chạy được Flume và chưa có output sink để đối chiếu. Em đã bàn giao runner tự lưu log và báo cáo để hoàn tất bước này trên máy có Docker. Em không dùng kết quả kiểm tra input để khẳng định pipeline đã thành công.

Ngay cả khi chạy thành công, em chỉ kết luận về số liệu quan sát được của lần chạy đó, không khẳng định exactly-once. Tuần hai sẽ kiểm xung đột và khử trùng eventId trước khi join movieId và tính số phiên xem, tổng thời gian xem, tỷ lệ hoàn thành.

**Sau khi thực nghiệm E2E thật:** thay đoạn hạn chế bằng số input, output, unique, thiếu và trùng từ reconciliation; chỉ nói “không phát hiện trùng trong lần chạy này” nếu báo cáo thực sự ghi 0.
