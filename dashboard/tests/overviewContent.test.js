import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { selectedSource } from './selectedSource.js';
import { presentActions, hourRange } from '../src/content/overviewContent.js';
import { calculateOverview } from '../src/services/overviewMetrics.js';
import { prepareAnalysis } from '../src/services/overviewAnalysis.js';
import { buildCsv, overviewTables } from '../src/services/overviewExport.js';

const read = async name => JSON.parse(await readFile(selectedSource(name),'utf8'));
const actions = await read('stats_action_distribution.json');
const users = await read('kmeans_assignments.json');

test('Ngôn ngữ Tổng quan giữ nguyên mã, số đếm, tỷ lệ và nguồn, không ảnh hưởng trang chi tiết', async () => {
  const overview = calculateOverview(actions,users);
  const analysis = prepareAnalysis(actions,await read('stats_hourly_activity.json'),await read('stats_top_movies_by_play.json'),overview.totalEvents);
  const before = JSON.stringify(analysis.actions);
  const presented = presentActions(analysis.actions);
  assert.equal(JSON.stringify(analysis.actions),before);
  assert.deepEqual(presented.map(({label,...row})=>row),analysis.actions.map(({label,...row})=>row));
  assert.equal(presented.find(row=>row.action==='view').label,'Xem thông tin phim');
  assert.equal(analysis.actions.find(row=>row.action==='view').label,'Xem thông tin');
  const plays = presented.find(row=>row.action==='play').count;
  assert.equal(plays,users.reduce((sum,row)=>sum+row.playCount,0));
  assert.notEqual(plays,overview.playedSessions);
  assert.equal(overview.playedSessions,users.reduce((sum,row)=>sum+row.playedSessionCount,0));
});

test('CSV đổi nhãn tiếng Việt nhưng giữ mã action và tỷ lệ chưa làm tròn', () => {
  const presented = presentActions(actions);
  const csv = buildCsv(overviewTables.actions.columns,presented);
  const decode = line => [...line.matchAll(/"((?:[^"]|"")*)"(?:,|$)/g)].map(match=>match[1].replaceAll('""','"'));
  const records = csv.slice(1).trimEnd().split('\r\n').slice(1).map(decode);
  assert.equal(records.length,actions.length);
  assert.deepEqual(records.map(row=>row.slice(1)),actions.map(row=>[row.action,String(row.count),String(row.percentage)]));
});

test('Khoảng giờ có đủ đầu/cuối để đọc kết quả cao điểm, không cố định một khung giờ', () => {
  assert.equal(hourRange(0),'00:00–00:59');
  assert.equal(hourRange(23),'23:00–23:59');
});
