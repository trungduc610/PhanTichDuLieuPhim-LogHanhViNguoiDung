# Tích hợp HDFS cho TV2

Nguồn hiện chọn: run-f63c810e9d8d. Status/reconciliation PASS, 254 file Sink,
1.000.000 events; movies local có 9.742 phim. Đây là kết quả local, chưa đủ
để tuyên bố HDFS/Spark hiện tại PASS.

## Tạo cluster/snapshot mới

Dùng Python >=3.10 và Docker CLI/Engine Linux tại root project:

```powershell
python -B scripts/run_hdfs.py --flume-run-id run-f63c810e9d8d --audit-dir evidence/week2-hdfs/check-new
```

Audit-dir phải mới; lấy context từ check-new/run-context.json. Runner tạo
project/volumes riêng và chờ DataNode live, safe mode OFF. Tiếp tục theo context:

```powershell
$contextFile='evidence/week2-hdfs/check-new/run-context.json'
$context=Get-Content $contextFile -Raw | ConvertFrom-Json
$env:HDFS_RUN_ID=$context.run_id
$clusterProject=$context.project
$evidenceDir=$context.evidence

docker compose -f compose.hdfs.yaml -p $clusterProject config
docker compose -f compose.hdfs.yaml -p $clusterProject ps
docker compose -f compose.hdfs.yaml -p $clusterProject exec -T namenode hdfs dfsadmin -report
docker compose -f compose.hdfs.yaml -p $clusterProject exec -T namenode hdfs dfsadmin -safemode get
python -B scripts/hdfs_io.py --context $contextFile --upload --client spark --label import-first
```

Nếu runtime bị chặn, chỉ tiếp tục khi Docker/HDFS sẵn sàng. Có thể start lại đúng
cluster theo context bằng lệnh dưới; không format hoặc xóa volume cũ:

```powershell
docker compose -f compose.hdfs.yaml -p $clusterProject up -d namenode datanode
```

## URI và provenance

Đọc movies_uri, logs_uri từ source_manifest.json của context:

- hdfs://namenode:9000/movie-log/raw/movies/<snapshot>/movies.csv
- hdfs://namenode:9000/movie-log/raw/user_logs/run-f63c810e9d8d/<hdfs-run-id>/
- /movie-log/processed và /movie-log/results cho bước tiếp theo.

Manifest lưu selected run, nguồn local, bytes, SHA256, expected_records và đích
HDFS. Danh sách Sink lấy từ reconciliation. Generated input chỉ kiểm lineage,
không được upload thay Sink. Evidence cũ có config_sha256 được hỗ trợ; nếu có
source_config_hashes, tất cả hash đó vẫn được kiểm. Hash bắt buộc log4j2.xml:
f7f47e1246016eaa5bfaa0a65a8c66be712baac931e05ce30adfd694625b277b.
Kiểm byte-exact, không chuẩn hóa lúc kiểm và không sửa evidence cũ để tạo PASS.

## Upload lại

```powershell
python -B scripts/hdfs_io.py --context $contextFile --upload --client spark --label import-repeat
```

Đích đã có chỉ SKIP khi actual remote bytes có size/SHA256 khớp; khác thì FAIL,
không overwrite. Mỗi lần dùng label mới để bảo toàn report. Upload dở tiếp tục
bằng việc skip file đã đúng và put file thiếu. Verifier chỉ kiểm hai raw namespaces,
vẫn bắt file thiếu/thừa trong snapshot; processed/results và snapshot khác không
gây FAIL. Không dùng down -v, format thủ công, put -f hoặc xóa snapshot cũ.

## Spark đọc HDFS

```powershell
docker compose -f compose.hdfs.yaml -p $clusterProject --profile spark run --rm --no-deps spark --driver-memory 2g scripts/spark_hdfs_validate.py --source-manifest "$evidenceDir/source_manifest.json" --hdfs-verification "$evidenceDir/import-first.json" --report "$evidenceDir/spark-hdfs-new.json"
docker compose -f compose.hdfs.yaml -p $clusterProject --profile spark run --rm --no-deps spark --driver-memory 1g scripts/hdfs_hash_verify.py --source-manifest "$evidenceDir/source_manifest.json" --report "$evidenceDir/hdfs-hashes-new.json"
```

Content report phải PASS, đúng hash manifest. Job kiểm filesystem
org.apache.hadoop.hdfs.DistributedFileSystem, HDFS URI, input file list/count/schema,
malformed/null/type/duplicate/orphan/session; local_fallback=false. Report phải mới.
Spark mount Hadoop XML và cùng network với NameNode/DataNode. namenode:9000
không phải endpoint công khai từ Windows host.

Schema ở src/schemas.py: movieId LongType, timestamp UTC Z, watchDuration là giây
phát sinh; log/runtime synthetic. Một NameNode/DataNode, replication 1: demo,
không HA/dự phòng. Snapshot hdfs-385a18d3f03a và run-aa6b9eb58dca trong báo cáo cũ
là lịch sử, không phải nguồn hiện chọn. Chưa thực hiện công việc TV2 trong phần này.

For many Sink parts, --client spark reuses Hadoop Java client in one JVM.
The CLI client remains available. Both verify remote bytes and forbid overwrite.
The Java byte-verification report is followed by independent Spark count/schema QA.

## Snapshot đã kiểm chứng tại checkout này

Cluster: hdfs-124cbf30bda7; Compose project: movie-hdfs-124cbf30bda7.

- [Context hiện tại](../evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json)
- [Source manifest](../evidence/week2-hdfs/hdfs-124cbf30bda7/source_manifest.json)
- [Acceptance checks](../evidence/week2-hdfs/hdfs-124cbf30bda7/acceptance_status.json)
- [Spark HDFS QA](../evidence/week2-hdfs/hdfs-124cbf30bda7/spark-hdfs-fixed.json)

Đã kiểm trực tiếp: NameNode/DataNode running, safe mode OFF, fsck HEALTHY,
255 file raw đúng SHA256, 9.742 phim, 1.000.000 events; 23 nhóm lỗi Spark = 0.
Upload lại: 0 file mới, 255 SKIP_VERIFIED. Filesystem là
org.apache.hadoop.hdfs.DistributedFileSystem, local_fallback=false.

Movies: hdfs://namenode:9000/movie-log/raw/movies/mls-1df01064e7a0-hdfs-124cbf30bda7/movies.csv

Logs: hdfs://namenode:9000/movie-log/raw/user_logs/run-f63c810e9d8d/hdfs-124cbf30bda7

Để tiếp tục snapshot này, dùng context liên kết ở trên. Content byte-verification
report là content-import-java-v2.json; Spark QA là spark-hdfs-fixed.json. Các lệnh
check-new ở trên dùng cho một lần triển khai mới. Giữ nguyên raw snapshot;
TV2 ghi output mới dưới processed/results. Cluster/volumes đang được giữ.
