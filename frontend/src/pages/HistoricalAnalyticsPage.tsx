import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  Clock,
  Car,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
  Layers,
  RotateCw,
  Sliders,
  ShieldCheck,
  ShieldAlert,
  Info,
  Radio,
  ArrowRightLeft,
  Flame,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import {
  getHistoricalSummary,
  getHistoricalTimeSeries,
  getVehicleCompositionTrends,
  getDirectionalTrends,
  getLaneIntelligence,
  getObservedPeakPeriods,
  getAnomalyHistory,
  getSourceComparison,
  getPeriodComparison,
} from '@/api/historicalAnalytics';
import { listCameraSources } from '@/api/cameraSources';
import { listVideos } from '@/api/videos';
import {
  HistoricalSummaryResponse,
  HistoricalTimeSeriesResponse,
  VehicleCompositionTrendResponse,
  DirectionalTrendResponse,
  LaneIntelligenceResponse,
  PeakPeriodsResponse,
  AnomalyHistoryResponse,
  SourceComparisonResponse,
  PeriodComparisonResponse,
  HistoricalProvenanceSummary,
  HistoricalFilterParams,
} from '@/types/historicalAnalytics';
import { CameraSource } from '@/types/camera';
import { VideoMetadata } from '@/types/video';

type TimePreset = '24h' | '7d' | '30d' | '90d' | 'custom';
type ActiveTab =
  | 'trends'
  | 'composition'
  | 'directions'
  | 'lanes'
  | 'peaks'
  | 'anomalies'
  | 'sources'
  | 'comparison';

export function HistoricalAnalyticsPage() {
  // Filter States
  const [preset, setPreset] = useState<TimePreset>('7d');
  const [startTime, setStartTime] = useState<string>('');
  const [endTime, setEndTime] = useState<string>('');
  const [bucketInterval, setBucketInterval] = useState<string>('hourly');
  const [selectedSourceId, setSelectedSourceId] = useState<string>('');
  const [selectedSessionMode, setSelectedSessionMode] = useState<string>('');
  const [includeSynthetic, setIncludeSynthetic] = useState<boolean>(true);

  // Active Tab
  const [activeTab, setActiveTab] = useState<ActiveTab>('trends');

  // Metadata for filter dropdowns
  const [sources, setSources] = useState<CameraSource[]>([]);
  const [videos, setVideos] = useState<VideoMetadata[]>([]);

  // Analytics Data States
  const [summary, setSummary] = useState<HistoricalSummaryResponse | null>(null);
  const [timeSeries, setTimeSeries] = useState<HistoricalTimeSeriesResponse | null>(null);
  const [composition, setComposition] = useState<VehicleCompositionTrendResponse | null>(null);
  const [directions, setDirections] = useState<DirectionalTrendResponse | null>(null);
  const [lanes, setLanes] = useState<LaneIntelligenceResponse | null>(null);
  const [peaks, setPeaks] = useState<PeakPeriodsResponse | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyHistoryResponse | null>(null);
  const [sourceComparison, setSourceComparison] = useState<SourceComparisonResponse | null>(null);
  const [periodComparison, setPeriodComparison] = useState<PeriodComparisonResponse | null>(null);

  // Status States
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Compute ISO time range based on preset or custom
  const getComputedTimeRange = useCallback(() => {
    if (preset === 'custom') {
      return {
        start_time: startTime ? new Date(startTime).toISOString() : undefined,
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
      };
    }
    const now = new Date();
    let hours = 24 * 7;
    if (preset === '24h') hours = 24;
    else if (preset === '7d') hours = 24 * 7;
    else if (preset === '30d') hours = 24 * 30;
    else if (preset === '90d') hours = 24 * 90;

    const start = new Date(now.getTime() - hours * 60 * 60 * 1000);
    return {
      start_time: start.toISOString(),
      end_time: now.toISOString(),
    };
  }, [preset, startTime, endTime]);

  // Load Sources & Videos on mount
  useEffect(() => {
    let mounted = true;
    async function loadMetadata() {
      try {
        const [camRes, vidRes] = await Promise.allSettled([
          listCameraSources(),
          listVideos(),
        ]);
        if (mounted) {
          if (camRes.status === 'fulfilled' && camRes.value?.items) {
            setSources(camRes.value.items);
          }
          if (vidRes.status === 'fulfilled' && Array.isArray(vidRes.value)) {
            setVideos(vidRes.value);
          }
        }
      } catch {
        // Soft fail on dropdown metadata
      }
    }
    loadMetadata();
    return () => {
      mounted = false;
    };
  }, []);

  // Main data fetcher
  const loadData = useCallback(
    async (isManual = false) => {
      if (isManual) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const range = getComputedTimeRange();
      const filterParams: HistoricalFilterParams = {
        start_time: range.start_time,
        end_time: range.end_time,
        time_preset: preset,
        camera_source_id: selectedSourceId || undefined,
        session_mode: selectedSessionMode || undefined,
        include_synthetic: includeSynthetic,
        bucket_interval: bucketInterval,
      };

      try {
        const [
          sumRes,
          tsRes,
          compRes,
          dirRes,
          laneRes,
          peaksRes,
          anomRes,
          srcCompRes,
          periodRes,
        ] = await Promise.all([
          getHistoricalSummary(filterParams),
          getHistoricalTimeSeries(filterParams),
          getVehicleCompositionTrends(filterParams),
          getDirectionalTrends(filterParams),
          getLaneIntelligence(filterParams),
          getObservedPeakPeriods(filterParams),
          getAnomalyHistory(filterParams),
          getSourceComparison(filterParams),
          getPeriodComparison(filterParams),
        ]);

        setSummary(sumRes);
        setTimeSeries(tsRes);
        setComposition(compRes);
        setDirections(dirRes);
        setLanes(laneRes);
        setPeaks(peaksRes);
        setAnomalies(anomRes);
        setSourceComparison(srcCompRes);
        setPeriodComparison(periodRes);
      } catch (err: any) {
        setError(
          err?.message || 'Failed to aggregate historical traffic intelligence records.'
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [
      getComputedTimeRange,
      preset,
      selectedSourceId,
      selectedSessionMode,
      includeSynthetic,
      bucketInterval,
    ]
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Provenance Banner Helper
  const renderProvenanceBanner = (prov?: HistoricalProvenanceSummary) => {
    if (!prov) return null;

    const label = prov.provenance_label;
    const isReal = label === 'REAL DATA';
    const isSynthetic = label === 'SYNTHETIC';
    const isMixed = label === 'MIXED';

    return (
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-lg border ${
              isReal
                ? 'bg-emerald-950/60 border-emerald-800/60 text-emerald-400'
                : isSynthetic
                ? 'bg-amber-950/60 border-amber-800/60 text-amber-400'
                : isMixed
                ? 'bg-cyan-950/60 border-cyan-800/60 text-cyan-400'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
          >
            {isReal ? (
              <ShieldCheck className="h-5 w-5" />
            ) : isSynthetic ? (
              <ShieldAlert className="h-5 w-5" />
            ) : (
              <Activity className="h-5 w-5" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                Data Provenance:
              </span>
              <Badge
                variant={
                  isReal ? 'success' : isSynthetic ? 'warning' : isMixed ? 'info' : 'default'
                }
                size="sm"
              >
                {label}
              </Badge>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {prov.description ||
                `${prov.session_count} session(s) analyzed. Zero extrapolation, zero predictive forecasting.`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-stretch sm:self-auto justify-end text-[11px] text-slate-400 bg-slate-950/50 px-3 py-1.5 rounded-lg border border-slate-800/80">
          <Info className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
          <span>Strictly discrete intervals — zero spline interpolation</span>
        </div>
      </div>
    );
  };

  // Format Helpers
  const formatDuration = (secs: number) => {
    if (secs <= 0) return '0m';
    const hours = Math.floor(secs / 3600);
    const mins = Math.floor((secs % 3600) / 60);
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  const formatDate = (iso?: string | null) => {
    if (!iso) return 'N/A';
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-[#0a0f1d] to-cyan-950/30 shadow-xl shadow-black/40">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <BarChart3 className="h-6 w-6 text-cyan-400" />
              <span>Historical Traffic Intelligence</span>
            </h1>
            <Badge variant="info" size="sm">
              Phase 22
            </Badge>
            <Badge
              variant="success"
              size="sm"
              className="hidden sm:inline-flex items-center gap-1 font-mono"
            >
              <ShieldCheck className="h-3 w-3" />
              Observed Reality
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
            Deterministic historical aggregation across uploaded video analysis and live camera
            sessions. Answers &ldquo;What actually happened?&rdquo; with zero predictive
            extrapolation and zero simulated traffic padding.
          </p>
        </div>

        {/* Global Action: Manual Refresh */}
        <div className="flex items-center gap-2.5 self-start md:self-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 bg-slate-900/80 border-slate-700 hover:bg-slate-800 text-slate-200"
          >
            <RotateCw
              className={`h-3.5 w-3.5 text-cyan-400 ${refreshing ? 'animate-spin' : ''}`}
            />
            <span>{refreshing ? 'Aggregating...' : 'Refresh Records'}</span>
          </Button>
        </div>
      </div>

      {/* Filter Control Bar */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 space-y-4 shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
          {/* Preset Buttons */}
          <div className="flex items-center gap-1.5 bg-slate-950/60 p-1 rounded-lg border border-slate-800/80">
            {(['24h', '7d', '30d', '90d', 'custom'] as TimePreset[]).map((p) => (
              <button
                key={p}
                onClick={() => setPreset(p)}
                className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                  preset === p
                    ? 'bg-cyan-600 text-white shadow-sm shadow-cyan-950'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                {p === 'custom' ? 'Custom Range' : p.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Synthetic Toggle */}
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeSynthetic}
              onChange={(e) => setIncludeSynthetic(e.target.checked)}
              className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-500/20"
            />
            <span>Include Synthetic Benchmarks</span>
          </label>
        </div>

        {/* Secondary Filters: Sources, Modes, Buckets */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Source Selector */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Traffic Source
            </label>
            <select
              value={selectedSourceId}
              onChange={(e) => setSelectedSourceId(e.target.value)}
              className="w-full text-xs rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-slate-200 focus:border-cyan-500 focus:outline-none"
            >
              <option value="">All Monitored Sources</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  Cam: {s.name} ({s.source_type})
                </option>
              ))}
              {videos.map((v) => (
                <option key={v.id} value={v.id}>
                  Vid: {v.original_filename}
                </option>
              ))}
            </select>
          </div>

          {/* Session Mode */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Analysis Mode
            </label>
            <select
              value={selectedSessionMode}
              onChange={(e) => setSelectedSessionMode(e.target.value)}
              className="w-full text-xs rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-slate-200 focus:border-cyan-500 focus:outline-none"
            >
              <option value="">All Processing Modes</option>
              <option value="file_analysis">Uploaded Video (Phases 4–10)</option>
              <option value="live_monitoring">Live Stream / Camera (Phase 21)</option>
            </select>
          </div>

          {/* Bucket Interval */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Aggregation Bucket
            </label>
            <select
              value={bucketInterval}
              onChange={(e) => setBucketInterval(e.target.value)}
              className="w-full text-xs rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-slate-200 focus:border-cyan-500 focus:outline-none"
            >
              <option value="15m">15 Minutes (Fine)</option>
              <option value="30m">30 Minutes (Standard)</option>
              <option value="hourly">1 Hour (Macro)</option>
              <option value="daily">1 Day (Overview)</option>
            </select>
          </div>

          {/* Custom Date Pickers */}
          {preset === 'custom' ? (
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-[11px] font-medium text-slate-400 mb-1">
                  Start Date
                </label>
                <input
                  type="datetime-local"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="w-full text-xs rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-200 focus:border-cyan-500 focus:outline-none"
                />
              </div>
              <div className="flex-1">
                <label className="block text-[11px] font-medium text-slate-400 mb-1">
                  End Date
                </label>
                <input
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="w-full text-xs rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-200 focus:border-cyan-500 focus:outline-none"
                />
              </div>
            </div>
          ) : (
            <div className="flex items-end">
              <div className="text-[11px] text-slate-400 pb-2">
                Window: <span className="text-slate-200 font-mono">{preset.toUpperCase()}</span>{' '}
                (bounded max 90 days)
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Loading & Error States */}
      {loading && !summary && (
        <div className="py-16">
          <LoadingState message="Aggregating deterministic historical traffic records across sessions..." />
        </div>
      )}

      {error && !summary && (
        <div className="py-12">
          <ErrorState
            title="Historical Intelligence Error"
            message={error}
            onRetry={() => loadData()}
          />
        </div>
      )}

      {/* Main Content */}
      {summary && (
        <div className="space-y-6">
          {/* Data Provenance & Boundary Banner */}
          {renderProvenanceBanner(summary.provenance)}

          {/* KPI Overview Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* KPI 1: Total Volume */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/90 shadow-md">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-xs font-medium">Observed Volume</span>
                <Car className="h-4 w-4 text-cyan-400" />
              </div>
              <div className="text-xl font-bold font-mono text-white">
                {summary.total_observed_volume.toLocaleString()}
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Vehicles Counted</p>
            </div>

            {/* KPI 2: Total Duration */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/90 shadow-md">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-xs font-medium">Monitored Duration</span>
                <Clock className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="text-xl font-bold font-mono text-emerald-400">
                {formatDuration(summary.observation_duration_seconds)}
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Observed Time</p>
            </div>

            {/* KPI 3: Avg Flow Rate */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/90 shadow-md">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-xs font-medium">Avg Flow Rate</span>
                <Activity className="h-4 w-4 text-indigo-400" />
              </div>
              <div className="text-xl font-bold font-mono text-indigo-300">
                {summary.flow_rate_per_minute.toFixed(1)}
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Vehicles / Min</p>
            </div>

            {/* KPI 4: Sessions Count */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/90 shadow-md">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-xs font-medium">Sessions</span>
                <Layers className="h-4 w-4 text-amber-400" />
              </div>
              <div className="text-xl font-bold font-mono text-amber-300">
                {summary.session_count}
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Analyzed Runs</p>
            </div>

            {/* KPI 5: Monitored Sources */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/90 shadow-md">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-xs font-medium">Sources</span>
                <Radio className="h-4 w-4 text-purple-400" />
              </div>
              <div className="text-xl font-bold font-mono text-purple-300">
                {summary.source_count}
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Cameras & Videos</p>
            </div>

            {/* KPI 6: Total Anomalies */}
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/90 shadow-md">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-xs font-medium">Logged Incidents</span>
                <AlertTriangle className="h-4 w-4 text-rose-400" />
              </div>
              <div className="text-xl font-bold font-mono text-rose-400">
                {summary.anomaly_count}
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Phase 15 Anomalies</p>
            </div>
          </div>

          {/* Empty State Guard */}
          {summary.session_count === 0 && summary.total_observed_volume === 0 && (
            <EmptyState
              icon={<BarChart3 className="h-8 w-8 text-slate-400" />}
              title="No Historical Observations in Selected Window"
              description="Zero traffic metric records were found matching the active time filter and source criteria. Historical intelligence is strictly unpadded: we never synthesize fake charts."
              action={
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPreset('90d')}
                  className="mt-2 text-xs"
                >
                  Expand to 90 Days
                </Button>
              }
            />
          )}

          {(summary.session_count > 0 || summary.total_observed_volume > 0) && (
            <>
              {/* Tab Navigation */}
              <div className="flex items-center gap-1.5 border-b border-slate-800 overflow-x-auto pb-1">
                {[
                  { id: 'trends', label: 'Traffic Trends', icon: BarChart3 },
                  { id: 'composition', label: 'Vehicle Composition', icon: Car },
                  { id: 'directions', label: 'Directional Flow', icon: ArrowRightLeft },
                  { id: 'lanes', label: 'Lane Intelligence', icon: Sliders },
                  { id: 'peaks', label: 'Observed Peaks', icon: Flame },
                  { id: 'anomalies', label: 'Anomaly History', icon: AlertTriangle },
                  { id: 'sources', label: 'Source Comparison', icon: Radio },
                  { id: 'comparison', label: 'Period Comparison', icon: TrendingUp },
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as ActiveTab)}
                      className={`flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg transition-all whitespace-nowrap ${
                        isActive
                          ? 'bg-cyan-600/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-950'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                      }`}
                    >
                      <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* TAB 1: TRAFFIC TRENDS (DISCRETE TIME SERIES) */}
              {activeTab === 'trends' && timeSeries && (
                <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
                  <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
                    <div>
                      <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                        <BarChart3 className="h-5 w-5 text-cyan-400" />
                        <span>Discrete Time-Series Buckets</span>
                      </CardTitle>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {timeSeries.buckets.length} non-interpolated discrete intervals (
                        {timeSeries.bucket_interval_seconds}s per bucket). Empty intervals reflect
                        genuine lack of observation.
                      </p>
                    </div>
                    <Badge variant="info" size="sm">
                      {timeSeries.bucket_interval_seconds}s interval
                    </Badge>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-6">
                    {/* Discrete Bucket Chart */}
                    {timeSeries.buckets.length > 0 ? (
                      <div className="space-y-4">
                        <div className="flex items-end gap-1.5 h-44 p-4 rounded-xl bg-slate-950/70 border border-slate-800 overflow-x-auto">
                          {(() => {
                            const maxVol = Math.max(
                              ...timeSeries.buckets.map((b) => b.observed_volume),
                              1
                            );
                            return timeSeries.buckets.map((bucket) => {
                              const heightPct = Math.max(
                                (bucket.observed_volume / maxVol) * 100,
                                6
                              );
                              return (
                                <div
                                  key={bucket.bucket_index}
                                  className="flex-1 min-w-[32px] max-w-[56px] flex flex-col items-center justify-end h-full group relative"
                                >
                                  {/* Tooltip on hover */}
                                  <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-16 bg-slate-800 text-white text-[10px] rounded px-2 py-1 border border-slate-700 whitespace-nowrap pointer-events-none z-20 shadow-xl">
                                    <div className="font-semibold text-cyan-300">
                                      {formatDate(bucket.start_time)}
                                    </div>
                                    <div>{bucket.observed_volume} veh ({bucket.flow_rate_per_minute.toFixed(1)}/min)</div>
                                    <div className="text-[9px] text-slate-400">
                                      {bucket.session_count} session(s)
                                    </div>
                                  </div>

                                  <div className="text-[10px] font-mono text-cyan-400 mb-1 font-bold">
                                    {bucket.observed_volume}
                                  </div>

                                  <div
                                    className="w-full rounded-t-md bg-gradient-to-t from-cyan-700 to-cyan-400 group-hover:from-cyan-500 group-hover:to-cyan-300 transition-all shadow-md shadow-cyan-950/50"
                                    style={{ height: `${heightPct}%` }}
                                  />

                                  <div className="text-[9px] font-mono text-slate-400 mt-1 truncate max-w-[48px]">
                                    {new Date(bucket.start_time).toLocaleTimeString([], {
                                      hour: '2-digit',
                                      minute: '2-digit',
                                    })}
                                  </div>
                                </div>
                              );
                            });
                          })()}
                        </div>

                        {/* Bucket Summary Row */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800">
                            <span className="text-[11px] text-slate-400">Total Buckets</span>
                            <div className="text-base font-bold font-mono text-slate-200">
                              {timeSeries.buckets.length}
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800">
                            <span className="text-[11px] text-slate-400">Max Bucket Volume</span>
                            <div className="text-base font-bold font-mono text-cyan-400">
                              {Math.max(...timeSeries.buckets.map((b) => b.observed_volume), 0)} veh
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800">
                            <span className="text-[11px] text-slate-400">Max Bucket Flow Rate</span>
                            <div className="text-base font-bold font-mono text-indigo-300">
                              {Math.max(
                                ...timeSeries.buckets.map((b) => b.flow_rate_per_minute),
                                0
                              ).toFixed(1)}{' '}
                              /min
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <EmptyState
                        title="No Discrete Buckets Generated"
                        description="No traffic metrics fell within discrete time buckets for this range."
                      />
                    )}
                  </CardContent>
                </Card>
              )}

              {/* TAB 2: VEHICLE COMPOSITION */}
              {activeTab === 'composition' && composition && (
                <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
                  <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
                    <div>
                      <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                        <Car className="h-5 w-5 text-cyan-400" />
                        <span>Supported Computer Vision Vehicle Classes</span>
                      </CardTitle>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Historical distribution across YOLO COCO classes verified in Phases 4–10. Total: {composition.total_vehicles} vehicles.
                      </p>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-4">
                    <div className="space-y-3">
                      {composition.classes.map((item) => (
                        <div key={item.class_name} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="capitalize font-medium text-slate-200">
                              {item.class_name}
                            </span>
                            <div className="flex items-center gap-2 font-mono">
                              <span className="text-slate-400">{item.count} veh</span>
                              <span className="text-cyan-400 font-bold">
                                {item.percentage.toFixed(1)}%
                              </span>
                            </div>
                          </div>
                          <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-cyan-600 to-cyan-400"
                              style={{ width: `${item.percentage}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* TAB 3: DIRECTIONAL FLOW */}
              {activeTab === 'directions' && directions && (
                <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
                  <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
                    <div>
                      <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                        <ArrowRightLeft className="h-5 w-5 text-cyan-400" />
                        <span>Directional Traffic Flow & Movement Balance</span>
                      </CardTitle>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Inbound vs Outbound vehicle flow balance aggregated across directional tripwires.
                      </p>
                    </div>
                    <Badge variant="outline" size="sm">
                      Ratio: {directions.directional_ratio.toFixed(2)}
                    </Badge>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-6">
                    {/* Visual Balance Split Bar */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs font-mono">
                        <span className="text-emerald-400 font-bold">
                          Inbound: {directions.inbound_count} (
                          {directions.inbound_percentage.toFixed(1)}%)
                        </span>
                        <span className="text-cyan-400 font-bold">
                          Outbound: {directions.outbound_count} (
                          {directions.outbound_percentage.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="h-3 rounded-full bg-slate-800 flex overflow-hidden">
                        <div
                          className="h-full bg-emerald-500"
                          style={{ width: `${directions.inbound_percentage}%` }}
                          title={`Inbound: ${directions.inbound_percentage.toFixed(1)}%`}
                        />
                        <div
                          className="h-full bg-cyan-500"
                          style={{ width: `${directions.outbound_percentage}%` }}
                          title={`Outbound: ${directions.outbound_percentage.toFixed(1)}%`}
                        />
                      </div>
                    </div>

                    {/* Movement Details Breakdown */}
                    {directions.directions.length > 0 && (
                      <div className="border border-slate-800 rounded-xl overflow-hidden">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-950/70 text-slate-400 border-b border-slate-800 font-medium">
                            <tr>
                              <th className="px-4 py-2.5">Movement Direction</th>
                              <th className="px-4 py-2.5 text-right">Count</th>
                              <th className="px-4 py-2.5 text-right">Share</th>
                              <th className="px-4 py-2.5 text-right">Rate / Hr</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800">
                            {directions.directions.map((d) => (
                              <tr key={d.direction} className="hover:bg-slate-800/40">
                                <td className="px-4 py-2.5 font-medium text-slate-200 capitalize">
                                  {d.direction}
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-cyan-400">
                                  {d.count}
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-slate-400">
                                  {d.percentage.toFixed(1)}%
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-indigo-300">
                                  {d.flow_rate_per_hour.toFixed(1)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* TAB 4: LANE INTELLIGENCE */}
              {activeTab === 'lanes' && lanes && (
                <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
                  <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
                    <div>
                      <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                        <Sliders className="h-5 w-5 text-cyan-400" />
                        <span>Lane Utilization & Occupancy Intelligence</span>
                      </CardTitle>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Aggregated metrics across designated lane regions from Phase 8.
                      </p>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-6">
                    {/* Prominent Calibration Warning Banner */}
                    <div className="flex items-start gap-3 p-3.5 rounded-xl border border-amber-800/60 bg-amber-950/30 text-amber-300 text-xs">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
                      <div>
                        <span className="font-bold">Density Calibration Notice:</span>{' '}
                        Image-space bounding-box heuristic (pixel/bbox area ratio). Not physical
                        highway density (veh/km) without multi-point planar camera survey calibration.
                      </div>
                    </div>

                    {/* Lane Table */}
                    {lanes.lanes.length > 0 ? (
                      <div className="border border-slate-800 rounded-xl overflow-hidden">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-950/70 text-slate-400 border-b border-slate-800 font-medium">
                            <tr>
                              <th className="px-4 py-2.5">Lane ID</th>
                              <th className="px-4 py-2.5">Name</th>
                              <th className="px-4 py-2.5 text-right">Volume</th>
                              <th className="px-4 py-2.5 text-right">Volume Share</th>
                              <th className="px-4 py-2.5 text-right">Peak Occupancy</th>
                              <th className="px-4 py-2.5 text-right">Avg Density</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800">
                            {lanes.lanes.map((lane) => (
                              <tr key={lane.lane_id} className="hover:bg-slate-800/40">
                                <td className="px-4 py-2.5 font-mono text-cyan-400 font-semibold">
                                  {lane.lane_id}
                                </td>
                                <td className="px-4 py-2.5 text-slate-200">{lane.lane_name}</td>
                                <td className="px-4 py-2.5 text-right font-mono text-white">
                                  {lane.total_volume}
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-cyan-300">
                                  {lane.volume_share_pct.toFixed(1)}%
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-amber-300">
                                  {(lane.peak_occupancy * 100).toFixed(1)}%
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-slate-400">
                                  {lane.average_density.toFixed(3)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <EmptyState
                        title="No Lane Records Found"
                        description="No lane analysis records exist for the selected filter parameters."
                      />
                    )}
                  </CardContent>
                </Card>
              )}

              {/* TAB 5: OBSERVED PEAKS */}
              {activeTab === 'peaks' && peaks && (
                <div className="space-y-4">
                  {/* Tie Breaking Alert */}
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 font-mono">
                    <Info className="h-4 w-4 text-cyan-400 shrink-0" />
                    <span>Deterministic Peak Selection Rule: {peaks.tie_breaking_rule}</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Peak Flow Rate */}
                    <Card className="border-slate-800 bg-slate-900/90 shadow-md">
                      <CardHeader className="pb-2 border-b border-slate-800/60">
                        <CardTitle className="text-sm font-bold text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <Flame className="h-4 w-4 text-rose-400" />
                            Peak Flow Rate
                          </span>
                          <Badge variant="danger" size="sm">
                            Flow Max
                          </Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-4 space-y-3">
                        {peaks.peak_flow ? (
                          <>
                            <div className="text-2xl font-bold font-mono text-rose-400">
                              {peaks.peak_flow.value.toFixed(1)}{' '}
                              <span className="text-xs text-slate-400 font-normal">
                                {peaks.peak_flow.unit}
                              </span>
                            </div>
                            <div className="space-y-1 text-xs text-slate-400 border-t border-slate-800/60 pt-2">
                              <div>
                                Window: {formatDate(peaks.peak_flow.start_time)} &rarr;{' '}
                                {formatDate(peaks.peak_flow.end_time)}
                              </div>
                              {peaks.peak_flow.details && <div>{peaks.peak_flow.details}</div>}
                              {peaks.peak_flow.source_name && (
                                <div>Source: {peaks.peak_flow.source_name}</div>
                              )}
                            </div>
                          </>
                        ) : (
                          <div className="text-xs text-slate-500">No peak flow observed</div>
                        )}
                      </CardContent>
                    </Card>

                    {/* Peak Volume */}
                    <Card className="border-slate-800 bg-slate-900/90 shadow-md">
                      <CardHeader className="pb-2 border-b border-slate-800/60">
                        <CardTitle className="text-sm font-bold text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <Car className="h-4 w-4 text-cyan-400" />
                            Peak Vehicle Volume
                          </span>
                          <Badge variant="info" size="sm">
                            Volume Max
                          </Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-4 space-y-3">
                        {peaks.peak_volume ? (
                          <>
                            <div className="text-2xl font-bold font-mono text-cyan-400">
                              {peaks.peak_volume.value}{' '}
                              <span className="text-xs text-slate-400 font-normal">
                                {peaks.peak_volume.unit}
                              </span>
                            </div>
                            <div className="space-y-1 text-xs text-slate-400 border-t border-slate-800/60 pt-2">
                              <div>
                                Window: {formatDate(peaks.peak_volume.start_time)} &rarr;{' '}
                                {formatDate(peaks.peak_volume.end_time)}
                              </div>
                              {peaks.peak_volume.details && (
                                <div>{peaks.peak_volume.details}</div>
                              )}
                              {peaks.peak_volume.source_name && (
                                <div>Source: {peaks.peak_volume.source_name}</div>
                              )}
                            </div>
                          </>
                        ) : (
                          <div className="text-xs text-slate-500">No peak volume observed</div>
                        )}
                      </CardContent>
                    </Card>

                    {/* Peak Density */}
                    <Card className="border-slate-800 bg-slate-900/90 shadow-md">
                      <CardHeader className="pb-2 border-b border-slate-800/60">
                        <CardTitle className="text-sm font-bold text-white flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <Activity className="h-4 w-4 text-amber-400" />
                            Peak Image Density
                          </span>
                          <Badge variant="warning" size="sm">
                            Heuristic Max
                          </Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-4 space-y-3">
                        {peaks.peak_density ? (
                          <>
                            <div className="text-2xl font-bold font-mono text-amber-400">
                              {peaks.peak_density.value.toFixed(3)}{' '}
                              <span className="text-xs text-slate-400 font-normal">
                                {peaks.peak_density.unit}
                              </span>
                            </div>
                            <div className="space-y-1 text-xs text-slate-400 border-t border-slate-800/60 pt-2">
                              <div>
                                Window: {formatDate(peaks.peak_density.start_time)} &rarr;{' '}
                                {formatDate(peaks.peak_density.end_time)}
                              </div>
                              {peaks.peak_density.details && (
                                <div>{peaks.peak_density.details}</div>
                              )}
                              <div className="text-[10px] text-amber-500/80">
                                Image-space bbox area ratio heuristic
                              </div>
                            </div>
                          </>
                        ) : (
                          <div className="text-xs text-slate-500">No peak density observed</div>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </div>
              )}

              {/* TAB 6: ANOMALY HISTORY */}
              {activeTab === 'anomalies' && anomalies && (
                <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
                  <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
                    <div>
                      <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-rose-400" />
                        <span>Observed Anomalies & Incident Records</span>
                      </CardTitle>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Phase 15 anomaly detector observations aggregated across the selected range.
                      </p>
                    </div>
                    <Badge variant="danger" size="sm">
                      {anomalies.total_anomalies} Total Incidents
                    </Badge>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-6">
                    {/* Summary Row */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {Object.entries(anomalies.by_severity).map(([sev, cnt]) => (
                        <div
                          key={sev}
                          className="p-3 rounded-lg bg-slate-950/60 border border-slate-800"
                        >
                          <span className="text-[11px] font-medium text-slate-400 uppercase">
                            {sev} Severity
                          </span>
                          <div className="text-lg font-bold font-mono text-rose-400">{cnt}</div>
                        </div>
                      ))}
                    </div>

                    {/* Recent Incident List */}
                    {anomalies.incidents.length > 0 ? (
                      <div className="border border-slate-800 rounded-xl overflow-hidden">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-950/70 text-slate-400 border-b border-slate-800 font-medium">
                            <tr>
                              <th className="px-4 py-2.5">Time</th>
                              <th className="px-4 py-2.5">Type</th>
                              <th className="px-4 py-2.5">Severity</th>
                              <th className="px-4 py-2.5">Status</th>
                              <th className="px-4 py-2.5">Description</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800">
                            {anomalies.incidents.map((anom) => (
                              <tr key={anom.id} className="hover:bg-slate-800/40">
                                <td className="px-4 py-2.5 font-mono text-slate-400 whitespace-nowrap">
                                  {formatDate(anom.created_at)}
                                </td>
                                <td className="px-4 py-2.5 font-semibold text-slate-200 capitalize">
                                  {anom.anomaly_type.replace('_', ' ')}
                                </td>
                                <td className="px-4 py-2.5">
                                  <Badge
                                    variant={
                                      anom.severity === 'critical'
                                        ? 'danger'
                                        : anom.severity === 'high'
                                        ? 'warning'
                                        : 'info'
                                    }
                                    size="sm"
                                  >
                                    {anom.severity.toUpperCase()}
                                  </Badge>
                                </td>
                                <td className="px-4 py-2.5">
                                  <span className="text-slate-400 uppercase text-[10px] font-mono">
                                    {anom.status}
                                  </span>
                                </td>
                                <td className="px-4 py-2.5 text-slate-300 truncate max-w-xs">
                                  {anom.description}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <EmptyState
                        title="No Incidents Logged"
                        description="No anomaly events detected in the active time window."
                      />
                    )}
                  </CardContent>
                </Card>
              )}

              {/* TAB 7: SOURCE COMPARISON */}
              {activeTab === 'sources' && sourceComparison && (
                <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
                  <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
                    <div>
                      <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                        <Radio className="h-5 w-5 text-cyan-400" />
                        <span>Source Comparison & Multi-Camera Breakdown</span>
                      </CardTitle>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Observed traffic metrics grouped across individual video and camera sources.
                      </p>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-4">
                    {sourceComparison.sources.length > 0 ? (
                      <div className="border border-slate-800 rounded-xl overflow-hidden">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-950/70 text-slate-400 border-b border-slate-800 font-medium">
                            <tr>
                              <th className="px-4 py-2.5">Source Name</th>
                              <th className="px-4 py-2.5">Type</th>
                              <th className="px-4 py-2.5 text-right">Sessions</th>
                              <th className="px-4 py-2.5 text-right">Volume</th>
                              <th className="px-4 py-2.5 text-right">Avg Flow Rate</th>
                              <th className="px-4 py-2.5 text-right">Duration</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800">
                            {sourceComparison.sources.map((src) => (
                              <tr key={src.source_id} className="hover:bg-slate-800/40">
                                <td className="px-4 py-2.5 font-medium text-slate-200">
                                  {src.source_name}
                                </td>
                                <td className="px-4 py-2.5">
                                  <Badge
                                    variant={src.source_type === 'camera' ? 'info' : 'outline'}
                                    size="sm"
                                  >
                                    {src.source_type}
                                  </Badge>
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-slate-300">
                                  {src.session_count}
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-cyan-400 font-semibold">
                                  {src.total_volume}
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-indigo-300">
                                  {src.average_flow_rate_vph.toFixed(1)} vph
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-slate-400">
                                  {formatDuration(src.total_duration_seconds)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <EmptyState
                        title="No Source Records Found"
                        description="No individual sources recorded traffic in this time period."
                      />
                    )}
                  </CardContent>
                </Card>
              )}

              {/* TAB 8: PERIOD COMPARISON */}
              {activeTab === 'comparison' && periodComparison && (
                <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
                  <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
                    <div>
                      <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-cyan-400" />
                        <span>Period-over-Period Delta Analysis</span>
                      </CardTitle>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Direct comparison between active window and preceding equivalent period.
                      </p>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-6">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      {/* Metric 1: Volume Delta */}
                      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
                        <span className="text-xs font-medium text-slate-400">Traffic Volume</span>
                        <div className="flex items-baseline justify-between mt-2">
                          <div className="text-xl font-bold font-mono text-white">
                            {periodComparison.volume_comparison.current_value} veh
                          </div>
                          <div
                            className={`flex items-center gap-1 text-xs font-mono font-bold ${
                              (periodComparison.volume_comparison.percentage_change || 0) >= 0
                                ? 'text-emerald-400'
                                : 'text-rose-400'
                            }`}
                          >
                            {(periodComparison.volume_comparison.percentage_change || 0) >= 0 ? (
                              <TrendingUp className="h-3.5 w-3.5" />
                            ) : (
                              <TrendingDown className="h-3.5 w-3.5" />
                            )}
                            <span>
                              {(periodComparison.volume_comparison.percentage_change || 0) >= 0
                                ? '+'
                                : ''}
                              {(
                                periodComparison.volume_comparison.percentage_change || 0
                              ).toFixed(1)}
                              %
                            </span>
                          </div>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-1">
                          Prior: {periodComparison.volume_comparison.previous_value} veh
                        </div>
                      </div>

                      {/* Metric 2: Flow Rate Delta */}
                      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
                        <span className="text-xs font-medium text-slate-400">Average Flow Rate</span>
                        <div className="flex items-baseline justify-between mt-2">
                          <div className="text-xl font-bold font-mono text-indigo-300">
                            {periodComparison.flow_rate_comparison.current_value.toFixed(1)}/min
                          </div>
                          <div
                            className={`flex items-center gap-1 text-xs font-mono font-bold ${
                              (periodComparison.flow_rate_comparison.percentage_change || 0) >= 0
                                ? 'text-emerald-400'
                                : 'text-rose-400'
                            }`}
                          >
                            {(periodComparison.flow_rate_comparison.percentage_change || 0) >= 0 ? (
                              <TrendingUp className="h-3.5 w-3.5" />
                            ) : (
                              <TrendingDown className="h-3.5 w-3.5" />
                            )}
                            <span>
                              {(periodComparison.flow_rate_comparison.percentage_change || 0) >= 0
                                ? '+'
                                : ''}
                              {(
                                periodComparison.flow_rate_comparison.percentage_change || 0
                              ).toFixed(1)}
                              %
                            </span>
                          </div>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-1">
                          Prior: {periodComparison.flow_rate_comparison.previous_value.toFixed(1)}/min
                        </div>
                      </div>

                      {/* Metric 3: Analyzed Sessions */}
                      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
                        <span className="text-xs font-medium text-slate-400">Sessions Count</span>
                        <div className="text-xl font-bold font-mono text-amber-300 mt-2">
                          {periodComparison.session_comparison.current_value}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-1">
                          Prior: {periodComparison.session_comparison.previous_value} sessions
                        </div>
                      </div>

                      {/* Metric 4: Duration */}
                      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
                        <span className="text-xs font-medium text-slate-400">Observed Duration</span>
                        <div className="text-xl font-bold font-mono text-emerald-400 mt-2">
                          {formatDuration(
                            periodComparison.duration_comparison.current_value
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-1">
                          Prior:{' '}
                          {formatDuration(
                            periodComparison.duration_comparison.previous_value
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default HistoricalAnalyticsPage;
