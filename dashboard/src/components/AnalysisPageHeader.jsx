import { DataScope } from './DataSource.jsx';
export default function AnalysisPageHeader({ title, description, detailed = false }) {
  return <header className="overview-heading">
    <p className="eyebrow">DỮ LIỆU PHIM & HÀNH VI</p>
    <h1>{title}</h1><p className="intro">{description}</p>
    <DataScope syntheticLabel={detailed ? 'Log hành vi mô phỏng' : undefined} />
    {detailed && <p className="analysis-origin">Thông tin phim: MovieLens · Kết quả xử lý theo lô</p>}
  </header>;
}
