import React from 'react';
import { SystemHealthSection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Activity, Database, Server, Clock, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

interface SystemHealthWidgetProps {
  data: SystemHealthSection;
}

export const SystemHealthWidget: React.FC<SystemHealthWidgetProps> = ({ data }) => {
  const { backend_online, database_connected, database_latency_ms, last_successful_session_at, subsystems } = data;

  const getSubsystemBadge = (status: string) => {
    switch (status) {
      case 'available':
        return <Badge variant="success" size="sm">Available</Badge>;
      case 'insufficient':
        return <Badge variant="warning" size="sm">Insufficient Data</Badge>;
      case 'degraded':
        return <Badge variant="warning" size="sm">Degraded</Badge>;
      case 'unavailable':
      default:
        return <Badge variant="danger" size="sm">Unavailable</Badge>;
    }
  };

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>System Health & Subsystems Matrix</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              Live component connectivity and operational readiness across Phases 4–13
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge provenance={data.provenance} size="sm" />
          <Link
            to="/system-info"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Open full System Info"
          >
            <ExternalLink className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Core Connectivity Status Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2.5">
            <Server className={`h-4 w-4 ${backend_online ? 'text-emerald-400' : 'text-rose-400'}`} />
            <div>
              <div className="text-[11px] text-slate-400 font-medium">FastAPI Backend</div>
              <div className="text-xs font-semibold text-slate-200">
                {backend_online ? 'Online & Responsive' : 'Unreachable'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Database className={`h-4 w-4 ${database_connected ? 'text-emerald-400' : 'text-rose-400'}`} />
            <div>
              <div className="text-[11px] text-slate-400 font-medium">Database Persistence</div>
              <div className="text-xs font-semibold text-slate-200">
                {database_connected ? `Connected (${database_latency_ms.toFixed(1)}ms)` : 'Disconnected'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Clock className="h-4 w-4 text-cyan-400" />
            <div>
              <div className="text-[11px] text-slate-400 font-medium">Last Video Processing</div>
              <div className="text-xs font-semibold text-slate-200">
                {last_successful_session_at
                  ? new Date(last_successful_session_at).toLocaleString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : 'No runs recorded'}
              </div>
            </div>
          </div>
        </div>

        {/* Subsystems Matrix */}
        <div className="space-y-1.5">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
            Subsystem Operational Catalog
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {subsystems.map((sub) => (
              <div
                key={sub.phase}
                className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/60 hover:border-slate-700/60 transition-colors"
              >
                <div className="min-w-0 pr-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono text-cyan-400 font-semibold">P{sub.phase}</span>
                    <span className="text-xs font-medium text-slate-200 truncate">{sub.name}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 truncate mt-0.5" title={sub.note}>
                    {sub.note}
                  </p>
                </div>
                <div className="flex-shrink-0">{getSubsystemBadge(sub.status)}</div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
