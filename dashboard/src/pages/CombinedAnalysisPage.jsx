import { useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel, HorizontalPlayChart, AnalysisTable } from '../components/OverviewCharts.jsx';
import { loadCombinedAnalysis } from '../services/dashboardData.js';
import { hourLabel, selectCombinedHour } from '../services/combinedAnalysis.js';
import { number } from '../services/formatNumbers.js';

function CombinedContent() {
  const state = useDashboardData();
  const [hour, setHour] = useState(0);
  const [onlySelected, setOnlySelected] = useState(false);
  const selected = state.status === 'ready' ? selectCombinedHour(state.metrics, hour) : null;
  return <>
    <h1>Phân tích kết hợp</h1>
    <p className="intro">Top 3 phim theo số sự kiện play trong từng khung giờ.</p>
    <aside className="data-note scope-note">
      <strong>Phim và khung giờ trong toàn kỳ</strong>
      <p>Kết quả gộp theo giờ Việt Nam (UTC+7) trên toàn kỳ 01/09/2026–30/09/2026, không phải riêng một ngày. Dữ liệu đã xuất chỉ giữ Top 3 phim mỗi giờ.</p>
      <p>Người dùng khác nhau được đếm riêng cho mỗi phim trong mỗi giờ. Không cộng các nhóm để suy ra tổng người dùng. Sự kiện play có thể lặp lại trong cùng một phiên hoặc cùng một người dùng.</p>
    </aside>
    <DataState />
    {selected && <>
      <ChartPanel title={`Top 3 phim · ${hourLabel(hour)}`} note="Biểu đồ so sánh số sự kiện play; tooltip và bảng bên dưới có số người dùng khác nhau cho từng phim.">
        <div className="chart-controls">
          <label htmlFor="combined-hour">Chọn khung giờ (UTC+7)</label>
          <select id="combined-hour" value={hour} onChange={(event) => setHour(Number(event.target.value))}>
            {state.metrics.byHour.map((group, index) => <option key={index} value={index}>{hourLabel(index)}</option>)}
          </select>
        </div>
        <HorizontalPlayChart data={selected.movies} showDistinctUsers />
        <div className="combined-selected"><AnalysisTable kind="combined" data={selected.movies} /></div>
      </ChartPanel>
      <section className="chart-panel combined-observation" aria-label="Nhận xét theo giờ">
        <h2>Nhận xét · {hourLabel(hour)}</h2>
        <p><strong>{selected.leader.title}</strong> dẫn đầu với {number(selected.leader.playCount)} sự kiện play và {number(selected.leader.distinctUsers)} người dùng khác nhau trong nhóm phim–giờ này.</p>
        <p>Phim tiếp theo là <strong>{selected.runnerUp.title}</strong> với {number(selected.runnerUp.playCount)} sự kiện play.
          {' '}{selected.gap === 0 ? 'Hai phim có cùng số sự kiện play; thứ hạng được phân định theo mã phim tăng dần.' : `Chênh lệch là ${number(selected.gap)} sự kiện play.`}</p>
        <p className="chart-note">Nhận xét chỉ mô tả kết quả mô phỏng đã xuất, không phản ánh sở thích người xem thật.</p>
      </section>
      <ChartPanel title="Tra cứu kết quả phim theo giờ" note="Bảng chứa đủ 72 dòng đã xuất: 24 giờ, mỗi giờ 3 phim. Có thể chỉ xem các dòng của giờ đang chọn.">
        <div className="chart-controls">
          <label><input id="combined-only-selected" type="checkbox" checked={onlySelected} onChange={(event) => setOnlySelected(event.target.checked)} /> Chỉ xem giờ đang chọn ({hourLabel(hour)})</label>
        </div>
        <p className="chart-note">Đang hiển thị {onlySelected ? selected.movies.length : state.metrics.rows.length}/72 dòng. Cuộn bảng để tra cứu.</p>
        <div className="combined-browse"><AnalysisTable kind="combined" data={onlySelected ? selected.movies : state.metrics.rows} /></div>
      </ChartPanel>
    </>}
  </>;
}

export default function CombinedAnalysisPage() {
  return <DashboardDataProvider loader={loadCombinedAnalysis}><CombinedContent /></DashboardDataProvider>;
}
