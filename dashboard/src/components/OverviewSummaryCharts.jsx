import { lazy, Suspense, useState, useRef } from 'react';
import OverviewHourlyChart from './OverviewHourlyChart.jsx';
import OverviewDataPanel from './OverviewDataPanel.jsx';
import OverviewMovieRanking from './OverviewMovieRanking.jsx';
import { movieRankingRows } from '../services/overviewExport.js';
import { presentActions, operationHelp, hourRange } from '../content/overviewContent.js';
import { number } from '../services/formatNumbers.js';
const OverviewActionDonut = lazy(() => import('./OverviewActionDonut.jsx'));

export default function OverviewSummaryCharts({ analysis }) {
  const [selectedAction, setSelectedAction] = useState(analysis.actions[0].action);
  const movies = movieRankingRows(analysis.topMovies);
  const actions = presentActions(analysis.actions);
  const chartDetails = useRef(null);
  const movieDetails = useRef(null);
  return <section className="overview-visualizations" aria-labelledby="overview-charts-title">
    <div className="overview-section-heading"><h2 id="overview-charts-title">Hoạt động trong kỳ</h2><p>Biểu đồ và số liệu đối chiếu</p></div>
    <div className="overview-chart-grid">
        <OverviewDataPanel kind="hourly" className="overview-hourly-panel" title="Số hành động theo giờ" note="Mỗi cột cộng các hành động ở cùng khung giờ trong toàn kỳ, theo giờ Việt Nam." help="Mỗi cột là tổng số hành động ghi nhận trong cùng khung giờ qua tất cả ngày của kỳ phân tích, không phải một ngày riêng lẻ. Một người có thể tạo nhiều hành động; không đọc cột này thành số người dùng. Cột đậm biểu thị khung giờ có số hành động cao nhất; viền cột cho biết giờ đang chọn." technical="Spark nhóm theo hour và đếm bản ghi thành eventCount trong stats_hourly_activity.json. Giờ đã được tính theo Asia/Ho_Chi_Minh; frontend không chuyển múi giờ thêm lần nữa." explanationTarget={chartDetails} instructions={operationHelp.hourly} rows={analysis.hourly} detailPath="/thoi-gian">
          <OverviewHourlyChart data={analysis.hourly} peakHours={analysis.peakHours.map(row => row.hour)} plainLanguage compactHelp />
          <p className="chart-insight">{analysis.peakHours.map(row => hourRange(row.hour)).join(' · ')} ghi nhận nhiều hành động nhất: <strong>{number(analysis.peakHours[0].eventCount)}</strong>{analysis.peakHours.length > 1 ? ' ở mỗi khung giờ' : ''}, cộng gộp toàn kỳ.</p>
        </OverviewDataPanel>
      <OverviewDataPanel kind="actions" title="Cơ cấu hành động được ghi nhận" note="Số lần ghi nhận và tỷ trọng của từng hành động trong kỳ." help="Tỷ lệ = số lần ghi nhận một loại hành động chia tổng số hành động trong kỳ, nhân 100%. Mẫu số gồm mọi hành động, không phải số người dùng. Một người có thể đóng góp nhiều lần vào cùng một loại hành động." technical="Spark nhóm theo action, tạo count và percentage trong stats_action_distribution.json. Mã hành động gốc được giữ trong CSV. complete chỉ xác nhận kết thúc xem hết thời lượng phim mô phỏng." explanationTarget={chartDetails} instructions={operationHelp.actions} rows={actions} detailPath="/hanh-vi">
        <Suspense fallback={<p className="donut-loading" role="status">Đang tải biểu đồ hành vi…</p>}><OverviewActionDonut data={actions} selectedAction={selectedAction} onSelect={setSelectedAction} plainLanguage compactHelp /></Suspense>
      </OverviewDataPanel>
      <div ref={chartDetails} className="independent-explanations chart-explanations" />
      <OverviewDataPanel kind="movies" className="overview-movies-panel" title="5 phim có nhiều lượt phát nhất" note="Xếp hạng theo số bản ghi phát phim trong kỳ." help="Thanh so sánh với phim dẫn đầu trong năm phim đang hiển thị. Lượt phát không phải số người xem hoặc số lượt xem hết phim. Bảng và CSV giữ đúng năm phim này." technical="Spark lọc action = play, nhóm theo movieId và title, đếm playCount; sắp giảm dần theo playCount, mã phim tăng dần khi bằng nhau. Tổng quan lấy năm dòng đầu từ stats_top_movies_by_play.json." explanationTarget={movieDetails} instructions={operationHelp.movies} rows={movies} detailPath="/phim">
        <OverviewMovieRanking rows={movies} countLabel="lượt phát phim" />
      </OverviewDataPanel>
    </div>
    <div ref={movieDetails} className="independent-explanations" />
  </section>;
}
