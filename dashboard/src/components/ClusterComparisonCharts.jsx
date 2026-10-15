import ComparisonBarChart from './ComparisonBarChart.jsx';

const metrics = [
  { key: 'avgPlayCount', title: 'Lượt phát phim trung bình', unit: 'lượt/người dùng' },
  { key: 'avgDistinctMovies', title: 'Phim khác nhau trung bình', unit: 'phim/người dùng' },
  { key: 'avgSessionCount', title: 'Số phiên trung bình', unit: 'phiên/người dùng' },
];

export default function ClusterComparisonCharts({ profiles }) {
  return <div className="cluster-comparisons">
    <p className="chart-note">Mỗi biểu đồ có một trục và một đơn vị riêng. Chỉ so sánh các cụm trong cùng chỉ số.</p>
    <div className="cluster-comparison-grid">
      {metrics.map(metric => <section key={metric.key} className="cluster-comparison" data-comparison={metric.key} aria-label={metric.title}>
        <h3>{metric.title}</h3>
        <ComparisonBarChart data={profiles} dataKey={metric.key} unit={metric.unit} title={metric.title} compactHelp />
      </section>)}
    </div>
  </div>;
}
