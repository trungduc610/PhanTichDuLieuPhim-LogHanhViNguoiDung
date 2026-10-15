# TV2 Tuần 3 — final run và kiểm tra

Final **tv2-aae83326c1ab**, PASS. Baseline `run-f63c810e9d8d` / `hdfs-124cbf30bda7`; project `movie-hdfs-124cbf30bda7`. Xem [handoff](week3_tv2_handoff.md), [report](week3_tv2_processing_report.md).

Python >=3.10 thật trên host và Docker Linux containers. Đặt TV1_PYTHON nếu Python chưa ở PATH; không copy đường dẫn executable cá nhân từ docs cũ.

```powershell
$py = $env:TV1_PYTHON
if (-not $py) {
  $py = (Get-Command python -All | Where-Object Source -NotMatch 'WindowsApps' | Select-Object -First 1).Source
}
if (-not $py) { throw 'Cần Python thật; đặt TV1_PYTHON.' }
$run = 'tv2-aae83326c1ab'
Get-Content "evidence/week3-tv2/$run/handoff.json" -Raw
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
& $py -B scripts/verify_tv2_results.py --run-id $run --evidence-root evidence/week3-tv2 --report "evidence/week3-tv2/$run/reverify-$stamp.json"
```

Nếu cần chạy toàn bộ lần mới sau khi kiểm tài nguyên/không có job khác, runner tạo UUID/namespace mới, không resume/overwrite final hoặc blocked/FAIL attempts:

```powershell
& $py -B -m unittest discover -s tests -p 'test_tv2*.py' -v
& $py -B scripts/run_tv2.py --hdfs-context evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json --evidence-root evidence/week3-tv2 --seed 42 --driver-memory 1536m
```

Runner chạy raw-before/HDFS QA, unit/Spark fixtures, pipeline, independent verification và raw-after. Sau runner PASS chạy host result verifier và chỉ phát hành handoff khi nghiệm thu đủ. Validator tính lại 7 analysis/features từ joined HDFS, kiểm formats/schema/count/values, reload model/scaler. Không fallback local, start/format cluster hoặc upload raw. Context paths dùng repo-relative với dấu / để chạy trong Linux container.

Mọi report path phải mới. Không trộn Week 2/recovery/blocked/FAIL outputs; không rerun Flume/regenerate data hay sửa Dashboard selection/UI. Các receipts final được niêm phong bằng delivery-manifest.json; chỉ append report mới khi kiểm lại, không sửa receipts đã đo.
