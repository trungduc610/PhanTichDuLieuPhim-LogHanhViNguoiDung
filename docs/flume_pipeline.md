# Cấu hình và vận hành Flume

Lựa chọn cục bộ: Spooling Directory Source → File Channel → File Roll Sink, agent `a1`. Xem `config/flume.conf`, `Dockerfile`, `compose.yaml`, `scripts/run_flume.sh`, `scripts/run_pipeline.py`.

Source đọc file đã đóng; channel đệm trên đĩa; sink ghi event body vào file output. `LINE` đọc một event mỗi dòng, `TEXT` thêm newline và không chèn header vào JSON. Không có interceptor đổi payload. Schema ứng dụng được validator kiểm trước và sau vận chuyển; Flume không tự hiểu các trường JSON.

| Đường dẫn trong container | Host khi dùng runner | Vai trò |
|---|---|---|
| /project/config/flume.conf | Được COPY vào image lúc build | Cấu hình agent |
| /data/spool | data/runs/<run-id>/spool | Input bất biến, tracker và `.COMPLETED` |
| /data/channel/checkpoint | volume Linux riêng; export data/runs/<run-id>/channel/checkpoint | Trạng thái File Channel |
| /data/channel/data | volume Linux riêng; export data/runs/<run-id>/channel/data | Nhật ký channel |
| /data/output | data/runs/<run-id>/output | JSONL cho PySpark |
| /logs | logs/<run-id> | Log INFO vận hành của agent qua log4j2.xml |

Console log luôn được runner thu bằng `docker compose logs --no-color --timestamps` vào `evidence/<run-id>/flume-operational.log`. Không coi file channel hoặc log vận hành là dữ liệu hành vi. Compose mặc định ngoài runner dùng `./data` và `./logs`; runner truyền mount riêng cho từng lần.

Source nhận `.jsonl`, bỏ qua `.tmp`, batch 500; transactionCapacity channel 1.000 đáp ứng batch source/sink. Channel capacity 1.000.000 event là trần hàng đợi, không phải yêu cầu nạp đủ một triệu trong RAM. Chừa ít nhất 100 MB theo minimumRequiredSpace; nên chừa nhiều hơn cho thực nghiệm. Sink batch 500, roll mỗi 10 giây. File rỗng do roll được đo bytes/hash/empty và giữ nguyên; không chứa event. Event phải nhỏ hơn giới hạn LINE 16.384 ký tự.

Runner copy vào tên `.tmp` trong spool, đóng xong mới rename cùng thư mục; không ghi thêm, sửa hay tái sử dụng tên file source đã thấy. Không kéo-thả file đang ghi vào spool. File `.COMPLETED` được giữ làm dấu tiếp nhận, nhưng chỉ báo source đã xử lý chứ chưa chứng minh sink đã ghi đủ.

Flume 1.11.0 được tải từ Apache archive, Docker build kiểm SHA512 trước giải nén. Không dùng image Flume bên thứ ba không rõ nguồn. Java base image là Temurin chính thức. Image ID/build/launcher đúng Flume 1.11.0 được lưu từng run. `flume-ng` đặt default JAVA_OPTS trước source flume-env.sh; vì vậy cấu hình heap trong config/flume-env.sh. Agent ghi PrintFlagsFinal và ps args, đo MaxHeapSize 536.870.912 byte. log4j2.xml ghi INFO ra console và /logs/flume.log; HTTP metrics port 41414 không publish ra host.

## Đọc kết quả kiểm thử

Runner đợi source hoàn tất và số dòng sink đạt số input, dừng container rồi validator đối chiếu: JSON, kiểu dữ liệu, trường bắt buộc, khóa movieId, số dòng, eventId duy nhất, trùng ID, xung đột cùng ID, event thiếu/thừa, payload bị thay đổi. Validator kiểm chuỗi trạng thái/giây xem/thời gian theo phiên trên input; output phải khớp payload từng eventId. So sánh bỏ qua thứ tự key JSON và thứ tự file output.

`PASS` cho một lần đối chiếu không phải cam kết **exactly-once**. Thử lại sau lỗi có thể tạo event trùng. File Channel giúp phục hồi nhưng không biến mọi sink thành giao dịch exactly-once với filesystem. `eventId` là khóa nhận diện lại; downstream kiểm xung đột rồi khử trùng. Chưa thử kill/restart hay lỗi đĩa, nên không có kết luận về phục hồi thực tế.

## Nếu sau này bắt buộc HDFS

Giữ source/channel và thay sink bằng HDFS Sink trong cấu hình mới: cần cluster thật, NameNode URI, quyền ghi, Hadoop client/config tương thích và mạng giữa container với cluster. Dùng DataStream + text serializer để giữ JSON Lines; cấu hình đường dẫn/roll rồi kiểm lại pipeline độc lập. Không chỉ đổi `/data/output` thành chuỗi `hdfs://...` trên File Roll Sink. HDFS chưa triển khai trong tuần này; không có dữ liệu nào được chứng nhận đã lưu HDFS.

Nguồn tra cứu: [Flume User Guide](https://flume.apache.org/FlumeUserGuide), [bản phân phối chính thức](https://flume.apache.org/download.html), [danh sách tag Temurin](https://github.com/docker-library/official-images/blob/master/library/eclipse-temurin). Đã kiểm lại ngày 11/10/2026; launcher snapshot lấy từ image thực tế.


Ngày kiểm lại: 11/10/2026 (Asia/Saigon). Đây là sản phẩm thực thi mới tại checkout Windows hiện tại, độc lập bằng chứng lịch sử. Movies: 9.742 dòng, SHA256 `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536`. Demo/main Flume E2E và Spark kiểm toàn bộ Sink đều PASS.

| Lô mới | Run Flume | Events / unique | File / rỗng | Bytes Sink |
|---|---|---:|---:|---:|
| Demo | `run-aefc814b0b5f` | 10,000 / 10,000 | 3 / 1 | 3,433,123 |
| Main | `run-aa6b9eb58dca` | 1,000,000 / 1,000,000 | 15 / 0 | 343,339,148 |

Missing/unexpected/duplicate/conflicting ID/changed payload, UTF-8/JSON/type/provenance/action/duration, session/sequence và user overlap: đều 0 trên hai lô mới. File rỗng do rolling được giữ và thống kê, không có event; tất cả file không rỗng kết thúc bằng LF. Đối chiếu canonical payload không phụ thuộc thứ tự file/key JSON. Một lần đối chiếu thành công không chứng minh exactly-once hoặc phục hồi lỗi.

Bằng chứng: `evidence/run-aefc814b0b5f/`, `evidence/run-aa6b9eb58dca/`, `evidence/recheck-20261011-221710/spark-demo.json`, `evidence/recheck-20261011-221710/spark-main.json`, `evidence/recheck-20261011-221710/dataset_quality.json`. Audit đầy đủ: `audit/2026-10-11-221710-week1-recheck/bao-cao-nghiem-thu-tuan-1-recheck.md`. Manifest mới: `evidence/recheck-20261011-221710/delivery_manifest.json`.
