import { lazy, Suspense, useRef, useState } from 'react';
import { DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import AnalysisExplanation, { AnalysisRelatedLinks } from '../components/AnalysisExplanation.jsx';
import AnalysisResultsTable from '../components/AnalysisResultsTable.jsx';
import RankingChart from '../components/RankingChart.jsx';
import OverviewHourlyChart from '../components/OverviewHourlyChart.jsx';
import DailyActivitySummary from '../components/DailyActivitySummary.jsx';
import { actionLabels, definitions, presentActions, hourRange, operationHelp } from '../content/overviewContent.js';
import { number, percent } from '../services/formatNumbers.js';
const ActionDonut = lazy(() => import('../components/OverviewActionDonut.jsx'));

const sections = {
  movies: {
    title: 'Phân tích phim', description: 'Những phim được phát nhiều nhất trong kỳ phân tích.', chartTitle: 'Xếp hạng theo lượt phát phim', icon: 'film',
    note: 'Lượt phát có thể lặp lại ở cùng một người dùng hoặc phiên.',
    help: 'Thanh dài nhất là phim dẫn đầu trong danh sách đã xuất. Các thanh còn lại so với phim đó. Lượt phát đếm từng bản ghi phát phim, không phải số người xem duy nhất, số phiên hay lượt xem hết phim.',
    technical: 'Nguồn: stats_top_movies_by_play.json. Spark lọc action = "play", nhóm movieId và title, đếm playCount; sắp xếp playCount giảm dần, movieId tăng dần khi bằng nhau. Trang giữ tối đa 20 phim do service hiện có chọn. Nguồn này không có số người xem duy nhất theo phim; không suy ra chỉ số đó từ playCount.',
    instructions: 'Di chuột hoặc dùng Tab để đọc và làm nổi bật từng phim. Cuộn trong khung để xem hết xếp hạng. Bảng bên dưới hỗ trợ tìm tên phim, chọn số dòng và chuyển trang; tìm kiếm giữ hạng gốc. CSV tải tất cả dòng khớp tìm kiếm với giá trị chưa làm tròn.',
    links: [['/the-loai','So sánh thể loại'],['/hanh-vi','Phân biệt các hành động']],
  },
  actions: {
    title: 'Hành vi người dùng', description: 'So sánh số lần ghi nhận năm hành động trong toàn kỳ.', chartTitle: 'Cơ cấu hành động được ghi nhận', icon: 'activity',
    note: 'Tỷ lệ tính trên tổng số hành động, không phải số người dùng.',
    help: 'Mỗi hành động tương ứng một bản ghi hợp lệ. Một người dùng hoặc phiên có thể tạo nhiều hành động. Tỷ lệ cho biết mỗi loại chiếm bao nhiêu trong tổng số hành động; không phải tỷ lệ người dùng, số phiên hay tỷ lệ chuyển đổi giữa các bước.',
    technical: 'Nguồn: stats_action_distribution.json; count là số bản ghi theo action, percentage = count / tổng count × 100. Số người dùng đếm userId phân biệt; phiên sử dụng đếm cặp (runId, sessionId) trong từng userId, không suy từ khoảng nghỉ 30 phút. Bảng này không chứa số người dùng hoặc số phiên riêng cho mỗi hành động.',
    instructions: 'Di chuột hoặc dùng Tab và các phím mũi tên để đọc từng hành động. Bấm, chạm, Enter hoặc phím cách để giữ lựa chọn; Esc bỏ đánh dấu tạm thời. Bảng bên cạnh giữ đủ năm hành động, độc lập với lựa chọn trên biểu đồ. CSV giữ mã gốc và tỷ lệ chưa làm tròn.',
    links: [['/phim','Xếp hạng lượt phát phim'],['/thoi-gian','Xem hoạt động theo thời gian']],
  },
  hourly: {
    title: 'Hoạt động theo thời gian', description: 'Đọc nhịp hoạt động theo giờ và số người dùng hoạt động theo ngày.', chartTitle: 'Số hành động theo giờ', icon: 'clock',
    note: 'Cùng khung giờ Việt Nam (UTC+7), cộng gộp mọi ngày trong kỳ.',
    help: 'Mỗi cột đếm các hành động trong cùng một khung giờ qua tất cả ngày của kỳ phân tích. Đây không phải số người dùng, cũng không phải hoạt động của một ngày cụ thể. Cột đậm là giờ có nhiều hành động nhất; cột có viền là giờ đang chọn.',
    technical: 'Nguồn: stats_hourly_activity.json. Spark nhóm theo hour theo Asia/Ho_Chi_Minh: eventCount đếm mọi hành động, playCount chỉ đếm play, distinctUsers đếm userId phân biệt trong từng giờ. Không cộng distinctUsers giữa các giờ để suy ra số người dùng toàn kỳ. Frontend không đổi múi giờ thêm lần nữa.',
    instructions: operationHelp.hourly + ' Bảng phía dưới giữ đủ số hành động, lượt phát và người dùng duy nhất trong từng giờ; CSV giữ toàn bộ khung giờ.',
    links: [['/hanh-vi','So sánh các hành động'],['/ket-hop','Xem phim theo khung giờ']],
  },
};

export default function AnalysisPage({ kind }) {
  const state = useDashboardData();
  const [selectedAction, setSelectedAction] = useState(null);
  const explanations = useRef(null);
  const section = sections[kind];
  const analysis = state.metrics?.analysis;
  const data = kind === 'actions' && analysis ? presentActions(analysis.actions) : analysis?.[kind];
  return <div className={'analysis-page overview-page detail-ux ' + kind + '-page'}>
    <AnalysisPageHeader title={section.title} description={section.description} detailed />
    <DataState />
    {state.status === 'ready' && <>
      {kind === 'hourly' && <p className="analysis-context">Khung giờ có nhiều hành động nhất: <strong>{analysis.peakHours.map(row=>hourRange(row.hour)).join(' · ')}</strong> — {number(analysis.peakHours[0].eventCount)} hành động{analysis.peakHours.length > 1 ? ' ở mỗi khung giờ' : ''}, cộng gộp toàn kỳ.</p>}
      {kind === 'actions' && <p className="analysis-context">Hành động được ghi nhận nhiều nhất: <strong>{data[0].label}</strong> — {number(data[0].count)} lần, chiếm {percent(data[0].percentage)} tổng số hành động trong kỳ.</p>}
      <div className="analysis-grid">
        <ChartPanel title={section.chartTitle} note={section.note} icon={section.icon} className={'analysis-primary ' + (kind === 'hourly' ? 'overview-hourly-panel' : '')}>
          {kind === 'movies' ? <RankingChart data={data} plainLanguage />
            : kind === 'actions' ? <Suspense fallback={<p role="status" className="donut-loading">Đang tải biểu đồ hành vi…</p>}>
              <ActionDonut data={data} selectedAction={selectedAction ?? data[0].action} onSelect={setSelectedAction} plainLanguage compactHelp />
            </Suspense> : <OverviewHourlyChart data={data} peakHours={analysis.peakHours.map(row=>row.hour)} plainLanguage compactHelp />}
          <AnalysisExplanation {...section} title={section.chartTitle} target={explanations}>
            {kind === 'actions' && <dl className="action-definitions">{Object.entries(actionLabels).map(([action,label])=><div key={action}><dt>{label} <code>{action}</code></dt><dd>{action === 'play' ? definitions.plays.meaning : action === 'view' ? 'Xem thông tin phim, không phải phát phim.' : action === 'pause' ? 'Ghi nhận tạm dừng trong chuỗi log.' : action === 'stop' ? 'Kết thúc xem trước hết thời lượng phim mô phỏng.' : 'Kết thúc xem hết thời lượng phim mô phỏng; không chứng minh người thật đã xem hết.'}</dd></div>)}</dl>}
          </AnalysisExplanation>
        </ChartPanel>
        {kind === 'actions' ? <ChartPanel title="Số lượng và tỷ lệ hành động" note="Đối chiếu biểu đồ với đủ năm hành động." icon="table">
          <AnalysisResultsTable kind={kind} data={data} />
        </ChartPanel> : kind === 'hourly' ? <DailyActivitySummary explanationTarget={explanations} /> : <ChartPanel title="Phim dẫn đầu" note="Trong danh sách phim đã xuất." icon="trophy" className="analysis-observation">
          <p className="analysis-leader">{data[0].title}</p>
          <p className="analysis-feature-value"><strong>{number(data[0].playCount)}</strong> lượt phát phim</p>
          {data[1] && <p>Tiếp theo: <strong>{data[1].title}</strong> — {number(data[1].playCount)} lượt phát phim.</p>}
          <p className="chart-note">Danh sách gồm {number(data.length)} phim, không phải toàn bộ danh mục MovieLens. Lượt phát không cho biết số người xem duy nhất.</p>
        </ChartPanel>}
        <div ref={explanations} className="independent-explanations analysis-wide" />
        {kind !== 'actions' && <ChartPanel className="analysis-wide" title={kind === 'movies' ? 'Tra cứu xếp hạng phim' : 'Bảng hoạt động theo giờ'} note={kind === 'movies' ? 'Tìm kiếm trong danh sách đã xuất; hạng giữ nguyên theo toàn danh sách.' : 'Các số đếm theo giờ trong toàn kỳ, không phải theo từng ngày.'} icon="table">
          <AnalysisResultsTable kind={kind} data={data} />
        </ChartPanel>}
      </div>
      <p className="analysis-limitation">Kết quả mô tả log hành vi mô phỏng trong phạm vi ngày nêu trên, không đại diện thói quen người xem ngoài đời{kind === 'hourly' ? ' và không chứng minh xu hướng tăng trưởng' : ''}.</p>
      <AnalysisRelatedLinks links={section.links} />
    </>}
  </div>;
}
