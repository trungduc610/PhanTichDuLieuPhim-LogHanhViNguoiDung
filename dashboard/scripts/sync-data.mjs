import { sync } from './verified-data.mjs';

try {
  const index = process.argv.indexOf('--run');
  if (index >= 0 && !process.argv[index + 1]) throw new Error('Thiếu Run ID sau --run.');
  await sync(index >= 0 ? process.argv[index + 1] : undefined);
} catch (error) {
  console.error(`Không thể đồng bộ dữ liệu đã xác minh: ${error.message}`);
  process.exitCode = 1;
}
