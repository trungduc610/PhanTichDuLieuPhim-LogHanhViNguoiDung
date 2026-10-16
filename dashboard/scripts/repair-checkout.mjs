// Restore committed, hash-attested bytes. This does not relax verifyRun.
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { readFile, writeFile, mkdir, lstat, realpath, rename, unlink } from 'node:fs/promises';
import { createHash, randomUUID } from 'node:crypto';
import path from 'node:path';

const exec = promisify(execFile);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const sameText = (a,b) => a.toString('latin1').replaceAll('\r\n','\n')
  === b.toString('latin1').replaceAll('\r\n','\n');

function relativeName(name) {
  if (typeof name !== 'string' || !name || /[\\\r\n\0:]/.test(name)
      || path.posix.isAbsolute(name) || path.posix.normalize(name) !== name
      || name.split('/').some(part => part === '..' || part === '.git')) {
    throw new Error('Đường dẫn manifest không an toàn.');
  }
  return name;
}

async function plainFile(root,name) {
  const target = path.join(root,relativeName(name));
  // Reject symlink/junction parents and files; never write through them.
  if (await realpath(path.dirname(target)) !== path.dirname(target)) {
    throw new Error(`Từ chối đường dẫn liên kết: ${name}`);
  }
  const stat = await lstat(target);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(`Cần file thường: ${name}`);
  return target;
}

async function makeDirectories(root,name) {
  let current = root;
  for (const part of relativeName(name).split('/')) {
    current = path.join(current,part);
    try { await mkdir(current); }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
    const stat = await lstat(current);
    if (!stat.isDirectory() || stat.isSymbolicLink() || await realpath(current) !== current) {
      throw new Error('Từ chối thư mục backup liên kết.');
    }
  }
  return current;
}

async function git(root,args,input) {
  const pending = exec('git',['--no-optional-locks','-C',root,...args],
    {encoding:'buffer',maxBuffer:64*1024*1024,windowsHide:true});
  pending.child.stdin.end(input);
  return (await pending).stdout;
}

async function gitBlobs(root,revision,names) {
  const output = await git(root,['cat-file','--batch'],names.map(name => `${revision}:${name}\n`).join(''));
  let cursor = 0;
  const result = new Map();
  for (const name of names) {
    const end = output.indexOf(10,cursor);
    const header = output.subarray(cursor,end).toString('utf8');
    const match = /^[a-f0-9]+ blob (\d+)$/.exec(header);
    if (!match) throw new Error(`Thiếu bản Git được chứng thực: ${name}`);
    const length = Number(match[1]);
    cursor = end + 1;
    const bytes = output.subarray(cursor,cursor + length);
    if (bytes.length !== length || output[cursor + length] !== 10) throw new Error('Git blob không đầy đủ.');
    result.set(name,bytes);
    cursor += length + 1;
  }
  return result;
}

export async function repairCheckout({root,check = false}) {
  root = await realpath(path.resolve(root));
  const top = path.resolve((await git(root,['rev-parse','--show-toplevel'])).toString('utf8').trim());
  if (top !== root) throw new Error('Cần repository root chính xác.');
  const selectionPath = await plainFile(root,'dashboard/data-source.json');
  const selection = JSON.parse(await readFile(selectionPath,'utf8'));
  if (!/^tv2-[a-f0-9]{12}$/.test(selection.runId) || selection.evidenceRoot !== 'evidence/week3-tv2') {
    throw new Error('repair:data chỉ hỗ trợ run bàn giao Week 3 được chọn rõ.');
  }
  const prefix = `${selection.evidenceRoot}/${selection.runId}`;
  const manifestName = `${prefix}/delivery-manifest.json`;
  const revision = (await git(root,['rev-parse','HEAD'])).toString('utf8').trim();
  const controls = await gitBlobs(root,revision,[manifestName]);
  const manifestBytes = controls.get(manifestName);
  const manifest = JSON.parse(manifestBytes.toString('utf8'));
  if (!manifest.files || Array.isArray(manifest.files) || !Object.keys(manifest.files).length) {
    throw new Error('Thiếu file map trong manifest Git.');
  }
  const expected = new Map();
  for (const [name,proof] of Object.entries(manifest.files)) {
    relativeName(name);
    if (!name.startsWith(prefix + '/') && !/^docs\/week3_tv2_[a-zA-Z0-9_-]+\.md$/.test(name)) continue;
    if (!/^[a-f0-9]{64}$/.test(proof.sha256) || !Number.isSafeInteger(proof.bytes) || proof.bytes < 0) {
      throw new Error(`Hash/byte manifest không hợp lệ: ${name}`);
    }
    expected.set(name,proof);
  }
  if (!expected.size || expected.has(manifestName)) throw new Error('Scope manifest không hợp lệ.');
  // The manifest itself comes from a pinned Git revision, never local edits.
  expected.set(manifestName,{sha256:hash(manifestBytes),bytes:manifestBytes.length});
  const blobs = await gitBlobs(root,revision,[...expected.keys()]);
  const plan = [];
  for (const [name,proof] of expected) {
    const target = await plainFile(root,name);
    const before = await readFile(target);
    if (before.length === proof.bytes && hash(before) === proof.sha256) continue;
    let bytes = blobs.get(name);
    let authority = 'Git blob';
    if (bytes.length !== proof.bytes || hash(bytes) !== proof.sha256) {
      bytes = await git(root,['cat-file','--filters',`${revision}:${name}`]);
      authority = 'Git checkout filters';
    }
    if (bytes.length !== proof.bytes || hash(bytes) !== proof.sha256) {
      throw new Error(`Git không khôi phục được SHA-256 gốc: ${name}`);
    }
    if (!sameText(before,bytes)) throw new Error(`Có sửa đổi nội dung thật; không ghi đè: ${name}`);
    plan.push({name,target,before,bytes,authority,proof});
  }
  const result = {status:check && plan.length ? 'NEEDS_REPAIR' : 'UNCHANGED',
    checkedAt:new Date().toISOString(),revision,runId:selection.runId,evidenceRoot:selection.evidenceRoot,
    checkedFiles:expected.size,files:plan.map(item => ({path:item.name,beforeSha256:hash(item.before),
      sha256:item.proof.sha256,bytes:item.proof.bytes,authority:item.authority}))};
  if (check || !plan.length) return result;

  const backup = `work/sha-checkout-repair/${randomUUID()}`;
  await makeDirectories(root,backup);
  result.backupDirectory = backup;
  // Finish every backup BEFORE replacing any original file.
  for (const item of plan) {
    await makeDirectories(root,`${backup}/${path.posix.dirname(item.name)}`);
    await writeFile(path.join(root,backup,item.name),item.before,{flag:'wx'});
  }
  const journal = path.join(root,backup,'repair.json');
  result.status = 'BACKED_UP';
  await writeFile(journal,JSON.stringify(result,null,2) + '\n',{flag:'wx'});
  try {
    for (const item of plan) {
      const temporary = item.target + `.sha-repair-${randomUUID()}.tmp`;
      try {
        await writeFile(temporary,item.bytes,{flag:'wx'});
        await plainFile(root,item.name);
        if (!(await readFile(item.target)).equals(item.before)) throw new Error(`File thay đổi khi đang sửa: ${item.name}`);
        await rename(temporary,item.target);
      } catch (error) {
        await unlink(temporary).catch(() => {}); // Only the temporary file we created.
        throw error;
      }
      if (hash(await readFile(item.target)) !== item.proof.sha256) throw new Error(`Read-back SHA không khớp: ${item.name}`);
    }
    result.status = 'RESTORED';
  } catch (error) {
    result.status = 'FAILED';
    result.error = error.message;
    throw error;
  } finally {
    await writeFile(journal,JSON.stringify(result,null,2) + '\n');
  }
  return result;
}
