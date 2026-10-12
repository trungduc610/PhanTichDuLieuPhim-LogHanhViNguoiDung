"""Correct binary-image references in the newly authored, unfrozen report."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from hdfs_common import new_json
from common import sha256,utcnow
report=AUDIT/'bao-cao-nghiem-thu-tv1-tuan-2-hdfs.md'
before=sha256(report)
body=report.read_text(encoding='utf-8').replace('.jpg:1)','.jpg)')
needle='| Xác nhận nhóm/TV2 chưa có |'
row='| Kiểm link ban đầu thử đọc JPEG như văn bản UTF-8 do link ảnh có :1 | Giữ failed wrapper delivery-paths; sửa link ảnh không dùng số dòng, chạy lại kiểm mọi link. Một câu lệnh chỉnh helper trước đó bị PowerShell ParserError trước thực thi, không thay file hay chạy Docker | Lỗi đóng gói tài liệu đã xử lý; không ảnh hưởng source/data/runtime |\n'
assert needle in body
body=body.replace(needle,row+needle)
report.write_text(body,encoding='utf-8')
new_json(AUDIT/'report-links-revision.json',{'edited_at_utc':utcnow(),'report':str(report),
    'before_sha256':before,'after_sha256':sha256(report),
    'reason':'Binary screenshot links have no source line numbers; record packaging verifier error. This is a new unfrozen Week 2 report; no historical report/data/status was modified.',
    'affected_recheck':'check_delivery.py; no data/config/job changes'})
print('Corrected new report image links; preserved failed verification log and report revision hashes')
