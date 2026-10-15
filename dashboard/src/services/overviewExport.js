// Cùng tập dữ liệu cho bảng và CSV; không lấy thêm dòng từ nguồn khác.
export const overviewTables = {
  hourly: {
    filename: 'hoat-dong-theo-gio-toan-ky.csv',
    caption: 'Các khung giờ Việt Nam (UTC+7), cộng gộp toàn kỳ phân tích',
    columns: [{ label: 'Giờ UTC+7 (toàn kỳ)', key: 'label' }, { label: 'Số hành động', key: 'eventCount', format: 'number' }],
  },
  actions: {
    filename: 'phan-bo-hanh-vi.csv',
    caption: 'Tỷ lệ tính trên tổng số hành động trong kỳ',
    columns: [{ label: 'Hành động', key: 'label' }, { label: 'Mã hành động', key: 'action' }, { label: 'Số lần ghi nhận', key: 'count', format: 'number' }, { label: 'Tỷ lệ tổng số hành động (%)', key: 'percentage', format: 'percent' }],
  },
  movies: {
    filename: 'top-5-phim-theo-play.csv',
    caption: 'Năm phim trên biểu đồ; lượt phát đếm các bản ghi hành động phát phim',
    columns: [{ label: 'Hạng', key: 'rank', format: 'number' }, { label: 'Tên phim', key: 'title' }, { label: 'Lượt phát phim', key: 'playCount', format: 'number' }],
  },
};

export function movieRankingRows(movies) {
  return movies.map((row, index) => ({ ...row, rank: index + 1 }));
}

function escapeCell(value) {
  let text = String(value ?? '');
  // Giữ tên phim an toàn khi bảng tính có thể diễn giải chuỗi thành công thức.
  if (typeof value === 'string' && (/^\s*[=+\-@]/u.test(text) || /^[\t\r\n]/u.test(text))) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

export function buildCsv(columns, rows) {
  return '\uFEFF' + [columns.map(column => escapeCell(column.label)).join(','),
    ...rows.map(row => columns.map(column => escapeCell(row[column.key])).join(','))].join('\r\n') + '\r\n';
}

export function downloadOverviewCsv(config, rows) {
  const blob = new Blob([buildCsv(config.columns, rows)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = config.filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
