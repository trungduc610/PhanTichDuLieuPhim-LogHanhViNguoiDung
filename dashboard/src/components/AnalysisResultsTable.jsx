import { useId, useState } from 'react';
import ScrollableTable from './ScrollableTable.jsx';
import Icon from './Icon.jsx';
import { number, percent } from '../services/formatNumbers.js';
import { downloadOverviewCsv } from '../services/overviewExport.js';

const columns = {
  movies: [{key:'rank',label:'Hạng',format:'number'}, {key:'title',label:'Phim'}, {key:'playCount',label:'Lượt phát phim',format:'number'}],
  genres: [{key:'rank',label:'Hạng',format:'number'}, {key:'genre',label:'Thể loại'}, {key:'playCount',label:'Lượt phát phim',format:'number'}],
  actions: [{key:'label',label:'Hành động'}, {key:'action',label:'Mã hành động'}, {key:'count',label:'Số hành động',format:'number'}, {key:'percentage',label:'Tỷ lệ hành động (%)',format:'percent'}],
  hourly: [{key:'label',label:'Giờ (UTC+7)'}, {key:'eventCount',label:'Số hành động',format:'number'}, {key:'playCount',label:'Lượt phát phim',format:'number'}, {key:'distinctUsers',label:'Người dùng duy nhất trong giờ',format:'number'}],
};

export default function AnalysisResultsTable({ kind, data }) {
  const id = useId();
  const [query,setQuery] = useState('');
  const [page,setPage] = useState(1);
  const [pageSize,setPageSize] = useState(20);
  // Chỉ lọc cách hiển thị; giữ nguyên thứ hạng và các giá trị từ nguồn.
  const ranked = data.map((row,index) => ({...row,rank:index+1}));
  const filtered = kind === 'movies' ? ranked.filter(row => row.title.toLocaleLowerCase('vi').includes(query.trim().toLocaleLowerCase('vi'))) : ranked;
  const pages = Math.max(1,Math.ceil(filtered.length/pageSize));
  const current = Math.min(page,pages);
  const visible = kind === 'movies' ? filtered.slice((current-1)*pageSize,current*pageSize) : filtered;
  const visibleColumns = columns[kind].filter(column=>column.key!=='action');
  return <div className="analysis-results" data-results={kind}>
    <div className="results-controls">
      {kind === 'movies' && <>
        <div className="filter-field"><label htmlFor={`${id}-search`}>Tìm trong danh sách phim đã xuất</label>
          <input id={`${id}-search`} type="search" value={query} placeholder="Nhập tên phim" onChange={event=>{setQuery(event.target.value);setPage(1);}} /></div>
        <div className="filter-field page-size"><label htmlFor={`${id}-size`}>Số dòng mỗi trang</label>
          <select id={`${id}-size`} value={pageSize} onChange={event=>{setPageSize(Number(event.target.value));setPage(1);}}><option value={10}>10</option><option value={20}>20</option></select></div>
      </>}
      <button className="csv-button" disabled={!filtered.length} onClick={()=>downloadOverviewCsv({columns:columns[kind],filename:`phan-tich-${kind}.csv`},filtered)}
        aria-label="Tải CSV bảng số liệu"><Icon name="download" size={16} />CSV</button>
    </div>
    {kind === 'movies' && <p className="results-status" role="status">Tìm thấy {number(filtered.length)}/{number(data.length)} phim. CSV gồm toàn bộ kết quả tìm kiếm, không chỉ trang hiện tại.</p>}
    <ScrollableTable label="Bảng số liệu chi tiết"><table>
      <caption>{kind === 'actions' ? 'Tỷ lệ trên tổng số hành động trong toàn kỳ' : kind === 'hourly' ? 'Cùng khung giờ Việt Nam, cộng gộp mọi ngày trong kỳ' : 'Thứ hạng theo lượt phát phim trong danh sách đã xuất'}</caption>
      <thead><tr>{visibleColumns.map(column=><th key={column.key} scope="col">{column.label}</th>)}</tr></thead>
      <tbody>{visible.map(row=><tr key={row.movieId??row.genre??row.action??row.hour}>{visibleColumns.map(column=>{
        const value=row[column.key];
        const text=column.format==='number'?number(value):column.format==='percent'?percent(value):value;
        return ['title','genre','label'].includes(column.key) ? <th key={column.key} scope="row">{text}</th> : <td key={column.key}>{text}</td>;
      })}</tr>)}</tbody>
    </table></ScrollableTable>
    {!visible.length && <p role="status">Không có phim phù hợp. Hãy thử tên khác hoặc xóa từ khóa.</p>}
    {kind === 'movies' && <div className="results-pagination" role="group" aria-label="Phân trang bảng phim">
      <button disabled={current===1} onClick={()=>setPage(current-1)}>Trang trước</button><span role="status">Trang {current}/{pages}</span><button disabled={current===pages} onClick={()=>setPage(current+1)}>Trang sau</button>
    </div>}
  </div>;
}
