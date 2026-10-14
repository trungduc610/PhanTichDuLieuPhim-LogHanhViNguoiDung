import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const dashboardRoot = fileURLToPath(new URL('../', import.meta.url));
const source = path.resolve(dashboardRoot, '../evidence/week2-tv2/tv2-4ed70c10cd84/dashboard');
const destination = path.join(dashboardRoot, 'public/data');
const files = [
  'stats_action_distribution.json',
  'kmeans_assignments.json',
  'stats_hourly_activity.json',
  'stats_daily_active_users.json',
  'stats_top_movies_by_play.json',
  'stats_top_genres.json',
  'stats_watch_duration_summary.json',
  'stats_user_movie_time.json',
  'kmeans_model_metadata.json',
  'kmeans_k_search.json',
  'kmeans_cluster_profiles.json',
];

try {
  // Đọc và kiểm tra toàn bộ trước khi ghi; evidence luôn chỉ được đọc.
  const inputs = await Promise.all(files.map(async (name) => {
    const content = await readFile(path.join(source, name), 'utf8');
    const rows = JSON.parse(content);
    if (!Array.isArray(rows) || rows.length === 0) {
      throw new Error(`${name}: cần một mảng dữ liệu không rỗng.`);
    }
    return { name, content };
  }));
  await mkdir(destination, { recursive: true });
  for (const { name, content } of inputs) {
    await writeFile(path.join(destination, name), content, 'utf8');
  }
  console.log(`Đã đồng bộ ${files.length} JSON từ ${source} sang public/data.`);
} catch (error) {
  console.error(`Không thể đồng bộ dữ liệu: ${error.message}`);
  process.exitCode = 1;
}
