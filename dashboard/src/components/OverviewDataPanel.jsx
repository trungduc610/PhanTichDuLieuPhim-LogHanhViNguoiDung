import { useId, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from './Icon.jsx';
import ScrollableTable from './ScrollableTable.jsx';
import { downloadOverviewCsv, overviewTables } from '../services/overviewExport.js';
import { number, percent } from '../services/formatNumbers.js';
import IndependentDisclosure from './IndependentDisclosure.jsx';

export default function OverviewDataPanel({ kind, title, note, help, technical, instructions, rows, detailPath, children, explanationTarget, className = '' }) {
  const [view, setView] = useState('chart');
  const id = useId();
  const config = overviewTables[kind];
  const visibleColumns = config.columns.filter(column => column.key !== 'action');
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
        <table><caption>{config.caption}</caption><thead><tr>{visibleColumns.map(column => <th scope="col" key={column.key}>{column.label}</th>)}</tr></thead>
          <tbody>{rows.map((row, index) => <tr key={row.movieId ?? row.action ?? row.hour ?? index}>{visibleColumns.map((column, columnIndex) => {
            const value = row[column.key];
            const text = column.format === 'number' ? number(value) : column.format === 'percent' ? percent(value) : value;
            return columnIndex === 0 ? <th scope="row" key={column.key}>{text}</th> : <td key={column.key}>{text}</td>;
          })}</tr>)}</tbody>
        </table>
      </ScrollableTable>}
    </div>
    <div className="overview-panel-footer">
      <div className="panel-explanations">
        <IndependentDisclosure className="overview-help" label="Giải thích dữ liệu"
          title={`Giải thích dữ liệu: ${title}`} target={explanationTarget}><p>{help}</p>
          {technical && <details className="technical-definition"><summary>Chi tiết kỹ thuật</summary><p>{technical}</p></details>}
        </IndependentDisclosure>
        {instructions && <IndependentDisclosure className="overview-help operation-help" label="Hướng dẫn thao tác"
          title={`Hướng dẫn thao tác: ${title}`} target={explanationTarget}><p>{instructions}</p></IndependentDisclosure>}
      </div>
      <Link className="detail-link" to={detailPath} aria-label={`Xem chi tiết: ${title}`}>Xem chi tiết <Icon name="arrow" size={16} /></Link>
    </div>
  </section>;
}
