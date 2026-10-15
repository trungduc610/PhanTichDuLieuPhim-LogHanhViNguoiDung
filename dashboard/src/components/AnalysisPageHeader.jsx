import { DataScope } from './DataSource.jsx';
export default function AnalysisPageHeader({ title, description }) {
  return <header className="overview-heading">
    <p className="eyebrow">DỮ LIỆU PHIM & HÀNH VI</p>
    <h1>{title}</h1><p className="intro">{description}</p>
    <DataScope />
  </header>;
}
