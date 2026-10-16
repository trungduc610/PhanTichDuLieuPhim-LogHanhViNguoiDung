import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { repairCheckout } from './repair-checkout.mjs';
import { verifyRun } from './verified-data.mjs';

try {
  if (process.argv.slice(2).some(arg => arg !== '--check')) throw new Error('Chỉ hỗ trợ tùy chọn --check.');
  const check = process.argv.includes('--check');
  const root = fileURLToPath(new URL('../../',import.meta.url));
  const result = await repairCheckout({root,check});
  if (result.status === 'NEEDS_REPAIR') {
    console.log(`Có ${result.files.length} file chỉ lệch LF/CRLF. Chạy npm run repair:data để sao lưu và khôi phục.`);
    process.exitCode = 2;
  } else {
    await verifyRun(path.resolve(root),result.runId,result.evidenceRoot);
    console.log(`SHA và handoff PASS: ${result.runId}. Khôi phục ${result.files.length} file.`);
    if (result.backupDirectory) console.log(`Backup: ${result.backupDirectory}`);
    console.log('Tiếp theo: npm run sync:data hoặc npm run dev.');
  }
} catch (error) {
  console.error(`Không thể khôi phục checkout an toàn: ${error.message}`);
  process.exitCode = 1;
}
