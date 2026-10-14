import { DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel, ActionChart, HourlyChart, MovieChart, AnalysisTable } from '../components/OverviewCharts.jsx';
import DailyActivitySummary from '../components/DailyActivitySummary.jsx';

const sections = {
  movies: {
    title: 'Phân tích phim', key: 'movies', Chart: MovieChart,
    note: 'Xếp hạng tối đa 20 phim từ kết quả đã xuất, theo số sự kiện phát (play). Một phiên hoặc người dùng có thể phát phim nhiều lần.',
  },
  actions: {
    title: 'Hành vi người dùng', key: 'actions', Chart: ActionChart,
    note: 'Phân bố 5 loại hành động theo số sự kiện và tỷ lệ trên tổng sự kiện. Một người dùng có thể tạo nhiều sự kiện; đây không phải tỷ lệ người dùng.',
  },
  hourly: {
    title: 'Hoạt động theo thời gian', key: 'hourly', Chart: HourlyChart,
    note: 'Số sự kiện của 24 khung giờ, cộng gộp tất cả ngày trong kỳ theo giờ Việt Nam (UTC+7). Người dùng được đếm riêng trong từng giờ; không cộng các giờ để tính người dùng toàn kỳ.',
  },
};

export default function AnalysisPage({ kind }) {
  const state = useDashboardData();
  const { title, key, Chart, note } = sections[kind];
  const data = state.metrics?.analysis[key];
  return <><h1>{title}</h1><DataState />
    {kind === 'hourly' && <DailyActivitySummary />}
    {state.status === 'ready' && <ChartPanel title="Kết quả trong kỳ" note={note}>
      <Chart data={data} />
      <AnalysisTable kind={kind} data={data} />
    </ChartPanel>}
  </>;
}
