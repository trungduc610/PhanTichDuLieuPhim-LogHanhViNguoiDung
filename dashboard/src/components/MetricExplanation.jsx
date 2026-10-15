import IndependentDisclosure from './IndependentDisclosure.jsx';

// Giữ nút details trong card; nội dung dài được đưa ra vùng riêng ngoài grid.
export default function MetricExplanation({ definition, target }) {
  return <IndependentDisclosure title={definition.title} label="Giải thích" className="metric-explanation" target={target}>
      <p>{definition.meaning}</p>
      <p><strong>Cách tính: </strong>{definition.calculation}</p>
      <p><strong>Lưu ý: </strong>{definition.caution}</p>
      <details className="technical-definition"><summary>Chi tiết kỹ thuật</summary><p>{definition.technical}</p></details>
  </IndependentDisclosure>;
}
