// Temporary Git fixtures test byte recovery, not a Spark/HDFS execution.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm, symlink } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createHash } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { repairCheckout } from '../scripts/repair-checkout.mjs';

const exec = promisify(execFile);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const runId = 'tv2-012345abcdef';
const prefix = `evidence/week3-tv2/${runId}`;
const names = {json:`${prefix}/run_status.json`,config:`${prefix}/source-snapshot/Dockerfile.tv2`,
  manifest:`${prefix}/delivery-manifest.json`};
const original = {json:Buffer.from('{"status":"PASS"}\n'),config:Buffer.from('FROM fixture\r\n# original\r\n')};
const cmd = (root,args) => exec('git',['-C',root,...args],{windowsHide:true});

async function fixture({badProof = false,badPath = false} = {}) {
  const root = await mkdtemp(path.join(os.tmpdir(),'sha-checkout-contract-'));
  await mkdir(path.join(root,'dashboard'),{recursive:true});
  await mkdir(path.join(root,prefix,'source-snapshot'),{recursive:true});
  await writeFile(path.join(root,'dashboard/data-source.json'),JSON.stringify({runId,evidenceRoot:'evidence/week3-tv2'}));
  await writeFile(path.join(root,'.gitignore'),'work/\n');
  await writeFile(path.join(root,'.gitattributes'),`${prefix}/** -text\n${names.config} text eol=crlf\n`);
  await writeFile(path.join(root,names.json),original.json);
  await writeFile(path.join(root,names.config),original.config);
  const files = Object.fromEntries(['json','config'].map(key => [names[key],
    {bytes:original[key].length,sha256:badProof && key === 'json' ? '0'.repeat(64) : hash(original[key])}]));
  if (badPath) files['../outside'] = {bytes:1,sha256:'0'.repeat(64)};
  await writeFile(path.join(root,names.manifest),JSON.stringify({files},null,2) + '\n');
  await cmd(root,['init','--quiet']);
  await cmd(root,['config','core.autocrlf','true']);
  await cmd(root,['add','--','.gitattributes','.gitignore','dashboard','evidence']);
  await cmd(root,['-c','user.name=Contract test','-c','user.email=contract@example.invalid','-c','commit.gpgsign=false','commit','--quiet','-m','fixture']);
  return root;
}

async function stale(root) {
  await writeFile(path.join(root,names.json),original.json.toString().replaceAll('\n','\r\n'));
  await writeFile(path.join(root,names.config),original.config.toString().replaceAll('\r\n','\n'));
}

test('Repair restores both LF and CRLF from Git, backs up exact old bytes and leaves index unchanged', async () => {
  const root = await fixture();
  try {
    await stale(root);
    const oldJson = await readFile(path.join(root,names.json));
    const oldConfig = await readFile(path.join(root,names.config));
    const beforeTree = (await cmd(root,['write-tree'])).stdout;
    const result = await repairCheckout({root});
    assert.equal(result.status,'RESTORED');
    assert.equal(result.files.length,2);
    assert.deepEqual(await readFile(path.join(root,names.json)),original.json);
    assert.deepEqual(await readFile(path.join(root,names.config)),original.config);
    assert.deepEqual(await readFile(path.join(root,result.backupDirectory,names.json)),oldJson);
    assert.deepEqual(await readFile(path.join(root,result.backupDirectory,names.config)),oldConfig);
    assert.equal((await cmd(root,['write-tree'])).stdout,beforeTree);
    assert.equal((await repairCheckout({root})).status,'UNCHANGED');
  } finally { await rm(root,{recursive:true,force:true}); }
});

test('Check mode reports stale files without modifying files or creating backups', async () => {
  const root = await fixture();
  try {
    await stale(root);
    const before = await readFile(path.join(root,names.json));
    const result = await repairCheckout({root,check:true});
    assert.equal(result.status,'NEEDS_REPAIR');
    assert.deepEqual(await readFile(path.join(root,names.json)),before);
    await assert.rejects(readFile(path.join(root,'work/sha-checkout-repair')),/ENOENT/);
  } finally { await rm(root,{recursive:true,force:true}); }
});

test('Substantive local edits abort the entire preflight before any replacement', async () => {
  const root = await fixture();
  try {
    await stale(root);
    const before = await readFile(path.join(root,names.json));
    await writeFile(path.join(root,names.config),'FROM edited\n');
    await assert.rejects(repairCheckout({root}),/nội dung thật/);
    assert.deepEqual(await readFile(path.join(root,names.json)),before);
    assert.equal(await readFile(path.join(root,names.config),'utf8'),'FROM edited\n');
    await assert.rejects(readFile(path.join(root,'work/sha-checkout-repair')),/ENOENT/);
  } finally { await rm(root,{recursive:true,force:true}); }
});

test('A Git candidate with the wrong expected SHA is refused; hashes are never regenerated', async () => {
  const root = await fixture({badProof:true});
  try {
    await stale(root);
    const before = await readFile(path.join(root,names.json));
    await assert.rejects(repairCheckout({root}),/SHA-256 gốc/);
    assert.deepEqual(await readFile(path.join(root,names.json)),before);
  } finally { await rm(root,{recursive:true,force:true}); }
});

test('Local manifest edits, missing files and path traversal are refused', async () => {
  const root = await fixture();
  const unsafe = await fixture({badPath:true});
  try {
    const manifestPath = path.join(root,names.manifest);
    const bytes = await readFile(manifestPath);
    await writeFile(manifestPath,'{"files":{}}\n');
    await assert.rejects(repairCheckout({root}),/nội dung thật/);
    await writeFile(manifestPath,bytes);
    await rm(path.join(root,names.config));
    await assert.rejects(repairCheckout({root}),/ENOENT/);
    await assert.rejects(repairCheckout({root:unsafe}),/không an toàn/);
  } finally {
    await rm(root,{recursive:true,force:true});
    await rm(unsafe,{recursive:true,force:true});
  }
});

test('Repair refuses a linked evidence directory instead of writing through it', async () => {
  const root = await fixture();
  const outside = await mkdtemp(path.join(os.tmpdir(),'sha-checkout-outside-'));
  try {
    await writeFile(path.join(outside,'Dockerfile.tv2'),'FROM external\n');
    await rm(path.join(root,prefix,'source-snapshot'),{recursive:true});
    await symlink(outside,path.join(root,prefix,'source-snapshot'),process.platform === 'win32' ? 'junction' : 'dir');
    await assert.rejects(repairCheckout({root}),/liên kết/);
    assert.equal(await readFile(path.join(outside,'Dockerfile.tv2'),'utf8'),'FROM external\n');
  } finally {
    await rm(root,{recursive:true,force:true});
    await rm(outside,{recursive:true,force:true});
  }
});
