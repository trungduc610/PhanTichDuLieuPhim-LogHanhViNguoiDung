import ComparisonBarChart from './ComparisonBarChart.jsx';

export default function ClusterSizeChart({ profiles }) {
  return <div className="cluster-size-chart">
    <ComparisonBarChart data={profiles} dataKey="userCount" unit="người dùng" title="Số người dùng từng cụm" vertical />
  </div>;
}
