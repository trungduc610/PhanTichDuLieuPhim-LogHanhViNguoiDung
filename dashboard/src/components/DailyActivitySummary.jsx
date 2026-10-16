import { DashboardDataProvider, DataState, useDashboardData } from './DashboardData.jsx';
import { loadDailyActivity } from '../services/dashboardData.js';
import { displayDate } from '../services/dailyActivity.js';
import { number } from '../services/formatNumbers.js';
import Icon from './Icon.jsx';
import AnalysisExplanation from './AnalysisExplanation.jsx';
import DailyActivityChart from './DailyActivityChart.jsx';
import ScrollableTable from './ScrollableTable.jsx';

function DailyActivityContent({ explanationTarget }) {
  const state = useDashboardData();
  const data = state.metrics;
  return <aside className="data-note daily-activity" aria-label="Người dùng hoạt động hằng ngày">
    <h2><Icon name="users" />Người dùng hoạt động hằng ngày</h2>
    <DataState />
    {state.status === 'ready' && <>
      <div className="daily-value">{data.min === data.max ? number(data.min) : `${number(data.min)}–${number(data.max)}`} <span>người dùng/ngày</span></div>
      <p>Từ {displayDate(data.firstDate)} đến {displayDate(data.lastDate)}, dữ liệu gồm {number(data.days)} ngày.
        {' '}{data.min === data.max ? `Mỗi ngày có ${number(data.min)} người dùng hoạt động; chuỗi DAU không thay đổi trong kỳ.` : `DAU dao động từ ${number(data.min)} đến ${number(data.max)} người dùng/ngày.`}</p>
      <DailyActivityChart rows={data.rows} compactHelp />
      <details><summary>Bảng người dùng theo ngày</summary><ScrollableTable label="Bảng DAU">
        <table><caption>Người dùng hoạt động theo ngày Việt Nam</caption>
          <thead><tr><th scope="col">Ngày</th><th scope="col">Người dùng</th></tr></thead>
          <tbody>{data.rows.map(row => <tr key={row.date}><th scope="row">{displayDate(row.date)}</th><td>{number(row.activeUsers)}</td></tr>)}</tbody>
        </table>
      </ScrollableTable></details>
      <AnalysisExplanation title="Người dùng hoạt động hằng ngày" target={explanationTarget}
        help="DAU là số người dùng có ít nhất một hành động trong ngày. Mỗi mã người dùng chỉ tính một lần trong ngày, bao gồm mọi loại hành động, không chỉ phát phim. Không cộng DAU giữa các ngày để suy ra số người dùng duy nhất toàn kỳ. Đây là số người dùng, khác với số hành động ở biểu đồ theo giờ."
        technical="Nguồn: stats_daily_active_users.json; Spark nhóm ngày theo Asia/Ho_Chi_Minh và đếm userId phân biệt thành activeUsers. Các giá trị nhỏ nhất, lớn nhất và khoảng ngày dùng service DAU hiện có. Chuỗi mô phỏng không chứng minh tăng trưởng người dùng ngoài đời."
        instructions="Di chuột hoặc chạm để đọc từng ngày. Tab vào biểu đồ, dùng ←/→ đổi ngày, Home/End đến đầu/cuối và Esc bỏ đánh dấu. Mở Bảng người dùng theo ngày để đối chiếu đầy đủ các ngày." />
    </>}
  </aside>;
}

export default function DailyActivitySummary({ explanationTarget }) {
  return <DashboardDataProvider loader={loadDailyActivity}><DailyActivityContent explanationTarget={explanationTarget} /></DashboardDataProvider>;
}
