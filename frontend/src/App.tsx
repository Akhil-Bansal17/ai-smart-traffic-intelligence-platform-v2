import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from '@/layouts/Layout';
import { DashboardPage } from '@/pages/DashboardPage';
import { VideoAnalysisPage } from '@/pages/VideoAnalysisPage';
import { LiveMonitoringPage } from '@/pages/LiveMonitoringPage';
import { TrafficAnalyticsPage } from '@/pages/TrafficAnalyticsPage';
import { HistoricalAnalyticsPage } from '@/pages/HistoricalAnalyticsPage';
import { PredictionsPage } from '@/pages/PredictionsPage';
import { SignalOptimizationPage } from '@/pages/SignalOptimizationPage';
import { EmergencySimulationPage } from '@/pages/EmergencySimulationPage';
import { HistoryPage } from '@/pages/HistoryPage';
import { ReportsPage } from '@/pages/ReportsPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { SystemInfoPage } from '@/pages/SystemInfoPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="video-analysis" element={<VideoAnalysisPage />} />
          <Route path="live-monitoring" element={<LiveMonitoringPage />} />
          <Route path="traffic-analytics" element={<TrafficAnalyticsPage />} />
          <Route path="historical-analytics" element={<HistoricalAnalyticsPage />} />
          <Route path="predictions" element={<PredictionsPage />} />
          <Route path="signal-optimization" element={<SignalOptimizationPage />} />
          <Route path="emergency-simulation" element={<EmergencySimulationPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="system-info" element={<SystemInfoPage />} />
          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}


export default App;
