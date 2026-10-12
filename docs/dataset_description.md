# Dataset phim

Nguồn: **MovieLens latest-small**, GroupLens, University of Minnesota.

- Trang nguồn: https://grouplens.org/datasets/movielens/latest/
- Tải: https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
- Điều kiện sử dụng: https://files.grouplens.org/datasets/movielens/ml-latest-small-README.html
- Tải thực tế: **11/10/2026, 22:20:20 giờ Việt Nam** (15:20:20 UTC).
- ZIP: 978.202 byte; SHA256 `696d65a3dfceac7c45750ad32df2c259311949efec81f0f144fdfb91ebc9e436`.
- Manifest máy đọc: `data/raw/download_manifest.json`. Giấy phép đầy đủ: `data/raw/ml-latest-small/README.txt`.

README snapshot ghi được sinh ngày 26/09/2018; đây là tập phát triển có thể thay đổi theo thời gian; hash snapshot giúp tái lập bản đã dùng. Không lấy số lượng trên website làm kết quả kiểm thử: bảng sau được đếm trực tiếp bằng CSV parser trên bản tải.

| File gốc | Số bản ghi, không tính header | Trường |
|---|---:|---|
| movies.csv | 9.742 | movieId, title, genres |
| ratings.csv | 100.836 | userId, movieId, rating, timestamp |
| tags.csv | 3.683 | userId, movieId, tag, timestamp |
| links.csv | 9.742 | movieId, imdbId, tmdbId |

CSV UTF-8, dấu phân cách phẩy, tiêu đề có dấu phẩy được quote. Phải dùng CSV parser, không `split(',')`. Genres phân tách bằng `|`.

| Trường chuẩn hóa | Kiểu khi đọc ở Spark | Ý nghĩa |
|---|---|---|
| movieId | long, không null | Khóa phim từ MovieLens |
| title | string | Giữ tên và hậu tố năm, bỏ khoảng trắng ngoài, Unicode NFC |
| genres | string | Danh sách nhãn ngăn bởi `|`; giữ `(no genres listed)` |
| releaseYear | integer, có thể null | Năm trích từ hậu tố `(YYYY)` cuối title |

Quy tắc năm: regex `\((\d{4})\)\s*$`, chỉ nhận khoảng 1870–2100. Không khớp, ngoài khoảng hoặc dạng năm kéo dài `(2006–2007)` → ô rỗng/null; không đoán, không lấy năm hiện tại. Title gốc vẫn được giữ để truy vết. Dataset không có runtime phim, không tự suy ra runtime từ title hay năm.

Kết quả QA: 0 ID trùng, 0 title trống, 0 genres trống, 34 giá trị `(no genres listed)`, 13 releaseYear rỗng, 11 dòng có thay đổi bởi chuẩn hóa. 0 lỗi giải mã UTF-8 và 0 lỗi cấu trúc CSV phát hiện. Đọc UTF-8 strict và kiểm ký tự thay thế/NUL không bảo đảm phát hiện mọi lỗi nội dung hay mọi trường hợp mojibake. Danh sách 13 phim và hash output nằm trong `evidence/recheck-20261011-221710/dataset_quality.json`.

Raw không sửa. Bản chuẩn hóa riêng vẫn có 9.742 dòng; không bỏ các phim thiếu năm/thể loại. Nếu ID trùng, title hoặc genres thiếu, script dừng để xử lý nguồn thay vì âm thầm chọn một dòng. Genres rỗng làm kiểm tra FAIL; không bịa nhãn mới. Chuỗi genres trùng trong một phim được loại trùng và giữ thứ tự.

Ba loại dữ liệu cần phân biệt: metadata mô tả phim; rating có sẵn phản ánh đánh giá người dùng MovieLens; JSONL của dự án là hành vi **mô phỏng**, không chuyển rating thành lượt play/watch. ID `sim-user-*` không liên quan userId trong ratings.csv. Ratings/tags chỉ được giữ nguyên và thống kê, chưa làm phân tích.

Sử dụng cho đồ án học tập, ghi nhận nguồn GroupLens; không ngụ ý được trường/nhóm nghiên cứu bảo trợ. Bản phân phối lại và biến đổi phải giữ điều kiện của nguồn; mục đích thương mại cần xin phép theo README. Trích dẫn: F. Maxwell Harper và Joseph A. Konstan (2015), *The MovieLens Datasets: History and Context*, DOI https://doi.org/10.1145/2827872. Giữ README gốc cùng dataset khi bàn giao.
