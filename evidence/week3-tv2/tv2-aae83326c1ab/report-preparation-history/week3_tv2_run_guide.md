# TV2 Tuần 3 — chạy sau khi TV1 mở runtime gate

Baseline cố định theo yêu cầu: `run-f63c810e9d8d`, `hdfs-124cbf30bda7`, project `movie-hdfs-124cbf30bda7`. Không dùng release phục hồi khác. Trạng thái lần chuẩn bị: `tv2-0523e144a808` BLOCKED_BY_TV1_RUNTIME.

Chạy từ repo root bằng Python >=3.10 thật, Docker Linux containers và Compose. Nếu Python không ở PATH, đặt TV1_PYTHON thành executable hiện có của máy; không copy đường dẫn máy cá nhân từ report cũ.

```powershell
$py = $env:TV1_PYTHON
if (-not $py) {
  $py = (Get-Command python -All | Where-Object Source -NotMatch 'WindowsApps' | Select-Object -First 1).Source
}
if (-not $py) { throw 'Cần Python thật; đặt TV1_PYTHON.' }
& $py -B -m unittest discover -s tests -p 'test_tv2*.py' -v
& $py -B scripts/run_tv2.py --hdfs-context evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json --evidence-root evidence/week3-tv2
```

Runner tạo run/evidence/namespace mới; kiểm baseline, services, safe mode, live DataNode, fsck, raw files/bytes, full raw SHA256 và Spark input schema/count QA trước preprocessing. Nếu chưa đạt gate thì BLOCKED_BY_TV1_RUNTIME; không tự start/format/upload raw. Chưa kiểm chứng nhánh runtime-ready của sửa đổi Tuần 3 tại lần audit này.

Sau pipeline PASS, lấy run ID từ stdout rồi chạy verifier với cùng evidence root:

```powershell
$run = Read-Host 'TV2 Week 3 run ID vừa PASS'
& $py -B scripts/verify_tv2_results.py --run-id $run --evidence-root evidence/week3-tv2 --report "evidence/week3-tv2/$run/result-verification.json"
```

Report path phải mới. Verifier local chỉ đọc small exports và recorded lineage; không thay kiểm HDFS input hoặc independent recomputation bảy analysis từ joined. Hiện các cross-check này vẫn chờ runtime, xem [report mục 6](week3_tv2_processing_report.md#6-analysis-validation).

Runner PASS một mình chưa có nghĩa final TV3 handoff. Chỉ phát hành handoff khi các kiểm bổ sung cùng run đều PASS, model reload assignments khớp và raw-before/raw-after khớp source. Không sửa blocked receipt thành PASS, không overwrite output Tuần 2, không đổi Dashboard selection/UI.
