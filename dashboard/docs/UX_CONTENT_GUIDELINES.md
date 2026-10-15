# Quy chuẩn UX và nội dung Dashboard

Áp dụng cho Tổng quan và bảy trang chi tiết qua hai đợt nâng cấp. Giữ nguyên năm trang đã nghiệm thu khi làm đợt 2. Giữ phiên bản 1.1 và final run `tv2-aae83326c1ab`.

## 1. Mục tiêu trải nghiệm

**Dễ hiểu khi xem — chuyên sâu khi cần.** Người xem đọc được quy mô, hoạt động phổ biến, phim và khung giờ nổi bật trước khi tìm hiểu kỹ thuật. Không đòi hỏi biết Spark, log hoặc session. Dashboard phân tích dữ liệu theo lô, không phải trang xem phim hay hệ thống realtime.

## 2. Ba lớp thông tin

1. **Phân tích chính:** KPI, đơn vị, biểu đồ/bảng, kết quả nổi bật và liên kết chi tiết. Viết bằng tiếng Việt; số liệu luôn từ JSON/metadata đã xác minh.
2. **Giải thích chỉ số:** mở bằng “Giải thích” hoặc “Giải thích dữ liệu”; nêu ý nghĩa, cách tính, điểm dễ nhầm. Chỉ dùng ví dụ khi cần và phải ghi rõ là ví dụ, không thay số liệu thật.
3. **Kỹ thuật:** mở “Chi tiết kỹ thuật” hoặc “Tìm hiểu dữ liệu và phương pháp phân tích”; chứa thuật ngữ gốc, trường, công thức, file nguồn, provenance và giới hạn.

“Hướng dẫn thao tác” là nhóm riêng: chuột, bàn phím, chọn biểu đồ, đổi Biểu đồ/Bảng, cuộn bảng và CSV. Không dùng nó để thay phần giải thích dữ liệu.

## 3. Tiêu đề

- Nêu câu hỏi hoặc đại lượng được phân tích: “Số hành động theo giờ”, “5 phim có nhiều lượt phát nhất”.
- Không dùng tên biến, tên file, thuật toán hoặc từ quảng cáo làm tiêu đề chính.
- Tiêu đề trang Tổng quan: “Tổng quan hoạt động xem phim”.
- Trang phân cụm dùng tiêu đề “Phân nhóm người dùng”; K-Means được giải thích trong phần phương pháp. Giữ route `/phan-cum` và menu hiện có.

## 4. KPI và đơn vị

- Ba KPI chính: **Tổng số hành động**, **Số người dùng**, **Lượt phát phim**.
- **Phiên sử dụng** và **Phiên có phát phim** vẫn truy cập được trong “Hiểu thêm về phiên sử dụng”. Không thay bằng lượt phát.
- Dùng định dạng số Việt Nam; số đếm là số nguyên; giữ quy tắc định dạng đang có. Tỷ lệ chỉ làm tròn khi hiển thị; CSV giữ giá trị gốc.
- Đơn vị ghi tại thẻ, biểu đồ hoặc cột bảng. Hành động tính bằng lần; phát phim tính bằng lượt; thời lượng gốc là giây; tỷ lệ dùng % và giải thích mẫu số.
- Không thêm KPI số phim nếu chưa có đường đọc và xác minh metadata tương ứng.

## 5. Viết nhận xét

- Dẫn kết quả bằng số liệu đã xuất, phạm vi toàn kỳ và đơn vị. Ví dụ khung giờ lấy từ `analysis.peakHours`, không ghi cố định một giờ trong JSX.
- Giữ các giờ cùng dẫn đầu khi bằng nhau. Thứ hạng phim giữ quy tắc Spark: lượt phát giảm dần, mã phim tăng dần khi bằng nhau.
- Không suy từ tương quan thành nguyên nhân, từ dữ liệu mô phỏng thành thói quen người thật, hoặc từ lượt phát thành lượt xem hết.
- Một nhận xét chính mỗi biểu đồ. Hướng dẫn dài chuyển vào phần mở rộng.

## 6. Từ vựng thống nhất

| Khái niệm/trường | Tên hiển thị | Ý nghĩa và giới hạn |
| --- | --- | --- |
| Event | Hành động được ghi nhận | Một bản ghi hành vi hợp lệ |
| Total events / totalEvents | Tổng số hành động | Tổng `count` của mọi hành động |
| distinct userId | Số người dùng | Đếm mỗi mã một lần trong toàn kỳ; người dùng mô phỏng |
| view | Xem thông tin phim | Không phải phát phim |
| play | Phát phim | Bản ghi có action = "play"; không suy thêm cơ chế phát từ tên chỉ số |
| playCount / count khi action=play | Lượt phát phim | Có thể lặp trong cùng người dùng/phiên; không phải người xem hoặc lượt xem hết |
| pause | Tạm dừng | Hành động tạm dừng trong chuỗi log |
| stop | Dừng phát | Kết thúc xem trước hết thời lượng mô phỏng |
| complete | Hoàn thành xem phim | Hành động kết thúc xem hết thời lượng phim mô phỏng; không chứng minh người thật xem hết |
| sessionCount | Phiên sử dụng | Số cặp `(runId, sessionId)` phân biệt trong từng userId |
| playedSessionCount | Phiên có phát phim | Phiên có ít nhất một play; mỗi phiên chỉ tính một lần |
| hourly activity / eventCount | Số hành động theo giờ | Cùng khung giờ cộng gộp mọi ngày trong kỳ |
| watchDuration | Thời lượng xem | Giây mới phát sinh của từng đoạn, không phải thời lượng trung bình phiên |
| K-Means | Phân nhóm người dùng | Phân cụm không giám sát; Silhouette không phải accuracy |

Định nghĩa giao diện đặt tại `src/content/overviewContent.js`. Bốn trang đợt 1 tái sử dụng tên hành động và định nghĩa này ở lớp trình bày; không thay service tính toán. Không sửa action code hoặc đổi ý nghĩa trường số để thống nhất câu chữ.

## 7. Nguồn dữ liệu và phương pháp

- Phần chính nêu MovieLens cung cấp thông tin phim, log hành vi mô phỏng, khoảng ngày từ metadata, giờ Việt Nam UTC+7 và xử lý theo lô.
- Run ID, tên JSON, SHA-256 và trường dữ liệu nằm trong vùng kỹ thuật chủ động mở. Không dùng ngày hardcode thay metadata.
- Hai nhánh đầu vào: **MovieLens → HDFS** và **log mô phỏng → Flume → HDFS**. Không mô tả MovieLens bắt buộc qua Flume.
- Spark đọc HDFS, làm sạch/chuyển đổi/ghép dữ liệu, tổng hợp và xuất JSON. Dashboard kiểm chứng, đồng bộ rồi đọc JSON. Mở website không chạy lại Spark.
- Tham chiếu nội bộ: `src/tv2_analytics.py`, `scripts/generate_logs.py`, `docs/week3_tv2_handoff.md`, `docs/week3_tv2_processing_report.md` ở repository root; hợp đồng và biên nhận của final run. Chỉ đọc, không sửa pipeline/evidence.
- Không mô tả session bằng quy tắc nghỉ 30 phút: source thực tế sử dụng mã phiên có sẵn.

## 8. Thành phần giải thích

- `MetricExplanation`: nhận định nghĩa gồm tên, ý nghĩa, cách tính, lưu ý và chi tiết kỹ thuật. `IndependentDisclosure` giữ native details/summary ở card, đưa nội dung dài sang vùng riêng qua portal của React khi có target.
- `MetricCard` nhận `explanation` tùy chọn; các trang chưa nâng cấp giữ nguyên.
- `OverviewDataPanel` tách giải thích dữ liệu và thao tác. Thuật ngữ gốc của hành động vẫn có trong CSV; bảng chính ưu tiên tên tiếng Việt.
- Không dùng tooltip chỉ mở khi hover để chứa thông tin thiết yếu; thông tin phải xem được bằng chạm và bàn phím.
- Phần giải thích mở ngay trong luồng đọc, không che số liệu hoặc làm mất focus. Không tự mở hàng loạt.
- Dùng duy nhất mũi tên phải khi đóng và mũi tên xuống khi mở, theo trạng thái `details` trực tiếp chứa `summary`. Không dùng selector descendant để gán trạng thái của mục cha cho mục con. Tắt marker mặc định khi dùng mũi tên CSS; không để cả +/− và mũi tên cùng xuất hiện.
- KPI và biểu đồ chỉ chứa nút mở; vùng giải thích riêng nằm dưới nhóm tương ứng. Có thể mở nhiều mục độc lập; nút Đóng trả focus về nút mở. Không cố định chiều cao văn bản hoặc chèn khoảng trắng để làm card bằng nhau.
- Grid biểu đồ dùng `align-items: start`. Donut và chú giải nằm cạnh nhau khi vùng nội dung đủ rộng, chuyển dọc khi hẹp. Mở chi tiết không được đổi chiều cao card hoặc vùng vẽ.

## 9. Liên kết giữa các trang

- Giữ nguyên tám route. Thẻ kết quả và biểu đồ dẫn tới phân tích tương ứng: phim `/phim`, hành vi `/hanh-vi`, giờ `/thoi-gian`.
- Tổng quan có thể dùng tên dễ hiểu hơn; tên menu của trang chưa nâng cấp giữ nguyên để tránh mở rộng phạm vi.
- Điều hướng không thay dữ liệu, bộ đếm hoặc run. “Xem chi tiết” có accessible name gắn với tiêu đề biểu đồ.

## 10. Khả năng truy cập và responsive

- Kiểm tra 1440/768/390/320px. Chỉ bảng có thể cuộn ngang; toàn trang không được tràn, cắt chữ hay chồng lớp.
- Tiêu đề có thứ bậc; summary/button/link giữ focus rõ, thao tác được bằng Tab, Enter/phím cách. Giữ đầy đủ các phím điều khiển biểu đồ đang có.
- Kết quả tương tác đọc qua vùng live hiện có; không thông báo lặp lại toàn bộ trang. Hướng dẫn bàn phím cho biểu đồ có liên kết aria-describedby hoặc nằm cạnh biểu đồ trong mục thao tác.
- Không chỉ dùng màu để phân biệt: tên, số, viền, thứ hạng và trạng thái nút bổ sung thông tin.
- CSS Tổng quan giới hạn trong `.overview-home`; CSS trang chi tiết trong `.detail-ux`. Quy tắc riêng cho ba trang đợt 2 phải thêm phạm vi `.advanced-ux`. Không sửa thiết kế các trang đã chốt.

## 11. Bốn trang phân tích đợt 1

- **Phim:** xếp hạng theo lượt phát; không gọi là số người xem. Chỉ tra cứu các phim đã xuất. Tìm kiếm không đánh lại hạng; phân trang chỉ đổi dòng hiển thị. CSV gồm mọi dòng khớp tìm kiếm, kể cả những trang khác; khi không có kết quả thì vô hiệu hóa nút tải. Mặc định bảng giữ đủ 20 dòng như trước.
- **Thể loại:** dùng số lượt phát, không biểu diễn các nhóm thành tỷ lệ loại trừ nhau. Một lượt phát có thể đóng góp cho nhiều thể loại. Bộ lọc Top 5/10/toàn bộ chỉ thay biểu đồ; bảng và CSV giữ đủ nguồn đã xuất.
- **Hành vi:** bảng và biểu đồ dùng năm tên tiếng Việt thống nhất; mã action gốc đặt trong giải thích thuật ngữ và CSV. Tỷ lệ dùng tổng hành động làm mẫu số; không suy ra tỷ lệ người dùng, số phiên hoặc chuyển đổi.
- **Thời gian:** giờ là hành động cộng gộp toàn kỳ, ngày là DAU đếm người dùng duy nhất trong ngày. Khoảng ngày lấy từ metadata/service, ghi UTC+7; giữ các giờ cùng dẫn đầu. Chuỗi DAU mô phỏng không chứng minh tăng trưởng.
- `AnalysisExplanation` tái sử dụng `IndependentDisclosure`: hai mục riêng cho dữ liệu và thao tác, chi tiết kỹ thuật lồng trong mục dữ liệu. Vùng nội dung đặt ngoài các card của hàng phân tích; đóng trả focus về đúng nút mở. Run/file nguồn đặt trong mục kỹ thuật.
- `AnalysisResultsTable` chỉ lọc/phân trang dữ liệu hiển thị; tái sử dụng cơ chế CSV hiện có để giữ giá trị gốc và mã hành động. Không thay phép tổng hợp, kiểm chứng hoặc JSON nguồn.
- Mỗi trang dùng bố cục theo nội dung riêng và có liên kết tới phân tích liên quan. Không nhân bản hàng KPI Tổng quan cho mọi trang.
- Card chứa bảng, kể cả card DAU dạng `aside`, cần `min-width: 0` khi nằm trong grid. Kiểm tra cả chiều rộng viewport thực tế khi mở bảng trên mobile; chỉ so `scrollWidth` với `innerWidth` có thể bỏ sót trường hợp trình duyệt tự nới viewport.

## 12. Ba trang phân tích đợt 2

- **Thời lượng:** giữ hai phạm vi `all_events` và `watch_segments` (thời lượng > 0). Nhóm dương nằm trong nhóm toàn bộ, không cộng hai nhóm. Trung bình là tổng giây chia số bản ghi trong từng nhóm; trung vị xấp xỉ là giá trị giữa; độ lệch chuẩn mẫu mô tả độ phân tán. Không gọi thời lượng bản ghi là thời lượng phiên. Tệp thống kê không xuất tổng thời lượng nên không tạo thêm chỉ số tổng từ trung bình đã làm tròn.
- **Kết hợp:** mỗi dòng là phim–giờ, cộng gộp mọi ngày trong kỳ theo UTC+7. Lượt phát có thể lặp; người dùng duy nhất chỉ có phạm vi nhóm phim–giờ. Giữ Top 3 và hạng Spark, không cộng số người dùng giữa các nhóm. Bộ lọc tìm tên/giờ và phân trang chỉ đổi bảng tra cứu; biểu đồ và nhận xét đi theo giờ đang chọn. Không suy nhân quả hoặc sở thích cá nhân.
- **Phân nhóm:** K-Means gom đặc trưng hành vi gần nhau, không phải dự đoán hoặc đề xuất phim. Tên hiển thị là “Cụm + mã”, giữ mã gốc trong CSV. Silhouette là điểm đánh giá phân tách/cohesion từ −1 đến 1, không phải accuracy hoặc phần trăm. Chỉ so sánh các K đã thử; đọc K, seed và danh sách đặc trưng từ metadata đã xác minh. StandardScaler và khoảng cách huấn luyện/đánh giá phải mô tả đúng code Spark; không mặc định mọi cột tra cứu đều là đầu vào ML.
- **Hồ sơ cụm:** dùng đơn vị gốc và các trung bình đã xuất. Trung bình tỷ lệ hoàn thành của từng người khác với tỷ lệ tổng hành động complete/play. Trung bình tổng thời lượng mỗi người khác với trung bình các trung bình đoạn dương theo người; không thay bằng thời lượng phiên. Người không có phiên play hiển thị “Chưa xác định” ở bảng tra cứu, giữ số 0 và cờ xác định trong CSV.
- Tái sử dụng `AnalysisExplanation`, `IndependentDisclosure` và vùng giải thích ngoài card. Chỉ dẫn bàn phím của biểu đồ vẫn được liên kết bằng `aria-describedby` khi ẩn đoạn hướng dẫn khỏi màn hình chính.
- `ResultCsvButton` dùng bộ mã hóa CSV hiện có. CSV thời lượng giữ cả hai nhóm, độc lập chỉ số đang chọn. CSV kết hợp và người dùng giữ mọi dòng khớp bộ lọc, kể cả các trang chưa hiển thị; không có kết quả thì vô hiệu hóa nút tải. Tỷ lệ gốc 0–1, cờ xác định và số phiên tử/mẫu phải giữ nguyên.
- Kiểm tra riêng ba trang bằng `node scripts/check-ui.mjs --advanced-pages`; ảnh đóng/mở và kết quả kiểm tra nằm trong `.browser-check/` (không đưa vào commit).

## Tham khảo bố cục

Tham khảo cách phân cấp thông tin và tổ chức thẻ/biểu đồ của [shadcn dashboard](https://ui.shadcn.com/blocks?category=dashboard), [Tremor](https://www.tremor.so/) và [Recharts examples](https://recharts.github.io/en-US/examples/). Tiếp tục dùng React/CSS/Recharts hiện có, không cài thêm template hoặc dependencies.
