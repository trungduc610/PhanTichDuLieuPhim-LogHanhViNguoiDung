import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { prepareWatchDuration, durationFields } from '../src/services/watchDuration.js';
import { number } from '../src/services/formatNumbers.js';
import { MissingDataError } from '../src/services/overviewMetrics.js';

const source = new URL('../../evidence/week2-tv2/tv2-4ed70c10cd84/dashboard/stats_watch_duration_summary.json', import.meta.url);
const rows = JSON.parse(await readFile(source, 'utf8'));

test('Giữ nguyên cả sáu thống kê và đơn vị từ JSON, không sửa dữ liệu nguồn', () => {
  const before = JSON.stringify(rows);
  const result = prepareWatchDuration([...rows].reverse());
  assert.deepEqual(result.allEvents, rows.find((row) => row.scope === 'all_events'));
  assert.deepEqual(result.watchSegments, rows.find((row) => row.scope === 'watch_segments'));
  assert.deepEqual(durationFields.map((field) => field.key), ['count', 'mean', 'median', 'min', 'max', 'stddev']);
  assert.equal(result.meanDifference, result.watchSegments.mean - result.allEvents.mean);
  assert.equal(JSON.stringify(rows), before);
});

test('Định dạng tiếng Việt, giây, tối đa 3 số lẻ khớp toàn bộ giá trị thực tế', () => {
  assert.deepEqual(rows.map((row) => durationFields.map(({ key }) => number(row[key]))), [
    ['1.000.000', '1.458,785', '0', '0', '10.800', '2.654,32'],
    ['348.474', '4.186,21', '3.833', '1', '10.800', '2.966,537'],
  ]);
  assert.equal(number(prepareWatchDuration(rows).meanDifference), '2.727,425');
});

test('Báo dữ liệu thiếu, nhóm trùng hoặc sai đơn vị', () => {
  assert.throws(() => prepareWatchDuration([]), MissingDataError);
  assert.throws(() => prepareWatchDuration(rows.slice(0, 1)), MissingDataError);
  assert.throws(() => prepareWatchDuration([...rows, rows[0]]), /trùng/);
  const invalid = structuredClone(rows);
  invalid[0].unit = 'minutes';
  assert.throws(() => prepareWatchDuration(invalid), /Đơn vị/);
});

test('Không đổi giá trị null, số âm hoặc số không hữu hạn thành số liệu hiển thị', () => {
  for (const key of ['mean', 'median', 'min', 'max', 'stddev']) {
    for (const value of [null, -1, Infinity, NaN]) {
      const invalid = structuredClone(rows);
      invalid[0][key] = value;
      assert.throws(() => prepareWatchDuration(invalid), /không hợp lệ/);
    }
  }
  const invalid = structuredClone(rows);
  invalid[1].min = 0;
  assert.throws(() => prepareWatchDuration(invalid), /lớn hơn 0/);
});
