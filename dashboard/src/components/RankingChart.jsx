import OverviewMovieRanking from './OverviewMovieRanking.jsx';

// Tái sử dụng thanh xếp hạng của Tổng quan, giữ đủ dòng và tên đầy đủ ở trang chi tiết.
export default function RankingChart({ data, nameKey = 'title', showDistinctUsers = false, label = 'Biểu đồ xếp hạng' }) {
  return <>
    <p className="chart-unit">Đơn vị: sự kiện phát (play) · Thanh so với vị trí dẫn đầu trong danh sách</p>
    <div className="ranking-scroll" role="region" aria-label={label} tabIndex={0}>
      <OverviewMovieRanking rows={data} nameKey={nameKey} showDistinctUsers={showDistinctUsers} />
    </div>
    <p className="overview-interaction-help">Di chuột hoặc dùng Tab để làm nổi bật từng dòng. Danh sách dài có thể cuộn trong khung.</p>
  </>;
}
