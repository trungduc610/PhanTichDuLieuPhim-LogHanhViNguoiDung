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
import { prepareGenres } from '../src/services/genreAnalysis.js';

export const files = ['stats_action_distribution.json', 'kmeans_assignments.json',
  'stats_hourly_activity.json', 'stats_daily_active_users.json', 'stats_top_movies_by_play.json',
  'stats_top_genres.json', 'stats_watch_duration_summary.json', 'stats_user_movie_time.json',
  'kmeans_model_metadata.json', 'kmeans_k_search.json', 'kmeans_cluster_profiles.json'];
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const json = async file => JSON.parse(await readFile(file, 'utf8'));
const dashboardRoot = fileURLToPath(new URL('../', import.meta.url));
const repository = path.resolve(dashboardRoot, '..');

function validateSchema(rows, schema, name) {
  if (schema?.type !== 'struct' || !schema.fields?.length) throw new Error(`${name}: thiếu schema bàn giao.`);
  const valid = (value, type, nullable) => {
    if (value === null) return nullable === true;
    if (typeof type === 'object' && type.type === 'array') return Array.isArray(value)
      && value.every(item => valid(item,type.elementType,type.containsNull));
    if (type === 'string') return typeof value === 'string';
    if (type === 'date') return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
      && new Date(value).toISOString().slice(0,10) === value;
    if (type === 'boolean') return typeof value === 'boolean';
    if (type === 'long' || type === 'integer') return Number.isSafeInteger(value);
    if (type === 'double') return typeof value === 'number' && Number.isFinite(value);
    return false;
  };
  for (const row of rows) {
    if (!row || typeof row !== 'object' || Array.isArray(row)
        || Object.keys(row).length !== schema.fields.length
        || schema.fields.some(field => !Object.hasOwn(row,field.name) || !valid(row[field.name],field.type,field.nullable))) {
      throw new Error(`${name}: dữ liệu không khớp schema bàn giao.`);
    }
  }
}

async function verifyHandoff(root, run, runId) {
  const handoff = await json(path.join(run,'handoff.json'));
  if (handoff.status !== 'PASS' || handoff.tv2_run_id !== runId || handoff.synthetic !== true
      || handoff.timezone?.calendar !== 'Asia/Ho_Chi_Minh'
      || handoff.hdfs_input?.local_fallback !== false) throw new Error('Handoff chưa PASS hoặc sai identity/timezone.');
  const receipts = ['run_status.json','pipeline_summary.json','input-hdfs-qa.json','spark-fixture-tests.json',
    'runtime-verification.json','result-verification.json','raw-preservation.json','host-tests-final.json','historical-preservation-after.json'];
  for (const name of receipts) {
    const proof = handoff.validation_receipts?.[name];
    const expected = path.join(run,name);
    if (!proof || path.resolve(root,proof.path) !== expected) throw new Error(`Đường dẫn biên nhận không khớp: ${name}`);
    const bytes = await readFile(expected);
    if (hash(bytes) !== proof.sha256) throw new Error(`SHA-256 biên nhận không khớp: ${name}`);
    const value = JSON.parse(bytes.toString('utf8'));
    if (value.status !== 'PASS' || (value.run_id && value.run_id !== runId)
        || (value.checks && Object.values(value.checks).some(check => check !== true))) {
      throw new Error(`Biên nhận chưa PASS đầy đủ: ${name}`);
    }
  }
  return handoff;
}

export async function verifyRun(root, runId, evidenceRoot = 'evidence/week3-tv2') {
  root = path.resolve(root);
  if (!/^tv2-[a-f0-9]{12}$/.test(runId)) throw new Error('Run ID không hợp lệ.');
  if (!['evidence/week2-tv2','evidence/week3-tv2'].includes(evidenceRoot)) throw new Error('Evidence root không hợp lệ.');
  const run = path.join(root, evidenceRoot, runId);
  const handoff = evidenceRoot === 'evidence/week3-tv2' ? await verifyHandoff(root,run,runId) : null;
  const [status, context, summary, manifest, source, before, after] = await Promise.all(
    ['run_status.json', 'run_context.json', 'pipeline_summary.json', 'output_manifest.json',
      'source_manifest.json', 'raw-before.json', 'raw-after.json'].map(name => json(path.join(run, name))));
  const requiredChecks = ['pipeline_pass','raw_unchanged','protected_tv1_unchanged','no_local_fallback','fixtures_pass'];
  if (status.status !== 'PASS' || summary.status !== 'PASS' || manifest.status !== 'PASS'
      || [status,summary,manifest,context].some(row => row.run_id !== runId)
      || summary.local_fallback !== false || requiredChecks.some(key => status.checks?.[key] !== true)
      || summary.model_reload_assignments_match !== true) throw new Error('Run chưa được xác minh PASS đầy đủ.');
  const sourceHash = hash(await readFile(path.join(run, 'source_manifest.json')));
  if (handoff && (handoff.hdfs_input.source_manifest_sha256 !== sourceHash
      || path.resolve(root,handoff.hdfs_input.source_manifest) !== path.join(run,'source_manifest.json')
      || handoff.tv1_flume_run !== context.flume_run_id || handoff.tv1_hdfs_run !== context.hdfs_run_id
      || handoff.hdfs_input.movies_uri !== summary.movies_uri || handoff.hdfs_input.logs_uri !== summary.logs_uri
      || handoff.hdfs_input.events !== summary.clean_events || handoff.hdfs_input.movies !== summary.movies
      || handoff.results_root !== summary.results_root || handoff.processed_root !== summary.processed_root
      || status.runtime_gate !== 'PASS' || status.checks.independent_runtime_verification !== true)) {
    throw new Error('Handoff/provenance không khớp pipeline.');
  }
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
  // Week 3 bàn giao bản chụp code đã chạy. Kiểm đúng byte lịch sử, không
  // phụ thuộc cách checkout code pipeline hiện tại hoặc chạy lại pipeline.
  const codeRoot = handoff ? path.join(run,'source-snapshot') : root;
  for (const [name,expected] of Object.entries(context.code_hashes)) {
    const target = path.resolve(codeRoot,name);
    if (!target.startsWith(codeRoot + path.sep) || hash(await readFile(target)) !== expected) throw new Error(`Source đã thay đổi sau run: ${name}`);
  }
  const inputs = await Promise.all(files.map(async name => {
    const target = path.join(run,'dashboard',name);
    const contracts = handoff?.dashboard_outputs?.filter(row => row.format === 'json'
      && row.name.replaceAll('/','_') + '.json' === name);
    const contract = contracts?.[0];
    if (handoff && (contracts.length !== 1 || path.resolve(root,contract.local_path) !== target
        || contract.hdfs_path !== `${handoff.results_root}/${contract.name}/json`
        || !Number.isSafeInteger(contract.rows) || contract.rows <= 0 || contract.rows !== contract.read_back_rows)) {
      throw new Error(`Hợp đồng output không khớp: ${name}`);
    }
    const bytes = await readFile(target);
    const proof = contract ? { bytes:contract.local_bytes, sha256:contract.local_sha256,
      rows:contract.rows, schema:contract.schema, localPath:contract.local_path } : manifest.dashboard_files?.[name];
    if (!proof || proof.bytes !== bytes.length || proof.sha256 !== hash(bytes)) throw new Error(`Hash output không khớp: ${name}`);
    if (handoff && (manifest.dashboard_files?.[name]?.bytes !== proof.bytes
        || manifest.dashboard_files?.[name]?.sha256 !== proof.sha256)) throw new Error(`Manifest/handoff không khớp: ${name}`);
    const rows = JSON.parse(bytes.toString('utf8'));
    if (!Array.isArray(rows) || !rows.length) throw new Error(`${name}: cần mảng dữ liệu không rỗng.`);
    if (contract) {
      if (rows.length !== contract.rows) throw new Error(`${name}: row count không khớp bàn giao.`);
      validateSchema(rows,contract.schema,name);
    }
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
  prepareGenres(data['stats_top_genres.json']);
  const sum = (rows,key) => rows.reduce((total,row) => total + row[key],0);
  const close = (actual,expected) => Math.abs(actual-expected) <= Math.max(1,Math.abs(expected))*1e-10;
  const play = data['stats_action_distribution.json'].find(row => row.action === 'play').count;
  const model = data['kmeans_model_metadata.json'][0];
  if (sum(users,'playCount') !== play || sum(data['stats_hourly_activity.json'],'playCount') !== play
      || data['stats_daily_active_users.json'].some(row => row.activeUsers > users.length)
      || data['stats_watch_duration_summary.json'].some(row => !close(row.mean * row.count,sum(users,'totalWatchDuration')))
      || data['stats_watch_duration_summary.json'].find(row => row.scope === 'all_events').count !== summary.clean_events) {
    throw new Error('Số liệu play/DAU/thời lượng không nhất quán.');
  }
  const means = {avgPlayCount:'playCount',avgCompleteCount:'completeCount',avgTotalWatchDuration:'totalWatchDuration',
    avgWatchDuration:'avgWatchDuration',avgDistinctMovies:'distinctMovies',avgDistinctGenres:'distinctGenres',
    avgSessionCount:'sessionCount',avgCompletionRate:'completionRate',avgActiveDays:'activeDays',avgEventCount:'eventCount'};
  for (const profile of data['kmeans_cluster_profiles.json']) {
    const members = users.filter(row => row.cluster === profile.cluster);
    if (Object.entries(means).some(([average,key]) => !close(profile[average],sum(members,key)/members.length))) {
      throw new Error('Trung bình hồ sơ cụm không khớp assignments.');
    }
  }
  if (handoff && (model.bestK !== handoff.best_k || model.silhouette !== handoff.silhouette
      || JSON.stringify(JSON.parse(model.featureColumnsJson)) !== JSON.stringify(handoff.feature_columns)
      || handoff.model.reload_assignments !== users.length || handoff.model.reload_mismatches !== 0
      || handoff.model.scaler_vectors_match !== true)) throw new Error('Mô hình không khớp handoff.');
  const dates = data['stats_daily_active_users.json'].map(row => row.date).sort();
  const metadata = { schemaVersion:1, status:status.status, runId, evidenceRoot, flumeRunId:context.flume_run_id,
    hdfsRunId:context.hdfs_run_id, generatedAt:summary.finished_at_utc, verifiedAt:status.finished_at_utc,
    timezone:summary.environment.calendar_timezone, firstDate:dates[0], lastDate:dates.at(-1),
    isSynthetic:handoff ? handoff.synthetic : true, staleAfterHours:24, sourceManifestSha256:sourceHash,
    ...(handoff ? { handoffSha256:hash(await readFile(path.join(run,'handoff.json'))), releasedAt:handoff.released_at_utc } : {}),
    files:Object.fromEntries(inputs.map(input => [input.name,input.proof])) };
  if (!Number.isFinite(Date.parse(metadata.verifiedAt)) || metadata.timezone !== 'Asia/Ho_Chi_Minh') throw new Error('Thời gian xác minh/múi giờ không hợp lệ.');
  return { inputs,metadata };
}

export async function sync(runId, { root = repository, outputRoot = dashboardRoot } = {}) {
  const selection = await json(path.join(outputRoot,'data-source.json'));
  runId ??= selection.runId;
  const evidenceRoot = selection.evidenceRoot ?? 'evidence/week3-tv2';
  const { inputs,metadata } = await verifyRun(root,runId,evidenceRoot);
  const parent = path.join(outputRoot,'public/data');
  await mkdir(parent,{ recursive:true });
  const destination = path.join(parent,runId);
  let exists = false;
  try { await mkdir(destination); }
  catch (error) { if (error.code !== 'EEXIST') throw error; exists = true; }
  if (exists) {
    for (const input of inputs) {
      try {
        if (hash(await readFile(path.join(destination,input.name))) !== input.proof.sha256) throw new Error('Snapshot frontend đã thay đổi; không ghi đè.');
      } catch (error) { throw new Error(`Snapshot frontend không đầy đủ hoặc đã thay đổi; không ghi đè: ${input.name}`,{ cause:error }); }
    }
  }
  for (const input of inputs) {
    try { await writeFile(path.join(destination,input.name),input.bytes,{ flag:'wx' }); }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
  }
  // Snapshot directory is immutable; publish its selector after every file exists.
  const sourcePath = path.join(parent,'source.json');
  const metadataText = JSON.stringify(metadata,null,2) + '\n';
  let previous;
  try { previous = await readFile(sourcePath,'utf8'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  // Tránh thay file đang được Vite/Windows đọc khi metadata không đổi.
  if (previous !== metadataText) {
    const temporary = path.join(parent,`source-${randomUUID()}.tmp`);
    await writeFile(temporary,metadataText,{ flag:'wx' });
    await rename(temporary,sourcePath);
  }
  const selectionText = JSON.stringify({ runId,evidenceRoot },null,2) + '\n';
  if (await readFile(path.join(outputRoot,'data-source.json'),'utf8') !== selectionText) {
    await writeFile(path.join(outputRoot,'data-source.json'),selectionText);
  }
  console.log(`Đã xác minh và đồng bộ ${inputs.length} JSON từ ${runId}.`);
}
