import MetricCard from '../components/MetricCard.jsx';
import OverviewCharts from '../components/OverviewCharts.jsx';
import { DataState, useDashboardData } from '../components/DashboardData.jsx';

export default function OverviewPage() {
  const state = useDashboardData();
  return <>
    <h1>Tổng quan</h1>
    <p className="intro">Hoạt động xem phim trong kỳ phân tích.</p>
    <DataState />
    {state.status === 'ready' && <>
      <section className="metrics-grid" aria-label="Chỉ số tổng quan">
        <MetricCard title="Tổng số sự kiện" value={state.metrics.totalEvents} description="Tất cả hành động được ghi nhận trong kỳ." />
        <MetricCard title="Người dùng khác nhau" value={state.metrics.distinctUsers} description="Mỗi người dùng chỉ tính một lần trong toàn kỳ." />
        <MetricCard title="Phiên được ghi nhận" value={state.metrics.totalSessions} description="Tổng số phiên truy cập của các người dùng." />
        <MetricCard title="Phiên có phát phim" value={state.metrics.playedSessions} description="Có ít nhất một lần phát; mỗi phiên chỉ tính một lần." />
      </section>
      <OverviewCharts analysis={state.metrics.analysis} />
    </>}
    <aside className="data-note">
      <strong>Nguồn dữ liệu: kết quả phân tích đợt tv2-4ed70c10cd84</strong>
      <p>Các chỉ số phản ánh toàn bộ kỳ. Một phiên có thể có nhiều sự kiện phát (play); số sự kiện không phải số phiên hay số người dùng.</p>
    </aside>
  </>;
}
