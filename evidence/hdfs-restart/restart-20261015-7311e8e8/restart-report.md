# HDFS BASELINE RESTART REPORT

## 1. Status

**PASS** — kiểm chứng ngày 15/10/2026. Evidence kết luận: [acceptance.json](acceptance.json). Hai service được để running; chưa chạy pipeline TV2.

## 2. Baseline

- HDFS run: `hdfs-124cbf30bda7`.
- Compose project: `movie-hdfs-124cbf30bda7`.
- Flume run: `run-f63c810e9d8d`.

## 3. Volumes

- NameNode volume exists: YES — `movie-hdfs-124cbf30bda7_namenode`.
- DataNode volume exists: YES — `movie-hdfs-124cbf30bda7_datanode`.
- VERSION đã đọc trực tiếp trước startup; clusterID đúng baseline. Storage properties trước/sau không đổi.

## 4. Containers

- NameNode: running.
- DataNode: running.
- Giữ nguyên hai container ID/volumes. Compose up dùng --no-recreate, --no-build, --pull never. Hai log REUSE_VERIFIED_VOLUME; không có marker format mới.

## 5. HDFS health

- Live DataNode: 1.
- Safe mode: OFF.
- fsck /movie-log: HEALTHY.
- /movie-log/processed và /movie-log/results truy cập được.

## 6. Raw data

- Movies path: `hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-124cbf30bda7/movies.csv`.
- Logs path: `hdfs://namenode:9000/movie-log/raw/user_logs/run-f63c810e9d8d/hdfs-124cbf30bda7`.
- Movie files: 1.
- Log files: 254.
- Total selected raw files: 255.
- Bytes: 343,872,495.
- Full file listing/size, count và du khớp source manifest. SHA256 255/255 khớp; missing/extra/hash mismatch=0.

## 7. Spark read check

- Filesystem: org.apache.hadoop.hdfs.DistributedFileSystem.
- Local fallback: false.
- Movies: 9,742.
- Events / unique eventId: 1,000,000 / 1,000,000.
- Log source files: 254 (thêm 1 movies source file).
- QA: 23 nhóm, tất cả lỗi=0.
- Status: PASS. Đọc đúng HDFS, không local/generated input.
- Reports: [byte hashes](raw-hashes.json), [full QA](spark-hdfs-qa.json), [summary](spark-verification.json).

## 8. Safety confirmation

Không format, không xóa volume, không overwrite/reimport raw, không đổi cluster/run/project, không rerun Flume, không sửa source, không chạy pipeline TV2, không commit/push. Container QA được giữ lại trạng thái exited; không chạy lệnh xóa.

Kiểm tra ban đầu dừng trước startup vì hdfs_common.py khác receipt Tuần 2. Đã đọc source và ghi [historical-config-review.json](historical-config-review.json): chỉ helper evidence/namespace khác; toàn bộ bootstrap files khớp. VERSION hai volume và IDs được xác minh trước khi up. Không sửa hash/receipt cũ.

## 9. Can TV2 Week 3 continue?

**YES.** Runtime baseline, raw byte integrity và Spark input QA đều PASS hiện tại. TV2 cần tạo run Tuần 3 mới khi được yêu cầu; giữ nguyên blocked attempt `tv2-0523e144a808` và evidence lịch sử.
