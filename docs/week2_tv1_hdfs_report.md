# Lưu trữ phân tán bằng HDFS — TV1 Tuần 2

Nhan Tử Mạnh — đề tài “Phân tích dữ liệu phim và log hành vi người dùng”. Thực nghiệm ngày 12/10/2026; thời gian máy được lưu theo UTC, giờ Việt Nam bằng UTC+7. Phạm vi chương này là HDFS và kiểm thử tích hợp Spark; chưa thực hiện tiền xử lý chuyên sâu, phân tích, K-Means hoặc dashboard.

## 1. Cơ sở lý thuyết

HDFS là hệ thống tệp phân tán của Hadoop, tổ chức dữ liệu thành các block trên các DataNode. NameNode quản lý namespace và ánh xạ tệp–block; DataNode lưu và phục vụ block. Client hỏi NameNode để tìm vị trí, rồi trao đổi dữ liệu với DataNode. Metadata được lưu bền vững thông qua FsImage và EditLog. Replication cho phép lưu nhiều bản block, tùy cấu hình và số DataNode sẵn có. Đây là kiến thức tổng quát; khả năng chịu lỗi phụ thuộc triển khai cụ thể. [Apache HDFS Architecture 3.3.6](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html).

Trong đề tài, HDFS cung cấp namespace chung để tách lô nhập khỏi môi trường Spark. Movie metadata và log có thể được đọc bằng URI ổn định trong Docker network. Flume Tuần 1 vẫn thu thập ra filesystem Sink; thao tác nhập HDFS là một bước riêng có manifest và kiểm toàn bộ nội dung. Không mô tả Flume đang trực tiếp ghi HDFS. Cách sử dụng client, safe mode, quản trị và Web UI được đối chiếu với [HDFS User Guide](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-hdfs/HdfsUserGuide.html).

## 2. Cấu hình thực nghiệm đã chạy

| Thành phần | Giá trị thực tế |
|---|---|
| Compose riêng | `compose.hdfs.yaml`; project `movie-hdfs-385a18d3f03a` |
| Hadoop server | Apache Hadoop 3.3.6, Java 1.8.0_212 |
| Image server | `apache/hadoop@sha256:62a22627f35a1bbf29c721192c02fe311c93749cc43d51df01792b2ac40ff144` |
| Runtime Spark | `apache/spark:3.5.1`; Spark/PySpark 3.5.1; Hadoop client 3.3.4 |
| Java/Python Spark | Java 11.0.22; Python 3.8.10 |
| NameNode RPC | `hdfs://namenode:9000` trong Docker network riêng |
| DataNode | hostname `datanode`; transfer 9866, IPC 9867, HTTP 9864 |
| UI host | [NameNode](http://127.0.0.1:19870/dfshealth.html#tab-overview), chỉ bind loopback |
| Storage | hai named volume riêng, `/hdfs/name`, `/hdfs/data` |
| Replication/block size | 1; 134.217.728 byte (128 MiB) |
| Resources | máy khoảng 16,6 GB RAM; trước Docker còn 7,6 GB RAM và khoảng 70 GB đĩa C: |

Image được kiểm publisher Apache Software Foundation tại [Docker Hub Apache Hadoop](https://hub.docker.com/r/apache/hadoop), pull rồi kiểm digest, version, Java và entrypoint thực tế. Không suy hành vi từ tên biến môi trường của image: entrypoint được thay bằng `scripts/hdfs_service.sh`, cấu hình XML gắn read-only vào container. Service chỉ format volume NameNode mới, trống; từ chối volume không trống chưa format hoặc cluster ID khác. Restart đọc lại metadata có cùng cluster ID. Không dùng `-force` hoặc xóa volume.

Hadoop client 3.3.4 trong Spark kết nối thật tới server 3.3.6. Đây là kết quả đã đo cho job hiện tại; chính sách tương thích minor cùng major được tham khảo tại [Hadoop Compatibility](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/Compatibility.html). Không suy ra mọi API hoặc bản nâng cấp đều đã kiểm thử.

## 3. Nguồn dữ liệu và namespace

Nguồn Tuần 1 được xác minh lại trước nhập: manifest 344 tệp còn khớp, status và reconciliation thuộc `run-aa6b9eb58dca`, toàn bộ 15 part Sink thật có bytes/hash đúng. Expected count được đóng băng trong `source_manifest.json`, không lấy từ count Spark đang đọc.

| Dữ liệu | Nguồn local | Đích HDFS |
|---|---|---|
| Metadata chuẩn hóa | `data/processed/movies.csv` | `hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-385a18d3f03a/movies.csv` |
| Output Sink thật | `data/runs/run-aa6b9eb58dca/output/` | `hdfs://namenode:9000/movie-log/raw/user_logs/run-aa6b9eb58dca/hdfs-385a18d3f03a/` |

`raw/movies` là vùng tiếp nhận metadata đã chuẩn hóa từ upstream, không phải bản ZIP MovieLens nguyên thủy. ZIP, CSV raw, README/license gốc vẫn được bảo toàn ở local. Các thư mục `/movie-log/processed` và `/movie-log/results` đã tạo và đang để trống, dành cho bước tiếp theo. `generated/main.jsonl` chỉ được kiểm hash để nối lineage tới run Flume; không được upload thay Sink. Cả 15 part đều không rỗng; không có part bị bỏ qua.

## 4. Nhập và kiểm toàn lô

`hdfs_io.py` tạo namespace rồi thử tồn tại từng đích; dùng `hdfs dfs -put` không có `-f`. Nếu có đích sẵn, chương trình dừng trước ghi. Các lệnh shell `-ls -R`, `-du`, `-cat` được đối chiếu với [FileSystem Shell](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/FileSystemShell.html). Mọi argv, cwd, UTC, exit code và stdout/stderr được lưu riêng.

Mỗi tệp HDFS được đọc trọn bằng `-cat`, stdout giữ dạng binary; SHA256 được tính trên byte gốc, không đổi newline/encoding. Metadata được đếm bằng CSV parser, các JSONL được parse từng record và kiểm types/provenance/actions/duration. Đây là đối chiếu nội dung toàn bộ, không lấy mẫu hoặc dùng checksum HDFS thay SHA256. Sau restart kiểm toàn bộ lần nữa. Kiểm cuối độc lập bằng Hadoop Java FSDataInputStream → DigestInputStream SHA-256, lưu `final-hdfs-hashes.json`.

| Phép đo | Kết quả |
|---|---:|
| Metadata | 9.742 phim; 533.347 byte |
| Sink/HDFS log | 15 tệp; 1.000.000 events; 343.339.148 byte |
| Toàn lô | 16 tệp; 343.872.495 byte |
| Thiếu/thừa tệp, sai bytes/hash/count | 0 |
| Invalid JSON/duplicate eventId | 0 / 0 |
| Metadata SHA256 | `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536` |
| HDFS blocks | 16; mọi block Live_repl=1 |
| Corrupt/missing/under-replicated blocks | 0 / 0 / 0 |
| DataNode live; safe mode | 1; OFF |

`hdfs fsck /movie-log -files -blocks -locations` trả HEALTHY. Các phép `dfsadmin -report`, safe mode và fsck dựa trên [HDFS Commands](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-hdfs/HDFSCommands.html). Mô hình một DataNode/replication 1 không có dự phòng block, HA hoặc khả năng chịu mất máy/volume; HEALTHY chỉ phản ánh trạng thái lô hiện tại.

## 5. Spark đọc HDFS thật

`scripts/spark_hdfs_validate.py` dùng `MOVIE_SCHEMA`, `USER_LOG_SCHEMA` trong `src/schemas.py` và bộ kiểm toàn lô `validate_frames` Tuần 1. Movie ID và log movie ID cùng LongType; `releaseYear` IntegerType có thể null; `sequenceNumber` LongType. Timestamp gốc là chuỗi UTC Z, parse thành `eventTime` TimestampType với session timezone UTC. `watchDuration` là số giây mới phát sinh từ play gần nhất, không phải thời lượng cộng dồn; runtime phim và logs là synthetic.

Job quan sát `org.apache.hadoop.hdfs.DistributedFileSystem`, URI đúng NameNode, `input_file_name()` đúng metadata và đủ 15 part HDFS. `local_fallback=false`. Đọc PERMISSIVE có `_corrupt_record`, CSV `header=true`, UTF-8, quote/escape `"`; không dựa riêng `nullable=False` để khẳng định hợp lệ.

Spark từ 07:53:44 đến 07:55:36 UTC ngày 12/10/2026 đã chạy action thật và materialize toàn bộ fields. Kết quả 9.742 phim, 1.000.000 events; 23 nhóm lỗi đều 0, gồm malformed/null/type/action/duration/provenance/timestamp, duplicate/conflict IDs, orphan join và thứ tự/segment/session. Có 13 releaseYear null hợp lệ, 1.000 users, 9.740 movies xuất hiện trong logs, 303.052 sessions và 1.458.785.357 giây xem. Bằng chứng: `evidence/week2-hdfs/hdfs-385a18d3f03a/spark-hdfs.json`.

Chuỗi đã chứng minh: generated input hash → reconciliation Flume thật → 15 part Sink hash → HDFS byte hash/count → Spark URI và QA. Không chạy lại Flume một triệu event vì nguồn và bằng chứng không đổi.

## 6. Lỗi thực tế, bảo toàn và giới hạn

Docker Engine ban đầu chưa chạy; giữ các lỗi pipe cùng exit code 1, mở Docker Desktop đã cài rồi kiểm lại. Không cài hệ thống hoặc sửa WSL. Ba fixture container riêng chứng minh từ chối volume không trống chưa format, cluster ID sai và role sai; fixture không được coi là dữ liệu Flume. Phép upload lại namespace hiện hữu dừng exit 1 trước `put`, đúng yêu cầu chống ghi đè.

Sau restart, bộ kiểm đầu tiên so bytes cả tệp VERSION và báo FAIL vì DataNode cập nhật comment thời gian. Raw VERSION trước/sau, FAIL và hash báo cáo gốc vẫn lưu. Bộ kiểm sửa so sánh tất cả Java properties, chỉ bỏ comment; có regression tests cho thay cluster/storage/layout và duplicate keys. Kết quả `persistence-reviewed.json` đạt: toàn bộ properties và toàn bộ dữ liệu không đổi; chỉ có một marker format, hai marker reuse. Không sửa FAIL lịch sử hoặc format lại.

21 host unit tests đạt. Cấu hình/model chỉ demo một máy, authentication simple và service user root trong container; không đổi quyền host. TV2 cần cùng Docker network, không thể dùng hostname container từ host như địa chỉ công khai. Named volumes đang giữ để bàn giao; manifest không xuất blocks/metadata volume thành gói portable.

## 7. Hướng tiếp theo và trạng thái phối hợp

TV2 nhận URI/schema/QA qua `docs/week2_tv2_hdfs_handoff.md`; tiền xử lý/phân tích/K-Means/dashboard là bước tiếp theo. Nếu phát triển môi trường thực, cần thêm DataNode, replication phù hợp, HA, quản lý quyền và giám sát rồi kiểm thử failure scenarios riêng. Chưa có xác nhận TV2 hoặc nhóm; điều kiện xác nhận kiến trúc và phần giới thiệu/cơ sở lý thuyết Tuần 1 vẫn còn thiếu. Chương HDFS đã được viết và nghiệm thu kỹ thuật; không coi việc viết chương này là nhóm đã phê duyệt toàn bộ báo cáo.
