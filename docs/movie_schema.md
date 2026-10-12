# Schema metadata phim

Nguồn local: `data/processed/movies.csv`, chuẩn hóa riêng từ MovieLens; raw giữ nguyên. Metadata không đi qua Flume. CSV UTF-8 strict, delimiter phẩy, header và quote CSV chuẩn; title có dấu phẩy dùng parser, `escape='"'` với Spark để đọc double quote.

| Field | Spark type | Nullable | Ràng buộc |
|---|---|---|---|
| movieId | LongType | false | Số dương <= 2^63-1, không trùng, join key |
| title | StringType | false | Không rỗng, Unicode NFC, bỏ khoảng trắng ngoài |
| genres | StringType | false | Không rỗng, nhãn phân cách bằng `\|`; giữ `(no genres listed)` |
| releaseYear | IntegerType | true | Hậu tố `(YYYY)` cuối title, 1870–2100; không xác định để null |

Schema tái sử dụng: `from src.schemas import MOVIE_SCHEMA`. 9.742 phim/ID unique; 13 null releaseYear hợp lệ, 34 `(no genres listed)`; không bỏ các dòng đó. Nullable=false là hợp đồng, Spark reader có thể vẫn tạo null; job kiểm riêng tất cả null bắt buộc, malformed, duplicate và range. Ví dụ đọc đầy đủ trong `scripts/spark_smoke_test.py`, kết quả QA trong `evidence/recheck-20261011-221710/dataset_quality.json` và Spark reports cùng thư mục.
