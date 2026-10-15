import { selectedSource, copiedSource } from './selectedSource.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { prepareGenres, selectGenres } from '../src/services/genreAnalysis.js';
import { MissingDataError } from '../src/services/overviewMetrics.js';

const source = selectedSource('stats_top_genres.json');
const rows = JSON.parse(await readFile(source, 'utf8'));

test('Xếp hạng, hai thể loại đầu và chênh lệch khớp JSON thực tế', () => {
  const result = prepareGenres(rows);
  assert.equal(result.genres.length, 20);
  assert.equal(result.first.genre, 'Comedy');
  assert.equal(result.first.playCount, 144882);
  assert.equal(result.second.genre, 'Drama');
  assert.equal(result.second.playCount, 143222);
  assert.equal(result.gap, 1660);
  assert.deepEqual(result.genres, rows);
});

test('Top 5, Top 10, toàn bộ và thứ tự nguồn được giữ nguyên', () => {
  const input = [...rows].reverse();
  const before = JSON.stringify(input);
  const { genres } = prepareGenres(input);
  assert.equal(selectGenres(genres, '5').length, 5);
  assert.equal(selectGenres(genres, '10').length, 10);
  assert.equal(selectGenres(genres, 'all').length, rows.length);
  assert.deepEqual(selectGenres(genres, '5'), rows.slice(0, 5));
  assert.equal(JSON.stringify(input), before);
  assert.throws(() => selectGenres(genres, '20'), /không hợp lệ/);
});

test('Từ chối dữ liệu trống, tên trùng và số đếm không hợp lệ', () => {
  assert.throws(() => prepareGenres([]), MissingDataError);
  assert.throws(() => prepareGenres({}), /phải là mảng/);
  assert.throws(() => prepareGenres([...rows, rows[0]]), /trùng/);
  const invalid = structuredClone(rows);
  invalid[0].playCount = null;
  assert.throws(() => prepareGenres(invalid), /số nguyên/);
  invalid[0].playCount = -1;
  assert.throws(() => prepareGenres(invalid), /số nguyên/);
  invalid[0].genre = '';
  assert.throws(() => prepareGenres(invalid), /Tên thể loại/);
});

test('Một thể loại không tạo nhận xét so sánh thiếu căn cứ', () => {
  const result = prepareGenres(rows.slice(0, 1));
  assert.equal(result.second, null);
  assert.equal(result.gap, null);
  assert.equal(selectGenres(result.genres, '10').length, 1);
});
