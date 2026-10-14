# Movie Analytics Dashboard

Điều hướng ở thanh bên trái trên desktop; màn hình nhỏ dùng nút “Mở menu”/“Đóng menu”, tự thu gọn khi chọn trang. Các đường dẫn hiện có được giữ nguyên. Trang phân cụm có KPI “Người dùng được phân cụm” đọc từ metadata, ba biểu đồ thanh nhóm so sánh play/phim/phiên bằng trục riêng cho từng đơn vị và bảng tra cứu có hướng dẫn cuộn ngang rõ ràng. Biểu đồ lấy trực tiếp các trung bình từ hồ sơ cụm; không đổi cách tính Spark.

Ứng dụng React + Vite, JavaScript/JSX, React Router, Recharts và CSS thông thường. Chưa có backend hoặc API.

## Chạy bằng VS Code

Trang thời gian có ghi chú DAU từ JSON: đếm người dùng khác nhau có sự kiện trong từng ngày (mọi hành động). Chuỗi hiện gồm 30 ngày đều có 1.000 người/ngày nên không cần biểu đồ hoặc cộng các ngày thành tổng người dùng toàn kỳ.

Mở repository trong VS Code, chọn Terminal → New Terminal (PowerShell):

```powershell
cd dashboard
npm.cmd ci
npm.cmd run dev
```

Mở URL Vite in trong Terminal (thường là http://localhost:5173). Dùng Ctrl+C để dừng. Dùng `npm.cmd` để tránh lỗi PowerShell chặn `npm.ps1`; không cần thay đổi Execution Policy.

```powershell
npm.cmd run build
npm.cmd run preview
npm.cmd test
```

`preview` phục vụ bản build tại URL được in trong Terminal (thường http://localhost:4173). Sau khi dữ liệu thay đổi, chạy lại build trước preview.

## Dữ liệu

`scripts/sync-data.mjs` đọc mười một tệp từ `../evidence/week2-tv2/tv2-4ed70c10cd84/dashboard/` và chép nguyên nội dung sang `public/data/`:

- `stats_action_distribution.json`
- `kmeans_assignments.json`
- `stats_hourly_activity.json`
- `stats_daily_active_users.json`
- `stats_top_movies_by_play.json`
- `stats_top_genres.json`
- `stats_watch_duration_summary.json`
- `stats_user_movie_time.json`
- `kmeans_model_metadata.json`
- `kmeans_k_search.json`
- `kmeans_cluster_profiles.json`

Script kiểm tra JSON là mảng không rỗng và báo lỗi nếu nguồn thiếu/hỏng. Tự chạy trước `dev`, `test` và `build`; cũng có thể chạy `npm.cmd run sync:data` khi dev đang mở, rồi tải lại trang. Sau khi clone, chạy `npm.cmd ci` trong dashboard để cài đúng package-lock; các JSON nguồn đã nằm trong evidence của repository. Không chỉnh sửa evidence hoặc chạy pipeline. Các bản sao JSON và thư mục build/node_modules được bỏ qua bởi `.gitignore` trong dashboard.

Frontend dùng fetch đọc `/data/*.json`. `services/overviewMetrics.js` tính:

- Tổng sự kiện: cộng `count` của tất cả action.
- Người dùng khác nhau: tập hợp `userId` của assignments.
- Phiên được ghi nhận: cộng `sessionCount` theo người dùng.
- Phiên có ít nhất một play: cộng `playedSessionCount` theo người dùng.

Phiên trong nguồn được đếm theo `(runId, sessionId)` trong từng người dùng; tổng phiên ở đây là tổng các số đếm đó. Không dùng số sự kiện play để thay cho số phiên. Kiểm tra số đếm hợp lệ, userId trùng, và tổng eventCount trong assignments khớp tổng action để tránh hiển thị dữ liệu không nhất quán. Không có số liệu giả/fallback. Có trạng thái tải, thiếu dữ liệu, lỗi JSON và nút thử lại.

## Cấu trúc

- `src/components/`: MetricCard tái sử dụng.
- `src/pages/`: trang Tổng quan.
- `src/services/`: đọc JSON, kiểm tra và tính chỉ số.
- `src/styles/`: CSS và bố cục responsive.
- `scripts/`: đồng bộ dữ liệu.
- `tests/`: kiểm tra cách tính trên JSON thực tế và từ chối dữ liệu lỗi.

Trang Tổng quan có bốn chỉ số và ba biểu đồ tóm tắt, không có bảng đầy đủ. Liên kết "Xem chi tiết" và thanh điều hướng dẫn đến:

- `/phim`: xếp hạng và bảng tối đa 20 phim trong JSON.
- `/phan-cum`: tổng quan K-Means, đặc trưng từ metadata, bảng K=2..6, số người dùng/hồ sơ từng cụm, nhận xét và tra cứu userId theo cụm với 20 dòng/trang.

Trang phân cụm chỉ đọc bốn JSON K-Means đã xuất (assignments đã có trong cơ chế đồng bộ). `clustering.js` kiểm tra metadata, silhouette, số cụm, tổng người dùng và số người dùng từng cụm giữa các nguồn; giữ nguyên các trung bình trong profiles. Tỷ lệ hoàn thành được nhân 100 để hiển thị %, không tính lại từ tổng complete/play. Tổng thời lượng trung bình mỗi người dùng và trung bình thời lượng đoạn xem theo người dùng được diễn giải riêng, đơn vị giây. Tra cứu hỗ trợ tìm một phần/chính xác userId, lọc mã cụm và phân trang; tìm kiếm hoặc đổi cụm trở về trang 1. Không gán lại cụm, huấn luyện hoặc tạo scatter chưa có phép chiếu. Các kết quả chỉ mô tả dữ liệu mô phỏng.
- `/ket-hop`: chọn 00h–23h, biểu đồ và bảng Top 3 phim theo giờ, nhận xét chênh lệch hai phim đầu; bảng tra cứu đủ 72 dòng có tùy chọn chỉ xem giờ đang chọn.

Trang kết hợp dùng loader `loadCombinedAnalysis` và các thành phần tải/lỗi, biểu đồ, bảng sẵn có. Service kiểm tra đủ 24 giờ, mỗi giờ đúng 3 phim; giữ nguyên thứ hạng Spark theo play giảm dần và mã phim tăng dần khi bằng nhau. `playCount` là số sự kiện play; `distinctUsers` được đếm riêng cho mỗi phim trong mỗi giờ, không cộng các nhóm để suy ra tổng người dùng. Dữ liệu gộp trên toàn kỳ theo giờ Việt Nam (UTC+7), không phải riêng một ngày; chỉ có Top 3 mỗi giờ, không bao gồm tất cả phim. Nhận xét là mô tả dữ liệu mô phỏng, không suy diễn sở thích người xem thật.
- `/thoi-luong`: so sánh số bản ghi, trung bình, trung vị xấp xỉ, nhỏ nhất, lớn nhất và độ lệch chuẩn mẫu giữa toàn bộ sự kiện và các sự kiện có thời lượng dương.

Trang thời lượng dùng loader riêng `loadWatchDuration` với cơ chế đọc JSON, tải/lỗi và thử lại hiện có. Giá trị gốc đơn vị giây được giữ nguyên; giao diện làm tròn tối đa 3 chữ số thập phân và dùng dấu phân cách tiếng Việt. Có bảng đủ 12 giá trị, thẻ số bản ghi/trung bình và nhận xét từ chênh lệch trung bình, trung vị. Các thống kê được Spark tổng hợp theo bản ghi sự kiện, không phải mỗi phiên xem. Không cộng hai nhóm, không tạo histogram hoặc phân bố chưa có dữ liệu. `watchDuration.js` kiểm tra đủ hai nhóm, đơn vị, giá trị hợp lệ. Không đổi null/sai dữ liệu thành 0.
- `/the-loai`: biểu đồ mặc định Top 10 thể loại, chọn Top 5/10/toàn bộ; bảng giữ tất cả thể loại đã xuất và nhận xét so sánh hai vị trí đầu.

Trang thể loại dùng lại `DashboardDataProvider` và hàm đọc JSON, với loader `loadGenres` riêng để báo thiếu/lỗi dữ liệu thể loại mà không ảnh hưởng các trang cũ. `genreAnalysis.js` kiểm tra tên thể loại, số đếm và sắp xếp giảm dần; nhận xét lấy hai vị trí đầu và hiệu số sự kiện. Biểu đồ thanh ngang và bảng được tái sử dụng từ components hiện có. Một phim có thể thuộc nhiều thể loại nên một sự kiện play có thể được đếm ở nhiều nhóm; không cộng các nhóm thành tổng play độc lập. Không chuyển các số đếm này thành kết luận về sở thích người xem thật.
- `/hanh-vi`: biểu đồ 5 hành vi, bảng số lượng và tỷ lệ.
- `/thoi-gian`: biểu đồ 24 giờ, bảng sự kiện, phát phim và người dùng khác nhau.

`DashboardDataProvider` đọc dữ liệu bằng service hiện có và dùng chung giữa các trang. Các trang tái sử dụng biểu đồ và bảng trong `OverviewCharts.jsx`; không sao chép cách tính KPI. `services/overviewAnalysis.js` vẫn kiểm tra tổng theo giờ và sắp xếp phim, trả thêm danh sách tối đa 20 phim. Trục số ghi rõ nghìn/triệu; tooltip và bảng dùng giá trị chính xác. Tên phim dài được xuống dòng/rút gọn trên trục; tên đầy đủ nằm trong tooltip và bảng chi tiết.

Phạm vi được hiển thị theo thông tin đã xác nhận: dữ liệu hành vi mô phỏng từ 01/09/2026 đến 30/09/2026, giờ Việt Nam (UTC+7). JSON theo giờ đã tổng hợp sẵn; frontend không chuyển múi giờ thêm một lần nữa. Các kết quả không đại diện sở thích người xem thật. Trang K-Means chỉ trình bày kết quả Spark đã xuất, không huấn luyện trong frontend; các lựa chọn và bộ lọc chỉ dùng dữ liệu hiện có.

Khi kiểm tra localhost, thử thanh điều hướng, các liên kết chi tiết, nút Back và tải lại trực tiếp ở từng đường dẫn. Di chuột vào cột để xem số chính xác. Thu nhỏ cửa sổ; bảng chi tiết cuộn ngang trong vùng riêng. Số phiên có phát phim vẫn là số phiên phân biệt, không phải số sự kiện play.

`node scripts/check-ui.mjs` kiểm tra bằng Edge cài sẵn trên Windows ở 1440/900/390/320px: đường dẫn, menu, Back, bảng, KPI, tooltip, tương tác, trạng thái tải/lỗi và tràn ngang. Ảnh kiểm tra và profile tạm nằm trong `.browser-check/` (được bỏ qua bởi .gitignore). Script không cài thư viện hoặc thay đổi evidence.
