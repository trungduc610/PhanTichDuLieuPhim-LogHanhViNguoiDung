import { useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel, AnalysisTable } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import ReadingGuide from '../components/ReadingGuide.jsx';
import RankingChart from '../components/RankingChart.jsx';
import { loadGenres } from '../services/dashboardData.js';
import { selectGenres } from '../services/genreAnalysis.js';
import { number } from '../services/formatNumbers.js';

function GenresContent() {
  const state = useDashboardData();
  const [limit, setLimit] = useState('10');
  const data = state.metrics;
  const visible = state.status === 'ready' ? selectGenres(data.genres, limit) : [];
  return <div className="analysis-page overview-page genres-page">
    <AnalysisPageHeader title="Phân tích thể loại" description="So sánh số sự kiện phát phim được ghi nhận theo thể loại trong kỳ." />
    <p className="analysis-context">Một phim có thể thuộc nhiều thể loại. Một sự kiện play có thể được tính vào nhiều nhóm; tổng các nhóm không phải tổng play độc lập.</p>
    <DataState />
    {state.status === 'ready' && <div className="analysis-grid">
      <ChartPanel title="Xếp hạng thể loại" note="Sắp xếp theo số sự kiện play; lựa chọn chỉ thay đổi số thể loại trên biểu đồ." icon="genre">
        <div className="chart-controls"><div className="filter-field">
          <label htmlFor="genre-limit">Thể loại trên biểu đồ</label>
          <select id="genre-limit" value={limit} onChange={event => setLimit(event.target.value)}>
            <option value="5">Top 5</option><option value="10">Top 10</option><option value="all">Toàn bộ dữ liệu đã xuất</option>
          </select>
        </div></div>
        <RankingChart data={visible} nameKey="genre" label="Biểu đồ xếp hạng thể loại" />
        <p className="chart-note" role="status">Đang hiển thị {visible.length}/{data.genres.length} thể loại.</p>
        <ReadingGuide><p>Tên thể loại giữ theo nguồn; “(no genres listed)” là nhóm chưa có thông tin thể loại. Các số đếm có thể trùng giữa các nhóm, không chuyển thành tỷ lệ trên tổng play độc lập.</p></ReadingGuide>
      </ChartPanel>
      <ChartPanel title="Nhận xét từ dữ liệu" note="So sánh hai thể loại đứng đầu trong nguồn." icon="trophy" className="genre-observation">
        <p className="analysis-leader">{data.first.genre}</p>
        <p>Đứng đầu với <strong>{number(data.first.playCount)}</strong> sự kiện play.</p>
        {data.second ? <><p>Tiếp theo là <strong>{data.second.genre}</strong> với {number(data.second.playCount)} sự kiện play.</p>
          <p>{data.gap === 0 ? 'Hai thể loại có cùng số sự kiện play.' : 'Chênh lệch giữa hai thể loại là ' + number(data.gap) + ' sự kiện play.'}</p></>
          : <p>Chỉ có một thể loại, chưa đủ dữ liệu để so sánh.</p>}
        <p className="chart-note">Nhận xét mô tả hành vi mô phỏng, không phản ánh sở thích người xem thật.</p>
      </ChartPanel>
      <ChartPanel className="analysis-wide" title="Bảng xếp hạng toàn bộ thể loại" note={'Gồm ' + data.genres.length + ' thể loại. Bảng giữ đầy đủ các dòng khi thay đổi lựa chọn biểu đồ.'} icon="table">
        <AnalysisTable kind="genres" data={data.genres} />
      </ChartPanel>
    </div>}
  </div>;
}

export default function GenresPage() {
  return <DashboardDataProvider loader={loadGenres}><GenresContent /></DashboardDataProvider>;
}
