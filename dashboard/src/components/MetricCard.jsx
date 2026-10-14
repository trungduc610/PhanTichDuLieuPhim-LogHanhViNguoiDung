const numberFormat = new Intl.NumberFormat('vi-VN');

export default function MetricCard({ title, value, description, unit }) {
  return (
    <article className="metric-card">
      <h2>{title}</h2>
      <p className="metric-value">{numberFormat.format(value)}{unit && <span className="metric-unit"> {unit}</span>}</p>
      <p className="metric-description">{description}</p>
    </article>
  );
}
