# Phân tích dữ liệu phim và log hành vi người dùng

Luồng thành viên 1: Movie Dataset → HDFS; User Log → Apache Flume → File Roll Sink → HDFS; Spark đọc toàn bộ input HDFS theo schema hiện có.

## Tuần 3 — Nhan Tử Mạnh: vận hành và nghiệm thu

[Demo ngắn](docs/week3_tv1_demo.md) · [Kiến trúc triển khai](docs/week3_tv1_architecture.md) · [Context bàn giao](evidence/week3-tv1/tv1-20261015-a91e7b2c/run-context.json).
Kết quả đo và hash nằm trong `source_manifest.json`, `acceptance.json`, `delivery-manifest.json` và `delivery-verification.json` cùng thư mục. Run ID trong bằng chứng là lịch sử được chọn rõ; script không mặc định một run ID.

### Điều kiện môi trường

Python >=3.10 trên host, Docker Desktop/Engine dùng Linux containers và Docker Compose. Host scripts dùng stdlib; Spark/Java chạy trong container. Images của cluster được kiểm tra từ `docker inspect`, Hadoop 3.3.6 được pin digest trong `compose.hdfs.yaml`; Spark image 3.5.1; Flume 1.11.0/Temurin 8 được build từ Dockerfile. Cần Docker Engine truy cập được, đủ RAM/đĩa cho images, input, Sink, channel và SQLite; đã kiểm nghiệm với 4 CPU/~7.5 GiB Docker RAM.

Chạy tại repo root. Đặt `TV1_PYTHON` nếu cần chọn executable Python; ví dụ dưới bỏ qua alias WindowsApps không thực thi được:

```powershell
$py = $env:TV1_PYTHON
if (-not $py) {
  $py = (Get-Command python -All | Where-Object Source -NotMatch 'WindowsApps' | Select-Object -First 1).Source
}
if (-not $py) { throw 'Cần Python >=3.10; đặt TV1_PYTHON là executable Python thật.' }
& $py --version
& $py -B scripts/week3_tv1.py --help
docker context show
docker version
docker compose version
```

Data ngoài Git phải đi kèm khi bàn giao: `data/raw/` (ZIP, CSV nguồn, license, download manifest), `data/processed/movies.csv`, generated input cùng manifest và **Sink output của đúng run** trong `data/runs/<run>/output/`. Verifier từ chối thiếu/hỏng input hoặc Sink; không tự lấy generated input thay Sink. Giữ nguyên evidence lịch sử có đường dẫn tuyệt đối; code vận hành xác định root từ vị trí script và dùng đường dẫn tương đối/container path.

### Demo nhanh trên context đã bàn giao

```powershell
$ctx = 'evidence/week3-tv1/tv1-20261015-a91e7b2c/run-context.json'
& $py -B scripts/week3_tv1.py check --context $ctx
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
& $py -B scripts/week3_tv1.py import --context $ctx --label "demo-import-$stamp"
& $py -B scripts/week3_tv1.py spark --context $ctx --verification "demo-import-$stamp" --label "demo-spark-$stamp"
& $py -B scripts/create_delivery_manifest.py --verify ((Split-Path $ctx) + '/delivery-manifest.json')
```

`check`: đúng cluster/project/mount/volume, 1 DataNode sống, Safe Mode OFF, dung lượng và list namespace được chọn. `import`: chỉ movies + các part Sink trong manifest; hash mọi byte HDFS, bỏ qua file đã khớp, từ chối nội dung khác, không overwrite/append. `spark`: đọc tất cả URI HDFS và schema; kiểm filesystem thực là DistributedFileSystem, count, field/type/timestamp/action/duration, ID trùng, join và session; không đọc sample, không fallback local. Expected counts và part count lấy từ manifest đã xác minh. Không chạy K-Means hoặc đổi nguồn Dashboard.

### Tạo đợt nghiệm thu mới, kế thừa snapshot chính thức

Chọn context và acceptance đã bàn giao, không chọn context demo/fixture. Các giá trị là tham số, có thể dùng một bàn giao PASS khác tương thích. `prepare` reverify manifest bàn giao, source/config/input/Sink rồi tạo thư mục mới; không tạo hay format cluster.

```powershell
$sourceContext = $ctx
$officialAcceptance = (Split-Path $sourceContext) + '/acceptance.json'
$audit = 'evidence/week3-tv1/tv1-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
& $py -B scripts/week3_tv1.py prepare --source-context $sourceContext --official-acceptance $officialAcceptance --evidence-dir $audit
$ctxNew = "$audit/run-context.json"
& $py -B scripts/week3_tv1.py stability --context $ctxNew --input data/generated/demo.jsonl
& $py -B scripts/week3_tv1.py import --context $ctxNew --label import-first
& $py -B scripts/week3_tv1.py import --context $ctxNew --label import-repeat
& $py -B scripts/week3_tv1.py persistence --context $ctxNew
& $py -B scripts/week3_tv1.py spark --context $ctxNew --verification import-repeat --label spark-full
# Snapshot lịch sử bổ sung được kế thừa từ acceptance, nếu có:
& $py -B scripts/week3_tv1.py history --context $ctxNew
& $py -B scripts/week3_tv1.py seal --context $ctxNew
& $py -B scripts/create_delivery_manifest.py --verify "$audit/delivery-manifest.json"
```

Chỉ chạy persistence khi cần chứng minh đợt này: script kiểm tra không có container Spark/Flume đang chạy, VERSION/cluster ID/volume hợp lệ, hash toàn bộ trước/sau, restart đúng hai service cũ, kiểm tra DataNode/Safe Mode và không phát sinh format. Không dừng/restart khi nhóm đang có job bên ngoài Docker mà script không quan sát được. Một NameNode/một DataNode với replication=1 chỉ chứng minh persistence trong thử nghiệm; không phải HA.

`stability` chạy Flume theo lô, output/channel/spool/volume riêng. Runner publish file `.tmp` đóng xong bằng rename, chỉ nhận `.jsonl`, đánh dấu `.COMPLETED`, chờ drain/timeout rồi dừng agent trước reconciliation; container/network của chính run được gỡ, volume vẫn giữ. Channel không dùng chung giữa các lần chạy. Lô <=10.000 event chỉ là thử ổn định, không được import vào namespace chính thức.

### Nếu phải chạy lại ingestion chính thức

Chỉ cần khi source/config/input/Sink chính thức không còn xác minh được. Sửa lỗi trước, chạy demo mới PASS với cùng source/config rồi chạy main trong run mới. Dùng input chính thức có hash/manifest khớp, hoặc sinh input mới qua generator; không sửa file đang ở spool hay output đã nghiệm thu.

```powershell
& $py -B scripts/run_pipeline.py --input data/generated/demo.jsonl --timeout 600
# Lấy status.json của run demo vừa PASS từ stdout/evidence, truyền bằng tham số:
$demoProof = Read-Host 'Đường dẫn evidence/<demo-run>/status.json mới'
& $py -B scripts/run_pipeline.py --input data/generated/main.jsonl --timeout 1800 --demo-proof $demoProof
```

Để đổi release chính thức, nhóm phải chọn rõ run main mới và lập context/acceptance tương ứng sau kiểm chứng bằng `hdfs_source.py`/`hdfs_io.py`/`spark_hdfs_validate.py`. Không dùng `--flume-run-id` để đổi ngầm nguồn của một acceptance cũ; wrapper sẽ từ chối. Dataset phim upload trực tiếp, mọi log upload phải từ Sink Flume. Flume không được mô tả là đang chạy liên tục sau khi batch runner đã dừng.

### Khởi động và dừng an toàn

```powershell
& $py -B scripts/week3_tv1.py start --context $ctx
# Chỉ dừng khi không có job sử dụng cluster:
& $py -B scripts/week3_tv1.py stop --context $ctx
& $py -B scripts/week3_tv1.py start --context $ctx
```

`start` chỉ start container cũ đã kiểm mount/volume/VERSION; không có container thì từ chối tạo. Không dùng `run_hdfs.py` để tạo lại cluster đang có. Không format NameNode, `down -v`, prune, reset volume hoặc xóa dữ liệu. NameNode Web UI mặc định [localhost:19870](http://127.0.0.1:19870/dfshealth.html), kiểm port thực từ inspect nếu dùng port khác.

### Kiểm thử và lỗi thường gặp

```powershell
& $py -B -m unittest discover -s tests -v
```

| Hiện tượng | Kiểm tra/xử lý |
|---|---|
| Docker không truy cập được | Khởi động Engine Linux, kiểm context/version; đây là lỗi môi trường, không tạo PASS. |
| Python WindowsApps lỗi | Chọn Python thật bằng `TV1_PYTHON`; host không cần PySpark. |
| Official source/config hash đổi | Rerun demo rồi main; không sửa hash trong receipt cũ. |
| Manifest bàn giao cũ lệch vì source đã sửa | Giữ FAIL/issues cũ, kiểm chứng lại rồi seal manifest mới; không gọi manifest cũ là PASS hiện tại. |
| Sink thiếu/trùng/truncated/UTF-8 lỗi | Xem reconciliation của run; giữ evidence FAIL, chạy run mới sau khi sửa nguyên nhân. |
| Import khác hash/list | Từ chối overwrite, kiểm nguồn/namespace; không append/gộp nhiều run. |
| Direct Compose báo thiếu HDFS_RUN_ID | Dùng wrapper `--context`; nếu gọi Compose trực tiếp, lấy `$env:HDFS_RUN_ID` từ `run_id` trong context, không tự đặt ID khác. |
| Safe Mode ON hoặc không có DataNode | Kiểm `commands/*/stderr.txt`, logs hai service, VERSION/mount; không ép format để sửa. |
| Cluster/job đang bận | Hoãn persistence/stop; không reset để giành tài nguyên. |
| Report/label đã tồn tại | Dùng label/thư mục mới; không ghi đè bằng chứng. |

Lệnh Docker/Spark và unit tests lưu argv/cwd/UTC/exit/stdout/stderr dưới `commands/`; Flume lưu `evidence/<run>/commands.json` và log riêng. Seal thực hiện **sau mọi thay đổi source/README/demo**; manifest dùng verifier hiện có và không hash chính nó/các verifier viết sau.

## Bàn giao và các phạm vi đã nghiệm thu trước

MovieLens là metadata phim nguồn GroupLens; `sim-user-*`, hành vi và runtime phim là mô phỏng. `watchDuration` là số giây mới phát sinh từ lần play gần nhất, không phải tổng tích lũy hay hành vi người thật. Không gộp demo/main thành hai quần thể độc lập.

Spark/K-Means và Dashboard đã được nghiệm thu trước trong [bằng chứng phục hồi](evidence/recovery-20261014/system-acceptance.json); Tuần 3 TV1 giữ nguyên source/output và lựa chọn Dashboard. Dashboard chọn snapshot qua `dashboard/data-source.json`; xem [hướng dẫn Dashboard](dashboard/README.md). Kết quả lịch sử không thay thế kiểm runtime hiện tại.

Tài liệu kỹ thuật trước: [schema phim](docs/movie_schema.md), [schema log](docs/user_log_schema.md), [Flume](docs/flume_pipeline.md), [bàn giao HDFS Tuần 2](docs/week2_tv2_hdfs_handoff.md), [hướng dẫn TV2](docs/week2_tv2_run_guide.md). Các hướng dẫn cluster mới/lần chạy cụ thể trong tài liệu Tuần 1/2 là lịch sử; luồng vận hành TV1 hiện tại dùng context ở trên.
