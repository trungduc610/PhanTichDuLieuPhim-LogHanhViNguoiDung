import { useId } from 'react';
import OverviewMovieRanking from './OverviewMovieRanking.jsx';

// Tái sử dụng thanh xếp hạng của Tổng quan, giữ đủ dòng và tên đầy đủ ở trang chi tiết.
export default function RankingChart({ data, nameKey = 'title', showDistinctUsers = false, label = 'Biểu đồ xếp hạng', plainLanguage = false }) {
  const id = useId();
  return <>
    <p className="chart-unit">Đơn vị: {plainLanguage ? 'lượt phát phim' : 'sự kiện phát (play)'} · Thanh so với vị trí dẫn đầu trong danh sách</p>
    <div className="ranking-scroll" role="region" aria-label={label} aria-describedby={plainLanguage ? id : undefined} tabIndex={0}>
      <OverviewMovieRanking rows={data} nameKey={nameKey} showDistinctUsers={showDistinctUsers} countLabel={plainLanguage ? 'lượt phát phim' : undefined} />
    </div>
    <p id={id} className={plainLanguage ? 'overview-sr-only' : 'overview-interaction-help'}>Di chuột hoặc dùng Tab để làm nổi bật từng dòng. Danh sách dài có thể cuộn trong khung.</p>
  </>;
}
