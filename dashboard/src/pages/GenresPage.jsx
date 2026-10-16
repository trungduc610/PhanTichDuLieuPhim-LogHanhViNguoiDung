import { useRef, useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import AnalysisExplanation, { AnalysisRelatedLinks } from '../components/AnalysisExplanation.jsx';
import AnalysisResultsTable from '../components/AnalysisResultsTable.jsx';
import RankingChart from '../components/RankingChart.jsx';
import { loadGenres } from '../services/dashboardData.js';
import { selectGenres } from '../services/genreAnalysis.js';
import { number } from '../services/formatNumbers.js';

function GenresContent() {
  const state = useDashboardData();
  const [limit, setLimit] = useState('10');
  const explanations = useRef(null);
  const data = state.metrics;
  const visible = state.status === 'ready' ? selectGenres(data.genres, limit) : [];
  return <div className="analysis-page overview-page detail-ux genres-page">
    <AnalysisPageHeader title="Phân tích thể loại" description="So sánh lượt phát phim giữa các thể loại trong kỳ phân tích." detailed />
    <p className="analysis-context">Một phim có thể thuộc nhiều thể loại, nên một lượt phát có thể được tính ở nhiều nhóm. Các thể loại không phải những nhóm loại trừ nhau.</p>
    <DataState />
    {state.status === 'ready' && <>
      <div className="analysis-grid">
        <ChartPanel title="Thể loại có nhiều lượt phát" note="So sánh số lượt phát, không biểu diễn tỷ lệ trên tổng lượt phát độc lập." icon="genre" className="analysis-primary">
          <div className="chart-controls"><div className="filter-field">
            <label htmlFor="genre-limit">Thể loại trên biểu đồ</label>
            <select id="genre-limit" value={limit} onChange={event=>setLimit(event.target.value)}>
              <option value="5">Top 5</option><option value="10">Top 10</option><option value="all">Toàn bộ dữ liệu đã xuất</option>
            </select>
          </div></div>
          <RankingChart data={visible} nameKey="genre" label="Biểu đồ xếp hạng thể loại" plainLanguage />
          <p className="chart-note" role="status">Đang hiển thị {visible.length}/{data.genres.length} thể loại.</p>
          <AnalysisExplanation title="Thể loại có nhiều lượt phát" target={explanations}
            help="Mỗi thanh là số lượt phát của phim thuộc thể loại đó. Một phim có nhiều thể loại đóng góp vào từng nhóm, nên các số đếm có thể trùng nhau. Không cộng các nhóm hoặc đổi sang tỷ lệ để suy ra cơ cấu lượt phát độc lập. Thanh dài nhất ứng với thể loại dẫn đầu trong danh sách."
            technical="Nguồn: stats_top_genres.json. Spark chọn action = play, tách danh sách genres của phim rồi nhóm theo genre và đếm playCount. Tên thể loại giữ theo nguồn; (no genres listed) là phim chưa có thông tin thể loại. Thứ tự dùng kết quả chuẩn hóa hiện có, không đổi số liệu hoặc cách tính."
            instructions="Chọn Top 5, Top 10 hoặc toàn bộ để thay số thanh. Di chuột hoặc dùng Tab để đọc từng thể loại, cuộn trong khung khi danh sách dài. Bảng và CSV bên dưới luôn giữ đủ các thể loại đã xuất, độc lập với lựa chọn biểu đồ." />
        </ChartPanel>
        <ChartPanel title="Hai thể loại đứng đầu" note="So sánh trong toàn bộ danh sách đã xuất." icon="trophy" className="genre-observation">
          <p className="analysis-leader">{data.first.genre}</p>
          <p className="analysis-feature-value"><strong>{number(data.first.playCount)}</strong> lượt phát phim</p>
          {data.second ? <><p>Tiếp theo: <strong>{data.second.genre}</strong> — {number(data.second.playCount)} lượt phát phim.</p>
            <p>{data.gap === 0 ? 'Hai thể loại có cùng số lượt phát phim.' : 'Chênh lệch giữa hai thể loại: ' + number(data.gap) + ' lượt phát phim.'}</p></> : <p>Chỉ có một thể loại, chưa đủ dữ liệu để so sánh.</p>}
          <p className="chart-note">Số lượt phát khác nhau không chứng minh sở thích của người xem ngoài đời.</p>
        </ChartPanel>
        <div ref={explanations} className="independent-explanations analysis-wide" />
        <ChartPanel className="analysis-wide" title="Bảng xếp hạng toàn bộ thể loại" note={'Gồm ' + data.genres.length + ' thể loại; không thay đổi khi lọc biểu đồ.'} icon="table">
          <AnalysisResultsTable kind="genres" data={data.genres} />
        </ChartPanel>
      </div>
      <p className="analysis-limitation">Kết quả mô tả log hành vi mô phỏng. Thông tin thể loại lấy từ phim MovieLens, không phải phân nhóm người dùng.</p>
      <AnalysisRelatedLinks links={[["/phim","Xếp hạng phim"],["/hanh-vi","Phân biệt các hành động"]]} />
    </>}
  </div>;
}

export default function GenresPage() {
  return <DashboardDataProvider loader={loadGenres}><GenresContent /></DashboardDataProvider>;
}
