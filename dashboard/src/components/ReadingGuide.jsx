import Icon from './Icon.jsx';

export default function ReadingGuide({ title = 'Cách đọc số liệu', children }) {
  return <details className="reading-guide">
    <summary><Icon name="info" size={16} />{title}</summary>
    <div>{children}</div>
  </details>;
}
