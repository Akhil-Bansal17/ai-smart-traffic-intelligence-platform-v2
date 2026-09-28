import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRightLeft,
  BarChart3,
  Car,
  CheckCircle2,
  ChevronRight,
  Clock,
  Flame,
  Info,
  Layers,
  LineChart,
  Network,
  Radio,
  RotateCw,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Truck,
} from 'lucide-react';

import {
  compareTrafficSources,
  getNetworkDirectionalAnalysis,
  getNetworkHistoricalComparison,
  getNetworkLaneAnalysis,
  getNetworkOverview,
  getNetworkTemporalAnalysis,
  getNetworkVehicleComposition,
  getTrafficHotspots,
} from '@/api/networkIntelligence';
import { listCameraSources } from '@/api/cameraSources';
import {
  NetworkDirectionalResponse,
  NetworkFilterParams,
  NetworkHotspotResponse,
  NetworkLaneResponse,
  NetworkOverviewResponse,
  NetworkSourceComparisonResponse,
  NetworkTemporalAnalysisResponse,
  NetworkVehicleCompositionResponse,
  PeriodComparisonResponse,
} from '@/types/networkIntelligence';
import { CameraSource } from '@/types/camera';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';

type TimePreset = '24h' | '7d' | '30d' | '90d' | 'custom';
type ActiveTab =
  | 'comparison'
  | 'hotspots'
  | 'composition'
  | 'directional'
  | 'lanes'
  | 'temporal'
  | 'historical';

export function NetworkIntelligencePage() {
  // Filter States
  const [preset, setPreset] = useState<TimePreset>('7d');
  const [startTime, setStartTime] = useState<string>('');
  const [endTime, setEndTime] = useState<string>('');
  const [selectedSourceId, setSelectedSourceId] = useState<string>('all');
  const [includeSynthetic, setIncludeSynthetic] = useState<boolean>(true);
  const [bucketInterval, setBucketInterval] = useState<string>('hourly');

  // Active Tab
  const [activeTab, setActiveTab] = useState<ActiveTab>('comparison');

  // Registered Sources for Filter Dropdown
  const [cameraSources, setCameraSources] = useState<CameraSource[]>([]);

  // Analytics Data States
  const [overview, setOverview] = useState<NetworkOverviewResponse | null>(null);
  const [comparison, setComparison] = useState<NetworkSourceComparisonResponse | null>(null);
  const [hotspots, setHotspots] = useState<NetworkHotspotResponse | null>(null);
  const [composition, setComposition] = useState<NetworkVehicleCompositionResponse | null>(null);
  const [directional, setDirectional] = useState<NetworkDirectionalResponse | null>(null);
  const [laneData, setLaneData] = useState<NetworkLaneResponse | null>(null);
  const [temporal, setTemporal] = useState<NetworkTemporalAnalysisResponse | null>(null);
  const [historicalComp, setHistoricalComp] = useState<PeriodComparisonResponse | null>(null);

  // Status States
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load camera sources list for filter
  useEffect(() => {
    async function loadSources() {
      try {
        const res = await listCameraSources();
        setCameraSources(res.items || []);
      } catch (err) {
        console.error('Failed to load camera sources for network intelligence filter:', err);
      }
    }
    loadSources();
  }, []);

  // Compute ISO time range based on preset or custom
  const getFilterParams = useCallback((): NetworkFilterParams => {
    const params: NetworkFilterParams = {
      time_preset: preset,
      include_synthetic: includeSynthetic,
      bucket_interval: bucketInterval,
    };

    if (preset === 'custom') {
      if (startTime) params.start_time = new Date(startTime).toISOString();
      if (endTime) params.end_time = new Date(endTime).toISOString();
    }

    if (selectedSourceId && selectedSourceId !== 'all') {
      params.source_ids = [selectedSourceId];
    }

    return params;
  }, [preset, startTime, endTime, selectedSourceId, includeSynthetic, bucketInterval]);

  // Fetch all network intelligence data
  const fetchData = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      const params = getFilterParams();

      try {
        const [
          overviewRes,
          compRes,
          hotspotsRes,
          compDataRes,
          dirRes,
          laneRes,
          temporalRes,
          histRes,
        ] = await Promise.all([
          getNetworkOverview(params),
          compareTrafficSources(params),
          getTrafficHotspots(params, 15),
          getNetworkVehicleComposition(params),
          getNetworkDirectionalAnalysis(params),
          getNetworkLaneAnalysis(params),
          getNetworkTemporalAnalysis(params),
          getNetworkHistoricalComparison(params).catch(() => null),
        ]);

        setOverview(overviewRes);
        setComparison(compRes);
        setHotspots(hotspotsRes);
        setComposition(compDataRes);
        setDirectional(dirRes);
        setLaneData(laneRes);
        setTemporal(temporalRes);
        setHistoricalComp(histRes);
      } catch (err: any) {
        console.error('Failed to fetch network intelligence:', err);
        setError(err.message || 'Failed to load network intelligence analytics.');
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [getFilterParams]
  );

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Helper for provenance badge variant
  const getProvenanceBadgeClass = (variant: string) => {
    switch (variant) {
      case 'success':
        return 'bg-emerald-950/80 text-emerald-400 border-emerald-800/80';
      case 'purple':
        return 'bg-purple-950/80 text-purple-300 border-purple-800/80';
      case 'warning':
        return 'bg-amber-950/80 text-amber-400 border-amber-800/80';
      case 'danger':
        return 'bg-rose-950/80 text-rose-400 border-rose-800/80';
      default:
        return 'bg-slate-800/80 text-slate-300 border-slate-700/80';
    }
  };

  const getEpistemicBadgeClass = (status: string) => {
    switch (status) {
      case 'OBSERVED':
        return 'bg-cyan-950/80 text-cyan-300 border-cyan-800/80';
      case 'DERIVED':
        return 'bg-indigo-950/80 text-indigo-300 border-indigo-800/80';
      case 'EXTRAPOLATED':
        return 'bg-amber-950/80 text-amber-300 border-amber-800/80';
      default:
        return 'bg-slate-800/80 text-slate-400 border-slate-700/80';
    }
  };

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev) {
      case 'critical':
        return 'bg-rose-950/80 text-rose-300 border-rose-800/80';
      case 'high':
        return 'bg-amber-950/80 text-amber-300 border-amber-800/80';
      case 'medium':
        return 'bg-yellow-950/80 text-yellow-300 border-yellow-800/80';
      default:
        return 'bg-blue-950/80 text-blue-300 border-blue-800/80';
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        <LoadingState message="Aggregating network intelligence across traffic sources..." />
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        <ErrorState message={error} onRetry={() => fetchData()} />
      </div>
    );
  }

  const provenance = overview?.provenance;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto text-slate-100">
      {/* --------------------------------------------------------------------- */}
      {/* Page Header & Meta Status */}
      {/* --------------------------------------------------------------------- */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-950/70 border border-cyan-800/60 text-cyan-400 shadow-sm">
              <Network className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white">
                  Network Intelligence
                </h1>
                <Badge variant="outline" size="sm" className="font-mono text-cyan-400 border-cyan-800/60 bg-cyan-950/40">
                  Phase 24
                </Badge>
                {overview && (
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold border ${getEpistemicBadgeClass(
                      overview.epistemic_status
                    )}`}
                  >
                    {overview.epistemic_status}
                  </span>
                )}
                {provenance && (
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold border ${getProvenanceBadgeClass(
                      provenance.provenance_badge_variant
                    )}`}
                  >
                    {provenance.provenance_label}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Cross-camera operations analytics, traffic hotspots, source comparison, and multi-source intelligence
              </p>
            </div>
          </div>
        </div>

        {/* Global Actions */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="border-slate-700 bg-slate-800/50 hover:bg-slate-800 text-slate-300"
          >
            <RotateCw className={`h-3.5 w-3.5 mr-1.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            {refreshing ? 'Updating...' : 'Refresh'}
          </Button>

          <Link to="/operations">
            <Button size="sm" variant="outline" className="border-slate-700 text-slate-300 hover:text-white">
              <ShieldAlert className="h-3.5 w-3.5 mr-1.5 text-rose-400" />
              Operations Center
            </Button>
          </Link>
          <Link to="/historical-analytics">
            <Button size="sm" variant="outline" className="border-slate-700 text-slate-300 hover:text-white">
              <LineChart className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />
              Historical Analytics
            </Button>
          </Link>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* Filter Toolbar */}
      {/* --------------------------------------------------------------------- */}
      <Card className="bg-[#0f172a]/80 border-slate-800/80 shadow-md">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            {/* Presets */}
            <div className="flex items-center gap-1.5 bg-slate-900/90 p-1 rounded-lg border border-slate-800">
              {(['24h', '7d', '30d', '90d', 'custom'] as TimePreset[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPreset(p)}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                    preset === p
                      ? 'bg-cyan-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  {p.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Custom Date Pickers */}
            {preset === 'custom' && (
              <div className="flex items-center gap-2 text-xs">
                <input
                  type="datetime-local"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
                />
                <span className="text-slate-500">to</span>
                <input
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
                />
              </div>
            )}

            {/* Source Filter */}
            <div className="flex items-center gap-2">
              <label htmlFor="source-filter-select" className="text-xs text-slate-400 font-medium">Source:</label>
              <select
                id="source-filter-select"
                aria-label="Filter traffic sources"
                value={selectedSourceId}
                onChange={(e) => setSelectedSourceId(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Sources ({overview?.total_sources || cameraSources.length})</option>
                {cameraSources.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} {s.location_name ? `(${s.location_name})` : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Temporal Bucket Interval */}
            <div className="flex items-center gap-2">
              <label htmlFor="bucket-interval-select" className="text-xs text-slate-400 font-medium">Bucket:</label>
              <select
                id="bucket-interval-select"
                aria-label="Temporal bucket interval"
                value={bucketInterval}
                onChange={(e) => setBucketInterval(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
              </select>
            </div>

            {/* Include Synthetic Toggle */}
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={includeSynthetic}
                onChange={(e) => setIncludeSynthetic(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-600 focus:ring-0 focus:ring-offset-0"
              />
              <span>Include Test Fixtures</span>
            </label>
          </div>
        </CardContent>
      </Card>

      {/* --------------------------------------------------------------------- */}
      {/* Network KPI Cards (6 Key Operational Metrics) */}
      {/* --------------------------------------------------------------------- */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Card 1: Total Volume */}
        <Card className="bg-[#0f172a]/90 border-slate-800 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-cyan-500/80" />
          <CardContent className="p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Observed Volume</span>
              <Car className="h-3.5 w-3.5 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold text-white font-mono">
              {overview?.total_volume?.toLocaleString() || 0}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1 truncate">
              <span className="text-cyan-400 font-mono font-medium">{overview?.flow_rate_per_hour || 0}</span> vph
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Monitored Sources */}
        <Card className="bg-[#0f172a]/90 border-slate-800 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-emerald-500/80" />
          <CardContent className="p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Active Sources</span>
              <Radio className="h-3.5 w-3.5 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-white font-mono">
              {overview?.active_sources_count || 0}
              <span className="text-xs font-normal text-slate-500 ml-1">/ {overview?.total_sources || 0}</span>
            </div>
            <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1 truncate">
              {overview?.session_count || 0} analysis sessions
            </div>
          </CardContent>
        </Card>

        {/* Card 3: Top Hotspot */}
        <Card className="bg-[#0f172a]/90 border-slate-800 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-rose-500/80" />
          <CardContent className="p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Primary Hotspot</span>
              <Flame className="h-3.5 w-3.5 text-rose-400" />
            </div>
            <div className="text-sm font-bold text-white truncate max-w-[150px] mt-1.5" title={overview?.top_hotspot_source_name || 'None'}>
              {overview?.top_hotspot_source_name || 'None'}
            </div>
            <div className="text-[11px] text-slate-400 mt-2 truncate">
              {hotspots?.total_hotspots_identified || 0} active hotspot(s)
            </div>
          </CardContent>
        </Card>

        {/* Card 4: Active Incidents */}
        <Card className="bg-[#0f172a]/90 border-slate-800 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-amber-500/80" />
          <CardContent className="p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Active Incidents</span>
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-white font-mono">
              {overview?.active_incident_count || 0}
            </div>
            <div className="text-[11px] text-amber-400/90 mt-1 truncate">
              {overview?.recurring_incident_locations_count || 0} recurring source(s)
            </div>
          </CardContent>
        </Card>

        {/* Card 5: Directional Balance */}
        <Card className="bg-[#0f172a]/90 border-slate-800 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-indigo-500/80" />
          <CardContent className="p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Direction Balance</span>
              <ArrowRightLeft className="h-3.5 w-3.5 text-indigo-400" />
            </div>
            <div className="text-sm font-bold text-indigo-300 font-mono mt-1.5 uppercase">
              {overview?.directional_summary?.balance_status?.replace('_', ' ') || 'BALANCED'}
            </div>
            <div className="text-[11px] text-slate-400 mt-2">
              Ratio: <span className="font-mono text-slate-200">{overview?.directional_summary?.directional_ratio || 1.0}</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 6: Lane Utilization */}
        <Card className="bg-[#0f172a]/90 border-slate-800 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-purple-500/80" />
          <CardContent className="p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Lanes Active</span>
              <Layers className="h-3.5 w-3.5 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-white font-mono">
              {overview?.lane_summary?.total_lanes || 0}
            </div>
            <div className="text-[11px] text-purple-300/90 mt-1 truncate" title={overview?.lane_summary?.busiest_lane_name || 'N/A'}>
              {overview?.lane_summary?.busiest_lane_name ? `Peak: ${overview.lane_summary.busiest_lane_name}` : 'No lane records'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* Navigation Tabs */}
      {/* --------------------------------------------------------------------- */}
      <div className="border-b border-slate-800 flex items-center gap-2 overflow-x-auto pb-px">
        <button
          onClick={() => setActiveTab('comparison')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'comparison'
              ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <BarChart3 className="h-4 w-4" />
          <span>Source Comparison</span>
          {comparison && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-800 text-slate-300 font-mono">
              {comparison.sources.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('hotspots')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'hotspots'
              ? 'border-rose-500 text-rose-400 bg-rose-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <Flame className="h-4 w-4" />
          <span>Traffic Hotspots</span>
          {hotspots && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-rose-950/60 text-rose-300 border border-rose-800/40 font-mono">
              {hotspots.total_hotspots_identified}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('composition')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'composition'
              ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <Car className="h-4 w-4" />
          <span>Vehicle Composition</span>
        </button>

        <button
          onClick={() => setActiveTab('directional')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'directional'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <ArrowRightLeft className="h-4 w-4" />
          <span>Directional Balance</span>
        </button>

        <button
          onClick={() => setActiveTab('lanes')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'lanes'
              ? 'border-purple-500 text-purple-400 bg-purple-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <Layers className="h-4 w-4" />
          <span>Lane Intelligence</span>
        </button>

        <button
          onClick={() => setActiveTab('temporal')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'temporal'
              ? 'border-amber-500 text-amber-400 bg-amber-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <Clock className="h-4 w-4" />
          <span>Temporal Analysis</span>
        </button>

        <button
          onClick={() => setActiveTab('historical')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'historical'
              ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <TrendingUp className="h-4 w-4" />
          <span>Period Comparison</span>
        </button>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* Tab 1: Source Comparison */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'comparison' && (
        <div className="space-y-4">
          {comparison?.window_mismatch_detected && (
            <div className="p-3.5 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-300 text-xs flex items-center gap-2.5">
              <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-400" />
              <div>
                <span className="font-semibold">Observation Window Mismatch: </span>
                <span>
                  {comparison.comparison_notes ||
                    'Some traffic sources have shorter or shifted observation intervals. Variance between metrics reflects differing recording spans.'}
                </span>
              </div>
            </div>
          )}

          <Card className="bg-[#0f172a]/90 border-slate-800">
            <CardHeader className="p-4 border-b border-slate-800 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold text-white">Cross-Source Comparative Analysis</CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Side-by-side volume, flow rate, composition, lanes, and incident metrics across all sources
                </p>
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Busiest: <span className="text-cyan-400 font-medium">{comparison?.busiest_source_name || 'None'}</span>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/80 text-slate-400 font-medium border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">Traffic Source</th>
                      <th className="py-3 px-4">Status / Provenance</th>
                      <th className="py-3 px-4">Observed Volume</th>
                      <th className="py-3 px-4">Flow Rate</th>
                      <th className="py-3 px-4">Dominant Class</th>
                      <th className="py-3 px-4">Direction Balance</th>
                      <th className="py-3 px-4">Lane Utilization</th>
                      <th className="py-3 px-4">Incidents</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {comparison?.sources.map((src) => (
                      <tr key={src.source_id} className="hover:bg-slate-800/30 transition-colors">
                        {/* Source Name */}
                        <td className="py-3 px-4">
                          <div className="font-medium text-white flex items-center gap-1.5">
                            <span>{src.source_name}</span>
                            {src.window_mismatch && (
                              <span title={src.window_mismatch_details || 'Window mismatch'}>
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-400 truncate max-w-[200px]">
                            {src.location_name || `Type: ${src.source_type}`}
                          </div>
                        </td>

                        {/* Status / Provenance */}
                        <td className="py-3 px-4">
                          <div className="flex flex-col gap-1">
                            <span className="text-[10px] font-mono text-slate-300">
                              {src.status.toUpperCase()}
                            </span>
                            <span
                              className={`inline-flex px-1.5 py-0.2 rounded text-[9px] font-mono w-fit border ${
                                src.provenance_label === 'REAL DATA'
                                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                                  : 'bg-purple-950/60 text-purple-300 border-purple-800/60'
                              }`}
                            >
                              {src.provenance_label}
                            </span>
                          </div>
                        </td>

                        {/* Volume */}
                        <td className="py-3 px-4">
                          <div className="font-mono font-medium text-white">{src.observed_volume.toLocaleString()}</div>
                          <div className="text-[10px] text-slate-500 font-mono">{src.session_count} sessions</div>
                        </td>

                        {/* Flow Rate */}
                        <td className="py-3 px-4 font-mono">
                          <span className="text-cyan-400 font-medium">{src.flow_rate_per_hour}</span> vph
                        </td>

                        {/* Dominant Class */}
                        <td className="py-3 px-4">
                          {src.dominant_vehicle_class ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                              <Car className="h-3 w-3 text-cyan-400" />
                              {src.dominant_vehicle_class}
                            </span>
                          ) : (
                            <span className="text-slate-500 font-mono text-[10px]">None</span>
                          )}
                        </td>

                        {/* Direction Balance */}
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded text-[10px] font-mono border ${
                              src.directional_balance === 'balanced'
                                ? 'bg-indigo-950/50 text-indigo-300 border-indigo-800/50'
                                : 'bg-amber-950/50 text-amber-300 border-amber-800/50'
                            }`}
                          >
                            {src.directional_balance.replace('_', ' ')}
                          </span>
                          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                            In: {src.inbound_count} | Out: {src.outbound_count}
                          </div>
                        </td>

                        {/* Lane Utilization */}
                        <td className="py-3 px-4">
                          {src.has_lane_data ? (
                            <div>
                              <div className="text-slate-300 font-medium">{src.busiest_lane_name || `${src.lane_count} lanes`}</div>
                              <div className="text-[10px] text-slate-500 font-mono">
                                Density: {src.average_lane_density !== null ? src.average_lane_density : 'N/A'}
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-500 text-[10px] font-mono">UNAVAILABLE</span>
                          )}
                        </td>

                        {/* Incidents */}
                        <td className="py-3 px-4">
                          <div className="font-mono font-medium">
                            <span className={src.incident_count > 0 ? 'text-rose-400' : 'text-slate-400'}>
                              {src.incident_count}
                            </span>
                            <span className="text-slate-500 text-[10px]"> active</span>
                          </div>
                          {src.recurring_incident_count > 0 && (
                            <div className="text-[10px] text-amber-400 font-mono">
                              {src.recurring_incident_count} recurring
                            </div>
                          )}
                        </td>

                        {/* Actions Drilldown */}
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Link
                              to={`/operations`}
                              title="Inspect in Operations Center"
                              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-400"
                            >
                              <ShieldAlert className="h-3.5 w-3.5" />
                            </Link>
                            <Link
                              to={`/historical-analytics?camera_source_id=${src.source_id}`}
                              title="View Historical Analytics"
                              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-indigo-400"
                            >
                              <LineChart className="h-3.5 w-3.5" />
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {(!comparison || comparison.sources.length === 0) && (
                      <tr>
                        <td colSpan={9} className="py-8 text-center text-slate-500">
                          No traffic source comparison records found for this time window.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* Tab 2: Traffic Hotspot Analysis */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'hotspots' && (
        <div className="space-y-4">
          <div className="p-3.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-300 flex items-start gap-2.5">
            <Info className="h-4 w-4 text-cyan-400 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-white">Evidence-Based Hotspot Determination: </span>
              <span>{hotspots?.epistemic_note}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {hotspots?.hotspots.map((hs) => (
              <Card key={hs.source_id} className="bg-[#0f172a]/90 border-slate-800 relative overflow-hidden">
                <div
                  className={`absolute top-0 left-0 right-0 h-[3px] ${
                    hs.severity === 'critical'
                      ? 'bg-rose-500'
                      : hs.severity === 'high'
                      ? 'bg-amber-500'
                      : hs.severity === 'medium'
                      ? 'bg-yellow-500'
                      : 'bg-blue-500'
                  }`}
                />
                <CardHeader className="p-4 pb-2 flex flex-row items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="h-6 w-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-mono font-bold text-white">
                      #{hs.rank}
                    </span>
                    <div>
                      <CardTitle className="text-sm font-semibold text-white truncate max-w-[180px]">
                        {hs.source_name}
                      </CardTitle>
                      <div className="text-[11px] text-slate-400">{hs.location_name || hs.hotspot_type}</div>
                    </div>
                  </div>
                  <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-mono font-bold border uppercase ${getSeverityBadgeClass(hs.severity)}`}>
                    {hs.severity}
                  </span>
                </CardHeader>

                <CardContent className="p-4 pt-2 space-y-3">
                  {/* Hotspot Intensity Meter */}
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Hotspot Intensity Score</span>
                      <span className="font-mono font-bold text-white">{hs.hotspot_score} / 100</span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all rounded-full ${
                          hs.hotspot_score >= 70
                            ? 'bg-rose-500'
                            : hs.hotspot_score >= 45
                            ? 'bg-amber-500'
                            : hs.hotspot_score >= 20
                            ? 'bg-yellow-500'
                            : 'bg-blue-500'
                        }`}
                        style={{ width: `${Math.min(100, hs.hotspot_score)}%` }}
                      />
                    </div>
                  </div>

                  {/* Primary Factor Banner */}
                  <div className="p-2 rounded bg-slate-900/80 border border-slate-800 text-[11px] text-slate-300">
                    <span className="text-slate-400 font-medium">Primary Factor: </span>
                    <span className="text-white font-medium">{hs.primary_contributing_factor}</span>
                  </div>

                  {/* Metrics grid */}
                  <div className="grid grid-cols-3 gap-2 text-center text-xs py-1">
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <div className="text-[10px] text-slate-400">Incidents</div>
                      <div className="font-mono font-bold text-rose-400 mt-0.5">{hs.incident_count}</div>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <div className="text-[10px] text-slate-400">Volume</div>
                      <div className="font-mono font-bold text-white mt-0.5">{hs.observed_volume.toLocaleString()}</div>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <div className="text-[10px] text-slate-400">Flow Rate</div>
                      <div className="font-mono font-bold text-cyan-400 mt-0.5">{hs.flow_rate_per_hour}</div>
                    </div>
                  </div>

                  {/* Contributing Factors Checklist */}
                  <div className="space-y-1">
                    <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
                      Contributing Evidence
                    </div>
                    {hs.contributing_factors.map((factor, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-[11px] text-slate-300">
                        <CheckCircle2 className="h-3 w-3 text-cyan-400 flex-shrink-0" />
                        <span className="truncate">{factor}</span>
                      </div>
                    ))}
                  </div>

                  {/* Action Link */}
                  <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">{hs.provenance_label}</span>
                    <Link
                      to={`/operations`}
                      className="text-xs text-cyan-400 hover:text-cyan-300 font-medium inline-flex items-center gap-1"
                    >
                      <span>Investigate in Ops</span>
                      <ChevronRight className="h-3 w-3" />
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}

            {(!hotspots || hotspots.hotspots.length === 0) && (
              <div className="col-span-full">
                <Card className="bg-[#0f172a]/90 border-slate-800">
                  <CardContent className="p-8 text-center text-slate-400">
                    <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
                    <div className="text-sm font-semibold text-white">No Traffic Hotspots Identified</div>
                    <p className="text-xs text-slate-500 mt-1">
                      No recurring operational incidents, abnormal congestion anomalies, or elevated flow concentrations
                      were detected across the selected observation window.
                    </p>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* Tab 3: Vehicle Composition */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'composition' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Network-wide distribution */}
            <Card className="bg-[#0f172a]/90 border-slate-800">
              <CardHeader className="p-4 border-b border-slate-800">
                <CardTitle className="text-sm font-semibold text-white">Network-Wide Vehicle Distribution</CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Breakdown across 5 supported YOLO object detection classes
                </p>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                <div className="space-y-3">
                  {composition?.classes.map((c) => (
                    <div key={c.class_name} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-300 capitalize">{c.class_name}</span>
                        <div className="flex items-center gap-2 font-mono">
                          <span className="text-white font-bold">{c.count.toLocaleString()}</span>
                          <span className="text-slate-400">({c.percentage}%)</span>
                        </div>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-cyan-500 rounded-full"
                          style={{ width: `${Math.min(100, c.percentage)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="p-3 rounded bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-slate-300">
                    <Truck className="h-4 w-4 text-amber-400" />
                    <span>Heavy Commercial Vehicle Share (Trucks + Buses)</span>
                  </div>
                  <span className="font-mono font-bold text-amber-300">
                    {composition?.heavy_vehicle_percentage || 0}%
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Dominant classes per source */}
            <Card className="bg-[#0f172a]/90 border-slate-800">
              <CardHeader className="p-4 border-b border-slate-800">
                <CardTitle className="text-sm font-semibold text-white">Source-Level Class Dominance</CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Identifies primary vehicle classes dominating each traffic feed
                </p>
              </CardHeader>
              <CardContent className="p-4">
                <div className="space-y-2.5">
                  {comparison?.sources.map((src) => {
                    const dom = composition?.source_dominant_classes[src.source_id] || 'car';
                    const srcComp = composition?.source_composition[src.source_id] || {};
                    const totalSrcVehicles = Object.values(srcComp).reduce((a, b) => a + b, 0);

                    return (
                      <div
                        key={src.source_id}
                        className="p-2.5 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs"
                      >
                        <div>
                          <div className="font-medium text-white">{src.source_name}</div>
                          <div className="text-[10px] text-slate-500 font-mono">
                            {totalSrcVehicles.toLocaleString()} vehicles observed
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-slate-400">Dominant:</span>
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 capitalize">
                            <Car className="h-3 w-3 text-cyan-400" />
                            {dom}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                  {(!comparison || comparison.sources.length === 0) && (
                    <div className="text-center py-6 text-slate-500 text-xs">No sources available.</div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* Tab 4: Directional Intelligence */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'directional' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Directional Summary Card */}
            <Card className="bg-[#0f172a]/90 border-slate-800">
              <CardHeader className="p-4 border-b border-slate-800">
                <CardTitle className="text-sm font-semibold text-white">Network Flow Balance</CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">Aggregate Inbound vs Outbound volumes</p>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">Inbound Traffic</span>
                    <span className="font-mono font-bold text-white">
                      {directional?.network_summary.inbound_count.toLocaleString()} (
                      {directional?.network_summary.inbound_percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${directional?.network_summary.inbound_percentage || 50}%` }}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">Outbound Traffic</span>
                    <span className="font-mono font-bold text-white">
                      {directional?.network_summary.outbound_count.toLocaleString()} (
                      {directional?.network_summary.outbound_percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full"
                      style={{ width: `${directional?.network_summary.outbound_percentage || 50}%` }}
                    />
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800 text-xs flex items-center justify-between">
                  <span className="text-slate-400">Directional Ratio (In/Out):</span>
                  <span className="font-mono font-bold text-cyan-300">
                    {directional?.network_summary.directional_ratio}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Source Balance Distribution */}
            <Card className="bg-[#0f172a]/90 border-slate-800 md:col-span-2">
              <CardHeader className="p-4 border-b border-slate-800">
                <CardTitle className="text-sm font-semibold text-white">Per-Source Directional Distribution</CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Detailed inbound/outbound breakdown and dominance classification per location
                </p>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto max-h-[350px]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/80 text-slate-400 font-medium border-b border-slate-800 sticky top-0">
                      <tr>
                        <th className="py-2.5 px-4">Source</th>
                        <th className="py-2.5 px-4">Inbound</th>
                        <th className="py-2.5 px-4">Outbound</th>
                        <th className="py-2.5 px-4">Ratio</th>
                        <th className="py-2.5 px-4">Classification</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {directional?.sources.map((src) => (
                        <tr key={src.source_id} className="hover:bg-slate-800/30">
                          <td className="py-2.5 px-4">
                            <div className="font-medium text-white">{src.source_name}</div>
                            <div className="text-[10px] text-slate-500">{src.location_name || 'Camera feed'}</div>
                          </td>
                          <td className="py-2.5 px-4 font-mono text-emerald-400">
                            {src.inbound_count.toLocaleString()} ({src.inbound_percentage}%)
                          </td>
                          <td className="py-2.5 px-4 font-mono text-indigo-400">
                            {src.outbound_count.toLocaleString()} ({src.outbound_percentage}%)
                          </td>
                          <td className="py-2.5 px-4 font-mono text-slate-200">{src.directional_ratio}</td>
                          <td className="py-2.5 px-4">
                            <span
                              className={`inline-flex px-2 py-0.5 rounded text-[10px] font-mono border ${
                                src.balance_status === 'balanced'
                                  ? 'bg-slate-800 text-slate-300 border-slate-700'
                                  : src.balance_status === 'inbound_dominant'
                                  ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                                  : 'bg-indigo-950/60 text-indigo-300 border-indigo-800/60'
                              }`}
                            >
                              {src.balance_status.replace('_', ' ')}
                            </span>
                          </td>
                        </tr>
                      ))}
                      {(!directional || directional.sources.length === 0) && (
                        <tr>
                          <td colSpan={5} className="py-6 text-center text-slate-500">
                            No directional records available.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* Tab 5: Lane Intelligence */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'lanes' && (
        <div className="space-y-4">
          <div className="p-3.5 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-300 text-xs flex items-start gap-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Density Calibration Disclaimer: </span>
              <span>{laneData?.density_calibration_disclaimer}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-[#0f172a]/90 border-slate-800">
              <CardHeader className="p-4 border-b border-slate-800">
                <CardTitle className="text-sm font-semibold text-white">Lane Coverage</CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Total Configured Lanes:</span>
                  <span className="font-mono font-bold text-white text-base">{laneData?.total_lanes || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Sources with Lanes:</span>
                  <span className="font-mono font-bold text-emerald-400">{laneData?.sources_with_lanes_count || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Sources without Lanes:</span>
                  <span className="font-mono font-bold text-slate-500">{laneData?.sources_without_lanes_count || 0}</span>
                </div>
                <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400">
                  Cameras without geometric polygon lane configurations report <span className="font-mono text-cyan-400">UNAVAILABLE</span>.
                </div>
              </CardContent>
            </Card>

            <Card className="bg-[#0f172a]/90 border-slate-800 md:col-span-2">
              <CardHeader className="p-4 border-b border-slate-800">
                <CardTitle className="text-sm font-semibold text-white">Active Lane Intelligence Registry</CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">Authoritative Phase 9 / Phase 22 lane records</p>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto max-h-[350px]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/80 text-slate-400 font-medium border-b border-slate-800 sticky top-0">
                      <tr>
                        <th className="py-2.5 px-4">Lane Name</th>
                        <th className="py-2.5 px-4">Direction</th>
                        <th className="py-2.5 px-4">Observed Vehicles</th>
                        <th className="py-2.5 px-4">Peak Occupancy</th>
                        <th className="py-2.5 px-4">Image Density</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {laneData?.lanes.map((lane) => (
                        <tr key={lane.lane_id} className="hover:bg-slate-800/30">
                          <td className="py-2.5 px-4 font-medium text-white">{lane.lane_name}</td>
                          <td className="py-2.5 px-4 text-slate-400 capitalize">{lane.direction_hint || 'Undirected'}</td>
                          <td className="py-2.5 px-4 font-mono text-white">{lane.total_volume.toLocaleString()}</td>
                          <td className="py-2.5 px-4 font-mono text-cyan-400">{lane.peak_occupancy} veh</td>
                          <td className="py-2.5 px-4 font-mono text-purple-300">{lane.average_density}</td>
                        </tr>
                      ))}
                      {(!laneData || laneData.lanes.length === 0) && (
                        <tr>
                          <td colSpan={5} className="py-6 text-center text-slate-500">
                            No configured lanes found in the database.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* Tab 6: Temporal Cross-Source Analysis */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'temporal' && (
        <div className="space-y-4">
          <div className="p-3.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-300 flex items-start gap-2.5">
            <Info className="h-4 w-4 text-cyan-400 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-white">Temporal Observation Boundaries: </span>
              <span>{temporal?.epistemic_note}</span>
            </div>
          </div>

          <Card className="bg-[#0f172a]/90 border-slate-800">
            <CardHeader className="p-4 border-b border-slate-800 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold text-white">Synchronized Time-Series Buckets</CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Cross-source traffic volume mapped across discrete {temporal?.bucket_interval || 'hourly'} intervals
                </p>
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Concurrent Peaks: <span className="text-amber-400 font-bold">{temporal?.synchronized_peak_buckets_count || 0}</span>
              </div>
            </CardHeader>
            <CardContent className="p-4">
              <div className="space-y-3 max-h-[450px] overflow-y-auto pr-2">
                {temporal?.buckets.map((b) => (
                  <div
                    key={b.bucket_index}
                    className={`p-3 rounded-lg border transition-colors ${
                      b.is_network_peak
                        ? 'bg-amber-950/20 border-amber-800/60'
                        : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/40'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-300 font-medium">
                          {new Date(b.start_time).toLocaleString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        {b.is_network_peak && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800">
                            <Flame className="h-3 w-3 text-amber-400" />
                            NETWORK PEAK
                          </span>
                        )}
                      </div>
                      <div className="font-mono font-bold text-white text-sm">
                        {b.total_volume.toLocaleString()} <span className="text-xs font-normal text-slate-400">veh</span>
                      </div>
                    </div>

                    {/* Breakdown by source */}
                    <div className="flex flex-wrap gap-2 pt-1 border-t border-slate-800/40">
                      {b.sources.map((s) => (
                        <div
                          key={s.source_id}
                          className="px-2 py-1 rounded bg-slate-800/60 border border-slate-700/60 text-[11px] flex items-center gap-1.5"
                        >
                          <span className="text-slate-300 truncate max-w-[120px]">{s.source_name}:</span>
                          <span className="font-mono font-semibold text-cyan-400">{s.volume}</span>
                        </div>
                      ))}
                      {b.sources.length === 0 && (
                        <span className="text-[11px] text-slate-500 italic">No traffic recorded in this bucket.</span>
                      )}
                    </div>
                  </div>
                ))}
                {(!temporal || temporal.buckets.length === 0) && (
                  <div className="text-center py-8 text-slate-500 text-xs">
                    No synchronized temporal buckets available for the selected interval.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* Tab 7: Period Comparison (Phase 22 Reuse) */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'historical' && (
        <div className="space-y-4">
          <Card className="bg-[#0f172a]/90 border-slate-800">
            <CardHeader className="p-4 border-b border-slate-800">
              <CardTitle className="text-sm font-semibold text-white">
                Period-over-Period Delta Analysis
              </CardTitle>
              <p className="text-xs text-slate-400 mt-0.5">
                Authoritative historical comparison comparing current window to preceding comparable window
              </p>
            </CardHeader>
            <CardContent className="p-4">
              {historicalComp ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
                  {/* Volume Comparison */}
                  <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                    <div className="text-xs text-slate-400 font-medium">Traffic Volume</div>
                    <div className="text-xl font-bold font-mono text-white mt-1">
                      {historicalComp.volume_comparison.current_value.toLocaleString()}
                    </div>
                    <div className="flex items-center gap-1 text-xs mt-1 font-mono">
                      {historicalComp.volume_comparison.trend_direction === 'up' ? (
                        <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                      ) : historicalComp.volume_comparison.trend_direction === 'down' ? (
                        <TrendingDown className="h-3.5 w-3.5 text-rose-400" />
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                      <span
                        className={
                          historicalComp.volume_comparison.trend_direction === 'up'
                            ? 'text-emerald-400'
                            : 'text-slate-400'
                        }
                      >
                        {typeof historicalComp.volume_comparison.percentage_change === 'number'
                          ? `${historicalComp.volume_comparison.percentage_change > 0 ? '+' : ''}${
                              historicalComp.volume_comparison.percentage_change
                            }%`
                          : 'N/A'}
                      </span>
                      <span className="text-slate-500 text-[10px]">vs prev</span>
                    </div>
                  </div>

                  {/* Flow Rate Comparison */}
                  <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                    <div className="text-xs text-slate-400 font-medium">Flow Rate (vph)</div>
                    <div className="text-xl font-bold font-mono text-white mt-1">
                      {historicalComp.flow_rate_comparison.current_value}
                    </div>
                    <div className="flex items-center gap-1 text-xs mt-1 font-mono">
                      <span className="text-cyan-400">
                        {typeof historicalComp.flow_rate_comparison.percentage_change === 'number'
                          ? `${historicalComp.flow_rate_comparison.percentage_change > 0 ? '+' : ''}${
                              historicalComp.flow_rate_comparison.percentage_change
                            }%`
                          : 'N/A'}
                      </span>
                      <span className="text-slate-500 text-[10px]">vs prev</span>
                    </div>
                  </div>

                  {/* Anomaly Comparison */}
                  <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                    <div className="text-xs text-slate-400 font-medium">Incidents / Anomalies</div>
                    <div className="text-xl font-bold font-mono text-white mt-1">
                      {historicalComp.anomaly_comparison.current_value}
                    </div>
                    <div className="flex items-center gap-1 text-xs mt-1 font-mono">
                      <span
                        className={
                          historicalComp.anomaly_comparison.current_value >
                          historicalComp.anomaly_comparison.previous_value
                            ? 'text-rose-400'
                            : 'text-emerald-400'
                        }
                      >
                        {typeof historicalComp.anomaly_comparison.percentage_change === 'number'
                          ? `${historicalComp.anomaly_comparison.percentage_change > 0 ? '+' : ''}${
                              historicalComp.anomaly_comparison.percentage_change
                            }%`
                          : 'Stable'}
                      </span>
                    </div>
                  </div>

                  {/* Observation Hours */}
                  <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                    <div className="text-xs text-slate-400 font-medium">Observation Time</div>
                    <div className="text-xl font-bold font-mono text-white mt-1">
                      {Math.round(historicalComp.duration_comparison.current_value / 3600)} hrs
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1 font-mono">
                      Prev: {Math.round(historicalComp.duration_comparison.previous_value / 3600)} hrs
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 text-xs">
                  Historical comparison data is currently unavailable.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* Provenance & Epistemic Audit Banner */}
      {/* --------------------------------------------------------------------- */}
      {provenance && (
        <Card className="bg-[#0b1329]/90 border-slate-800/80 shadow-sm">
          <CardContent className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-800 text-cyan-400">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="font-semibold text-white flex items-center gap-2">
                  <span>Authoritative Provenance Audit</span>
                  <span
                    className={`inline-flex items-center px-2 py-0.2 rounded-full text-[10px] font-mono font-bold border ${getProvenanceBadgeClass(
                      provenance.provenance_badge_variant
                    )}`}
                  >
                    {provenance.provenance_label}
                  </span>
                </div>
                <p className="text-slate-400 text-[11px] mt-0.5">{provenance.description}</p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-slate-400 font-mono text-[11px]">
              <div>
                Duration: <span className="text-white">{Math.round(provenance.observation_duration_seconds / 3600)}h</span>
              </div>
              <div>
                Sessions: <span className="text-white">{provenance.session_count}</span>
              </div>
              <div>
                Sources: <span className="text-white">{provenance.camera_source_count}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
