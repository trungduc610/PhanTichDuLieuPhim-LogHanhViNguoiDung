# Demo Dataset/Log → Flume → HDFS → Spark — Nhan Tử Mạnh

Dùng 5–8 phút. Mở PowerShell tại repo, chọn `$py` như README và `$ctx` là context bàn giao. Demo có thể read-only trên snapshot chính thức; lô Flume nhỏ là màn trình diễn riêng. Không rerun K-Means, đổi Dashboard hoặc restart giữa buổi nếu có job.

1. Giới thiệu `data/raw/ml-latest-small/README.txt`, `data/processed/movies.csv` và `data/generated/main.jsonl.manifest.json`. MovieLens là nguồn metadata; user/hành vi/runtime là mô phỏng; thời lượng là giây tăng thêm mỗi segment. Không lấy generated JSONL upload HDFS.
2. Mở `config/flume.conf`: r1→c1→k1, spooldir UTF-8/FAIL/LINE max 16384, File Channel, File Roll Sink TEXT + newline. Chỉ nhận `.jsonl`, bỏ qua `.tmp`; `.COMPLETED` giữ vết nhận. Đây là batch runner, Flume dừng sau drain/reconciliation.
3. Mở `official-ingestion-inherited.json` và reconciliation của run được chọn. Chỉ rõ đây là ingestion chính thức lịch sử đã kiểm lại hash source/config/input/tất cả Sink; mở `stability.json` của run nhỏ mới để chứng minh thực thi hiện tại. Part count được đo, không cố định.
4. Kiểm runtime, list HDFS và Web UI NameNode/Datanodes bằng lệnh dưới. URI chính thức lấy từ source manifest; mọi part Sink + movies có size/SHA256 tương ứng trên HDFS.
5. Chạy import an toàn rồi Spark kiểm input toàn bộ; mở report PASS và commands/stdout/stderr/exit. Repeat import phải `uploaded=0`, `skipped_verified=files`, count Spark không tăng.
6. Mở `persistence.json`, `preservation-check.json`, `delivery-verification.json` và screenshot thực. Persistence đã đo có kiểm soát; không cần restart lại khi trình bày. Nêu rõ một NameNode/một DataNode không HA.

```powershell
$ctx = 'evidence/week3-tv1/tv1-20261015-a91e7b2c/run-context.json'
& $py -B scripts/week3_tv1.py check --context $ctx
$folder = Split-Path $ctx
$source = Get-Content "$folder/source_manifest.json" -Raw | ConvertFrom-Json
$source | Select-Object flume_run_id,hdfs_run_id,expected_movies,expected_logs,movies_uri,logs_uri
$source.files | Select-Object kind,local_path,bytes,sha256,hdfs_path
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
& $py -B scripts/week3_tv1.py import --context $ctx --label "demo-import-$stamp"
& $py -B scripts/week3_tv1.py spark --context $ctx --verification "demo-import-$stamp" --label "demo-spark-$stamp"
Get-Content "$folder/demo-import-$stamp.json","$folder/demo-spark-$stamp.json" -Raw
& $py -B scripts/create_delivery_manifest.py --verify "$folder/delivery-manifest.json"
```

Muốn biểu diễn Flume trực tiếp, dùng runner gốc tạo run nhỏ mới, xem ID in cuối stdout và `evidence/<run>/status.json`/`reconciliation.json`. Không dùng `stability` trên context đã seal vì report `stability.json` cố ý không được ghi đè; một đợt nghiệm thu mới dùng `prepare` như README.

```powershell
& $py -B scripts/run_pipeline.py --input data/generated/demo.jsonl --timeout 600
```

Runner tạo spool/output/channel/volume riêng. Không publish lại cùng tên vào spool cũ; không dùng demo làm nguồn chính thức. Nếu lỗi, mở log của run, giữ FAIL và sửa trước khi chạy mới. Full Spark input QA có thể mất vài phút; chuẩn bị report đã đo và vẫn chạy lệnh khi cần chứng minh thực thi.

Bằng chứng mới cùng folder: `official-ingestion-inherited.json`, `stability.json`, `import-first.json`, `import-repeat.json`, `persistence-before.json`, `persistence-after.json`, `persistence.json`, `spark-full.json`, `acceptance.json`, `delivery-manifest.json`, `delivery-verification.json`. Commands có thời điểm UTC và exit code. Screenshot là capture trực tiếp trình duyệt localhost, không dựng từ log.

[README](../README.md) · [Sơ đồ](week3_tv1_architecture.md).
