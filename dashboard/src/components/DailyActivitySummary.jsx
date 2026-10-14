import { DashboardDataProvider, DataState, useDashboardData } from './DashboardData.jsx';
import { loadDailyActivity } from '../services/dashboardData.js';
import { displayDate } from '../services/dailyActivity.js';
import { number } from '../services/formatNumbers.js';

function DailyActivityContent() {
  const state = useDashboardData();
  const data = state.metrics;
  return <aside className="data-note daily-activity" aria-label="Người dùng hoạt động hằng ngày">
    <strong>Người dùng hoạt động hằng ngày (DAU)</strong>
    <DataState />
    {state.status === 'ready' && <>
      <p>Từ {displayDate(data.firstDate)} đến {displayDate(data.lastDate)}, dữ liệu gồm {number(data.days)} ngày.
        {' '}{data.min === data.max ? `Mỗi ngày có ${number(data.min)} người dùng hoạt động; chuỗi DAU không thay đổi trong kỳ.` : `DAU dao động từ ${number(data.min)} đến ${number(data.max)} người dùng/ngày.`}</p>
      <p>Mỗi người dùng có ít nhất một sự kiện được tính một lần trong ngày, bao gồm mọi loại hành động, không chỉ play. Không cộng DAU giữa các ngày để suy ra người dùng khác nhau toàn kỳ.</p>
    </>}
  </aside>;
}

export default function DailyActivitySummary() {
  return <DashboardDataProvider loader={loadDailyActivity}><DailyActivityContent /></DashboardDataProvider>;
}
