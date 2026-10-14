import { lazy, Suspense, useState } from 'react';
import OverviewHourlyChart from './OverviewHourlyChart.jsx';
import OverviewDataPanel from './OverviewDataPanel.jsx';
import OverviewMovieRanking from './OverviewMovieRanking.jsx';
import { movieRankingRows } from '../services/overviewExport.js';
const OverviewActionDonut = lazy(() => import('./OverviewActionDonut.jsx'));

export default function OverviewSummaryCharts({ analysis }) {
  const [selectedAction, setSelectedAction] = useState(analysis.actions[0].action);
  const movies = movieRankingRows(analysis.topMovies);
  return <section className="overview-visualizations" aria-labelledby="overview-charts-title">
    <div className="overview-section-heading"><h2 id="overview-charts-title">Khám phá dữ liệu</h2><p>Xem biểu đồ, đối chiếu bảng hoặc tải CSV</p></div>
    <div className="overview-chart-grid">
        <OverviewDataPanel kind="hourly" className="overview-hourly-panel" title="Hoạt động theo giờ" note="24 khung giờ UTC+7 trên toàn kỳ. Cột xanh đậm: giờ cao điểm; cột có viền: giờ đang xem." help="Mỗi cột cộng tất cả sự kiện tại cùng khung giờ trong 30 ngày, không phải hoạt động của riêng một ngày. Đây là số sự kiện, không phải số người dùng." rows={analysis.hourly} detailPath="/thoi-gian">
          <OverviewHourlyChart data={analysis.hourly} peakHours={analysis.peakHours.map(row => row.hour)} />
        </OverviewDataPanel>
      <OverviewDataPanel kind="actions" title="Phân bố hành vi" note="Năm hành động · tỷ lệ trên tổng sự kiện." help="Chọn tên hành động để đọc số sự kiện và tỷ lệ. Mẫu số là tất cả sự kiện trong kỳ; một người dùng có thể tạo nhiều sự kiện. View là xem thông tin phim, play là phát phim; tỷ lệ này không phải tỷ lệ người dùng." rows={analysis.actions} detailPath="/hanh-vi">
        <Suspense fallback={<p className="donut-loading" role="status">Đang tải biểu đồ hành vi…</p>}><OverviewActionDonut data={analysis.actions} selectedAction={selectedAction} onSelect={setSelectedAction} /></Suspense>
      </OverviewDataPanel>
      <OverviewDataPanel kind="movies" className="overview-movies-panel" title="Top 5 phim" note="Xếp hạng theo sự kiện play, bao gồm các lần phát lặp lại." help="Độ dài thanh so với phim dẫn đầu trong Top 5. Số sự kiện play được giữ nguyên, không phải lượt xem duy nhất, số người xem hay số phiên. Bảng và CSV chỉ chứa đúng năm phim đang hiển thị." rows={movies} detailPath="/phim">
        <OverviewMovieRanking rows={movies} />
      </OverviewDataPanel>
    </div>
  </section>;
}
