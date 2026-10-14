import { useId } from 'react';
import Icon from './Icon.jsx';
import { number, percent } from '../services/formatNumbers.js';
import ScrollableTable from './ScrollableTable.jsx';

export function ChartPanel({ title, note, children, icon = 'chart', className = '' }) {
  const id = useId();
  return <section className={'chart-panel ' + className} aria-labelledby={id}>
    <div className="overview-panel-heading"><div><h2 id={id}><Icon name={icon} />{title}</h2>
      {note && <p className="chart-note">{note}</p>}</div></div>
    {children}
  </section>;
}

export function AnalysisTable({ kind, data }) {
  const headings = kind === 'combined' ? ['Giờ (UTC+7)', 'Hạng trong giờ', 'Phim', 'Sự kiện play', 'Người dùng khác nhau']
    : kind === 'genres' ? ['Hạng', 'Thể loại', 'Sự kiện phát (play)']
    : kind === 'movies' ? ['Hạng', 'Phim', 'Sự kiện phát (play)']
    : kind === 'actions' ? ['Hành động', 'Sự kiện', 'Tỷ lệ (%)']
      : ['Giờ (UTC+7)', 'Sự kiện', 'Sự kiện phát (play)', 'Người dùng khác nhau'];
  return <ScrollableTable label="Bảng số liệu chi tiết">
    <table><caption>Số liệu chi tiết trong toàn kỳ phân tích</caption>
      <thead><tr>{headings.map(heading => <th key={heading} scope="col">{heading}</th>)}</tr></thead>
      <tbody>{data.map((row, index) => <tr key={kind === 'combined' ? row.hour + '-' + row.movieId : row.genre ?? row.movieId ?? row.action ?? row.hour}>
        {kind === 'combined' ? <><td>{row.hourLabel}</td><td>{row.rank}</td><th scope="row">{row.title}</th><td>{number(row.playCount)}</td><td>{number(row.distinctUsers)}</td></>
          : kind === 'movies' || kind === 'genres' ? <><td>{index + 1}</td><th scope="row">{kind === 'genres' ? row.genre : row.title}</th><td>{number(row.playCount)}</td></>
          : kind === 'actions' ? <><th scope="row">{row.label} ({row.action})</th><td>{number(row.count)}</td><td>{percent(row.percentage)}</td></>
            : <><th scope="row">{row.label}</th><td>{number(row.eventCount)}</td><td>{number(row.playCount)}</td><td>{number(row.distinctUsers)}</td></>}
      </tr>)}</tbody>
    </table>
  </ScrollableTable>;
}
