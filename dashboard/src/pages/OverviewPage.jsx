import MetricCard from '../components/MetricCard.jsx';
import OverviewHighlights from '../components/OverviewHighlights.jsx';
import OverviewSummaryCharts from '../components/OverviewSummaryCharts.jsx';
import { DataState, useDashboardData } from '../components/DashboardData.jsx';
import '../styles/overview.css';
import { DataScope, useSource } from '../components/DataSource.jsx';
import MetricExplanation from '../components/MetricExplanation.jsx';
import OverviewMethodology, { OverviewSessions } from '../components/OverviewMethodology.jsx';
import { definitions } from '../content/overviewContent.js';
import '../styles/overview-ux.css';
import { useRef } from 'react';

export default function OverviewPage() {
  const state = useDashboardData();
  const source = useSource();
  const metricDetails = useRef(null);
  return <div className="overview-page overview-home">
    <header className="overview-heading">
      <p className="eyebrow">DỮ LIỆU PHIM & HÀNH VI</p>
      <h1>Tổng quan hoạt động xem phim</h1>
      <p className="intro">Tổng hợp kết quả phân tích dữ liệu phim và hoạt động của người dùng trong kỳ.</p>
      <DataScope syntheticLabel="Log hành vi mô phỏng" />
      <p className="overview-origin">Thông tin phim: MovieLens · Kết quả xử lý theo lô</p>
    </header>
    <DataState />
    {state.status === 'ready' && <>
      <section className="metrics-grid" aria-label="Chỉ số tổng quan">
        <MetricCard icon="events" title={definitions.totalActions.title} value={state.metrics.totalEvents} description="Tất cả hành động được ghi nhận trong kỳ." explanation={<MetricExplanation definition={definitions.totalActions} target={metricDetails} />} />
        <MetricCard icon="users" title={definitions.users.title} value={state.metrics.distinctUsers} description="Mỗi mã người dùng chỉ tính một lần trong kỳ." explanation={<MetricExplanation definition={definitions.users} target={metricDetails} />} />
        <MetricCard icon="play" title={definitions.plays.title} value={state.metrics.analysis.actions.find(row => row.action === 'play').count} description="Số lần ghi nhận hành động phát phim trong kỳ." explanation={<MetricExplanation definition={definitions.plays} target={metricDetails} />} />
      </section>
      <div ref={metricDetails} className="independent-explanations" />
      <OverviewSessions metrics={state.metrics} />
      <OverviewHighlights analysis={state.metrics.analysis} />
      <OverviewSummaryCharts analysis={state.metrics.analysis} />
    </>}
    {source && <OverviewMethodology source={source} />}
    </div>;
}
