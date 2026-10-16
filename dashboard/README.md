# Movie Analytics Dashboard 1.1

Phiên bản bàn giao: **1.1** (package version: **1.1.0**). Bản này hoàn thiện giao diện và tương tác của tám trang, giữ nguyên dữ liệu và các phép thống kê Spark/PySpark.

Dashboard trình bày kết quả Spark/PySpark đã xuất, bằng React + Vite, JSX, React Router, Recharts và CSS thông thường. Không có backend, API, đăng nhập hoặc huấn luyện mô hình trong frontend.

Tổng quan mới nhất là bố cục duy nhất. Component và liên kết chuyển về Tổng quan V1 đã được loại bỏ; URL cũ có tham số layout không mở lại bố cục cũ.

## UX và nội dung Dashboard

Tổng quan ưu tiên ba chỉ số: **Tổng số hành động**, **Số người dùng**, **Lượt phát phim**. Hai số đếm phiên vẫn xem được khi mở “Hiểu thêm về phiên sử dụng”. Không đổi công thức hoặc nguồn dữ liệu; lượt phát lấy đúng số hành động `play`, không thay bằng số phiên có phát.

Nội dung có ba lớp: kết quả chính luôn hiện; “Giải thích”/“Giải thích dữ liệu” nêu ý nghĩa và cách đếm; “Chi tiết kỹ thuật” cùng “Tìm hiểu dữ liệu và phương pháp phân tích” chứa trường, file nguồn, luồng Flume/HDFS/Spark và giới hạn. “Hướng dẫn thao tác” tách riêng khỏi phần giải thích dữ liệu. Các mục mở rộng dùng bàn phím được. Bảng ưu tiên tên tiếng Việt; CSV vẫn giữ mã action và giá trị gốc.

Quy chuẩn chung của tám trang: [UX_CONTENT_GUIDELINES.md](docs/UX_CONTENT_GUIDELINES.md). Định nghĩa nằm ở `src/content/overviewContent.js`; `MetricExplanation` dùng cho các KPI, `AnalysisExplanation` dùng cho trang chi tiết. CSS giới hạn ở `.overview-home`, `.detail-ux` và `.advanced-ux` để giữ phạm vi trình bày. Các trang dùng thống nhất thuật ngữ, đơn vị, định dạng số và phần giải thích chủ động mở.

Các mục mở rộng dùng mũi tên phải/xuống theo trạng thái thực của từng mục. `IndependentDisclosure` đưa phần giải thích dài ra vùng riêng dưới nhóm KPI hoặc biểu đồ, cho phép mở nhiều mục mà không kéo cao các card; nút Đóng trả focus về nút mở. Donut và chú giải xếp cạnh nhau khi đủ chỗ, xếp dọc khi hẹp. “Cơ cấu hành động được ghi nhận” tính tỷ lệ trên tổng hành động; nhãn “Log hành vi mô phỏng” phân biệt với thông tin phim MovieLens.

## Chạy bằng VS Code

Mở Terminal → New Terminal tại repository:

```powershell
cd dashboard
npm.cmd ci
npm.cmd run dev
```

Mở URL Local Vite in ra, thường http://localhost:5173. Dùng Ctrl+C để dừng. Trên PowerShell dùng npm.cmd để tránh bị chặn npm.ps1; không cần thay đổi Execution Policy. Chỉ cần npm.cmd ci khi mới clone hoặc chưa có dependencies.

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run preview
```

Preview dùng bản build đã tạo, thường tại http://localhost:4173. Nếu dữ liệu thay đổi, chạy build lại trước preview.

## Tám trang

| Đường dẫn | Nội dung |
| --- | --- |
| / | Ba KPI chính, hai số đếm phiên trong phần mở rộng, kết quả nổi bật, ba biểu đồ/Bảng/CSV và ba lớp giải thích |
| /phim | Xếp hạng tối đa 20 phim, tìm tên, phân trang, CSV và nhận xét phim dẫn đầu |
| /the-loai | Chọn Top 5/10/toàn bộ trên biểu đồ; bảng giữ đầy đủ thể loại đã xuất |
| /hanh-vi | Donut tương tác và bảng đủ năm hành động, số lượng và tỷ lệ |
| /thoi-gian | Hành động cộng gộp theo giờ, người dùng duy nhất trong giờ, DAU theo ngày và CSV |
| /thoi-luong | Thống kê hai nhóm bản ghi, chọn chỉ số trên biểu đồ và CSV; không phải thời lượng phiên |
| /ket-hop | Top 3 phim mỗi giờ, lượt phát/người dùng trong nhóm; lọc giờ, tìm tên, phân trang và CSV |
| /phan-cum | Phân nhóm người dùng: quy mô/hồ sơ, K-Means và Silhouette; tra cứu theo mã/cụm, 20 dòng/trang và CSV |

Sidebar luôn có tám đường dẫn. Desktop dùng thanh bên trái; từ 1023px trở xuống dùng menu mở/đóng. Escape đóng menu và trả focus về nút mở. Khi chuyển route, trang cuộn về đầu và focus đến tiêu đề; đổi bộ lọc không làm mất focus. Có liên kết “Đến nội dung chính” khi dùng Tab.

## Dữ liệu và phạm vi

Nguồn chính thức là **TV2 Week 3 final run `tv2-aae83326c1ab`**, tại `evidence/week3-tv2/tv2-aae83326c1ab/`. Các run Week 2 và các attempt Week 3 khác chỉ là lịch sử. Giữ phiên bản Dashboard **1.1.0**.

Frontend đọc snapshot trong `public/data/<runId>/`, chọn bằng `public/data/source.json`. Cấu hình `data-source.json` ghi run và `evidenceRoot`. Script `scripts/sync-data.mjs` đọc `handoff.json`, kiểm SHA-256 của chín biên nhận PASS, identity/provenance HDFS, manifest nguồn, raw trước/sau và hash code đã chạy. Với từng JSON cần dùng, script đối chiếu đúng `local_path`, HDFS URI, `local_bytes`, `local_sha256`, schema (tên trường, kiểu, nullable) và `rows/read_back_rows`. Các tổng sự kiện/play/thời lượng, DAU, mô hình và trung bình hồ sơ cụm được đối chiếu thêm giữa các bảng.

Handoff liệt kê 12 bảng JSON; Dashboard chỉ đọc **11 JSON** dưới đây. `kmeans_user_features.json` không được chép vì assignments đã chứa các trường mà giao diện cần. Không đổi cấu trúc JSON và không trộn run.

- stats_action_distribution.json
- stats_top_movies_by_play.json
- stats_top_genres.json
- stats_hourly_activity.json
- stats_daily_active_users.json
- stats_watch_duration_summary.json
- stats_user_movie_time.json
- kmeans_model_metadata.json
- kmeans_k_search.json
- kmeans_cluster_profiles.json
- kmeans_assignments.json

```powershell
# Tại dashboard/, không cần Docker, HDFS hoặc Spark đang chạy
npm.cmd run sync:data
npm.cmd test
npm.cmd run build
npm.cmd run dev
```

Lần chuyển nguồn đầu tiên dùng `node scripts/sync-data.mjs --run tv2-aae83326c1ab`. Selector frontend và cấu hình chọn run chỉ được cập nhật sau khi cả 11 file được xác minh và chép thành công. Chạy lại với snapshot đúng hash là an toàn; snapshot thiếu file hoặc sai hash bị từ chối, không ghi đè. Không có fallback về run cũ khi nguồn lỗi.

Script tự chạy trước dev/test/build. Khi dev đang mở, chạy `npm.cmd run sync:data` rồi tải lại trang. `public/data`, `dist`, `node_modules` và `.browser-check` được Git bỏ qua; không commit các bản sao hoặc tệp sinh tạm.

### Evidence cần giữ sau khi clone

Giữ nguyên final-run directory, tối thiểu gồm:

- `handoff.json` và 11 JSON trong `dashboard/` đã liệt kê.
- `run_context.json`, `source_manifest.json`, `output_manifest.json`, `raw-before.json`, `raw-after.json`.
- Chín biên nhận được niêm phong trong `handoff.validation_receipts`: `run_status.json`, `pipeline_summary.json`, `input-hdfs-qa.json`, `spark-fixture-tests.json`, `runtime-verification.json`, `result-verification.json`, `raw-preservation.json`, `host-tests-final.json`, `historical-preservation-after.json`.
- Thư mục `source-snapshot/` chứa các file được `run_context.code_hashes` tham chiếu. Script kiểm hash chính xác trên bản chụp đã chạy, không phụ thuộc code pipeline hiện tại, không chạy các file này. Hai snapshot `compose.tv2.yaml` và `Dockerfile.tv2` giữ CRLF theo biên nhận.

Thiếu file, JSON hỏng, sai hash/byte/schema/row count hoặc biên nhận không PASS sẽ dừng sync với tên file/nguyên nhân. Kiểm tra bộ evidence bàn giao và khôi phục đúng byte từ nguồn có thẩm quyền; không sửa số liệu, hash trong handoff hay bỏ kiểm chứng để chạy web. Không dùng bản sao cũ để che lỗi. Đặc biệt tránh công cụ tự đổi xuống dòng: JSON/biên nhận phải giữ byte gốc; CSV bàn giao dùng CRLF. Không cần copy dữ liệu thủ công hoặc khởi động lại pipeline.

Các quy tắc riêng của final run trong `.gitattributes` giữ nguyên byte mặc định, với ngoại lệ CRLF cho CSV, `source_manifest.json`, hai snapshot cấu hình và bốn file stdout/stderr đã được đo bằng CRLF. Giữ các ngoại lệ này khi clone trên Windows/Linux; không tự chuyển toàn bộ evidence sang một kiểu xuống dòng.

`generatedAt` là lúc pipeline hoàn tất; `verifiedAt` là lúc runner hoàn tất theo `run_status.json`, không phải giờ chạy sync. `releasedAt` lấy từ handoff. Run Flume/HDFS, timezone, khoảng ngày và hash từng file đều lấy từ evidence tương ứng; việc sync không tạo biên nhận thực nghiệm mới.

Dữ liệu hành vi mô phỏng từ 01/09/2026 đến 30/09/2026 theo giờ Việt Nam (UTC+7). JSON theo giờ đã được tổng hợp sẵn; frontend không chuyển múi giờ thêm lần nữa. Nhận xét chỉ mô tả kết quả đã xuất, không đại diện sở thích người xem thật.

### Cách đọc chỉ số

- Tổng sự kiện: cộng count của các hành động. Người dùng khác nhau toàn kỳ: userId phân biệt trong assignments.
- Phiên ghi nhận và phiên có ít nhất một play: cộng sessionCount và playedSessionCount theo người dùng. Phiên phân biệt theo (runId, sessionId) trong từng người dùng. Không dùng số sự kiện play thay số phiên.
- Play có thể lặp lại trong cùng phiên/người dùng. View là xem thông tin phim, không phải phát phim. Tỷ lệ hành động có mẫu số là tổng sự kiện, không phải tổng người dùng.
- Một phim có nhiều thể loại nên một play có thể vào nhiều nhóm. Không cộng nhóm thể loại thành tổng play độc lập.
- Theo giờ: cộng gộp toàn kỳ, không phải một ngày. Người dùng khác nhau theo giờ hoặc phim–giờ được đếm riêng trong từng nhóm; không cộng các nhóm để suy ra tổng người dùng.
- DAU đếm mỗi người có ít nhất một sự kiện một lần/ngày, gồm mọi hành động. Chuỗi hiện có 30 ngày đều 1.000 người/ngày; biểu đồ đường và bảng DAU giữ số liệu theo ngày, hỗ trợ bàn phím. Không cộng DAU các ngày thành người dùng khác nhau toàn kỳ.
- Thời lượng có đơn vị gốc giây, tính theo bản ghi sự kiện. all_events gồm cả thời lượng 0; watch_segments chỉ gồm thời lượng dương và là tập con. Không cộng hai nhóm. Trung vị xấp xỉ; độ lệch chuẩn mẫu. Biểu đồ so sánh chọn trung bình, trung vị, min/max hoặc độ lệch chuẩn bằng giây; không suy ra thời lượng mỗi phiên hoặc histogram khi chưa có dữ liệu.
- K-Means chỉ trình bày kết quả Spark đã xử lý. Đặc trưng đọc từ featureColumnsJson; bestK và silhouette đọc từ metadata. Silhouette không có đơn vị, đo phân tách cụm theo squared Euclidean, không chứng minh hành vi người xem thật.
- completionRate là tỷ lệ từ 0–1, nhân 100 khi hiển thị %. Tỷ lệ của người dùng = số phiên có complete / số phiên có play; trung bình cụm là trung bình tỷ lệ người dùng, không phải tổng complete chia tổng play. Người không có phiên play ghi “Chưa xác định” khi tra cứu.
- avgTotalWatchDuration là trung bình tổng thời lượng mỗi người dùng. avgWatchDuration là trung bình các trung bình đoạn xem dương của từng người, bằng 0 nếu không có đoạn xem. Hai chỉ số không thay thế nhau. Hiển thị “Cụm + mã”, giữ mã gốc trong CSV, không gán nhãn tâm lý/kinh doanh.

Các services kiểm tra nguồn, đơn vị, số đếm và sự nhất quán giữa JSON. Không có số liệu demo hoặc fallback giả. Có trạng thái tải, thiếu dữ liệu, JSON hỏng và nút thử lại. Metadata nguồn thiếu/hỏng chặn hiển thị; hiển thị run, thời điểm xác minh và cảnh báo snapshot cũ sau 24 giờ.

## Giao diện và tương tác

Tám trang dùng cùng typography, phạm vi dữ liệu, màu nhấn, thẻ, bảng và định dạng số tiếng Việt. Thông tin chính luôn hiển thị; diễn giải dài nằm trong “Giải thích dữ liệu” với “Chi tiết kỹ thuật” lồng bên trong. “Hướng dẫn thao tác” là mục riêng. Các mục mở/đóng bằng Enter hoặc phím cách, mũi tên theo đúng trạng thái từng mục; phần giải thích độc lập không kéo giãn card bên cạnh.

- Biểu đồ giờ: hover để highlight; click/chạm lấy giờ trực tiếp từ cột. Tab vào biểu đồ, dùng ←/→, Home/End; Escape bỏ highlight. Số liệu ở vùng đọc cố định, không che cột.
- Donut: hover/focus là xem tạm; click/chạm hoặc Enter/phím cách giữ lựa chọn. Mũi tên/Home/End chuyển giữa các hành động. Escape bỏ highlight. Giữ lựa chọn khi đổi Biểu đồ/Bảng ở Tổng quan.
- Phim/thể loại/phim–giờ dùng lại thanh xếp hạng HTML/CSS của Tổng quan, tên đầy đủ và số sự kiện gốc. Hover/Tab làm nổi bật từng dòng. Danh sách dài cuộn trong khung, mọi dòng vẫn truy cập được.
- K-Means dùng một đơn vị/trục riêng cho mỗi chỉ số. Biểu đồ đọc trực tiếp hồ sơ cụm, hỗ trợ hover, click/chạm và mũi tên/Home/End/Escape; không có scatter hay phép chiếu giả.
- Bảng rộng có vùng cuộn và hướng dẫn khi cần. Tab đến vùng bảng rồi dùng ←/→; Home/End đến cột đầu/cuối khi có cuộn ngang, nếu không thì giữ cuộn dọc mặc định. Bảng dài có cuộn riêng và tiêu đề cột cố định; bảng người dùng giữ mã người dùng bên trái.
- Tìm userId hoặc đổi cụm trở về trang 1. Không gán lại cụm hoặc thay đổi kết quả mô hình.

CSV Tổng quan giữ đúng 24/5/5 dòng đang trình bày. Trang phim xuất mọi dòng khớp tìm tên, giữ hạng gốc. Thể loại, hành vi và giờ giữ đầy đủ bảng đã xuất. Thời lượng giữ cả hai nhóm, độc lập chỉ số đang chọn. Trang kết hợp và tra cứu người dùng xuất mọi dòng khớp bộ lọc, kể cả các trang chưa hiển thị. Không có kết quả thì vô hiệu hóa nút tải. Tỷ lệ phiên trong CSV người dùng giữ giá trị 0–1, cờ xác định và số phiên tử/mẫu.

CSV dùng UTF-8 có BOM và số gốc chưa làm tròn. Tên có dấu phẩy/nháy/xuống dòng được thoát đúng; chuỗi có thể là công thức bảng tính được trung hòa. Dùng chức năng nhập CSV nếu bảng tính mặc định dùng dấu chấm phẩy.

## Cấu trúc và kiểm thử

- src/pages/: tám chức năng; AnalysisPage dùng cấu hình cho phim, hành vi và thời gian.
- src/components/: header/thẻ/bảng/hướng dẫn và biểu đồ tái sử dụng. OverviewMovieRanking dùng cả Tổng quan và trang xếp hạng; OverviewActionDonut và OverviewHourlyChart dùng chung với trang chi tiết. ComparisonBarChart dùng chung cho bốn biểu đồ K-Means.
- src/styles/: global.css cho shell; overview.css cho hệ thống trình bày mới; analysis.css cho bố cục chi tiết.
- src/services/: đọc và kiểm tra JSON, định dạng và chuẩn bị thống kê. Các phép tính phân tích giữ nguyên.
- scripts/: đồng bộ JSON và kiểm tra Edge.
- tests/: đối chiếu nguồn JSON thực tế, kiểm tra thống kê, bộ lọc và từ chối dữ liệu lỗi.

npm.cmd test chạy unit test; npm.cmd run build tạo production build. node scripts/check-ui.mjs dùng Edge có sẵn trên Windows, không cài thư viện trình duyệt:

- Kiểm tra tám route ở 1440/768/390/320px, menu, Back, focus, bàn phím và cảm ứng mô phỏng.
- Đối chiếu bảng/biểu đồ/nhận xét/bộ lọc với JSON; tải và kiểm tra CSV thực ở cả tám trang, gồm phạm vi lọc và các trang chưa hiển thị.
- Kiểm tra giải thích đóng/mở độc lập, mục kỹ thuật lồng nhau, ký hiệu trạng thái, trả focus và chiều cao card khi mở; kiểm cả chiều rộng viewport thực trên mobile.
- Kiểm tra tải chậm, dữ liệu trống, JSON hỏng, thử lại và không tràn ngang toàn trang.
- Kiểm tra URL cũ không phục hồi giao diện Tổng quan cũ.
- Ảnh, profile và tệp tải thử nằm trong .browser-check, được Git bỏ qua.

Có thể giới hạn bằng `--width=320`, `--route=/phan-cum`, `--detail-pages` (bốn trang đợt 1) hoặc `--advanced-pages` (ba trang đợt 2). Không truyền tham số để kiểm toàn bộ tám route ở bốn kích thước. Kiểm tra thêm trực quan với Device Toolbar, thiết bị cảm ứng/trình đọc màn hình thật nếu có. Cảnh báo bundle lớn hơn 500 kB được giữ để theo dõi; không tự tái cấu trúc chỉ để xóa cảnh báo.
