import Icon from './Icon.jsx';
import { downloadOverviewCsv } from '../services/overviewExport.js';

// Chỉ xuất các dòng được truyền vào, giữ giá trị gốc và dùng bộ mã hóa CSV hiện có.
export default function ResultCsvButton({ columns, rows, filename, label }) {
  return <button type="button" className="csv-button" data-export={filename} disabled={!rows.length}
    aria-label={`Tải CSV: ${label}`} onClick={()=>downloadOverviewCsv({columns,filename},rows)}>
    <Icon name="download" size={16} />CSV
  </button>;
}
