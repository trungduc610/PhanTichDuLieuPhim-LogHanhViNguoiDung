import { selectedSource, copiedSource } from './selectedSource.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { prepareCombinedAnalysis, selectCombinedHour, hourLabel } from '../src/services/combinedAnalysis.js';
import { MissingDataError } from '../src/services/overviewMetrics.js';

const source = selectedSource('stats_user_movie_time.json');
const rows = JSON.parse(await readFile(source, 'utf8'));

test('Đủ 72 dòng, 24 giờ và 3 phim mỗi giờ; giữ nguyên giá trị và thứ hạng Spark', () => {
  const before = JSON.stringify(rows);
  const data = prepareCombinedAnalysis([...rows].reverse());
  assert.equal(data.rows.length, 72);
  assert.equal(data.byHour.length, 24);
  for (let hour = 0; hour < 24; hour++) {
    assert.deepEqual(data.byHour[hour], rows.filter(row => row.hour === hour).map(row => ({...row, hourLabel: hourLabel(hour)})));
    assert.deepEqual(data.byHour[hour].map(row => row.rank), [1, 2, 3]);
    const selected = selectCombinedHour(data, hour);
    assert.equal(selected.leader.playCount, data.byHour[hour][0].playCount);
    assert.equal(selected.gap, data.byHour[hour][0].playCount - data.byHour[hour][1].playCount);
  }
  assert.equal(JSON.stringify(rows), before);
});

test('Đổi giờ thay đổi đúng Top 3 và chênh lệch, không dùng một kết quả cố định', () => {
  const data = prepareCombinedAnalysis(rows);
  assert.equal(selectCombinedHour(data, 0).gap, 212);
  assert.equal(selectCombinedHour(data, 23).gap, 634);
  assert.equal(selectCombinedHour(data, 23).leader.distinctUsers, 687);
  assert.notDeepEqual(selectCombinedHour(data, 0).movies, selectCombinedHour(data, 23).movies);
  assert.equal(hourLabel(0), '00h');
  assert.equal(hourLabel(23), '23h');
  assert.throws(() => selectCombinedHour(data, 24), /không hợp lệ/);
});

test('Báo lỗi khi thiếu giờ/phim, trùng thứ hạng hoặc số đếm sai', () => {
  assert.throws(() => prepareCombinedAnalysis([]), MissingDataError);
  assert.throws(() => prepareCombinedAnalysis(rows.slice(1)), /72 dòng/);
  assert.throws(() => prepareCombinedAnalysis([...rows, rows[0]]), /trùng/);
  const invalid = structuredClone(rows);
  invalid[0].distinctUsers = invalid[0].playCount + 1;
  assert.throws(() => prepareCombinedAnalysis(invalid), /không hợp lệ/);
  invalid[0] = {...rows[0], hour: 24};
  assert.throws(() => prepareCombinedAnalysis(invalid), /0 đến 23/);
  invalid[0] = {...rows[0], playCount: null};
  assert.throws(() => prepareCombinedAnalysis(invalid), /số nguyên/);
});

test('Không âm thầm tính lại thứ hạng khi khác quy tắc Spark', () => {
  const invalid = structuredClone(rows);
  [invalid[0].rank, invalid[1].rank] = [invalid[1].rank, invalid[0].rank];
  assert.throws(() => prepareCombinedAnalysis(invalid), /quy tắc Spark/);
});
