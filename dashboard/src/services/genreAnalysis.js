import { requireRows, requireCount } from './overviewMetrics.js';

export function prepareGenres(rows) {
  requireRows(rows, 'stats_top_genres.json');
  const names = new Set();
  const genres = rows.map((row) => {
    if (typeof row.genre !== 'string' || !row.genre.trim() || names.has(row.genre)) {
      throw new Error('Tên thể loại thiếu hoặc trùng lặp.');
    }
    names.add(row.genre);
    requireCount(row.playCount, 'Số sự kiện play theo thể loại');
    return { ...row };
  }).sort((a, b) => b.playCount - a.playCount || a.genre.localeCompare(b.genre, 'en'));

  const first = genres[0];
  const second = genres[1] ?? null;
  return { genres, first, second, gap: second ? first.playCount - second.playCount : null };
}

export function selectGenres(genres, limit) {
  if (!['5', '10', 'all'].includes(limit)) throw new Error('Lựa chọn số thể loại không hợp lệ.');
  return limit === 'all' ? genres : genres.slice(0, Number(limit));
}
