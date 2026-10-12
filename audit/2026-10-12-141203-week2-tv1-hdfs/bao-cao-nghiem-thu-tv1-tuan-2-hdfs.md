# Nghiệm thu TV1 Tuần 2 — HDFS

Nhan Tử Mạnh — “Phân tích dữ liệu phim và log hành vi người dùng”. Báo cáo được lập từ bằng chứng thực tại 2026-10-12T08:19:33.933558+00:00.

## A. Kết luận

**Phần việc TV1 Tuần 2 đã hoàn thành đầy đủ chưa? Có, về phạm vi triển khai và nghiệm thu kỹ thuật được yêu cầu: 10/10 nhiệm vụ ĐẠT (100%); đủ 7/7 sản phẩm.** Không có blocker kỹ thuật TV1 còn lại. Năm trạng thái riêng runtime/upload/content/Spark/E2E đều ĐẠT tại [evidence/week2-hdfs/hdfs-385a18d3f03a/acceptance_status.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/acceptance_status.json:1). Checkpoint startup `runtime_status.json` vẫn giữ trạng thái các bước chưa chạy ở thời điểm khởi động; không bị sửa hồi tố.

Xác nhận của nhóm về kiến trúc và phần giới thiệu/cơ sở lý thuyết Tuần 1 vẫn thiếu; chưa có xác nhận TV2 đã nhận hoặc tích hợp. Đây là điều kiện phối hợp chưa được chứng minh, không được tự coi đã phê duyệt. Không kết luận toàn bộ Tuần 2 hoàn thành: tiền xử lý chuyên sâu, phân tích, K-Means và dashboard nằm ngoài lượt này.

## B. Phạm vi, revision, runtime và giới hạn

Root/cwd mọi command: `C:\Users\User\Documents\GitHub\PhanTichDuLieuPhim-LogHanhViNguoiDung`. HEAD `bcb28b7fac0c9d260af0e6acb121947f991355f8`, branch main; không commit/push. 23 tracked modifications có sẵn từ trước; lượt TV1 Tuần 2 chỉ thêm file mới. [audit/2026-10-12-141203-week2-tv1-hdfs/artifacts-final.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/artifacts-final.json:1) xác minh **514/514 tệp có trước** không đổi bytes/SHA256 và manifest Tuần 1 **344/344** còn khớp. Git status/diff/revision cuối tại [evidence/week2-hdfs/hdfs-385a18d3f03a/git-final.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/git-final.json:1).

Project `movie-hdfs-385a18d3f03a`; cluster/import `hdfs-385a18d3f03a`; source Flume `run-aa6b9eb58dca`. Một NameNode, một DataNode, Docker network riêng, hai named volumes; replication 1, block size 128 MiB. Servers còn chạy để TV2 dùng; không xóa volume. Không bật lại Flume. UI [NameNode thực](http://127.0.0.1:19870/dfshealth.html#tab-overview).

Hadoop server 3.3.6/Java 1.8.0_212, image Apache digest `62a22627f35a1bbf29c721192c02fe311c93749cc43d51df01792b2ac40ff144`. Spark/PySpark 3.5.1, Hadoop client 3.3.4, Python 3.8.10, Java 11.0.22, local[2], driver 2 GiB, UTC. Host Python dùng ghi audit: 3.12.14, không phải Python của Spark. Client/server đã đọc thật trong [evidence/week2-hdfs/hdfs-385a18d3f03a/spark-hdfs.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/spark-hdfs.json:1). Docker Client/Engine 29.7.2, Linux containers, context desktop-linux; version/info/context/Compose thực nằm trong commands.

Mô hình demo một máy, simple auth, root chỉ trong container; không HA hoặc dự phòng khi mất DataNode/host/volume. Host trước Docker khoảng 16,6 GB RAM tổng, 7,6 GB available, 70 GB C: free; số capacity khoảng 1 TB do DataNode báo là dung lượng filesystem WSL, không suy ra host còn 1 TB đĩa vật lý. Không cài hệ thống, sửa quyền host hay WSL. Log/runtime phim synthetic; metadata HDFS là CSV đã chuẩn hóa, raw ZIP/license local giữ nguyên.

## C. Ma trận đủ 10 nhiệm vụ

| ID | Yêu cầu | Trạng thái | Bằng chứng (file:dòng khi là source/docs) | Thiếu sót | Việc cần làm |
|---|---|---|---|---|---|
| TV1-W2-01 | HDFS thật với NameNode/DataNode | ĐẠT | [compose.hdfs.yaml](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/compose.hdfs.yaml:2); [scripts/hdfs_service.sh](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_service.sh:19); [evidence/week2-hdfs/hdfs-385a18d3f03a/final-runtime.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/final-runtime.json:1) | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |
| TV1-W2-02 | Namespace raw, processed, results theo snapshot/run/import | ĐẠT | [scripts/hdfs_source.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_source.py:63); [evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json:1); final-list trong final-runtime | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |
| TV1-W2-03 | Metadata và chính Sink Flume thật lên HDFS | ĐẠT | [scripts/hdfs_io.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_io.py:36); [evidence/week2-hdfs/hdfs-385a18d3f03a/upload_status.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/upload_status.json:1); [evidence/week2-hdfs/hdfs-385a18d3f03a/content-import.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/content-import.json:1) | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |
| TV1-W2-04 | Tồn tại, dung lượng, nội dung và trạng thái HDFS | ĐẠT | [scripts/hdfs_io.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_io.py:51); [evidence/week2-hdfs/hdfs-385a18d3f03a/final-runtime.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/final-runtime.json:1); [evidence/week2-hdfs/hdfs-385a18d3f03a/screenshots/namenode-full-page.jpg](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/screenshots/namenode-full-page.jpg) | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |
| TV1-W2-05 | Đối chiếu đầy đủ file/bytes/SHA256/count | ĐẠT | [scripts/hdfs_io.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_io.py:64); [scripts/hdfs_hash_verify.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_hash_verify.py:32); [evidence/week2-hdfs/hdfs-385a18d3f03a/content-after-restart.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/content-after-restart.json:1); [evidence/week2-hdfs/hdfs-385a18d3f03a/final-hdfs-hashes.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/final-hdfs-hashes.json:1) | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |
| TV1-W2-06 | Job/config và hợp đồng tích hợp Spark cho TV2 | ĐẠT | [scripts/spark_hdfs_validate.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/spark_hdfs_validate.py:13); [docs/week2_tv2_hdfs_handoff.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_tv2_hdfs_handoff.md:5); [evidence/week2-hdfs/hdfs-385a18d3f03a/spark-hdfs.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/spark-hdfs.json:1) | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |
| TV1-W2-07 | Flume → Sink → HDFS → Spark được chứng minh | ĐẠT | [scripts/hdfs_source.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_source.py:21); [evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json:1); [evidence/run-aa6b9eb58dca/reconciliation.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/run-aa6b9eb58dca/reconciliation.json:1); [evidence/week2-hdfs/hdfs-385a18d3f03a/acceptance_status.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/acceptance_status.json:1) | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |
| TV1-W2-08 | Cấu hình/lệnh/log/ảnh/lỗi có bằng chứng | ĐẠT | [scripts/hdfs_common.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_common.py:18); [audit/2026-10-12-141203-week2-tv1-hdfs/commands-final.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/commands-final.json:1); [evidence/week2-hdfs/hdfs-385a18d3f03a/screenshots/namenode-full-page.jpg](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/screenshots/namenode-full-page.jpg); mục F | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |
| TV1-W2-09 | Chương báo cáo lý thuyết và thực nghiệm HDFS | ĐẠT | [docs/week2_tv1_hdfs_report.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_tv1_hdfs_report.md:5); [docs/week2_tv1_hdfs_report.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_tv1_hdfs_report.md:72) | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |
| TV1-W2-10 | Kiến trúc sau bổ sung HDFS, rõ phần tiếp theo | ĐẠT | [docs/week2_system_architecture.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_system_architecture.md:6); [docs/week2_system_architecture.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_system_architecture.md:26) | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |


TV1-W2-06 nghiệm thu việc chuẩn bị hợp đồng và chạy job thực; không khẳng định TV2 đã xác nhận. TV1-W2-09/10 nghiệm thu tài liệu/sơ đồ được bổ sung; không khẳng định nhóm đã phê duyệt. Chỉ tính số ĐẠT/10 × 100; không cộng điều kiện phối hợp chưa xác minh vào số ĐẠT.

## D. Bảy sản phẩm bàn giao

| STT | Sản phẩm | Trạng thái | Artifact |
|---|---|---|---|
| 1 | Cấu hình và runtime HDFS Docker chạy được | ĐẠT | [compose.hdfs.yaml](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/compose.hdfs.yaml:1); [config/hdfs/core-site.xml](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/config/hdfs/core-site.xml:1); [config/hdfs/hdfs-site.xml](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/config/hdfs/hdfs-site.xml:1); [scripts/hdfs_service.sh](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_service.sh:1) |
| 2 | NameNode/DataNode hoạt động | ĐẠT | [evidence/week2-hdfs/hdfs-385a18d3f03a/final-runtime.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/final-runtime.json:1); [evidence/week2-hdfs/hdfs-385a18d3f03a/persistence-reviewed.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/persistence-reviewed.json:1) |
| 3 | Movie dataset và output Flume thật trên HDFS | ĐẠT | [evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json:1); [evidence/week2-hdfs/hdfs-385a18d3f03a/content-after-restart.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/content-after-restart.json:1); URI/từng tệp ở mục E |
| 4 | Job/config và bằng chứng Spark HDFS | ĐẠT | [scripts/spark_hdfs_validate.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/spark_hdfs_validate.py:1); [evidence/week2-hdfs/hdfs-385a18d3f03a/spark-hdfs.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/spark-hdfs.json:1); [docs/week2_tv2_hdfs_handoff.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_tv2_hdfs_handoff.md:1) |
| 5 | Ảnh/lệnh/log và đối chiếu HDFS | ĐẠT | [evidence/week2-hdfs/hdfs-385a18d3f03a/screenshots/namenode-full-page.jpg](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/screenshots/namenode-full-page.jpg); [audit/2026-10-12-141203-week2-tv1-hdfs/commands-final.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/commands-final.json:1); [evidence/week2-hdfs/hdfs-385a18d3f03a/final-hdfs-hashes.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/final-hdfs-hashes.json:1) |
| 6 | Nội dung báo cáo lưu trữ phân tán | ĐẠT | [docs/week2_tv1_hdfs_report.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_tv1_hdfs_report.md:1) |
| 7 | Sơ đồ kiến trúc cập nhật | ĐẠT | [docs/week2_system_architecture.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_system_architecture.md:6) |

## E. Commands, UTC, exit code và kết quả đo

Catalog đầy đủ **166 command records đã hoàn tất**: [audit/2026-10-12-141203-week2-tv1-hdfs/commands-final.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/commands-final.json:1). Mỗi entry giữ argv dưới dạng mảng, cwd, UTC bắt đầu/kết thúc, environment và đường dẫn stdout/stderr; record raw vẫn còn ở `execution/*/command.json` hoặc `commands/*/finished.json`. Không đưa exit 1 của phép thử từ chối vào kết quả upload/E2E thành công. Lượt tạo/verify manifest diễn ra sau catalog này, có command records riêng được loại khỏi chính manifest để tránh vòng tự hash.

| Bước outer wrapper | UTC bắt đầu → kết thúc | Exit code | Record và stdout/stderr cùng thư mục |
|---|---|---:|---|
| git-before-5f4ede1a | 2026-10-12T07:13:24.222823+00:00 → 2026-10-12T07:13:24.613821+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/git-before-5f4ede1a/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/git-before-5f4ede1a/command.json:1) |
| week1-manifest-3d114c75 | 2026-10-12T07:13:24.870825+00:00 → 2026-10-12T07:13:30.324892+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/week1-manifest-3d114c75/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/week1-manifest-3d114c75/command.json:1) |
| host-resources-1815b00b | 2026-10-12T07:13:30.686893+00:00 → 2026-10-12T07:13:31.495890+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/host-resources-1815b00b/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/host-resources-1815b00b/command.json:1) |
| docker-version-98aa7368 | 2026-10-12T07:13:31.288893+00:00 → 2026-10-12T07:13:31.789230+00:00 | 1 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/docker-version-98aa7368/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/docker-version-98aa7368/command.json:1) |
| docker-info-6c0549b4 | 2026-10-12T07:13:31.996229+00:00 → 2026-10-12T07:13:33.682142+00:00 | 1 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/docker-info-6c0549b4/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/docker-info-6c0549b4/command.json:1) |
| spark-hadoop-client-22a9adab | 2026-10-12T07:13:33.897190+00:00 → 2026-10-12T07:13:34.219602+00:00 | 1 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/spark-hadoop-client-22a9adab/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/spark-hadoop-client-22a9adab/command.json:1) |
| docker-ready-1c45cd3d | 2026-10-12T07:15:07.434287+00:00 → 2026-10-12T07:15:07.785560+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/docker-ready-1c45cd3d/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/docker-ready-1c45cd3d/command.json:1) |
| spark-client-ready-490f7734 | 2026-10-12T07:15:08.122051+00:00 → 2026-10-12T07:15:12.602172+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/spark-client-ready-490f7734/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/spark-client-ready-490f7734/command.json:1) |
| hadoop-pull-c399a88c | 2026-10-12T07:15:12.905444+00:00 → 2026-10-12T07:19:03.463484+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/hadoop-pull-c399a88c/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/hadoop-pull-c399a88c/command.json:1) |
| hadoop-image-inspect-b802e46a | 2026-10-12T07:20:35.827136+00:00 → 2026-10-12T07:20:36.189828+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/hadoop-image-inspect-b802e46a/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/hadoop-image-inspect-b802e46a/command.json:1) |
| hadoop-runtime-inspect-bd7b32f5 | 2026-10-12T07:20:36.380091+00:00 → 2026-10-12T07:20:38.252456+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/hadoop-runtime-inspect-bd7b32f5/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/hadoop-runtime-inspect-bd7b32f5/command.json:1) |
| hdfs-runtime-16d5530c | 2026-10-12T07:24:35.471876+00:00 → 2026-10-12T07:25:41.377839+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/hdfs-runtime-16d5530c/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/hdfs-runtime-16d5530c/command.json:1) |
| hdfs-import-5a48dd7d | 2026-10-12T07:30:57.660489+00:00 → 2026-10-12T07:41:46.582153+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/hdfs-import-5a48dd7d/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/hdfs-import-5a48dd7d/command.json:1) |
| hdfs-guards-6d53ded8 | 2026-10-12T07:38:21.481167+00:00 → 2026-10-12T07:38:30.661857+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/hdfs-guards-6d53ded8/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/hdfs-guards-6d53ded8/command.json:1) |
| hdfs-persistence-6def900b | 2026-10-12T07:44:57.147740+00:00 → 2026-10-12T07:51:18.474422+00:00 | 1 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/hdfs-persistence-6def900b/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/hdfs-persistence-6def900b/command.json:1) |
| persistence-review-817a4eb7 | 2026-10-12T07:53:32.541492+00:00 → 2026-10-12T07:53:32.876771+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/persistence-review-817a4eb7/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/persistence-review-817a4eb7/command.json:1) |
| spark-hdfs-599fc32f | 2026-10-12T07:53:37.679787+00:00 → 2026-10-12T07:55:37.141647+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/spark-hdfs-599fc32f/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/spark-hdfs-599fc32f/command.json:1) |
| unit-tests-3814f723 | 2026-10-12T07:56:18.171560+00:00 → 2026-10-12T07:56:21.422227+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/unit-tests-3814f723/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/unit-tests-3814f723/command.json:1) |
| overwrite-refusal-2b4040d6 | 2026-10-12T07:56:27.208319+00:00 → 2026-10-12T07:56:46.666967+00:00 | 1 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/overwrite-refusal-2b4040d6/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/overwrite-refusal-2b4040d6/command.json:1) |
| final-hdfs-hashes-c5f93c1f | 2026-10-12T08:04:17.618869+00:00 → 2026-10-12T08:04:47.008791+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-hdfs-hashes-c5f93c1f/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-hdfs-hashes-c5f93c1f/command.json:1) |
| final-live-80f47a15 | 2026-10-12T08:08:19.105402+00:00 → 2026-10-12T08:08:42.733777+00:00 | 1 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-live-80f47a15/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-live-80f47a15/command.json:1) |
| final-live-reviewed-945f615c | 2026-10-12T08:10:05.693658+00:00 → 2026-10-12T08:10:42.130440+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-live-reviewed-945f615c/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-live-reviewed-945f615c/command.json:1) |
| final-artifacts-02ad5c86 | 2026-10-12T08:12:09.661480+00:00 → 2026-10-12T08:12:26.388722+00:00 | 1 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-artifacts-02ad5c86/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-artifacts-02ad5c86/command.json:1) |
| final-git-0910ce10 | 2026-10-12T08:13:34.039366+00:00 → 2026-10-12T08:13:34.992943+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-git-0910ce10/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-git-0910ce10/command.json:1) |
| final-artifacts-reviewed-d0e8c4fb | 2026-10-12T08:13:42.918151+00:00 → 2026-10-12T08:14:03.680593+00:00 | 1 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-artifacts-reviewed-d0e8c4fb/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-artifacts-reviewed-d0e8c4fb/command.json:1) |
| final-artifacts-closed-c03c596f | 2026-10-12T08:17:47.595578+00:00 → 2026-10-12T08:17:59.323906+00:00 | 0 | [audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-artifacts-closed-c03c596f/command.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/execution/final-artifacts-closed-c03c596f/command.json:1) |


Lệnh runtime nội bộ chính: `docker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a up -d namenode datanode`; `exec -T namenode hdfs dfs -mkdir -p ...`, `-test -e ...`, `-put <actual Sink> <snapshot>`; `-ls -R /movie-log`, `-du -s /movie-log/raw`, `-cat <từng tệp>`; `hdfs dfsadmin -report`, `-safemode get`; `hdfs fsck /movie-log -files -blocks -locations`. Không dùng `-put -f`, checksum HDFS thay SHA256, local fallback hoặc generated input thay Sink. Lệnh chính xác mỗi tệp gồm full path nằm trong catalog; các stdout.bin là byte thực đọc từ HDFS.


Movies URI: `hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-385a18d3f03a/movies.csv`.

Logs URI: `hdfs://namenode:9000/movie-log/raw/user_logs/run-aa6b9eb58dca/hdfs-385a18d3f03a`. Dưới đây tên/tổng byte/expected records/SHA256 từng tệp; HDFS URI từng log là logs URI + `/` + tên. Local logs là `data/runs/run-aa6b9eb58dca/output/<tên>`, metadata `data/processed/movies.csv`. Mỗi mapping đầy đủ nằm trong source manifest; mỗi phép đo thực nằm trong content report và final Java hash receipt.

| Tệp | Loại | Byte | Records | SHA256 (source = HDFS) |
|---|---|---:|---:|---|
| movies.csv | movies | 533347 | 9742 | `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536` |
| 1791733800297-1.jsonl | logs | 4463241 | 13000 | `6ed5f6b90cbb1d161426f2bd7ce0636a6df514111d90374babe095490c3bc6d3` |
| 1791733800297-10.jsonl | logs | 33132563 | 96500 | `41ef63fc07b4cec662e1ef7421522110cca0d164a41c48556b1f6a06a9773cff` |
| 1791733800297-11.jsonl | logs | 30213917 | 88000 | `c96c149a8dfbb6cb281c99ff586a76f096a653a8975d96c13e0719e5697ec476` |
| 1791733800297-12.jsonl | logs | 29183763 | 85000 | `a34334e974804408393bc0391b6953a31185c3acccce91f1ded75f843a3d5d0b` |
| 1791733800297-13.jsonl | logs | 27810781 | 81000 | `973b637795fe8a6ed8e124289432d9cb925bf9e4cb47c1c6fa407ea8f9b95e2b` |
| 1791733800297-14.jsonl | logs | 25063177 | 73000 | `ffda6b53198a9a59e62e7bec22a28c0fadb2cf5b28b3d05e63f9eae18891ec8f` |
| 1791733800297-15.jsonl | logs | 16995792 | 49500 | `50ee9e5eb716c5f65c8ec22eeba8b9be0087526d8832624fc929ac609d0c87e2` |
| 1791733800297-2.jsonl | logs | 23690281 | 69000 | `98b3379a79e466f890dbc870c7152de1975067c2ca8005b594290cc653cd3400` |
| 1791733800297-3.jsonl | logs | 23862302 | 69500 | `906db4c89f799a84579241ed538f4389c4901a05562f71f4373f922fa1752f29` |
| 1791733800297-4.jsonl | logs | 15792847 | 46000 | `7272a6197bb9a76ceb9c426cc224cef232a8780544fbe2a9c768901e8c225b0c` |
| 1791733800297-5.jsonl | logs | 16308520 | 47500 | `91e4b04ad6dfe69af904db00e9c5fe773ab15c6f4205736117667d44848d5b96` |
| 1791733800297-6.jsonl | logs | 23175894 | 67500 | `67a7b145e62c7557c601a55a50a34972ccb35c43e23b2607a0921025511afd16` |
| 1791733800297-7.jsonl | logs | 24892171 | 72500 | `000ff17e425ea92be8757b504aa8fc53721c20a1969420a1c64592edfe653290` |
| 1791733800297-8.jsonl | logs | 24032718 | 70000 | `38450c96d21781aad2aceb8f73f1cbee829be5a8dd249d40e844f9adf96c620e` |
| 1791733800297-9.jsonl | logs | 24721181 | 72000 | `e44b281d6b0a6c361297d7a833f629319a692b63acb08585ccf9ef6918ab9f58` |


**Tổng 16 tệp, 343.872.495 byte**: movies 9.742 rows/533.347 byte; logs 1.000.000 events/343.339.148 byte. File list thiếu/thừa 0, bytes/hash/count mismatch 0; 15 part không rỗng. CSV parser kiểm header/record; parse mọi JSON object/types; cat binary tính SHA256 trên toàn byte. Sau controlled restart, toàn bộ nội dung vẫn khớp. Kiểm cuối độc lập Hadoop Java stream cũng khớp cả 16 tệp, không đổi mtime/size trong lúc đọc.

HDFS fsck HEALTHY: 16 files/16 blocks, 1 live DataNode, replication thực 1, corrupt/missing/under-replicated/missing replicas đều 0, safe mode OFF. `du` đo logical bytes; DFS Used gồm block/checksum/storage overhead, không đồng nhất với logical bytes. Các thư mục processed/results tồn tại và trống.

Spark từ 2026-10-12T07:53:44.162081+00:00 tới 2026-10-12T07:55:36.680793+00:00: 9.742 movies, 1.000.000 events, 1.000.000 unique event IDs; 13 null releaseYear hợp lệ. 23 nhóm lỗi đều 0. Full anti join orphan=0, trùng/conflicting=0, malformed/null/type/time/action/duration/provenance/session đều 0. `input_file_name` đúng movies URI và đủ 15 logs HDFS URI; JVM filesystem là DistributedFileSystem; timezone UTC, eventTime TimestampType, movieId hai phía LongType. Schema contract và schema actual read được lưu đầy đủ; nullable khai báo không được dùng thay kiểm giá trị.

Năm stage ĐẠT được lập từ source manifest cùng run, PASS content và Spark đúng report hash. Generated chỉ nối input hash tới reconciliation Flume; output nguồn là chính Sink Tuần 1 đã xác minh, không chạy lại Flume vì dữ liệu/source không đổi.

## F. Lỗi đã xử lý, lỗi còn lại và mức ảnh hưởng

| Sự kiện thực tế | Xử lý và bằng chứng | Ảnh hưởng hiện tại |
|---|---|---|
| Docker pipe thiếu khi Engine chưa chạy; exit 1 | Giữ log docker-version/info/spark-hadoop-client ban đầu; mở Docker Desktop đã cài, kiểm ready lại | Đã xử lý; không đổi hệ thống |
| Poll lúc HDFS khởi động/restart; RPC chưa sẵn | Poll có giới hạn; chỉ nhận ready khi 1 DN live và safe mode OFF | Đã xử lý, mọi attempt được giữ |
| Volume inspect trước deploy exit 1 | Bằng chứng volume riêng chưa tồn tại; script còn kiểm volume trống trước format | Expected guard, không lỗi dữ liệu |
| Ba fixture container exit 1 | Từ chối nonempty unformatted/wrong cluster/invalid role; disposable tmpfs không đụng volume thật | Expected guard PASS; không là Flume evidence |
| Upload lại namespace hiện hữu exit 1 | `overwrite-refused.json` FAIL giữ nguyên; -test -e exit 0, không có -put trong khoảng lượt này | Chống ghi đè đạt, dữ liệu không đổi |
| Persistence verifier ban đầu FAIL do VERSION comment timestamp | Giữ raw trước/sau và `persistence.json`; sửa comparator kiểm tất cả Java properties, regression tests; lưu `persistence-reviewed.json` riêng | Dữ liệu toàn lô đã PASS, một lần format và restart reuse giữ nguyên identity; lỗi verifier đã xử lý |
| final-live verifier đòi chuỗi Dead datanodes (0) không tồn tại khi section được Hadoop bỏ | Giữ failed wrapper; đọc stdout thật, parse count khi có section và coi absent section=0, chạy lượt mới | Không lỗi cluster, final-runtime PASS |
| final-artifacts verifier đòi từ exist trong str(FileExistsError(path)) | Giữ failed wrappers; kiểm đúng path, -test exit 0 và command window không có -put. Lượt tiếp giữ FAIL do glob week2_ bao gồm docs/week2_handoff.md lịch sử; sửa sang kiểm ba đường dẫn mới cụ thể, bảo toàn doc cũ, chạy lượt mới | Không lỗi upload; artifacts-final PASS |
| Kiểm link ban đầu thử đọc JPEG như văn bản UTF-8 do link ảnh có :1 | Giữ failed wrapper delivery-paths; sửa link ảnh không dùng số dòng, chạy lại kiểm mọi link. Một câu lệnh chỉnh helper trước đó bị PowerShell ParserError trước thực thi, không thay file hay chạy Docker | Lỗi đóng gói tài liệu đã xử lý; không ảnh hưởng source/data/runtime |
| Xác nhận nhóm/TV2 chưa có | Không tự tạo xác nhận hoặc gửi tin nhắn | CHƯA THỂ XÁC MINH, điều kiện phối hợp còn thiếu; không cản các tiêu chí kỹ thuật TV1 này |

21 host unit tests PASS (gồm 3 regression VERSION); 3 container guards PASS; actual duplicate import từ chối đúng; Spark/HDFS final checks PASS. Không còn lỗi kỹ thuật HDFS/Spark mở trong phạm vi. Không có auto-review rejection hay hành động ngoài quyền cần người dùng duyệt.

## G. File thêm, manifest và tái kiểm chứng

Các file có trước không bị sửa. Các file mới về chức năng:

| File/dòng | Lý do thêm |
|---|---|
| [compose.hdfs.yaml](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/compose.hdfs.yaml:1) | Compose HDFS riêng, không bật Flume |
| [config/hdfs/core-site.xml](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/config/hdfs/core-site.xml:1) | fs.defaultFS và tmp dir |
| [config/hdfs/hdfs-site.xml](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/config/hdfs/hdfs-site.xml:1) | RPC/DN host/volumes/replication/block size |
| [config/hdfs/log4j.properties](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/config/hdfs/log4j.properties:1) | Log Hadoop ra console |
| [scripts/hdfs_service.sh](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_service.sh:1) | Format chỉ volume mới trống; bảo vệ cluster ID/reuse |
| [scripts/hdfs_common.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_common.py:1) | Command ledger và JSON reports tạo mới |
| [scripts/hdfs_source.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_source.py:1) | Đóng băng lineage Sink Tuần 1 và expected counts |
| [scripts/run_hdfs.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/run_hdfs.py:1) | Cluster/project/volume mới, ready check/version |
| [scripts/hdfs_io.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_io.py:1) | Namespace/upload no overwrite, parse/hash toàn HDFS |
| [scripts/spark_hdfs_validate.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/spark_hdfs_validate.py:1) | Đọc trực tiếp HDFS và full QA dùng schemas chung |
| [scripts/hdfs_hash_verify.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_hash_verify.py:1) | Kiểm byte SHA256 độc lập bằng Java Hadoop client |
| [scripts/hdfs_guard_tests.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_guard_tests.py:1) | Guard fixtures riêng, không là output Flume |
| [scripts/hdfs_restart_verify.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/hdfs_restart_verify.py:1) | Controlled restart, so mọi properties và dữ liệu |
| [scripts/create_hdfs_manifest.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/scripts/create_hdfs_manifest.py:1) | Manifest scope/exclusions, local verify tách remote |
| [tests/test_hdfs_properties.py](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/tests/test_hdfs_properties.py:1) | Regression kiểm properties không lẫn comment |
| [docs/week2_tv1_hdfs_report.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_tv1_hdfs_report.md:1) | Chương lý thuyết + thực nghiệm với nguồn Apache chính thức |
| [docs/week2_tv2_hdfs_handoff.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_tv2_hdfs_handoff.md:1) | Hợp đồng URI/schema/QA/lệnh/giới hạn cho TV2 |
| [docs/week2_system_architecture.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_system_architecture.md:1) | Sơ đồ và trạng thái đã chạy/công việc tiếp theo |


Thêm thư mục audit hiện tại chứa inventory trước, resource receipt, run_step/helpers, source-review đánh số dòng, artifacts-final, command catalog, báo cáo này và execution logs. Thêm evidence/week2-hdfs/hdfs-385a18d3f03a chứa context/source/runtime/upload/content/Spark/persistence/guards/final receipts, binary streams và ảnh thực. Manifest liệt kê từng tệp bàn giao kèm bytes/SHA256; danh sách source/doc kiểm cuối tại [audit/2026-10-12-141203-week2-tv1-hdfs/artifacts-final.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/artifacts-final.json:1) và [audit/2026-10-12-141203-week2-tv1-hdfs/source-review-final.txt](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/audit/2026-10-12-141203-week2-tv1-hdfs/source-review-final.txt:1).

Manifest mới: [evidence/week2-hdfs/hdfs-385a18d3f03a/delivery_manifest.json](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/delivery_manifest.json:1). Scope gồm source/config/tests/docs, root Compose/HDFS và file project chọn rõ, MovieLens raw/processed/generated (generated chỉ để lineage), 15 Sink thật, evidence Flume main, evidence recheck Tuần 1, audit/evidence của lượt này. Exclusions: .git, channel/spool, run/audit ngoài scope, fixtures/temporary/cache/part/CA tạm, image layers, named-volume metadata/blocks trực tiếp, manifest tự thân, bước tạo đang chạy và verification receipts về sau. Đây là bàn giao tệp + receipt HDFS, không phải export live volume portable.

Mọi local entry được kiểm bytes/SHA256 khi tạo và bằng lượt verify độc lập có receipt mới. `remote_hdfs.files` ghi URI/hash/bytes/records của 16 tệp đã đọc thật; verify local không khẳng định trạng thái HDFS sau đó. Khi cần xác minh remote hiện tại, chạy job Java hash với report mới, rồi full Spark QA khi dữ liệu/config thay đổi. Không sửa manifest cũ hoặc report cũ để tái dùng tên.


Lệnh kiểm lại (PowerShell tại root, cần Engine hoạt động cho remote):

```powershell
$pyExe='C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$verifyId=[guid]::NewGuid().ToString('N')
& $pyExe -B scripts/create_hdfs_manifest.py --verify evidence/week2-hdfs/hdfs-385a18d3f03a/delivery_manifest.json --receipt "evidence/week2-hdfs/hdfs-385a18d3f03a/manifest-verification-$verifyId.json"
& $pyExe -B scripts/create_delivery_manifest.py --verify evidence/recheck-20261011-221710/delivery_manifest.json
$env:HDFS_RUN_ID='hdfs-385a18d3f03a'
docker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a --profile spark run --rm --no-deps spark --driver-memory 1g scripts/hdfs_hash_verify.py --source-manifest evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json --report "evidence/week2-hdfs/hdfs-385a18d3f03a/hashes-reverify-$verifyId.json"
```

Lệnh khởi động HDFS và full Spark HDFS QA có tên report mới nằm tại [docs/week2_tv2_hdfs_handoff.md](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/docs/week2_tv2_hdfs_handoff.md:31). Không thay snapshots/raw hoặc chạy lại Flume khi không cần.

Ảnh UI thật sau restart, không dựng từ text/log:

![NameNode thực: cluster, DataNode, block và safe mode](C:/Users/User/Documents/GitHub/PhanTichDuLieuPhim-LogHanhViNguoiDung/evidence/week2-hdfs/hdfs-385a18d3f03a/screenshots/namenode-full-page.jpg)

Các ảnh viewport ban đầu vẫn giữ riêng; ảnh full-page là screenshot browser thực. Kết luận cuối: **TV1 Tuần 2 ĐẠT 10/10**. Điều kiện còn thiếu bên ngoài phạm vi kỹ thuật là xác nhận phối hợp của nhóm/TV2 và phần việc tiếp theo chưa chạy; không tuyên bố toàn bộ Tuần 2 hoặc báo cáo nhóm đã hoàn thành.
