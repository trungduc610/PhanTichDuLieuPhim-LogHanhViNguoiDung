import { useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel } from '../components/OverviewCharts.jsx';
import MetricCard from '../components/MetricCard.jsx';
import ClusterSizeChart from '../components/ClusterSizeChart.jsx';
import ClusterComparisonCharts from '../components/ClusterComparisonCharts.jsx';
import { loadClustering } from '../services/dashboardData.js';
import { featureLabels, profileMetrics, findUsers, formatProfile, formatCompletion, scoreNumber } from '../services/clustering.js';
import { number } from '../services/formatNumbers.js';

function UserLookup({ data }) {
  const [query, setQuery] = useState('');
  const [cluster, setCluster] = useState('all');
  const [page, setPage] = useState(1);
  const result = findUsers(data.assignments, { query, cluster, page });
  return <ChartPanel title="Tra cứu người dùng mô phỏng" note="Tìm chính xác hoặc theo một phần userId. Mỗi trang tối đa 20 dòng; cụm gán được giữ nguyên từ Spark.">
    <div className="chart-controls">
      <label htmlFor="cluster-user-query">userId</label>
      <input id="cluster-user-query" type="search" value={query} placeholder="Nhập mã hoặc một phần mã người dùng" onChange={event => { setQuery(event.target.value); setPage(1); }} />
      <label htmlFor="cluster-user-filter">Cụm</label>
      <select id="cluster-user-filter" value={cluster} onChange={event => { setCluster(event.target.value); setPage(1); }}>
        <option value="all">Tất cả cụm</option>
        {data.profiles.map(row => <option key={row.cluster} value={row.cluster}>{row.label}</option>)}
      </select>
    </div>
    <p className="lookup-status" role="status">Tìm thấy {number(result.total)} người dùng · Trang {result.page}/{result.totalPages}</p>
    <p id="user-scroll-help" className="table-scroll-help">↔ Bảng có 10 cột. Cuộn ngang hoặc kéo sang phải để xem tỷ lệ hoàn thành và thời lượng. Khi dùng bàn phím, chọn vùng bảng rồi dùng phím mũi tên.</p>
    <div className="table-scroll user-lookup" tabIndex={0} aria-label="Bảng người dùng có thể cuộn ngang" aria-describedby="user-scroll-help">
      <table><caption>Đặc trưng người dùng trên toàn kỳ</caption><thead><tr>
        <th scope="col">userId</th><th scope="col">Cụm</th><th scope="col">Sự kiện play</th><th scope="col">Sự kiện complete</th>
        <th scope="col">Phim khác nhau</th><th scope="col">Thể loại khác nhau</th><th scope="col">Phiên</th>
        <th scope="col">Hoàn thành phiên (%)</th><th scope="col">Tổng thời lượng (giây)</th><th scope="col">Trung bình đoạn xem (giây)</th>
      </tr></thead><tbody>{result.rows.map(row => <tr key={row.userId}>
        <th scope="row">{row.userId}</th><td>Cluster {row.cluster}</td><td>{number(row.playCount)}</td><td>{number(row.completeCount)}</td>
        <td>{number(row.distinctMovies)}</td><td>{number(row.distinctGenres)}</td><td>{number(row.sessionCount)}</td>
        <td>{formatCompletion(row)}</td><td>{number(row.totalWatchDuration)}</td><td>{number(row.avgWatchDuration)}</td>
      </tr>)}</tbody></table>
    </div>
    {result.total === 0 && <p>Không tìm thấy người dùng phù hợp.</p>}
    <div className="cluster-pagination">
      <button disabled={result.page === 1} onClick={() => setPage(result.page - 1)}>Trang trước</button>
      <button disabled={result.page === result.totalPages} onClick={() => setPage(result.page + 1)}>Trang sau</button>
    </div>
  </ChartPanel>;
}

function ClusteringContent() {
  const state = useDashboardData();
  const data = state.metrics;
  const first = data?.profiles[0];
  const second = data?.profiles[1];
  return <div className="clustering-page">
    <h1>Phân cụm người dùng</h1>
    <p className="intro">Kết quả K-Means do Spark MLlib xử lý trên dữ liệu hành vi mô phỏng.</p>
    <DataState />
    {state.status === 'ready' && <>
      <section className="metrics-grid" aria-label="Tổng quan mô hình">
        <MetricCard title="Người dùng được phân cụm" value={data.metadata.users} description="Số người dùng trong kết quả mô hình đã xuất." />
        <MetricCard title="Số cụm K được chọn" value={data.metadata.bestK} description="Đọc từ metadata của mô hình đã xuất." />
        <article className="metric-card"><h2>Silhouette Score</h2><p className="metric-value">{scoreNumber(data.metadata.silhouette)}</p><p className="metric-description">Điểm đánh giá, không có đơn vị; phạm vi từ −1 đến 1.</p></article>
      </section>
      <aside className="data-note">
        <strong>Đọc kết quả mô hình</strong>
        <p>Silhouette đo mức độ phân tách cụm theo thước đo đánh giá mô hình, không chứng minh hành vi hay sở thích của người xem thật. Nhãn Cluster chỉ là mã cụm.</p>
        <p>Các đặc trưng được chuẩn hóa trước khi Spark huấn luyện; hồ sơ dưới đây dùng đơn vị gốc. Frontend chỉ trình bày kết quả đã xuất.</p>
      </aside>
      <ChartPanel title="Đặc trưng đầu vào" note="Danh sách đọc từ featureColumnsJson của metadata, không lấy tất cả trường trong bảng người dùng làm đầu vào mô hình.">
        <ul className="feature-list">{data.features.map(key => <li key={key}>{featureLabels[key] || key} <code>{key}</code></li>)}</ul>
      </ChartPanel>
      <ChartPanel title="Thử nghiệm K từ 2 đến 6" note="Điểm silhouette do Spark tính trên đặc trưng đã chuẩn hóa, khoảng cách đánh giá squared Euclidean. K được chọn được đánh dấu theo metadata.">
        <div className="table-scroll" tabIndex={0}><table className="k-search-table"><caption>So sánh điểm đánh giá mô hình</caption>
          <thead><tr><th scope="col">K</th><th scope="col">Silhouette Score</th><th scope="col">Trạng thái</th></tr></thead>
          <tbody>{data.search.map(row => <tr key={row.k} className={row.k === data.metadata.bestK ? 'selected-k' : ''}>
            <th scope="row">{row.k}</th><td title={String(row.silhouette)}>{scoreNumber(row.silhouette)}</td><td>{row.k === data.metadata.bestK ? 'K được chọn' : 'Đã thử nghiệm'}</td>
          </tr>)}</tbody></table></div>
      </ChartPanel>
      <ChartPanel title="Số người dùng từng cụm" note={`Tổng ${number(data.metadata.users)} người dùng; đã đối chiếu hồ sơ cụm, metadata và assignments.`}>
        <ClusterSizeChart profiles={data.profiles} />
        <p className="cluster-size-summary">{data.profiles.map(row => `${row.label}: ${number(row.userCount)} người dùng`).join(' · ')}</p>
      </ChartPanel>
      <ChartPanel title="So sánh đặc điểm các cụm" note="Giá trị lấy trực tiếp từ hồ sơ cụm: trung bình theo người dùng trong toàn kỳ; số lẻ ở chỉ số đếm là kết quả trung bình.">
        <ClusterComparisonCharts profiles={data.profiles} />
        <div className="table-scroll" tabIndex={0}><table className="cluster-profile-table"><caption>Hồ sơ cụm bằng đơn vị gốc</caption>
          <thead><tr><th scope="col">Chỉ số</th>{data.profiles.map(row => <th scope="col" key={row.cluster}>{row.label}</th>)}</tr></thead>
          <tbody>{profileMetrics.map(metric => <tr key={metric.key} data-profile={metric.key}>
            <th scope="row">{metric.label} ({metric.unit})</th>{data.profiles.map(row => <td key={row.cluster} title={String(row[metric.key])}>{formatProfile(metric.key, row[metric.key])}</td>)}
          </tr>)}</tbody></table></div>
        <p className="chart-note">Tỷ lệ hoàn thành của mỗi người dùng = số phiên phân biệt có complete / số phiên có play. Tỷ lệ hoàn thành trung bình của cụm là trung bình các tỷ lệ người dùng, không phải tổng sự kiện complete chia tổng sự kiện play. Người dùng không có phiên play có giá trị 0 trong hồ sơ và được ghi “Chưa xác định” khi tra cứu.</p>
        <p className="chart-note">Tổng thời lượng trung bình mỗi người dùng (avgTotalWatchDuration) là trung bình tổng thời lượng từng người trong kỳ. Trung bình thời lượng đoạn xem theo người dùng (avgWatchDuration) là trung bình của các trung bình đoạn xem dương của từng người; bằng 0 cho người không có đoạn xem. Hai chỉ số này không thay thế nhau và không phải thời lượng trung bình mỗi phiên.</p>
        <p className="chart-note">Phiên phân biệt theo (runId, sessionId) trong từng người dùng. Phim khác nhau và phiên tính trên các sự kiện đã ghi nhận; một phiên có thể có nhiều sự kiện play.</p>
      </ChartPanel>
      {second && <section className="chart-panel cluster-observation" aria-label="Nhận xét từ dữ liệu">
        <h2>Nhận xét từ dữ liệu</h2>
        <p>So sánh {first.label} và {second.label}: số sự kiện play trung bình lần lượt là {number(first.avgPlayCount)} và {number(second.avgPlayCount)} sự kiện/người dùng; số phim khác nhau trung bình là {number(first.avgDistinctMovies)} và {number(second.avgDistinctMovies)} phim/người dùng.</p>
        <p>Tỷ lệ hoàn thành phiên trung bình lần lượt là {formatProfile('avgCompletionRate', first.avgCompletionRate)} và {formatProfile('avgCompletionRate', second.avgCompletionRate)}. Trung bình thời lượng đoạn xem theo người dùng là {number(first.avgWatchDuration)} và {number(second.avgWatchDuration)} giây.</p>
        <p className="chart-note">Các khác biệt mô tả hồ sơ cụm trong dữ liệu mô phỏng; không gán ý nghĩa tâm lý hoặc kinh doanh cho các cụm.</p>
      </section>}
      <UserLookup data={data} />
    </>}
  </div>;
}

export default function ClusteringPage() {
  return <DashboardDataProvider loader={loadClustering}><ClusteringContent /></DashboardDataProvider>;
}
