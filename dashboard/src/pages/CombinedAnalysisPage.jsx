import { useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel, AnalysisTable } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import ReadingGuide from '../components/ReadingGuide.jsx';
import RankingChart from '../components/RankingChart.jsx';
import { loadCombinedAnalysis } from '../services/dashboardData.js';
import { hourLabel, selectCombinedHour } from '../services/combinedAnalysis.js';
import { number } from '../services/formatNumbers.js';

function CombinedContent() {
  const state = useDashboardData();
  const [hour, setHour] = useState(0);
  const [onlySelected, setOnlySelected] = useState(false);
  const selected = state.status === 'ready' ? selectCombinedHour(state.metrics, hour) : null;
  return <div className="analysis-page overview-page combined-page">
    <AnalysisPageHeader title="Phân tích kết hợp" description="Khám phá Top 3 phim theo số sự kiện phát trong từng khung giờ." />
    <p className="analysis-context">Khung giờ được cộng gộp trên toàn kỳ theo UTC+7, không phải riêng một ngày. Dữ liệu chỉ giữ Top 3 phim mỗi giờ.</p>
    <DataState />
    {selected && <div className="analysis-grid">
      <ChartPanel title={'Top 3 phim · ' + hourLabel(hour)} note="So sánh số sự kiện play và đọc số người dùng khác nhau trong từng nhóm phim–giờ." icon="combined">
        <div className="chart-controls"><div className="filter-field">
          <label htmlFor="combined-hour">Chọn khung giờ (UTC+7)</label>
          <select id="combined-hour" value={hour} onChange={event => setHour(Number(event.target.value))}>
            {state.metrics.byHour.map((group, index) => <option key={index} value={index}>{hourLabel(index)}</option>)}
          </select>
        </div></div>
        <RankingChart data={selected.movies} showDistinctUsers />
        <div className="combined-selected"><AnalysisTable kind="combined" data={selected.movies} /></div>
        <ReadingGuide><p>Người dùng khác nhau được đếm riêng cho mỗi phim trong mỗi giờ. Không cộng các nhóm để suy ra tổng người dùng. Sự kiện play có thể lặp lại trong cùng một phiên hoặc cùng một người dùng.</p></ReadingGuide>
      </ChartPanel>
      <ChartPanel title={'Nhận xét · ' + hourLabel(hour)} note="Cập nhật theo khung giờ đang chọn." icon="trophy" className="combined-observation">
        <p className="analysis-leader">{selected.leader.title}</p>
        <p>Dẫn đầu với <strong>{number(selected.leader.playCount)}</strong> sự kiện play và {number(selected.leader.distinctUsers)} người dùng khác nhau trong nhóm phim–giờ này.</p>
        <p>Tiếp theo là <strong>{selected.runnerUp.title}</strong> với {number(selected.runnerUp.playCount)} sự kiện play.</p>
        <p>{selected.gap === 0 ? 'Hai phim có cùng số sự kiện play; thứ hạng được phân định theo mã phim tăng dần.' : 'Chênh lệch là ' + number(selected.gap) + ' sự kiện play.'}</p>
        <p className="chart-note">Kết quả mô tả dữ liệu mô phỏng, không phản ánh sở thích người xem thật.</p>
      </ChartPanel>
      <ChartPanel className="analysis-wide" title="Tra cứu kết quả phim theo giờ" note="Toàn bộ kết quả đã xuất: 24 giờ, mỗi giờ 3 phim." icon="table">
        <div className="chart-controls">
          <label className="checkbox-field"><input id="combined-only-selected" type="checkbox" checked={onlySelected} onChange={event => setOnlySelected(event.target.checked)} /> Chỉ xem giờ đang chọn ({hourLabel(hour)})</label>
        </div>
        <p className="chart-note" role="status">Đang hiển thị {onlySelected ? selected.movies.length : state.metrics.rows.length}/{state.metrics.rows.length} dòng. Cuộn bảng để tra cứu.</p>
        <div className="combined-browse"><AnalysisTable kind="combined" data={onlySelected ? selected.movies : state.metrics.rows} /></div>
      </ChartPanel>
    </div>}
  </div>;
}

export default function CombinedAnalysisPage() {
  return <DashboardDataProvider loader={loadCombinedAnalysis}><CombinedContent /></DashboardDataProvider>;
}
