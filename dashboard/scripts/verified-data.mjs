import { readFile, mkdir, writeFile, rename } from 'node:fs/promises';
import { createHash, randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { calculateOverview } from '../src/services/overviewMetrics.js';
import { prepareAnalysis } from '../src/services/overviewAnalysis.js';
import { prepareClustering } from '../src/services/clustering.js';
import { prepareDailyActivity } from '../src/services/dailyActivity.js';
import { prepareWatchDuration } from '../src/services/watchDuration.js';
import { prepareCombinedAnalysis } from '../src/services/combinedAnalysis.js';

export const files = ['stats_action_distribution.json', 'kmeans_assignments.json',
  'stats_hourly_activity.json', 'stats_daily_active_users.json', 'stats_top_movies_by_play.json',
  'stats_top_genres.json', 'stats_watch_duration_summary.json', 'stats_user_movie_time.json',
  'kmeans_model_metadata.json', 'kmeans_k_search.json', 'kmeans_cluster_profiles.json'];
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const json = async file => JSON.parse(await readFile(file, 'utf8'));
const dashboardRoot = fileURLToPath(new URL('../', import.meta.url));
const repository = path.resolve(dashboardRoot, '..');

export async function verifyRun(root, runId) {
  if (!/^tv2-[a-f0-9]{12}$/.test(runId)) throw new Error('Run ID không hợp lệ.');
  const run = path.join(root, 'evidence/week2-tv2', runId);
  const [status, context, summary, manifest, source, before, after] = await Promise.all(
    ['run_status.json', 'run_context.json', 'pipeline_summary.json', 'output_manifest.json',
      'source_manifest.json', 'raw-before.json', 'raw-after.json'].map(name => json(path.join(run, name))));
  const requiredChecks = ['pipeline_pass','raw_unchanged','protected_tv1_unchanged','no_local_fallback','fixtures_pass'];
  if (status.status !== 'PASS' || summary.status !== 'PASS' || manifest.status !== 'PASS'
      || [status,summary,manifest,context].some(row => row.run_id !== runId)
      || summary.local_fallback !== false || requiredChecks.some(key => status.checks?.[key] !== true)
      || summary.model_reload_assignments_match !== true) throw new Error('Run chưa được xác minh PASS đầy đủ.');
  const sourceHash = hash(await readFile(path.join(run, 'source_manifest.json')));
  if (sourceHash !== context.source_manifest_sha256 || sourceHash !== summary.source_manifest_sha256
      || before.status !== 'PASS' || after.status !== 'PASS'
      || before.source_manifest_sha256 !== sourceHash || after.source_manifest_sha256 !== sourceHash
      || summary.movies_uri !== source.movies_uri || summary.logs_uri !== source.logs_uri
      || !source.movies_uri?.startsWith('hdfs://namenode:9000/')
      || !source.logs_uri?.includes(`/raw/user_logs/${context.flume_run_id}/`)) throw new Error('Nguồn HDFS/provenance không khớp run.');
  const fingerprint = rows => JSON.stringify(rows.map(row => [row.uri,row.bytes,row.sha256]).sort((a,b) => a[0].localeCompare(b[0])));
  if (fingerprint(before.files) !== fingerprint(after.files)) throw new Error('Raw đã thay đổi trong khi chạy.');
  const expected = source.files.map(row => ({ ...row, uri:source.authority + row.hdfs_path }));
  if (fingerprint(before.files) !== fingerprint(expected)) throw new Error('Raw không khớp source manifest.');
  if (!manifest.artifacts?.length || manifest.artifacts.some(row => row.rows !== row.read_back_rows)) throw new Error('Output chưa đọc lại thành công.');
  if (!context.code_hashes || Object.keys(context.code_hashes).length < 10) throw new Error('Thiếu hash source đã thực thi.');
  for (const [name,expected] of Object.entries(context.code_hashes)) {
    const target = path.resolve(root,name);
    if (!target.startsWith(path.resolve(root) + path.sep) || hash(await readFile(target)) !== expected) throw new Error(`Source đã thay đổi sau run: ${name}`);
  }
  const inputs = await Promise.all(files.map(async name => {
    const bytes = await readFile(path.join(run,'dashboard',name));
    const proof = manifest.dashboard_files?.[name];
    if (!proof || proof.bytes !== bytes.length || proof.sha256 !== hash(bytes)) throw new Error(`Hash output không khớp: ${name}`);
    const rows = JSON.parse(bytes.toString('utf8'));
    if (!Array.isArray(rows) || !rows.length) throw new Error(`${name}: cần mảng dữ liệu không rỗng.`);
    return { name,bytes,proof };
  }));
  const data = Object.fromEntries(inputs.map(input => [input.name,JSON.parse(input.bytes.toString('utf8'))]));
  const users = data['kmeans_assignments.json'];
  if (data['stats_action_distribution.json'].reduce((sum,row) => sum + row.count,0) !== summary.clean_events
      || users.length !== summary.user_count || new Set(users.map(row => row.userId)).size !== users.length
      || users.reduce((sum,row) => sum + row.eventCount,0) !== summary.clean_events
      || data['stats_hourly_activity.json'].reduce((sum,row) => sum + row.eventCount,0) !== summary.clean_events) throw new Error('Kết quả Dashboard không khớp tổng pipeline.');
  const overview = calculateOverview(data['stats_action_distribution.json'],users);
  prepareAnalysis(data['stats_action_distribution.json'],data['stats_hourly_activity.json'],data['stats_top_movies_by_play.json'],overview.totalEvents);
  prepareClustering(data['kmeans_model_metadata.json'],data['kmeans_k_search.json'],data['kmeans_cluster_profiles.json'],users);
  prepareDailyActivity(data['stats_daily_active_users.json']);
  prepareWatchDuration(data['stats_watch_duration_summary.json']);
  prepareCombinedAnalysis(data['stats_user_movie_time.json']);
  const dates = data['stats_daily_active_users.json'].map(row => row.date).sort();
  const metadata = { schemaVersion:1, status:'PASS', runId, flumeRunId:context.flume_run_id,
    hdfsRunId:context.hdfs_run_id, generatedAt:summary.finished_at_utc, verifiedAt:status.finished_at_utc,
    timezone:summary.environment.calendar_timezone, firstDate:dates[0], lastDate:dates.at(-1),
    isSynthetic:true, staleAfterHours:24, sourceManifestSha256:sourceHash,
    files:Object.fromEntries(inputs.map(input => [input.name,input.proof])) };
  if (!Number.isFinite(Date.parse(metadata.verifiedAt)) || metadata.timezone !== 'Asia/Ho_Chi_Minh') throw new Error('Thời gian xác minh/múi giờ không hợp lệ.');
  return { inputs,metadata };
}

export async function sync(runId) {
  runId ??= (await json(path.join(dashboardRoot,'data-source.json'))).runId;
  const { inputs,metadata } = await verifyRun(repository,runId);
  const parent = path.join(dashboardRoot,'public/data');
  await mkdir(parent,{ recursive:true });
  const destination = path.join(parent,runId);
  let exists = false;
  try { await mkdir(destination); }
  catch (error) { if (error.code !== 'EEXIST') throw error; exists = true; }
  if (exists) {
    for (const input of inputs) {
      try {
        if (hash(await readFile(path.join(destination,input.name))) !== input.proof.sha256) throw new Error('Snapshot frontend đã thay đổi; không ghi đè.');
      } catch (error) { if (error.code !== 'ENOENT') throw error; }
    }
  }
  for (const input of inputs) {
    try { await writeFile(path.join(destination,input.name),input.bytes,{ flag:'wx' }); }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
  }
  // Snapshot directory is immutable; publish its selector after every file exists.
  const temporary = path.join(parent,`source-${randomUUID()}.tmp`);
  await writeFile(temporary,JSON.stringify(metadata,null,2) + '\n',{ flag:'wx' });
  await rename(temporary,path.join(parent,'source.json'));
  await writeFile(path.join(dashboardRoot,'data-source.json'),JSON.stringify({ runId },null,2) + '\n');
  console.log(`Đã xác minh và đồng bộ ${inputs.length} JSON từ ${runId}.`);
}
