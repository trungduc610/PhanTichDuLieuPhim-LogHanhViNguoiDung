import { requireRows, requireCount, MissingDataError } from './overviewMetrics.js';

export const durationFields = [
  { key: 'count', label: 'Số bản ghi', unit: 'bản ghi' },
  { key: 'mean', label: 'Thời lượng trung bình', unit: 'giây' },
  { key: 'median', label: 'Trung vị (xấp xỉ)', unit: 'giây' },
  { key: 'min', label: 'Nhỏ nhất', unit: 'giây' },
  { key: 'max', label: 'Lớn nhất', unit: 'giây' },
  { key: 'stddev', label: 'Độ lệch chuẩn mẫu', unit: 'giây' },
];

export function prepareWatchDuration(rows) {
  requireRows(rows, 'stats_watch_duration_summary.json');
  const groups = new Map();
  for (const row of rows) {
    if (!['all_events', 'watch_segments'].includes(row.scope) || groups.has(row.scope)) {
      throw new Error('Nhóm thống kê thời lượng không hợp lệ hoặc bị trùng.');
    }
    if (row.unit !== 'seconds') throw new Error('Đơn vị thời lượng phải là giây (seconds).');
    requireCount(row.count, 'Số bản ghi thời lượng');
    if (row.count === 0) throw new MissingDataError(`Nhóm ${row.scope} chưa có bản ghi.`);
    for (const { key } of durationFields.filter((field) => field.key !== 'count')) {
      if (typeof row[key] !== 'number' || !Number.isFinite(row[key]) || row[key] < 0) {
        throw new Error(`${row.scope}: chỉ số ${key} thiếu hoặc không hợp lệ.`);
      }
    }
    if (row.min > row.max || row.mean < row.min || row.mean > row.max
        || row.median < row.min || row.median > row.max) {
      throw new Error('Các thống kê thời lượng không nhất quán.');
    }
    if (row.scope === 'watch_segments' && row.min <= 0) {
      throw new Error('Nhóm đoạn xem phải chỉ có thời lượng lớn hơn 0.');
    }
    groups.set(row.scope, { ...row });
  }
  if (!groups.has('all_events') || !groups.has('watch_segments')) {
    throw new MissingDataError('Thiếu nhóm toàn bộ sự kiện hoặc đoạn xem có thời lượng dương.');
  }
  const allEvents = groups.get('all_events');
  const watchSegments = groups.get('watch_segments');
  if (watchSegments.count > allEvents.count) throw new Error('Số bản ghi đoạn xem vượt toàn bộ sự kiện.');
  return { allEvents, watchSegments, meanDifference: watchSegments.mean - allEvents.mean };
}
