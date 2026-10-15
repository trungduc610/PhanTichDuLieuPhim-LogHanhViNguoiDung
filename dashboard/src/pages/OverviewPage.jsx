import MetricCard from '../components/MetricCard.jsx';
import OverviewHighlights from '../components/OverviewHighlights.jsx';
import OverviewSummaryCharts from '../components/OverviewSummaryCharts.jsx';
import { DataState, useDashboardData } from '../components/DashboardData.jsx';
import '../styles/overview.css';
import { DataScope, useSource } from '../components/DataSource.jsx';

export default function OverviewPage() {
  const state = useDashboardData();
  const source = useSource();
  return <div className="overview-page">
    <header className="overview-heading">
      <p className="eyebrow">DỮ LIỆU PHIM & HÀNH VI</p>
      <h1>Tổng quan</h1>
      <p className="intro">Khám phá hoạt động sử dụng hệ thống, các phim dẫn đầu và những khung giờ nổi bật.</p>
      <DataScope />
    </header>
    <DataState />
    {state.status === 'ready' && <>
      <section className="metrics-grid" aria-label="Chỉ số tổng quan">
        <MetricCard icon="events" title="Tổng số sự kiện" value={state.metrics.totalEvents} description="Tất cả hành động được ghi nhận trong kỳ." />
        <MetricCard icon="users" title="Người dùng khác nhau" value={state.metrics.distinctUsers} description="Mỗi người dùng chỉ tính một lần trong toàn kỳ." />
        <MetricCard icon="sessions" title="Phiên được ghi nhận" value={state.metrics.totalSessions} description="Tổng số phiên truy cập của các người dùng." />
        <MetricCard icon="play" title="Phiên có phát phim" value={state.metrics.playedSessions} description="Có ít nhất một lần phát; mỗi phiên chỉ tính một lần." />
      </section>
      <OverviewHighlights analysis={state.metrics.analysis} />
      <OverviewSummaryCharts analysis={state.metrics.analysis} />
    </>}
    <details className="overview-source">
      <summary>Nguồn dữ liệu và cách đọc chỉ số</summary>
      <p>Dữ liệu hành vi mô phỏng, không đại diện cho sở thích của người xem thật. Các chỉ số phản ánh toàn bộ kỳ, không phải một ngày riêng lẻ.</p>
      <p>Một phiên có thể có nhiều sự kiện phát (play). Người dùng khác nhau chỉ được đếm một lần trong toàn kỳ; phiên có phát phim chỉ được đếm một lần khi có ít nhất một play.</p>
      <p>Số phiên trong nguồn được đếm theo (runId, sessionId) trong từng người dùng. Tổng phiên trên trang là tổng các số đếm đó, không phải số sự kiện play.</p>
      <p>Nguồn: <code>evidence/week2-tv2/{source?.runId}/dashboard/</code>. Frontend đọc các bản sao JSON đã kiểm hash, giữ nguyên kết quả Spark.</p>
      <ul><li><code>stats_action_distribution.json</code>: tổng sự kiện và phân bố hành động.</li><li><code>kmeans_assignments.json</code>: người dùng, số phiên và số phiên có play.</li><li><code>stats_hourly_activity.json</code>: số sự kiện theo giờ Việt Nam, cộng gộp toàn kỳ.</li><li><code>stats_top_movies_by_play.json</code>: xếp hạng phim theo sự kiện phát.</li></ul>
    </details>
    </div>;
}
