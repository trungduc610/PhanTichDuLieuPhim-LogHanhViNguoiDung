import { Link } from 'react-router-dom';
import { number, percent } from '../services/formatNumbers.js';
import Icon from './Icon.jsx';
import { presentActions, hourRange } from '../content/overviewContent.js';

export default function OverviewHighlights({ analysis }) {
  const movie = analysis.topMovies[0];
  const actions = presentActions(analysis.actions);
  const action = actions[0];
  const topActions = actions.filter(row => row.count === action.count);
  return <section className="overview-highlights" aria-labelledby="highlights-title">
    <div className="overview-section-heading"><h2 id="highlights-title">Kết quả nổi bật</h2><p>Trong toàn bộ kỳ phân tích</p></div>
    <div className="highlight-grid">
      <article className="highlight-card highlight-movie" data-highlight="movie">
        <p className="highlight-label"><Icon name="trophy" size={17} />Phim được phát nhiều nhất</p>
        <h3>{movie.title}</h3>
        <p className="highlight-value">{number(movie.playCount)} <span>lượt phát phim</span></p>
        <Link to="/phim">Xem xếp hạng phim →</Link>
      </article>
      <article className="highlight-card highlight-action" data-highlight="action">
        <p className="highlight-label"><Icon name="activity" size={17} />Hành động phổ biến nhất</p>
        <h3>{topActions.map(row => row.label).join(' · ')}</h3>
        <p className="highlight-value">{number(action.count)} <span>lần · {percent(action.percentage)} tổng số hành động</span></p>
        <Link to="/hanh-vi">Xem phân tích hành vi →</Link>
      </article>
      <article className="highlight-card highlight-hour" data-highlight="hour">
        <p className="highlight-label"><Icon name="clock" size={17} />Khung giờ có nhiều hoạt động nhất</p>
        <h3>{analysis.peakHours.map(row => hourRange(row.hour)).join(' · ')}</h3>
        <p className="highlight-value">{number(analysis.peakHours[0].eventCount)} <span>{analysis.peakHours.length > 1 ? 'hành động ở mỗi khung giờ' : 'hành động trong toàn kỳ'}</span></p>
        <Link to="/thoi-gian">Xem phân tích theo giờ →</Link>
      </article>
    </div>
    <p className="highlight-context">Các kết quả mô tả log mô phỏng, không đại diện cho thói quen của người xem ngoài đời.</p>
  </section>;
}
