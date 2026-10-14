import { lazy, Suspense, useState } from 'react';
import { DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel, AnalysisTable } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import ReadingGuide from '../components/ReadingGuide.jsx';
import RankingChart from '../components/RankingChart.jsx';
import OverviewHourlyChart from '../components/OverviewHourlyChart.jsx';
import DailyActivitySummary from '../components/DailyActivitySummary.jsx';
import { number, percent } from '../services/formatNumbers.js';
const ActionDonut = lazy(() => import('../components/OverviewActionDonut.jsx'));

const sections = {
  movies: { title: 'Phân tích phim', description: 'Khám phá các phim dẫn đầu theo số sự kiện phát trong kỳ.', chartTitle: 'Xếp hạng phim', icon: 'film', note: 'Tối đa 20 phim từ kết quả Spark đã xuất. Sự kiện play bao gồm các lần phát lặp lại.' },
  actions: { title: 'Hành vi người dùng', description: 'Tìm hiểu năm hành động được ghi nhận và tỷ lệ của chúng trong tổng sự kiện.', chartTitle: 'Phân bố hành vi', icon: 'activity', note: 'Tỷ lệ trên tổng sự kiện trong kỳ, không phải tỷ lệ người dùng.' },
  hourly: { title: 'Hoạt động theo thời gian', description: 'Khám phá hoạt động theo 24 khung giờ và số người dùng hoạt động hằng ngày.', chartTitle: 'Hoạt động theo giờ', icon: 'clock', note: 'Cộng gộp toàn kỳ UTC+7. Cột xanh đậm: giờ cao điểm; cột có viền: giờ đang xem.' },
};

export default function AnalysisPage({ kind }) {
  const state = useDashboardData();
  const [selectedAction, setSelectedAction] = useState(null);
  const section = sections[kind];
  const analysis = state.metrics?.analysis;
  const data = analysis?.[kind];
  return <div className={'analysis-page overview-page ' + kind + '-page'}>
    <AnalysisPageHeader title={section.title} description={section.description} />
    <DataState />
    {state.status === 'ready' && <div className="analysis-grid">
      <ChartPanel title={section.chartTitle} note={section.note} icon={section.icon}>
        {kind === 'movies' ? <RankingChart data={data} />
          : kind === 'actions' ? <Suspense fallback={<p role="status" className="donut-loading">Đang tải biểu đồ hành vi…</p>}>
            <ActionDonut data={data} selectedAction={selectedAction ?? data[0].action} onSelect={setSelectedAction} />
          </Suspense> : <OverviewHourlyChart data={data} peakHours={analysis.peakHours.map(row => row.hour)} />}
      </ChartPanel>
      {kind === 'actions' ? <ChartPanel title="Số lượng và tỷ lệ" note="Đủ năm hành động trong nguồn dữ liệu." icon="table">
        <AnalysisTable kind={kind} data={data} />
        <ReadingGuide><p>Một người dùng có thể tạo nhiều sự kiện. View là xem thông tin phim; play là phát phim. Mẫu số của tỷ lệ là tất cả sự kiện trong kỳ.</p></ReadingGuide>
      </ChartPanel> : kind === 'hourly' ? <DailyActivitySummary /> : <ChartPanel title="Phim dẫn đầu" note="Nhận xét từ dữ liệu mô phỏng." icon="trophy">
        <p className="analysis-leader">{data[0].title}</p>
        <p><strong>{number(data[0].playCount)}</strong> sự kiện play trong kỳ.</p>
        <p className="chart-note">Danh sách xếp hạng chỉ gồm các phim đã được xuất, không phải toàn bộ danh mục phim của hệ thống.</p>
        <ReadingGuide><p>Sự kiện play không phải lượt xem duy nhất, số người xem hoặc số phiên. Một phiên hoặc người dùng có thể phát phim nhiều lần.</p><p>Các kết quả mô tả dữ liệu mô phỏng, không đại diện sở thích người xem thật.</p></ReadingGuide>
      </ChartPanel>}
      {kind !== 'actions' && <ChartPanel className="analysis-wide" title={kind === 'movies' ? 'Bảng xếp hạng đầy đủ' : 'Bảng hoạt động theo giờ'} note={'Gồm ' + data.length + ' dòng trong kết quả đã xuất; cuộn trong bảng để tra cứu.'} icon="table">
        <AnalysisTable kind={kind} data={data} />
        <ReadingGuide>{kind === 'movies' ? <p>Số sự kiện play bao gồm phát lặp lại, không dùng thay cho số người dùng hoặc phiên xem.</p>
          : <p>Mỗi khung giờ cộng tất cả ngày trong kỳ. Người dùng khác nhau được đếm riêng trong từng giờ; không cộng các giờ để suy ra tổng người dùng toàn kỳ.</p>}</ReadingGuide>
      </ChartPanel>}
      {kind === 'actions' && <p className="analysis-context analysis-wide">Hành động có nhiều sự kiện nhất là <strong>{data[0].label}</strong>: {number(data[0].count)} sự kiện · {percent(data[0].percentage)} tổng sự kiện. Kết quả mô tả dữ liệu mô phỏng.</p>}
    </div>}
  </div>;
}
