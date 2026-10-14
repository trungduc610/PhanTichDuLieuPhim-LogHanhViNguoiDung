export default function AnalysisPageHeader({ title, description }) {
  return <header className="overview-heading">
    <p className="eyebrow">DỮ LIỆU PHIM & HÀNH VI</p>
    <h1>{title}</h1><p className="intro">{description}</p>
    <div className="overview-scope" aria-label="Phạm vi dữ liệu">
      <span className="simulation-badge">Dữ liệu mô phỏng</span>
      <span>01/09/2026–30/09/2026</span><span>Giờ Việt Nam · UTC+7</span>
    </div>
  </header>;
}
