import { Route, Routes, Link } from 'react-router-dom';
import AppNavigation from './components/AppNavigation.jsx';
import RouteFocus from './components/RouteFocus.jsx';
import OverviewPage from './pages/OverviewPage.jsx';
import AnalysisPage from './pages/AnalysisPage.jsx';
import GenresPage from './pages/GenresPage.jsx';
import WatchDurationPage from './pages/WatchDurationPage.jsx';
import CombinedAnalysisPage from './pages/CombinedAnalysisPage.jsx';
import ClusteringPage from './pages/ClusteringPage.jsx';
import { DashboardDataProvider } from './components/DashboardData.jsx';
import { SourceGate, SourceInfo } from './components/DataSource.jsx';

export default function App() {
  return <SourceGate><DashboardDataProvider><DashboardLayout /></DashboardDataProvider></SourceGate>;
}

export function DashboardLayout() {
  return (
    <div className="app-layout">
      <a className="skip-link" href="#main-content">Đến nội dung chính</a>
      <AppNavigation />
      <main id="main-content" className="main-content" tabIndex={-1}>
        <SourceInfo />
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
        <RouteFocus />
      </main>
    </div>
  );
}
