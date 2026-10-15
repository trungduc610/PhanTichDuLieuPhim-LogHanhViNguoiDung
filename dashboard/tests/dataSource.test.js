import test from 'node:test';
import assert from 'node:assert/strict';
import { validateSource, isStale, loadSource } from '../src/services/dataSource.js';

const metadata = () => ({ schemaVersion:1,status:'PASS',runId:'tv2-012345abcdef',
  verifiedAt:'2026-10-14T10:00:00Z',generatedAt:'2026-10-14T09:00:00Z',timezone:'Asia/Ho_Chi_Minh',
  isSynthetic:true,firstDate:'2026-09-01',lastDate:'2026-09-30',staleAfterHours:24,
  files:Object.fromEntries(Array.from({length:11},(_,i) => [`file${i}`,{bytes:2,sha256:'a'.repeat(64)}])) });

test('Metadata sai, FAIL, thiếu hash hoặc run ID traversal không được dùng', () => {
  assert.equal(validateSource(metadata()).status,'PASS');
  for (const change of [{status:'FAIL'},{runId:'../history'},{timezone:'UTC'},
    {files:{}},{verifiedAt:'invalid'},{isSynthetic:'true'}]) assert.throws(() => validateSource({...metadata(),...change}));
});
test('Cảnh báo cũ theo thời điểm xác minh, không theo tháng dữ liệu mô phỏng', () => {
  assert.equal(isStale(metadata(),Date.parse('2026-10-14T20:00:00Z')),false);
  assert.equal(isStale(metadata(),Date.parse('2026-10-16T10:00:00Z')),true);
});
test('Thiếu nguồn hoặc JSON hỏng không được che bằng snapshot mặc định', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response('',{status:404});
    await assert.rejects(loadSource(),/Thiếu nguồn/);
    globalThis.fetch = async () => new Response('{broken',{status:200});
    await assert.rejects(loadSource(),/JSON không hợp lệ/);
  } finally { globalThis.fetch = original; }
});
