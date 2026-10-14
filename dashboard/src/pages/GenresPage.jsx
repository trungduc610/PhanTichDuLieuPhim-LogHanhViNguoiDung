import { useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel, HorizontalPlayChart, AnalysisTable } from '../components/OverviewCharts.jsx';
import { loadGenres } from '../services/dashboardData.js';
import { selectGenres } from '../services/genreAnalysis.js';
import { number } from '../services/formatNumbers.js';

function GenresContent() {
  const state = useDashboardData();
  const [limit, setLimit] = useState('10');
  const data = state.metrics;
  return <>
    <h1>Phân tích thể loại</h1>
    <p className="intro">So sánh số sự kiện phát phim được ghi nhận theo thể loại trong kỳ.</p>
    <aside className="data-note scope-note">
      <strong>Cách đọc số liệu thể loại</strong>
      <p>Một phim có thể thuộc nhiều thể loại, nên một sự kiện play có thể được tính vào nhiều nhóm. Tổng các nhóm thể loại không phải tổng số sự kiện play độc lập.</p>
    </aside>
    <DataState />
    {state.status === 'ready' && <>
      <ChartPanel title="Xếp hạng thể loại theo số sự kiện play" note="Sắp xếp từ nhiều đến ít; lựa chọn chỉ thay đổi số thể loại trên biểu đồ.">
        <div className="chart-controls">
          <label htmlFor="genre-limit">Thể loại trên biểu đồ</label>
          <select id="genre-limit" value={limit} onChange={(event) => setLimit(event.target.value)}>
            <option value="5">Top 5</option>
            <option value="10">Top 10</option>
            <option value="all">Toàn bộ dữ liệu đã xuất</option>
          </select>
        </div>
        <HorizontalPlayChart data={selectGenres(data.genres, limit)} nameKey="genre" rowHeight={44} className="genre-chart" />
        <p className="chart-note">Đang hiển thị {selectGenres(data.genres, limit).length}/{data.genres.length} thể loại. Tên thể loại được giữ theo nguồn; “(no genres listed)” là nhóm chưa có thông tin thể loại.</p>
      </ChartPanel>
      <section className="chart-panel genre-observation" aria-label="Nhận xét từ dữ liệu">
        <h2>Nhận xét từ dữ liệu</h2>
        <p><strong>{data.first.genre}</strong> đứng đầu bảng xếp hạng với {number(data.first.playCount)} sự kiện play.</p>
        {data.second ? <p>Thể loại tiếp theo là <strong>{data.second.genre}</strong> với {number(data.second.playCount)} sự kiện play.
          {' '}{data.gap === 0 ? 'Hai thể loại có cùng số sự kiện play.' : `Chênh lệch giữa hai thể loại là ${number(data.gap)} sự kiện play.`}</p>
          : <p>Dữ liệu đã xuất chỉ có một thể loại, chưa đủ để so sánh với thể loại tiếp theo.</p>}
        <p className="chart-note">Nhận xét mô tả kết quả hành vi mô phỏng, không phản ánh sở thích người xem thật.</p>
      </section>
      <ChartPanel title="Bảng xếp hạng toàn bộ thể loại" note={`Gồm ${data.genres.length} thể loại trong dữ liệu đã xuất. Bảng giữ đầy đủ các dòng khi thay đổi lựa chọn biểu đồ.`}>
        <AnalysisTable kind="genres" data={data.genres} />
      </ChartPanel>
    </>}
  </>;
}

export default function GenresPage() {
  // Lỗi nguồn thể loại được xử lý riêng, giữ nguyên dữ liệu và các trang hiện có.
  return <DashboardDataProvider loader={loadGenres}><GenresContent /></DashboardDataProvider>;
}
