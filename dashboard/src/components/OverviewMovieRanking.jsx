import { number } from '../services/formatNumbers.js';
import Icon from './Icon.jsx';

export default function OverviewMovieRanking({ rows, nameKey = 'title', showDistinctUsers = false, countLabel = 'sự kiện play' }) {
  const maximum = rows[0].playCount;
  return <ol className="movie-ranking" aria-label={`Xếp hạng ${rows.length} ${nameKey === 'genre' ? 'thể loại' : 'phim'} theo ${countLabel === 'sự kiện play' ? 'số sự kiện play' : countLabel}`}>
    {rows.map((row, index) => <li key={row.movieId ?? row.genre} className={index === 0 ? 'rank-leader' : ''} data-movie={row.movieId} data-genre={row.genre} tabIndex={0} aria-label={`Hạng ${row.rank ?? index + 1}: ${row[nameKey]}, ${number(row.playCount)} ${countLabel}${showDistinctUsers ? `, ${number(row.distinctUsers)} người dùng khác nhau` : ''}`}>
      <span className="movie-rank" aria-label={`Hạng ${row.rank ?? index + 1}`}>{row.rank ?? index + 1}</span>
      <div className="movie-rank-content">
        <div className="movie-rank-heading"><h3>{row[nameKey]}{index === 0 && <Icon name="trophy" size={16} />}</h3><p><strong>{number(row.playCount)}</strong> <span>{countLabel}</span></p></div>
        {showDistinctUsers && <p className="ranking-users">{number(row.distinctUsers)} người dùng khác nhau trong nhóm phim–giờ</p>}
        <div className="movie-rank-track" aria-hidden="true"><div className="movie-rank-fill" style={{ width: `${maximum > 0 ? row.playCount * 100 / maximum : 0}%` }} /></div>
      </div>
    </li>)}
  </ol>;
}
