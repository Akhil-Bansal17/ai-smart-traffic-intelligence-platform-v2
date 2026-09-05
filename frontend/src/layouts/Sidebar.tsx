import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Video,
  BarChart3,
  TrendingUp,
  Sliders,
  Siren,
  History,
  Settings,
  Info,
  X,
  Radio,
} from 'lucide-react';
import { cn } from '@/utils/cn';

export interface NavItem {
  name: string;
  path: string;
  icon: React.ElementType;
  phaseTag?: string;
  isSimulation?: boolean;
}

const mainNavItems: NavItem[] = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Video Analysis', path: '/video-analysis', icon: Video, phaseTag: 'Ph 4-8' },
  { name: 'Traffic Analytics', path: '/traffic-analytics', icon: BarChart3, phaseTag: 'Ph 9' },
  { name: 'Predictions', path: '/predictions', icon: TrendingUp, phaseTag: 'Ph 13' },
  { name: 'Signal Optimization', path: '/signal-optimization', icon: Sliders, phaseTag: 'Ph 14', isSimulation: true },
  { name: 'Emergency Simulation', path: '/emergency-simulation', icon: Siren, phaseTag: 'Ph 15', isSimulation: true },
  { name: 'History', path: '/history', icon: History, phaseTag: 'Ph 12' },
];

const secondaryNavItems: NavItem[] = [
  { name: 'System Info', path: '/system-info', icon: Info },
  { name: 'Settings', path: '/settings', icon: Settings, phaseTag: 'Ph 16' },
];

export interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          'fixed top-0 bottom-0 left-0 z-50 w-64 bg-[#0c1322] border-r border-slate-800/80 flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:z-auto',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Brand Header */}
        <div className="h-16 px-5 flex items-center justify-between border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-cyan-600/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-sm">
              <Radio className="h-4 w-4 text-cyan-400" />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-100 flex items-center gap-1.5">
                <span>Traffic AI</span>
                <span className="text-[10px] text-cyan-400 font-mono font-semibold px-1 py-0.2 bg-cyan-950/80 border border-cyan-800/60 rounded">
                  v0.1
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium truncate max-w-[130px]">
                Intelligence Platform
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800/80 lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Groups */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {/* Main Navigation */}
          <div>
            <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Platform Modules
            </div>
            <nav className="space-y-1">
              {mainNavItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => {
                    if (window.innerWidth < 1024) onClose();
                  }}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all group select-none',
                      isActive
                        ? 'bg-cyan-600/15 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-950/50'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <div className="flex items-center gap-2.5">
                        <item.icon
                          className={cn(
                            'h-4 w-4 transition-colors',
                            isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-slate-200'
                          )}
                        />
                        <span>{item.name}</span>
                      </div>

                      <div className="flex items-center gap-1">
                        {item.phaseTag && !isActive && (
                          <span className="text-[9px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/50">
                            {item.phaseTag}
                          </span>
                        )}
                        {item.isSimulation && (
                          <span className="text-[8px] font-mono font-semibold text-indigo-300 bg-indigo-950/70 border border-indigo-800/50 px-1 py-0.2 rounded">
                            SIM
                          </span>
                        )}
                      </div>
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </div>

          {/* System Navigation */}
          <div>
            <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Configuration & Info
            </div>
            <nav className="space-y-1">
              {secondaryNavItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => {
                    if (window.innerWidth < 1024) onClose();
                  }}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all group select-none',
                      isActive
                        ? 'bg-cyan-600/15 text-cyan-300 border border-cyan-500/30'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <div className="flex items-center gap-2.5">
                        <item.icon
                          className={cn(
                            'h-4 w-4 transition-colors',
                            isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-slate-200'
                          )}
                        />
                        <span>{item.name}</span>
                      </div>

                      {item.phaseTag && !isActive && (
                        <span className="text-[9px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/50">
                          {item.phaseTag}
                        </span>
                      )}
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
          <div className="flex items-center justify-between text-[11px] text-slate-400 px-2">
            <span>Phase 3 Foundation</span>
            <span className="font-mono text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/50 px-1.5 py-0.5 rounded">
              Ready
            </span>
          </div>
        </div>
      </aside>
    </>
  );
}
