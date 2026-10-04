# Log hành vi mô phỏng

JSON Lines UTF-8, mỗi event một dòng kết thúc bằng LF, không BOM. Event timestamp dùng ISO 8601 UTC (`Z`). Giờ cao điểm được chọn theo UTC+07:00/Asia/Saigon. Không yêu cầu các phiên khác nhau được sắp xếp theo thời gian trong file; trong mỗi phiên luôn đúng thứ tự.

| Trường | Kiểu JSON | Ràng buộc |
|---|---|---|
| eventId | string | UUID v5 từ run + phiên + vị trí; duy nhất trong lô |
| userId | string | `sim-user-000001`… trong tập user giả lập |
| sessionId | string | UUID v5; một user, một phim, một chuỗi hành vi |
| movieId | integer | Tồn tại trong movies.csv chuẩn hóa |
| action | string | view / play / pause / stop / complete |
| timestamp | string | UTC Z, tăng nghiêm ngặt theo sequenceNumber trong phiên |
| watchDuration | integer >=0 | **Số giây xem mới phát sinh từ play gần nhất**, không phải tổng lũy kế |
| sequenceNumber | integer >=0 | Bắt đầu 0, tăng 1 trong phiên |
| runId | string | Định danh lần mô phỏng; mặc định từ hash các tham số |
| isSynthetic | boolean | Luôn true |
| simulatedMovieDuration | integer | 3.600–10.800 giây, giả lập cố định theo movieId + seed |
| durationSource | string | Luôn `synthetic`; không phải runtime lấy từ MovieLens |

## Trạng thái và thời lượng

| Action | watchDuration | Ý nghĩa |
|---|---:|---|
| view | 0 | Mở trang/chi tiết phim, có thể rời đi mà không play |
| play | 0 | Bắt đầu hoặc tiếp tục xem; không cộng lại đoạn trước |
| pause | Thời gian từ play vừa trước đến pause | Đóng một đoạn xem |
| stop | Thời gian từ play vừa trước đến stop | Kết thúc sớm; tổng phiên < runtime mô phỏng |
| complete | Thời gian từ play vừa trước đến complete | Tổng phiên bằng runtime mô phỏng |

Chuỗi sinh: `view`; `view → play → stop/complete`; hoặc `view → play → pause → play → stop/complete`. Thời gian chờ trước play và thời gian pause không tính xem. Không có seek, tua nhanh, nhiều tab đồng thời hoặc phiên qua nhiều phim trong mô hình này. Sau khử trùng eventId, cộng watchDuration trên toàn bộ event của phiên là tổng thời gian xem.

Ví dụ diễn giải (không phải bằng chứng Flume): xem 120 giây → pause ghi 120; chờ 30 giây → play ghi 0; xem thêm 180 giây → stop ghi 180. Tổng xem 300 giây, không phải 420 hay 330 giây.

## Phân bố và tái lập

Các phim được shuffle bằng seed rồi gán trọng số rank^-0,85. User được shuffle rồi gán trọng số rank^-0,65. Không dùng số rating để giả vờ mô phỏng phản ánh thực tế. Chọn giờ bắt đầu với trọng số 5 cho 19–23h, 0,5 cho 0–5h, 1,5 cho các giờ khác, nhân số giây hợp lệ trong khung giờ. Dự trữ bốn giờ cuối khoảng để phiên không vượt biên. Lịch sử phiên theo user dùng để loại các khoảng chồng nhau; điều này có thể làm phân bố thực tế lệch khỏi trọng số ban đầu khi dữ liệu dày.

Xấp xỉ 15% phiên chỉ view; phiên đã play có xác suất complete 55%, và xác suất có pause 35% nếu ngân sách event cho phép. Đây là tham số mô hình, không phải tỷ lệ đo từ người dùng. Nếu còn 1–2 event cuối, tạo phiên view-only để giữ đúng số lượng mà không cắt dở phiên. Một phần user/phim có thể không được chọn; `--users` là kích thước tập user, không ép tất cả phải hoạt động.

RAM không chứa một triệu JSON event: ghi từng phiên tối đa 5 event ra `.part`, sau hoàn tất mới rename. Chỉ giữ metadata, trọng số, bộ đếm và khoảng thời gian phiên để chống chồng lấn; bộ nhớ phần lịch tăng theo số phiên, không hằng số. Validator lưu eventId/payload vào SQLite tạm trên đĩa, cache 16 MB. Cần đủ đĩa tạm khi kiểm tra dữ liệu lớn; chưa benchmark main một triệu event.

Cùng dataset/seed/tham số tái tạo cùng eventId: một bản chạy lại không được nhập như hành vi mới. Nếu muốn lô độc lập, chỉ định `--run-id` khác. Nếu ghép demo và main, có thể có cùng user và khoảng ngày: chọn riêng dataset/lần chạy cho phân tích, không mặc nhiên coi chúng là một lịch sử người dùng liên tục.

Kết quả demo: 10.000 event, 3.058 phiên; view 3.058, play 3.471, pause 904, stop 1.177, complete 1.390. Có 861 user hoạt động trong tập 1.000 user và 1.664 phim được chọn. Số play gồm cả resume; số phiên thực sự bắt đầu xem là 2.567. Kiểm tra input không phát hiện ID trùng, phiên sai hoặc phiên chồng nhau.
