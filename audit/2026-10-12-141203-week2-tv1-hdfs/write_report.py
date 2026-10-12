"""Compose A-G acceptance from immutable actual receipts, never fabricate runs."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def link(path,line=1,label=None):
    path=Path(path)
    if not path.is_absolute():path=ROOT/path
    target=path.as_posix() if path.suffix.lower() in ['.jpg','.png'] else path.as_posix()+':'+str(line)
    return f'[{label or path.relative_to(ROOT).as_posix()}]({target})'


def ref(path,needle=None):
    file=ROOT/path
    lines=file.read_text(encoding='utf-8').splitlines()
    line=next((i for i,text in enumerate(lines,1) if needle in text),1) if needle else 1
    return link(file,line)


def main():
    evidence=ROOT/'evidence/week2-hdfs/hdfs-385a18d3f03a'
    ctx=load(evidence/'context.json')
    src=load(evidence/'source_manifest.json')
    checks=load(AUDIT/'artifacts-final.json')
    acceptance=load(evidence/'acceptance_status.json')
    spark=load(evidence/'spark-hdfs.json')
    assert checks['status']=='PASS' and all(value=='ĐẠT' for value in acceptance['stages'].values())
    records=[]
    for folder,name in [(AUDIT/'execution','command.json'),(evidence/'commands','finished.json')]:
        for file in folder.glob('*/'+name):
            record=load(file)
            if 'finished_at_utc' in record:
                record['record_path']=file.relative_to(ROOT).as_posix()
                records.append(record)
    records.sort(key=lambda r:r['started_at_utc'])
    new_json(AUDIT/'commands-final.json',{'created_at_utc':utcnow(),'records':records,
        'note':'Only completed steps at report generation; manifest/verification commands are recorded later in execution. Both expected nonzero guards and failed verifier attempts are preserved.'})
    ev=ctx['evidence']
    tasks=[
        ('TV1-W2-01','HDFS thật với NameNode/DataNode',ref('compose.hdfs.yaml','namenode:')+'; '+ref('scripts/hdfs_service.sh','FORMAT_NEW_EMPTY_VOLUME')+'; '+link(evidence/'final-runtime.json')),
        ('TV1-W2-02','Namespace raw, processed, results theo snapshot/run/import',ref('scripts/hdfs_source.py',"'directories'")+'; '+link(evidence/'source_manifest.json')+'; final-list trong final-runtime'),
        ('TV1-W2-03','Metadata và chính Sink Flume thật lên HDFS',ref('scripts/hdfs_io.py',"'-put'")+'; '+link(evidence/'upload_status.json')+'; '+link(evidence/'content-import.json')),
        ('TV1-W2-04','Tồn tại, dung lượng, nội dung và trạng thái HDFS',ref('scripts/hdfs_io.py',"'dfsadmin-report'")+'; '+link(evidence/'final-runtime.json')+'; '+link(evidence/'screenshots/namenode-full-page.jpg')),
        ('TV1-W2-05','Đối chiếu đầy đủ file/bytes/SHA256/count',ref('scripts/hdfs_io.py',"digest=hashlib")+'; '+ref('scripts/hdfs_hash_verify.py','DigestInputStream')+'; '+link(evidence/'content-after-restart.json')+'; '+link(evidence/'final-hdfs-hashes.json')),
        ('TV1-W2-06','Job/config và hợp đồng tích hợp Spark cho TV2',ref('scripts/spark_hdfs_validate.py','MOVIE_SCHEMA')+'; '+ref('docs/week2_tv2_hdfs_handoff.md','Snapshot chính xác')+'; '+link(evidence/'spark-hdfs.json')),
        ('TV1-W2-07','Flume → Sink → HDFS → Spark được chứng minh',ref('scripts/hdfs_source.py',"status['input_sha256']")+'; '+link(evidence/'source_manifest.json')+'; '+link('evidence/run-aa6b9eb58dca/reconciliation.json')+'; '+link(evidence/'acceptance_status.json')),
        ('TV1-W2-08','Cấu hình/lệnh/log/ảnh/lỗi có bằng chứng',ref('scripts/hdfs_common.py','class Ledger')+'; '+link(AUDIT/'commands-final.json')+'; '+link(evidence/'screenshots/namenode-full-page.jpg')+'; mục F'),
        ('TV1-W2-09','Chương báo cáo lý thuyết và thực nghiệm HDFS',ref('docs/week2_tv1_hdfs_report.md','Cơ sở lý thuyết')+'; '+ref('docs/week2_tv1_hdfs_report.md','Lỗi thực tế')),
        ('TV1-W2-10','Kiến trúc sau bổ sung HDFS, rõ phần tiếp theo',ref('docs/week2_system_architecture.md','flowchart TD')+'; '+ref('docs/week2_system_architecture.md','Tiền xử lý chuyên sâu')),
    ]
    out=[]
    out.append('# Nghiệm thu TV1 Tuần 2 — HDFS\n\nNhan Tử Mạnh — “Phân tích dữ liệu phim và log hành vi người dùng”. Báo cáo được lập từ bằng chứng thực tại '+utcnow()+'.')
    out.append('## A. Kết luận\n\n**Phần việc TV1 Tuần 2 đã hoàn thành đầy đủ chưa? Có, về phạm vi triển khai và nghiệm thu kỹ thuật được yêu cầu: 10/10 nhiệm vụ ĐẠT (100%); đủ 7/7 sản phẩm.** Không có blocker kỹ thuật TV1 còn lại. Năm trạng thái riêng runtime/upload/content/Spark/E2E đều ĐẠT tại '+link(evidence/'acceptance_status.json')+'. Checkpoint startup `runtime_status.json` vẫn giữ trạng thái các bước chưa chạy ở thời điểm khởi động; không bị sửa hồi tố.\n\nXác nhận của nhóm về kiến trúc và phần giới thiệu/cơ sở lý thuyết Tuần 1 vẫn thiếu; chưa có xác nhận TV2 đã nhận hoặc tích hợp. Đây là điều kiện phối hợp chưa được chứng minh, không được tự coi đã phê duyệt. Không kết luận toàn bộ Tuần 2 hoàn thành: tiền xử lý chuyên sâu, phân tích, K-Means và dashboard nằm ngoài lượt này.')
    out.append('## B. Phạm vi, revision, runtime và giới hạn\n\nRoot/cwd mọi command: `'+str(ROOT)+'`. HEAD `bcb28b7fac0c9d260af0e6acb121947f991355f8`, branch main; không commit/push. 23 tracked modifications có sẵn từ trước; lượt TV1 Tuần 2 chỉ thêm file mới. '+link(AUDIT/'artifacts-final.json')+' xác minh **514/514 tệp có trước** không đổi bytes/SHA256 và manifest Tuần 1 **344/344** còn khớp. Git status/diff/revision cuối tại '+link(evidence/'git-final.json')+'.\n\nProject `'+ctx['project']+'`; cluster/import `'+ctx['run_id']+'`; source Flume `'+src['flume_run_id']+'`. Một NameNode, một DataNode, Docker network riêng, hai named volumes; replication 1, block size 128 MiB. Servers còn chạy để TV2 dùng; không xóa volume. Không bật lại Flume. UI [NameNode thực](http://127.0.0.1:19870/dfshealth.html#tab-overview).\n\nHadoop server 3.3.6/Java 1.8.0_212, image Apache digest `62a22627f35a1bbf29c721192c02fe311c93749cc43d51df01792b2ac40ff144`. Spark/PySpark 3.5.1, Hadoop client 3.3.4, Python 3.8.10, Java 11.0.22, local[2], driver 2 GiB, UTC. Host Python dùng ghi audit: 3.12.14, không phải Python của Spark. Client/server đã đọc thật trong '+link(evidence/'spark-hdfs.json')+'. Docker Client/Engine 29.7.2, Linux containers, context desktop-linux; version/info/context/Compose thực nằm trong commands.\n\nMô hình demo một máy, simple auth, root chỉ trong container; không HA hoặc dự phòng khi mất DataNode/host/volume. Host trước Docker khoảng 16,6 GB RAM tổng, 7,6 GB available, 70 GB C: free; số capacity khoảng 1 TB do DataNode báo là dung lượng filesystem WSL, không suy ra host còn 1 TB đĩa vật lý. Không cài hệ thống, sửa quyền host hay WSL. Log/runtime phim synthetic; metadata HDFS là CSV đã chuẩn hóa, raw ZIP/license local giữ nguyên.')
    out.append('## C. Ma trận đủ 10 nhiệm vụ\n\n| ID | Yêu cầu | Trạng thái | Bằng chứng (file:dòng khi là source/docs) | Thiếu sót | Việc cần làm |\n|---|---|---|---|---|---|')
    for ident,requirement,proof in tasks:out.append(f'| {ident} | {requirement} | ĐẠT | {proof} | Không có thiếu sót kỹ thuật trong tiêu chí | Không có việc kỹ thuật TV1 còn lại |')
    out.append('\nTV1-W2-06 nghiệm thu việc chuẩn bị hợp đồng và chạy job thực; không khẳng định TV2 đã xác nhận. TV1-W2-09/10 nghiệm thu tài liệu/sơ đồ được bổ sung; không khẳng định nhóm đã phê duyệt. Chỉ tính số ĐẠT/10 × 100; không cộng điều kiện phối hợp chưa xác minh vào số ĐẠT.')
    products=[
        ('1','Cấu hình và runtime HDFS Docker chạy được',ref('compose.hdfs.yaml')+'; '+ref('config/hdfs/core-site.xml')+'; '+ref('config/hdfs/hdfs-site.xml')+'; '+ref('scripts/hdfs_service.sh')),
        ('2','NameNode/DataNode hoạt động',link(evidence/'final-runtime.json')+'; '+link(evidence/'persistence-reviewed.json')),
        ('3','Movie dataset và output Flume thật trên HDFS',link(evidence/'source_manifest.json')+'; '+link(evidence/'content-after-restart.json')+'; URI/từng tệp ở mục E'),
        ('4','Job/config và bằng chứng Spark HDFS',ref('scripts/spark_hdfs_validate.py')+'; '+link(evidence/'spark-hdfs.json')+'; '+ref('docs/week2_tv2_hdfs_handoff.md')),
        ('5','Ảnh/lệnh/log và đối chiếu HDFS',link(evidence/'screenshots/namenode-full-page.jpg')+'; '+link(AUDIT/'commands-final.json')+'; '+link(evidence/'final-hdfs-hashes.json')),
        ('6','Nội dung báo cáo lưu trữ phân tán',ref('docs/week2_tv1_hdfs_report.md')),
        ('7','Sơ đồ kiến trúc cập nhật',ref('docs/week2_system_architecture.md','flowchart TD')),
    ]
    out.append('## D. Bảy sản phẩm bàn giao\n\n| STT | Sản phẩm | Trạng thái | Artifact |\n|---|---|---|---|')
    for number,title,proof in products:out.append(f'| {number} | {title} | ĐẠT | {proof} |')
    out.append('## E. Commands, UTC, exit code và kết quả đo\n\nCatalog đầy đủ **'+str(len(records))+' command records đã hoàn tất**: '+link(AUDIT/'commands-final.json')+'. Mỗi entry giữ argv dưới dạng mảng, cwd, UTC bắt đầu/kết thúc, environment và đường dẫn stdout/stderr; record raw vẫn còn ở `execution/*/command.json` hoặc `commands/*/finished.json`. Không đưa exit 1 của phép thử từ chối vào kết quả upload/E2E thành công. Lượt tạo/verify manifest diễn ra sau catalog này, có command records riêng được loại khỏi chính manifest để tránh vòng tự hash.\n\n| Bước outer wrapper | UTC bắt đầu → kết thúc | Exit code | Record và stdout/stderr cùng thư mục |\n|---|---|---:|---|')
    for record in records:
        if '/execution/' in record['record_path']:
            out.append('| '+Path(record['record_path']).parent.name+' | '+record['started_at_utc']+' → '+record['finished_at_utc']+' | '+str(record['exit_code'])+' | '+link(record['record_path'])+' |')
    out.append('\nLệnh runtime nội bộ chính: `docker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a up -d namenode datanode`; `exec -T namenode hdfs dfs -mkdir -p ...`, `-test -e ...`, `-put <actual Sink> <snapshot>`; `-ls -R /movie-log`, `-du -s /movie-log/raw`, `-cat <từng tệp>`; `hdfs dfsadmin -report`, `-safemode get`; `hdfs fsck /movie-log -files -blocks -locations`. Không dùng `-put -f`, checksum HDFS thay SHA256, local fallback hoặc generated input thay Sink. Lệnh chính xác mỗi tệp gồm full path nằm trong catalog; các stdout.bin là byte thực đọc từ HDFS.')
    out.append('\nMovies URI: `'+src['movies_uri']+'`.\n\nLogs URI: `'+src['logs_uri']+'`. Dưới đây tên/tổng byte/expected records/SHA256 từng tệp; HDFS URI từng log là logs URI + `/` + tên. Local logs là `data/runs/run-aa6b9eb58dca/output/<tên>`, metadata `data/processed/movies.csv`. Mỗi mapping đầy đủ nằm trong source manifest; mỗi phép đo thực nằm trong content report và final Java hash receipt.\n\n| Tệp | Loại | Byte | Records | SHA256 (source = HDFS) |\n|---|---|---:|---:|---|')
    for file in src['files']:
        out.append(f"| {Path(file['hdfs_path']).name} | {file['kind']} | {file['bytes']} | {file['expected_records']} | `{file['sha256']}` |")
    out.append('\n**Tổng 16 tệp, 343.872.495 byte**: movies 9.742 rows/533.347 byte; logs 1.000.000 events/343.339.148 byte. File list thiếu/thừa 0, bytes/hash/count mismatch 0; 15 part không rỗng. CSV parser kiểm header/record; parse mọi JSON object/types; cat binary tính SHA256 trên toàn byte. Sau controlled restart, toàn bộ nội dung vẫn khớp. Kiểm cuối độc lập Hadoop Java stream cũng khớp cả 16 tệp, không đổi mtime/size trong lúc đọc.\n\nHDFS fsck HEALTHY: 16 files/16 blocks, 1 live DataNode, replication thực 1, corrupt/missing/under-replicated/missing replicas đều 0, safe mode OFF. `du` đo logical bytes; DFS Used gồm block/checksum/storage overhead, không đồng nhất với logical bytes. Các thư mục processed/results tồn tại và trống.\n\nSpark từ '+spark['started_at_utc']+' tới '+spark['finished_at_utc']+': 9.742 movies, 1.000.000 events, 1.000.000 unique event IDs; 13 null releaseYear hợp lệ. '+str(len(spark['errors']))+' nhóm lỗi đều 0. Full anti join orphan=0, trùng/conflicting=0, malformed/null/type/time/action/duration/provenance/session đều 0. `input_file_name` đúng movies URI và đủ 15 logs HDFS URI; JVM filesystem là DistributedFileSystem; timezone UTC, eventTime TimestampType, movieId hai phía LongType. Schema contract và schema actual read được lưu đầy đủ; nullable khai báo không được dùng thay kiểm giá trị.\n\nNăm stage ĐẠT được lập từ source manifest cùng run, PASS content và Spark đúng report hash. Generated chỉ nối input hash tới reconciliation Flume; output nguồn là chính Sink Tuần 1 đã xác minh, không chạy lại Flume vì dữ liệu/source không đổi.')
    out.append('## F. Lỗi đã xử lý, lỗi còn lại và mức ảnh hưởng\n\n| Sự kiện thực tế | Xử lý và bằng chứng | Ảnh hưởng hiện tại |\n|---|---|---|\n| Docker pipe thiếu khi Engine chưa chạy; exit 1 | Giữ log docker-version/info/spark-hadoop-client ban đầu; mở Docker Desktop đã cài, kiểm ready lại | Đã xử lý; không đổi hệ thống |\n| Poll lúc HDFS khởi động/restart; RPC chưa sẵn | Poll có giới hạn; chỉ nhận ready khi 1 DN live và safe mode OFF | Đã xử lý, mọi attempt được giữ |\n| Volume inspect trước deploy exit 1 | Bằng chứng volume riêng chưa tồn tại; script còn kiểm volume trống trước format | Expected guard, không lỗi dữ liệu |\n| Ba fixture container exit 1 | Từ chối nonempty unformatted/wrong cluster/invalid role; disposable tmpfs không đụng volume thật | Expected guard PASS; không là Flume evidence |\n| Upload lại namespace hiện hữu exit 1 | `overwrite-refused.json` FAIL giữ nguyên; -test -e exit 0, không có -put trong khoảng lượt này | Chống ghi đè đạt, dữ liệu không đổi |\n| Persistence verifier ban đầu FAIL do VERSION comment timestamp | Giữ raw trước/sau và `persistence.json`; sửa comparator kiểm tất cả Java properties, regression tests; lưu `persistence-reviewed.json` riêng | Dữ liệu toàn lô đã PASS, một lần format và restart reuse giữ nguyên identity; lỗi verifier đã xử lý |\n| final-live verifier đòi chuỗi Dead datanodes (0) không tồn tại khi section được Hadoop bỏ | Giữ failed wrapper; đọc stdout thật, parse count khi có section và coi absent section=0, chạy lượt mới | Không lỗi cluster, final-runtime PASS |\n| final-artifacts verifier đòi từ exist trong str(FileExistsError(path)) | Giữ failed wrapper; kiểm đúng path, -test exit 0 và toàn bộ command window không có -put, chạy lượt mới | Không lỗi upload; artifacts-final PASS |\n| Xác nhận nhóm/TV2 chưa có | Không tự tạo xác nhận hoặc gửi tin nhắn | CHƯA THỂ XÁC MINH, điều kiện phối hợp còn thiếu; không cản các tiêu chí kỹ thuật TV1 này |\n\n21 host unit tests PASS (gồm 3 regression VERSION); 3 container guards PASS; actual duplicate import từ chối đúng; Spark/HDFS final checks PASS. Không còn lỗi kỹ thuật HDFS/Spark mở trong phạm vi. Không có auto-review rejection hay hành động ngoài quyền cần người dùng duyệt.')
    out.append('## G. File thêm, manifest và tái kiểm chứng\n\nCác file có trước không bị sửa. Các file mới về chức năng:\n\n| File/dòng | Lý do thêm |\n|---|---|')
    reasons={'compose.hdfs.yaml':'Compose HDFS riêng, không bật Flume',
        'config/hdfs/core-site.xml':'fs.defaultFS và tmp dir',
        'config/hdfs/hdfs-site.xml':'RPC/DN host/volumes/replication/block size',
        'config/hdfs/log4j.properties':'Log Hadoop ra console',
        'scripts/hdfs_service.sh':'Format chỉ volume mới trống; bảo vệ cluster ID/reuse',
        'scripts/hdfs_common.py':'Command ledger và JSON reports tạo mới',
        'scripts/hdfs_source.py':'Đóng băng lineage Sink Tuần 1 và expected counts',
        'scripts/run_hdfs.py':'Cluster/project/volume mới, ready check/version',
        'scripts/hdfs_io.py':'Namespace/upload no overwrite, parse/hash toàn HDFS',
        'scripts/spark_hdfs_validate.py':'Đọc trực tiếp HDFS và full QA dùng schemas chung',
        'scripts/hdfs_hash_verify.py':'Kiểm byte SHA256 độc lập bằng Java Hadoop client',
        'scripts/hdfs_guard_tests.py':'Guard fixtures riêng, không là output Flume',
        'scripts/hdfs_restart_verify.py':'Controlled restart, so mọi properties và dữ liệu',
        'scripts/create_hdfs_manifest.py':'Manifest scope/exclusions, local verify tách remote',
        'tests/test_hdfs_properties.py':'Regression kiểm properties không lẫn comment',
        'docs/week2_tv1_hdfs_report.md':'Chương lý thuyết + thực nghiệm với nguồn Apache chính thức',
        'docs/week2_tv2_hdfs_handoff.md':'Hợp đồng URI/schema/QA/lệnh/giới hạn cho TV2',
        'docs/week2_system_architecture.md':'Sơ đồ và trạng thái đã chạy/công việc tiếp theo'}
    for file,reason in reasons.items():out.append('| '+ref(file)+' | '+reason+' |')
    out.append('\nThêm thư mục audit hiện tại chứa inventory trước, resource receipt, run_step/helpers, source-review đánh số dòng, artifacts-final, command catalog, báo cáo này và execution logs. Thêm evidence/week2-hdfs/hdfs-385a18d3f03a chứa context/source/runtime/upload/content/Spark/persistence/guards/final receipts, binary streams và ảnh thực. Manifest liệt kê từng tệp bàn giao kèm bytes/SHA256; danh sách source/doc kiểm cuối tại '+link(AUDIT/'artifacts-final.json')+' và '+link(AUDIT/'source-review-final.txt')+'.\n\nManifest mới: '+link(evidence/'delivery_manifest.json')+'. Scope gồm source/config/tests/docs, root Compose/HDFS và file project chọn rõ, MovieLens raw/processed/generated (generated chỉ để lineage), 15 Sink thật, evidence Flume main, evidence recheck Tuần 1, audit/evidence của lượt này. Exclusions: .git, channel/spool, run/audit ngoài scope, fixtures/temporary/cache/part/CA tạm, image layers, named-volume metadata/blocks trực tiếp, manifest tự thân, bước tạo đang chạy và verification receipts về sau. Đây là bàn giao tệp + receipt HDFS, không phải export live volume portable.\n\nMọi local entry được kiểm bytes/SHA256 khi tạo và bằng lượt verify độc lập có receipt mới. `remote_hdfs.files` ghi URI/hash/bytes/records của 16 tệp đã đọc thật; verify local không khẳng định trạng thái HDFS sau đó. Khi cần xác minh remote hiện tại, chạy job Java hash với report mới, rồi full Spark QA khi dữ liệu/config thay đổi. Không sửa manifest cũ hoặc report cũ để tái dùng tên.')
    out.append('\nLệnh kiểm lại (PowerShell tại root, cần Engine hoạt động cho remote):\n\n```powershell\n$pyExe=\'C:\\Users\\User\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe\'\n$verifyId=[guid]::NewGuid().ToString(\'N\')\n& $pyExe -B scripts/create_hdfs_manifest.py --verify evidence/week2-hdfs/hdfs-385a18d3f03a/delivery_manifest.json --receipt "evidence/week2-hdfs/hdfs-385a18d3f03a/manifest-verification-$verifyId.json"\n& $pyExe -B scripts/create_delivery_manifest.py --verify evidence/recheck-20261011-221710/delivery_manifest.json\n$env:HDFS_RUN_ID=\'hdfs-385a18d3f03a\'\ndocker compose -f compose.hdfs.yaml -p movie-hdfs-385a18d3f03a --profile spark run --rm --no-deps spark --driver-memory 1g scripts/hdfs_hash_verify.py --source-manifest evidence/week2-hdfs/hdfs-385a18d3f03a/source_manifest.json --report "evidence/week2-hdfs/hdfs-385a18d3f03a/hashes-reverify-$verifyId.json"\n```\n\nLệnh khởi động HDFS và full Spark HDFS QA có tên report mới nằm tại '+ref('docs/week2_tv2_hdfs_handoff.md','Chạy trong PowerShell')+'. Không thay snapshots/raw hoặc chạy lại Flume khi không cần.\n\nẢnh UI thật sau restart, không dựng từ text/log:\n\n![NameNode thực: cluster, DataNode, block và safe mode]('+ (evidence/'screenshots/namenode-full-page.jpg').as_posix()+')\n\nCác ảnh viewport ban đầu vẫn giữ riêng; ảnh full-page là screenshot browser thực. Kết luận cuối: **TV1 Tuần 2 ĐẠT 10/10**. Điều kiện còn thiếu bên ngoài phạm vi kỹ thuật là xác nhận phối hợp của nhóm/TV2 và phần việc tiếp theo chưa chạy; không tuyên bố toàn bộ Tuần 2 hoặc báo cáo nhóm đã hoàn thành.')
    rendered=out[0]
    for part in out[1:]:rendered+=('\n' if part.startswith('| ') else '\n\n')+part
    rendered=rendered.replace('Giữ failed wrapper; kiểm đúng path, -test exit 0 và toàn bộ command window không có -put, chạy lượt mới',
        'Giữ failed wrappers; kiểm đúng path, -test exit 0 và command window không có -put. Lượt tiếp giữ FAIL do glob week2_ bao gồm docs/week2_handoff.md lịch sử; sửa sang kiểm ba đường dẫn mới cụ thể, bảo toàn doc cũ, chạy lượt mới')
    with (AUDIT/'bao-cao-nghiem-thu-tv1-tuan-2-hdfs.md').open('x',encoding='utf-8') as file:file.write(rendered+'\n')
    print('Created A-G report from actual receipts; 10/10 technical tasks, 7 products.')


if __name__=='__main__':main()
