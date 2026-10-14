import Icon from './Icon.jsx';
const numberFormat = new Intl.NumberFormat('vi-VN');

export default function MetricCard({ title, value, description, unit, icon }) {
  return (
    <article className="metric-card">
      {icon ? <div className="metric-topline"><h2>{title}</h2><span className="metric-icon"><Icon name={icon} size={18} /></span></div> : <h2>{title}</h2>}
      <p className="metric-value">{numberFormat.format(value)}{unit && <span className="metric-unit"> {unit}</span>}</p>
      <p className="metric-description">{description}</p>
    </article>
  );
}
