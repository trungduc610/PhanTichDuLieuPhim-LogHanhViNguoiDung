# Kiến trúc hệ thống — Hệ thống thu thập và phân tích log xem phim

Đề tài: **“Phân tích dữ liệu phim và log hành vi người dùng trên hệ thống xem phim”**

---

## 1. Định hướng công nghệ và vai trò các thành phần

Hệ thống được thiết kế theo đúng định hướng công nghệ trọng tâm của đồ án môn học Nhập môn Big Data:

### A. Apache Flume — Công nghệ trọng tâm / Cốt lõi của đồ án
* **Vai trò trung tâm**: Đóng vai trò là thành phần cốt lõi của luồng thu thập và vận chuyển dữ liệu log hành vi người dùng (User Behavior Log).
* **Cơ chế hoạt động**: Hoạt động theo kiến trúc chuẩn:
  $$\text{Input Log} \longrightarrow \text{Source (spooldir)} \longrightarrow \text{Channel (file)} \longrightarrow \text{Sink (file\_roll)} \longrightarrow \text{Storage JSONL}$$
* **Nhiệm vụ**: Đảm bảo log được tiếp nhận tin cậy, đệm bền vững trên đĩa chống mất mát dữ liệu khi có sự cố, và xuất ra các tệp JSON Lines ổn định phục vụ xử lý phía sau.

### B. Các công nghệ hỗ trợ
1. **Docker / Docker Compose**:
   * Đóng vai trò hỗ trợ đóng gói môi trường, quản lý tài nguyên và đảm bảo tính tái lập (reproducibility) trên các hệ điều hành khác nhau của sinh viên và giảng viên.
2. **Spark / PySpark**:
   * Đóng vai trò **downstream** (phía sau luồng thu thập). Spark chỉ được sử dụng sau khi Apache Flume đã thu thập và kết xuất log thành công. Spark kiểm tra chất lượng, làm sạch dữ liệu, biến đổi và thực hiện các phép tính phân tích. *Spark không phải là công nghệ chính/trọng tâm của đồ án.*
3. **MovieLens Dataset**:
   * Là tập dữ liệu metadata tĩnh mô tả thông tin phim (tên, thể loại, năm phát hành). **MovieLens không cần và không đi qua Apache Flume**, được lưu trực tiếp vào kho lưu trữ để Spark kết hợp (join) với log hành vi.
4. **Dashboard**:
   * Chỉ đóng vai trò trực quan hóa kết quả phân tích cuối cùng ở giai đoạn sau.

---

## 2. Sơ đồ kiến trúc luồng dữ liệu (Data Flow Architecture)

```text
+------------------------+
|   MovieLens Dataset    | (Metadata tĩnh)
+------------------------+
           |
           v
  [prepare_movies.py]
           |
           v
+------------------------+
|       movies.csv       | ----------------------------------+
+------------------------+                                   |
                                                             |
+------------------------+                                   |
| User Behavior Log Gen  | (Mô phỏng hành vi xem phim)       |
+------------------------+                                   |
           |                                                 |
           v                                                 |
     Raw JSONL Logs                                          |
           |                                                 |
           v                                                 |
======================================================       |
||           APACHE FLUME PIPELINE (TRỌNG TÂM)      ||       |
||                                                  ||       |
||  [Source: spooldir]                              ||       |
||     Quét thư mục spool, nạp atomic, đuôi COMPLETED||      |
||           |                                      ||       |
||           v                                      ||       |
||  [Channel: file]                                 ||       |
||     Đệm bền vững trên đĩa (checkpoint & data)    ||       |
||           |                                      ||       |
||           v                                      ||       |
||  [Sink: file_roll]                               ||       |
||     Cắt lô JSON Lines mỗi 10s (TEXT serializer)  ||       |
======================================================       |
           |                                                 |
           v                                                 |
+------------------------+                                   |
| Storage / Output JSONL | ----------------------------------+
+------------------------+                                   |
                                                             v
                                             +-------------------------------+
                                             |       SPARK / PYSPARK         |
                                             |  - Tuần 1: Schema & Validation|
                                             |  - Tuần 2: Cleaning & Analysis|
                                             +-------------------------------+
                                                             |
                                                             v
                                             +-------------------------------+
                                             |   Kết quả phân tích (CSV)     |
                                             +-------------------------------+
                                                             |
                                                             v
                                             +-------------------------------+
                                             |           DASHBOARD           |
                                             |     (Trực quan hóa Tuần 2)    |
                                             +-------------------------------+
```

---

## 3. Kiến trúc Container Docker

Hệ thống được module hóa thành các service độc lập qua Docker Compose:

1. **Service `flume`**:
   * Image: `movie-log-flume:1.11.0-local` (OpenJDK JRE 8 + Apache Flume 1.11.0).
   * Volume: Mount thư mục `./data` và `./logs`.
   * Trách nhiệm: Thu thập log và ghi output JSON Lines vào `./data/runs/<run-id>/output/`.

2. **Service `spark`** (Tích hợp Tuần 1):
   * Image: `apache/spark:3.5.1` (OpenJDK 17 + Python 3.10/3.11 + PySpark 3.5.1).
   * Volume: Mount thư mục dự án vào `/opt/spark/work-dir` hoặc `/project`.
   * Trách nhiệm: Đọc `movies.csv` và output JSONL của Flume để xác thực schema, kiểm tra chất lượng dữ liệu và kiểm thử liên kết khóa `movieId`.

*Hai service hoạt động với các phiên bản Java độc lập (Flume dùng Java 8, Spark dùng Java 17), không xung đột môi trường và đảm bảo tính cô lập hoàn toàn.*
