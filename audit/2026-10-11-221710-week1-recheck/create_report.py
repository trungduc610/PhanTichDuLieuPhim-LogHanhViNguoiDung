"""Author the final Vietnamese acceptance report from immutable measured evidence."""
import argparse
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
E='evidence/recheck-20261011-221710'
A=AUDIT.relative_to(ROOT).as_posix()
I=A+'/final-inspection'
p=argparse.ArgumentParser()
p.add_argument('--demo',required=True)
p.add_argument('--main',required=True)
a=p.parse_args()
def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))
def line(path,needle):
    lines=(ROOT/path).read_text(encoding='utf-8').splitlines()
    return next(i for i,text in enumerate(lines,1) if needle in text)
def link(path,at=1,label=None):
    if (ROOT/path).is_dir() or Path(path).suffix=='.zip':
        return f'[{label or path}](<{(ROOT/path).as_posix()}>)'
    return f'[{label or path+":"+str(at)}](<{(ROOT/path).as_posix()}:{at}>)'
def ref(path,needle):
    return link(path,line(path,needle))
def step(label):
    if label=='inspection-final':
        label='inspection-final-v2'
    files=sorted(path for path in (AUDIT/'execution').glob('*/command.json') if re.fullmatch(re.escape(label)+r'-[0-9a-f]{8}',path.parent.name))
    if len(files)!=1:
        raise ValueError((label,files))
    return link(files[0].relative_to(ROOT).as_posix(),2,label+' argv/exit/logs')
demo=read(f'evidence/{a.demo}/reconciliation.json')
main=read(f'evidence/{a.main}/reconciliation.json')
spark=read(E+'/spark-main.json')
independent=read(A+'/reconciliation-independent-main.json')
inspection=read(I+'/runs-independent.json')
preservation=read(I+'/preservation-final.json')
sources=read(I+'/source-final.json')
assert all(x['status']=='PASS' for x in [demo,main,spark,independent,inspection,preservation])
assert not sources['ast_errors']
old=(ROOT/'audit/2026-10-11-week1/bao-cao-nghiem-thu-tuan-1.md').read_text(encoding='utf-8')
before={}
for text in old.splitlines():
    if text.startswith('| TV'):
        cells=[s.strip() for s in text.split('|')]
        before[cells[1]]=cells[3]
assert len(before)==22
rec=f'evidence/{a.main}/reconciliation.json'
demo_rec=f'evidence/{a.demo}/reconciliation.json'
runtime=E+'/spark-main.json'
qa=E+'/dataset_quality.json'
matrix=[
('TV1-01','Movie dataset, nguồn/snapshot/license','docs/dataset_description.md','Nguồn:', 'data/raw/download_manifest.json', 'download-ca','GroupLens, ZIP + README local; snapshot README 26/09/2018, tải mới 11/10/2026.'),
('TV1-02','Kiểm metadata và trường cần dùng','scripts/prepare_movies.py','def prepare', I+'/dataset-independent.json','movies-prepare','Parser toàn CSV; năm theo hậu tố 1870–2100; 13 null hợp lệ, raw không sửa.'),
('TV1-03','Nguồn/CSV/encoding/header/count/dictionary','docs/dataset_description.md','| File gốc', I+'/dataset-independent.json','download-ca','Đếm mới movies 9742/ratings 100836/tags 3683/links 9742; hash, header, license local.'),
('TV1-04','Generator và semantics synthetic','scripts/generate_logs.py','def generate', 'data/generated/main.jsonl.manifest.json','generate-main','Generator thật, seed42, phiên hoàn chỉnh, durations synthetic, không chồng user.'),
('TV1-05','Hợp đồng log, units/timezone/consistency','docs/user_log_schema.md','| Field',rec,'flume-main','12 fields đúng schema chính; sequenceNumber Long; timestamp UTC Z; duration giây phát sinh.'),
('TV1-06','Log thực đủ phục vụ Tuần 2','docs/week2_handoff.md','| Phân tích',rec,'generate-main','Có main đúng1M + Sink thật; thống kê toàn lô, khóa phim/thể loại/giờ hoạt động đủ.'),
('TV1-07','Build/config/start Flume, heap/logging','config/flume-env.sh','export JAVA_OPTS',f'evidence/{a.main}/flume-operational.log','flume-main','Flume1.11.0/Java8; actual agent PrintFlagsFinal MaxHeapSize536870912 byte; build hashverified.'),
('TV1-08','Source/publish immutable file','scripts/run_pipeline.py','temporary.rename',rec,'flume-main','Spooldir LINE UTF8/batch500/max16384; .tmp ghi xong rename; actual Source nhận1M.'),
('TV1-09','File Channel isolation/capacity/rights','compose.yaml','flume-channel:/data/channel',f'evidence/{a.main}/channel-volume.json','flume-main','Volume Linux riêng project; checkpoint/data ghi thật, xuất sau stop; capacity1M/txn1000, queue0.'),
('TV1-10','Sink/newline/rolling/storage/mount','config/flume.conf','a1.sinks.k1.type',rec,'flume-main','File Roll localfilesystem, TEXT LF/batch500/roll10s; bytes/hash/empty/newline đo từngpart.'),
('TV1-11','E2E eventId/canonical payload toàn lô','scripts/validate_pipeline.py','missing = db.execute',A+'/reconciliation-independent-main.json','reconciliation-independent-main','Demo trước main cùngsource/config; full input/output thiếu/thừa/trùng/conflict/changed đều0.'),
('TV1-12','Log thực Source/Channel/Sink cùng run','config/log4j2.xml','<Root',f'evidence/{a.main}/flume-operational.log','flume-main','LogINFO timestamp, agent/components, Java args, counters; liên kết input/source/image/output cùngrun.'),
('TV2-01','Đọc và kiểm metadata/log thật','scripts/spark_smoke_test.py','sink=ROOT',runtime,'spark-main','Spark và validator độc lập đọc chính Sink đã đóng; hash và filelist khớp, không thay generated.'),
('TV2-02','Kiểu/nullability/units/ranges','src/schemas.py','MOVIE_SCHEMA',runtime,'spark-main','Long/String/Boolean/Integer đồng bộ; null bắt buộc0, yearnullable13; longbound vàduration kiểm.'),
('TV2-03','Reusable schemas + timestamp parse','scripts/spark_smoke_test.py',"withColumn('eventTime'",runtime,'spark-main','Áp StructType chính cả CSV/JSON, materialize mọi field; to_timestamp UTC và parsefail0.'),
('TV2-04','movieId type/unique/null/full orphan','scripts/spark_smoke_test.py',"'left_anti'",runtime,'spark-main','9742 unique movies, null0; full left anti join1Mlog orphan0, LongType hai bên.'),
('TV2-05','Full quality và ví dụ lỗi truy vết','scripts/spark_smoke_test.py','def validate_frames',runtime,'spark-main','UTF8/CSV/JSON/type/null/action/duration/time/duplicate/session kiểm toàn lô; fixture chứngminh phát hiệnlỗi.'),
('TV2-06','Kiến trúc + bằng chứng nhóm thống nhất','docs/architecture_decision_pending.md','chưa có xác nhận',I+'/source-final.json','inspection-final-v2','Có sơ đồ và triển khai nhất quán; chưa có ngày/người/biên bản xác nhận của nhóm.'),
('TV2-07','Luồng metadata/log -> Spark -> kết quả/dashboard','docs/system_architecture.md','Data Flow Architecture',runtime,'spark-main','Metadata trực tiếp Spark; log quaFlume; QA Tuần1đãchạy, phân tích/dashboard là Tuần2.'),
('TV2-08','Môi trường host/Flume/Spark đã xác minh','requirements.txt','Spark jobs',runtime,'spark-main','HostPython3.12.14; FlumeJava8; containerSpark3.5.1/PySpark3.5.1/Python3.8.10/Java11.0.22, digestlưu.'),
('TV2-09','SparkSession + action thật','scripts/spark_smoke_test.py','basic_action_count',runtime,'spark-main','SparkSessionlocal[2], range(5).count=5; nhiều count/collect/shuffle thật, exit0.'),
('TV2-10','Spark đọc full Sink/expectedcount/constraints','scripts/spark_smoke_test.py',".json([str(p)",runtime,'spark-main','Readactualparts, fullcount1M/9742 so manifest/recon; lỗi parse/null/key toàn log0.')]
out=[]
def add(text=''):
    out.append(text)
add('# Báo cáo triển khai và nghiệm thu lại Tuần 1')
add('\nProject: Phân tích dữ liệu phim và log hành vi người dùng. Ngày bắt đầu 11/10/2026 22:17:10 +07; các bước qua nửa đêm được ghi UTC thực trong command.json. Revision `bcb28b7fac0c9d260af0e6acb121947f991355f8`, branch `main`, không commit/push.')
add('\n## A. Kết luận nghiệm thu và sẵn sàng Tuần 2\n')
add('**Project hiện tại chưa hoàn thành đầy đủ các nhiệm vụ Tuần 1.** Kết quả: **21 ĐẠT, 1 ĐẠT MỘT PHẦN (TV2-06), 0 CHƯA ĐẠT, 0 CHƯA THỂ XÁC MINH**. Tỷ lệ chỉ tính ĐẠT: `21 / 22 × 100 = 95,45%`. Còn thiếu bằng chứng nhóm xác nhận kiến trúc; không tự điền thay nhóm. '+link('docs/architecture_decision_pending.md',3))
add('\n**Về kỹ thuật và dữ liệu: đã đủ 11 sản phẩm và sẵn sàng cho Tuần 2.** MovieLens được tải/giữ raw/license, demo10.000 và main1.000.000 được generator thật tạo sau demo E2E đạt, Flume chạy thật và Spark kiểm toàn bộ Sink mới. Dataset, input, Sink và logs thực sự tồn tại local; không dùng fixture/copy input làm output. '+link(A+'/dataset-independent.json')+', '+link(A+'/runs-independent.json')+', '+link(runtime)+'.')
add('\nMain: `'+a.main+'`; demo cấu hình cuối: `'+a.demo+'`. Đối chiếu độc lập toàn input/output có 0 missing/unexpected/duplicates/conflicting IDs/changed payload và 0 lỗi dữ liệu/phiên/user overlap. PASS là kết quả quan sát lô này, không chứng minh exactly-once hoặc phục hồi sự cố. '+link(A+'/reconciliation-independent-main.json')+'.')
add('\n## B. Phạm vi, revision, môi trường và giới hạn\n')
add('Root: `'+str(ROOT)+'`. Không có AGENTS.md tại các tổ tiên đã kiểm và không thấy file hướng dẫn nested; '+link(A+'/instructions-before.json')+'. Đã đọc yêu cầu gốc, audit cũ và yêu cầu mở rộng. Baseline inventory172 file; mọi file evidence lịch sử, data placeholder và toàn bộ audit cũ giữ hash nguyên. Source/docs được sửa trong quyền cho phép; '+link(A+'/inventory-before.json')+', '+link(A+'/preservation-final.json')+'.')
add('\nĐã đọc toàn bộ '+str(len(sources['files_read']))+' file source/config/tests/docs/root cuối bằng UTF8strict, đánh số dòng, AST mọiPython; '+link(A+'/numbered-final-project-files.txt')+', '+link(A+'/source-final.json')+'. Tất cả rawCSV parserstrict, generated/Sink streaming/SQLite theo từngevent và Spark fullactions; không kết luận toàn lô từ sample. Git revision/diff/status và sourcehash cuối: '+link(A+'/git-final.json')+'. Không sửa raw, status/reconciliation cũ; không cài hệ thống, thay WSL/security, commit/push, gửi dịch vụ hoặc triển khai Tuần2.')
add('\n| Runtime | Phiên bản/môi trường thực đo | Bằng chứng |\n|---|---|---|')
add('| Host | Windows10 build19045; Python3.12.14 bundled thực, không dùng alias WindowsApps | '+step('host-resources')+' |')
add('| Docker | Desktop4.88.1; Client/Engine29.7.2; Composev5.4.0; desktop-linux; Linux containers; 4CPU/7,486GiB | '+step('docker-version')+', '+step('docker-info')+' |')
add('| Flume | 1.11.0, TemurinJava1.8.0_504; agent heap128MiB/512MiB | '+link(f'evidence/{a.main}/flume-version.txt')+', '+link(f'evidence/{a.main}/java-version.txt')+', '+ref(f'evidence/{a.main}/flume-operational.log','MaxHeapSize')+' |')
add('| Spark | Spark/PySpark3.5.1, Python3.8.10, Java11.0.22, local[2], driver2GiB | '+ref(runtime,'"runtime"')+', '+step('spark-image')+' |')
add('\nDocker ban đầu chưa chạy; sandbox không đọc được Docker config/context. Dùng thao tác đã được phép để mở Docker Desktop có sẵn và gọi Docker ngoài sandbox, không sửa quyền/cấu hình bảo mật. TLS Python lần đầu lỗi CA (exit1); bundle rootCApublic từ Node giúp tải HTTPS verified (exit0), không tắt TLS. '+step('download')+', '+step('download-ca')+'.')
add('\nTài nguyên: host16.587.788.288 byteRAM; sau tải images khoảng69.081.079.808 byteđĩatrống. Linux `/tmp` có997.983.784KiB available (đĩaảo; dung lượng vật lý host vẫn giới hạn); budget khoảng12GB gồmimages/input+spool+Sink/channel+export/SQLite. Temporary validator của wrapper nằm trong audit riêng, Spark/validatorcontainer dùng /tmpLinux. Đo và môi trường tại '+step('host-resources')+', '+step('container-resources')+'. Main thực tế hoàn tất đúngquymô, không giảm event.')
add('\nGiới hạn: synthetic không đại diện hành vi người thật; snapshot phát triển MovieLens có thể đổi; chưa fault-injection/recovery benchmark/HDFS/dashboard, không suy các khả năng đó từ runPASS. Tag image mutable; imageID/digest/build/launcher lưu cùng run. Phần nhóm thống nhất là quyết định bên ngoài, vẫn chưa xác minh.')
add('\n## C. Ma trận đủ 22 nhiệm vụ\n')
add('| ID | Yêu cầu | Trạng thái | Bằng chứng cụ thể | Thiếu sót | Việc cần làm |\n|---|---|---|---|---|---|')
for ident,title,source,needle,data,execution,detail in matrix:
    status='ĐẠT MỘT PHẦN' if ident=='TV2-06' else 'ĐẠT'
    evidence=ref(source,needle)+'; '+link(data)+'; '+step(execution)+'; '+detail
    missing='Chưa có xác nhận kiến trúc của các thành viên.' if ident=='TV2-06' else 'Không còn thiếu trong phạm vi nhiệm vụ.'
    nextstep='Nhóm cung cấp ngày/người/biên bản xác nhận; kiểm lại TV2-06.' if ident=='TV2-06' else 'Giữ artifacts/hash và áp hợp đồng khi dùng Tuần2.'
    add(f'| {ident} | {title} | {status} | {evidence} | {missing} | {nextstep} |')
add('\nSo sánh theo từng nhiệm vụ với báo cáo trước (không thay bằng chứng lịch sử):\n')
add('| ID | Trước | Sau |\n|---|---|---|')
for ident,*_ in matrix:
    add(f'| {ident} | {before[ident]} | '+('ĐẠT MỘT PHẦN' if ident=='TV2-06' else 'ĐẠT')+' |')
add('\n## D. 11 sản phẩm bàn giao\n')
add('| STT | Sản phẩm | Tồn tại/đường dẫn | Chất lượng và bằng chứng | Trạng thái / phần thiếu |\n|---|---|---|---|---|')
products=[('Movie dataset hoàn chỉnh','data/raw/ml-latest-small.zip','ZIP978202B + README/license +4rawCSV + movies9742; parser/hash '+link(A+'/dataset-independent.json')),
('File log hành vi','data/generated/main.jsonl','1M thực,343339148B, manifest/seed/provenance; demo10000 cũng có '+link('data/generated/main.jsonl.manifest.json')),
('Mô tả dataset/log','docs/dataset_description.md',link('docs/log_schema.md')+'; nguồn/snapshot/dictionary/session/units/timezone cập nhật'),
('flume.conf','config/flume.conf','Source/Channel/Sink cấu hình đúng, source hash khớp demo/main '+link(A+'/runs-independent.json')),
('Output dữ liệu sau Flume',f'data/runs/{a.main}/output',str(main['output_file_summary']['files'])+'file/'+str(main['output_file_summary']['bytes'])+'bytes, Sinkthật fullrecon '+link(rec)),
('Log chứng minh Flume',f'evidence/{a.main}/flume-operational.log','INFOthànhphần/counters/heap; logs/run cũng có, không cần ảnh '+link(f'evidence/{a.main}/metrics-final.json')),
('Bảng schema','docs/movie_schema.md',link('docs/user_log_schema.md')+'; đồngbộ nullable/types với schemachính'),
('Danh sách trường và kiểu','src/schemas.py','4movie+12log fields; đượcimport/ápdụng trong Spark '+link(runtime)),
('Sơ đồ/luồng kiến trúc','docs/system_architecture.md','Có sơ đồ đúng code; sảnphẩmtài liệuĐẠT, xácnhận nhóm vẫnthiếu tại TV2-06'),
('Runtime Spark đã kiểm thử',runtime,'SparkSession/actionthật; stdout/stderr/argv/exit0 '+step('spark-main')),
('Xác nhận Sink dùng Tuần2','docs/week2_handoff.md','Schema/count/parse/null/orphan/session hợp lệ toàn1M; chỉ số/limits rõ '+link(A+'/reconciliation-independent-main.json'))]
for i,(name,path,detail) in enumerate(products,1):
    assert (ROOT/path).exists(),path
    add(f'| {i} | {name} | Có: {link(path)} | {detail} | ĐẠT; '+('phêduyệt nhóm xét ởTV2-06.' if i==9 else 'không thiếu sảnphẩm kỹthuật.')+' |')
add('\nData/log bị `.gitignore` nhưng đã kiểm tồn tại và hash tại checkout; cần bàn giao cùng source/evidence theo manifest mới, không chỉ cloneGit. Manifest bao phủroot/source/config/schema/tests/docs/raw+license/generated/Sink/logs/evidence/audit; excludeschannel/spool/tempfixtures/CApublic/cache/historykhôngchọn/chínhmanifest/laterverification. '+link(E+'/delivery_manifest.json')+'.')
add('\n## E. Lệnh, exit code, số liệu đo và lịch sử\n')
add('Mỗi command.json có argv tách thành danh sách, cwd, started/finishedUTC, Python/OS/biếnruntime, exitcode và stdout/stderr path. Flume từng lệnh con có nhật ký trong commands.json, gồm resolvedCompose/image/build/Java/Flume/launcher/heap/counter/stop/export/down. '+link(f'evidence/{a.main}/commands.json')+'.')
add('\n| Bước | Exit | UTC bắt đầu → kết thúc | Lệnh/đầu ra |\n|---|---:|---|---|')
for folder in sorted((AUDIT/'execution').iterdir()):
    if not (folder/'command.json').exists():continue
    r=json.loads((folder/'command.json').read_text(encoding='utf-8'))
    if 'finished_at_utc' not in r:continue
    add('| '+folder.name+' | '+str(r.get('exit_code'))+' | '+r['started_at_utc']+' → '+r['finished_at_utc']+' | '+link((folder/'command.json').relative_to(ROOT).as_posix())+' |')
add('\n18 Python tests PASS; 7 Spark nghiệp vụ fixtures PASS và 2 parser fixtures PASS. Assertions thật yêu cầu phát hiện missing/trùng/changed/invalid, genresmissing, duplicatemovie, truncatedLF, signedlongoverflow, inputnooverwrite, orphan ngoài5dòng, timestampnull/type/conflicts. Fixtures không được coi là Flume. '+step('tests-final')+', '+link(A+'/spark-fixtures.json')+', '+link(A+'/spark-parser-fixtures.json')+'.')
add('\nLệnh đọc SQLite tiến độ cuối exit1 vì container --rm đã hoàn tất và bị gỡ trước khi probe chạy; validator độc lập exit0/PASS. Helper viết báo cáo lần đầu exit1 do chọn command theo prefix không phân biệt download với download-ca; đã sửa chọn đúng label và chạy lại. Các lỗi phụ này giữ nguyên logs và không thay kết quả dữ liệu/runtime. '+step('independent-sqlite-progress')+', '+step('report-authoring')+'.')
add('\n| Đo toàn lô | Demo cấu hình cuối | Main |\n|---|---:|---:|')
for name,key in [('Eventinput/output','total'),('Hợplệinput/output','valid'),('IDuniqueinput/output','unique'),('Duplicate','duplicates'),('Conflicting','conflicting_ids'),('Invalid','invalid'),('Users','users'),('Movies','movies'),('Sessions','sessions'),('Watch seconds','watch_seconds'),('UTCmin','timestamp_min'),('UTCmax','timestamp_max')]:
    add(f"| {name} | {demo['output'][key]} | {main['output'][key]} |")
for name,key in [('Files','files'),('Sinkbytes','bytes'),('Emptyfiles','empty_files'),('Missingfinalnewline','missing_final_newline_files')]:
    add(f"| {name} | {demo['output_file_summary'][key]} | {main['output_file_summary'][key]} |")
for action in ['view','play','pause','stop','complete']:
    add(f"| Action {action} | {demo['output']['actions'][action]} | {main['output']['actions'][action]} |")
add('\nThống kê input/output đều khớp, không chỉ outputcount. Nguồn số liệu: '+link(demo_rec)+', '+link(rec)+', '+link(A+'/reconciliation-independent-main.json')+', '+link(runtime)+'. Khoảngmôphỏng là tháng09/2026 giờViệtNam; UTC có thể bắt đầu31/08. Watchtime giâyphát sinh, không tổnglũykế/runtime; sessions đãplay = stop+complete (main'+str(main['output']['actions']['stop']+main['output']['actions']['complete'])+'). Giờbắtđầuphiên đo trong manifest, không suy trọngsố generator là phân bốthực.')
add('\n| File | Bytes/SHA256 |\n|---|---|')
for path in ['data/raw/ml-latest-small.zip','data/processed/movies.csv','data/generated/demo.jsonl','data/generated/main.jsonl']:
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from common import sha256
    add('| '+link(path)+' | '+str((ROOT/path).stat().st_size)+' / `'+sha256(ROOT/path)+'` |')
add('\nSink có SHA256/bytes/empty/finalnewline từngpart trong reconciliation. '+ref(rec,'"output_files"')+'. Movies QA0IDtrùng/title/genresmissing; year13null/no_genres34 là dữliệu chấpnhận, không bỏ dòng. UTF8/JSON/type/time/action/provenance errors đều0 trong fullvalidator/Spark. Validator báo lỗi đầu tiên mỗi dòng lỗi; sessionerrors và overlap có counter riêng. Spark kiểm từng constraint trên toàn lô, examplestruyvết `_file`/eventId chỉ xuất khi lỗi.')
add('\nTrình tự thực: demo `run-8ceda3a1111e` E2EPASS ban đầu; sau sửa volume/agentheapflags, chạy demo `'+a.demo+'` PASS mới trước sinh/main `'+a.main+'`. Source/config hashes cùngcấuhìnhcuối khớp; actualimage/build/source snapshots lưu riêng. Các thayđổi docs/check_environment/Sparkparserfixture sau đó không ảnhhưởng cấuhình/source pipeline đãchạy. Không cần chạy lại pipeline1M khi data/source liênquan khôngđổi.')
add('\nLịch sử nguyên trạng: demo run-558d55e8a73f/run-a9b3a8a26afb và main run-f63c810e9d8d báoPASS cũ; run-a16e0fb65471 FAIL với550573output/449427missing; run-62b191534ce6 BLOCKED; run-8309c89de03e builddở. Lịch sử D:\\Code không thaycho checkouthiện tại. Manifestcũ54mục khôngbao phủđủ đượcgiữ, thaybằng manifestmới. Audit trước7ĐẠT/11partial/1chưađạt/3chưaxácminh nguyênhash. '+link('audit/2026-10-11-week1/bao-cao-nghiem-thu-tuan-1.md')+', '+link(A+'/preservation-final.json')+'.')
add('\n## F. Lỗi, mâu thuẫn và giới hạn còn lại\n')
add('| Mức | Vị trí / ảnh hưởng | Cách xử lý |\n|---|---|---|')
add('| Nghiêm trọng | Không thấy blocker kỹthuật/dữliệu cho Tuần2 sau QA toànlô. | Giữ snapshot/hash, bàn giao dữliệu Gitignored cùngmanifest. |')
add('| Lớn | '+link('docs/architecture_decision_pending.md',3)+'; TV2-06 thiếu xácnhận nhóm nên chặn kếtluận đầyđủ22/22. | Cungcấp ngày/người/nội dungphêduyệt; táikiểm hồsơ này, không cần chạy lại main nếu source/datađổi0. |')
add('| Nhỏ / giới hạn | Image tag có thể đổi; host/container phiênbản khác nhau; recovery chưa thử. | Giữ image ID/digest/source snapshot; chạy theo container/documentationthựcđo; không côngbố exactlyonce. |')
add('\nĐã khắc phục lỗi thực tế: JAVA_OPTSenv sai cơ chế launcher; thiếu log4j2INFO; smoke chỉ join5/assertcount>0; thiếu timestamp/null/fullorphans; setmovieId chedup; genresmissingkhôngFAIL; empty/newlinepartchưađo; reportoldoverwrite/hardcoderun; types/runtime/docs lệch. Bằngchứng trước vẫn giữ; chỉ hiệnhành được sửa.')
add('\nMột lần chạy script môi trường sau sửa CLI bị lỗi AttributeError do biến options bị vòng lặp shadow (exit1); đã đổi tên biến, chạy lại exit0 và tạo report mới. Đây là lỗi của sửa đổi trong lượt này, không phải blocker Docker; cả hai command logs được giữ. '+step('environment-final')+', '+step('environment-final-fixed')+'.')
add('\nCác file sửa/thêm và lý do:\n')
reasons={'Dockerfile':'Copy flume-env/log4j2 và dùng biến heap đúng launcher.', 'compose.yaml':'Volume File Channel Linux riêng, SparkCLI rõ report/run, không tạo pycache.',
 '.dockerignore':'Loại audit khỏi buildcontext.', 'requirements.txt':'Tách stdlibhost với PySpark/Java bundledcontainer.',
 'scripts/check_environment.py':'Reportpathmới, bảo vệ bằngchứng cũ.', 'scripts/prepare_movies.py':'Reportnooverwrite/genresmissingFAIL.',
 'scripts/run_flume.sh':'HTTPmetrics và logging hợp Flume1.11.', 'scripts/run_pipeline.py':'Snapshot/hash/source/demo gating, commandtiming/exit/heap/counters/exportchannel, fullrecon.',
 'scripts/validate_pipeline.py':'Fullmetadataquality/64bit/duration/errors/stats/emptyparts/newline/nooverwrite.',
 'scripts/spark_smoke_test.py':'FullactualSink schema/parse/null/count/key/sessionchecks thay mẫu.',
 'scripts/movie_quality.py':'CSVparserfull uniqueness/null/year/encoding/normalization.',
 'scripts/spark_regression_test.py':'7fixture Spark nghiệp vụ có assertions.',
 'scripts/spark_parser_regression_test.py':'2fixtureparse Spark thật, malformed/typeerrors.',
 'config/flume-env.sh':'Options đúng thờiđiểm launcher, PrintFlagsFinal từactualagent.',
 'config/log4j2.xml':'INFOconsole/file ghi agent/source/channel/sink.',
 'tests/test_project.py':'6regression quantrọng, tổng18.', 'docs/architecture_decision_pending.md':'Đềxuất cụthể chờphêduyệt, không giảack.'}
changed=set(preservation['changed_authorized_source_docs'])
baseline={r['path'] for r in read(A+'/inventory-before.json')}
changed.update(r['path'] for r in sources['files_read'] if r['path'] not in baseline)
add('| File | Lý do |\n|---|---|')
for path in sorted(changed):
    add('| '+link(path)+' | '+reasons.get(path,'Đồngbộ tài liệu hiệnhành với run/output/schema/runtime mới đãđo; phânbiệt history và pendingapproval.')+' |')
add('\nAudit helpers là file bổsung trong audit riêng để ghi command/resource/đọcđộclập/tạo docs/report. Sourcehash/nội dung filecuối ghi trong source-final; không có commit/push. Raw/generated/Sink/manifest là sảnphẩmmới, không ghiđè fileold.')
add('\n## G. Thống kê và ưu tiên hoàn thiện\n')
add('| Kết quả | Trước | Sau |\n|---|---:|---:|\n| ĐẠT | 7 | 21 |\n| ĐẠT MỘT PHẦN | 11 | 1 |\n| CHƯA ĐẠT | 1 | 0 |\n| CHƯA THỂ XÁC MINH | 3 | 0 |\n| Tổng | 22 | 22 |')
add('\nƯu tiên duy nhất để chốt đầyđủ Tuần1: nhóm xác nhận kiến trúc/units/runtime/đườngdẫn/phâncông theo tài liệu chờ quyếtđịnh. Có xácnhận mới thì bổsung bằngchứngmới và cậpnhật nhiệm vụ TV2-06 trong một audit mới; không đổi status/reconlịch sử.')
add('\nLệnh táikiểm chứng (reportphải chọn tên mới; `$py` dùng Pythonthật đãghi ởB):\n')
add('```powershell\n& $py -m unittest discover -s tests -v\n& $py scripts/validate_pipeline.py --input data/generated/main.jsonl --output-dir data/runs/'+a.main+'/output --report evidence/main-independent-new.json\ndocker compose -p movie-spark-new run --rm spark --driver-memory 2g scripts/spark_smoke_test.py --movie-report '+qa+' --run-evidence evidence/'+a.main+' --report evidence/spark-independent-new.json\n& $py scripts/create_delivery_manifest.py --verify '+E+'/delivery_manifest.json\n```')
add('\nBản kiểmđộc lập hiệntại đã chạy validator toànlô trên Linuxcontainer /tmp (stdlibPython3.8.10) và host đọc/hash/source/Git: '+step('reconciliation-independent-main')+', '+step('inspection-final')+'. Không tạo lại Sink. Kiểmmanifest cuối được lưu trong execution/manifest-verify...; manifesttựloại chính nó và báo cáo/lệnhkiểm tạo sau để tránh tựthamchiếu hash. Inventory/preservationauditcuốinguyênhash cho mọievidence/auditold.')
add('\n**Trả lời:** chưa hoàn thành đầy đủ Tuần1 vì thiếu xácnhậnkiếntrúc của nhóm; 21/22nhiệm vụĐẠT, 11/11sảnphẩm kỹthuật cóthật và đã kiểm, dữliệu kỹthuật sẵn sàng Tuần2.')
target=AUDIT/'bao-cao-nghiem-thu-tuan-1-recheck.md'
if target.exists():raise FileExistsError(target)
body='\n'.join(out)+'\n'
for filename in ['dataset-independent.json','runs-independent.json','preservation-final.json','source-final.json','numbered-final-project-files.txt','git-final.json']:
    body=body.replace(A+'/'+filename,I+'/'+filename)
# Keep the Vietnamese report readable; technical identifiers/paths stay literal.
spacing={
 'đồngbộ':'đồng bộ','Đồngbộ':'Đồng bộ','độclập':'độc lập','kiểmđộc':'kiểm độc','kiểmđịnh':'kiểm định',
 'toànlô':'toàn lô','toàn1M':'toàn 1M','toàn log0':'toàn log: 0','từngevent':'từng event','từngpart':'từng part',
 'nguồn/snapshot/license':'nguồn / snapshot / license','thựcđo':'thực đo','đãđo':'đã đo','đãchạy':'đã chạy',
 'nhómphêduyệt':'nhóm phê duyệt','phêduyệt':'phê duyệt','xácnhận':'xác nhận','kếtluận':'kết luận',
 'nghiệmthu':'nghiệm thu','kiếntrúc':'kiến trúc','thànhphần':'thành phần','cấu hìnhcuối':'cấu hình cuối',
 'cấu hình/source':'cấu hình / source','cấu hìnhđổi':'cấu hình đổi','cấu hìnhchính':'cấu hình chính',
 'hệthống':'hệ thống','kỹthuật':'kỹ thuật','dữliệu':'dữ liệu','sảnphẩm':'sản phẩm','sảnphẩmtài':'sản phẩm tài',
 'tài liệuĐẠT':'tài liệu ĐẠT','đườngdẫn':'đường dẫn','phâncông':'phân công','hồsơ':'hồ sơ',
 'kiểmthử':'kiểm thử','kiểm thửhồi':'kiểm thử hồi','kiểm trađầy':'kiểm tra đầy','đủquymô':'đủ quy mô',
 'đúngquymô':'đúng quy mô','bằngchứng':'bằng chứng','hiệnhành':'hiện hành','lịch sửnguyên':'lịch sử nguyên',
 'hiện tạiđược':'hiện tại được','checkouthiện':'checkout hiện','đườngdẫn':'đường dẫn','tồn tại/hash':'tồn tại / hash',
 'khôngđổi':'không đổi','đổi0':'đổi: 0','liênquan':'liên quan','thayđổi':'thay đổi','khắcp hục':'khắc phục',
 'Chuyểnđổi':'Chuyển đổi','chuyểnđổi':'chuyển đổi','chuyển sangTimestamp':'chuyển sang Timestamp',
 'đápứng':'đáp ứng','lớpQA':'lớp QA','nhỏnhất':'nhỏ nhất','đóngfile':'đóng file','cùngrun':'cùng run',
 'cùngcấuhìnhcuối':'cùng cấu hình cuối','cùngsource/config':'cùng source/config','cùngrun':'cùng run',
 'trênfull':'trên full','fullrecon':'full reconciliation','fulldataset':'full dataset','fullinput':'full input',
 'masterlocal':'master local','local[2]':'local[2]','Flume1.11.0':'Flume 1.11.0','FlumeJava8':'Flume Java 8',
 'TemurinJava':'Temurin Java','PySpark3.5.1':'PySpark 3.5.1','Spark3.5.1':'Spark 3.5.1',
 'Python3.12.14':'Python 3.12.14','Python3.8.10':'Python 3.8.10','Java11.0.22':'Java 11.0.22',
 'Desktop4.88.1':'Desktop 4.88.1','Engine29.7.2':'Engine 29.7.2','Composev5.4.0':'Compose v5.4.0',
 '4CPU/7,486GiB':'4 CPU / 7,486 GiB','2GiB':'2 GiB','12GB':'12 GB','byteRAM':' byte RAM','byteđĩatrống':' byte đĩa trống',
 'KiB available':' KiB available','đĩaảo':'đĩa ảo','/tmpLinux':'/tmp Linux','/tmpLinux':'/tmp Linux',
 'driver2GiB':'driver 2 GiB','heap128MiB/512MiB':'heap 128 MiB / 512 MiB','Actualheap':'Actual heap',
 'agentheapflags':'agent heap flags','max_heap':'max_heap','INFOconsole/file':'INFO console/file',
 'INFOthành':'INFO thành','stampthực':'stamp thực','snapshotmới':'snapshot mới','schemachính':'schema chính',
 'Source nhận1M':'Source nhận 1M','actualparts':'actual parts','actualimage':'actual image','sourcehash':'source hash',
 'sourcehashcuối':'source hash cuối','Sourcehash':'Source hash','quyềnhạn':'quyền hạn','hashverified':'hash verified',
 'MaxHeapSize536870912':'MaxHeapSize 536870912','counter riêng':'counter riêng','queue0':'queue: 0',
 'scope/exclusions':'scope / exclusions','status/reconlịch':'status/recon lịch','lịch sửthiếu':'lịch sử thiếu',
 'phục hồiđĩa':'phục hồi đĩa','đúngcode':'đúng code','cuốiđược':'cuối được','/eventId':' / eventId',
 'nooverwrite':'không ghi đè','reportpathmới':'đường dẫn report mới','LongType hai':'LongType hai',
 'metadataquality':'metadata quality','signedlongoverflow':'signed long overflow','durationkiểm':'duration được kiểm',
 'unitshost':'units host','TimestampTypeUTC':'TimestampType UTC','runtimeđã':'runtime đã',
 'parsefail0':'parse failures: 0','null0':'null: 0','orphan0':'orphan: 0','error0':'error: 0','movies9742':'movies: 9742',
 'runPASS':'run PASS','lượtPASS':'lượt PASS','lịch sửD:':'lịch sử D:','khôngbao':'không bao','đầyđủ':'đầy đủ',
 'táikiểm':'tái kiểm','tựthamchiếu':'tự tham chiếu','tựloại':'tự loại','chínhmanifest':'chính manifest',
 'chínhrun':'chính run','vàsequence':'và sequence','địnhnghĩa':'định nghĩa','bổsung':'bổ sung','táchbiệt':'tách biệt',
 'sẵn sàngTuần':'sẵn sàng Tuần','Tuần1':'Tuần 1','Tuần2':'Tuần 2','1Mlog':'1M log','logcount':'log count',
 'fullcount1M/9742':'full count 1M / 9742','12fields':'12 fields','fullactions':'full actions','Pythonthật':'Python thật',
 'người/nội dungphê':'người / nội dung phê','môphỏng':'mô phỏng','Watchtime':'Watch time','thời lượnglũy':'thời lượng lũy',
 'giờViệtNam':'giờ Việt Nam','giâyphát':'giây phát','tổnglũykế':'tổng lũy kế','bắtđầuphiên':'bắt đầu phiên',
 'trọngsố':'trọng số','phân bốthực':'phân bố thực','dòngmissing':'dòng missing','errorcounts':'error counts',
 'chấpnhận':'chấp nhận','đầu tiên mỗi':'đầu tiên mỗi','đượcgiữ':'được giữ','đượcchọn':'được chọn',
 'bao phủđủ':'bao phủ đủ','thốngnhất':'thống nhất','đủ22/22':'đủ 22/22','thờiđiểm':'thời điểm',
 'phát hiệnlỗi':'phát hiện lỗi','chứngminh':'chứng minh','đĩatrống':'đĩa trống','con số1M':'con số 1M',
 'unit tests':'unit tests','INPUTPASS':'INPUT_PASS','đãplay':'đã play','main1.000.000':'main 1.000.000',
 'demo10.000':'demo 10.000','demo10000':'demo 10000','restorelịch':'restore lịch','sai cơ chếlauncher':'sai cơ chế launcher',
 'Hợplệ':'Hợp lệ','Eventinput/output':'Event input / output','IDuniqueinput/output':'ID unique input / output',
 'Sinkbytes':'Sink bytes','Emptyfiles':'Empty files','Missingfinalnewline':'Missing final newline','UTCmin':'UTC min','UTCmax':'UTC max',
 'trước7ĐẠT':'trước 7 ĐẠT','mọievidence':'mọi evidence','auditcuối':'audit cuối','cuốinguyênhash':'cuối nguyên hash',
 'tài liệuchờ':'tài liệu chờ','ưu tiênhoàn':'ưu tiên hoàn','kiểmmanifest':'kiểm manifest','báo cáo/lệnhkiểm':'báo cáo / lệnh kiểm',
 'host đọc/hash/source/Git':'host đọc/hash/source/Git','ngày/người/biên bản':'ngày / người / biên bản',
 '11/11sản':'11/11 sản','21/22nhiệm':'21/22 nhiệm','nhiệm vụĐẠT':'nhiệm vụ ĐẠT','cóthật':'có thật',
 'và đã kiểm':'và đã kiểm','bàn giao dữ liệu Gitignored':'bàn giao dữ liệu bị Git ignore',
 'tách stdlibhost':'tách stdlib host','bundledcontainer':'bundled container','6regression':'6 regression',
 'tổng18':'tổng 18','2fixtureparse':'2 fixture parse','7fixture':'7 fixture','có assertions':'có assertions',
 'schema/runtime mới đã đo':'schema/runtime mới đã đo','đúng thờiđiểm':'đúng thời điểm','Sourc e':'Source',
 'stat us':'status','filecuối':'file cuối','bảo vệ bằng chứng cũ':'bảo vệ bằng chứng cũ','historykhôngchọn':'history không chọn',
 'CApublic':'CA public','chínhmanifest/laterverification':'chính manifest / later verification',
 'exactlyonce':'exactly-once','Tuần 1đãchạy':'Tuần 1 đã chạy','TV2-06.' :'TV2-06.',
}
for old_text,new_text in sorted(spacing.items(),key=lambda pair:len(pair[0]),reverse=True):
    body=body.replace(old_text,new_text)
target.write_text(body,encoding='utf-8')
print(target)
