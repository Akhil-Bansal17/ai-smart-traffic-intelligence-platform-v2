import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

const routeTitleMap: Record<string, string> = {
  '/': 'Platform Dashboard',
  '/video-analysis': 'Video Ingestion & Analysis',
  '/traffic-analytics': 'Traffic Analytics & Flow Engine',
  '/predictions': 'Short-Horizon Traffic Predictions',
  '/signal-optimization': 'Signal Timing Optimization (Simulation)',
  '/emergency-simulation': 'Emergency Corridor Simulation',
  '/history': 'Historical Traffic Analytics',
  '/settings': 'Platform Settings & Configuration',
  '/system-info': 'System Architecture & Health Diagnostics',
};

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const currentTitle = routeTitleMap[location.pathname] || 'Traffic Intelligence Platform';

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col lg:flex-row">
      {/* Navigation Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <Header
          onMenuToggle={() => setSidebarOpen((prev) => !prev)}
          title={currentTitle}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
