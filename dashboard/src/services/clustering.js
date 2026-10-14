import { requireRows, requireCount } from './overviewMetrics.js';
import { number, percent } from './formatNumbers.js';

export const featureLabels = {
  playCount: 'Sự kiện play', completeCount: 'Sự kiện complete',
  totalWatchDuration: 'Tổng thời lượng ghi nhận (giây)',
  avgWatchDuration: 'Trung bình đoạn xem dương (giây)',
  distinctMovies: 'Phim khác nhau', distinctGenres: 'Thể loại khác nhau',
  sessionCount: 'Phiên được ghi nhận', completionRate: 'Tỷ lệ hoàn thành phiên',
  activeDays: 'Ngày hoạt động', eventCount: 'Tổng sự kiện',
};

export const profileMetrics = [
  { key: 'avgPlayCount', label: 'Sự kiện play trung bình', unit: 'sự kiện/người dùng' },
  { key: 'avgDistinctMovies', label: 'Phim khác nhau trung bình', unit: 'phim/người dùng' },
  { key: 'avgSessionCount', label: 'Số phiên trung bình', unit: 'phiên/người dùng' },
  { key: 'avgCompletionRate', label: 'Tỷ lệ hoàn thành phiên trung bình', unit: '%', rate: true },
  { key: 'avgTotalWatchDuration', label: 'Tổng thời lượng trung bình mỗi người dùng', unit: 'giây/người dùng' },
  { key: 'avgWatchDuration', label: 'Trung bình thời lượng đoạn xem theo người dùng', unit: 'giây' },
];

export const scoreNumber = (value) => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 6 }).format(value);
export const formatProfile = (key, value) => key === 'avgCompletionRate' ? percent(value * 100) : number(value);
export const formatCompletion = (row) => row.completionRateDefined ? percent(row.completionRate * 100) : 'Chưa xác định';

function finite(value, name, min = 0, max = Infinity) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw new Error(`${name}: giá trị thiếu hoặc ngoài phạm vi.`);
  }
}

export function prepareClustering(metadataRows, searchRows, profileRows, assignmentRows) {
  for (const [rows, name] of [[metadataRows, 'metadata'], [searchRows, 'K search'], [profileRows, 'hồ sơ cụm'], [assignmentRows, 'người dùng']]) {
    requireRows(rows, name);
  }
  if (metadataRows.length !== 1) throw new Error('Cần đúng một bản ghi metadata.');
  const metadata = { ...metadataRows[0] };
  requireCount(metadata.users, 'Số người dùng mô hình');
  requireCount(metadata.bestK, 'K được chọn');
  finite(metadata.silhouette, 'Silhouette mô hình', -1, 1);
  let features;
  try { features = JSON.parse(metadata.featureColumnsJson); }
  catch { throw new Error('featureColumnsJson không phải chuỗi JSON hợp lệ.'); }
  if (!Array.isArray(features) || features.length === 0 || features.some(name => typeof name !== 'string' || !name.trim())
      || new Set(features).size !== features.length) throw new Error('Danh sách đặc trưng đầu vào không hợp lệ.');

  const search = searchRows.map(row => ({ ...row, cluster_sizes: [...(Array.isArray(row.cluster_sizes) ? row.cluster_sizes : [])] })).sort((a, b) => a.k - b.k);
  if (search.length !== 5 || search.some((row, index) => row.k !== index + 2)) throw new Error('K search phải có đủ K từ 2 đến 6.');
  for (const row of search) {
    finite(row.silhouette, `Silhouette K=${row.k}`, -1, 1);
    if (row.users !== metadata.users || row.cluster_sizes.length !== row.k) throw new Error('K search không khớp số người dùng/số cụm.');
    row.cluster_sizes.forEach(size => requireCount(size, 'Số người dùng trong cụm thử nghiệm'));
    if (row.cluster_sizes.reduce((sum, size) => sum + size, 0) !== metadata.users) throw new Error('Tổng kích thước cụm thử nghiệm không khớp metadata.');
  }
  const selected = search.find(row => row.k === metadata.bestK);
  if (!selected || Math.abs(selected.silhouette - metadata.silhouette) > 1e-12) throw new Error('K hoặc silhouette được chọn không khớp metadata.');

  const profiles = profileRows.map(row => ({ ...row })).sort((a, b) => a.cluster - b.cluster);
  if (profiles.length !== metadata.bestK) throw new Error('Số hồ sơ cụm không khớp bestK.');
  for (const [index, row] of profiles.entries()) {
    if (row.cluster !== index || row.label !== `Cluster ${row.cluster}`) throw new Error('Mã hoặc nhãn cụm không khớp kết quả gốc.');
    requireCount(row.userCount, 'Số người dùng cụm');
    if (row.userCount !== selected.cluster_sizes[row.cluster]) throw new Error('Hồ sơ cụm không khớp kích thước cụm K được chọn.');
    for (const metric of profileMetrics) finite(row[metric.key], metric.label, 0, metric.rate ? 1 : Infinity);
  }
  if (profiles.reduce((sum, row) => sum + row.userCount, 0) !== metadata.users) throw new Error('Tổng người dùng hồ sơ cụm không khớp metadata.');

  const ids = new Set();
  const counts = new Map(profiles.map(row => [row.cluster, 0]));
  const assignments = assignmentRows.map(row => {
    if (typeof row.userId !== 'string' || !row.userId.trim() || ids.has(row.userId)) throw new Error('userId thiếu hoặc trùng.');
    ids.add(row.userId);
    if (!counts.has(row.cluster)) throw new Error('Người dùng có mã cụm không hợp lệ.');
    counts.set(row.cluster, counts.get(row.cluster) + 1);
    for (const key of ['playCount', 'completeCount', 'distinctMovies', 'distinctGenres', 'sessionCount', 'playedSessionCount', 'completedSessionCount']) requireCount(row[key], key);
    finite(row.totalWatchDuration, 'Tổng thời lượng người dùng');
    finite(row.avgWatchDuration, 'Trung bình đoạn xem người dùng');
    finite(row.completionRate, 'Tỷ lệ hoàn thành', 0, 1);
    if (typeof row.completionRateDefined !== 'boolean' || row.completionRateDefined !== (row.playedSessionCount > 0)
        || row.playedSessionCount > row.sessionCount || row.completedSessionCount > row.sessionCount) throw new Error('Phạm vi phiên hoặc trạng thái tỷ lệ hoàn thành không hợp lệ.');
    const expectedRate = row.playedSessionCount > 0 ? row.completedSessionCount / row.playedSessionCount : 0;
    if (Math.abs(row.completionRate - expectedRate) > 1e-12) throw new Error('Tỷ lệ hoàn thành người dùng không khớp số phiên.');
    for (const key of features) finite(row[key], `Đặc trưng ${key}`);
    return { ...row };
  }).sort((a, b) => a.userId.localeCompare(b.userId));
  if (assignments.length !== metadata.users || profiles.some(row => counts.get(row.cluster) !== row.userCount)) {
    throw new Error('Assignments, hồ sơ cụm và metadata không khớp số người dùng.');
  }
  return { metadata, features, search, profiles, assignments };
}

export function findUsers(assignments, { query = '', cluster = 'all', page = 1, pageSize = 20 } = {}) {
  if (!Number.isInteger(pageSize) || pageSize < 1 || !Number.isInteger(page) || page < 1) throw new Error('Phân trang không hợp lệ.');
  const needle = query.trim().toLowerCase();
  const filtered = assignments.filter(row => row.userId.toLowerCase().includes(needle) && (cluster === 'all' || String(row.cluster) === String(cluster)));
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  return { rows: filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize), total: filtered.length, totalPages, page: currentPage };
}
