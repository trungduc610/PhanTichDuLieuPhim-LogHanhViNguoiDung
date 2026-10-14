export class MissingDataError extends Error {}

export function requireRows(rows, name) {
  if (!Array.isArray(rows)) throw new Error(`${name}: JSON phải là mảng.`);
  if (rows.length === 0) throw new MissingDataError(`${name}: dữ liệu trống.`);
  if (rows.some((row) => !row || typeof row !== 'object' || Array.isArray(row))) {
    throw new Error(`${name}: bản ghi không hợp lệ.`);
  }
}

export function requireCount(value, field) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new Error(`${field}: cần số nguyên không âm trong giới hạn an toàn.`);
  }
  return value;
}

export function calculateOverview(actions, assignments) {
  requireRows(actions, 'stats_action_distribution.json');
  requireRows(assignments, 'kmeans_assignments.json');
  const actionNames = new Set();
  const totalEvents = actions.reduce((total, row) => {
    if (typeof row.action !== 'string' || !row.action.trim() || actionNames.has(row.action)) {
      throw new Error('Tên action thiếu hoặc trùng lặp.');
    }
    actionNames.add(row.action);
    return requireCount(total + requireCount(row.count, 'count'), 'Tổng sự kiện');
  }, 0);

  const users = new Set();
  let totalSessions = 0;
  let playedSessions = 0;
  let userEvents = 0;
  for (const row of assignments) {
    if (typeof row.userId !== 'string' || !row.userId.trim() || users.has(row.userId)) {
      throw new Error('userId thiếu hoặc trùng lặp; không thể cộng chính xác số phiên.');
    }
    users.add(row.userId);
    const sessions = requireCount(row.sessionCount, 'sessionCount');
    const played = requireCount(row.playedSessionCount, 'playedSessionCount');
    if (played > sessions) throw new Error('Số phiên có play vượt số phiên được ghi nhận.');
    totalSessions = requireCount(totalSessions + sessions, 'Tổng phiên');
    playedSessions = requireCount(playedSessions + played, 'Tổng phiên có play');
    userEvents = requireCount(userEvents + requireCount(row.eventCount, 'eventCount'), 'Tổng sự kiện người dùng');
  }
  if (userEvents !== totalEvents) {
    throw new Error('Hai nguồn dữ liệu không khớp tổng số sự kiện. Hãy đồng bộ lại dữ liệu.');
  }
  return { totalEvents, distinctUsers: users.size, totalSessions, playedSessions };
}
