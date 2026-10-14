// Cùng tập dữ liệu cho bảng và CSV; không lấy thêm dòng từ nguồn khác.
export const overviewTables = {
  hourly: {
    filename: 'hoat-dong-theo-gio-toan-ky.csv',
    caption: '24 khung giờ UTC+7, cộng gộp toàn kỳ 01/09/2026–30/09/2026',
    columns: [{ label: 'Giờ UTC+7 (toàn kỳ)', key: 'label' }, { label: 'Tổng sự kiện', key: 'eventCount', format: 'number' }],
  },
  actions: {
    filename: 'phan-bo-hanh-vi.csv',
    caption: '5 hành động; tỷ lệ có mẫu số là tổng sự kiện trong kỳ',
    columns: [{ label: 'Hành động', key: 'label' }, { label: 'Mã hành động', key: 'action' }, { label: 'Số sự kiện', key: 'count', format: 'number' }, { label: 'Tỷ lệ tổng sự kiện (%)', key: 'percentage', format: 'percent' }],
  },
  movies: {
    filename: 'top-5-phim-theo-play.csv',
    caption: 'Đúng 5 phim trên biểu đồ; số sự kiện play bao gồm phát lặp lại',
    columns: [{ label: 'Hạng', key: 'rank', format: 'number' }, { label: 'Tên phim', key: 'title' }, { label: 'Sự kiện play', key: 'playCount', format: 'number' }],
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
