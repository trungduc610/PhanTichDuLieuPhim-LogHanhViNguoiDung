# Phạm vi công bố lên GitHub

Repository: [trungduc610/PhanTichDuLieuPhim-LogHanhViNguoiDung](https://github.com/trungduc610/PhanTichDuLieuPhim-LogHanhViNguoiDung). Branch công bố: `codex/week2-tv1-hdfs`. Người dùng đã cho phép commit/push branch này; không merge vào main. Tài liệu lập ngày 12/10/2026, cho các thay đổi Tuần 1 và TV1 Tuần 2 đã có trong checkout.

## Nội dung được công bố

- Source, scripts, tests và schema dùng chung: chuẩn hóa metadata, sinh log synthetic, Flume runner/reconciliation, Spark full QA, HDFS deployment/import/hash/restart/guards và manifest verification.
- Dockerfile, Compose Flume/Spark, `compose.hdfs.yaml`, cấu hình Flume logging/heap và Hadoop XML/entrypoint. HDFS demo gồm một NameNode, một DataNode, replication 1; không HA/dự phòng.
- README, tài liệu dataset/schema/pipeline, báo cáo nghiệm thu Tuần 1 và TV1 Tuần 2, hợp đồng tích hợp TV2, sơ đồ kiến trúc và điều kiện xác nhận nhóm chưa có.
- Bằng chứng nhẹ trong các audit/evidence lịch sử: JSON, log văn bản, command records, source snapshots, manifest, samples synthetic nhỏ và ảnh UI thực. Giữ nguyên cả FAIL/BLOCKED, các lỗi verifier và kết quả sửa lại; không công bố chỉ các PASS.

Staging dùng danh sách đường dẫn cụ thể đã kiểm kích thước/nội dung/bí mật, không dùng `git add .` hoặc `git add -A`. Tệp mới được chọn không vượt 2 MiB/tệp; không có file lớn trên 50 MiB đang tracked cần xử lý. Phạm vi cuối gồm 1.021 tệp thay đổi so với main, khoảng 5,40 MB byte local: lượt đầu 1.018 tệp, sau đó bổ sung ba `source-snapshot/Dockerfile` của các run Flume và cập nhật tài liệu này bằng commit tiếp theo. Không viết lại commit đã push. Tổng staged thực tế và SHA commit được ghi trong audit công bố local; xem toàn bộ file list bằng `git diff --stat main...codex/week2-tv1-hdfs`.

## Dữ liệu và bằng chứng giữ local

Không đưa nội dung `data/raw/`, `data/processed/`, `data/generated/`, `data/runs/` hoặc `logs/` lên Git mới; các `.gitkeep` từ lịch sử vẫn giữ. Không đưa full Sink, spool/tracker, File Channel/checkpoints, Docker volume metadata/blocks, cache, SQLite, fixture/tạm, CA bundle, private key, `.env` chứa bí mật hoặc `stdout.bin` vào commit. Audit của chính lượt công bố giữ local để tránh tự ghi staged diff/commit receipt vào commit đang tạo. Không cài hoặc chuyển sang Git LFS, không rewrite history.

| Artifact local quan trọng | Dung lượng/nội dung | Lý do giữ local |
|---|---|---|
| `data/raw/` | MovieLens ZIP 978.202 byte, CSV/README/license/download manifest | Không công bố lại full dataset; giữ nguồn, license và snapshot |
| `data/processed/movies.csv` | 533.347 byte; 9.742 phim | Cùng phạm vi dữ liệu bàn giao local, kiểm bằng hash |
| `data/generated/main.jsonl` | 343.339.148 byte; 1.000.000 synthetic events | Vượt giới hạn file Git thông thường; không phải output Flume |
| `data/generated/demo.jsonl` | 3.433.123 byte; 10.000 synthetic events | Không publish full event stream |
| `data/runs/run-aa6b9eb58dca/output/` | 15 part Sink thật; tổng 343.339.148 byte | Full output được giữ local/HDFS, không publish dataset lên Git |
| `evidence/week2-hdfs/hdfs-385a18d3f03a/commands/cat-*/stdout.bin` | Hai lượt đọc byte toàn lô, mỗi lượt 343.872.495 byte | Binary byte streams để chứng minh đối chiếu; JSON/log kết quả đã công bố |
| Spool/channel và named volumes | Trạng thái vận hành, bản copy input và blocks | Không phải source/bằng chứng nhẹ; không portable trong Git |

Các dữ liệu này không bị xóa, sửa hoặc ghi đè. Việc bỏ khỏi staging không thay đổi manifest hoặc nghiệm thu local.

## Manifest và ý nghĩa của clone GitHub

Manifest Tuần 1 `evidence/recheck-20261011-221710/delivery_manifest.json` có 344 mục; manifest HDFS `evidence/week2-hdfs/hdfs-385a18d3f03a/delivery_manifest.json` có 820 mục. **Hai manifest giữ nguyên byte**, gồm cả tham chiếu tới dataset, binary streams và các artifact local khác theo scope/exclusions đã nghiệm thu. Không sửa manifest để tạo PASS cho bản clone thiếu dữ liệu.

**Clone GitHub là bản source và bằng chứng nhẹ, không phải bộ bàn giao dữ liệu đầy đủ.** Các file audit/JSON có thể chứa đường dẫn tuyệt đối và revision/giờ của máy thực nghiệm trước commit; đó là dấu vết lịch sử, không phải thông tin runtime của máy clone. Link tuyệt đối trong audit có thể không mở được trên máy khác; tìm tệp tương ứng theo đường dẫn trong repository.

Git có `core.autocrlf=true` ở máy công bố và `.gitattributes` quy định LF cho `.py/.sh/.conf`; một số text được chuẩn hóa newline trong Git blob. SHA256 manifest là **byte local đã nghiệm thu**, không bảo đảm SHA256 của mọi text trong clone mới giống khi Git đổi newline. Kiểm local manifests tại checkout gốc trước và sau staging/commit; không coi Git blob SHA là SHA256 nội dung. Để bàn giao dữ liệu đầy đủ, sao chép độc lập các artifact đúng manifest từ checkout gốc và kiểm SHA256, hoặc tái tạo vào đường dẫn mới rồi nghiệm thu lượt mới. Không gửi dữ liệu qua dịch vụ khác trong lượt công bố này.

## Kiểm chứng và tái tạo

Scripts host dùng Python >=3.10/std library. Spark 3.5.1/Python 3.8.10/Java 11 và Hadoop client 3.3.4 được kiểm trong container ở lượt nghiệm thu; HDFS server 3.3.6. Chạy tại root project với executable Python thực:

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/create_delivery_manifest.py --verify evidence/recheck-20261011-221710/delivery_manifest.json
python -B scripts/create_hdfs_manifest.py --verify evidence/week2-hdfs/hdfs-385a18d3f03a/delivery_manifest.json
```

Hai lệnh manifest chỉ đạt khi các file local đúng snapshot có đủ; FAIL do missing file trên clone source là kết quả dự kiến, không sửa expected để che thiếu dữ liệu. Metadata SHA256 `1df01064e7a0680e11dc93a57d10782a59323716596440244f9e6200c2925536`; main input SHA256 `c89a753a83a7f194992f7e1c75eddc0c326f1e560c4e436de17b66865377eefd`. SHA256 từng Sink và mapping HDFS nằm trong source manifest/reconciliation.

Muốn tái tạo trên máy mới: dùng `download_dataset.py`, `prepare_movies.py`, `generate_logs.py` với output/report mới; đối chiếu snapshot MovieLens (ZIP SHA256 `696d65a3dfceac7c45750ad32df2c259311949efec81f0f144fdfb91ebc9e436`), seed/tham số trong manifest nguồn. Chạy demo Flume trước main theo README; giữ run/project/output/evidence mới, không giả generated input là Sink. Chạy `run_hdfs.py --flume-run-id <run-PASS> --audit-dir <audit-dir-mới>` để có cluster/import/namespace mới trống, nhập chính Sink đã kiểm bằng `hdfs_io.py`, đọc byte SHA256 và full Spark QA. Việc này là một lượt thực nghiệm mới, không phục dựng giả lịch sử hoặc format volume cũ.

Để kiểm HDFS hiện hữu tại máy gốc, dùng URI và lệnh có report tên mới trong [hợp đồng TV2](week2_tv2_hdfs_handoff.md), job `hdfs_hash_verify.py` và `spark_hdfs_validate.py`. HDFS URI chỉ dùng trong Docker network của project; các receipt đã publish chứng minh lần chạy được ghi, không tự bảo đảm cluster hiện đang hoạt động. Lượt commit/push này không chạy pipeline hoặc điều khiển container.

Kết quả TV1 Tuần 2 là 10/10 nhiệm vụ kỹ thuật; chưa có xác nhận TV2/nhóm. Điều kiện xác nhận kiến trúc và giới thiệu/cơ sở lý thuyết Tuần 1 vẫn thiếu. Tiền xử lý chuyên sâu, phân tích, K-Means/dashboard là phần tiếp theo; không công bố toàn bộ Tuần 2 đã hoàn thành.
