import { Link } from 'react-router-dom';
import IndependentDisclosure from './IndependentDisclosure.jsx';
import { useSource } from './DataSource.jsx';

// Nội dung mở ở vùng riêng, không làm cao card trong hàng biểu đồ.
export default function AnalysisExplanation({ title, target, help, technical, instructions, children }) {
  const source = useSource();
  return <div className="analysis-explanations">
    <IndependentDisclosure label="Giải thích dữ liệu" title={`Giải thích dữ liệu: ${title}`} target={target}>
      <p>{help}</p>{children}
      <details className="technical-definition"><summary>Chi tiết kỹ thuật</summary><p>{technical}</p><p>Run đã xác minh: <code>{source?.runId}</code>. Dashboard đọc kết quả theo lô, không chạy lại Spark.</p></details>
    </IndependentDisclosure>
    <IndependentDisclosure label="Hướng dẫn thao tác" title={`Hướng dẫn thao tác: ${title}`} target={target}>
      <p>{instructions}</p>
    </IndependentDisclosure>
  </div>;
}

export function AnalysisRelatedLinks({ links }) {
  return <div className="analysis-related" role="navigation" aria-label="Phân tích liên quan">
    <span>Khám phá thêm</span>{links.map(([to,label]) => <Link key={to} to={to}>{label} →</Link>)}
  </div>;
}
