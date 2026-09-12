import { useEffect, useState, useCallback } from 'react';
import { getDashboardSummary } from '@/api/dashboard';
import { DashboardSummaryResponse } from '@/types/dashboard';
import { SystemHealthWidget } from '@/components/dashboard/SystemHealthWidget';
import { TrafficOverviewWidget } from '@/components/dashboard/TrafficOverviewWidget';
import { VehicleCompositionWidget } from '@/components/dashboard/VehicleCompositionWidget';
import { TrafficFlowChartWidget } from '@/components/dashboard/TrafficFlowChartWidget';
import { LaneDensityWidget } from '@/components/dashboard/LaneDensityWidget';
import { AlertsWidget } from '@/components/dashboard/AlertsWidget';
import { PredictionAvailabilityWidget } from '@/components/dashboard/PredictionAvailabilityWidget';
import { SignalOptimizationWidget } from '@/components/dashboard/SignalOptimizationWidget';
import { EmergencyCorridorWidget } from '@/components/dashboard/EmergencyCorridorWidget';
import { HistoricalSessionsWidget } from '@/components/dashboard/HistoricalSessionsWidget';
import { DataProvenancePanel } from '@/components/dashboard/DataProvenancePanel';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import {
  RotateCw,
  ShieldCheck,
  Radio,
  Layers,
  Sparkles,
  TrafficCone,
  ShieldAlert,
  History,
  Video,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | undefined>(undefined);

  const loadSummary = useCallback(async (sessionId?: string, isManualRefresh = false) => {
    if (isManualRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const res = await getDashboardSummary(sessionId);
      setData(res);
      if (!sessionId && res.traffic_overview.active_session_id) {
        setSelectedSessionId(res.traffic_overview.active_session_id);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch unified dashboard intelligence summary.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadSummary(selectedSessionId);
  }, [loadSummary, selectedSessionId]);

  const handleSelectSession = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    loadSummary(sessionId);
  };

  if (loading && !data) {
    return (
      <div className="py-16">
        <LoadingState message="Aggregating system-wide traffic intelligence & decision support metrics..." />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="py-16">
        <ErrorState
          title="Dashboard Intelligence Unavailable"
          message={error}
          onRetry={() => loadSummary(selectedSessionId)}
        />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Dashboard Command Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-[#0a0f1d] to-cyan-950/30 shadow-xl shadow-black/40">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Traffic Intelligence Command</span>
            </h1>
            <Badge variant="info" size="sm">Phase 14</Badge>
            <Badge variant="success" size="sm" className="hidden sm:inline-flex items-center gap-1 font-mono">
              <ShieldCheck className="h-3 w-3" />
              Read-Only Aggregator
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
            Unified Decision-Support Dashboard synthesizing verified outputs across Computer Vision (Phases 4–10),
            Predictive Machine Learning (Phase 11), Traffic Signal Optimization (Phase 12), and Coordinated Emergency
            Corridor Simulation (Phase 13).
          </p>
        </div>

        {/* Top Control Bar: Manual Refresh & Session Switcher */}
        <div className="flex items-center gap-2.5 self-start md:self-auto flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadSummary(selectedSessionId, true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 bg-slate-900/80 border-slate-700 hover:bg-slate-800 text-slate-200"
            title="Read latest aggregated records (strictly read-only; never triggers processing or simulations)"
          >
            <RotateCw className={`h-3.5 w-3.5 text-cyan-400 ${refreshing ? 'animate-spin' : ''}`} />
            <span>{refreshing ? 'Refreshing...' : 'Refresh Data'}</span>
          </Button>

          <Link
            to="/system-info"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <Radio className="h-3.5 w-3.5 text-cyan-400" />
            <span>Telemetry</span>
          </Link>
        </div>
      </div>

      {/* Section 1: System Health & Subsystems Matrix (Full Width) */}
      <SystemHealthWidget data={data.system_health} />

      {/* Row 2: Traffic Overview (2/3 width) + Vehicle Class Composition (1/3 width) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TrafficOverviewWidget data={data.traffic_overview} />
        </div>
        <div className="lg:col-span-1">
          <VehicleCompositionWidget data={data.vehicle_composition} />
        </div>
      </div>

      {/* Row 3: Traffic Flow Discrete Time-Series (1/2 width) + Lane Density Intelligence (1/2 width) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrafficFlowChartWidget data={data.traffic_flow_metrics} />
        <LaneDensityWidget data={data.lane_density} />
      </div>

      {/* Row 4: Phase 15 Traffic Anomaly & Congestion Incident Detection (Full Width) */}
      <AlertsWidget
        activeSessionId={selectedSessionId || data.traffic_overview.active_session_id}
        videoFilename={data.traffic_overview.video_filename}
        isSyntheticSession={data.traffic_overview.provenance.state === 'SYNTHETIC'}
      />

      {/* Row 5: Prediction Availability & ML Readiness (Full Width) */}
      <PredictionAvailabilityWidget data={data.prediction_availability} />

      {/* Row 5: Signal Optimization Simulation (1/2 width) + Emergency Corridor Simulation (1/2 width) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SignalOptimizationWidget data={data.signal_optimization} />
        <EmergencyCorridorWidget data={data.emergency_corridor} />
      </div>

      {/* Row 6: Historical Analysis Sessions (1/2 width) + Data Provenance & Trust Boundary Panel (1/2 width) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <HistoricalSessionsWidget
          data={data.recent_history}
          onSelectSession={handleSelectSession}
          activeSessionId={selectedSessionId || data.traffic_overview.active_session_id}
        />
        <DataProvenancePanel data={data.data_provenance} />
      </div>

      {/* Module Direct Navigation Shortcuts */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Layers className="h-3.5 w-3.5 text-cyan-400" />
          <span>Platform Subsystem Quick Jump</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          <Link
            to="/video-analysis"
            className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-900 transition-all text-center group"
          >
            <Video className="h-4 w-4 text-cyan-400 mx-auto mb-1 group-hover:scale-110 transition-transform" />
            <div className="text-xs font-medium text-slate-200 group-hover:text-cyan-300">CV Pipeline</div>
          </Link>

          <Link
            to="/traffic-analytics"
            className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900 transition-all text-center group"
          >
            <Layers className="h-4 w-4 text-emerald-400 mx-auto mb-1 group-hover:scale-110 transition-transform" />
            <div className="text-xs font-medium text-slate-200 group-hover:text-emerald-300">Analytics</div>
          </Link>

          <Link
            to="/predictions"
            className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-900 transition-all text-center group"
          >
            <Sparkles className="h-4 w-4 text-cyan-400 mx-auto mb-1 group-hover:scale-110 transition-transform" />
            <div className="text-xs font-medium text-slate-200 group-hover:text-cyan-300">ML Forecast</div>
          </Link>

          <Link
            to="/signal-optimization"
            className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900 transition-all text-center group"
          >
            <TrafficCone className="h-4 w-4 text-indigo-400 mx-auto mb-1 group-hover:scale-110 transition-transform" />
            <div className="text-xs font-medium text-slate-200 group-hover:text-indigo-300">Signal Opt</div>
          </Link>

          <Link
            to="/emergency-simulation"
            className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-rose-500/50 hover:bg-slate-900 transition-all text-center group"
          >
            <ShieldAlert className="h-4 w-4 text-rose-400 mx-auto mb-1 group-hover:scale-110 transition-transform" />
            <div className="text-xs font-medium text-slate-200 group-hover:text-rose-300">Emergency Cor.</div>
          </Link>

          <Link
            to="/history"
            className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-slate-600 hover:bg-slate-900 transition-all text-center group"
          >
            <History className="h-4 w-4 text-slate-400 mx-auto mb-1 group-hover:scale-110 transition-transform" />
            <div className="text-xs font-medium text-slate-200 group-hover:text-white">Full History</div>
          </Link>
        </div>
      </div>
    </div>
  );
}
