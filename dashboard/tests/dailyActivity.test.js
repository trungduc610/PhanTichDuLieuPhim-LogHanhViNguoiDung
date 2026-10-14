import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { prepareDailyActivity, displayDate } from '../src/services/dailyActivity.js';
import { MissingDataError } from '../src/services/overviewMetrics.js';

const source = new URL('../../evidence/week2-tv2/tv2-4ed70c10cd84/dashboard/stats_daily_active_users.json', import.meta.url);
const rows = JSON.parse(await readFile(source, 'utf8'));
test('DAU khớp 30 ngày dữ liệu thật; không cộng thành người dùng toàn kỳ', () => {
  const result = prepareDailyActivity([...rows].reverse());
  assert.deepEqual(result.rows, rows);
  assert.equal(result.days, 30);
  assert.equal(result.firstDate, '2026-09-01');
  assert.equal(result.lastDate, '2026-09-30');
  assert.equal(result.min, 1000);
  assert.equal(result.max, 1000);
  assert.equal(displayDate(result.firstDate), '01/09/2026');
  assert.equal('totalUsers' in result, false);
});
test('Báo lỗi dữ liệu DAU rỗng, ngày trùng/sai và số người dùng sai', () => {
  assert.throws(() => prepareDailyActivity([]), MissingDataError);
  assert.throws(() => prepareDailyActivity([...rows, rows[0]]), /trùng/);
  const invalid = structuredClone(rows);
  invalid[0].date = '2026-09-31';
  assert.throws(() => prepareDailyActivity(invalid), /không hợp lệ/);
  invalid[0] = {...rows[0], activeUsers: null};
  assert.throws(() => prepareDailyActivity(invalid), /số nguyên/);
});
