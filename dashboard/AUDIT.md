# Rà soát trước nghiệm thu — 14/10/2026

Đối chiếu kết quả đã xuất, không chạy lại Spark hoặc chỉnh sửa evidence. Không phát hiện lỗi chặn nghiệm thu về số liệu, điều hướng hoặc tương tác trong phạm vi kiểm tra.

| Trang | Trạng thái | Phát hiện và xử lý |
| --- | --- | --- |
| Tổng quan `/` | Đạt | 4 KPI khớp JSON; phân biệt sự kiện, người dùng và phiên. Lưới tóm tắt tự chuyển một cột khi không đủ chiều rộng, tránh ép hẹp biểu đồ cạnh thanh bên. |
| Phân tích phim `/phim` | Đạt | Bảng 20 phim và biểu đồ dùng đúng playCount; tên đầy đủ có trong bảng/tooltip. Không đồng nhất lượt play với người xem hoặc phiên. |
| Phân tích thể loại `/the-loai` | Đạt | 20 thể loại, Top 5/10/toàn bộ và nhận xét khớp JSON. Có chú thích play có thể được tính vào nhiều thể loại. |
| Hành vi người dùng `/hanh-vi` | Đạt | 5 hành vi; số lượng và tỷ lệ trên tổng sự kiện đúng. Không gọi tỷ lệ sự kiện là tỷ lệ người dùng. |
| Hoạt động theo thời gian `/thoi-gian` | Đạt | Bảng/biểu đồ 24 giờ khớp JSON. Bổ sung DAU ngắn gọn: 30 ngày, mỗi ngày 1.000 người; không cộng các ngày. |
| Thời lượng xem `/thoi-luong` | Đạt | 12 giá trị của hai nhóm khớp JSON; giây, trung vị xấp xỉ và độ lệch chuẩn mẫu đúng nghĩa. Không gọi là trung bình mỗi phiên. |
| Phân tích kết hợp `/ket-hop` | Đạt | Đủ 72 dòng, đúng 3 phim mỗi giờ; đã đổi cả 24 giờ và đối chiếu bảng, nhãn, người dùng và nhận xét. Không cộng người dùng giữa nhóm phim–giờ. |
| Phân cụm người dùng `/phan-cum` | Đạt | Metadata, K=2..6, hồ sơ, kích thước cụm, đặc trưng và biểu đồ khớp nguồn. Tỷ lệ ×100; trung bình tỷ lệ theo người dùng. Tìm kiếm, lọc và phân trang giữ kết quả gán cụm. |

## Bằng chứng kiểm tra

- `npm.cmd run build`: thành công. JavaScript khoảng 691 kB sau minify, 208 kB gzip; cảnh báo chunk >500 kB vẫn còn.
- `npm.cmd test`: 29/29 đạt. Bao gồm đối chiếu nguyên nội dung 11 bản sao JSON, tổng sự kiện/play/thời lượng và trung bình hồ sơ cụm so với assignments. Tính lại trong kiểm thử chỉ để đối chiếu, không thay cách tính hay kết quả Spark trong frontend.
- `node scripts/check-ui.mjs`: Edge headless tại 1440, 900, 390 và 320 px. Đủ 8 đường dẫn, menu đang chọn, mở/đóng menu mobile, Back và trang không tồn tại. Kiểm tra từng bảng, tooltip của mỗi biểu đồ, cuộn ngang và các lựa chọn hiện có. Không có lỗi JavaScript/React hoặc tràn ngang toàn trang.
- Cả 8 trang đã thử tải chậm, JSON rỗng, JSON hỏng và nút thử lại. Dữ liệu lỗi chỉ được mô phỏng trong phản hồi mạng của phiên kiểm thử, không ghi vào evidence/public data. Các loader có unit test HTTP 404/500 và HTML thay cho JSON.
- DAU xác nhận trong mã Spark: nhóm theo `date`, `countDistinct(userId)` trên mọi sự kiện. Trang thời gian đọc DAU riêng để lỗi của nguồn này không làm mất bảng 24 giờ.

## Phân loại vấn đề

- **Bắt buộc sửa:** không còn lỗi số liệu/điều hướng/tương tác phát hiện trong phạm vi kiểm tra. Không thay đổi phép thống kê hiện có.
- **Cải thiện nhỏ đã làm:** lưới Tổng quan thích ứng chiều rộng; ghi chú DAU và mở rộng kiểm thử nghiệm thu.
- **Không cấp thiết:** tối ưu chunk hoặc tải trang theo nhu cầu ở lượt sau. Chưa đổi cấu trúc bundle để tránh phát sinh thay đổi tải module trong lượt nghiệm thu.

## Chưa thể kiểm chứng

- Không kiểm chứng lại trung vị, độ lệch chuẩn, DAU hay chất lượng huấn luyện từ log thô; chỉ đối chiếu JSON và cách tổng hợp trong mã liên quan. Không chạy lại pipeline.
- UTC+7 dùng theo phạm vi người phụ trách đã xác nhận; JSON ngày/giờ tổng hợp không chứa múi giờ để kiểm chứng độc lập bước chuyển timestamp trước xuất dữ liệu.
- Chưa thử Safari/Firefox, cảm ứng trên điện thoại thật, công nghệ hỗ trợ hoặc triển khai hosting. Kết quả trình duyệt áp dụng cho Edge trên máy hiện tại.
- Ảnh chụp toàn trang quá dài có thể bỏ phần SVG trong Edge headless; kiểm tra tooltip và ảnh chụp vùng biểu đồ được dùng để xác nhận render, không coi ảnh trắng này là lỗi dữ liệu.

## Thay đổi trong lượt này

Thêm `src/services/dailyActivity.js`, `src/components/DailyActivitySummary.jsx` và các kiểm thử DAU, đối chiếu evidence, lỗi loader. Cập nhật trang thời gian, loader, đồng bộ JSON, CSS lưới tóm tắt, script kiểm tra Edge và README. Không thêm thư viện, backend hoặc thao tác Git.
