# Cấu hình và vận hành Flume

Lựa chọn cục bộ: Spooling Directory Source → File Channel → File Roll Sink, agent `a1`. Xem `config/flume.conf`, `Dockerfile`, `compose.yaml`, `scripts/run_flume.sh`, `scripts/run_pipeline.py`.

Source đọc file đã đóng; channel đệm trên đĩa; sink ghi event body vào file output. `LINE` đọc một event mỗi dòng, `TEXT` thêm newline và không chèn header vào JSON. Không có interceptor đổi payload. Schema ứng dụng được validator kiểm trước và sau vận chuyển; Flume không tự hiểu các trường JSON.

| Đường dẫn trong container | Host khi dùng runner | Vai trò |
|---|---|---|
| /project/config/flume.conf | Được COPY vào image lúc build | Cấu hình agent |
| /data/spool | data/runs/<run-id>/spool | Input bất biến, tracker và `.COMPLETED` |
| /data/channel/checkpoint | data/runs/<run-id>/channel/checkpoint | Trạng thái File Channel |
| /data/channel/data | data/runs/<run-id>/channel/data | Nhật ký channel |
| /data/output | data/runs/<run-id>/output | JSONL cho PySpark |
| /logs | logs/<run-id> | Log vận hành của agent nếu launcher ghi file |

Console log luôn được runner thu bằng `docker compose logs --no-color --timestamps` vào `evidence/<run-id>/flume-operational.log`. Không coi file channel hoặc log vận hành là dữ liệu hành vi. Compose mặc định ngoài runner dùng `./data` và `./logs`; runner truyền mount riêng cho từng lần.

Source nhận `.jsonl`, bỏ qua `.tmp`, batch 500; transactionCapacity channel 1.000 đáp ứng batch source/sink. Channel capacity 1.000.000 event là trần hàng đợi, không phải yêu cầu nạp đủ một triệu trong RAM. Chừa ít nhất 100 MB theo minimumRequiredSpace; nên chừa nhiều hơn cho thực nghiệm. Sink batch 500, roll mỗi 10 giây. File rỗng do roll có thể xuất hiện và được validator bỏ qua về số event. Event phải nhỏ hơn giới hạn LINE 16.384 ký tự.

Runner copy vào tên `.tmp` trong spool, đóng xong mới rename cùng thư mục; không ghi thêm, sửa hay tái sử dụng tên file source đã thấy. Không kéo-thả file đang ghi vào spool. File `.COMPLETED` được giữ làm dấu tiếp nhận, nhưng chỉ báo source đã xử lý chứ chưa chứng minh sink đã ghi đủ.

Flume 1.11.0 được tải từ Apache archive, Docker build kiểm SHA512 trước giải nén. Không dùng image Flume bên thứ ba không rõ nguồn. Java base image là Temurin chính thức; chưa có digest bản pull trong lần bàn giao vì Docker chưa sẵn sàng. Cấu hình chỉ được đối chiếu tài liệu, chưa xác nhận qua JVM thật.

## Đọc kết quả kiểm thử

Runner đợi source hoàn tất và số dòng sink đạt số input, dừng container rồi validator đối chiếu: JSON, kiểu dữ liệu, trường bắt buộc, khóa movieId, số dòng, eventId duy nhất, trùng ID, xung đột cùng ID, event thiếu/thừa, payload bị thay đổi. Validator kiểm chuỗi trạng thái/giây xem/thời gian theo phiên trên input; output phải khớp payload từng eventId. So sánh bỏ qua thứ tự key JSON và thứ tự file output.

`PASS` cho một lần đối chiếu không phải cam kết **exactly-once**. Thử lại sau lỗi có thể tạo event trùng. File Channel giúp phục hồi nhưng không biến mọi sink thành giao dịch exactly-once với filesystem. `eventId` là khóa nhận diện lại; downstream kiểm xung đột rồi khử trùng. Chưa thử kill/restart hay lỗi đĩa, nên không có kết luận về phục hồi thực tế.

## Nếu sau này bắt buộc HDFS

Giữ source/channel và thay sink bằng HDFS Sink trong cấu hình mới: cần cluster thật, NameNode URI, quyền ghi, Hadoop client/config tương thích và mạng giữa container với cluster. Dùng DataStream + text serializer để giữ JSON Lines; cấu hình đường dẫn/roll rồi kiểm lại pipeline độc lập. Không chỉ đổi `/data/output` thành chuỗi `hdfs://...` trên File Roll Sink. HDFS chưa triển khai trong tuần này; không có dữ liệu nào được chứng nhận đã lưu HDFS.

Nguồn tra cứu: [Flume User Guide](https://flume.apache.org/FlumeUserGuide), [bản phân phối chính thức](https://flume.apache.org/download.html), [danh sách tag Temurin](https://github.com/docker-library/official-images/blob/master/library/eclipse-temurin). Đã tra cứu ngày 03/10/2026.
