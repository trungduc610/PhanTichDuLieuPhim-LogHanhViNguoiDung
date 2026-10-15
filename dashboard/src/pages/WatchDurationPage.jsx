import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import ReadingGuide from '../components/ReadingGuide.jsx';
import MetricCard from '../components/MetricCard.jsx';
import ScrollableTable from '../components/ScrollableTable.jsx';
import { loadWatchDuration } from '../services/dashboardData.js';
import { durationFields } from '../services/watchDuration.js';
import { number } from '../services/formatNumbers.js';
import { useState } from 'react';
import ComparisonBarChart from '../components/ComparisonBarChart.jsx';

function WatchDurationContent() {
  const state = useDashboardData();
  const data = state.metrics;
  const [stat,setStat] = useState('mean');
  const metric = durationFields.find(row => row.key === stat);
  return <div className="analysis-page overview-page duration-page">
    <AnalysisPageHeader title="Thời lượng xem" description="So sánh thời lượng trên toàn bộ sự kiện và những đoạn xem có thời lượng lớn hơn 0." />
    <p className="analysis-context"><strong>Đơn vị gốc: giây.</strong> Thống kê theo bản ghi sự kiện, không phải thời lượng trung bình mỗi phiên xem.</p>
    <DataState />
    {state.status === 'ready' && <>
      <section className="metrics-grid duration-metrics" aria-label="Số bản ghi và trung bình thời lượng">
        <MetricCard icon="events" title="Toàn bộ sự kiện · Số bản ghi" value={data.allEvents.count} description="Bao gồm cả thời lượng bằng 0." />
        <MetricCard icon="duration" title="Toàn bộ sự kiện · Trung bình" value={data.allEvents.mean} unit="giây" description="Trên tất cả bản ghi sự kiện." />
        <MetricCard icon="events" title="Đoạn xem · Số bản ghi" value={data.watchSegments.count} description="Chỉ các bản ghi có thời lượng lớn hơn 0." />
        <MetricCard icon="duration" title="Đoạn xem · Trung bình" value={data.watchSegments.mean} unit="giây" description="Trên các bản ghi có thời lượng dương." />
      </section>
      <div className="analysis-grid">
        <ChartPanel className="analysis-wide" title="Biểu đồ so sánh thời lượng" note="So sánh cùng một chỉ số bằng giây; không cộng hai phạm vi bản ghi." icon="chart">
          <div className="chart-controls"><div className="filter-field">
            <label htmlFor="duration-stat">Chỉ số thời lượng</label>
            <select id="duration-stat" value={stat} onChange={event => setStat(event.target.value)}>
              {durationFields.filter(row => row.unit === 'giây').map(row => <option key={row.key} value={row.key}>{row.label}</option>)}
            </select>
          </div></div>
          <div data-chart="watch-duration" data-statistic={stat}>
            <ComparisonBarChart data={[{ cluster:0,label:'Toàn bộ',value:data.allEvents[stat] },
              { cluster:1,label:'Đoạn dương',value:data.watchSegments[stat] }]}
              dataKey="value" unit="giây" title={metric.label} itemName="nhóm" />
            <div className="duration-values" aria-label="Giá trị chỉ số đang chọn">
              <span data-duration-scope="all_events">Toàn bộ: <strong>{number(data.allEvents[stat])} giây</strong></span>
              <span data-duration-scope="watch_segments">Đoạn dương: <strong>{number(data.watchSegments[stat])} giây</strong></span>
            </div>
          </div>
        </ChartPanel>
        <ChartPanel title="So sánh thống kê thời lượng" note="Đơn vị giây; làm tròn tối đa 3 chữ số thập phân. Số bản ghi giữ nguyên số nguyên." icon="table">
          <ScrollableTable label="Bảng thống kê thời lượng">
            <table className="duration-table"><caption>Thống kê trên bản ghi sự kiện — nguồn stats_watch_duration_summary.json</caption>
              <thead><tr><th scope="col">Chỉ số</th><th scope="col">Toàn bộ sự kiện</th><th scope="col">Đoạn xem có thời lượng &gt; 0</th></tr></thead>
              <tbody>{durationFields.map(({ key, label, unit }) => <tr key={key} data-stat={key}>
                <th scope="row">{label} ({unit})</th>
                <td title={String(data.allEvents[key])}>{number(data.allEvents[key])}</td>
                <td title={String(data.watchSegments[key])}>{number(data.watchSegments[key])}</td>
              </tr>)}</tbody>
            </table>
          </ScrollableTable>
          <ReadingGuide><p>Toàn bộ sự kiện gồm cả bản ghi có thời lượng bằng 0. Nhóm đoạn xem chỉ gồm các sự kiện có thời lượng lớn hơn 0 và là một phần của nhóm toàn bộ; không cộng số bản ghi của hai nhóm.</p>
            <p>Trung vị được Spark tính xấp xỉ; độ lệch chuẩn là độ lệch chuẩn mẫu, thể hiện mức biến thiên của thời lượng quanh trung bình.</p>
          </ReadingGuide>
        </ChartPanel>
        <ChartPanel title="Nhận xét từ dữ liệu" note="Hai nhóm có phạm vi bản ghi khác nhau." icon="info" className="duration-observation">
          <p>Trung bình nhóm đoạn xem {data.meanDifference === 0 ? 'bằng nhóm toàn bộ sự kiện.' : (data.meanDifference > 0 ? 'cao hơn' : 'thấp hơn') + ' nhóm toàn bộ sự kiện ' + number(Math.abs(data.meanDifference)) + ' giây.'}</p>
          <p>Trung vị của toàn bộ sự kiện là <strong>{number(data.allEvents.median)} giây</strong>, trong khi nhóm đoạn xem là <strong>{number(data.watchSegments.median)} giây</strong>.</p>
          <p className="chart-note">Thống kê trên toàn bộ sự kiện bao gồm các thời lượng bằng 0. Nhận xét mô tả dữ liệu mô phỏng, không suy ra thời lượng mỗi phiên hay sở thích người xem thật.</p>
        </ChartPanel>
      </div>
    </>}
  </div>;
}

export default function WatchDurationPage() {
  return <DashboardDataProvider loader={loadWatchDuration}><WatchDurationContent /></DashboardDataProvider>;
}
