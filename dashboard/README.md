# Movie Analytics Dashboard 1.1

Phiên bản bàn giao: **1.1** (package version: **1.1.0**). Bản này hoàn thiện giao diện và tương tác của tám trang, giữ nguyên dữ liệu và các phép thống kê Spark/PySpark.

Dashboard trình bày kết quả Spark/PySpark đã xuất, bằng React + Vite, JSX, React Router, Recharts và CSS thông thường. Không có backend, API, đăng nhập hoặc huấn luyện mô hình trong frontend.

Tổng quan mới nhất là bố cục duy nhất. Component và liên kết chuyển về Tổng quan V1 đã được loại bỏ; URL cũ có tham số layout không mở lại bố cục cũ.

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
| / | Bốn KPI, điểm nổi bật, hoạt động theo giờ, donut hành vi, Top 5 phim; Biểu đồ/Bảng, CSV và nguồn dữ liệu |
| /phim | Thanh xếp hạng và bảng tối đa 20 phim, nhận xét phim dẫn đầu |
| /the-loai | Chọn Top 5/10/toàn bộ trên biểu đồ; bảng giữ đầy đủ thể loại đã xuất |
| /hanh-vi | Donut tương tác và bảng đủ năm hành động, số lượng và tỷ lệ |
| /thoi-gian | 24 giờ, bảng sự kiện/play/người dùng khác nhau và tóm tắt DAU |
| /thoi-luong | Số bản ghi, trung bình, trung vị, min/max, độ lệch chuẩn của hai nhóm sự kiện |
| /ket-hop | Chọn 00h–23h; Top 3 phim và người dùng khác nhau theo giờ; tra cứu đủ 72 dòng hoặc chỉ giờ đang chọn |
| /phan-cum | Metadata, thử nghiệm K, kích thước/hồ sơ cụm, nhận xét và tra cứu người dùng theo cụm, 20 dòng/trang |

Sidebar luôn có tám đường dẫn. Desktop dùng thanh bên trái; từ 1023px trở xuống dùng menu mở/đóng. Escape đóng menu và trả focus về nút mở. Khi chuyển route, trang cuộn về đầu và focus đến tiêu đề; đổi bộ lọc không làm mất focus. Có liên kết “Đến nội dung chính” khi dùng Tab.

## Dữ liệu và phạm vi

Frontend fetch các bản sao JSON trong public/data. Script scripts/sync-data.mjs chép nguyên nội dung từ ../evidence/week2-tv2/tv2-4ed70c10cd84/dashboard/:

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

Script kiểm tra JSON là mảng không rỗng, báo lỗi khi nguồn thiếu hoặc hỏng, tự chạy trước dev/test/build. Khi dev đang mở, dùng npm.cmd run sync:data rồi tải lại trang. Sau khi clone cần giữ nguyên thư mục evidence tương ứng. public/data, dist, node_modules và .browser-check được bỏ qua bởi .gitignore; không commit các bản sao hoặc tệp sinh tạm.

Dữ liệu hành vi mô phỏng từ 01/09/2026 đến 30/09/2026 theo giờ Việt Nam (UTC+7). JSON theo giờ đã được tổng hợp sẵn; frontend không chuyển múi giờ thêm lần nữa. Nhận xét chỉ mô tả kết quả đã xuất, không đại diện sở thích người xem thật.

### Cách đọc chỉ số

- Tổng sự kiện: cộng count của các hành động. Người dùng khác nhau toàn kỳ: userId phân biệt trong assignments.
- Phiên ghi nhận và phiên có ít nhất một play: cộng sessionCount và playedSessionCount theo người dùng. Phiên phân biệt theo (runId, sessionId) trong từng người dùng. Không dùng số sự kiện play thay số phiên.
- Play có thể lặp lại trong cùng phiên/người dùng. View là xem thông tin phim, không phải phát phim. Tỷ lệ hành động có mẫu số là tổng sự kiện, không phải tổng người dùng.
- Một phim có nhiều thể loại nên một play có thể vào nhiều nhóm. Không cộng nhóm thể loại thành tổng play độc lập.
- Theo giờ: cộng gộp toàn kỳ, không phải một ngày. Người dùng khác nhau theo giờ hoặc phim–giờ được đếm riêng trong từng nhóm; không cộng các nhóm để suy ra tổng người dùng.
- DAU đếm mỗi người có ít nhất một sự kiện một lần/ngày, gồm mọi hành động. Chuỗi hiện có 30 ngày đều 1.000 người/ngày; hiển thị tóm tắt thay biểu đồ lớn. Không cộng DAU các ngày thành người dùng khác nhau toàn kỳ.
- Thời lượng có đơn vị gốc giây, tính theo bản ghi sự kiện. all_events gồm cả thời lượng 0; watch_segments chỉ gồm thời lượng dương và là tập con. Không cộng hai nhóm. Trung vị xấp xỉ; độ lệch chuẩn mẫu. Không suy ra thời lượng mỗi phiên hoặc histogram khi chưa có dữ liệu.
- K-Means chỉ trình bày kết quả Spark đã xử lý. Đặc trưng đọc từ featureColumnsJson; bestK và silhouette đọc từ metadata. Silhouette không có đơn vị, đo phân tách cụm theo squared Euclidean, không chứng minh hành vi người xem thật.
- completionRate là tỷ lệ từ 0–1, nhân 100 khi hiển thị %. Tỷ lệ của người dùng = số phiên có complete / số phiên có play; trung bình cụm là trung bình tỷ lệ người dùng, không phải tổng complete chia tổng play. Người không có phiên play ghi “Chưa xác định” khi tra cứu.
- avgTotalWatchDuration là trung bình tổng thời lượng mỗi người dùng. avgWatchDuration là trung bình các trung bình đoạn xem dương của từng người, bằng 0 nếu không có đoạn xem. Hai chỉ số không thay thế nhau. Giữ nhãn Cluster gốc, không gán nhãn tâm lý/kinh doanh.

Các services kiểm tra nguồn, đơn vị, số đếm và sự nhất quán giữa JSON. Không có số liệu demo hoặc fallback giả. Có trạng thái tải, thiếu dữ liệu, JSON hỏng và nút thử lại.

## Giao diện và tương tác

Tám trang dùng cùng typography, phạm vi dữ liệu, màu nhấn, thẻ, bảng và định dạng số tiếng Việt. Thông tin chính luôn hiển thị; diễn giải dài nằm trong “Cách đọc số liệu”, mở/đóng được bằng Enter hoặc phím cách.

- Biểu đồ giờ: hover để highlight; click/chạm lấy giờ trực tiếp từ cột. Tab vào biểu đồ, dùng ←/→, Home/End; Escape bỏ highlight. Số liệu ở vùng đọc cố định, không che cột.
- Donut: hover/focus là xem tạm; click/chạm hoặc Enter/phím cách giữ lựa chọn. Mũi tên/Home/End chuyển giữa các hành động. Escape bỏ highlight. Giữ lựa chọn khi đổi Biểu đồ/Bảng ở Tổng quan.
- Phim/thể loại/phim–giờ dùng lại thanh xếp hạng HTML/CSS của Tổng quan, tên đầy đủ và số sự kiện gốc. Hover/Tab làm nổi bật từng dòng. Danh sách dài cuộn trong khung, mọi dòng vẫn truy cập được.
- K-Means dùng một đơn vị/trục riêng cho mỗi chỉ số. Biểu đồ đọc trực tiếp hồ sơ cụm, hỗ trợ hover, click/chạm và mũi tên/Home/End/Escape; không có scatter hay phép chiếu giả.
- Bảng rộng có vùng cuộn và hướng dẫn khi cần. Tab đến vùng bảng rồi dùng ←/→; Home/End đến cột đầu/cuối khi có cuộn ngang, nếu không thì giữ cuộn dọc mặc định. Bảng dài có cuộn riêng và tiêu đề cột cố định; bảng người dùng giữ mã người dùng bên trái.
- Tìm userId hoặc đổi cụm trở về trang 1. Không gán lại cụm hoặc thay đổi kết quả mô hình.

CSV chỉ có ở ba phần Tổng quan, giữ đúng 24/5/5 dòng đang trình bày. UTF-8 có BOM; số gốc chưa làm tròn. Tên có dấu phẩy/nháy/xuống dòng được thoát đúng; chuỗi có thể là công thức bảng tính được trung hòa. Dùng chức năng nhập CSV nếu bảng tính mặc định dùng dấu chấm phẩy.

## Cấu trúc và kiểm thử

- src/pages/: tám chức năng; AnalysisPage dùng cấu hình cho phim, hành vi và thời gian.
- src/components/: header/thẻ/bảng/hướng dẫn và biểu đồ tái sử dụng. OverviewMovieRanking dùng cả Tổng quan và trang xếp hạng; OverviewActionDonut và OverviewHourlyChart dùng chung với trang chi tiết. ComparisonBarChart dùng chung cho bốn biểu đồ K-Means.
- src/styles/: global.css cho shell; overview.css cho hệ thống trình bày mới; analysis.css cho bố cục chi tiết.
- src/services/: đọc và kiểm tra JSON, định dạng và chuẩn bị thống kê. Các phép tính phân tích giữ nguyên.
- scripts/: đồng bộ JSON và kiểm tra Edge.
- tests/: đối chiếu nguồn JSON thực tế, kiểm tra thống kê, bộ lọc và từ chối dữ liệu lỗi.

npm.cmd test chạy unit test; npm.cmd run build tạo production build. node scripts/check-ui.mjs dùng Edge có sẵn trên Windows, không cài thư viện trình duyệt:

- Kiểm tra tám route ở 1440/768/390/320px, menu, Back, focus, bàn phím và cảm ứng mô phỏng.
- Đối chiếu bảng/biểu đồ/nhận xét/bộ lọc với JSON, ba CSV tải thật, tìm kiếm/lọc/phân trang K-Means.
- Kiểm tra tải chậm, dữ liệu trống, JSON hỏng, thử lại và không tràn ngang toàn trang.
- Kiểm tra URL cũ không phục hồi giao diện Tổng quan cũ.
- Ảnh, profile và tệp tải thử nằm trong .browser-check, được Git bỏ qua.

Có thể giới hạn bằng --width=320 hoặc --route=/phan-cum. Kiểm tra thêm trực quan với Device Toolbar ở bốn kích thước trên, và thiết bị cảm ứng/trình đọc màn hình thật nếu có.
