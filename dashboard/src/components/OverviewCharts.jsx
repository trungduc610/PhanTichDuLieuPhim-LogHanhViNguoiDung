import { Link } from 'react-router-dom';
import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList } from 'recharts';
import { number, percent, axisNumber } from '../services/formatNumbers.js';

export function ChartPanel({ title, note, children, detailPath }) {
  return <section className="chart-panel" aria-label={title}>
    <h2>{title}</h2><p className="chart-note">{note}</p>
    {children}
    {detailPath && <Link className="detail-link" to={detailPath} aria-label={`Xem chi tiết: ${title}`}>Xem chi tiết →</Link>}
  </section>;
}

export function ActionChart({ data }) {
  return <><div className="chart-unit">Đơn vị: % tổng sự kiện</div><div className="chart-frame">
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 60, bottom: 8, left: 0 }} accessibilityLayer>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tickFormatter={percent} tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="label" width={100} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(value, name, item) => [`${percent(value)} · ${number(item.payload.count)} sự kiện`, 'Tỷ lệ']} />
        <Bar dataKey="percentage" fill="#3865b5" isAnimationActive={false} radius={[0, 4, 4, 0]}>
          <LabelList dataKey="percentage" position="right" formatter={percent} fontSize={11} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  </div></>;
}

export function HourlyChart({ data }) {
  return <><div className="chart-unit">Đơn vị: sự kiện · Giờ Việt Nam (UTC+7)</div><div className="chart-frame">
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 16, right: 12, bottom: 8, left: 0 }} accessibilityLayer>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={8} />
        <YAxis tickFormatter={axisNumber} width={82} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(value) => [`${number(value)} sự kiện`, 'Tổng hoạt động']} labelFormatter={(label) => `Khung giờ ${label} (UTC+7)`} />
        <Bar dataKey="eventCount" fill="#287b79" isAnimationActive={false} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  </div></>;
}

// Chia tên dài thành dòng; tên đầy đủ luôn có trong tooltip và bảng chi tiết.
function MovieNameTick({ x, y, payload }) {
  const lines = [''];
  for (const word of String(payload.value).split(' ')) {
    const last = lines.length - 1;
    if (lines[last] && `${lines[last]} ${word}`.length > 21) lines.push(word);
    else lines[last] = `${lines[last]} ${word}`.trim();
  }
  const visible = lines.slice(0, 3);
  if (lines.length > 3) visible[2] += '…';
  return <text x={x} y={y} textAnchor="end" fill="#526079" fontSize={11}>
    <title>{payload.value}</title>
    {visible.map((line, index) => <tspan key={index} x={x} dy={index === 0 ? -(visible.length - 1) * 6 + 4 : 12}>{line}</tspan>)}
  </text>;
}

export function MovieChart({ data }) {
  return <HorizontalPlayChart data={data} />;
}

export function HorizontalPlayChart({ data, nameKey = 'title', rowHeight = 64, className = 'movie-chart', showDistinctUsers = false }) {
  return <><div className="chart-unit">Đơn vị: sự kiện phát (play)</div>
    <div className={`chart-frame ${className}`} style={{ height: Math.max(280, data.length * rowHeight + 48) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 58, bottom: 8, left: 0 }} accessibilityLayer>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tickFormatter={axisNumber} tick={{ fontSize: 11 }} tickCount={3} />
          <YAxis type="category" dataKey={nameKey} width={142} interval={0} tick={<MovieNameTick />} />
          <Tooltip formatter={(value, name, item) => [showDistinctUsers
            ? `${number(value)} sự kiện · ${number(item.payload.distinctUsers)} người dùng khác nhau`
            : `${number(value)} sự kiện`, 'Phát phim']} />
          <Bar dataKey="playCount" fill="#8061ab" isAnimationActive={false} radius={[0, 4, 4, 0]}>
            <LabelList dataKey="playCount" position="right" formatter={number} fontSize={11} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  </>;
}

export function AnalysisTable({ kind, data }) {
  const headings = kind === 'combined' ? ['Giờ (UTC+7)', 'Hạng trong giờ', 'Phim', 'Sự kiện play', 'Người dùng khác nhau']
    : kind === 'genres' ? ['Hạng', 'Thể loại', 'Sự kiện phát (play)']
    : kind === 'movies' ? ['Hạng', 'Phim', 'Sự kiện phát (play)']
    : kind === 'actions' ? ['Hành động', 'Sự kiện', 'Tỷ lệ (%)']
      : ['Giờ (UTC+7)', 'Sự kiện', 'Sự kiện phát (play)', 'Người dùng khác nhau'];
  return <div className="table-scroll" tabIndex={0} aria-label="Bảng số liệu có thể cuộn ngang">
    <table><caption>Số liệu chi tiết trong toàn kỳ phân tích</caption>
      <thead><tr>{headings.map((heading) => <th key={heading} scope="col">{heading}</th>)}</tr></thead>
      <tbody>{data.map((row, index) => <tr key={kind === 'combined' ? `${row.hour}-${row.movieId}` : row.genre ?? row.movieId ?? row.action ?? row.hour}>
        {kind === 'combined' ? <><td>{row.hourLabel}</td><td>{row.rank}</td><th scope="row">{row.title}</th><td>{number(row.playCount)}</td><td>{number(row.distinctUsers)}</td></>
          : kind === 'movies' || kind === 'genres' ? <><td>{index + 1}</td><th scope="row">{kind === 'genres' ? row.genre : row.title}</th><td>{number(row.playCount)}</td></>
          : kind === 'actions' ? <><th scope="row">{row.label} ({row.action})</th><td>{number(row.count)}</td><td>{percent(row.percentage)}</td></>
            : <><th scope="row">{row.label}</th><td>{number(row.eventCount)}</td><td>{number(row.playCount)}</td><td>{number(row.distinctUsers)}</td></>}
      </tr>)}</tbody>
    </table>
  </div>;
}

export default function OverviewCharts({ analysis }) {
  return <div className="analysis-sections summary-grid">
    <ChartPanel title="Phân bố hành vi" note="Tỷ lệ sự kiện theo hành động trong kỳ." detailPath="/hanh-vi">
      <ActionChart data={analysis.actions} />
    </ChartPanel>
    <ChartPanel title="Hoạt động theo giờ" note="Sự kiện theo 24 giờ, cộng gộp tất cả ngày trong kỳ." detailPath="/thoi-gian">
      <HourlyChart data={analysis.hourly} />
    </ChartPanel>
    <ChartPanel title="Top 5 phim" note="Xếp hạng theo số sự kiện phát, gồm các lần phát lặp lại." detailPath="/phim">
      <MovieChart data={analysis.topMovies} />
    </ChartPanel>
  </div>;
}
