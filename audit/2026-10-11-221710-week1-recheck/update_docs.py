"""Update current documentation from measured new run reports; preserve history."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser()
p.add_argument('--demo',required=True)
p.add_argument('--main',required=True)
a=p.parse_args()
E='evidence/recheck-20261011-221710'
A='audit/2026-10-11-221710-week1-recheck'
def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))
demo=read(f'evidence/{a.demo}/reconciliation.json')
main=read(f'evidence/{a.main}/reconciliation.json')
sp=read(E+'/spark-main.json')
qa=read(E+'/dataset_quality.json')
assert demo['status']==main['status']==sp['status']==qa['status']=='PASS'
def write(path,body):
    (ROOT/path).write_text(body.strip()+'\n',encoding='utf-8')
def table():
    s='| Lô mới | Run Flume | Events / unique | File / rỗng | Bytes Sink |\n|---|---|---:|---:|---:|\n'
    for label,rid,r in [('Demo',a.demo,demo),('Main',a.main,main)]:
        s+=f"| {label} | `{rid}` | {r['output']['total']:,} / {r['output']['unique']:,} | {r['output_file_summary']['files']} / {r['output_file_summary']['empty_files']} | {r['output_file_summary']['bytes']:,} |\n"
    return s
measured=f"""Ngày kiểm lại: 11/10/2026 (Asia/Saigon). Đây là sản phẩm thực thi mới tại checkout Windows hiện tại, độc lập bằng chứng lịch sử. Movies: 9.742 dòng, SHA256 `{main['movies_sha256']}`. Demo/main Flume E2E và Spark kiểm toàn bộ Sink đều PASS.

{table()}
Missing/unexpected/duplicate/conflicting ID/changed payload, UTF-8/JSON/type/provenance/action/duration, session/sequence và user overlap: đều 0 trên hai lô mới. File rỗng do rolling được giữ và thống kê, không có event; tất cả file không rỗng kết thúc bằng LF. Đối chiếu canonical payload không phụ thuộc thứ tự file/key JSON. Một lần đối chiếu thành công không chứng minh exactly-once hoặc phục hồi lỗi.

Bằng chứng: `evidence/{a.demo}/`, `evidence/{a.main}/`, `{E}/spark-demo.json`, `{E}/spark-main.json`, `{E}/dataset_quality.json`. Audit đầy đủ: `{A}/bao-cao-nghiem-thu-tuan-1-recheck.md`. Manifest mới: `{E}/delivery_manifest.json`.
"""
runtime=f"""Host Windows 10 build 19045 dùng Python 3.12.14 thật tại `C:\\Users\\User\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe`; alias WindowsApps không dùng. Docker Desktop 4.88.1, Client/Engine 29.7.2, Compose v5.4.0, context desktop-linux, Linux containers, 4 CPU / 7,486 GiB Docker memory. Flume 1.11.0 chạy Temurin Java 1.8.0_504; agent thực ghi InitialHeapSize 134.217.728 và MaxHeapSize 536.870.912 byte. Spark/PySpark {sp['runtime']['spark']}, Python {sp['runtime']['python'].split()[0]}, Java {sp['runtime']['java']}, master local[2], driver 2 GiB trong `apache/spark:3.5.1`. Host không cần PySpark/Java; scripts host dùng stdlib. Phiên bản/digest thực đo nằm trong execution logs và image-inspect; tag có thể thay đổi nên giữ image ID/digest khi bàn giao."""
write('README.md',f"""# Phân tích dữ liệu phim và log hành vi người dùng

Apache Flume là thành phần thu thập log; Spark kiểm tra dữ liệu phía sau. Dữ liệu kỹ thuật đã sẵn sàng cho Tuần 2. Nghiệm thu chưa đầy đủ vì chưa có bằng chứng nhóm xác nhận kiến trúc (TV2-06); không tuyên bố hoàn thành 100%.

## Kết quả thực thi hiện tại

{measured}
MovieLens là metadata/rating nguồn GroupLens; log `sim-user-*` là synthetic do generator tạo. `watchDuration` là giây mới phát sinh từ play gần nhất; runtime phim cũng synthetic. Không kết luận về người xem thật.

## Luồng và runtime

```text
MovieLens -> prepare_movies -> movies.csv -----------------------+
                                                               v
Generator -> spooldir Source -> File Channel -> File Roll Sink -> Spark QA
                                                               |
                                             Tuần 2: phân tích -> Dashboard
```

{runtime}

File Channel dùng volume Linux riêng theo Compose project; runner xuất checkpoint/data về `data/runs/<run-id>/channel/` sau khi dừng. Volume được giữ lại. Sink/spool bind vào thư mục run trên host; Storage là filesystem local, không HDFS. Không chạy hai lần trong cùng Compose project/channel.

## Chạy và kiểm lại

Trong PowerShell đặt `$py` là executable Python thật ở trên (hoặc Python >=3.10 có sẵn). Chạy ở thư mục project; Linux dùng `python3`. Không cần pip cho scripts host; Spark chạy từ service container có sẵn dependency.

```powershell
& $py scripts/check_environment.py --report evidence/environment-new.json
& $py scripts/download_dataset.py
& $py scripts/prepare_movies.py --output data/processed/movies-repeat.csv --report evidence/movies-repeat.json
& $py -m unittest discover -s tests -v
& $py scripts/generate_logs.py --mode demo --output data/generated/demo-repeat.jsonl
& $py scripts/run_pipeline.py --input data/generated/demo-repeat.jsonl --timeout 600
```

Downloader tái sử dụng snapshot đã có sau kiểm hash; không ghi đè raw. Mọi output/report phải là đường dẫn mới chưa tồn tại. Nếu cần CA, truyền `--ca-file` với bundle tin cậy; giữ HTTPS verification. Bản tải mới 11/10 đã dùng root CA public từ runtime Node, không tắt TLS.

Chỉ sinh/chạy main sau demo E2E PASS với cùng source/config. Trong checkout này main đã có; chọn tên khác nếu sinh lại. Thay `run-DEMO-MOI` bằng run thực sự mới vừa PASS; bằng chứng lịch sử thiếu hash snapshot không được runner chấp nhận.

```powershell
& $py scripts/generate_logs.py --mode main --events 1000000 --output data/generated/main-repeat.jsonl
& $py scripts/run_pipeline.py --input data/generated/main-repeat.jsonl --timeout 1800 --demo-proof evidence/run-DEMO-MOI/status.json
& $py scripts/validate_pipeline.py --input data/generated/main.jsonl --output-dir data/runs/{a.main}/output --report evidence/main-recheck-new.json
docker compose -p movie-spark-recheck run --rm spark --driver-memory 2g scripts/spark_smoke_test.py --movie-report {E}/dataset_quality.json --run-evidence evidence/{a.main} --report evidence/spark-recheck-new.json
& $py scripts/create_delivery_manifest.py --verify {E}/delivery_manifest.json
```

Lệnh Spark kiểm hash và file list của đúng Sink run PASS, dùng schema từ `src/schemas.py`, action đọc tất cả fields, parse timestamp UTC, kiểm null/type/duplicate/full left anti join/session. Expected count lấy từ manifest/reconciliation đã xác minh, không lấy count quan sát để tạo PASS. `INPUT_PASS`, `.COMPLETED`, count và mẫu join không thay E2E reconciliation.

Runner tạo run/project/output/evidence riêng, publish `.tmp` đóng xong rồi rename cùng spool, lưu argv/cwd/UTC/exit/logs/source hashes/launcher/heap/counters/images/Compose. Dừng và gỡ container/network của chính run; giữ volume/channel/data. Build không tính vào timeout drain. Khoảng 12 GB đĩa dự kiến cho images, generated/spool/Sink, channel/export và SQLite; máy thực đo có 16 GB RAM và trên 60 GB đĩa trống. Không dùng `docker system prune`.

## Bàn giao

`data/raw/` có ZIP/CSV/README license/manifest; `data/processed/` có movies; `data/generated/` có input/manifest. Dữ liệu phân tích là `data/runs/{a.main}/output/`; demo `{a.demo}` chỉ dùng kiểm thử. `logs/<run>/` và `evidence/<run>/` là log/bằng chứng, không phải event input. Không gộp demo/main như hai lịch sử người dùng độc lập.

Data/logs bị Git ignore nhưng thực sự tồn tại local, phải chép cùng source và evidence theo manifest khi bàn giao. Manifest loại spool bản copy, channel, temporary/fixtures, CA public tạm, history không được chọn và chính manifest; scope/exclusions được lưu trong JSON. Bằng chứng FAIL/BLOCKED/PASS cũ và audit cũ giữ nguyên, không dùng thay kết quả hiện tại.

Tài liệu: [dataset](docs/dataset_description.md), [log](docs/log_schema.md), [movie schema](docs/movie_schema.md), [log schema](docs/user_log_schema.md), [Flume](docs/flume_pipeline.md), [kiến trúc](docs/system_architecture.md), [quyết định chờ nhóm](docs/architecture_decision_pending.md), [chất lượng](docs/data_quality_report.md), [bàn giao Tuần 2](docs/week2_handoff.md).
""")
path=ROOT/'docs/dataset_description.md'
body=path.read_text(encoding='utf-8').replace('03/10/2026, 15:51:21 giờ Việt Nam** (08:51:21 UTC)','11/10/2026, 22:20:20 giờ Việt Nam** (15:20:20 UTC)').replace('`evidence/dataset_quality.json`',f'`{E}/dataset_quality.json`').replace('Nếu ID trùng hoặc title thiếu','Nếu ID trùng, title hoặc genres thiếu').replace('Genres rỗng được thống kê, không bịa nhãn mới.','Genres rỗng làm kiểm tra FAIL; không bịa nhãn mới.')
body=body.replace('Đây là tập phát triển', 'README snapshot ghi được sinh ngày 26/09/2018; đây là tập phát triển')
write('docs/dataset_description.md',body)
path=ROOT/'docs/log_schema.md'
body=path.read_text(encoding='utf-8').replace('chưa benchmark main một triệu event.',f'lô main một triệu event đã chạy và được đo tại `evidence/{a.main}/reconciliation.json`.')
write('docs/log_schema.md',body+'\n\n'+measured)
write('docs/movie_schema.md',"""# Schema metadata phim

Nguồn local: `data/processed/movies.csv`, chuẩn hóa riêng từ MovieLens; raw giữ nguyên. Metadata không đi qua Flume. CSV UTF-8 strict, delimiter phẩy, header và quote CSV chuẩn; title có dấu phẩy dùng parser, `escape='"'` với Spark để đọc double quote.

| Field | Spark type | Nullable | Ràng buộc |
|---|---|---|---|
| movieId | LongType | false | Số dương <= 2^63-1, không trùng, join key |
| title | StringType | false | Không rỗng, Unicode NFC, bỏ khoảng trắng ngoài |
| genres | StringType | false | Không rỗng, nhãn phân cách bằng `|`; giữ `(no genres listed)` |
| releaseYear | IntegerType | true | Hậu tố `(YYYY)` cuối title, 1870–2100; không xác định để null |

Schema tái sử dụng: `from src.schemas import MOVIE_SCHEMA`. 9.742 phim/ID unique; 13 null releaseYear hợp lệ, 34 `(no genres listed)`; không bỏ các dòng đó. Nullable=false là hợp đồng, Spark reader có thể vẫn tạo null; job kiểm riêng tất cả null bắt buộc, malformed, duplicate và range. Ví dụ đọc đầy đủ trong `scripts/spark_smoke_test.py`, kết quả QA trong `evidence/recheck-20261011-221710/dataset_quality.json` và Spark reports cùng thư mục.
""")
fields=[('eventId','StringType','ID event; duy nhất trong lô, UUID v5 tái lập'),('userId','StringType','User synthetic, không liên quan ratings.userId'),('sessionId','StringType','Một user/phim/phiên'),('movieId','LongType','Khóa ngoại dương, <=2^63-1, tồn tại trong movies'),('action','StringType','view/play/pause/stop/complete'),('timestamp','StringType','ISO UTC YYYY-MM-DDTHH:MM:SSZ; parse sang TimestampType UTC'),('watchDuration','LongType','Giây mới phát sinh; view/play=0, pause/stop/complete>0'),('sequenceNumber','LongType','Bắt đầu 0, tăng 1 trong phiên, <=2^63-1'),('runId','StringType','ID lô mô phỏng; khác ID run vận chuyển Flume'),('isSynthetic','BooleanType','true'),('simulatedMovieDuration','LongType','3600–10800 giây, cố định theo movieId+seed'),('durationSource','StringType','synthetic')]
rows='\n'.join(f'| {name} | {typ} | false | {meaning} |' for name,typ,meaning in fields)
write('docs/user_log_schema.md',f"""# Schema log hành vi

Sink thật hiện tại: `data/runs/{a.main}/output/` (main) và `data/runs/{a.demo}/output/` (demo). JSON Lines UTF-8/LF, 12 trường; không dùng generated input thay Sink. Tái sử dụng `from src.schemas import USER_LOG_SCHEMA`, không khai báo schema bản sao.

| Field | Spark type | Nullable | Ý nghĩa/ràng buộc |
|---|---|---|---|
{rows}

Các string định danh không rỗng. Nullable=false không tự cưỡng chế reader; kiểm null riêng. Timestamp ban đầu StringType, job dùng to_timestamp, kiểm thất bại parse và khoảng thời gian trên toàn lô. Thứ tự vật lý giữa phiên/file không bảo đảm; sort trong phiên bằng sequenceNumber. Quy tắc transition, thời lượng/completion và chống chồng giờ user trong `docs/log_schema.md`, generator và streaming validator. Spark đọc/quét mọi field, kiểm duplicate/conflict và left anti join toàn log. UUID lặp lại khi cùng seed/tham số; không mô tả duy nhất toàn cục qua nhiều lần nhập.

{measured}
""")
path=ROOT/'docs/system_architecture.md'
body=path.read_text(encoding='utf-8').replace('đệm bền vững trên đĩa chống mất mát dữ liệu khi có sự cố','đệm bền vững trên đĩa; chưa kiểm thử phục hồi sự cố').replace('Mount thư mục `./data` và `./logs`.','Runner bind spool/output/log riêng theo run; File Channel dùng named volume Linux riêng theo Compose project, được xuất về host sau stop.').replace('OpenJDK 17 + Python 3.10/3.11 + PySpark 3.5.1','OpenJDK 11.0.22 + Python 3.8.10 + PySpark 3.5.1').replace('`/opt/spark/work-dir` hoặc `/project`','`/project`').replace('Spark dùng Java 17','Spark dùng Java 11')
write('docs/system_architecture.md',body+'\n\nNgày kiểm thực tế 11/10/2026: Flume và Spark QA đã chạy; phân tích/dashboard là Tuần 2. Chưa có bằng chứng nhóm phê duyệt kiến trúc; xem `docs/architecture_decision_pending.md`.\n')
path=ROOT/'docs/flume_pipeline.md'
body=path.read_text(encoding='utf-8').replace('data/runs/<run-id>/channel/checkpoint','volume Linux riêng; export data/runs/<run-id>/channel/checkpoint').replace('data/runs/<run-id>/channel/data','volume Linux riêng; export data/runs/<run-id>/channel/data').replace('Log vận hành của agent nếu launcher ghi file','Log INFO vận hành của agent qua log4j2.xml').replace('File rỗng do roll có thể xuất hiện và được validator bỏ qua về số event.','File rỗng do roll được đo bytes/hash/empty và giữ nguyên; không chứa event.').replace('Java base image là Temurin chính thức; chưa có digest bản pull trong lần bàn giao vì Docker chưa sẵn sàng. Cấu hình chỉ được đối chiếu tài liệu, chưa xác nhận qua JVM thật.','Java base image là Temurin chính thức. Image ID/build/launcher đúng Flume 1.11.0 được lưu từng run. `flume-ng` đặt default JAVA_OPTS trước source flume-env.sh; vì vậy cấu hình heap trong config/flume-env.sh. Agent ghi PrintFlagsFinal và ps args, đo MaxHeapSize 536.870.912 byte. log4j2.xml ghi INFO ra console và /logs/flume.log; HTTP metrics port 41414 không publish ra host.').replace('Đã tra cứu ngày 03/10/2026.','Đã kiểm lại ngày 11/10/2026; launcher snapshot lấy từ image thực tế.')
write('docs/flume_pipeline.md',body+'\n\n'+measured)
write('docs/week1_report.md',f'# Báo cáo Tuần 1 cập nhật sau thực thi\n\n{measured}\n{runtime}\n\n18 unit tests host và 9 kiểm thử Spark fixture đạt. Fixture không phải Sink evidence. Toàn bộ source/config/tests/docs cuối được đọc lại, dữ liệu toàn lô được đối chiếu độc lập, manifest kiểm bytes/SHA256. Xác nhận kiến trúc nhóm vẫn thiếu: TV2-06 ĐẠT MỘT PHẦN. Báo cáo này ghi kết quả tự động kiểm lại, không xác nhận thay đóng góp hoặc phê duyệt của cá nhân.\n')
write('docs/week1_member2_report.md',f"""# Báo cáo Tuần 1 — kiểm chứng downstream

{measured}
{runtime}

Job `scripts/spark_smoke_test.py` áp schema chính, cache và materialize canonical payload tất cả fields; count movies/log so với snapshot/run, null bắt buộc, malformed CSV/JSON, timestamp parse/range UTC, action/duration/provenance, metadata uniqueness, eventId duplicate/conflict và full left anti join. Kiểm sequence/time/segment duration/session identity toàn log; streaming validator bổ sung full transition/completion/user overlap. Hai lớp QA độc lập đọc dữ liệu thật; không drop/filter lỗi để PASS.

SparkSession local[2] và spark.range(5).count()=5 đã chạy; stdout/stderr/argv/cwd/UTC/exit 0 trong audit execution. 7 fixture nghiệp vụ và 2 fixture parser phát hiện lỗi có chủ đích, tách khỏi output Flume. Timestamp string chuyển sang TimestampType UTC; releaseYear nullable=true (13) được chấp nhận. Ở Tuần 2 kiểm xung đột trước dedup, join theo Long movieId, phân tích và dashboard; chưa triển khai các sản phẩm Tuần 2.
""")
write('docs/data_quality_report.md',f"""# Chất lượng dữ liệu sau lượt kiểm lại

{measured}
Movies được đọc bằng CSV parser UTF-8 strict, header/field count/positive signed long ID/title/genres/year/NFC kiểm toàn bộ. 9.742 ID phân biệt, 0 lỗi; 13 năm null và 34 nhãn `(no genres listed)` giữ nguyên; 11 dòng được chuẩn hóa trong file riêng, raw không sửa. Ratings 100.836, tags 3.683, links 9.742 đo bằng CSV parser, chưa phân tích ratings/tags.

Spark báo cáo từng loại lỗi và ví dụ eventId/_file khi lỗi; streaming validator có path:dòng. Không có ví dụ lỗi trong lô PASS vì mọi counter bằng 0, không tạo ví dụ giả. Trên fixture có lỗi, assertions yêu cầu phát hiện orphan ngoài 5 dòng đầu, parse timestamp/null, metadata trùng, eventId xung đột, duration âm, malformed CSV/JSON/type; các fixture luôn được ghi rõ không phải Flume.

Watch duration main: {main['output']['watch_seconds']:,} giây; {main['output']['sessions']:,} phiên, {main['output']['users']:,} user, {main['output']['movies']:,} phim. UTC từ {main['output']['timestamp_min']} đến {main['output']['timestamp_max']}. Không có lỗi phiên, sequence, completion hoặc overlap trên full reconciliation độc lập. File rolling rỗng không là event lỗi; tất cả file có bytes được parse và kiểm newline.

Tuần 2: kiểm eventId conflict trước dedup (không coi dropDuplicates bảo đảm exactly-once), xử lý year null thành nhóm unknown, split/explode genres, chuyển UTC sang Asia/Ho_Chi_Minh để thống kê giờ. Các thống kê phản ánh mô phỏng, không phải sở thích người xem thật.
""")
write('docs/week2_handoff.md',f"""# Bàn giao dữ liệu cho Tuần 2

{measured}
Metadata: `data/processed/movies.csv`. Lô phân tích: `data/runs/{a.main}/output/`; demo không gộp vào main. Dùng MOVIE_SCHEMA/USER_LOG_SCHEMA từ `src/schemas.py`: movieId hai bên LongType, sequenceNumber LongType, timestamp StringType chuyển TimestampType UTC, duration LongType đơn vị giây mới phát sinh. ReleaseYear IntegerType nullable; các field còn lại không null theo hợp đồng và được kiểm riêng.

```python
from src.schemas import MOVIE_SCHEMA, USER_LOG_SCHEMA
from pyspark.sql import functions as F
spark.conf.set('spark.sql.session.timeZone', 'UTC')
movies = spark.read.option('header', True).option('escape', '"').schema(MOVIE_SCHEMA).csv('data/processed/movies.csv')
events = spark.read.schema(USER_LOG_SCHEMA).json('data/runs/{a.main}/output/*.jsonl')
events = events.withColumn('eventTime', F.to_timestamp('timestamp'))
# Kiểm null/orphan và eventId conflict trước dedup trong job downstream.
joined = events.join(movies, 'movieId', 'left')
```

Job QA đầy đủ `scripts/spark_smoke_test.py` đã đọc chính Sink này bằng Spark thật; mẫu trên không thay QA. Bàn giao raw/license, processed, generated manifests, Sink/log/evidence và source theo manifest; data Git ignore vẫn có local. SHA256 từng file Sink và bytes trong reconciliation/manifest. Spool copy, channel/checkpoint không dùng làm dataset cho Spark.

| Phân tích Tuần 2 | Định nghĩa |
|---|---|
| Lượt xem chi tiết | Đếm action=view |
| Phiên bắt đầu xem | Count distinct (runId,sessionId) có play; không đếm resume là lượt mới |
| Thời gian xem | SUM(watchDuration), không cộng runtime |
| Hoàn thành | Phiên complete / phiên có play, mẫu số 0 -> null |
| Phim phổ biến | Nhóm movieId rồi join title |
| Thể loại | Split genres theo `|`, explode; nhiều thể loại có thể làm tổng tăng, ghi rõ cách tính |
| Giờ hoạt động | UTC -> Asia/Ho_Chi_Minh trước hour |

Timestamp/min/max/actions/users/movies/sessions/watch seconds và thống kê giờ bắt đầu trong manifest input và reconciliation. User/phim có trọng số; không suy chúng đại diện người dùng thật. HDFS, dashboard, job phân tích chuyên sâu và phục hồi lỗi chưa thực hiện, không thuộc nghiệm thu Tuần 1. Nhóm vẫn cần xác nhận kiến trúc theo `docs/architecture_decision_pending.md`.
""")
write('docs/presentation_script.md',f"""# Bài nói về kết quả kiểm lại 11/10/2026

Project dùng MovieLens latest-small của GroupLens: parser đếm 9.742 phim, metadata gồm movieId/title/genres, thêm releaseYear từ hậu tố năm; 13 phim để null vì không xác định được. ZIP, CSV gốc và giấy phép được giữ nguyên, bản chuẩn hóa riêng có SHA256.

Log là synthetic, không phải hành vi thu từ người dùng thật. Bộ main có một triệu sự kiện, {main['output']['sessions']:,} phiên, {main['output']['users']:,} user và {main['output']['movies']:,} phim. watchDuration ghi giây mới phát sinh từ play; xem 120 giây, pause, xem 180 giây thì tổng là 300 giây. Runtime phim cũng được ghi rõ mô phỏng.

Flume 1.11.0 chạy trên Docker: spooldir Source nhận file đã đóng, File Channel đệm trên volume Linux riêng, File Roll Sink ghi JSONL ra filesystem local. Demo {a.demo} đã đạt trước khi chạy main {a.main}. Đối chiếu toàn bộ eventId và canonical payload cho main thấy đủ một triệu sự kiện, không mất/thừa/trùng/xung đột/đổi payload. JVM agent ghi heap tối đa 512 MiB, log thể hiện đầy đủ thành phần/counter.

Spark/PySpark 3.5.1 đã tạo SparkSession và action thật, đọc metadata cùng chính Sink main, kiểm mọi field, timestamp UTC, null/duplicate và full orphan join. Các bộ kiểm đều đạt; file rolling rỗng được đo riêng. Không suy exactly-once hoặc phục hồi lỗi từ lần chạy này.

Dữ liệu đủ để Tuần 2 phân tích lượt xem, thời gian xem, phim/thể loại và giờ hoạt động; dashboard chưa triển khai. Về nghiệm thu nhóm, vẫn thiếu xác nhận kiến trúc TV2-06 nên chưa tuyên bố hoàn thành đầy đủ Tuần 1. Tất cả kết luận liên kết tới audit và bằng chứng mới; lịch sử FAIL/BLOCKED được giữ nguyên.
""")
print('Updated current docs from actual PASS artifacts:',a.demo,a.main)
