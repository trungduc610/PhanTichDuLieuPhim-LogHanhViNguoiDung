import { selectedSource, copiedSource } from './selectedSource.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = selectedSource('');
const copied = copiedSource;
const files = ['stats_action_distribution.json', 'stats_hourly_activity.json', 'stats_daily_active_users.json',
  'stats_top_movies_by_play.json', 'stats_top_genres.json', 'stats_watch_duration_summary.json',
  'stats_user_movie_time.json', 'kmeans_model_metadata.json', 'kmeans_k_search.json',
  'kmeans_cluster_profiles.json', 'kmeans_assignments.json'];
const read = async name => JSON.parse(await readFile(new URL(name, source), 'utf8'));

test('11 bản sao frontend giống nguyên nội dung evidence', async () => {
  for (const name of files) assert.equal(await readFile(new URL(name, copied), 'utf8'), await readFile(new URL(name, source), 'utf8'), name);
});
test('Đối chiếu chéo sự kiện, play, thời lượng và hồ sơ cụm trên kết quả thật', async () => {
  const [actions, hourly, users, profiles, durations] = await Promise.all([
    read('stats_action_distribution.json'), read('stats_hourly_activity.json'), read('kmeans_assignments.json'),
    read('kmeans_cluster_profiles.json'), read('stats_watch_duration_summary.json'),
  ]);
  const events = actions.reduce((sum,row) => sum + row.count,0);
  assert.equal(events, hourly.reduce((sum,row) => sum + row.eventCount,0));
  assert.equal(events, users.reduce((sum,row) => sum + row.eventCount,0));
  assert.equal(actions.find(row => row.action === 'play').count, users.reduce((sum,row) => sum + row.playCount,0));
  for (const row of actions) assert.ok(Math.abs(row.percentage - row.count * 100 / events) < 1e-10);
  const totalDuration = users.reduce((sum,row) => sum + row.totalWatchDuration,0);
  const close = (a,b) => assert.ok(Math.abs(a-b) <= Math.max(1, Math.abs(b))*1e-10, `${a} ≠ ${b}`);
  for (const row of durations) close(row.mean, totalDuration/row.count);
  const mapping = {avgPlayCount:'playCount', avgDistinctMovies:'distinctMovies', avgSessionCount:'sessionCount',
    avgCompletionRate:'completionRate', avgTotalWatchDuration:'totalWatchDuration', avgWatchDuration:'avgWatchDuration'};
  // Chỉ tính để kiểm chứng; frontend vẫn đọc trực tiếp profiles, không thay kết quả Spark.
  for (const profile of profiles) {
    const members = users.filter(row => row.cluster === profile.cluster);
    assert.equal(members.length, profile.userCount);
    for (const [target,key] of Object.entries(mapping)) close(profile[target], members.reduce((sum,row) => sum + row[key],0)/members.length);
  }
});
