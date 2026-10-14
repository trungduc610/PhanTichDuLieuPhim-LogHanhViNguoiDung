import { Link } from 'react-router-dom';
import { number, percent } from '../services/formatNumbers.js';
import Icon from './Icon.jsx';

export default function OverviewHighlights({ analysis }) {
  const movie = analysis.topMovies[0];
  const action = analysis.actions[0];
  const topActions = analysis.actions.filter(row => row.count === action.count);
  return <section className="overview-highlights" aria-labelledby="highlights-title">
    <div className="overview-section-heading"><h2 id="highlights-title">Điểm nổi bật trong kỳ</h2><p>Tóm tắt từ kết quả đã xuất</p></div>
    <div className="highlight-grid">
      <article className="highlight-card highlight-movie" data-highlight="movie">
        <p className="highlight-label"><Icon name="trophy" size={17} />Phim dẫn đầu theo sự kiện play</p>
        <h3>{movie.title}</h3>
        <p className="highlight-value">{number(movie.playCount)} <span>sự kiện phát</span></p>
        <Link to="/phim">Xem xếp hạng phim →</Link>
      </article>
      <article className="highlight-card highlight-action" data-highlight="action">
        <p className="highlight-label"><Icon name="activity" size={17} />Hành động có nhiều sự kiện nhất</p>
        <h3>{topActions.map(row => row.label).join(' · ')}</h3>
        <p className="highlight-value">{number(action.count)} <span>sự kiện · {percent(action.percentage)} tổng sự kiện</span></p>
        <Link to="/hanh-vi">Khám phá hành vi →</Link>
      </article>
      <article className="highlight-card highlight-hour" data-highlight="hour">
        <p className="highlight-label"><Icon name="clock" size={17} />Giờ có nhiều hoạt động nhất</p>
        <h3>{analysis.peakHours.map(row => row.label).join(' · ')}</h3>
        <p className="highlight-value">{number(analysis.peakHours[0].eventCount)} <span>{analysis.peakHours.length > 1 ? 'sự kiện mỗi khung giờ trong kỳ' : 'sự kiện trong kỳ'}</span></p>
        <Link to="/thoi-gian">Khám phá theo giờ →</Link>
      </article>
    </div>
    <p className="highlight-context">Các kết quả mô tả dữ liệu mô phỏng. Hoạt động theo giờ được cộng gộp trên toàn kỳ theo UTC+7.</p>
  </section>;
}
