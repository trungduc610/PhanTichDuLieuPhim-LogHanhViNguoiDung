import test from 'node:test';
import assert from 'node:assert/strict';
import { loadOverview, loadGenres, loadWatchDuration, loadCombinedAnalysis, loadClustering, loadDailyActivity } from '../src/services/dashboardData.js';
import { MissingDataError } from '../src/services/overviewMetrics.js';

test('Mọi loader báo lỗi HTTP, thiếu tệp, HTML thay JSON, JSON hỏng và dữ liệu rỗng', async () => {
  const original = globalThis.fetch;
  const loaders = [loadOverview, loadGenres, loadWatchDuration, loadCombinedAnalysis, loadClustering, loadDailyActivity];
  try {
    for (const loader of loaders) {
      for (const [status,body,expected] of [[404,'',MissingDataError], [500,'',/HTTP 500/],
        [200,'<!doctype html>',MissingDataError], [200,'{broken',/JSON không hợp lệ/], [200,'[]',MissingDataError]]) {
        globalThis.fetch = async () => new Response(body,{status});
        await assert.rejects(loader(),expected,loader.name);
      }
    }
  } finally { globalThis.fetch = original; }
});
