import { createContext, useContext, useEffect, useState } from 'react';
import { loadOverview } from '../services/dashboardData.js';
import { MissingDataError } from '../services/overviewMetrics.js';

export const DashboardContext = createContext(null);
export const useDashboardData = () => useContext(DashboardContext);

export function DashboardDataProvider({ children, loader = loadOverview }) {
  const [state, setState] = useState({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: 'loading' });
    loader(controller.signal).then((metrics) => {
      if (!controller.signal.aborted) setState({ status: 'ready', metrics });
    }).catch((error) => {
      if (!controller.signal.aborted) {
        setState({ status: error instanceof MissingDataError ? 'missing' : 'error', message: error.message });
      }
    });
    return () => controller.abort();
  }, [attempt, loader]);
  return <DashboardContext.Provider value={{ ...state, retry: () => setAttempt((value) => value + 1) }}>{children}</DashboardContext.Provider>;
}

export function DataState() {
  const state = useDashboardData();
  if (state.status === 'loading') return <p className="status-panel" role="status">Đang tải dữ liệu…</p>;
  if (state.status === 'ready') return null;
  return <div className="status-panel error-panel" role="alert">
    <h2>{state.status === 'missing' ? 'Thiếu dữ liệu' : 'Không thể đọc dữ liệu'}</h2>
    <p>{state.message}</p><button onClick={state.retry}>Thử lại</button>
  </div>;
}
