import { definitions } from '../content/overviewContent.js';
import MetricExplanation from './MetricExplanation.jsx';
import { number } from '../services/formatNumbers.js';
import { useRef } from 'react';

export function OverviewSessions({ metrics }) {
  const sessionDetails = useRef(null);
  return <details className="overview-sessions">
    <summary>Hiểu thêm về phiên sử dụng <span>Hai chỉ số bổ sung</span></summary>
    <div className="session-grid">
      {[['sessions',metrics.totalSessions],['playedSessions',metrics.playedSessions]].map(([key,value]) => <article key={key}>
        <h3>{definitions[key].title}</h3><p className="session-value" data-session={key}>{number(value)}</p>
        <MetricExplanation definition={definitions[key]} target={sessionDetails} />
      </article>)}
    </div>
    <div ref={sessionDetails} className="independent-explanations" />
  </details>;
}

export default function OverviewMethodology({ source }) {
  return <details className="overview-source overview-methodology">
    <summary>Tìm hiểu dữ liệu và phương pháp phân tích</summary>
    <div className="methodology-grid">
      <section><h3>Dữ liệu đầu vào là gì?</h3>
        <p>MovieLens cung cấp thông tin phim. Mã người dùng, hành vi và thời lượng phim dùng để mô phỏng được tạo cho đồ án; đây không phải lịch sử xem phim của người dùng thật.</p>
      </section>
      <section><h3>Các chỉ số được tính như thế nào?</h3>
        <p>Quy tắc đếm, tên trường và file nguồn nằm trong phần Giải thích của từng chỉ số và biểu đồ.</p>
        <p><code>view</code> là xem thông tin phim. Lượt phát chỉ đếm bản ghi <code>action = "play"</code>. <code>complete</code> là hành động kết thúc xem hết thời lượng phim mô phỏng, không chứng minh một người thật đã xem hết phim.</p>
        <p>Thời lượng là giây mới phát sinh của từng đoạn xem; không phải thời lượng trung bình mỗi phiên.</p>
      </section>
      <section><h3>Dữ liệu đi qua hệ thống ra sao?</h3>
        <ol className="methodology-flow">
          <li><strong>Thông tin phim → HDFS.</strong> Danh mục MovieLens được lưu vào HDFS.</li>
          <li><strong>Log mô phỏng → Flume → HDFS.</strong> Flume thu thập log; dữ liệu được chuyển vào vùng lưu trữ HDFS.</li>
          <li><strong>HDFS → Spark → JSON.</strong> Spark làm sạch, chuyển đổi, ghép thông tin phim, tổng hợp và xuất kết quả theo lô. K-Means phân cụm theo đặc trưng hành vi.</li>
          <li><strong>JSON → Dashboard.</strong> Script kiểm chứng và đồng bộ kết quả trước khi frontend đọc dữ liệu. Mở trang không chạy lại Spark.</li>
        </ol>
      </section>
      <section><h3>Dashboard lấy kết quả từ đâu?</h3>
        <p>Run phân tích: <code>{source.runId}</code>. Nguồn: <code>{source.evidenceRoot}/{source.runId}/dashboard/</code>.</p>
        <ul><li><code>stats_action_distribution.json</code>: số hành động và tỷ lệ.</li>
          <li><code>kmeans_assignments.json</code>: người dùng và các số đếm phiên.</li>
          <li><code>stats_hourly_activity.json</code>: hoạt động theo giờ.</li>
          <li><code>stats_top_movies_by_play.json</code>: xếp hạng phim theo lượt phát.</li></ul>
        <p>Hợp đồng <code>handoff.json</code> và các biên nhận PASS xác định đúng run, nguồn HDFS, kích thước, SHA-256, schema và số dòng. Chỉ công bố nguồn sau khi đồng bộ đủ các file đã kiểm chứng; không dùng run cũ để che lỗi.</p>
        <p>Nút Biểu đồ/Bảng đổi cách xem cùng dữ liệu. CSV giữ giá trị gốc chưa làm tròn; bảng có vùng cuộn hỗ trợ phím mũi tên và Home/End.</p>
      </section>
      <section className="methodology-limits"><h3>Những giới hạn cần biết</h3>
        <p>Dữ liệu được xử lý theo lô, không cập nhật thời gian thực. Ngày và giờ đã được Spark tổng hợp theo Asia/Ho_Chi_Minh (UTC+7).</p>
        <p>Một người có thể phát phim nhiều lần; lượt phát không phải số người xem hoặc lượt xem hoàn chỉnh. Một phim có nhiều thể loại nên số lượt giữa các thể loại có thể chồng lặp.</p>
        <p>Kết quả mô tả bộ dữ liệu mô phỏng, không suy ra sở thích hay thói quen của người xem ngoài đời. K-Means phân nhóm, không dự đoán hoặc đề xuất phim; Silhouette không phải độ chính xác.</p>
      </section>
    </div>
  </details>;
}
