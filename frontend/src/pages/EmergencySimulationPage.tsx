import { useState, useEffect, useCallback } from 'react';
import {
  Siren,
  Play,
  Zap,
  Info,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Clock,
  Layers,
  BarChart3,
  History,
  Trash2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  MapPin,
  Flame,
  ShieldAlert,
  Gauge,
  Navigation,
  RefreshCw,
} from 'lucide-react';

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  getEmergencyCorridorPresets,
  runEmergencyCorridorSimulation,
  getEmergencyCorridorRuns,
  getEmergencyCorridorRunDetail,
  deleteEmergencyCorridorRun,
} from '@/api/emergencyCorridor';
import { getAnalysisSessions } from '@/api/analysis';
import {
  CorridorPresetsResponse,
  EmergencyCorridorDetailResponse,
  EmergencyCorridorSummary,
  EmergencyVehicleType,
  PriorityStrategyType,
  RecoveryStrategyType,
} from '@/types/emergencyCorridor';
import { AnalysisSessionSummary } from '@/types/analysis';

export function EmergencySimulationPage() {
  // Presets & Persisted Sessions
  const [presets, setPresets] = useState<CorridorPresetsResponse | null>(null);
  const [persistedSessions, setPersistedSessions] = useState<AnalysisSessionSummary[]>([]);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState<boolean>(true);

  // Configuration State
  const [selectedCorridorId, setSelectedCorridorId] = useState<string>('corridor_3node_medical');
  const [selectedVehiclePresetId, setSelectedVehiclePresetId] = useState<string>('ambulance_code_3');
  const [selectedVehicleType, setSelectedVehicleType] = useState<EmergencyVehicleType>('ambulance');
  const [cruisingSpeedKmh, setCruisingSpeedKmh] = useState<number>(65);
  const [dispatchTimeSec, setDispatchTimeSec] = useState<number>(0);
  const [selectedStrategy, setSelectedStrategy] = useState<PriorityStrategyType>('green_extension_early_green');
  const [selectedRecovery, setSelectedRecovery] = useState<RecoveryStrategyType>('smooth_compensation');
  const [selectedSessionId, setSelectedSessionId] = useState<string>('');
  const [demandSourceType, setDemandSourceType] = useState<'preset' | 'session'>('preset');

  // Execution & Active Result State
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeResult, setActiveResult] = useState<EmergencyCorridorDetailResponse | null>(null);

  // History & Modal State
  const [historyRuns, setHistoryRuns] = useState<EmergencyCorridorSummary[]>([]);
  const [showHistoryModal, setShowHistoryModal] = useState<boolean>(false);
  const [showMathDetails, setShowMathDetails] = useState<boolean>(false);

  // Fetch initial metadata and presets
  const loadInitialData = useCallback(async () => {
    setIsLoadingMetadata(true);
    try {
      const [presetsRes, sessionsRes] = await Promise.all([
        getEmergencyCorridorPresets(),
        getAnalysisSessions(1, 20).catch(() => ({ sessions: [], total: 0 })),
      ]);
      setPresets(presetsRes);
      const sessList = (sessionsRes as any).sessions || (sessionsRes as any).items || [];
      setPersistedSessions(sessList);
      if (sessList.length > 0) {
        setSelectedSessionId(sessList[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load initial corridor simulation metadata:', err);
      setError('Failed to load corridor simulation presets.');
    } finally {
      setIsLoadingMetadata(false);
    }
  }, []);

  // Fetch historical runs
  const fetchHistory = useCallback(async () => {
    try {
      const runsRes = await getEmergencyCorridorRuns(1, 20);
      setHistoryRuns(runsRes.items || []);
    } catch (err: any) {
      console.error('Failed to load corridor history:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadInitialData();
    fetchHistory();
  }, [loadInitialData, fetchHistory]);

  // Handle vehicle preset change
  const handleVehiclePresetChange = (presetId: string) => {
    setSelectedVehiclePresetId(presetId);
    if (!presets) return;
    const vp = presets.vehicles.find((v) => v.preset_id === presetId);
    if (vp) {
      setSelectedVehicleType(vp.vehicle_type);
      setCruisingSpeedKmh(vp.cruising_speed_kmh);
      setDispatchTimeSec(vp.dispatch_time_seconds);
    }
  };

  // Run simulation handler
  const handleExecuteSimulation = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const requestPayload: any = {
        corridor_preset_id: selectedCorridorId,
        strategy_type: selectedStrategy,
        recovery_strategy: selectedRecovery,
        save_to_history: true,
        vehicle: {
          vehicle_type: selectedVehicleType,
          cruising_speed_kmh: cruisingSpeedKmh,
          dispatch_time_seconds: dispatchTimeSec,
          priority_level: selectedVehiclePresetId === 'fire_truck_heavy' ? 'critical' : 'high',
        },
      };

      if (demandSourceType === 'session' && selectedSessionId) {
        requestPayload.session_id = selectedSessionId;
      }

      const response = await runEmergencyCorridorSimulation(requestPayload);
      setActiveResult(response);
      fetchHistory();
    } catch (err: any) {
      console.error('Emergency corridor simulation execution failed:', err);
      setError(err?.message || 'Emergency corridor simulation failed to execute.');
    } finally {
      setIsRunning(false);
    }
  };

  // Run initial simulation once presets load
  useEffect(() => {
    if (presets && !activeResult && !isRunning) {
      handleExecuteSimulation();
    }
  }, [presets]);

  // Load a historical run into the inspector
  const handleInspectRun = async (runId: string) => {
    try {
      const runDetail = await getEmergencyCorridorRunDetail(runId);
      setActiveResult(runDetail);
      setShowHistoryModal(false);
    } catch (err: any) {
      console.error('Failed to load run details:', err);
    }
  };

  // Delete a historical run
  const handleDeleteRun = async (e: React.MouseEvent, runId: string) => {
    e.stopPropagation();
    try {
      await deleteEmergencyCorridorRun(runId);
      fetchHistory();
      if (activeResult?.id === runId) {
        setActiveResult(null);
      }
    } catch (err: any) {
      console.error('Failed to delete run:', err);
    }
  };

  // Vehicle icon helper
  const renderVehicleIcon = (type: string, className = 'h-5 w-5') => {
    switch (type) {
      case 'ambulance':
        return <Siren className={`${className} text-rose-400`} />;
      case 'fire_truck':
        return <Flame className={`${className} text-amber-400`} />;
      case 'police':
        return <ShieldAlert className={`${className} text-cyan-400`} />;
      default:
        return <Navigation className={`${className} text-emerald-400`} />;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* 1. Header & Disclaimers */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
              <Siren className="h-7 w-7 animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Emergency Corridor Simulation
                <Badge variant="outline" className="text-xs bg-rose-950/40 text-rose-400 border-rose-800/60 font-mono">
                  Phase 13 • Decision Support
                </Badge>
              </h1>
              <p className="text-sm text-gray-400 mt-0.5">
                Multi-intersection signal priority, queue pre-clearance, and transit time savings decision support
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowHistoryModal(true)}
            className="flex items-center gap-2 text-gray-300 border-gray-700 hover:bg-gray-800"
          >
            <History className="h-4 w-4" />
            Run History ({historyRuns.length})
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowMathDetails(!showMathDetails)}
            className="flex items-center gap-2 text-gray-300 border-gray-700 hover:bg-gray-800"
          >
            <Info className="h-4 w-4 text-cyan-400" />
            Explainability
            {showMathDetails ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </Button>

          <Button
            onClick={handleExecuteSimulation}
            disabled={isRunning || isLoadingMetadata}
            className="flex items-center gap-2 bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white font-medium shadow-lg shadow-rose-900/20"
          >
            {isRunning ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Simulating...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-white" />
                Simulate Priority
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Safety Boundary Disclaimer Banner */}
      <div className="rounded-lg bg-rose-950/20 border border-rose-800/40 p-3.5 flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
        <div className="text-xs text-rose-200/90 leading-relaxed">
          <strong className="font-semibold text-rose-300">Decision-Support Simulation Scope:</strong> This system models emergency signal priority, queue pre-clearance, and travel-time savings as a decision-support simulation. It explicitly does not control physical traffic lights, municipal infrastructure, or emergency dispatch systems.
        </div>
      </div>

      {/* 2. Simulation Configuration & Parameter Controls */}
      <Card className="bg-gray-900/90 border-gray-800">
        <CardHeader className="pb-3 border-b border-gray-800/60">
          <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
            <Zap className="h-4 w-4 text-rose-400" />
            Corridor & Emergency Scenario Parameters
          </CardTitle>
          <CardDescription className="text-xs text-gray-400">
            Configure multi-intersection arterial routes, emergency vehicle response profiles, and priority timing rules.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Corridor Preset Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-300 flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-cyan-400" />
              Corridor Topology
            </label>
            <select
              value={selectedCorridorId}
              onChange={(e) => setSelectedCorridorId(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-rose-500 transition-colors"
            >
              {presets?.corridors.map((c) => (
                <option key={c.corridor_id} value={c.corridor_id}>
                  {c.name} ({c.node_count} nodes, {c.total_distance_meters}m)
                </option>
              ))}
            </select>
            <p className="text-[11px] text-gray-500">
              {presets?.corridors.find((c) => c.corridor_id === selectedCorridorId)?.description || ''}
            </p>
          </div>

          {/* Vehicle Scenario Preset */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-300 flex items-center gap-1.5">
              <Siren className="h-3.5 w-3.5 text-rose-400" />
              Emergency Vehicle Scenario
            </label>
            <select
              value={selectedVehiclePresetId}
              onChange={(e) => handleVehiclePresetChange(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-rose-500 transition-colors"
            >
              {presets?.vehicles.map((v) => (
                <option key={v.preset_id} value={v.preset_id}>
                  {v.name} ({v.cruising_speed_kmh} km/h)
                </option>
              ))}
            </select>
            <p className="text-[11px] text-gray-500">
              {presets?.vehicles.find((v) => v.preset_id === selectedVehiclePresetId)?.description || ''}
            </p>
          </div>

          {/* Cruising Speed & Dispatch Time */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <label className="font-medium text-gray-300 flex items-center gap-1">
                <Gauge className="h-3.5 w-3.5 text-amber-400" />
                Target Cruise Speed
              </label>
              <span className="text-amber-400 font-mono font-semibold">{cruisingSpeedKmh} km/h</span>
            </div>
            <input
              type="range"
              min={30}
              max={100}
              step={5}
              value={cruisingSpeedKmh}
              onChange={(e) => setCruisingSpeedKmh(Number(e.target.value))}
              className="w-full accent-amber-500 h-1.5 bg-gray-800 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-gray-500 font-mono">
              <span>30 km/h</span>
              <span>65 km/h</span>
              <span>100 km/h</span>
            </div>
          </div>

          {/* Priority & Recovery Strategy */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-300 flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              Priority Strategy
            </label>
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value as PriorityStrategyType)}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-rose-500 transition-colors"
            >
              <option value="green_extension_early_green">Green Extension & Early Green</option>
              <option value="green_wave_progression">Progression Green Wave Window</option>
            </select>
            <div className="flex items-center gap-2 mt-1">
              <select
                value={selectedRecovery}
                onChange={(e) => setSelectedRecovery(e.target.value as RecoveryStrategyType)}
                className="w-full bg-gray-950 border border-gray-800 rounded px-2 py-1 text-[11px] text-gray-300 focus:outline-none"
              >
                <option value="smooth_compensation">Smooth Phase-Safe Recovery</option>
                <option value="immediate_resume">Immediate Baseline Resume</option>
              </select>
            </div>
          </div>

          {/* Traffic Demand Source */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-300 flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-cyan-400" />
              Traffic Demand Source
            </label>
            <select
              value={demandSourceType}
              onChange={(e) => setDemandSourceType(e.target.value as 'preset' | 'session')}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-rose-500 transition-colors"
            >
              <option value="preset">Preset Scenario Volumes</option>
              {persistedSessions.length > 0 && <option value="session">Recorded Analysis Session</option>}
            </select>
            {demandSourceType === 'session' && persistedSessions.length > 0 && (
              <select
                value={selectedSessionId}
                onChange={(e) => setSelectedSessionId(e.target.value)}
                className="w-full bg-gray-950 border border-gray-800 rounded px-2 py-1 text-[11px] text-gray-300 focus:outline-none mt-1"
              >
                {persistedSessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    Session {s.id.slice(0, 8)} ({s.video_filename || 'Video'})
                  </option>
                ))}
              </select>
            )}
          </div>

        </CardContent>
      </Card>

      {/* Explainability / Math Drawer (Expandable) */}
      {showMathDetails && (
        <Card className="bg-gradient-to-br from-gray-900 to-gray-950 border-cyan-900/40 animate-in fade-in-50 duration-200">
          <CardHeader className="pb-2 border-b border-gray-800/80">
            <CardTitle className="text-sm font-semibold text-cyan-300 flex items-center gap-2">
              <Info className="h-4 w-4 text-cyan-400" />
              Signal Priority Mathematical Formulation & Safety Disciplinary Rules
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 text-xs text-gray-300 space-y-3 leading-relaxed">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-3 bg-gray-950/80 rounded-lg border border-gray-800">
                <div className="font-semibold text-cyan-400 mb-1">1. Queue Clearance Lead-Time (t_lead)</div>
                <div className="font-mono text-gray-400 text-[11px] mb-1.5">
                  t_lead = min(25.0, max(3.0, Q_approach × h_d + 2.0s))
                </div>
                <p className="text-[11px] text-gray-400">
                  Activates corridor green before the emergency vehicle arrives to discharge standing vehicle queues (h_d ≈ 2.0 s/veh), guaranteeing a clear approach.
                </p>
              </div>

              <div className="p-3 bg-gray-950/80 rounded-lg border border-gray-800">
                <div className="font-semibold text-emerald-400 mb-1">2. Non-Negotiable Safety Constraints</div>
                <ul className="list-disc list-inside text-[11px] text-gray-400 space-y-0.5">
                  <li>Minimum green (g_min ≥ 10.0s) strictly enforced on all phases.</li>
                  <li>Clearance intervals (yellow 4.0s, all-red 2.0s) never bypassed.</li>
                  <li>Zero simultaneous green on conflicting approaches.</li>
                  <li>Maximum priority green capped at ≤ 80.0s.</li>
                </ul>
              </div>

              <div className="p-3 bg-gray-950/80 rounded-lg border border-gray-800">
                <div className="font-semibold text-amber-400 mb-1">3. Phase-Safe Recovery & Trade-Offs</div>
                <p className="text-[11px] text-gray-400">
                  Compensates starved cross-street phases with additional green (+Δg_comp) in the subsequent cycle. Evaluates exact cross-street delay penalty honestly.
                </p>
              </div>

            </div>
          </CardContent>
        </Card>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-lg bg-red-950/30 border border-red-800/60 p-4 text-red-200 text-sm flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {activeResult && (
        <div className="space-y-6">
          {/* 3. Comparative KPI Cards (Baseline vs Priority) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* KPI 1: Corridor Travel Time */}
            <Card className="bg-gray-900 border-gray-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5">
                  <span className="font-medium flex items-center gap-1.5">
                    <Clock className="h-4 w-4 text-rose-400" />
                    Corridor Travel Time
                  </span>
                  <Badge variant="outline" className="text-[10px] bg-emerald-950/50 text-emerald-400 border-emerald-800">
                    -{activeResult.travel_time_savings_pct.toFixed(1)}% Saved
                  </Badge>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white font-mono">
                    {activeResult.priority_travel_time_seconds.toFixed(1)}s
                  </span>
                  <span className="text-xs text-gray-500 line-through font-mono">
                    {activeResult.baseline_travel_time_seconds.toFixed(1)}s
                  </span>
                </div>
                <p className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
                  <TrendingDown className="h-3 w-3" />
                  Saved {activeResult.travel_time_savings_seconds.toFixed(1)}s transit time
                </p>
              </CardContent>
            </Card>

            {/* KPI 2: Emergency Signal Delay */}
            <Card className="bg-gray-900 border-gray-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5">
                  <span className="font-medium flex items-center gap-1.5">
                    <Zap className="h-4 w-4 text-amber-400" />
                    Emergency Signal Delay
                  </span>
                  <Badge variant="outline" className="text-[10px] bg-emerald-950/50 text-emerald-400 border-emerald-800">
                    -{activeResult.emergency_delay_reduction_pct.toFixed(1)}% Delay
                  </Badge>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white font-mono">
                    {activeResult.priority_emergency_delay_seconds.toFixed(1)}s
                  </span>
                  <span className="text-xs text-gray-500 line-through font-mono">
                    {activeResult.baseline_emergency_delay_seconds.toFixed(1)}s
                  </span>
                </div>
                <p className="text-[11px] text-amber-400/90 mt-1">
                  Clearance across {activeResult.corridor_nodes_count} intersections
                </p>
              </CardContent>
            </Card>

            {/* KPI 3: Progression Speed & LOS */}
            <Card className="bg-gray-900 border-gray-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5">
                  <span className="font-medium flex items-center gap-1.5">
                    <Gauge className="h-4 w-4 text-cyan-400" />
                    Corridor Progression Speed
                  </span>
                  <Badge variant="outline" className="text-[10px] bg-cyan-950/50 text-cyan-400 border-cyan-800 font-mono">
                    LOS {activeResult.metrics_summary?.corridor_los_priority || 'A'}
                  </Badge>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white font-mono">
                    {activeResult.metrics_summary?.average_progression_speed_kmh_priority.toFixed(1)} km/h
                  </span>
                  <span className="text-xs text-gray-500 line-through font-mono">
                    {activeResult.metrics_summary?.average_progression_speed_kmh_baseline.toFixed(1)} km/h
                  </span>
                </div>
                <p className="text-[11px] text-cyan-400/90 mt-1 flex items-center gap-1">
                  <TrendingUp className="h-3 w-3" />
                  Free-flow green wave progression
                </p>
              </CardContent>
            </Card>

            {/* KPI 4: Cross-Street Delay Impact (Honest Trade-off) */}
            <Card className="bg-gray-900 border-gray-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5">
                  <span className="font-medium flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    Cross-Street Delay Impact
                  </span>
                  <Badge variant="outline" className="text-[10px] bg-amber-950/50 text-amber-400 border-amber-800">
                    Trade-Off Impact
                  </Badge>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-amber-300 font-mono">
                    {activeResult.cross_street_delay_impact_pct >= 0 ? '+' : ''}
                    {activeResult.cross_street_delay_impact_pct.toFixed(1)}%
                  </span>
                  <span className="text-xs text-gray-400 font-mono">
                    ({activeResult.baseline_cross_street_delay_avg.toFixed(0)}s → {activeResult.priority_cross_street_delay_avg.toFixed(0)}s)
                  </span>
                </div>
                <p className="text-[11px] text-gray-400 mt-1">
                  Compensated in {activeResult.total_recovery_duration_seconds.toFixed(0)}s recovery phase
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 4. Corridor Topology Visual Map Chain */}
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader className="pb-3 border-b border-gray-800">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
                    <Navigation className="h-4 w-4 text-rose-400" />
                    Corridor Progression & Intersection Topology Chain
                  </CardTitle>
                  <CardDescription className="text-xs text-gray-400">
                    Emergency transit path from origin to destination across {activeResult.corridor_nodes_count} signalized intersections.
                  </CardDescription>
                </div>
                <Badge variant="outline" className="text-xs bg-gray-950 text-gray-300 border-gray-700 font-mono">
                  {activeResult.total_distance_meters.toFixed(0)}m Total Distance
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-5">
              <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 relative">
                {activeResult.node_timelines.map((node, idx) => (
                  <div key={node.node_id} className="flex-1 flex flex-col items-center relative">
                    <div className="w-full bg-gray-950 rounded-xl border border-gray-800 p-4 hover:border-gray-700 transition-colors shadow-md">
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="outline" className="text-[10px] bg-rose-950/40 text-rose-400 border-rose-800">
                          Node {idx + 1}
                        </Badge>
                        <span className="text-[11px] font-mono text-cyan-400 font-semibold">
                          ETA: {node.estimated_arrival_seconds.toFixed(1)}s
                        </span>
                      </div>

                      <div className="text-sm font-bold text-white truncate mb-1">
                        {node.intersection_name}
                      </div>

                      <div className="text-xs text-gray-400 mb-3 flex items-center justify-between font-mono text-[11px]">
                        <span>Dist: {node.distance_from_origin_m.toFixed(0)}m</span>
                        <span className="text-emerald-400">Saved: -{node.delay_savings_seconds.toFixed(1)}s</span>
                      </div>

                      {/* Signal Action Indicator */}
                      <div className="p-2 bg-gray-900 rounded-lg border border-gray-800/80 flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
                          <span className="text-[11px] font-medium text-gray-200 capitalize">
                            {node.priority_window.action_applied.replace('_', ' ')}
                          </span>
                        </div>
                        <span className="text-[10px] text-gray-400 font-mono">
                          Lead: {node.priority_window.queue_clearance_lead_time_seconds.toFixed(1)}s
                        </span>
                      </div>
                    </div>

                    {/* Arrow to next node */}
                    {idx < activeResult.node_timelines.length - 1 && (
                      <div className="hidden lg:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10 p-1 rounded-full bg-gray-800 text-gray-400">
                        <ArrowRight className="h-3 w-3" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 5. Interactive Progression Gantt / Signal Cycle Timeline */}
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader className="pb-3 border-b border-gray-800">
              <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-cyan-400" />
                Intersection Priority Window & Signal Timing Comparison (Gantt)
              </CardTitle>
              <CardDescription className="text-xs text-gray-400">
                Visualizing baseline signal cycles vs priority window activation [T_start, T_end], green extension, and recovery transitions.
              </CardDescription>

            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              {activeResult.node_timelines.map((node) => {
                const cycle = node.baseline_plan.cycle_length_seconds;
                const baseGreen = node.baseline_plan.phase_timings[0]?.green_seconds || 30;
                const baseGreenPct = (baseGreen / cycle) * 100;


                return (
                  <div key={node.node_id} className="p-3.5 bg-gray-950 rounded-xl border border-gray-800/80 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <div className="font-semibold text-white flex items-center gap-2">
                        <span>{node.intersection_name}</span>
                        <Badge variant="outline" className="text-[10px] bg-gray-900 text-gray-400 border-gray-700">
                          Cycle: {cycle.toFixed(0)}s
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] font-mono">
                        <span className="text-gray-400">Arrival: {node.estimated_arrival_seconds.toFixed(1)}s</span>
                        <span className="text-emerald-400 font-semibold">Priority Delay: {node.priority_delay_seconds.toFixed(1)}s</span>
                      </div>
                    </div>

                    {/* Visual Comparison Bars */}
                    <div className="space-y-1.5 pt-1">
                      {/* Baseline Signal Cycle */}
                      <div className="flex items-center gap-2 text-[10px] font-mono text-gray-400">
                        <span className="w-14 shrink-0 text-right">Baseline:</span>
                        <div className="flex-1 h-4 bg-gray-800 rounded overflow-hidden flex relative">
                          <div
                            style={{ width: `${baseGreenPct}%` }}
                            className="h-full bg-emerald-600/70 flex items-center justify-center text-[9px] text-white"
                          >
                            Green ({baseGreen.toFixed(0)}s)
                          </div>
                          <div
                            style={{ width: `${100 - baseGreenPct}%` }}
                            className="h-full bg-rose-900/60 flex items-center justify-center text-[9px] text-rose-200"
                          >
                            Red / Yellow
                          </div>
                          {/* Arrival marker */}
                          <div
                            style={{ left: `${(node.estimated_arrival_seconds % cycle / cycle) * 100}%` }}
                            className="absolute top-0 bottom-0 w-0.5 bg-yellow-400 z-10 shadow"
                            title={`Arrival at ${node.estimated_arrival_seconds.toFixed(1)}s`}
                          />
                        </div>
                      </div>

                      {/* Priority Signal Cycle */}
                      <div className="flex items-center gap-2 text-[10px] font-mono text-gray-400">
                        <span className="w-14 shrink-0 text-right text-cyan-400">Priority:</span>
                        <div className="flex-1 h-4 bg-gray-800 rounded overflow-hidden flex relative">
                          <div
                            style={{ width: `${Math.min(100, baseGreenPct + 20)}%` }}
                            className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 flex items-center justify-center text-[9px] text-white font-bold"
                          >
                            Priority Green Wave ({node.priority_window.action_applied})
                          </div>
                          <div
                            style={{ width: `${Math.max(0, 100 - (baseGreenPct + 20))}%` }}
                            className="h-full bg-amber-900/40 flex items-center justify-center text-[9px] text-amber-300"
                          >
                            Recovery
                          </div>
                          {/* Arrival marker */}
                          <div
                            style={{ left: `${(node.estimated_arrival_seconds % cycle / cycle) * 100}%` }}
                            className="absolute top-0 bottom-0 w-0.5 bg-yellow-400 z-10 shadow"
                            title={`Arrival at ${node.estimated_arrival_seconds.toFixed(1)}s`}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* 6. Granular Intersection Breakdown Table */}
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader className="pb-3 border-b border-gray-800">
              <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
                <Layers className="h-4 w-4 text-cyan-400" />
                Intersection-by-Intersection Priority Metrics
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] text-gray-400 uppercase bg-gray-950/60 border-b border-gray-800">
                  <tr>
                    <th className="px-4 py-3">Intersection</th>
                    <th className="px-3 py-3">Distance</th>
                    <th className="px-3 py-3">ETA</th>
                    <th className="px-3 py-3">Base State</th>
                    <th className="px-3 py-3">Priority Action</th>
                    <th className="px-3 py-3">Queue Cleared</th>
                    <th className="px-3 py-3">Time Saved</th>
                    <th className="px-3 py-3">Cross Delay Impact</th>
                    <th className="px-4 py-3">Recovery Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 font-mono text-[11px]">
                  {activeResult.node_timelines.map((node) => (
                    <tr key={node.node_id} className="hover:bg-gray-800/40">
                      <td className="px-4 py-3 font-sans font-medium text-white">
                        {node.intersection_name}
                      </td>
                      <td className="px-3 py-3 text-gray-300">
                        {node.distance_from_origin_m.toFixed(0)}m
                      </td>
                      <td className="px-3 py-3 text-cyan-400 font-semibold">
                        {node.estimated_arrival_seconds.toFixed(1)}s
                      </td>
                      <td className="px-3 py-3">
                        <Badge
                          variant="outline"
                          className={`text-[10px] uppercase ${
                            node.baseline_signal_state_at_arrival === 'green'
                              ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800'
                              : 'bg-rose-950/40 text-rose-400 border-rose-800'
                          }`}
                        >
                          {node.baseline_signal_state_at_arrival}
                        </Badge>
                      </td>
                      <td className="px-3 py-3">
                        <Badge variant="outline" className="text-[10px] bg-cyan-950/40 text-cyan-300 border-cyan-800">
                          {node.priority_window.action_applied.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td className="px-3 py-3 text-gray-300">
                        {node.queue_cleared_vehicles.toFixed(1)} veh
                      </td>
                      <td className="px-3 py-3 text-emerald-400 font-semibold">
                        -{node.delay_savings_seconds.toFixed(1)}s
                      </td>
                      <td className="px-3 py-3 text-amber-400">
                        {node.cross_street_delay_delta >= 0 ? '+' : ''}
                        {node.cross_street_delay_delta.toFixed(1)}s
                      </td>
                      <td className="px-4 py-3 text-gray-400">
                        {node.priority_window.recovery_duration_seconds.toFixed(0)}s
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* 7. Explainability Notes */}
          {activeResult.simulation_notes && activeResult.simulation_notes.length > 0 && (
            <Card className="bg-gray-900/60 border-gray-800">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-gray-300 flex items-center gap-2">
                  <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                  Simulation Summary & Explainability Logs
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-2">
                <ul className="space-y-1 text-xs text-gray-400">
                  {activeResult.simulation_notes.map((note, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-cyan-500 font-mono">•</span>
                      <span>{note}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* 8. History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in-50">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-2xl w-full max-h-[80vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <History className="h-4 w-4 text-rose-400" />
                Emergency Corridor Simulation History
              </h2>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="text-gray-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-2.5 flex-1">
              {historyRuns.length === 0 ? (
                <div className="text-center py-8 text-sm text-gray-500">
                  No historical simulation runs found.
                </div>
              ) : (
                historyRuns.map((run) => (
                  <div
                    key={run.id}
                    onClick={() => handleInspectRun(run.id)}
                    className="p-3 bg-gray-950 rounded-xl border border-gray-800 hover:border-gray-700 cursor-pointer flex items-center justify-between transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-gray-900 border border-gray-800">
                        {renderVehicleIcon(run.vehicle_type)}
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-white">{run.corridor_name}</div>
                        <div className="text-xs text-gray-400 flex items-center gap-2 mt-0.5">
                          <span className="capitalize">{run.vehicle_type}</span>
                          <span>•</span>
                          <span>{run.corridor_nodes_count} intersections</span>
                          <span>•</span>
                          <span className="text-emerald-400 font-mono">
                            -{run.travel_time_savings_pct.toFixed(1)}% time
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => handleDeleteRun(e, run.id)}
                        className="p-1.5 text-gray-500 hover:text-red-400 rounded-lg hover:bg-gray-900 transition-colors"
                        title="Delete run"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
