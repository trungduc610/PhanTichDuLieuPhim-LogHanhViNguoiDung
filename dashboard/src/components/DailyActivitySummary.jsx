import { DashboardDataProvider, DataState, useDashboardData } from './DashboardData.jsx';
import { loadDailyActivity } from '../services/dashboardData.js';
import { displayDate } from '../services/dailyActivity.js';
import { number } from '../services/formatNumbers.js';
import Icon from './Icon.jsx';
import ReadingGuide from './ReadingGuide.jsx';
import DailyActivityChart from './DailyActivityChart.jsx';
import ScrollableTable from './ScrollableTable.jsx';

function DailyActivityContent() {
  const state = useDashboardData();
  const data = state.metrics;
  return <aside className="data-note daily-activity" aria-label="Người dùng hoạt động hằng ngày">
    <h2><Icon name="users" />Người dùng hoạt động hằng ngày</h2>
    <DataState />
    {state.status === 'ready' && <>
      <div className="daily-value">{data.min === data.max ? number(data.min) : `${number(data.min)}–${number(data.max)}`} <span>người dùng/ngày</span></div>
      <p>Từ {displayDate(data.firstDate)} đến {displayDate(data.lastDate)}, dữ liệu gồm {number(data.days)} ngày.
        {' '}{data.min === data.max ? `Mỗi ngày có ${number(data.min)} người dùng hoạt động; chuỗi DAU không thay đổi trong kỳ.` : `DAU dao động từ ${number(data.min)} đến ${number(data.max)} người dùng/ngày.`}</p>
      <DailyActivityChart rows={data.rows} />
      <details><summary>Bảng người dùng theo ngày</summary><ScrollableTable label="Bảng DAU">
        <table><caption>Người dùng hoạt động theo ngày Việt Nam</caption>
          <thead><tr><th scope="col">Ngày</th><th scope="col">Người dùng</th></tr></thead>
          <tbody>{data.rows.map(row => <tr key={row.date}><th scope="row">{displayDate(row.date)}</th><td>{number(row.activeUsers)}</td></tr>)}</tbody>
        </table>
      </ScrollableTable></details>
      <ReadingGuide title="DAU được tính thế nào?"><p>Mỗi người dùng có ít nhất một sự kiện được tính một lần trong ngày, bao gồm mọi loại hành động, không chỉ play. Không cộng DAU giữa các ngày để suy ra người dùng khác nhau toàn kỳ.</p><p>Kết quả mô tả dữ liệu mô phỏng, không chứng minh hoạt động của người xem thật.</p></ReadingGuide>
    </>}
  </aside>;
}

export default function DailyActivitySummary() {
  return <DashboardDataProvider loader={loadDailyActivity}><DailyActivityContent /></DashboardDataProvider>;
}
