import { useId, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from './Icon.jsx';
import ScrollableTable from './ScrollableTable.jsx';
import { downloadOverviewCsv, overviewTables } from '../services/overviewExport.js';
import { number, percent } from '../services/formatNumbers.js';

export default function OverviewDataPanel({ kind, title, note, help, rows, detailPath, children, className = '' }) {
  const [view, setView] = useState('chart');
  const id = useId();
  const config = overviewTables[kind];
  return <section className={`chart-panel overview-data-panel ${className}`} data-panel={kind} aria-labelledby={`${id}-title`}>
    <div className="overview-panel-heading">
      <div><h2 id={`${id}-title`}><Icon name={kind === 'hourly' ? 'clock' : kind === 'actions' ? 'activity' : 'film'} />{title}</h2><p className="chart-note">{note}</p></div>
      <button className="csv-button" onClick={() => downloadOverviewCsv(config, rows)} aria-label={`Tải CSV: ${title}`}><Icon name="download" size={16} /><span>CSV</span></button>
    </div>
    <div className="overview-view-switch" role="group" aria-label={`Chế độ xem: ${title}`}>
      {['chart', 'table'].map(mode => <button key={mode} aria-pressed={view === mode} aria-controls={`${id}-content`} onClick={() => setView(mode)}><Icon name={mode} size={16} />{mode === 'chart' ? 'Biểu đồ' : 'Bảng'}</button>)}
    </div>
    <div id={`${id}-content`} className="overview-panel-content">
      {view === 'chart' ? children : <ScrollableTable label={`Bảng ${title}`}>
        <table><caption>{config.caption}</caption><thead><tr>{config.columns.map(column => <th scope="col" key={column.key}>{column.label}</th>)}</tr></thead>
          <tbody>{rows.map((row, index) => <tr key={row.movieId ?? row.action ?? row.hour ?? index}>{config.columns.map((column, columnIndex) => {
            const value = row[column.key];
            const text = column.format === 'number' ? number(value) : column.format === 'percent' ? percent(value) : value;
            return columnIndex === 0 ? <th scope="row" key={column.key}>{text}</th> : <td key={column.key}>{text}</td>;
          })}</tr>)}</tbody>
        </table>
      </ScrollableTable>}
    </div>
    <div className="overview-panel-footer">
      <details className="overview-help"><summary><Icon name="info" size={16} />Cách đọc</summary><p>{help}</p></details>
      <Link className="detail-link" to={detailPath} aria-label={`Xem chi tiết: ${title}`}>Xem chi tiết <Icon name="arrow" size={16} /></Link>
    </div>
  </section>;
}
