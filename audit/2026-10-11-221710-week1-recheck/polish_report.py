"""Polish the new report draft before freezing its handoff hash."""
import re
from pathlib import Path

folder=Path(__file__).resolve().parent
target=folder/'bao-cao-nghiem-thu-tuan-1-recheck.md'
body=target.read_text(encoding='utf-8')
backup=folder/'report-draft-before-polish.md'
with backup.open('x',encoding='utf-8') as f:f.write(body)
replacements={
 'các bước qua nửa đêm được ghi UTC thực':'thời điểm từng bước được ghi UTC thực',
 'Baseline inventory172':'Inventory ban đầu: 172','UTF8strict':'UTF-8 strict','mọiPython':'mọi file Python',
 'rawCSV parserstrict':'CSV gốc được đọc bằng parser strict','Windows10':'Windows 10','build19045':'build 19045',
 'Java1.8.0_504':'Java 1.8.0_504','exit1':'exit 1','exit0':'exit 0','rootCA':'root CA',
 'host16.587':'host 16.587','khoảng69.081':'khoảng 69.081','có997.983':'có 997.983','khoảng12':'khoảng 12',
 'gồmimages':'gồm images','validatorcontainer':'validator trong container','imageID':'image ID',
 'seed42':'seed 42','đúng1M':'đúng 1M','Java8':'Java 8','UTF8':'UTF-8','batch500':'batch 500',
 'max16384':'max 16384','capacity1M/txn1000':'capacity 1M / transactionCapacity 1000',
 'localfilesystem':'filesystem local','roll10s':'roll 10 giây','đều0':'đều 0','LogINFO':'Log INFO',
 'filelist':'danh sách file','bắt buộc0':'bắt buộc: 0','yearnullable13':'13 năm null hợp lệ',
 'longbound vàduration kiểm':'biên Long và duration được kiểm','to_timestamp UTC':'to_timestamp UTC',
 'unique movies':'movieId phân biệt','LongType hai bên':'LongType ở cả hai bên','SparkSessionlocal':'SparkSession local',
 'log: 0':'log: 0','dữ liệu Gitignored':'dữ liệu bị Git ignore','cùngmanifest':'cùng manifest',
 'source/datađổi: 0':'source/data không đổi','Cungcấp':'Cung cấp','phiênbản':'phiên bản',
 'documentationthực đo':'tài liệu theo runtime thực đo','côngbố':'công bố','JAVA_OPTSenv':'JAVA_OPTS trong ENV',
 'log4j2INFO':'log4j2 INFO','join5/assertcount>0':'join 5 dòng/assert count > 0','fullorphans':'full orphan check',
 'setmovieId chedup':'set movieId che ID trùng','genresmissingkhôngFAIL':'genres thiếu chưa làm FAIL',
 'empty/newlinepartchưađo':'chưa đo file rỗng/newline cuối từng part',
 'reportoldoverwrite/hardcoderun':'report có thể ghi đè/hardcode run','Bằngchứng':'Bằng chứng',
 'buildcontext':'build context','phânbiệt':'phân biệt','pendingapproval':'xác nhận đang chờ',
 'SparkCLI':'Spark CLI','từactualagent':'từ chính agent đang chạy','Đềxuất':'Đề xuất','cụthể':'cụ thể',
 'chờphê duyệt':'chờ phê duyệt','giảack':'giả lập xác nhận','stdlibhost':'stdlib trên host',
 'Reportpathmới':'Đường dẫn report mới','CSVparserfull':'CSV parser toàn dữ liệu',
 'Reportkhông ghi đè/genresmissingFAIL':'Report không ghi đè, genres thiếu làm FAIL',
 'HTTPmetrics':'HTTP metrics','Flume1.11':'Flume 1.11','commandtiming':'thời điểm từng lệnh',
 'exportchannel':'xuất channel','typeerrors':'lỗi kiểu','FullactualSink':'Kiểm toàn bộ Sink thực tế',
 'sessionchecks':'kiểm phiên','Fullmetadata quality/64bit':'Kiểm metadata toàn lô/64-bit',
 'emptyparts':'file rỗng','quantrọng':'quan trọng','đọcđộc lập':'đọc độc lập',
 'sản phẩmmới':'sản phẩm mới','ghiđè':'ghi đè','fileold':'file cũ','quyếtđịnh':'quyết định',
 'bằng chứngmới':'bằng chứng mới','cậpnhật':'cập nhật','reportphải':'report phải','đãghi ởB':'đã ghi ở B',
 'hiệntại':'hiện tại','Linuxcontainer':'container Linux','stdlibPython':'stdlib Python',
 'Kiểmmanifest':'Kiểm manifest','manifesttự':'manifest tự','preservationaudit':'preservation audit',
 'auditold':'audit cũ','xác nhậnkiến trúc':'xác nhận kiến trúc','sản phẩm kỹthuật':'sản phẩm kỹ thuật',
 'genresmissing':'genres thiếu','duplicatemovie':'movieId trùng','truncatedLF':'thiếu LF cuối',
 'inputkhông ghi đè':'không ghi đè input','ngoài5dòng':'ngoài 5 dòng đầu','timestampnull':'timestamp null',
 'Hợp lệinput/output':'Hợp lệ input / output','outputcount':'count output','Khoảngmô phỏng':'Khoảng mô phỏng',
 'tháng09':'tháng 09','đầu31/08':'đầu 31/08','main257928':'main: 257.928',
 'Giờbắt đầu':'Giờ bắt đầu','QA0IDtrùng/title/genres thiếu':'QA: 0 ID trùng/title thiếu/genres thiếu',
 'year13null/no_genres34':'13 năm null/34 nhãn no_genres','fullvalidator':'validator toàn lô',
 'sessionerrors':'lỗi phiên','examplestruyvết':'ví dụ truy vết','E2EPASS':'E2E PASS',
 'Sparkparserfixture':'fixture parser Spark','ảnhhưởng cấuhình':'ảnh hưởng cấu hình',
 'pipeline1M':'pipeline 1M','báoPASS':'báo PASS','với550573output/449427missing':'với 550.573 output/449.427 missing',
 'builddở':'build dở','thaycho':'thay cho','Manifestcũ54mục':'Manifest cũ 54 mục','thaybằng':'thay bằng',
 'manifestmới':'manifest mới','11partial/1chưađạt/3chưaxácminh':'11 ĐẠT MỘT PHẦN/1 CHƯA ĐẠT/3 CHƯA THỂ XÁC MINH',
 'nguyênhash':'giữ nguyên hash','no_genres34':'no_genres: 34','4movie+12log':'4 trường movie + 12 trường log',
 'ZIP978202B':'ZIP 978.202 byte','4rawCSV':'4 CSV gốc','1M thực,343339148B':'1M thực, 343.339.148 byte',
 'Sinkthật':'Sink thật','INFOthànhphần':'INFO thành phần','log: 0':'log: 0','10000':'10000',
 'null/duplicate':'null/duplicate','sourcehash':'source hash','capacity1000000':'capacity 1000000',
 'payloadcharacters':'payload characters','12 GB gồm':'12 GB gồm','phê duyệt nhóm xét ởTV2-06':'phê duyệt nhóm xét ở TV2-06',
 'không thiếu sản phẩm kỹthuật':'không thiếu sản phẩm kỹ thuật','một triệu input/output':'một triệu input/output',
 'excludeschannel':'Loại trừ channel','/spool/tempfixtures':'/spool/fixture tạm','/CA public/cache':'/CA public/cache',
 'scope/exclusions':'scope/exclusions','CPU30':'CPU 30','giâyphát':'giây phát',
}
parts=re.split(r'(```[\s\S]*?```|`[^`]*`|\[[^\]]*\]\(<[^>]*>\))',body)
for index in range(0,len(parts),2):
    text=parts[index]
    for old,new in sorted(replacements.items(),key=lambda pair:len(pair[0]),reverse=True):
        text=text.replace(old,new)
    text=re.sub(r'(?<=\S) {2,}(?=\S)',' ',text)
    parts[index]=text
body=''.join(parts)
body=body.replace('Đồng bộ tài liệu hiện hành với run/output/schema/runtime mới đã đo; phân biệt history và xác nhận đang chờ. |\n| [scripts/movie_quality',
 'Tạo/kiểm manifest mới có scope/exclusions, bytes/SHA256; không ghi đè manifest cũ. |\n| [scripts/movie_quality')
target.write_text(body,encoding='utf-8')
print('Polished report; original draft preserved:',backup)
