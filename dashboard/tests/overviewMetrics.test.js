import { selectedSource, copiedSource } from './selectedSource.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { calculateOverview, MissingDataError } from '../src/services/overviewMetrics.js';

const source = selectedSource('');
const actions = JSON.parse(await readFile(new URL('stats_action_distribution.json', source), 'utf8'));
const assignments = JSON.parse(await readFile(new URL('kmeans_assignments.json', source), 'utf8'));

test('Tính đủ bốn chỉ số từ dữ liệu thật, phân biệt phiên có play với sự kiện play', () => {
  const metrics = calculateOverview(actions, assignments);
  assert.equal(metrics.totalEvents, assignments.reduce((sum, row) => sum + row.eventCount, 0));
  assert.equal(metrics.distinctUsers, new Set(assignments.map((row) => row.userId)).size);
  assert.equal(metrics.totalSessions, assignments.reduce((sum, row) => sum + row.sessionCount, 0));
  assert.equal(metrics.playedSessions, assignments.reduce((sum, row) => sum + row.playedSessionCount, 0));
  assert.notEqual(metrics.playedSessions, actions.find((row) => row.action === 'play').count);
});

test('Không hiển thị dữ liệu trống, sai cấu trúc hoặc userId trùng', () => {
  assert.throws(() => calculateOverview([], assignments), MissingDataError);
  assert.throws(() => calculateOverview({}, assignments), /phải là mảng/);
  assert.throws(() => calculateOverview(actions, [...assignments, assignments[0]]), /trùng lặp/);
});

test('Từ chối số phiên sai và hai nguồn không nhất quán', () => {
  const invalid = structuredClone(assignments);
  invalid[0].playedSessionCount = invalid[0].sessionCount + 1;
  assert.throws(() => calculateOverview(actions, invalid), /vượt/);
  invalid[0].playedSessionCount = assignments[0].playedSessionCount;
  invalid[0].sessionCount = null;
  assert.throws(() => calculateOverview(actions, invalid), /số nguyên/);
  const mismatched = structuredClone(actions);
  mismatched[0].count += 1;
  assert.throws(() => calculateOverview(mismatched, assignments), /không khớp/);
});
