import { MissingDataError } from './overviewMetrics.js';

export function validateSource(value) {
  if (Array.isArray(value) && !value.length) throw new MissingDataError('Thiếu nguồn dữ liệu đã xác minh.');
  if (!value || value.schemaVersion !== 1 || value.status !== 'PASS'
      || !/^tv2-[a-f0-9]{12}$/.test(value.runId)
      || !Number.isFinite(Date.parse(value.verifiedAt)) || !Number.isFinite(Date.parse(value.generatedAt))
      || value.timezone !== 'Asia/Ho_Chi_Minh' || typeof value.isSynthetic !== 'boolean'
      || !/^\d{4}-\d{2}-\d{2}$/.test(value.firstDate) || !/^\d{4}-\d{2}-\d{2}$/.test(value.lastDate)
      || !Number.isFinite(value.staleAfterHours) || value.staleAfterHours <= 0
      || !value.files || Object.keys(value.files).length !== 11
      || Object.values(value.files).some(row => !/^[a-f0-9]{64}$/.test(row.sha256) || !Number.isSafeInteger(row.bytes) || row.bytes <= 0)) {
    throw new Error('Metadata nguồn chưa được xác minh hoặc không hợp lệ.');
  }
  return value;
}

export async function loadSource(signal) {
  const response = await fetch(`${import.meta.env?.BASE_URL ?? '/'}data/source.json`, { signal, cache:'no-store' });
  if (response.status === 404) throw new MissingDataError('Thiếu nguồn đã xác minh. Hãy đồng bộ một run PASS.');
  if (!response.ok) throw new Error(`Không đọc được nguồn dữ liệu (HTTP ${response.status}).`);
  const text = await response.text();
  if (text.trimStart().startsWith('<')) throw new MissingDataError('Thiếu metadata nguồn dữ liệu.');
  let value;
  try { value = JSON.parse(text); }
  catch { throw new Error('Metadata nguồn: JSON không hợp lệ.'); }
  return validateSource(value);
}

export const isStale = (source, now = Date.now()) => now - Date.parse(source.verifiedAt) > source.staleAfterHours * 3600000;
export const displaySourceDate = date => date.split('-').reverse().join('/');
