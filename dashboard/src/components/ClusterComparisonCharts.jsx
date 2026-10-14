import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList, Legend } from 'recharts';
import { number, axisNumber } from '../services/formatNumbers.js';

const metrics = [
  { key: 'avgPlayCount', title: 'Sự kiện play trung bình', unit: 'sự kiện/người dùng' },
  { key: 'avgDistinctMovies', title: 'Phim khác nhau trung bình', unit: 'phim/người dùng' },
  { key: 'avgSessionCount', title: 'Số phiên trung bình', unit: 'phiên/người dùng' },
];
const colors = ['#3865b5', '#287b79'];

export default function ClusterComparisonCharts({ profiles }) {
  return <div className="cluster-comparisons">
    <p className="chart-note">Mỗi biểu đồ dùng một trục riêng và một đơn vị. So sánh các cụm trong từng chỉ số; độ dài thanh giữa các biểu đồ không dùng để so sánh các chỉ số khác đơn vị.</p>
    <div className="cluster-comparison-grid">
      {metrics.map(metric => {
        const row = Object.fromEntries(profiles.map(profile => [profile.label, profile[metric.key]]));
        return <section className="cluster-comparison" key={metric.key} data-comparison={metric.key} aria-label={metric.title}>
          <h3>{metric.title}</h3><p className="chart-unit">Đơn vị: {metric.unit}</p>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[row]} layout="vertical" margin={{ top: 8, right: 70, bottom: 8, left: 4 }} accessibilityLayer>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tickFormatter={axisNumber} tick={{ fontSize: 11 }} tickCount={3} />
                <YAxis type="category" hide />
                <Tooltip formatter={(value, label) => [`${number(value)} ${metric.unit}`, label]} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {profiles.map((profile, index) => <Bar key={profile.cluster} dataKey={profile.label} fill={colors[index % colors.length]} isAnimationActive={false} radius={[0, 4, 4, 0]} maxBarSize={36}>
                  <LabelList dataKey={profile.label} position="right" formatter={number} fontSize={11} />
                </Bar>)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>;
      })}
    </div>
  </div>;
}
