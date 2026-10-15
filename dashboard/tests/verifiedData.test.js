// Contract fixtures only: they do not claim that Spark/HDFS executed here.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { verifyRun, files } from '../scripts/verified-data.mjs';

const hash = content => createHash('sha256').update(content).digest('hex');
const fixtureSource = new URL('../../evidence/week2-tv2/tv2-4ed70c10cd84/dashboard/',import.meta.url);

async function fixture() {
  const root = await mkdtemp(path.join(os.tmpdir(),'verified-data-contract-'));
  const runId = 'tv2-012345abcdef';
  const run = path.join(root,'evidence/week2-tv2',runId);
  await mkdir(path.join(run,'dashboard'),{recursive:true});
  const put = (name,value) => writeFile(path.join(run,name),JSON.stringify(value));
  const source = {authority:'hdfs://namenode:9000',movies_uri:'hdfs://namenode:9000/raw/movies.csv',
    logs_uri:'hdfs://namenode:9000/raw/user_logs/run-abc/snapshot',files:[{hdfs_path:'/raw/movies.csv',bytes:10,sha256:'b'.repeat(64)}]};
  await put('source_manifest.json',source);
  const sourceHash = hash(await readFile(path.join(run,'source_manifest.json')));
  const context = {run_id:runId,flume_run_id:'run-abc',hdfs_run_id:'hdfs-abc',source_manifest_sha256:sourceHash,code_hashes:{}};
  for (let i=0;i<10;i++) {
    const name = `fixture-code-${i}.py`;
    await writeFile(path.join(root,name),'# fixture only\n');
    context.code_hashes[name] = hash(await readFile(path.join(root,name)));
  }
  await put('run_context.json',context);
  const summary = {status:'PASS',run_id:runId,local_fallback:false,model_reload_assignments_match:true,
    source_manifest_sha256:sourceHash,movies_uri:source.movies_uri,logs_uri:source.logs_uri,
    clean_events:1000000,user_count:1000,environment:{calendar_timezone:'Asia/Ho_Chi_Minh'},finished_at_utc:'2026-10-14T10:00:00Z'};
  await put('pipeline_summary.json',summary);
  const status = {status:'PASS',run_id:runId,finished_at_utc:'2026-10-14T10:01:00Z',checks:{pipeline_pass:true,raw_unchanged:true,protected_tv1_unchanged:true,no_local_fallback:true,fixtures_pass:true}};
  await put('run_status.json',status);
  const raw = {status:'PASS',source_manifest_sha256:sourceHash,files:source.files.map(row => ({...row,uri:source.authority+row.hdfs_path}))};
  await put('raw-before.json',raw);await put('raw-after.json',raw);
  const manifest = {status:'PASS',run_id:runId,artifacts:[{rows:1,read_back_rows:1}],dashboard_files:{}};
  for (const name of files) {
    const content = await readFile(new URL(name,fixtureSource));
    await writeFile(path.join(run,'dashboard',name),content);
    manifest.dashboard_files[name] = {bytes:content.length,sha256:hash(content)};
  }
  await put('output_manifest.json',manifest);
  return {root,run,runId,put,status,raw,manifest};
}

test('Sync từ chối FAIL, dữ liệu bị sửa, source thay đổi và raw không nhất quán', async () => {
  const f = await fixture();
  try {
    assert.equal((await verifyRun(f.root,f.runId)).inputs.length,11);
    await f.put('run_status.json',{...f.status,status:'FAIL'});
    await assert.rejects(verifyRun(f.root,f.runId),/PASS/);
    await f.put('run_status.json',f.status);
    await f.put('raw-after.json',{...f.raw,files:[{...f.raw.files[0],bytes:11}]});
    await assert.rejects(verifyRun(f.root,f.runId),/Raw đã thay đổi/);
    await f.put('raw-after.json',f.raw);
    await writeFile(path.join(f.root,'fixture-code-0.py'),'# changed');
    await assert.rejects(verifyRun(f.root,f.runId),/Source đã thay đổi/);
    await writeFile(path.join(f.root,'fixture-code-0.py'),'# fixture only\n');
    await writeFile(path.join(f.run,'dashboard',files[0]),'[]');
    await assert.rejects(verifyRun(f.root,f.runId),/Hash output/);
    await assert.rejects(verifyRun(f.root,'../history'),/Run ID/);
  } finally { await rm(f.root,{recursive:true,force:true}); }
});
