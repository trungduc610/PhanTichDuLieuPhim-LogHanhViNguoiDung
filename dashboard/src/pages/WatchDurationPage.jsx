import { useRef, useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import AnalysisExplanation, { AnalysisRelatedLinks } from '../components/AnalysisExplanation.jsx';
import MetricCard from '../components/MetricCard.jsx';
import ScrollableTable from '../components/ScrollableTable.jsx';
import ResultCsvButton from '../components/ResultCsvButton.jsx';
import { loadWatchDuration } from '../services/dashboardData.js';
import { durationFields } from '../services/watchDuration.js';
import { number } from '../services/formatNumbers.js';
import ComparisonBarChart from '../components/ComparisonBarChart.jsx';

const csvColumns = [{key:'scope',label:'Nhóm bản ghi'}, {key:'unit',label:'Đơn vị gốc'}, ...durationFields.map(row=>({key:row.key,label:`${row.label} (${row.unit})`}))];
const meaning = {
  mean: 'Trung bình là tổng giây ghi nhận chia cho số bản ghi của từng nhóm. Các bản ghi bằng 0 vẫn được tính ở nhóm toàn bộ hành động.',
  median: 'Trung vị là giá trị ở giữa khi sắp xếp thời lượng. Spark tính xấp xỉ, nên không nhất thiết bằng trung bình.',
  min: 'Giá trị nhỏ nhất trong từng nhóm bản ghi. Nhóm toàn bộ có thể có thời lượng bằng 0; nhóm dương chỉ có giá trị lớn hơn 0.',
  max: 'Giá trị lớn nhất của một bản ghi trong từng nhóm, không phải thời lượng dài nhất của một phiên.',
  stddev: 'Độ lệch chuẩn mẫu mô tả mức phân tán của thời lượng quanh trung bình. Giá trị lớn hơn nghĩa là các thời lượng phân tán hơn, không phải người dùng xem lâu hơn.',
};
const controls = 'Tab vào biểu đồ; dùng các phím mũi tên để đổi nhóm, Home/End đến đầu/cuối và Esc bỏ đánh dấu. Có thể di chuột hoặc chạm vào thanh để đọc số liệu.';

function WatchDurationContent() {
  const state = useDashboardData();
  const data = state.metrics;
  const [stat,setStat] = useState('mean');
  const chartInfo = useRef(null);
  const tableInfo = useRef(null);
  const metric = durationFields.find(row=>row.key===stat);
  return <div className="analysis-page overview-page detail-ux advanced-ux duration-page">
    <AnalysisPageHeader title="Thời lượng xem" description="So sánh thời lượng ghi nhận trên toàn bộ hành động và các bản ghi có thời lượng dương." detailed />
    <p className="analysis-context"><strong>Đơn vị: giây.</strong> Đây là thời lượng của từng bản ghi, không phải thời lượng mỗi phiên sử dụng.</p>
    <DataState />
    {state.status==='ready' && <>
      <section className="metrics-grid duration-metrics" aria-label="Số bản ghi và trung bình thời lượng">
        <MetricCard icon="events" title="Toàn bộ hành động · Bản ghi" value={data.allEvents.count} description="Gồm cả bản ghi có thời lượng bằng 0." />
        <MetricCard icon="duration" title="Toàn bộ hành động · Trung bình" value={data.allEvents.mean} unit="giây" description="Trung bình trên mọi bản ghi hợp lệ." />
        <MetricCard icon="events" title="Thời lượng dương · Bản ghi" value={data.watchSegments.count} description="Chỉ các bản ghi có thời lượng lớn hơn 0." />
        <MetricCard icon="duration" title="Thời lượng dương · Trung bình" value={data.watchSegments.mean} unit="giây" description="Trung bình trên các bản ghi dương." />
      </section>
      <div className="analysis-grid">
        <ChartPanel className="analysis-wide" title="So sánh thời lượng giữa hai nhóm" note="Hai nhóm có phạm vi khác nhau; nhóm dương nằm trong nhóm toàn bộ." icon="chart">
          <div className="chart-controls"><div className="filter-field"><label htmlFor="duration-stat">Chỉ số thời lượng</label>
            <select id="duration-stat" value={stat} onChange={event=>setStat(event.target.value)}>{durationFields.filter(row=>row.unit==='giây').map(row=><option key={row.key} value={row.key}>{row.label}</option>)}</select>
          </div></div>
          <p className="stat-meaning" role="status">{meaning[stat]}</p>
          <div data-chart="watch-duration" data-statistic={stat}>
            <ComparisonBarChart data={[{cluster:0,label:'Toàn bộ',value:data.allEvents[stat]},{cluster:1,label:'Đoạn dương',value:data.watchSegments[stat]}]}
              dataKey="value" unit="giây" title={metric.label} itemName="nhóm" compactHelp />
            <div className="duration-values" aria-label="Giá trị chỉ số đang chọn">
              <span data-duration-scope="all_events">Toàn bộ hành động: <strong>{number(data.allEvents[stat])} giây</strong></span>
              <span data-duration-scope="watch_segments">Bản ghi dương: <strong>{number(data.watchSegments[stat])} giây</strong></span>
            </div>
          </div>
          <AnalysisExplanation title="Thống kê thời lượng" target={chartInfo}
            help="Nhóm toàn bộ hành động tính cả các bản ghi có thời lượng bằng 0. Nhóm thời lượng dương chỉ giữ những đoạn có số giây mới phát sinh lớn hơn 0. Không cộng hai nhóm vì nhóm dương đã nằm trong nhóm toàn bộ."
            technical="Nguồn: stats_watch_duration_summary.json. scope = all_events hoặc watch_segments (watchDuration > 0), unit = seconds. Spark tính count, avg, percentile_approx tại 0,5, min, max và stddev_samp. watchDuration là giây mới phát sinh ở từng đoạn, không phải thời lượng phiên. Tệp này không xuất tổng thời lượng; không dùng trung bình đã làm tròn để suy ra tổng."
            instructions={'Chọn chỉ số để cập nhật hai thanh trên cùng đơn vị giây. '+controls} />
        </ChartPanel>
        <div ref={chartInfo} className="independent-explanations analysis-wide" />
        <ChartPanel title="Đối chiếu các thống kê" note="Số đếm giữ nguyên; thời lượng hiển thị tối đa 3 chữ số thập phân." icon="table">
          <div className="results-controls"><ResultCsvButton columns={csvColumns} rows={[data.allEvents,data.watchSegments]} filename="thong-ke-thoi-luong.csv" label="Thống kê thời lượng" /></div>
          <ScrollableTable label="Bảng thống kê thời lượng"><table className="duration-table"><caption>Thời lượng theo bản ghi trong toàn kỳ</caption>
            <thead><tr><th scope="col">Chỉ số</th><th scope="col">Toàn bộ hành động</th><th scope="col">Bản ghi có thời lượng &gt; 0</th></tr></thead>
            <tbody>{durationFields.map(({key,label,unit})=><tr key={key} data-stat={key}><th scope="row">{label} ({unit})</th><td title={String(data.allEvents[key])}>{number(data.allEvents[key])}</td><td title={String(data.watchSegments[key])}>{number(data.watchSegments[key])}</td></tr>)}</tbody>
          </table></ScrollableTable>
          <AnalysisExplanation title="Cách đọc bảng thời lượng" target={tableInfo}
            help="Số bản ghi cho biết quy mô từng nhóm. Trung bình mô tả mức bình quân; trung vị mô tả giá trị giữa. Nhỏ nhất, lớn nhất và độ lệch chuẩn cho biết phạm vi và độ phân tán. Không có cột nào ở đây là tổng thời lượng hoặc trung bình phiên."
            technical="Trung vị dùng percentile_approx(watchDuration, 0.5, 10000); độ lệch chuẩn là stddev_samp. Giao diện làm tròn khi hiển thị, CSV giữ giá trị gốc chưa làm tròn của hai nhóm."
            instructions="Cuộn trong bảng để đọc đủ cột; Tab vào vùng bảng rồi dùng ←/→, Home/End khi có cột bị khuất. CSV giữ cả hai nhóm và toàn bộ chỉ số, độc lập với chỉ số đang chọn trên biểu đồ." />
        </ChartPanel>
        <ChartPanel title="Điểm khác biệt giữa hai nhóm" note="Đối chiếu các thống kê đã xuất, không ước lượng thêm." icon="info" className="duration-observation">
          <p>Trung bình nhóm dương {data.meanDifference===0?'bằng nhóm toàn bộ hành động.':(data.meanDifference>0?'cao hơn':'thấp hơn')+' nhóm toàn bộ hành động '+number(Math.abs(data.meanDifference))+' giây.'}</p>
          <p>Trung vị toàn bộ hành động: <strong>{number(data.allEvents.median)} giây</strong>. Trung vị nhóm dương: <strong>{number(data.watchSegments.median)} giây</strong>.</p>
          <p className="chart-note">Nhóm toàn bộ còn tính các bản ghi bằng 0. Hai phạm vi khác nhau nên cần đọc tên nhóm trước khi so sánh.</p>
        </ChartPanel>
        <div ref={tableInfo} className="independent-explanations analysis-wide" />
      </div>
      <p className="analysis-limitation">Kết quả mô tả log mô phỏng; không suy ra thời lượng phiên hay sở thích của người xem ngoài đời.</p>
      <AnalysisRelatedLinks links={[["/hanh-vi","Phân biệt các hành động"],["/phan-cum","So sánh các nhóm người dùng"]]} />
    </>}
  </div>;
}
export default function WatchDurationPage() {
  return <DashboardDataProvider loader={loadWatchDuration}><WatchDurationContent /></DashboardDataProvider>;
}
