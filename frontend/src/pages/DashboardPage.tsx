import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatusIndicator } from '@/components/StatusIndicator';
import { useBackendHealth } from '@/hooks/useBackendHealth';
import {
  Video,
  Car,
  Activity,
  Gauge,
  ArrowUpRight,
  Radio,
  Clock,
  Sparkles,
  Layers,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export function DashboardPage() {
  const { status, data, error, latencyMs, isChecking, checkHealth } = useBackendHealth();

  return (
    <div className="space-y-6">
      {/* Welcome & Overview Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-[#0c1322] to-cyan-950/20 shadow-lg shadow-black/30">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Traffic Intelligence Command
            </h1>
            <Badge variant="info" size="sm">Phase 3</Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
            Welcome to the AI Smart Traffic Intelligence Platform. This dashboard aggregates live CV detection feeds,
            congestion scoring, predictive models, and decision-support simulation engines.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto">
          <Link
            to="/system-info"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <Radio className="h-3.5 w-3.5 text-cyan-400" />
            <span>System Status</span>
          </Link>
        </div>
      </div>

      {/* Backend Connectivity Status Panel */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Radio className="h-3.5 w-3.5 text-cyan-400" />
            <span>Backend Integration Status</span>
          </h3>
          <span className="text-[11px] text-slate-400">Live API Health Monitor</span>
        </div>
        <StatusIndicator
          status={status}
          data={data}
          error={error}
          latencyMs={latencyMs}
          isChecking={isChecking}
          onRefresh={checkHealth}
          variant="detailed"
        />
      </div>

      {/* KPI Cards Grid (Labeled Demo Data) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-cyan-400" />
            <span>Key Traffic Indicators</span>
          </h3>
          <Badge variant="warning" size="sm">
            <Clock className="h-3 w-3 mr-1" />
            Demo data (Static Shell)
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Active Ingestion */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs text-slate-400">Video Sources</CardTitle>
              <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
                <Video className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-slate-100">0</div>
              <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                <span>Phase 4: Video Ingestion</span>
              </p>
            </CardContent>
          </Card>

          {/* Card 2: Vehicles Detected */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs text-slate-400">Vehicles Counted</CardTitle>
              <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800/50 text-emerald-400">
                <Car className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-slate-100">--</div>
              <p className="text-[11px] text-slate-400 mt-1">
                <span>Phase 7: Counting Pipeline</span>
              </p>
            </CardContent>
          </Card>

          {/* Card 3: Congestion Index */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs text-slate-400">Congestion Index</CardTitle>
              <div className="p-2 rounded-lg bg-amber-950/60 border border-amber-800/50 text-amber-400">
                <Gauge className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-slate-100">-- / 100</div>
              <p className="text-[11px] text-slate-400 mt-1">
                <span>Phase 9: Analytics Engine</span>
              </p>
            </CardContent>
          </Card>

          {/* Card 4: Predictions Model */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs text-slate-400">ML Predictions</CardTitle>
              <div className="p-2 rounded-lg bg-indigo-950/60 border border-indigo-800/50 text-indigo-400">
                <Sparkles className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-slate-100">Standby</div>
              <p className="text-[11px] text-slate-400 mt-1">
                <span>Phase 13: 5–15 min Horizon</span>
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Module Overview Grid */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2 px-1">
          <Layers className="h-3.5 w-3.5 text-cyan-400" />
          <span>Platform Roadmaps & Planned Modules</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/video-analysis"
            className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-cyan-500/40 hover:bg-slate-900/90 transition-all group"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-semibold text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/60">
                CV Pipeline
              </span>
              <ArrowUpRight className="h-4 w-4 text-slate-400 group-hover:text-cyan-400 transition-colors" />
            </div>
            <h4 className="text-sm font-semibold text-white group-hover:text-cyan-300 transition-colors">
              Video Ingestion & Tracking
            </h4>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Ultralytics YOLO detection, ByteTrack multi-object tracking, and lane boundary crossing.
            </p>
          </Link>

          <Link
            to="/traffic-analytics"
            className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-cyan-500/40 hover:bg-slate-900/90 transition-all group"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-semibold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/60">
                Analytics
              </span>
              <ArrowUpRight className="h-4 w-4 text-slate-400 group-hover:text-emerald-400 transition-colors" />
            </div>
            <h4 className="text-sm font-semibold text-white group-hover:text-emerald-300 transition-colors">
              Flow & Density Engine
            </h4>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Lane-level density calculations, directional distribution, and explainable 0–100 congestion metrics.
            </p>
          </Link>

          <Link
            to="/signal-optimization"
            className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-indigo-500/40 hover:bg-slate-900/90 transition-all group"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-semibold text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-800/60">
                Decision Support
              </span>
              <ArrowUpRight className="h-4 w-4 text-slate-400 group-hover:text-indigo-400 transition-colors" />
            </div>
            <h4 className="text-sm font-semibold text-white group-hover:text-indigo-300 transition-colors">
              Simulation Engines
            </h4>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Advisory green-time optimization simulations and priority emergency corridor pathing.
            </p>
          </Link>
        </div>
      </div>
    </div>
  );
}
