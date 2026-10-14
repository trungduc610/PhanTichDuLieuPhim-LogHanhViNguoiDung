import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { prepareClustering, findUsers, formatProfile, formatCompletion } from '../src/services/clustering.js';
import { loadClustering } from '../src/services/dashboardData.js';
import { MissingDataError } from '../src/services/overviewMetrics.js';

const source = new URL('../../evidence/week2-tv2/tv2-4ed70c10cd84/dashboard/', import.meta.url);
const files = ['kmeans_model_metadata.json', 'kmeans_k_search.json', 'kmeans_cluster_profiles.json', 'kmeans_assignments.json'];
const inputs = await Promise.all(files.map(async name => JSON.parse(await readFile(new URL(name, source), 'utf8'))));
const data = prepareClustering(...inputs);

test('Metadata, đặc trưng, K search, hồ sơ và gán cụm khớp JSON', () => {
  assert.equal(data.metadata.bestK, 2);
  assert.equal(data.metadata.silhouette, inputs[0][0].silhouette);
  assert.deepEqual(data.features, JSON.parse(inputs[0][0].featureColumnsJson));
  assert.deepEqual(data.profiles, inputs[2]);
  assert.equal(data.profiles.reduce((sum, row) => sum + row.userCount, 0), 1000);
  assert.deepEqual(data.profiles.map(row => row.userCount), [237, 763]);
  for (const profile of data.profiles) assert.equal(data.assignments.filter(row => row.cluster === profile.cluster).length, profile.userCount);
  assert.deepEqual(data.assignments, inputs[3]);
});

test('Tỷ lệ hoàn thành hiển thị nhân 100; không nhầm hai trường thời lượng', () => {
  assert.equal(formatProfile('avgCompletionRate', data.profiles[0].avgCompletionRate), '48,62%');
  assert.equal(formatProfile('avgCompletionRate', data.profiles[1].avgCompletionRate), '58,22%');
  assert.equal(formatCompletion(data.assignments[0]), '57,96%');
  assert.notEqual(data.profiles[0].avgTotalWatchDuration, data.profiles[0].avgWatchDuration);
  assert.equal(formatProfile('avgTotalWatchDuration', data.profiles[0].avgTotalWatchDuration), '1.612.246,895');
  assert.equal(formatProfile('avgWatchDuration', data.profiles[0].avgWatchDuration), '3.743,761');
  assert.equal(formatCompletion({...data.assignments[0], completionRateDefined: false}), 'Chưa xác định');
});

test('Tìm một phần hoặc chính xác userId, kết hợp lọc cụm và phân trang', () => {
  assert.equal(findUsers(data.assignments).rows.length, 20);
  const next = findUsers(data.assignments, {page: 2});
  assert.equal(next.rows[0].userId, data.assignments[20].userId);
  assert.equal(findUsers(data.assignments, {query: data.assignments[0].userId}).total, 1);
  assert.equal(findUsers(data.assignments, {query: ' SIM-USER-0000 '}).total, data.assignments.filter(row => row.userId.includes('sim-user-0000')).length);
  assert.equal(findUsers(data.assignments, {cluster: '0'}).total, 237);
  assert.equal(findUsers(data.assignments, {cluster: '1'}).total, 763);
  assert.equal(findUsers(data.assignments, {query: data.assignments[0].userId, cluster: '0'}).total, 0);
  const last = findUsers(data.assignments, {cluster: '0', page: 99});
  assert.equal(last.page, 12);
  assert.equal(last.rows.length, 17);
  assert.equal(findUsers(data.assignments, {query: 'khong-co-user'}).rows.length, 0);
  assert.equal(findUsers(data.assignments, {query: 'khong-co-user'}).totalPages, 1);
});

test('Không sửa nguồn; từ chối dữ liệu trống và nguồn không nhất quán', () => {
  const snapshot = JSON.stringify(inputs);
  prepareClustering(...inputs);
  assert.equal(JSON.stringify(inputs), snapshot);
  assert.throws(() => prepareClustering([], ...inputs.slice(1)), MissingDataError);
  let invalid = structuredClone(inputs);
  invalid[0][0].featureColumnsJson = '{';
  assert.throws(() => prepareClustering(...invalid), /featureColumnsJson/);
  invalid = structuredClone(inputs);
  invalid[0][0].bestK = 3;
  assert.throws(() => prepareClustering(...invalid), /metadata/);
  invalid = structuredClone(inputs);
  invalid[2][0].userCount++;
  assert.throws(() => prepareClustering(...invalid), /kích thước/);
  invalid = structuredClone(inputs);
  invalid[2][0].avgCompletionRate = 48.6;
  assert.throws(() => prepareClustering(...invalid), /phạm vi/);
  invalid = structuredClone(inputs);
  invalid[3][0].cluster = 99;
  assert.throws(() => prepareClustering(...invalid), /mã cụm/);
});

test('Loader báo lỗi JSON hỏng, thiếu tệp và metadata rỗng', async () => {
  const originalFetch = globalThis.fetch;
  const contents = Object.fromEntries(files.map((name, index) => [name, JSON.stringify(inputs[index])]));
  try {
    globalThis.fetch = async url => new Response(contents[String(url).split('/').pop()], {status: 200});
    const loaded = await loadClustering();
    assert.equal(loaded.metadata.users, 1000);
    globalThis.fetch = async () => new Response('{broken', {status: 200});
    await assert.rejects(loadClustering(), /JSON không hợp lệ/);
    globalThis.fetch = async () => new Response('', {status: 404});
    await assert.rejects(loadClustering(), MissingDataError);
    globalThis.fetch = async () => new Response('[]', {status: 200});
    await assert.rejects(loadClustering(), MissingDataError);
  } finally { globalThis.fetch = originalFetch; }
});
