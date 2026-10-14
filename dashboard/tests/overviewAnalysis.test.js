import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { prepareAnalysis } from '../src/services/overviewAnalysis.js';
import { MissingDataError } from '../src/services/overviewMetrics.js';

const source = new URL('../../evidence/week2-tv2/tv2-4ed70c10cd84/dashboard/', import.meta.url);
const read = async (name) => JSON.parse(await readFile(new URL(name, source), 'utf8'));
const actions = await read('stats_action_distribution.json');
const hourly = await read('stats_hourly_activity.json');
const movies = await read('stats_top_movies_by_play.json');
const total = actions.reduce((sum, row) => sum + row.count, 0);

test('Nhận xét, tỷ lệ và Top 5 khớp kết quả JSON thực tế', () => {
  const result = prepareAnalysis(actions, hourly, movies, total);
  assert.equal(result.actions[0].action, 'play');
  assert.equal(result.actions[0].percentage, 348474 * 100 / total);
  assert.deepEqual(result.peakHours.map((row) => row.hour), [23]);
  assert.equal(result.peakHours[0].eventCount, 64062);
  assert.deepEqual(result.topMovies.map((row) => row.movieId), [7262, 100044, 45720, 52281, 7074]);
  assert.equal(result.topMovies[0].playCount, 17064);
  assert.equal(result.movies.length, 20);
  assert.deepEqual(result.movies.slice(0, 5).map((row) => row.movieId), result.topMovies.map((row) => row.movieId));
});

test('Sắp xếp dữ liệu mà không sửa mảng nguồn', () => {
  const reversedHours = [...hourly].reverse();
  const reversedMovies = [...movies].reverse();
  const before = JSON.stringify({ reversedHours, reversedMovies });
  const result = prepareAnalysis(actions, reversedHours, reversedMovies, total);
  assert.equal(result.hourly[0].hour, 0);
  assert.equal(result.topMovies[0].movieId, 7262);
  assert.equal(JSON.stringify({ reversedHours, reversedMovies }), before);
});

test('Từ chối dữ liệu thiếu, tỷ lệ sai và các giờ không nhất quán', () => {
  assert.throws(() => prepareAnalysis(actions, [], movies, total), MissingDataError);
  const invalidActions = structuredClone(actions);
  invalidActions[0].percentage += 1;
  assert.throws(() => prepareAnalysis(invalidActions, hourly, movies, total), /Tỷ lệ/);
  assert.throws(() => prepareAnalysis(actions, hourly.slice(1), movies, total), /chưa đủ/);
  const invalidHours = structuredClone(hourly);
  invalidHours[0].eventCount += 1;
  assert.throws(() => prepareAnalysis(actions, invalidHours, movies, total), /không khớp/);
  invalidHours[0].hour = 24;
  assert.throws(() => prepareAnalysis(actions, invalidHours, movies, total), /0–23/);
  assert.throws(() => prepareAnalysis(actions, hourly, movies.slice(0, 4), total), /Top 5/);
});
