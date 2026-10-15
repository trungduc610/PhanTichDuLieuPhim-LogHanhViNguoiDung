import { calculateOverview, MissingDataError } from './overviewMetrics.js';
import { prepareAnalysis } from './overviewAnalysis.js';
import { prepareGenres } from './genreAnalysis.js';
import { prepareWatchDuration } from './watchDuration.js';
import { prepareCombinedAnalysis } from './combinedAnalysis.js';
import { prepareClustering } from './clustering.js';
import { prepareDailyActivity } from './dailyActivity.js';
import { validateSource } from './dataSource.js';

let directory = 'data/';
export function selectDataSource(source) {
  validateSource(source);
  directory = `data/${source.runId}/`;
}

async function readJson(name, signal) {
  const response = await fetch(`${import.meta.env?.BASE_URL ?? '/'}${directory}${name}`, { signal, cache: 'no-store' });
  if (response.status === 404) throw new MissingDataError(`Thiếu ${name}. Hãy chạy npm.cmd run sync:data.`);
  if (!response.ok) throw new Error(`Không đọc được ${name} (HTTP ${response.status}).`);
  const content = await response.text();
  // Vite có thể trả index.html khi một tệp tĩnh không tồn tại.
  if (content.trimStart().startsWith('<')) {
    throw new MissingDataError(`Không tìm thấy JSON ${name}. Hãy đồng bộ dữ liệu.`);
  }
  try {
    return JSON.parse(content);
  } catch {
    throw new Error(`${name}: nội dung JSON không hợp lệ.`);
  }
}

export async function loadOverview(signal) {
  const [actions, assignments, hourly, movies] = await Promise.all([
    readJson('stats_action_distribution.json', signal),
    readJson('kmeans_assignments.json', signal),
    readJson('stats_hourly_activity.json', signal),
    readJson('stats_top_movies_by_play.json', signal),
  ]);
  const metrics = calculateOverview(actions, assignments);
  return { ...metrics, analysis: prepareAnalysis(actions, hourly, movies, metrics.totalEvents) };
}

export async function loadGenres(signal) {
  return prepareGenres(await readJson('stats_top_genres.json', signal));
}

export async function loadDailyActivity(signal) {
  return prepareDailyActivity(await readJson('stats_daily_active_users.json', signal));
}

export async function loadWatchDuration(signal) {
  return prepareWatchDuration(await readJson('stats_watch_duration_summary.json', signal));
}

export async function loadCombinedAnalysis(signal) {
  return prepareCombinedAnalysis(await readJson('stats_user_movie_time.json', signal));
}

export async function loadClustering(signal) {
  const [metadata, search, profiles, assignments] = await Promise.all([
    readJson('kmeans_model_metadata.json', signal),
    readJson('kmeans_k_search.json', signal),
    readJson('kmeans_cluster_profiles.json', signal),
    readJson('kmeans_assignments.json', signal),
  ]);
  return prepareClustering(metadata, search, profiles, assignments);
}
