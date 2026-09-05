import { Menu } from 'lucide-react';
import { StatusIndicator } from '@/components/StatusIndicator';
import { useBackendHealth } from '@/hooks/useBackendHealth';

export interface HeaderProps {
  onMenuToggle: () => void;
  title?: string;
}

export function Header({ onMenuToggle, title }: HeaderProps) {
  const { status, data, error, latencyMs, isChecking, checkHealth } = useBackendHealth();

  return (
    <header className="h-16 px-4 lg:px-8 border-b border-slate-800/80 bg-[#090d16]/80 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between">
      {/* Left side: Menu Toggle & Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 lg:hidden focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div>
          <h2 className="text-sm font-semibold text-slate-100 hidden sm:block">
            {title || 'Traffic Intelligence System'}
          </h2>
          <p className="text-[11px] text-slate-400 hidden md:block">
            Decisions & Analytics Command Platform
          </p>
        </div>
      </div>

      {/* Right side: Real Backend Health Indicator */}
      <div className="flex items-center gap-3">
        <StatusIndicator
          status={status}
          data={data}
          error={error}
          latencyMs={latencyMs}
          isChecking={isChecking}
          onRefresh={checkHealth}
          variant="compact"
        />
      </div>
    </header>
  );
}
