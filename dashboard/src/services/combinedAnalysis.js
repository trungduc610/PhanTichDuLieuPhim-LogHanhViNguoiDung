import { requireRows, requireCount } from './overviewMetrics.js';

export const hourLabel = (hour) => `${String(hour).padStart(2, '0')}h`;

export function prepareCombinedAnalysis(input) {
  requireRows(input, 'stats_user_movie_time.json');
  const byHour = Array.from({ length: 24 }, () => []);
  for (const row of input) {
    if (!Number.isInteger(row.hour) || row.hour < 0 || row.hour > 23) {
      throw new Error('Giờ phải là số nguyên từ 0 đến 23.');
    }
    if (!Number.isInteger(row.rank) || row.rank < 1 || row.rank > 3) {
      throw new Error('Thứ hạng phải từ 1 đến 3.');
    }
    requireCount(row.movieId, 'Mã phim');
    requireCount(row.playCount, 'Số sự kiện play');
    requireCount(row.distinctUsers, 'Số người dùng khác nhau');
    if (typeof row.title !== 'string' || !row.title.trim()) throw new Error('Thiếu tên phim.');
    if (row.playCount === 0 || row.distinctUsers === 0 || row.distinctUsers > row.playCount) {
      throw new Error('Số sự kiện play hoặc người dùng trong nhóm không hợp lệ.');
    }
    const group = byHour[row.hour];
    if (group.some((item) => item.rank === row.rank || item.movieId === row.movieId)) {
      throw new Error('Phim hoặc thứ hạng bị trùng trong cùng một giờ.');
    }
    group.push({ ...row, hourLabel: hourLabel(row.hour) });
  }
  for (const group of byHour) {
    if (group.length !== 3) throw new Error('Cần đủ 24 khung giờ, mỗi giờ đúng 3 phim (72 dòng).');
    group.sort((a, b) => a.rank - b.rank);
    for (let index = 1; index < group.length; index++) {
      const previous = group[index - 1];
      const current = group[index];
      if (previous.playCount < current.playCount
          || (previous.playCount === current.playCount && previous.movieId > current.movieId)) {
        throw new Error('Thứ hạng không khớp quy tắc Spark: play giảm dần, mã phim tăng dần khi bằng nhau.');
      }
    }
  }
  return { rows: byHour.flat(), byHour };
}

export function selectCombinedHour(data, hour) {
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) throw new Error('Khung giờ được chọn không hợp lệ.');
  const movies = data.byHour[hour];
  return { movies, leader: movies[0], runnerUp: movies[1], gap: movies[0].playCount - movies[1].playCount };
}
