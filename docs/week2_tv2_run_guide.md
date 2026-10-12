# Hướng dẫn chạy TV2 Tuần 2

TV2 xử lý MovieLens metadata và user log đã đi qua Apache Flume File Roll Sink rồi nhập HDFS. Runner đọc manifest của TV1, kiểm tra HDFS đang chạy, xác minh raw, chạy cleaning → transformation → join → Parquet → thống kê → user features → K=2..6 → chọn model → export → kiểm tra raw sau chạy.

## Runtime và input

Chạy từ thư mục gốc project bằng Python >=3.10 trên host và Docker Desktop Linux containers. Spark chạy trong container, không cần cài PySpark/Java trên host. Context hiện tại:

```text
evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json
hdfs-124cbf30bda7
movie-hdfs-124cbf30bda7
```

Input được lấy từ source manifest, không từ generated/main.jsonl:

```text
hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-124cbf30bda7/movies.csv
hdfs://namenode:9000/movie-log/raw/user_logs/run-f63c810e9d8d/hdfs-124cbf30bda7
```

Runner yêu cầu NameNode/DataNode running, safe mode OFF và filesystem thực tế là org.apache.hadoop.hdfs.DistributedFileSystem. Nếu không đạt, runner FAIL và giữ evidence; không fallback local hay tự tạo lại cluster.

Overlay compose.tv2.yaml chỉ bổ sung image Spark có NumPy 1.24.4, cần cho PySpark MLlib. Image gốc vẫn là Spark 3.5.1. Dockerfile.tv2 không thay đổi compose.hdfs.yaml hoặc config TV1. Build cần truy cập package index nếu image TV2 chưa có.

## Lệnh chạy

Ví dụ PowerShell, đặt biến executable Python thật nếu lệnh python trên máy chỉ là WindowsApps alias:

```powershell
$py = 'C:\Users\GIGA\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -B scripts/run_tv2.py --hdfs-context evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json
```

Mặc định driver-memory=1536m và seed lấy từ event manifest (run hiện tại là 42). Có thể truyền --driver-memory 1536m hoặc --seed 42. Không chạy đồng thời hai TV2 job trên máy khi chưa đánh giá bộ nhớ Docker.

Mỗi lần chạy tạo tv2-<12 hex> mới và evidence/week2-tv2/<run-id>/. Mọi HDFS writer dùng errorifexists hoặc model save không overwrite:

```text
hdfs://namenode:9000/movie-log/processed/tv2/<run-id>/
hdfs://namenode:9000/movie-log/results/tv2/<run-id>/
```

Chạy lại bằng runner sẽ tạo namespace mới, giữ nguyên output/evidence cũ. Không chạy lại trực tiếp tv2_pipeline.py với context đã có output.

Runner tự ghi argv, cwd, thời gian UTC, exit code, stdout.txt và stderr.txt vào commands/<step-id>/. run_status.json là kết luận toàn bộ run; pipeline_summary.json là kết luận job Spark. Phải có cả hai PASS và raw-before/raw-after PASS mới nghiệm thu.

## Kiểm thử và bước độc lập

Host tests:

```powershell
& $py -B -m unittest discover -s tests -p test_tv2*.py -v
```

Spark fixture tests dùng DataFrame tạm trong bộ nhớ. Để chạy riêng, chọn report mới chưa tồn tại:

```powershell
$env:HDFS_RUN_ID = 'hdfs-124cbf30bda7'
docker compose -f compose.hdfs.yaml -f compose.tv2.yaml -p movie-hdfs-124cbf30bda7 --profile spark build spark
docker compose -f compose.hdfs.yaml -f compose.tv2.yaml -p movie-hdfs-124cbf30bda7 --profile spark run --rm --no-deps spark --driver-memory 1g scripts/tv2_spark_tests.py --report evidence/week2-tv2/fixture-check-new.json
```

Runner chính đã bao gồm các kiểm thử này, hash raw trước/sau, read-back số dòng của các output và reload model để kiểm tra assignment giống nhau. Không cần chạy lại Flume hoặc sinh thêm log.

## Quy ước dữ liệu và features

Schema nghiệp vụ được import từ src/schemas.py. Movie releaseYear được phép null. Log có 12 field bắt buộc; required null được kiểm tra riêng vì reader không cưỡng chế nullable=false.

Timestamp gốc dạng UTC Z. eventTimestamp dùng UTC; date/hour/dayOfWeek lấy theo Asia/Ho_Chi_Minh. dayOfWeek: 1=Chủ nhật, 7=Thứ bảy. eventLocalTimestamp là wall-clock địa phương được tính bằng from_utc_timestamp trong Spark session UTC.

watchDuration giữ nguyên giây mới phát sinh ở mỗi đoạn xem; watchDurationMinutes là cột mới. Không cộng duration như giá trị tích lũy của phiên. genresArray tách dấu |, trim và loại phần tử trùng; giữ (no genres listed) là nhóm metadata chưa biết.

Dataset user_features giữ đủ 10 feature yêu cầu và 3 cột giải thích completionRate:
playedSessionCount, completedSessionCount, completionRateDefined. Khóa session là (runId, sessionId).

- playCount/completeCount: số event theo action, play có thể gồm resume.
- totalWatchDuration: tổng giây watchDuration.
- avgWatchDuration: trung bình đoạn watchDuration >0; 0 nếu không có đoạn xem.
- distinctMovies/distinctGenres: số giá trị khác nhau trên toàn bộ tương tác hợp lệ.
- sessionCount: số session khác nhau.
- completionRate: số session có complete / số session có play; 0 và defined=false nếu mẫu số 0.
- activeDays: số ngày địa phương có event.
- eventCount: tổng event hợp lệ.

ML kiểm null/NaN/Infinity, loại feature có variance=0 và loại eventCount nếu xác minh đúng eventCount=sessionCount+2*playCount trên toàn bộ users. Những cột này vẫn có trong dataset/profile. selected_k.json ghi rõ feature vector cuối cùng, variance, lý do loại và cấu hình scaler.

VectorAssembler → StandardScaler(withMean=true, withStd=true) → PySpark MLlib KMeans(seed=42, maxIter=50). K=2..6 đều được fit thật và đánh giá ClusteringEvaluator silhouette squaredEuclidean. Chọn điểm cao nhất; chỉ chọn K nhỏ hơn khi điểm bằng nhau chính xác. Không dùng sklearn hoặc K chọn trước.

## Bàn giao cho Dashboard

Mỗi nhóm stats và K-Means có thư mục parquet/, csv/, json/ dưới results_root. Output nhỏ dùng một data part; không giả định tên part cố định. Đọc *.csv/*.json, bỏ _SUCCESS. CSV có header UTF-8, JSON là newline-delimited ở HDFS.

Bản local nhỏ nằm tại evidence/week2-tv2/<run-id>/dashboard/*.csv và *.json. JSON local là array, tiện cho Dashboard. Các cột array như cluster_sizes được encode JSON trong CSV. Full metadata nằm tại selected_k.json/model_metadata.json và HDFS results_root/reports/.

Processed cleaned_logs/joined_events/rejected_logs/user_features là Parquet. Dataset lớn repartition 8, không coalesce(1). Model đã lưu dưới results_root/kmeans/model và chứa assembler, fitted scaler, selected KMeans model. Cần sử dụng cùng Spark/runtime để load.

Xem output_manifest.json để lấy URI, schema, số dòng ghi/đọc lại và danh sách file thực tế. Không hard-code run cũ trong Dashboard; dùng run_context.json của run PASS muốn bàn giao. Báo cáo kết quả đã chạy: [week2_tv2_processing_report.md](week2_tv2_processing_report.md).

## Giới hạn diễn giải

Log và movie runtime là synthetic; các cluster chỉ mô tả cohort giả lập trong tháng dữ liệu. Silhouette đánh giá phân tách trên vector đã scale, không chứng minh hành vi người dùng thật hay chất lượng recommendation. Các feature về số lần hoạt động còn tương quan dù eventCount bị loại. Median dùng percentile_approx với accuracy=10000, stddev là sample stddev. Genre play được tính cho mỗi genre của phim nên tổng genre counts có thể lớn hơn tổng play.
