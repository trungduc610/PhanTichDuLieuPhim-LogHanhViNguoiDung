# Schema dữ liệu Movie Dataset (Phim)

## 1. Nguồn dữ liệu
* **File nguồn**: [`data/processed/movies.csv`](file:///d:/Code/Bigdata/movie-log-bigdata-week1/movie-log-bigdata/data/processed/movies.csv) (chuẩn hóa từ MovieLens Latest Small của GroupLens, University of Minnesota).
* **Định dạng**: CSV (UTF-8, delimiter `,`, quote standard).
* **Số lượng bản ghi**: 9.742 dòng (không tính header).
* **Vai trò trong hệ thống**: Dữ liệu metadata mô tả thông tin phim. **Không đi qua Apache Flume**, được lưu trữ tĩnh và đưa trực tiếp vào Spark để kết nối (join) với log hành vi người dùng.

## 2. Bảng đặc tả Schema

| Field | Spark Type | Nullable | Ý nghĩa | Ghi chú ràng buộc |
|---|---|---|---|---|
| `movieId` | `LongType` | `false` | Khóa định danh duy nhất của phim | Khóa chính (Primary Key), dùng làm khóa liên kết (`join key`). Đảm bảo 100% unique, không null. |
| `title` | `StringType` | `false` | Tên phim đầy đủ | Giữ nguyên tên gốc kèm hậu tố năm nếu có (ví dụ: `Toy Story (1995)`). Chuẩn hóa khoảng trắng và Unicode NFC. |
| `genres` | `StringType` | `false` | Danh sách thể loại phim | Ngăn cách bởi dấu gạch đứng `\|` (ví dụ: `Adventure\|Animation\|Children`). Phim không có thể loại ghi `(no genres listed)`. |
| `releaseYear` | `IntegerType` | `true` | Năm phát hành của phim | Trích xuất bằng regex từ `title` dạng `(YYYY)` trong khoảng 1870–2100. Có 13 phim không có năm trong title được gán `null`. |

## 3. Khai báo Schema bằng PySpark (StructType)

```python
from pyspark.sql.types import StructType, StructField, LongType, StringType, IntegerType

MOVIE_SCHEMA = StructType([
    StructField("movieId", LongType(), nullable=False),
    StructField("title", StringType(), nullable=False),
    StructField("genres", StringType(), nullable=False),
    StructField("releaseYear", IntegerType(), nullable=True),
])
```

## 4. Hướng dẫn đọc bằng PySpark

```python
movies_df = (
    spark.read
    .option("header", "true")
    .option("encoding", "UTF-8")
    .schema(MOVIE_SCHEMA)
    .csv("data/processed/movies.csv")
)
```
