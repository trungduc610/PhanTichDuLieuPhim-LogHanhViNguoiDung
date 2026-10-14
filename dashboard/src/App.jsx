import { Route, Routes, Link } from 'react-router-dom';
import AppNavigation from './components/AppNavigation.jsx';
import OverviewPage from './pages/OverviewPage.jsx';
import AnalysisPage from './pages/AnalysisPage.jsx';
import GenresPage from './pages/GenresPage.jsx';
import WatchDurationPage from './pages/WatchDurationPage.jsx';
import CombinedAnalysisPage from './pages/CombinedAnalysisPage.jsx';
import ClusteringPage from './pages/ClusteringPage.jsx';
import { DashboardDataProvider } from './components/DashboardData.jsx';

export default function App() {
  return <DashboardDataProvider><DashboardLayout /></DashboardDataProvider>;
}

export function DashboardLayout() {
  return (
    <div className="app-layout">
      <AppNavigation />
      <main className="main-content">
        <aside className="data-note scope-note" aria-label="Phạm vi dữ liệu">
          <strong>Dữ liệu hành vi mô phỏng · 01/09/2026–30/09/2026 · Giờ Việt Nam (UTC+7)</strong>
          <p>Kết quả mô tả dữ liệu mô phỏng, không đại diện cho sở thích người xem thật.</p>
        </aside>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/phim" element={<AnalysisPage kind="movies" />} />
          <Route path="/the-loai" element={<GenresPage />} />
          <Route path="/hanh-vi" element={<AnalysisPage kind="actions" />} />
          <Route path="/thoi-gian" element={<AnalysisPage kind="hourly" />} />
          <Route path="/thoi-luong" element={<WatchDurationPage />} />
          <Route path="/ket-hop" element={<CombinedAnalysisPage />} />
          <Route path="/phan-cum" element={<ClusteringPage />} />
          <Route path="*" element={<><h1>Không tìm thấy trang</h1><Link to="/">Về Tổng quan</Link></>} />
        </Routes>
      </main>
    </div>
  );
}
