import { requireRows, requireCount } from './overviewMetrics.js';

const actionLabels = {
  view: 'Xem thông tin',
  play: 'Phát phim',
  pause: 'Tạm dừng',
  stop: 'Dừng phát',
  complete: 'Hoàn thành',
};

export function prepareAnalysis(actions, hourly, movies, totalEvents) {
  requireRows(actions, 'Phân bố hành vi');
  requireRows(hourly, 'Hoạt động theo giờ');
  requireRows(movies, 'Phim theo số sự kiện phát');
  requireCount(totalEvents, 'Tổng sự kiện');
  if (totalEvents === 0) throw new Error('Không có sự kiện để tính phân bố hành vi.');

  const actionData = actions.map((row) => {
    requireCount(row.count, 'Số sự kiện hành vi');
    const percentage = row.count * 100 / totalEvents;
    if (!Number.isFinite(row.percentage) || Math.abs(row.percentage - percentage) > 0.0001) {
      throw new Error('Tỷ lệ hành vi không khớp số sự kiện.');
    }
    return { ...row, label: actionLabels[row.action] || row.action };
  }).sort((a, b) => b.count - a.count);

  const hours = new Set();
  const hourlyData = hourly.map((row) => {
    if (!Number.isInteger(row.hour) || row.hour < 0 || row.hour > 23 || hours.has(row.hour)) {
      throw new Error('Giờ thiếu, trùng hoặc nằm ngoài khoảng 0–23.');
    }
    hours.add(row.hour);
    requireCount(row.eventCount, 'Sự kiện theo giờ');
    requireCount(row.playCount, 'Sự kiện phát theo giờ');
    requireCount(row.distinctUsers, 'Người dùng theo giờ');
    if (row.playCount > row.eventCount || row.distinctUsers > row.eventCount) {
      throw new Error('Số đếm theo giờ không hợp lệ.');
    }
    return { ...row, label: `${String(row.hour).padStart(2, '0')}h` };
  }).sort((a, b) => a.hour - b.hour);
  const playEvents = actions.find((row) => row.action === 'play')?.count;
  if (hours.size !== 24 || hourlyData.reduce((sum, row) => sum + row.eventCount, 0) !== totalEvents
      || hourlyData.reduce((sum, row) => sum + row.playCount, 0) !== playEvents) {
    throw new Error('Dữ liệu theo giờ chưa đủ hoặc không khớp phân bố hành vi.');
  }

  const ids = new Set();
  const rankedMovies = movies.map((row) => {
    requireCount(row.movieId, 'Mã phim');
    requireCount(row.playCount, 'Số sự kiện phát phim');
    if (ids.has(row.movieId) || typeof row.title !== 'string' || !row.title.trim()) {
      throw new Error('Mã phim trùng hoặc thiếu tên phim.');
    }
    ids.add(row.movieId);
    return { ...row };
  }).sort((a, b) => b.playCount - a.playCount || a.movieId - b.movieId);
  if (rankedMovies.length < 5) throw new Error('Chưa đủ dữ liệu cho Top 5 phim.');

  const peakEventCount = Math.max(...hourlyData.map((row) => row.eventCount));
  return {
    actions: actionData,
    hourly: hourlyData,
    movies: rankedMovies.slice(0, 20),
    topMovies: rankedMovies.slice(0, 5).map((row, index) => ({ ...row, rankLabel: `#${index + 1}` })),
    peakHours: hourlyData.filter((row) => row.eventCount === peakEventCount),
  };
}
