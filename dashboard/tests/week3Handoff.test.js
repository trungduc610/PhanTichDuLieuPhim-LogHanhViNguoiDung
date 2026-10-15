// Các bản sao tạm chỉ kiểm thử hợp đồng; không sửa evidence bàn giao.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, copyFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { verifyRun, sync, files } from '../scripts/verified-data.mjs';

const repository = fileURLToPath(new URL('../../',import.meta.url));
const runId = 'tv2-aae83326c1ab';
const evidenceRoot = 'evidence/week3-tv2';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

async function fixture() {
  const root = await mkdtemp(path.join(os.tmpdir(),'dashboard-week3-'));
  const run = path.join(root,evidenceRoot,runId);
  const source = path.join(repository,evidenceRoot,runId);
  const handoff = JSON.parse(await readFile(path.join(source,'handoff.json'),'utf8'));
  const context = JSON.parse(await readFile(path.join(source,'run_context.json'),'utf8'));
  const names = ['handoff.json','run_context.json','source_manifest.json','raw-before.json','raw-after.json',
    'output_manifest.json',...Object.keys(handoff.validation_receipts),...files.map(name => `dashboard/${name}`)];
  for (const name of names) {
    await mkdir(path.dirname(path.join(run,name)),{recursive:true});
    await copyFile(path.join(source,name),path.join(run,name));
  }
  for (const name of Object.keys(context.code_hashes)) {
    await mkdir(path.dirname(path.join(run,'source-snapshot',name)),{recursive:true});
    await copyFile(path.join(source,'source-snapshot',name),path.join(run,'source-snapshot',name));
  }
  const outputRoot = path.join(root,'dashboard');
  await mkdir(outputRoot);
  const selection = JSON.stringify({runId:'tv2-56569b78b4e1',evidenceRoot});
  await writeFile(path.join(outputRoot,'data-source.json'),selection);
  return {root,run,handoff,outputRoot,selection};
}

test('Week 3: 11 JSON khớp hash, byte, schema, row count và metadata chính thức', async () => {
  const {inputs,metadata} = await verifyRun(repository,runId);
  assert.equal(inputs.length,11);
  assert.equal(metadata.runId,runId);
  assert.equal(metadata.evidenceRoot,evidenceRoot);
  const run = path.join(repository,evidenceRoot,runId);
  const status = JSON.parse(await readFile(path.join(run,'run_status.json'),'utf8'));
  const summary = JSON.parse(await readFile(path.join(run,'pipeline_summary.json'),'utf8'));
  assert.equal(metadata.verifiedAt,status.finished_at_utc);
  assert.equal(metadata.generatedAt,summary.finished_at_utc);
  for (const input of inputs) {
    assert.equal(input.bytes.length,input.proof.bytes);
    assert.equal(hash(input.bytes),input.proof.sha256);
    assert.equal(JSON.parse(input.bytes).length,input.proof.rows);
  }
});

test('Week 3: từ chối thiếu file, JSON hỏng, sai hash/schema/rows/path và biên nhận FAIL', async () => {
  const f = await fixture();
  const target = path.join(f.run,'dashboard',files[0]);
  const original = await readFile(target);
  const handoffPath = path.join(f.run,'handoff.json');
  const putHandoff = value => writeFile(handoffPath,JSON.stringify(value));
  try {
    await verifyRun(f.root,runId);
    const capturedCode = path.join(f.run,'source-snapshot','compose.tv2.yaml');
    const capturedBytes = await readFile(capturedCode);
    await writeFile(capturedCode,'changed');
    await assert.rejects(verifyRun(f.root,runId),/Source đã thay đổi/);
    await writeFile(capturedCode,capturedBytes);
    await rm(target);
    await assert.rejects(verifyRun(f.root,runId),/ENOENT/);
    await writeFile(target,'{broken');
    await assert.rejects(verifyRun(f.root,runId),/Hash output/);
    // Hash-consistent malformed JSON must also fail, never fall back.
    const malformed = structuredClone(f.handoff);
    const entry = malformed.dashboard_outputs.find(row => row.local_path?.endsWith('/'+files[0]) && row.format === 'json');
    entry.local_bytes = 7; entry.local_sha256 = hash('{broken');
    const manifestPath = path.join(f.run,'output_manifest.json');
    const manifestBytes = await readFile(manifestPath);
    const manifest = JSON.parse(manifestBytes);
    manifest.dashboard_files[files[0]] = {bytes:7,sha256:entry.local_sha256};
    await writeFile(manifestPath,JSON.stringify(manifest));
    await putHandoff(malformed);
    await assert.rejects(verifyRun(f.root,runId),SyntaxError);
    await writeFile(manifestPath,manifestBytes);
    await writeFile(target,original);
    for (const mutate of [
      row => { row.rows++; row.read_back_rows++; },
      row => { row.schema.fields[0].type = 'boolean'; },
      row => { row.local_path = '../outside.json'; },
      row => { row.local_sha256 = '0'.repeat(64); },
      row => { row.local_bytes++; },
    ]) {
      const changed = structuredClone(f.handoff);
      mutate(changed.dashboard_outputs.find(row => row.local_path?.endsWith('/'+files[0]) && row.format === 'json'));
      await putHandoff(changed);
      await assert.rejects(verifyRun(f.root,runId),/row count|schema|Hợp đồng|Hash output/);
    }
    const receiptPath = path.join(f.run,'run_status.json');
    const receipt = JSON.parse(await readFile(receiptPath,'utf8'));
    receipt.status = 'FAIL';
    const changed = structuredClone(f.handoff);
    const receiptBytes = JSON.stringify(receipt);
    changed.validation_receipts['run_status.json'].sha256 = hash(receiptBytes);
    await writeFile(receiptPath,receiptBytes);
    await putHandoff(changed);
    await assert.rejects(sync(runId,{root:f.root,outputRoot:f.outputRoot}),/PASS/);
    assert.equal(await readFile(path.join(f.outputRoot,'data-source.json'),'utf8'),f.selection);
    await assert.rejects(readFile(path.join(f.outputRoot,'public/data/source.json')),/ENOENT/);
  } finally { await rm(f.root,{recursive:true,force:true}); }
});

test('Week 3: chỉ công bố đủ snapshot, không ghi đè snapshot sai hash hoặc thiếu file', async () => {
  const f = await fixture();
  try {
    await sync(runId,{root:f.root,outputRoot:f.outputRoot});
    const selectorPath = path.join(f.outputRoot,'public/data/source.json');
    const selector = await readFile(selectorPath,'utf8');
    const destination = path.join(f.outputRoot,'public/data',runId);
    for (const name of files) assert.deepEqual(await readFile(path.join(destination,name)),await readFile(path.join(f.run,'dashboard',name)));
    await sync(runId,{root:f.root,outputRoot:f.outputRoot});
    const target = path.join(destination,files[0]);
    await writeFile(target,'[]');
    await assert.rejects(sync(runId,{root:f.root,outputRoot:f.outputRoot}),/không ghi đè/);
    assert.equal(await readFile(target,'utf8'),'[]');
    assert.equal(await readFile(selectorPath,'utf8'),selector);
    await rm(target);
    await assert.rejects(sync(runId,{root:f.root,outputRoot:f.outputRoot}),/không ghi đè/);
  } finally { await rm(f.root,{recursive:true,force:true}); }
});
