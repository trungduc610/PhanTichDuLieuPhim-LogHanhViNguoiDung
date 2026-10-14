import { requireRows, requireCount } from './overviewMetrics.js';

export function prepareDailyActivity(input) {
  requireRows(input, 'stats_daily_active_users.json');
  const dates = new Set();
  const rows = input.map(row => {
    if (typeof row.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(row.date)
        || !Number.isFinite(Date.parse(`${row.date}T00:00:00Z`))
        || new Date(`${row.date}T00:00:00Z`).toISOString().slice(0, 10) !== row.date
        || dates.has(row.date)) throw new Error('Ngày DAU thiếu, không hợp lệ hoặc bị trùng.');
    dates.add(row.date);
    requireCount(row.activeUsers, 'Người dùng hoạt động trong ngày');
    return { ...row };
  }).sort((a, b) => a.date.localeCompare(b.date));
  const values = rows.map(row => row.activeUsers);
  return { rows, days: rows.length, firstDate: rows[0].date, lastDate: rows.at(-1).date,
    min: Math.min(...values), max: Math.max(...values) };
}

export const displayDate = (date) => date.split('-').reverse().join('/');
