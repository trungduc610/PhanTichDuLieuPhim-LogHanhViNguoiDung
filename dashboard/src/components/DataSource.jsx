import { createContext, useContext, useEffect, useState } from 'react';
import { loadSource, isStale, displaySourceDate } from '../services/dataSource.js';
import { selectDataSource } from '../services/dashboardData.js';

const SourceContext = createContext(null);
export const useSource = () => useContext(SourceContext);

export function SourceGate({ children }) {
  const [state,setState] = useState({ status:'loading' });
  const [attempt,setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ status:'loading' });
    loadSource(controller.signal).then(source => {
      if (!controller.signal.aborted) {
        selectDataSource(source);
        setState({ status:'ready', source });
      }
    }).catch(error => {
      if (!controller.signal.aborted) setState({ status:'error', message:error.message });
    });
    return () => controller.abort();
  },[attempt]);
  if (state.status === 'loading') return <p className="status-panel" role="status">Đang xác minh nguồn dữ liệu…</p>;
  if (state.status === 'error') return <div className="status-panel error-panel" role="alert">
    <h2>Nguồn dữ liệu chưa được xác minh</h2><p>{state.message}</p>
    <button onClick={() => setAttempt(value => value + 1)}>Thử lại</button>
  </div>;
  return <SourceContext.Provider value={state.source}>{children}</SourceContext.Provider>;
}

export function DataScope({ syntheticLabel = 'Dữ liệu mô phỏng' }) {
  const source = useSource();
  if (!source) return null;
  return <div className="overview-scope" aria-label="Phạm vi dữ liệu">
    <span className="simulation-badge">{source.isSynthetic ? syntheticLabel : 'Dữ liệu thực tế'}</span>
    <span>{displaySourceDate(source.firstDate)}–{displaySourceDate(source.lastDate)}</span><span>Giờ Việt Nam · UTC+7</span>
  </div>;
}

export function SourceInfo() {
  const source = useSource();
  if (!source) return null;
  const verified = new Intl.DateTimeFormat('vi-VN', { dateStyle:'short', timeStyle:'short', timeZone:'Asia/Ho_Chi_Minh' }).format(new Date(source.verifiedAt));
  return <details className="source-info">
    <summary>{isStale(source) ? 'Snapshot cũ · ' : 'Snapshot đã xác minh · '}{verified}</summary>
    <p>Run phân tích: <code>{source.runId}</code> · Flume: <code>{source.flumeRunId}</code> · HDFS: <code>{source.hdfsRunId}</code>.</p>
    <p>Dữ liệu đã được kiểm tra trước khi đồng bộ; đây là kết quả theo lô, không cập nhật trực tiếp.</p>
    {isStale(source) && <p className="source-stale" role="status">Snapshot đã xác minh hơn {source.staleAfterHours} giờ trước. Cần chọn và đồng bộ run mới nếu muốn kết quả mới hơn.</p>}
  </details>;
}
