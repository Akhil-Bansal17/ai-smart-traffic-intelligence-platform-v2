import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  Eye,
  FileText,
  History,
  LineChart,
  Radio,
  RefreshCw,
  RotateCw,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Sliders,
  TrendingUp,
  Video,
  WifiOff,
  X,
  ChevronRight,
  Gauge,
  Sparkles,
  Flame,
} from 'lucide-react';

import {
  getOperationsOverview,
  updateOperationsIncidentStatus,
  getOperationsHistoricalContext,
} from '@/api/operations';
import {
  CameraHealthStatus,
  OperationsHistoricalContextResponse,
  OperationsIncidentItem,
  OperationsOverviewResponse,
} from '@/types/operations';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { getApiBaseUrl } from '@/config/env';

export function OperationsCenterPage() {

  // Primary operational state
  const [overview, setOverview] = useState<OperationsOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Polling configuration
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const pollIntervalMs = 5000;
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Incident Filtering & Actions
  const [incidentFilterStatus, setIncidentFilterStatus] = useState<string>('all');
  const [incidentFilterSeverity, setIncidentFilterSeverity] = useState<string>('all');
  const [activeModalIncident, setActiveModalIncident] = useState<OperationsIncidentItem | null>(null);
  const [statusActionTarget, setStatusActionTarget] = useState<'acknowledged' | 'resolved' | null>(null);
  const [operatorNote, setOperatorNote] = useState<string>('');
  const [actionSubmitting, setActionSubmitting] = useState<boolean>(false);

  // Detail inspection modal
  const [detailIncident, setDetailIncident] = useState<OperationsIncidentItem | null>(null);

  // Historical Context Drawer
  const [selectedSourceForContext, setSelectedSourceForContext] = useState<string | null>(null);
  const [historicalContext, setHistoricalContext] = useState<OperationsHistoricalContextResponse | null>(null);
  const [loadingContext, setLoadingContext] = useState<boolean>(false);

  // Timeline Filtering
  const [timelineFilter, setTimelineFilter] = useState<string>('all');

  // Fetch overview data
  const fetchOverview = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true);
    try {
      const data = await getOperationsOverview();
      setOverview(data);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch operations overview:', err);
      if (!overview) {
        setError(err?.message || 'Failed to connect to Operations Center backend.');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [overview]);

  // Initial load
  useEffect(() => {
    fetchOverview(false);
  }, []);

  // Coordinated auto-polling loop
  useEffect(() => {
    if (!autoRefresh) {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      return;
    }

    pollTimerRef.current = setInterval(() => {
      fetchOverview(true);
    }, pollIntervalMs);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [autoRefresh, fetchOverview]);

  // Load historical context when source is selected
  useEffect(() => {
    if (!selectedSourceForContext) {
      setHistoricalContext(null);
      return;
    }

    const loadContext = async () => {
      setLoadingContext(true);
      try {
        const res = await getOperationsHistoricalContext(selectedSourceForContext, '7d');
        setHistoricalContext(res);
      } catch (err) {
        console.error('Failed to load historical context:', err);
      } finally {
        setLoadingContext(false);
      }
    };

    loadContext();
  }, [selectedSourceForContext]);

  // Handle status update (acknowledge or resolve)
  const handleUpdateStatusSubmit = async () => {
    if (!activeModalIncident || !statusActionTarget) return;
    setActionSubmitting(true);
    try {
      await updateOperationsIncidentStatus(activeModalIncident.id, {
        status: statusActionTarget,
        note: operatorNote.trim() || undefined,
      });
      setActiveModalIncident(null);
      setStatusActionTarget(null);
      setOperatorNote('');
      await fetchOverview(true);
    } catch (err: any) {
      alert(`Error updating incident: ${err?.message || 'Unknown error'}`);
    } finally {
      setActionSubmitting(false);
    }
  };

  // Helper for camera health badge
  const renderHealthBadge = (health: CameraHealthStatus) => {
    switch (health) {
      case 'ONLINE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-700/60 shadow-sm shadow-emerald-950">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            ONLINE
          </span>
        );
      case 'CONNECTING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-700/60 animate-pulse">
            <RotateCw className="h-3 w-3 animate-spin text-cyan-400" />
            CONNECTING
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-950/80 text-amber-300 border border-amber-700/60 shadow-sm shadow-amber-950">
            <AlertTriangle className="h-3 w-3 text-amber-400" />
            DEGRADED
          </span>
        );
      case 'OFFLINE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-900 text-slate-400 border border-slate-700/50">
            <WifiOff className="h-3 w-3 text-slate-500" />
            OFFLINE
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-900 text-zinc-400 border border-zinc-700/50">
            UNKNOWN
          </span>
        );
    }
  };

  // Helper for incident severity badge
  const renderSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-rose-950 text-rose-300 border border-rose-600 animate-pulse">
            <Flame className="h-3 w-3 text-rose-400" />
            CRITICAL
          </span>
        );
      case 'high':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-rose-950/70 text-rose-300 border border-rose-800">
            HIGH
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-950/70 text-amber-300 border border-amber-800">
            MEDIUM
          </span>
        );
      case 'low':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-950/70 text-blue-300 border border-blue-800">
            LOW
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-800 text-slate-300">
            {severity.toUpperCase()}
          </span>
        );
    }
  };

  // Helper for Provenance Badge
  const renderProvenanceBadge = (prov?: OperationsOverviewResponse['provenance_summary']) => {
    if (!prov) return null;
    const label = prov.provenance_label;
    if (label === 'REAL DATA') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-600/80">
          <ShieldCheck className="h-3 w-3 text-emerald-400" />
          REAL DATA
        </span>
      );
    }
    if (label === 'MIXED') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-950/80 text-amber-300 border border-amber-600/80">
          <AlertTriangle className="h-3 w-3 text-amber-400" />
          MIXED PROVENANCE
        </span>
      );
    }
    if (label === 'TEST FIXTURE') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-950/80 text-purple-300 border border-purple-600/80">
          <Sparkles className="h-3 w-3 text-purple-400" />
          TEST FIXTURE
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-900 text-slate-400 border border-slate-700">
        {label}
      </span>
    );
  };

  // Filtered incidents
  const filteredIncidents = (overview?.active_incidents || []).filter((inc) => {
    if (incidentFilterStatus !== 'all' && inc.status !== incidentFilterStatus) return false;
    if (incidentFilterSeverity !== 'all' && inc.severity !== incidentFilterSeverity) return false;
    return true;
  });

  // Filtered timeline
  const filteredTimeline = (overview?.timeline || []).filter((ev) => {
    if (timelineFilter !== 'all' && ev.event_type !== timelineFilter) return false;
    return true;
  });

  if (loading && !overview) {
    return <LoadingState message="Initializing Unified Traffic Operations Center..." />;
  }

  if (error && !overview) {
    return (
      <ErrorState
        title="Operations Center Offline"
        message={error}
        onRetry={() => fetchOverview(false)}
      />
    );
  }

  const lastUpdatedFormatted = overview?.timestamp
    ? new Date(overview.timestamp).toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short',
      })
    : '--:--:--';

  return (
    <div className="space-y-6 pb-12 animate-fadeIn">
      {/* 1. Header Command Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 bg-[#0e1726]/90 border border-slate-800/80 rounded-xl p-4 lg:p-6 backdrop-blur-md shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-cyan-600/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-lg shadow-cyan-950/60">
              <ShieldAlert className="h-5 w-5 text-cyan-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-white tracking-wide">
                  Unified Traffic Operations Center
                </h1>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-cyan-950/90 text-cyan-300 border border-cyan-800/60">
                  PHASE 23
                </span>
                {renderProvenanceBadge(overview?.provenance_summary)}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Live Monitoring • Incident Response • Decision Intelligence • Fleet Telemetry
              </p>
            </div>
          </div>
        </div>

        {/* Polling & Refresh Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
            <Clock className="h-3.5 w-3.5 text-slate-400" />
            <span>Last updated:</span>
            <span className="font-mono text-cyan-300 font-semibold">{lastUpdatedFormatted}</span>
          </div>

          {/* Auto Refresh Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
              autoRefresh
                ? 'bg-cyan-950/60 text-cyan-300 border-cyan-800/60 hover:bg-cyan-900/40'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
            }`}
            title={autoRefresh ? 'Auto-refresh active (5s)' : 'Auto-refresh paused'}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                autoRefresh ? 'bg-cyan-400 animate-pulse' : 'bg-slate-500'
              }`}
            />
            {autoRefresh ? 'Live Polling (5s)' : 'Polling Paused'}
          </button>

          {/* Manual Refresh */}
          <Button
            size="sm"
            variant="outline"
            onClick={() => fetchOverview(false)}
            disabled={refreshing}
            className="flex items-center gap-1.5 border-slate-700 bg-slate-800/60 hover:bg-slate-700/80"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* 2. Test Fixture Warning Banner (if synthetic data present) */}
      {overview?.provenance_summary.is_synthetic && (
        <div className="p-3.5 rounded-xl bg-purple-950/40 border border-purple-800/60 flex items-start gap-3 backdrop-blur shadow-sm">
          <Sparkles className="h-5 w-5 text-purple-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-xs font-bold text-purple-200 uppercase tracking-wider">
              {overview.provenance_summary.provenance_label}: Test Fixture Telemetry Active
            </h4>
            <p className="text-xs text-purple-300/90 mt-0.5">
              {overview.provenance_summary.mix_warning ||
                'Active camera sources or recent sessions include synthetic test fixtures. Telemetry and vehicle counts are generated for regression verification and must not be used for municipal control.'}
            </p>
          </div>
        </div>
      )}

      {/* 3. Quick Action / Operational Drill-Down Ribbon */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider pl-1 shrink-0">
          Drill-Down:
        </span>
        <Link
          to="/live-monitoring"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-cyan-300 hover:border-cyan-700/50 transition-all shrink-0"
        >
          <Radio className="h-3.5 w-3.5 text-cyan-400" />
          <span>Live Console</span>
        </Link>
        <Link
          to="/historical-analytics"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-cyan-300 hover:border-cyan-700/50 transition-all shrink-0"
        >
          <LineChart className="h-3.5 w-3.5 text-indigo-400" />
          <span>Historical Analytics</span>
        </Link>
        <Link
          to="/video-analysis"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-cyan-300 hover:border-cyan-700/50 transition-all shrink-0"
        >
          <Video className="h-3.5 w-3.5 text-blue-400" />
          <span>Video Analysis</span>
        </Link>
        <Link
          to="/reports"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-cyan-300 hover:border-cyan-700/50 transition-all shrink-0"
        >
          <FileText className="h-3.5 w-3.5 text-emerald-400" />
          <span>Reporting Studio</span>
        </Link>
        <Link
          to="/signal-optimization"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-indigo-300 hover:border-indigo-700/50 transition-all shrink-0"
        >
          <Sliders className="h-3.5 w-3.5 text-indigo-400" />
          <span>Signal Sim</span>
          <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60">
            SIM
          </span>
        </Link>
        <Link
          to="/emergency-simulation"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-indigo-300 hover:border-indigo-700/50 transition-all shrink-0"
        >
          <Siren className="h-3.5 w-3.5 text-rose-400" />
          <span>Emergency Corridor Sim</span>
          <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60">
            SIM
          </span>
        </Link>
        <Link
          to="/predictions"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-400 hover:text-slate-200 transition-all shrink-0"
        >
          <TrendingUp className="h-3.5 w-3.5 text-slate-400" />
          <span>Forecasting (N &lt; 20)</span>
        </Link>
      </div>

      {/* 4. Top KPI Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Cameras */}
        <Card className="bg-[#0e1726]/80 border-slate-800 hover:border-slate-700 transition-all">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Active Cameras</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold font-mono text-white">
                  {overview?.active_cameras_count || 0}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  / {overview?.total_cameras_count || 0} registered
                </span>
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-cyan-950/80 border border-cyan-800/50 flex items-center justify-center text-cyan-400">
              <Radio className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        {/* Active Incidents */}
        <Card className="bg-[#0e1726]/80 border-slate-800 hover:border-slate-700 transition-all">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Active Incidents</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span
                  className={`text-2xl font-bold font-mono ${
                    (overview?.active_incidents_count || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'
                  }`}
                >
                  {overview?.active_incidents_count || 0}
                </span>
                {(overview?.critical_incidents_count || 0) > 0 && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 animate-pulse">
                    {overview?.critical_incidents_count} CRITICAL
                  </span>
                )}
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-rose-950/80 border border-rose-800/50 flex items-center justify-center text-rose-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        {/* Live Active Tracks & Volume */}
        <Card className="bg-[#0e1726]/80 border-slate-800 hover:border-slate-700 transition-all">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Observed Traffic Volume</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold font-mono text-cyan-300">
                  {overview?.traffic_snapshot.observed_vehicle_volume || 0}
                </span>
                <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {overview?.traffic_snapshot.data_status}
                </span>
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-blue-950/80 border border-blue-800/50 flex items-center justify-center text-blue-400">
              <Activity className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        {/* Decision Insights */}
        <Card className="bg-[#0e1726]/80 border-slate-800 hover:border-slate-700 transition-all">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Active Insights</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold font-mono text-amber-300">
                  {overview?.active_insights_count || 0}
                </span>
                <span className="text-xs text-slate-400 font-medium">advisories</span>
              </div>
            </div>
            <div className="h-10 w-10 rounded-xl bg-amber-950/80 border border-amber-800/50 flex items-center justify-center text-amber-400">
              <Sparkles className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 5. Main Split: Left (Fleet & Snapshot) + Right (Active Incidents & Insights) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 cols): Camera Fleet & Real-time Snapshot */}
        <div className="lg:col-span-8 space-y-6">
          {/* Camera Fleet Overview */}
          <Card className="bg-[#0e1726]/90 border-slate-800">
            <CardHeader className="p-4 border-b border-slate-800 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Radio className="h-4 w-4 text-cyan-400" />
                <CardTitle className="text-sm font-bold text-white">
                  Camera Fleet & Telemetry Overview
                </CardTitle>
              </div>
              <Link
                to="/live-monitoring"
                className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
              >
                Manage Streams <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </CardHeader>
            <CardContent className="p-4">
              {(!overview?.cameras || overview.cameras.length === 0) ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No cameras registered in system. Add camera feeds in Live Monitoring.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {overview.cameras.map((cam) => (
                    <div
                      key={cam.id}
                      className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/90 hover:border-slate-700 transition-all flex flex-col justify-between"
                    >
                      <div>
                        {/* Header: Name & Health */}
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div>
                            <h4 className="text-xs font-bold text-slate-100 truncate max-w-[180px]">
                              {cam.name}
                            </h4>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-[10px] font-mono text-slate-400 uppercase">
                                {cam.source_type}
                              </span>
                              <span className="text-slate-400 text-[10px]">•</span>
                              <span className="text-[10px] font-mono text-slate-400 truncate max-w-[120px]">
                                {cam.connection_uri_redacted}
                              </span>
                            </div>
                          </div>
                          {renderHealthBadge(cam.health_status)}
                        </div>

                        {/* Live JPEG Preview Thumbnail (if active) */}
                        <div className="relative aspect-video rounded-lg bg-black/60 border border-slate-800 overflow-hidden mb-3 flex items-center justify-center">
                          {cam.is_active && cam.has_preview ? (
                            <img
                              src={`${getApiBaseUrl()}/api/v1/camera-sources/${cam.id}/preview.jpg?t=${Date.now()}`}
                              alt={cam.name}
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none';
                              }}
                            />
                          ) : (
                            <div className="flex flex-col items-center gap-1 text-slate-400">
                              <Video className="h-6 w-6 text-slate-400" />
                              <span className="text-[10px] font-medium">
                                {cam.is_active ? 'Awaiting Frame...' : 'Stream Inactive'}
                              </span>
                            </div>
                          )}

                          {cam.is_active && (
                            <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/70 backdrop-blur text-[9px] font-mono text-emerald-400 border border-emerald-500/40 flex items-center gap-1">
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              LIVE
                            </div>
                          )}
                        </div>

                        {/* Metrics Strip */}
                        <div className="grid grid-cols-3 gap-2 text-center py-2 px-1 bg-slate-950/60 rounded-lg border border-slate-800/60 mb-3 font-mono text-[11px]">
                          <div>
                            <span className="text-[10px] text-slate-400 block font-sans">FPS</span>
                            <span className="font-bold text-white">
                              {cam.is_active ? cam.processing_fps.toFixed(1) : cam.fps.toFixed(0)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-sans">Tracks</span>
                            <span className="font-bold text-cyan-400">
                              {cam.active_tracks_count}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-sans">Volume</span>
                            <span className="font-bold text-white">
                              {cam.current_vehicle_count}
                            </span>
                          </div>
                        </div>

                        {/* Dropped frames warning if any */}
                        {cam.dropped_frames > 0 && (
                          <div className="flex items-center gap-1.5 text-[10px] text-amber-400/90 mb-2">
                            <AlertTriangle className="h-3 w-3 shrink-0" />
                            <span>{cam.dropped_frames} frames dropped (rate limit)</span>
                          </div>
                        )}
                      </div>

                      {/* Footer Actions */}
                      <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                        <button
                          onClick={() => setSelectedSourceForContext(cam.id)}
                          className="text-[11px] text-slate-400 hover:text-indigo-300 flex items-center gap-1 font-medium transition-colors"
                        >
                          <History className="h-3 w-3 text-indigo-400" />
                          <span>History & Peaks</span>
                        </button>
                        <Link
                          to={`/live-monitoring?camera_id=${cam.id}`}
                          className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
                        >
                          <span>Live View</span>
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Current Traffic Snapshot */}
          <Card className="bg-[#0e1726]/90 border-slate-800">
            <CardHeader className="p-4 border-b border-slate-800 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Gauge className="h-4 w-4 text-cyan-400" />
                <CardTitle className="text-sm font-bold text-white">
                  Current Traffic Snapshot
                </CardTitle>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                  {overview?.traffic_snapshot.data_status}
                </span>
              </div>
              <div className="text-xs text-slate-400">
                Density:{' '}
                <span
                  className={`font-semibold uppercase ${
                    overview?.traffic_snapshot.traffic_density_state === 'congested'
                      ? 'text-rose-400'
                      : overview?.traffic_snapshot.traffic_density_state === 'moderate'
                      ? 'text-amber-400'
                      : 'text-emerald-400'
                  }`}
                >
                  {overview?.traffic_snapshot.traffic_density_state || 'Normal'}
                </span>
              </div>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              {/* Flow & Extrapolation Strip */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                    Flow Rate (veh/min)
                  </span>
                  <div className="flex items-baseline gap-1 mt-1">
                    <span className="text-xl font-bold font-mono text-white">
                      {overview?.traffic_snapshot.flow_rate_per_minute.toFixed(1) || '0.0'}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">vpm</span>
                  </div>
                  <span className="text-[9px] font-mono text-cyan-400/90 block mt-0.5">
                    Tag: {overview?.traffic_snapshot.flow_rate_tag}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                    Hourly Equivalent
                  </span>
                  <div className="flex items-baseline gap-1 mt-1">
                    <span className="text-xl font-bold font-mono text-white">
                      {overview?.traffic_snapshot.flow_rate_per_hour.toFixed(0) || '0'}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">vph</span>
                  </div>
                  <span className="text-[9px] font-mono text-slate-400 block mt-0.5">
                    {overview?.traffic_snapshot.flow_rate_tag === 'EXTRAPOLATED'
                      ? 'Extrapolated (< 5m window)'
                      : 'Observed Rate'}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                    Directional Balance
                  </span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-xs text-slate-300">
                      In:{' '}
                      <strong className="text-cyan-300 font-mono">
                        {overview?.traffic_snapshot.directional_split?.inbound || 0}
                      </strong>
                    </span>
                    <span className="text-xs text-slate-300">
                      Out:{' '}
                      <strong className="text-indigo-300 font-mono">
                        {overview?.traffic_snapshot.directional_split?.outbound || 0}
                      </strong>
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    Ratio:{' '}
                    <strong className="font-mono text-slate-300">
                      {overview?.traffic_snapshot.directional_ratio !== null
                        ? `${overview?.traffic_snapshot.directional_ratio}x`
                        : 'Balanced'}
                    </strong>
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                    Observation Window
                  </span>
                  <div className="flex items-baseline gap-1 mt-1">
                    <span className="text-xl font-bold font-mono text-white">
                      {overview?.traffic_snapshot.observation_duration_seconds.toFixed(0) || 0}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">seconds</span>
                  </div>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Continuous telemetry</span>
                </div>
              </div>

              {/* Vehicle Composition Breakdown */}
              <div>
                <span className="text-xs font-semibold text-slate-300 mb-2 block">
                  Vehicle Composition (Observed Fleet)
                </span>
                {overview?.traffic_snapshot.class_distribution &&
                Object.keys(overview.traffic_snapshot.class_distribution).length > 0 ? (
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                    {Object.entries(overview.traffic_snapshot.class_distribution).map(
                      ([cls, count]) => {
                        const total = overview.traffic_snapshot.observed_vehicle_volume || 1;
                        const pct = Math.round((count / total) * 100);
                        return (
                          <div
                            key={cls}
                            className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80"
                          >
                            <div className="flex items-center justify-between text-[11px] mb-1">
                              <span className="text-slate-400 capitalize">{cls}</span>
                              <span className="font-mono font-bold text-white">{count}</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                              <div
                                className="h-full bg-cyan-500 rounded-full"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-[9px] text-slate-400 mt-1 block font-mono">
                              {pct}% share
                            </span>
                          </div>
                        );
                      }
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-slate-400 py-3 text-center bg-slate-900/40 rounded-lg">
                    No active vehicle detections recorded in current snapshot.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column (4 cols): Active Incidents Panel & Decision Insights */}
        <div className="lg:col-span-4 space-y-6">
          {/* Active Incidents Panel */}
          <Card className="bg-[#0e1726]/90 border-slate-800">
            <CardHeader className="p-4 border-b border-slate-800 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-rose-400" />
                  <CardTitle className="text-sm font-bold text-white">Active Incidents</CardTitle>
                </div>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                  {overview?.active_incidents_count || 0} ACTIVE
                </span>
              </div>

              {/* Status / Severity Filter Pills */}
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] pt-1">
                <span className="text-[10px] text-slate-500 uppercase font-mono">Status:</span>
                {['all', 'open', 'acknowledged'].map((st) => (
                  <button
                    key={st}
                    onClick={() => setIncidentFilterStatus(st)}
                    className={`px-2 py-0.5 rounded capitalize font-medium transition-all ${
                      incidentFilterStatus === st
                        ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/50'
                        : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {st}
                  </button>
                ))}
                <span className="text-slate-600 mx-1">|</span>
                <span className="text-[10px] text-slate-500 uppercase font-mono">Severity:</span>
                {['all', 'critical', 'high', 'medium'].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setIncidentFilterSeverity(sev)}
                    className={`px-2 py-0.5 rounded capitalize font-medium transition-all ${
                      incidentFilterSeverity === sev
                        ? 'bg-rose-950/80 text-rose-300 border border-rose-700/60'
                        : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </CardHeader>
            <CardContent className="p-3 max-h-[460px] overflow-y-auto space-y-2.5">
              {filteredIncidents.length === 0 ? (
                <div className="py-12 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
                  <CheckCircle2 className="h-8 w-8 text-emerald-400/60" />
                  <span>No active operational incidents matching filter.</span>
                  <span className="text-[10px] text-slate-400">All approaches operating within thresholds.</span>
                </div>
              ) : (
                filteredIncidents.map((inc) => (
                  <div
                    key={inc.id}
                    className="p-3 rounded-xl bg-slate-900/80 border border-slate-800/90 hover:border-slate-700 transition-all space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-1.5">
                          {renderSeverityBadge(inc.severity)}
                          <span className="text-xs font-bold text-slate-200 truncate max-w-[150px]">
                            {inc.title}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-400 block mt-1">
                          Source: {inc.camera_name || inc.video_filename || 'Unknown Feed'}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold">
                        {inc.status}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 leading-snug line-clamp-2">
                      {inc.description}
                    </p>

                    {/* Metric trigger strip */}
                    <div className="text-[11px] font-mono text-slate-300 bg-slate-950/60 p-1.5 rounded flex items-center justify-between">
                      <span>Trigger: {inc.trigger_value.toFixed(1)}</span>
                      <span className="text-slate-400">Limit: {inc.threshold_value.toFixed(1)}</span>
                      <span className="text-rose-400 font-semibold">{inc.duration_seconds.toFixed(0)}s</span>
                    </div>

                    {/* Operator Note (if acknowledged) */}
                    {inc.operator_note && (
                      <div className="text-[10px] text-cyan-300 bg-cyan-950/40 border border-cyan-800/40 p-1.5 rounded italic">
                        Note: "{inc.operator_note}"
                      </div>
                    )}

                    {/* Actions: Acknowledge / Resolve / Details */}
                    <div className="flex items-center justify-between pt-1 gap-2">
                      <button
                        onClick={() => setDetailIncident(inc)}
                        className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1 font-medium"
                      >
                        <Eye className="h-3 w-3" />
                        Details
                      </button>

                      <div className="flex items-center gap-1.5">
                        {inc.status === 'open' && (
                          <button
                            onClick={() => {
                              setActiveModalIncident(inc);
                              setStatusActionTarget('acknowledged');
                            }}
                            className="text-[10px] px-2 py-1 rounded bg-amber-950/80 text-amber-300 border border-amber-800 hover:bg-amber-900 transition-all font-semibold"
                          >
                            Acknowledge
                          </button>
                        )}
                        {inc.status !== 'resolved' && (
                          <button
                            onClick={() => {
                              setActiveModalIncident(inc);
                              setStatusActionTarget('resolved');
                            }}
                            className="text-[10px] px-2 py-1 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800 hover:bg-emerald-900 transition-all font-semibold"
                          >
                            Resolve
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Decision Insights (Phase 18 Integration) */}
          <Card className="bg-[#0e1726]/90 border-slate-800">
            <CardHeader className="p-4 border-b border-slate-800 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber-400" />
                <CardTitle className="text-sm font-bold text-white">Decision Insights</CardTitle>
              </div>
              <span className="text-[10px] text-slate-400 italic">Advisory Only</span>
            </CardHeader>
            <CardContent className="p-3 max-h-[380px] overflow-y-auto space-y-2.5">
              {(!overview?.insights || overview.insights.length === 0) ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No active advisory insights currently flagged by decision engine.
                </div>
              ) : (
                overview.insights.map((ins) => (
                  <div
                    key={ins.id}
                    className="p-3 rounded-xl bg-slate-900/80 border border-slate-800/80 hover:border-slate-700 transition-all space-y-1.5"
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-xs font-bold text-slate-200">{ins.title}</span>
                      <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800">
                        {ins.category}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 leading-snug line-clamp-2">
                      {ins.summary}
                    </p>
                    {ins.recommendation && (
                      <div className="text-[11px] text-cyan-300/90 bg-cyan-950/30 border border-cyan-800/40 p-2 rounded-lg mt-1">
                        <strong className="text-cyan-400">Advisory:</strong> {ins.recommendation}
                      </div>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 6. Recent Authoritative Event Timeline */}
      <Card className="bg-[#0e1726]/90 border-slate-800">
        <CardHeader className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-cyan-400" />
            <CardTitle className="text-sm font-bold text-white">
              Operations Event Timeline
            </CardTitle>
            <span className="text-[10px] text-slate-400 font-mono">(Authoritative Events)</span>
          </div>

          {/* Timeline Filter Pills */}
          <div className="flex items-center gap-1.5 text-xs overflow-x-auto">
            {[
              { id: 'all', label: 'All Events' },
              { id: 'incident_started', label: 'Incidents' },
              { id: 'job_completed', label: 'Jobs' },
              { id: 'insight_generated', label: 'Insights' },
              { id: 'report_generated', label: 'Reports' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setTimelineFilter(tab.id)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                  timelineFilter === tab.id
                    ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="p-4 max-h-[380px] overflow-y-auto">
          {filteredTimeline.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              No recent timeline events found matching filter.
            </div>
          ) : (
            <div className="relative border-l border-slate-800 ml-4 space-y-4">
              {filteredTimeline.map((ev) => {
                const evTime = new Date(ev.timestamp).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                });
                return (
                  <div key={ev.id} className="relative pl-6">
                    <span className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full bg-cyan-500 border-2 border-[#0e1726]" />
                    <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-200">{ev.title}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900 text-slate-400 border border-slate-800 uppercase">
                          {ev.source_type}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">{evTime}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">{ev.description}</p>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 7. Historical Context Drawer Modal */}
      {selectedSourceForContext && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#0e1726] border border-slate-800 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <LineChart className="h-5 w-5 text-indigo-400" />
                <h3 className="text-base font-bold text-white">Retrospective Historical Context</h3>
              </div>
              <button
                onClick={() => setSelectedSourceForContext(null)}
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {loadingContext ? (
              <LoadingState message="Querying Phase 22 Historical Analytics..." />
            ) : historicalContext ? (
              <div className="space-y-4 text-xs">
                <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="text-slate-400 block font-sans">Source</span>
                    <strong className="text-white text-sm">{historicalContext.source_name}</strong>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                    Window: {historicalContext.time_window}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">Total Volume</span>
                    <span className="text-base font-mono font-bold text-white">
                      {historicalContext.total_volume} veh
                    </span>
                  </div>
                  <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">Peak Flow Rate</span>
                    <span className="text-base font-mono font-bold text-cyan-300">
                      {historicalContext.peak_flow_rate !== null && historicalContext.peak_flow_rate !== undefined
                        ? `${historicalContext.peak_flow_rate.toFixed(0)} vph`
                        : 'N/A'}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                    <span className="text-slate-400 block">Anomalies</span>
                    <span className="text-base font-mono font-bold text-amber-300">
                      {historicalContext.anomaly_count}
                    </span>
                  </div>
                </div>

                {/* Forecasting Boundary Statement */}
                <div className="p-3 bg-slate-900/40 rounded-xl border border-slate-800/80 space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Forecasting Status (Phase 11 Boundary)
                  </span>
                  <p className="text-xs text-slate-400">{historicalContext.forecast_reason}</p>
                </div>

                <div className="flex justify-end pt-2">
                  <Link
                    to={`/historical-analytics?camera_source_id=${historicalContext.source_id}`}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center gap-1.5"
                  >
                    <span>Open Historical Deep-Dive</span>
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-slate-400">
                No historical records found for this source.
              </div>
            )}
          </div>
        </div>
      )}

      {/* 8. Incident Operator Action Modal (Acknowledge / Resolve) */}
      {activeModalIncident && statusActionTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#0e1726] border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white capitalize">
                {statusActionTarget} Incident
              </h3>
              <button
                onClick={() => {
                  setActiveModalIncident(null);
                  setStatusActionTarget(null);
                }}
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-slate-400 block">Incident:</span>
                <strong className="text-slate-100 text-sm">{activeModalIncident.title}</strong>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Operator Audit Note (Optional)
                </label>
                <textarea
                  value={operatorNote}
                  onChange={(e) => setOperatorNote(e.target.value)}
                  placeholder="e.g. Cleared stalled vehicle, verified sensor calibration, notified field crew..."
                  className="w-full h-24 bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setActiveModalIncident(null);
                  setStatusActionTarget(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleUpdateStatusSubmit}
                disabled={actionSubmitting}
                className={statusActionTarget === 'resolved' ? 'bg-emerald-600 hover:bg-emerald-500' : ''}
              >
                {actionSubmitting ? 'Submitting...' : `Confirm ${statusActionTarget}`}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 9. Incident Detail Modal */}
      {detailIncident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#0e1726] border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-rose-400" />
                <h3 className="text-base font-bold text-white">Incident Details & Evidence</h3>
              </div>
              <button
                onClick={() => setDetailIncident(null)}
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-white">{detailIncident.title}</h4>
                  {renderSeverityBadge(detailIncident.severity)}
                </div>
                <p className="text-slate-300 mt-1">{detailIncident.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-slate-300">
                <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block">Anomaly Type</span>
                  <span className="font-mono font-bold text-white">{detailIncident.anomaly_type}</span>
                </div>
                <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block">Status</span>
                  <span className="font-mono font-bold text-white uppercase">{detailIncident.status}</span>
                </div>
                <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block">Trigger Value</span>
                  <span className="font-mono font-bold text-rose-300">{detailIncident.trigger_value}</span>
                </div>
                <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block">Threshold</span>
                  <span className="font-mono font-bold text-white">{detailIncident.threshold_value}</span>
                </div>
              </div>

              {detailIncident.operator_note && (
                <div className="p-3 bg-cyan-950/40 border border-cyan-800/60 rounded-xl space-y-1">
                  <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider block">
                    Operator Note
                  </span>
                  <p className="text-cyan-200">{detailIncident.operator_note}</p>
                </div>
              )}

              <div className="p-3 bg-slate-900/40 rounded-xl border border-slate-800 text-slate-400 space-y-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Provenance Lineage
                </span>
                <p>Provenance Category: <strong className="text-slate-300">{detailIncident.provenance_category}</strong></p>
                <p>Synthetic Test: <strong className="text-slate-300">{detailIncident.is_synthetic ? 'Yes (Test Fixture)' : 'No (Real World Feeds)'}</strong></p>
                <p>Session ID: <strong className="text-slate-300 font-mono">{detailIncident.session_id}</strong></p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button size="sm" variant="outline" onClick={() => setDetailIncident(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default OperationsCenterPage;
