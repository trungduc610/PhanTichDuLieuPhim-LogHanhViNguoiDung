import { useState } from 'react';
import { DashboardDataProvider, DataState, useDashboardData } from '../components/DashboardData.jsx';
import { ChartPanel } from '../components/OverviewCharts.jsx';
import AnalysisPageHeader from '../components/AnalysisPageHeader.jsx';
import ReadingGuide from '../components/ReadingGuide.jsx';
import MetricCard from '../components/MetricCard.jsx';
import Icon from '../components/Icon.jsx';
import ScrollableTable from '../components/ScrollableTable.jsx';
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
  return <ChartPanel className="analysis-wide" title="Tra cứu người dùng mô phỏng" note="Tìm theo toàn bộ hoặc một phần mã người dùng. Giữ nguyên cụm Spark đã gán; tối đa 20 dòng/trang." icon="users">
    <div className="chart-controls">
      <div className="filter-field"><label htmlFor="cluster-user-query">Mã người dùng (userId)</label>
        <input id="cluster-user-query" type="search" value={query} placeholder="Nhập mã hoặc một phần mã người dùng" onChange={event => { setQuery(event.target.value); setPage(1); }} />
      </div>
      <div className="filter-field"><label htmlFor="cluster-user-filter">Cụm</label>
        <select id="cluster-user-filter" value={cluster} onChange={event => { setCluster(event.target.value); setPage(1); }}>
          <option value="all">Tất cả cụm</option>
          {data.profiles.map(row => <option key={row.cluster} value={row.cluster}>{row.label}</option>)}
        </select>
      </div>
    </div>
    <p className="lookup-status" role="status">Tìm thấy {number(result.total)} người dùng · Trang {result.page}/{result.totalPages}</p>
    <ScrollableTable className="user-lookup" label="Bảng tra cứu người dùng" hintId="user-scroll-help" hint="Bảng có 10 cột. Cuộn ngang hoặc kéo sang phải để xem tỷ lệ hoàn thành và thời lượng.">
      <table><caption>Đặc trưng người dùng trên toàn kỳ</caption><thead><tr>
        <th scope="col">userId</th><th scope="col">Cụm</th><th scope="col">Sự kiện play</th><th scope="col">Sự kiện complete</th>
        <th scope="col">Phim khác nhau</th><th scope="col">Thể loại khác nhau</th><th scope="col">Phiên</th>
        <th scope="col">Hoàn thành phiên (%)</th><th scope="col">Tổng thời lượng (giây)</th><th scope="col">Trung bình đoạn xem (giây)</th>
      </tr></thead><tbody>{result.rows.map(row => <tr key={row.userId}>
        <th scope="row">{row.userId}</th><td>Cluster {row.cluster}</td><td>{number(row.playCount)}</td><td>{number(row.completeCount)}</td>
        <td>{number(row.distinctMovies)}</td><td>{number(row.distinctGenres)}</td><td>{number(row.sessionCount)}</td>
        <td>{formatCompletion(row)}</td><td>{number(row.totalWatchDuration)}</td><td>{number(row.avgWatchDuration)}</td>
      </tr>)}</tbody></table>
    </ScrollableTable>
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
  return <div className="analysis-page overview-page clustering-page">
    <AnalysisPageHeader title="Phân cụm người dùng" description="Khám phá kết quả K-Means và so sánh các nhóm người dùng mô phỏng do Spark MLlib xử lý." />
    <DataState />
    {state.status === 'ready' && <>
      <section className="metrics-grid" aria-label="Tổng quan mô hình">
        <MetricCard icon="users" title="Người dùng được phân cụm" value={data.metadata.users} description="Số người dùng trong kết quả mô hình đã xuất." />
        <MetricCard icon="cluster" title="Số cụm K được chọn" value={data.metadata.bestK} description="Đọc từ metadata của mô hình đã xuất." />
        <article className="metric-card"><div className="metric-topline"><h2>Silhouette Score</h2><span className="metric-icon"><Icon name="chart" size={18} /></span></div>
          <p className="metric-value">{scoreNumber(data.metadata.silhouette)}</p><p className="metric-description">Điểm phân tách cụm, không có đơn vị; phạm vi −1 đến 1.</p>
        </article>
      </section>
      <p className="analysis-context">K-Means mô tả các nhóm trong dữ liệu mô phỏng. Silhouette không chứng minh hành vi người xem thật; nhãn Cluster chỉ là mã cụm.</p>
      <div className="analysis-grid">
        <ChartPanel title="Số người dùng từng cụm" note={'Tổng ' + number(data.metadata.users) + ' người dùng; đối chiếu từ các kết quả mô hình.'} icon="users">
          <ClusterSizeChart profiles={data.profiles} />
          <p className="cluster-size-summary chart-note">{data.profiles.map(row => row.label + ': ' + number(row.userCount) + ' người dùng').join(' · ')}</p>
        </ChartPanel>
        <ChartPanel title="Thử nghiệm K từ 2 đến 6" note="K được chọn được đánh dấu theo metadata." icon="cluster">
          <ScrollableTable label="Bảng thử nghiệm K"><table className="k-search-table"><caption>So sánh điểm đánh giá mô hình</caption>
            <thead><tr><th scope="col">K</th><th scope="col">Silhouette Score</th><th scope="col">Trạng thái</th></tr></thead>
            <tbody>{data.search.map(row => <tr key={row.k} className={row.k === data.metadata.bestK ? 'selected-k' : ''}>
              <th scope="row">{row.k}</th><td title={String(row.silhouette)}>{scoreNumber(row.silhouette)}</td><td>{row.k === data.metadata.bestK ? 'K được chọn' : 'Đã thử nghiệm'}</td>
            </tr>)}</tbody></table>
          </ScrollableTable>
          <ReadingGuide title="Đặc trưng và phương pháp mô hình">
            <p>Các đặc trưng được chuẩn hóa trước khi Spark huấn luyện; hồ sơ dùng đơn vị gốc. Silhouette được Spark tính với khoảng cách đánh giá squared Euclidean.</p>
            <p>Đặc trưng đầu vào đọc từ featureColumnsJson của metadata, không lấy tất cả trường trong bảng người dùng:</p>
            <ul className="feature-list">{data.features.map(key => <li key={key}>{featureLabels[key] || key}<code>{key}</code></li>)}</ul>
          </ReadingGuide>
        </ChartPanel>
        <ChartPanel className="analysis-wide" title="So sánh đặc điểm các cụm" note="Trung bình theo người dùng trong toàn kỳ, lấy trực tiếp từ hồ sơ cụm; chỉ số đếm trung bình có thể là số lẻ." icon="chart">
          <ClusterComparisonCharts profiles={data.profiles} />
          <ScrollableTable label="Bảng so sánh hồ sơ cụm"><table className="cluster-profile-table"><caption>Hồ sơ cụm bằng đơn vị gốc</caption>
            <thead><tr><th scope="col">Chỉ số</th>{data.profiles.map(row => <th scope="col" key={row.cluster}>{row.label}</th>)}</tr></thead>
            <tbody>{profileMetrics.map(metric => <tr key={metric.key} data-profile={metric.key}>
              <th scope="row">{metric.label} ({metric.unit})</th>{data.profiles.map(row => <td key={row.cluster} title={String(row[metric.key])}>{formatProfile(metric.key, row[metric.key])}</td>)}
            </tr>)}</tbody></table>
          </ScrollableTable>
          <p className="chart-note">Tỷ lệ hoàn thành trung bình là trung bình tỷ lệ của từng người dùng, không phải tổng sự kiện complete chia tổng sự kiện play.</p>
          <ReadingGuide title="Cách đọc tỷ lệ, phiên và thời lượng">
            <p>Tỷ lệ hoàn thành của mỗi người dùng = số phiên phân biệt có complete / số phiên có play. Khi hiển thị %, nhân tỷ lệ từ 0–1 với 100. Người không có phiên play có giá trị 0 trong hồ sơ và được ghi “Chưa xác định” khi tra cứu.</p>
            <p>Tổng thời lượng trung bình mỗi người dùng (avgTotalWatchDuration) là trung bình tổng thời lượng từng người trong kỳ. Trung bình thời lượng đoạn xem theo người dùng (avgWatchDuration) là trung bình của các trung bình đoạn xem dương của từng người; bằng 0 cho người không có đoạn xem. Hai chỉ số không thay thế nhau và không phải thời lượng trung bình mỗi phiên.</p>
            <p>Phiên phân biệt theo (runId, sessionId) trong từng người dùng. Phim khác nhau và phiên tính trên các sự kiện đã ghi nhận; một phiên có thể có nhiều sự kiện play.</p>
          </ReadingGuide>
        </ChartPanel>
        {second && <ChartPanel className="analysis-wide cluster-observation" title="Nhận xét từ dữ liệu" note="So sánh hồ sơ cụm, không gán nhãn tâm lý hoặc kinh doanh." icon="info">
          <p>So sánh {first.label} và {second.label}: số sự kiện play trung bình lần lượt là {number(first.avgPlayCount)} và {number(second.avgPlayCount)} sự kiện/người dùng; số phim khác nhau trung bình là {number(first.avgDistinctMovies)} và {number(second.avgDistinctMovies)} phim/người dùng.</p>
          <p>Tỷ lệ hoàn thành phiên trung bình lần lượt là {formatProfile('avgCompletionRate', first.avgCompletionRate)} và {formatProfile('avgCompletionRate', second.avgCompletionRate)}. Trung bình thời lượng đoạn xem theo người dùng là {number(first.avgWatchDuration)} và {number(second.avgWatchDuration)} giây.</p>
          <p className="chart-note">Các khác biệt chỉ mô tả dữ liệu mô phỏng, không phản ánh sở thích người xem thật.</p>
        </ChartPanel>}
        <UserLookup data={data} />
      </div>
    </>}
  </div>;
}

export default function ClusteringPage() {
  return <DashboardDataProvider loader={loadClustering}><ClusteringContent /></DashboardDataProvider>;
}
