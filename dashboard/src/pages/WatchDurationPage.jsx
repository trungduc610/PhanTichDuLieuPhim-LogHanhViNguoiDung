import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel } from '../components/OverviewCharts.jsx';
import MetricCard from '../components/MetricCard.jsx';
import { loadWatchDuration } from '../services/dashboardData.js';
import { durationFields } from '../services/watchDuration.js';
import { number } from '../services/formatNumbers.js';

function WatchDurationContent() {
  const state = useDashboardData();
  const data = state.metrics;
  return <>
    <h1>Thời lượng xem</h1>
    <p className="intro">So sánh thời lượng ghi nhận trên từng sự kiện trong kỳ phân tích.</p>
    <aside className="data-note scope-note">
      <strong>Đơn vị gốc: giây</strong>
      <p>Toàn bộ sự kiện gồm cả bản ghi có thời lượng bằng 0. Nhóm đoạn xem chỉ gồm các sự kiện có thời lượng lớn hơn 0.</p>
      <p>Các thống kê được tính theo bản ghi sự kiện, không phải theo phiên xem hay người dùng. Nhóm đoạn xem là một phần của toàn bộ sự kiện, không cộng số bản ghi của hai nhóm.</p>
    </aside>
    <DataState />
    {state.status === 'ready' && <>
      <section className="metrics-grid duration-metrics" aria-label="Số bản ghi và trung bình thời lượng">
        <MetricCard title="Toàn bộ sự kiện · Số bản ghi" value={data.allEvents.count} description="Bao gồm cả thời lượng bằng 0." />
        <MetricCard title="Toàn bộ sự kiện · Trung bình" value={data.allEvents.mean} unit="giây" description="Trung bình thời lượng trên tất cả bản ghi." />
        <MetricCard title="Đoạn xem · Số bản ghi" value={data.watchSegments.count} description="Chỉ các bản ghi có thời lượng lớn hơn 0." />
        <MetricCard title="Đoạn xem · Trung bình" value={data.watchSegments.mean} unit="giây" description="Trung bình thời lượng trên các bản ghi dương." />
      </section>
      <ChartPanel title="So sánh thống kê thời lượng" note="Giá trị thời lượng hiển thị bằng giây, làm tròn tối đa 3 chữ số thập phân; số bản ghi giữ nguyên số nguyên.">
        <div className="table-scroll" tabIndex={0} aria-label="Bảng thời lượng có thể cuộn ngang">
          <table className="duration-table"><caption>Thống kê trên bản ghi sự kiện — nguồn stats_watch_duration_summary.json</caption>
            <thead><tr><th scope="col">Chỉ số</th><th scope="col">Toàn bộ sự kiện</th><th scope="col">Đoạn xem có thời lượng &gt; 0</th></tr></thead>
            <tbody>{durationFields.map(({ key, label, unit }) => <tr key={key} data-stat={key}>
              <th scope="row">{label} ({unit})</th>
              <td title={String(data.allEvents[key])}>{number(data.allEvents[key])}</td>
              <td title={String(data.watchSegments[key])}>{number(data.watchSegments[key])}</td>
            </tr>)}</tbody>
          </table>
        </div>
        <p className="chart-note">Trung vị được Spark tính xấp xỉ; độ lệch chuẩn là độ lệch chuẩn mẫu, thể hiện mức biến thiên của thời lượng quanh trung bình.</p>
      </ChartPanel>
      <section className="chart-panel duration-observation" aria-label="Nhận xét thời lượng">
        <h2>Nhận xét từ dữ liệu</h2>
        <p>Trung bình của nhóm đoạn xem {data.meanDifference === 0 ? 'bằng nhóm toàn bộ sự kiện.' : `${data.meanDifference > 0 ? 'cao hơn' : 'thấp hơn'} nhóm toàn bộ sự kiện ${number(Math.abs(data.meanDifference))} giây.`}</p>
        <p>Trung vị của toàn bộ sự kiện là {number(data.allEvents.median)} giây, trong khi nhóm đoạn xem là {number(data.watchSegments.median)} giây. Hai nhóm có phạm vi bản ghi khác nhau; thống kê trên toàn bộ sự kiện bao gồm các thời lượng bằng 0.</p>
        <p className="chart-note">Nhận xét chỉ mô tả dữ liệu hành vi mô phỏng đã xuất, không suy ra thời lượng mỗi phiên hoặc sở thích của người xem thật.</p>
      </section>
    </>}
  </>;
}

export default function WatchDurationPage() {
  return <DashboardDataProvider loader={loadWatchDuration}><WatchDurationContent /></DashboardDataProvider>;
}
