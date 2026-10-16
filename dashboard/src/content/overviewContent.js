// Từ vựng của Tổng quan. Không đổi mã action, trường số hay kết quả Spark.
export const actionLabels = {
  play: 'Phát phim', view: 'Xem thông tin phim', pause: 'Tạm dừng',
  stop: 'Dừng phát', complete: 'Hoàn thành xem phim',
};

export const definitions = {
  totalActions: {
    title: 'Tổng số hành động',
    meaning: 'Mỗi lần hệ thống ghi nhận một thao tác của người dùng được tính là một hành động.',
    calculation: 'Cộng số lần phát phim, xem thông tin phim, tạm dừng, dừng phát và hoàn thành xem phim trong kỳ.',
    caution: 'Một người có thể tạo nhiều hành động. Đây không phải số người dùng hoặc số phiên sử dụng.',
    technical: 'Event; tổng count trong stats_action_distribution.json. Spark nhóm theo action và đếm các bản ghi hợp lệ.',
  },
  users: {
    title: 'Số người dùng',
    meaning: 'Số người dùng mô phỏng xuất hiện trong dữ liệu của toàn kỳ.',
    calculation: 'Mỗi mã người dùng chỉ được tính một lần, dù có nhiều hành động hoặc nhiều ngày hoạt động.',
    caution: 'Không cộng số người dùng của từng ngày hoặc từng khung giờ để suy ra chỉ số này.',
    technical: 'Distinct users; đếm userId phân biệt trong kmeans_assignments.json. Service kiểm tra không có mã trùng.',
  },
  plays: {
    title: 'Lượt phát phim',
    meaning: 'Mỗi bản ghi hợp lệ có hành động phát phim được tính là một lượt phát phim.',
    calculation: 'Đếm từng bản ghi phát phim trong kỳ. Một người dùng có thể tạo nhiều bản ghi phát phim.',
    caution: 'Không phải số người xem, số phiên có phát phim hay số lần xem hết phim.',
    technical: 'action = "play"; count trong stats_action_distribution.json. Theo phim dùng playCount trong stats_top_movies_by_play.json.',
  },
  sessions: {
    title: 'Phiên sử dụng',
    meaning: 'Một chuỗi hành động được bộ log mô phỏng gắn chung mã phiên. Một phiên có thể chỉ xem thông tin phim.',
    calculation: 'Đếm cặp mã đợt log và mã phiên khác nhau trong từng người dùng, rồi cộng trên toàn bộ người dùng.',
    caution: 'Không suy phiên bằng khoảng nghỉ 30 phút. Một phiên có thể có nhiều lượt phát phim.',
    technical: 'Session; Spark countDistinct(struct(runId, sessionId)) theo userId, tạo sessionCount. Tổng quan cộng sessionCount từ kmeans_assignments.json.',
  },
  playedSessions: {
    title: 'Phiên có phát phim',
    meaning: 'Phiên sử dụng có ít nhất một hành động phát phim.',
    calculation: 'Mỗi phiên chỉ tính một lần, kể cả khi có nhiều bản ghi phát phim trong cùng phiên đó.',
    caution: 'Lượt phát phim đếm từng hành động phát; phiên có phát phim đếm từng phiên. Hai chỉ số có ý nghĩa khác nhau.',
    technical: 'playedSessionCount; countDistinct cặp (runId, sessionId) khi action = "play", theo userId. Tổng quan cộng số đếm đã xuất.',
  },
};

export function presentActions(rows) {
  return rows.map(row => ({ ...row, label: actionLabels[row.action] ?? row.label }));
}

export const hourRange = hour => `${String(hour).padStart(2,'0')}:00–${String(hour).padStart(2,'0')}:59`;

export const operationHelp = {
  hourly: 'Di chuột để đọc số liệu; bấm hoặc chạm vào cột để chọn giờ. Dùng Tab vào biểu đồ, ←/→ để đổi giờ, Home/End đến đầu/cuối và Esc để bỏ đánh dấu.',
  actions: 'Di chuột hoặc dùng Tab và các phím mũi tên để đọc từng hành động. Bấm, chạm, Enter hoặc phím cách để giữ lựa chọn; Esc bỏ đánh dấu tạm thời. Lựa chọn vẫn được giữ khi đổi Biểu đồ/Bảng.',
  movies: 'Di chuột hoặc dùng Tab để làm nổi bật từng phim. Chuyển sang Bảng để đối chiếu số liệu; nút CSV tải đúng năm phim đang hiển thị.',
};
