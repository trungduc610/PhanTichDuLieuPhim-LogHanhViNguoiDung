import { useRef, useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import AnalysisExplanation, { AnalysisRelatedLinks } from '../components/AnalysisExplanation.jsx';
import MetricCard from '../components/MetricCard.jsx';
import Icon from '../components/Icon.jsx';
import ScrollableTable from '../components/ScrollableTable.jsx';
import ResultCsvButton from '../components/ResultCsvButton.jsx';
import ClusterSizeChart from '../components/ClusterSizeChart.jsx';
import ClusterComparisonCharts from '../components/ClusterComparisonCharts.jsx';
import { loadClustering } from '../services/dashboardData.js';
import { featureLabels, profileMetrics, findUsers, formatProfile, formatCompletion, scoreNumber } from '../services/clustering.js';
import { number } from '../services/formatNumbers.js';

const featureNames = {...featureLabels,playCount:'Lượt phát phim',completeCount:'Hành động hoàn thành xem phim',eventCount:'Tổng số hành động'};
const csvColumns = [['userId','Mã người dùng'],['cluster','Mã cụm'],['playCount','Lượt phát phim'],['completeCount','Hành động hoàn thành xem phim'],['distinctMovies','Phim khác nhau'],['distinctGenres','Thể loại khác nhau'],['sessionCount','Phiên sử dụng'],['playedSessionCount','Phiên có phát phim'],['completedSessionCount','Phiên có hoàn thành'],['completionRate','Tỷ lệ hoàn thành phiên (0–1)'],['completionRateDefined','Tỷ lệ có xác định'],['totalWatchDuration','Tổng thời lượng (giây)'],['avgWatchDuration','Trung bình đoạn xem (giây)']].map(([key,label])=>({key,label}));
const chartControls = 'Di chuột hoặc chạm thanh để đọc giá trị. Tab vào từng biểu đồ, dùng các phím mũi tên để đổi cụm, Home/End đến đầu/cuối và Esc bỏ đánh dấu.';

function UserLookup({ data, explanationTarget }) {
  const [query,setQuery] = useState('');
  const [cluster,setCluster] = useState('all');
  const [page,setPage] = useState(1);
  const result = findUsers(data.assignments,{query,cluster,page});
  const exportRows = findUsers(data.assignments,{query,cluster,pageSize:data.assignments.length}).rows;
  return <ChartPanel className="analysis-wide" title="Tra cứu người dùng mô phỏng" note="Tìm trong kết quả Spark đã xuất; 20 người dùng mỗi trang, giữ nguyên mã cụm." icon="users">
    <div className="chart-controls">
      <div className="filter-field"><label htmlFor="cluster-user-query">Mã người dùng</label><input id="cluster-user-query" type="search" value={query} placeholder="Nhập mã hoặc một phần mã người dùng" onChange={event=>{setQuery(event.target.value);setPage(1);}} /></div>
      <div className="filter-field"><label htmlFor="cluster-user-filter">Cụm</label><select id="cluster-user-filter" value={cluster} onChange={event=>{setCluster(event.target.value);setPage(1);}}><option value="all">Tất cả cụm</option>{data.profiles.map(row=><option key={row.cluster} value={row.cluster}>{row.label}</option>)}</select></div>
      <ResultCsvButton columns={csvColumns} rows={exportRows} filename="nguoi-dung-theo-cum.csv" label="Người dùng khớp bộ lọc" />
    </div>
    <p className="lookup-status" role="status">Tìm thấy {number(result.total)} người dùng · Trang {result.page}/{result.totalPages}</p>
    <ScrollableTable className="user-lookup" label="Bảng tra cứu người dùng" hintId="user-scroll-help" hint="Bảng có 10 cột. Cuộn ngang để xem tỷ lệ hoàn thành và thời lượng.">
      <table><caption>Đặc trưng người dùng trên toàn kỳ</caption><thead><tr>
        <th scope="col">Mã người dùng</th><th scope="col">Cụm</th><th scope="col">Lượt phát phim</th><th scope="col">Hoàn thành xem phim (lần)</th><th scope="col">Phim khác nhau</th><th scope="col">Thể loại khác nhau</th><th scope="col">Phiên sử dụng</th><th scope="col">Hoàn thành phiên (%)</th><th scope="col">Tổng thời lượng (giây)</th><th scope="col">Trung bình đoạn xem (giây)</th>
      </tr></thead><tbody>{result.rows.map(row=><tr key={row.userId}>
        <th scope="row">{row.userId}</th><td>Cụm {row.cluster}</td><td>{number(row.playCount)}</td><td>{number(row.completeCount)}</td><td>{number(row.distinctMovies)}</td><td>{number(row.distinctGenres)}</td><td>{number(row.sessionCount)}</td><td>{formatCompletion(row)}</td><td>{number(row.totalWatchDuration)}</td><td>{number(row.avgWatchDuration)}</td>
      </tr>)}</tbody></table>
    </ScrollableTable>
    {result.total===0 && <p role="status">Không tìm thấy người dùng phù hợp.</p>}
    <div className="cluster-pagination"><button disabled={result.page===1} onClick={()=>setPage(result.page-1)}>Trang trước</button><button disabled={result.page===result.totalPages} onClick={()=>setPage(result.page+1)}>Trang sau</button></div>
    <AnalysisExplanation title="Đặc trưng từng người dùng" target={explanationTarget}
      help="Mỗi dòng là một người dùng mô phỏng và cụm mô hình đã gán. Lượt phát và hành động hoàn thành đếm từng bản ghi; phiên sử dụng đếm mã phiên. Phim và thể loại khác nhau được đếm trên mọi hành động đã ghi nhận, kể cả xem thông tin phim. Tổng thời lượng cộng số giây ghi nhận của người đó trong kỳ; trung bình đoạn xem chỉ tính các đoạn dương, không phải trung bình phiên."
      technical="Nguồn: kmeans_assignments.json. userId là mã mô phỏng, cluster là nhãn phân cụm. completionRate = completedSessionCount / playedSessionCount; khi không có phiên play, completionRateDefined = false, bảng ghi Chưa xác định và giá trị số nguồn bằng 0. CSV giữ tỷ lệ gốc 0–1 cùng cờ xác định và số phiên làm tử/mẫu. Không dùng completeCount / playCount để thay tỷ lệ phiên."
      instructions="Kết hợp tìm mã và lọc cụm, rồi dùng Trang trước/Trang sau. Tab vào bảng, dùng ←/→ và Home/End để cuộn các cột. CSV gồm mọi người dùng khớp bộ lọc, không chỉ 20 dòng trên trang; thay bộ lọc không chạy lại mô hình." />
  </ChartPanel>;
}
function ClusteringContent() {
  const state = useDashboardData();
  // Chỉ Việt hóa nhãn hiển thị; giữ nguyên ID, số liệu và kết quả gán cụm.
  const data = state.metrics ? {...state.metrics,profiles:state.metrics.profiles.map(row=>({...row,label:`Cụm ${row.cluster}`}))} : null;
  const modelInfo = useRef(null);
  const profileInfo = useRef(null);
  const lookupInfo = useRef(null);
  const first = data?.profiles[0], second = data?.profiles[1];
  return <div className="analysis-page overview-page detail-ux advanced-ux clustering-page">
    <AnalysisPageHeader title="Phân nhóm người dùng" description="So sánh các nhóm người dùng mô phỏng có đặc trưng hành vi gần nhau." detailed />
    <DataState />
    {state.status==='ready' && <>
      <p className="analysis-context">K-Means gom người dùng dựa trên đặc trưng hành vi đã đo. Đây là phân cụm không giám sát, không phải dự đoán hành vi hoặc hệ thống đề xuất phim; mã cụm không biểu thị tính cách hay sở thích.</p>
      <section className="metrics-grid" aria-label="Kết quả phân nhóm">
        <MetricCard icon="users" title="Người dùng được phân nhóm" value={data.metadata.users} description="Người dùng trong kết quả mô hình đã xuất." />
        <MetricCard icon="cluster" title="Số cụm được chọn" value={data.metadata.bestK} description="K được chọn trong các lần thử đã xuất." />
        <article className="metric-card"><div className="metric-topline"><h2>Silhouette Score</h2><span className="metric-icon"><Icon name="chart" size={18} /></span></div><p className="metric-value">{scoreNumber(data.metadata.silhouette)}</p><p className="metric-description">Điểm phân tách cụm từ −1 đến 1; không phải độ chính xác hay tỷ lệ phần trăm.</p></article>
      </section>
      <div className="analysis-grid">
        <ChartPanel title="Quy mô từng cụm" note={'Tổng '+number(data.metadata.users)+' người dùng trong toàn kỳ.'} icon="users">
          <ClusterSizeChart profiles={data.profiles} />
          <p className="cluster-size-summary chart-note">{data.profiles.map(row=>row.label+': '+number(row.userCount)+' người dùng').join(' · ')}</p>
          <AnalysisExplanation title="Quy mô từng cụm" target={modelInfo}
            help="Mỗi người dùng được gán vào một cụm trong kết quả này. Chiều cao thanh thể hiện số người dùng, không phải mức độ quan trọng của cụm. Mã cụm là nhãn trung tính và không có thứ tự tốt/xấu."
            technical="Nguồn: kmeans_cluster_profiles.json (userCount, cluster), đối chiếu số người dùng với metadata và assignments bằng cơ chế hiện có. Mã cụm chỉ có ý nghĩa trong lần chạy này; không tự gán tên tính cách hoặc so sánh ID giữa các lần huấn luyện."
            instructions={chartControls} />
        </ChartPanel>
        <ChartPanel title="So sánh số cụm đã thử" note="Đối chiếu Silhouette; dòng được chọn theo metadata của mô hình." icon="cluster">
          <ScrollableTable label="Bảng thử nghiệm K"><table className="k-search-table"><caption>Điểm Silhouette theo số cụm K</caption><thead><tr><th scope="col">Số cụm K</th><th scope="col">Silhouette Score</th><th scope="col">Trạng thái</th></tr></thead>
            <tbody>{data.search.map(row=><tr key={row.k} className={row.k===data.metadata.bestK?'selected-k':''}><th scope="row">{row.k}</th><td title={String(row.silhouette)}>{scoreNumber(row.silhouette)}</td><td>{row.k===data.metadata.bestK?'K được chọn':'Đã thử nghiệm'}</td></tr>)}</tbody>
          </table></ScrollableTable>
          <AnalysisExplanation title="K-Means và Silhouette" target={modelInfo}
            help="K là số nhóm cần chia. K-Means lặp việc gán người dùng về tâm gần nhất rồi cập nhật tâm nhóm trên các đặc trưng đã chuẩn hóa. Silhouette so sánh mức gần trong cùng cụm với mức tách khỏi cụm khác: gần 1 thường tách rõ hơn, gần 0 dễ chồng lấp, âm có thể gán chưa phù hợp. Điểm này không đo dự đoán đúng/sai và không xác nhận sở thích người thật."
            technical={<><span>Nguồn: kmeans_model_metadata.json, kmeans_k_search.json; mã nguồn src/tv2_clustering.py. StandardScaler dùng withMean = true, withStd = true; K-Means dùng Euclidean, ClusteringEvaluator dùng squaredEuclidean. Chọn Silhouette lớn nhất trong các K đã thử, chỉ ưu tiên K nhỏ khi bằng điểm chính xác. Seed từ metadata: {data.metadata.seed}. Đặc trưng đầu vào đọc từ featureColumnsJson:</span><span className="feature-list" role="list">{data.features.map(key=><span role="listitem" key={key}>{featureNames[key]||key} <code>{key}</code></span>)}</span><span>Các trường trong bảng tra cứu không mặc nhiên đều là đầu vào mô hình. Hồ sơ cụm dưới đây dùng đơn vị gốc, không phải tọa độ tâm đã chuẩn hóa.</span></>}
            instructions="Đọc dòng K được chọn và so điểm giữa các lần thử trong bảng. Mở Chi tiết kỹ thuật để xem đặc trưng, seed và cách chuẩn hóa. Mở trang chỉ đọc kết quả, không huấn luyện lại mô hình." />
        </ChartPanel>
        <div ref={modelInfo} className="independent-explanations analysis-wide" />
        <ChartPanel className="analysis-wide" title="So sánh đặc điểm các cụm" note="Trung bình theo người dùng, giữ đơn vị gốc; số đếm trung bình có thể là số lẻ." icon="chart">
          <ClusterComparisonCharts profiles={data.profiles} />
          <ScrollableTable label="Bảng so sánh hồ sơ cụm"><table className="cluster-profile-table"><caption>Hồ sơ cụm trên toàn kỳ bằng đơn vị gốc</caption><thead><tr><th scope="col">Chỉ số</th>{data.profiles.map(row=><th scope="col" key={row.cluster}>{row.label}</th>)}</tr></thead>
            <tbody>{profileMetrics.map(metric=><tr key={metric.key} data-profile={metric.key}><th scope="row">{metric.key==='avgPlayCount'?'Lượt phát phim trung bình (lượt/người dùng)':`${metric.label} (${metric.unit})`}</th>{data.profiles.map(row=><td key={row.cluster} title={String(row[metric.key])}>{formatProfile(metric.key,row[metric.key])}</td>)}</tr>)}</tbody>
          </table></ScrollableTable>
          <p className="chart-note">Mỗi chỉ số có đơn vị riêng. Tỷ lệ hoàn thành là trung bình tỷ lệ phiên của từng người dùng, không phải tỷ lệ hành động.</p>
          <AnalysisExplanation title="Hồ sơ và sự khác biệt giữa các cụm" target={profileInfo}
            help="Các thanh so sánh cùng một chỉ số giữa các cụm. Bảng bổ sung tỷ lệ phiên và thời lượng; không so chiều dài thanh ở các biểu đồ khác đơn vị. Hồ sơ trung bình mô tả nhóm, không khẳng định mọi thành viên giống nhau."
            technical="Nguồn: kmeans_cluster_profiles.json. avgPlayCount, avgDistinctMovies, avgSessionCount là trung bình đặc trưng từng người. avgCompletionRate là trung bình completionRate, không phải tổng complete chia tổng play. Mỗi người: completionRate = số phiên phân biệt có complete / số phiên có play; mẫu số 0 được lưu bằng 0 trong hồ sơ. avgTotalWatchDuration là trung bình tổng giây của từng người trong kỳ. avgWatchDuration là trung bình các trung bình đoạn xem dương của từng người, kể cả giá trị 0 cho người không có đoạn dương; không phải trung bình gộp các đoạn hoặc thời lượng phiên. Phiên phân biệt theo (runId, sessionId) trong từng userId."
            instructions={chartControls+' Cuộn bảng để đối chiếu đủ các chỉ số. Các bộ lọc tra cứu người dùng bên dưới không thay đổi hồ sơ cụm.'} />
        </ChartPanel>
        <div ref={profileInfo} className="independent-explanations analysis-wide" />
        {second && <ChartPanel className="analysis-wide cluster-observation" title="Khác biệt được ghi nhận" note="So sánh hai hồ sơ đầu theo mã cụm; không gán nhãn tính cách hoặc giá trị người dùng." icon="info">
          <p>{first.label} và {second.label} có lượt phát trung bình lần lượt <strong>{number(first.avgPlayCount)}</strong> và <strong>{number(second.avgPlayCount)}</strong> lượt/người dùng; số phim khác nhau trung bình là {number(first.avgDistinctMovies)} và {number(second.avgDistinctMovies)} phim/người dùng.</p>
          <p>Tỷ lệ hoàn thành phiên trung bình: {formatProfile('avgCompletionRate',first.avgCompletionRate)} và {formatProfile('avgCompletionRate',second.avgCompletionRate)}. Đây là khác biệt của log mô phỏng, không phải kết luận về sở thích cá nhân.</p>
        </ChartPanel>}
        <UserLookup data={data} explanationTarget={lookupInfo} />
        <div ref={lookupInfo} className="independent-explanations analysis-wide" />
      </div>
      <p className="analysis-limitation">Phân cụm không giám sát mô tả dữ liệu mô phỏng của final run đã xác minh; không phải mô hình dự đoán hoặc đề xuất phim.</p>
      <AnalysisRelatedLinks links={[["/hanh-vi","Đối chiếu các hành động"],["/thoi-luong","Hiểu các thống kê thời lượng"]]} />
    </>}
  </div>;
}
export default function ClusteringPage() {
  return <DashboardDataProvider loader={loadClustering}><ClusteringContent /></DashboardDataProvider>;
}
