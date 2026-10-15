import { useRef, useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import AnalysisExplanation, { AnalysisRelatedLinks } from '../components/AnalysisExplanation.jsx';
import RankingChart from '../components/RankingChart.jsx';
import ScrollableTable from '../components/ScrollableTable.jsx';
import ResultCsvButton from '../components/ResultCsvButton.jsx';
import { loadCombinedAnalysis } from '../services/dashboardData.js';
import { hourLabel, selectCombinedHour } from '../services/combinedAnalysis.js';
import { number } from '../services/formatNumbers.js';

const csvColumns = [['hour','Giờ UTC+7'],['rank','Hạng trong giờ'],['movieId','Mã phim'],['title','Phim'],['playCount','Lượt phát phim'],['distinctUsers','Người dùng duy nhất trong nhóm']].map(([key,label])=>({key,label}));
function CombinedTable({ rows }) {
  return <ScrollableTable label="Bảng phim theo giờ"><table><caption>Lượt phát và người dùng theo từng phim–giờ trong toàn kỳ</caption>
    <thead><tr>{['Giờ (UTC+7)','Hạng trong giờ','Phim','Lượt phát phim','Người dùng duy nhất trong nhóm'].map(label=><th key={label} scope="col">{label}</th>)}</tr></thead>
    <tbody>{rows.map(row=><tr key={`${row.hour}-${row.movieId}`}><td>{row.hourLabel}</td><td>{row.rank}</td><th scope="row">{row.title}</th><td>{number(row.playCount)}</td><td>{number(row.distinctUsers)}</td></tr>)}</tbody>
  </table></ScrollableTable>;
}
function CombinedContent() {
  const state = useDashboardData();
  const [hour,setHour] = useState(0);
  const [onlySelected,setOnlySelected] = useState(false);
  const [query,setQuery] = useState('');
  const [page,setPage] = useState(1);
  const [pageSize,setPageSize] = useState(0);
  const chartInfo = useRef(null);
  const tableInfo = useRef(null);
  const selected = state.status==='ready' ? selectCombinedHour(state.metrics,hour) : null;
  const filtered = selected ? (onlySelected?selected.movies:state.metrics.rows).filter(row=>row.title.toLocaleLowerCase('vi').includes(query.trim().toLocaleLowerCase('vi'))) : [];
  const pages = pageSize?Math.max(1,Math.ceil(filtered.length/pageSize)):1;
  const current = Math.min(page,pages);
  const visible = pageSize?filtered.slice((current-1)*pageSize,current*pageSize):filtered;
  return <div className="analysis-page overview-page detail-ux advanced-ux combined-page">
    <AnalysisPageHeader title="Phân tích kết hợp" description="Đối chiếu phim được phát, số người dùng và khung giờ trong cùng kết quả phân tích." detailed />
    <p className="analysis-context">Mỗi nhóm gồm một phim trong một khung giờ Việt Nam (UTC+7), cộng gộp mọi ngày trong kỳ. Kết quả chỉ giữ các phim trong Top 3 của từng giờ.</p>
    <DataState />
    {selected && <>
      <div className="analysis-grid">
        <ChartPanel title={'Top 3 phim · '+hourLabel(hour)} note="Xếp hạng theo lượt phát; số người dùng được đếm riêng trong từng nhóm phim–giờ." icon="combined">
          <div className="chart-controls"><div className="filter-field"><label htmlFor="combined-hour">Chọn khung giờ (UTC+7)</label>
            <select id="combined-hour" value={hour} onChange={event=>{setHour(Number(event.target.value));setPage(1);}}>{state.metrics.byHour.map((group,index)=><option key={index} value={index}>{hourLabel(index)}</option>)}</select>
          </div></div>
          <RankingChart data={selected.movies} showDistinctUsers plainLanguage />
          <div className="combined-selected"><CombinedTable rows={selected.movies} /></div>
          <AnalysisExplanation title="Phim và người dùng theo giờ" target={chartInfo}
            help="Thanh xếp hạng so sánh lượt phát của các phim trong giờ đang chọn. Số người dùng là số mã người dùng phân biệt đã phát phim đó trong giờ ấy. Một người có thể phát nhiều lần và xuất hiện ở nhiều nhóm; không cộng các nhóm để suy ra tổng người dùng toàn kỳ."
            technical="Nguồn: stats_user_movie_time.json. Spark lọc action = play, nhóm hour, movieId, title; playCount đếm bản ghi và distinctUsers đếm userId phân biệt. rank xếp theo playCount giảm dần, movieId tăng dần khi bằng nhau; chỉ xuất rank ≤ 3. Giờ theo Asia/Ho_Chi_Minh, không phải một ngày riêng lẻ."
            instructions="Chọn giờ để cập nhật đồng thời xếp hạng, bảng nhóm được chọn và nhận xét. Di chuột hoặc Tab để đọc từng phim; cuộn ngang trong bảng nếu có cột bị khuất. Bộ lọc ở bảng tra cứu phía dưới không thay đổi biểu đồ này." />
        </ChartPanel>
        <ChartPanel title={'Phim dẫn đầu · '+hourLabel(hour)} note="Nhận xét thay đổi theo giờ đang chọn." icon="trophy" className="combined-observation">
          <p className="analysis-leader">{selected.leader.title}</p>
          <p className="analysis-feature-value"><strong>{number(selected.leader.playCount)}</strong> lượt phát phim</p>
          <p>{number(selected.leader.distinctUsers)} người dùng duy nhất trong nhóm phim–giờ này.</p>
          <p>Tiếp theo: <strong>{selected.runnerUp.title}</strong> — {number(selected.runnerUp.playCount)} lượt phát phim.</p>
          <p>{selected.gap===0?'Hai phim có cùng lượt phát; thứ hạng phân định theo mã phim tăng dần.':'Chênh lệch: '+number(selected.gap)+' lượt phát phim.'}</p>
          <p className="chart-note">Các số đếm mô tả hoạt động được ghi nhận, không chứng minh giờ này gây ra lượt phát hay sở thích cá nhân.</p>
        </ChartPanel>
        <div ref={chartInfo} className="independent-explanations analysis-wide" />
        <ChartPanel className="analysis-wide" title="Tra cứu phim theo giờ" note="Bảng đối chiếu toàn bộ kết quả đã xuất; giữ hạng gốc khi lọc và phân trang." icon="table">
          <div className="chart-controls"><label className="checkbox-field"><input id="combined-only-selected" type="checkbox" checked={onlySelected} onChange={event=>{setOnlySelected(event.target.checked);setPage(1);}} />Chỉ xem giờ đang chọn ({hourLabel(hour)})</label></div>
          <div className="results-controls">
            <div className="filter-field"><label htmlFor="combined-query">Tìm tên phim trong kết quả đã xuất</label><input id="combined-query" type="search" value={query} placeholder="Nhập tên phim" onChange={event=>{setQuery(event.target.value);setPage(1);}} /></div>
            <div className="filter-field page-size"><label htmlFor="combined-page-size">Số dòng mỗi trang</label><select id="combined-page-size" value={pageSize} onChange={event=>{setPageSize(Number(event.target.value));setPage(1);}}><option value={0}>Toàn bộ</option><option value={24}>24</option><option value={12}>12</option></select></div>
            <ResultCsvButton columns={csvColumns} rows={filtered} filename="phim-theo-gio.csv" label="Kết quả phim theo giờ đã lọc" />
          </div>
          <p className="chart-note" role="status">Tìm thấy {filtered.length}/{state.metrics.rows.length} dòng; đang hiển thị {visible.length} dòng. CSV gồm mọi dòng khớp bộ lọc.</p>
          <div className="combined-browse"><CombinedTable rows={visible} /></div>
          {!filtered.length && <p role="status">Không có phim phù hợp với bộ lọc.</p>}
          {pageSize>0 && <div className="results-pagination" role="group" aria-label="Phân trang phim theo giờ"><button disabled={current===1} onClick={()=>setPage(current-1)}>Trang trước</button><span role="status">Trang {current}/{pages}</span><button disabled={current===pages} onClick={()=>setPage(current+1)}>Trang sau</button></div>}
          <AnalysisExplanation title="Tra cứu phim theo giờ" target={tableInfo}
            help="Bảng giữ thứ hạng trong từng giờ, không phải thứ hạng toàn kỳ. Mỗi dòng cho biết một phim, khung giờ và hai số đếm: lượt phát có thể lặp, người dùng được đếm duy nhất trong chính nhóm ấy. Không có dữ liệu cá nhân hay quan hệ nhân quả trong bảng này."
            technical="hour là giờ Việt Nam, movieId là mã phim, rank là thứ hạng trong giờ, playCount là số bản ghi play, distinctUsers là số userId phân biệt trong nhóm phim–giờ. Tìm kiếm và phân trang chỉ đổi các dòng hiển thị, không tính lại xếp hạng Spark."
            instructions="Kết hợp ô Chỉ xem giờ đang chọn với tìm tên phim. Chọn số dòng rồi dùng Trang trước/Trang sau khi cần. Tab vào bảng và dùng ←/→, Home/End để cuộn các cột. CSV giữ giá trị gốc của tất cả dòng khớp bộ lọc, kể cả các trang chưa hiển thị." />
        </ChartPanel>
        <div ref={tableInfo} className="independent-explanations analysis-wide" />
      </div>
      <p className="analysis-limitation">Kết quả chỉ mô tả log mô phỏng và Top 3 phim mỗi giờ, không đại diện toàn bộ phim hoặc sở thích người xem ngoài đời.</p>
      <AnalysisRelatedLinks links={[["/phim","Xếp hạng phim toàn kỳ"],["/thoi-gian","Đối chiếu hoạt động theo thời gian"]]} />
    </>}
  </div>;
}
export default function CombinedAnalysisPage() {
  return <DashboardDataProvider loader={loadCombinedAnalysis}><CombinedContent /></DashboardDataProvider>;
}
