import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Sliders,
  Play,
  Zap,
  Info,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Clock,
  Car,
  Layers,
  BarChart3,
  History,
  Trash2,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  getSignalOptimizationPresets,
  runSignalSimulation,
  getSignalSimulationRuns,
  getSignalSimulationRunDetail,
  deleteSignalSimulationRun,
} from '@/api/signalOptimization';
import { getAnalysisSessions } from '@/api/analysis';
import {
  OptimizationAlgorithm,
  SignalSimulationDetailResponse,
  SignalSimulationSummary,
  PresetsResponse,
  LevelOfService,
} from '@/types/signalOptimization';
import { AnalysisSessionSummary } from '@/types/analysis';

export function SignalOptimizationPage() {
  // Presets & Persisted Sessions
  const [presets, setPresets] = useState<PresetsResponse | null>(null);
  const [persistedSessions, setPersistedSessions] = useState<AnalysisSessionSummary[]>([]);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState<boolean>(true);

  // Configuration State
  const [selectedPresetId, setSelectedPresetId] = useState<string>('int_4way_standard');
  const [demandSourceType, setDemandSourceType] = useState<'preset' | 'session' | 'manual'>('preset');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('arterial_rush_ns');
  const [selectedSessionId, setSelectedSessionId] = useState<string>('');
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<OptimizationAlgorithm>('demand_proportional');
  const [targetCycleLength, setTargetCycleLength] = useState<number>(90);
  const [manualDemands, setManualDemands] = useState<Record<string, number>>({
    north: 1150,
    south: 980,
    east: 240,
    west: 210,
  });

  // Execution & Active Result State
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeResult, setActiveResult] = useState<SignalSimulationDetailResponse | null>(null);

  // History State
  const [historyRuns, setHistoryRuns] = useState<SignalSimulationSummary[]>([]);
  const [showHistoryModal, setShowHistoryModal] = useState<boolean>(false);
  const [showMathDetails, setShowMathDetails] = useState<boolean>(false);

  // Fetch initial metadata and presets
  const loadInitialData = useCallback(async () => {
    setIsLoadingMetadata(true);
    try {
      const [presetsRes, sessionsRes] = await Promise.all([
        getSignalOptimizationPresets(),
        getAnalysisSessions(1, 20).catch(() => ({ sessions: [], total: 0 })),
      ]);
      setPresets(presetsRes);
      const sessList = (sessionsRes as any).sessions || (sessionsRes as any).items || [];
      setPersistedSessions(sessList);
      if (sessList.length > 0) {
        setSelectedSessionId(sessList[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load initial simulation metadata:', err);
      setError('Failed to load simulation presets.');
    } finally {
      setIsLoadingMetadata(false);
    }
  }, []);

  // Fetch historical runs
  const fetchHistory = useCallback(async () => {
    try {
      const runsRes = await getSignalSimulationRuns(1, 20);
      setHistoryRuns(runsRes.items || []);
    } catch (err: any) {
      console.error('Failed to load simulation history:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadInitialData();
    fetchHistory();
  }, [loadInitialData, fetchHistory]);

  // Run simulation handler
  const handleExecuteSimulation = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const requestPayload: any = {
        algorithm: selectedAlgorithm,
        target_cycle_length: targetCycleLength,
        save_to_history: true,
      };

      if (demandSourceType === 'preset') {
        requestPayload.intersection_preset_id = selectedPresetId;
        requestPayload.demand_scenario_id = selectedScenarioId;
      } else if (demandSourceType === 'session') {
        requestPayload.intersection_preset_id = selectedPresetId;
        requestPayload.session_id = selectedSessionId;
      } else {
        // Manual custom demands
        requestPayload.intersection_preset_id = selectedPresetId;
        requestPayload.demands = Object.entries(manualDemands).map(([appId, vph]) => ({
          approach_id: appId,
          vehicle_flow_rate_vph: vph,
          data_provenance: 'simulation_configured',
        }));
      }

      const response = await runSignalSimulation(requestPayload);
      setActiveResult(response);
      fetchHistory();
    } catch (err: any) {
      console.error('Simulation execution failed:', err);
      setError(err?.message || 'Signal simulation failed to execute.');
    } finally {
      setIsRunning(false);
    }
  };

  // Run initial default simulation once presets are ready
  useEffect(() => {
    if (presets && !activeResult && !isRunning) {
      handleExecuteSimulation();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presets]);

  // Handle loading a historical run
  const handleLoadHistoryRun = async (runId: string) => {
    try {
      setIsRunning(true);
      const detail = await getSignalSimulationRunDetail(runId);
      setActiveResult(detail);
      setShowHistoryModal(false);
    } catch (err: any) {
      console.error('Failed to load historical run:', err);
    } finally {
      setIsRunning(false);
    }
  };

  // Handle deleting a historical run
  const handleDeleteHistoryRun = async (runId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteSignalSimulationRun(runId);
      setHistoryRuns((prev) => prev.filter((r) => r.id !== runId));
      if (activeResult?.id === runId) {
        setActiveResult(null);
      }
    } catch (err: any) {
      console.error('Failed to delete history run:', err);
    }
  };

  // Chart data preparation
  const chartData = useMemo(() => {
    if (!activeResult) return [];
    const appMap = new Map(activeResult.approach_comparisons.map((ac) => [ac.approach_id, ac]));
    const maxDemand = Math.max(...activeResult.demand_input.map((d) => d.vehicle_flow_rate_vph), 100);
    const maxGreen = Math.max(
      ...activeResult.approach_comparisons.map((ac) => Math.max(ac.baseline_green_seconds, ac.optimized_green_seconds)),
      10
    );

    return activeResult.demand_input.map((d) => {
      const comp = appMap.get(d.approach_id);
      return {
        name: comp?.name || d.approach_id.toUpperCase(),
        demand: d.vehicle_flow_rate_vph,
        demandPct: (d.vehicle_flow_rate_vph / maxDemand) * 100,
        baselineGreen: comp?.baseline_green_seconds || 0,
        baselineGreenPct: ((comp?.baseline_green_seconds || 0) / maxGreen) * 100,
        optimizedGreen: comp?.optimized_green_seconds || 0,
        optimizedGreenPct: ((comp?.optimized_green_seconds || 0) / maxGreen) * 100,
        baselineDelay: comp?.baseline_delay_seconds || 0,
        optimizedDelay: comp?.optimized_delay_seconds || 0,
      };
    });
  }, [activeResult]);

  // LOS Badge Color Helper
  const getLosBadgeColor = (los: LevelOfService) => {
    switch (los) {
      case 'A':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'B':
        return 'bg-teal-500/10 text-teal-400 border-teal-500/30';
      case 'C':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
      case 'D':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'E':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      case 'F':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header & Simulation Disclaimer Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Sliders className="h-6 w-6 text-primary-400" />
              Traffic Signal Optimization Simulation
            </h1>
            <Badge variant="outline" className="bg-primary-500/10 text-primary-400 border-primary-500/30 text-xs">
              Phase 12
            </Badge>
            <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/30 text-xs">
              Decision Support Simulation
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Evaluate and optimize intersection green-time allocations using explainable demand-proportional and Webster models.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowHistoryModal(true)}
            className="flex items-center gap-1.5 border-slate-700 hover:bg-slate-800"
          >
            <History className="h-4 w-4 text-slate-400" />
            Simulation History ({historyRuns.length})
          </Button>
          <Button
            size="sm"
            onClick={handleExecuteSimulation}
            disabled={isRunning || isLoadingMetadata}
            className="flex items-center gap-1.5 bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-500/20"
          >
            <Play className="h-4 w-4" />
            {isRunning ? 'Optimizing...' : 'Run Simulation'}
          </Button>
        </div>
      </div>

      {/* Decision-Support Safety Notice Alert */}
      <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-3 text-sm text-amber-200">
        <ShieldCheck className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-amber-300">Decision-Support Simulation Notice: </span>
          <span>
            This system provides advisory traffic signal timing simulation and comparative delay modeling. It does{' '}
            <strong className="text-white underline">not</strong> directly connect to, actuate, or control physical traffic signal infrastructure.
          </span>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid: Control Panel (Left) & Results (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Interactive Configuration Controls */}
        <div className="lg:col-span-4 space-y-5">
          {/* Card 1: Intersection Topology */}
          <Card className="bg-slate-900/70 border-slate-800 backdrop-blur-md">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                <Layers className="h-4 w-4 text-cyan-400" />
                1. Intersection Topology
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Select intersection geometry and approach layout
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Preset Geometry</label>
                <select
                  value={selectedPresetId}
                  onChange={(e) => setSelectedPresetId(e.target.value)}
                  className="w-full text-xs rounded-md bg-slate-800 border border-slate-700 text-slate-200 px-2.5 py-2 focus:ring-1 focus:ring-primary-500 outline-none"
                >
                  {presets?.intersections.map((int) => (
                    <option key={int.id} value={int.id}>
                      {int.name} ({int.approaches_count} Appro., {int.phases_count} Ph.)
                    </option>
                  ))}
                </select>
              </div>

              {presets?.intersections.find((i) => i.id === selectedPresetId) && (
                <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800 text-xs text-slate-400 space-y-1">
                  <div className="text-slate-300 font-medium">
                    {presets.intersections.find((i) => i.id === selectedPresetId)?.name}
                  </div>
                  <div>{presets.intersections.find((i) => i.id === selectedPresetId)?.description}</div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Card 2: Traffic Demand Input Source */}
          <Card className="bg-slate-900/70 border-slate-800 backdrop-blur-md">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                <Car className="h-4 w-4 text-emerald-400" />
                2. Traffic Demand Input
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Choose live video analytics, benchmark scenario, or manual inputs
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Demand Source Tabs */}
              <div className="grid grid-cols-3 gap-1 p-1 bg-slate-950 rounded-lg border border-slate-800 text-xs">
                <button
                  type="button"
                  onClick={() => setDemandSourceType('preset')}
                  className={`py-1.5 rounded text-center font-medium transition-all ${
                    demandSourceType === 'preset'
                      ? 'bg-primary-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Preset Flow
                </button>
                <button
                  type="button"
                  onClick={() => setDemandSourceType('session')}
                  className={`py-1.5 rounded text-center font-medium transition-all ${
                    demandSourceType === 'session'
                      ? 'bg-primary-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  DB Session
                </button>
                <button
                  type="button"
                  onClick={() => setDemandSourceType('manual')}
                  className={`py-1.5 rounded text-center font-medium transition-all ${
                    demandSourceType === 'manual'
                      ? 'bg-primary-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Custom
                </button>
              </div>

              {demandSourceType === 'preset' && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-300">Flow Scenario</label>
                  <select
                    value={selectedScenarioId}
                    onChange={(e) => setSelectedScenarioId(e.target.value)}
                    className="w-full text-xs rounded-md bg-slate-800 border border-slate-700 text-slate-200 px-2.5 py-2 focus:ring-1 focus:ring-primary-500 outline-none"
                  >
                    {presets?.scenarios.map((sc) => (
                      <option key={sc.id} value={sc.id}>
                        {sc.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {demandSourceType === 'session' && (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-slate-300">Persisted Analysis Session</label>
                  {persistedSessions.length > 0 ? (
                    <select
                      value={selectedSessionId}
                      onChange={(e) => setSelectedSessionId(e.target.value)}
                      className="w-full text-xs rounded-md bg-slate-800 border border-slate-700 text-slate-200 px-2.5 py-2 focus:ring-1 focus:ring-primary-500 outline-none"
                    >
                      {persistedSessions.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.video_filename} ({s.total_vehicles_counted} counted, {new Date(s.started_at).toLocaleDateString()})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="text-xs text-amber-300 p-2 rounded bg-amber-500/10 border border-amber-500/20">
                      No completed video analysis sessions available in DB.
                    </div>
                  )}
                  <p className="text-[11px] text-slate-400 leading-tight">
                    Measured North/South directional counts bridge to the corridor; cross-street approaches are populated with configured background flow.
                  </p>
                </div>
              )}

              {demandSourceType === 'manual' && (
                <div className="space-y-2">
                  {['north', 'south', 'east', 'west'].map((appId) => (
                    <div key={appId} className="flex items-center justify-between gap-3 text-xs">
                      <span className="capitalize text-slate-300 font-medium">{appId} Approach:</span>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min="0"
                          max="4000"
                          step="50"
                          value={manualDemands[appId] || 0}
                          onChange={(e) =>
                            setManualDemands((prev) => ({
                              ...prev,
                              [appId]: Math.max(0, parseInt(e.target.value, 10) || 0),
                            }))
                          }
                          className="w-20 px-2 py-1 rounded bg-slate-800 border border-slate-700 text-right text-white text-xs outline-none"
                        />
                        <span className="text-[11px] text-slate-500">vph</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Card 3: Optimization Algorithm & Constraints */}
          <Card className="bg-slate-900/70 border-slate-800 backdrop-blur-md">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" />
                3. Algorithm & Constraints
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Select optimization strategy and cycle timing parameters
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Optimization Algorithm</label>
                <select
                  value={selectedAlgorithm}
                  onChange={(e) => setSelectedAlgorithm(e.target.value as OptimizationAlgorithm)}
                  className="w-full text-xs rounded-md bg-slate-800 border border-slate-700 text-slate-200 px-2.5 py-2 focus:ring-1 focus:ring-primary-500 outline-none"
                >
                  <option value="demand_proportional">Demand-Proportional Green Split (Equi-Saturation)</option>
                  <option value="webster_optimal">Webster&apos;s Optimal Cycle & Split Model</option>
                  <option value="constrained_delay_minimization">Constrained Delay Minimization (Search)</option>
                </select>
              </div>

              {/* Cycle Length Slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Target Cycle Length</span>
                  <span className="text-primary-400 font-bold">{targetCycleLength}s</span>
                </div>
                <input
                  type="range"
                  min="45"
                  max="130"
                  step="5"
                  value={targetCycleLength}
                  onChange={(e) => setTargetCycleLength(parseInt(e.target.value, 10))}
                  className="w-full accent-primary-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>Min: 45s</span>
                  <span>Standard: 90s</span>
                  <span>Max: 130s</span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800 grid grid-cols-2 gap-2 text-[11px] text-slate-400">
                <div>Min Green: <span className="text-slate-200">10.0s</span></div>
                <div>Max Green: <span className="text-slate-200">65.0s</span></div>
                <div>Yellow Time: <span className="text-slate-200">4.0s</span></div>
                <div>All-Red Time: <span className="text-slate-200">2.0s</span></div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Simulation Dashboard & Comparative Analysis */}
        <div className="lg:col-span-8 space-y-6">
          {activeResult ? (
            <>
              {/* Top Key Performance Indicator Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {/* KPI 1: Delay Reduction */}
                <Card className="bg-slate-900/80 border-slate-800">
                  <CardContent className="p-4 space-y-1">
                    <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                      Avg Vehicle Delay
                    </div>
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-2xl font-bold text-white">
                        {activeResult.optimized_metrics.average_delay_seconds_per_vehicle.toFixed(1)}s
                      </span>
                      <span className="text-xs text-slate-400">
                        (was {activeResult.baseline_metrics.average_delay_seconds_per_vehicle.toFixed(1)}s)
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-xs">
                      {activeResult.delay_reduction_pct >= 0 ? (
                        <span className="text-emerald-400 font-semibold flex items-center">
                          <TrendingDown className="h-3.5 w-3.5 mr-0.5" />
                          -{activeResult.delay_reduction_pct.toFixed(1)}% Delay
                        </span>
                      ) : (
                        <span className="text-amber-400 font-semibold flex items-center">
                          <TrendingUp className="h-3.5 w-3.5 mr-0.5" />
                          +{Math.abs(activeResult.delay_reduction_pct).toFixed(1)}% Delay
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* KPI 2: Queue Length Proxy */}
                <Card className="bg-slate-900/80 border-slate-800">
                  <CardContent className="p-4 space-y-1">
                    <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                      Queue Length Proxy
                    </div>
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-2xl font-bold text-white">
                        {activeResult.optimized_metrics.total_queue_vehicles.toFixed(1)}
                      </span>
                      <span className="text-xs text-slate-400">veh</span>
                    </div>
                    <div className="text-xs text-cyan-400 font-semibold flex items-center">
                      <TrendingDown className="h-3.5 w-3.5 mr-0.5" />
                      -{activeResult.queue_reduction_pct.toFixed(1)}% vs Baseline
                    </div>
                  </CardContent>
                </Card>

                {/* KPI 3: Intersection LOS */}
                <Card className="bg-slate-900/80 border-slate-800">
                  <CardContent className="p-4 space-y-1">
                    <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                      Level of Service
                    </div>
                    <div className="flex items-center gap-2 pt-0.5">
                      <Badge className={getLosBadgeColor(activeResult.optimized_metrics.intersection_los)}>
                        LOS {activeResult.optimized_metrics.intersection_los}
                      </Badge>
                      <span className="text-xs text-slate-400">
                        (was LOS {activeResult.baseline_metrics.intersection_los})
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 pt-0.5">
                      v/c Max: {activeResult.optimized_metrics.critical_v_c_ratio.toFixed(2)}
                    </div>
                  </CardContent>
                </Card>

                {/* KPI 4: Cycle & Runtime */}
                <Card className="bg-slate-900/80 border-slate-800">
                  <CardContent className="p-4 space-y-1">
                    <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                      Cycle & Latency
                    </div>
                    <div className="text-xl font-bold text-white">
                      {activeResult.optimized_plan.cycle_length_seconds.toFixed(0)}s Cycle
                    </div>
                    <div className="text-xs text-slate-400 flex items-center gap-1">
                      <Clock className="h-3 w-3 text-slate-400" />
                      Computed in {activeResult.execution_time_ms.toFixed(2)}ms
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Dual Cycle Allocation Timeline (Baseline vs Optimized) */}
              <Card className="bg-slate-900/80 border-slate-800">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                        <Clock className="h-4 w-4 text-primary-400" />
                        Cycle Timing & Green Split Comparison
                      </CardTitle>
                      <CardDescription className="text-xs text-slate-400">
                        Visualizing available green reallocation across phases (Lost Clearance = {activeResult.baseline_plan.total_lost_seconds}s)
                      </CardDescription>
                    </div>
                    <Badge variant="outline" className="text-xs text-slate-400 border-slate-700">
                      {activeResult.algorithm_used.replace('_', ' ').toUpperCase()}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Baseline Cycle Bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-slate-400">
                      <span className="font-medium text-slate-300">Baseline Plan (Fixed 50/50 Split)</span>
                      <span>Total: {activeResult.baseline_plan.cycle_length_seconds}s</span>
                    </div>
                    <div className="h-8 w-full bg-slate-950 rounded-md overflow-hidden flex border border-slate-800 text-[11px] font-medium text-white select-none">
                      {activeResult.baseline_plan.phase_timings.map((pt, idx) => (
                        <div
                          key={pt.phase_id}
                          style={{ width: `${pt.split_percentage}%` }}
                          className={`h-full flex items-center justify-center px-1.5 transition-all ${
                            idx === 0 ? 'bg-indigo-600/80 border-r border-indigo-400/40' : 'bg-slate-700/80 border-r border-slate-500/40'
                          }`}
                          title={`${pt.name}: ${pt.green_seconds}s green + ${pt.yellow_seconds + pt.all_red_seconds}s clearance`}
                        >
                          <span className="truncate">{pt.name.split(':')[0]}: {pt.green_seconds}s ({pt.split_percentage.toFixed(0)}%)</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Optimized Cycle Bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-slate-400">
                      <span className="font-medium text-emerald-400 flex items-center gap-1">
                        <Sparkles className="h-3.5 w-3.5" />
                        Optimized Plan ({activeResult.algorithm_used.replace('_', ' ')})
                      </span>
                      <span>Total: {activeResult.optimized_plan.cycle_length_seconds}s</span>
                    </div>
                    <div className="h-8 w-full bg-slate-950 rounded-md overflow-hidden flex border border-slate-800 text-[11px] font-medium text-white select-none shadow-inner">
                      {activeResult.optimized_plan.phase_timings.map((pt, idx) => (
                        <div
                          key={pt.phase_id}
                          style={{ width: `${pt.split_percentage}%` }}
                          className={`h-full flex items-center justify-center px-1.5 transition-all ${
                            idx === 0 ? 'bg-emerald-600/90 border-r border-emerald-400/40' : 'bg-cyan-600/90 border-r border-cyan-400/40'
                          }`}
                          title={`${pt.name}: ${pt.green_seconds}s green + ${pt.yellow_seconds + pt.all_red_seconds}s clearance`}
                        >
                          <span className="truncate">{pt.name.split(':')[0]}: {pt.green_seconds}s ({pt.split_percentage.toFixed(0)}%)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Phase-by-Phase Comparison Table */}
              <Card className="bg-slate-900/80 border-slate-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                    <Sliders className="h-4 w-4 text-cyan-400" />
                    Phase-by-Phase Timing Breakdown
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-950/70 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="py-2.5 px-4 font-medium">Phase</th>
                          <th className="py-2.5 px-4 font-medium">Controlled Movements</th>
                          <th className="py-2.5 px-4 font-medium text-right">Baseline Green</th>
                          <th className="py-2.5 px-4 font-medium text-right">Optimized Green</th>
                          <th className="py-2.5 px-4 font-medium text-right">Delta (Δg)</th>
                          <th className="py-2.5 px-4 font-medium text-right">Split %</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-200">
                        {activeResult.phase_comparisons.map((pc) => (
                          <tr key={pc.phase_id} className="hover:bg-slate-800/40">
                            <td className="py-2.5 px-4 font-medium text-white">{pc.name}</td>
                            <td className="py-2.5 px-4 text-slate-400 capitalize">
                              {pc.controlled_approaches.join(', ')}
                            </td>
                            <td className="py-2.5 px-4 text-right font-mono">{pc.baseline_green_seconds.toFixed(1)}s</td>
                            <td className="py-2.5 px-4 text-right font-mono font-bold text-emerald-400">
                              {pc.optimized_green_seconds.toFixed(1)}s
                            </td>
                            <td className="py-2.5 px-4 text-right font-mono font-semibold">
                              <span className={pc.green_delta_seconds >= 0 ? 'text-emerald-400' : 'text-amber-400'}>
                                {pc.green_delta_seconds >= 0 ? `+${pc.green_delta_seconds.toFixed(1)}s` : `${pc.green_delta_seconds.toFixed(1)}s`}
                              </span>
                            </td>
                            <td className="py-2.5 px-4 text-right font-mono text-slate-300">
                              {pc.optimized_split_pct.toFixed(1)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Approach Performance & Level of Service (LOS) Table */}
              <Card className="bg-slate-900/80 border-slate-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-emerald-400" />
                    Approach Performance & Service Level (LOS)
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-950/70 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="py-2.5 px-4 font-medium">Approach</th>
                          <th className="py-2.5 px-4 font-medium text-right">Demand (vph)</th>
                          <th className="py-2.5 px-4 font-medium text-right">Baseline Delay</th>
                          <th className="py-2.5 px-4 font-medium text-right">Optimized Delay</th>
                          <th className="py-2.5 px-4 font-medium text-right">Delay Δ</th>
                          <th className="py-2.5 px-4 font-medium text-right">Queue (veh)</th>
                          <th className="py-2.5 px-4 font-medium text-center">LOS Transition</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-200">
                        {activeResult.approach_comparisons.map((ac) => (
                          <tr key={ac.approach_id} className="hover:bg-slate-800/40">
                            <td className="py-2.5 px-4 font-medium text-white">{ac.name}</td>
                            <td className="py-2.5 px-4 text-right font-mono text-slate-300">
                              {ac.demand_vph.toFixed(0)}
                            </td>
                            <td className="py-2.5 px-4 text-right font-mono text-slate-400">
                              {ac.baseline_delay_seconds.toFixed(1)}s
                            </td>
                            <td className="py-2.5 px-4 text-right font-mono font-bold text-white">
                              {ac.optimized_delay_seconds.toFixed(1)}s
                            </td>
                            <td className="py-2.5 px-4 text-right font-mono">
                              <span className={ac.delay_reduction_pct >= 0 ? 'text-emerald-400' : 'text-amber-400'}>
                                {ac.delay_reduction_pct >= 0 ? `-${ac.delay_reduction_pct.toFixed(1)}%` : `+${Math.abs(ac.delay_reduction_pct).toFixed(1)}%`}
                              </span>
                            </td>
                            <td className="py-2.5 px-4 text-right font-mono text-slate-300">
                              {ac.optimized_queue_vehicles.toFixed(1)}
                            </td>
                            <td className="py-2.5 px-4 text-center">
                              <div className="flex items-center justify-center gap-1.5">
                                <Badge className={`text-[10px] py-0 px-1.5 ${getLosBadgeColor(ac.baseline_los)}`}>
                                  {ac.baseline_los}
                                </Badge>
                                <ArrowRight className="h-3 w-3 text-slate-500" />
                                <Badge className={`text-[10px] py-0 px-1.5 font-bold ${getLosBadgeColor(ac.optimized_los)}`}>
                                  {ac.optimized_los}
                                </Badge>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Graphical Visualizer: Demand vs Green Allocation Bars */}
              <Card className="bg-slate-900/80 border-slate-800">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-primary-400" />
                      Approach Traffic Volume vs Allocated Green Duration
                    </CardTitle>
                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-sm bg-blue-500" />
                        <span>Demand (vph)</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-sm bg-slate-500" />
                        <span>Baseline Green</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />
                        <span>Optimized Green</span>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    {chartData.map((item) => (
                      <div key={item.name} className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1.5">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-medium text-white">{item.name}</span>
                          <div className="flex gap-4 font-mono text-[11px]">
                            <span className="text-blue-400">{item.demand.toFixed(0)} vph</span>
                            <span className="text-slate-400">Base: {item.baselineGreen.toFixed(1)}s</span>
                            <span className="text-emerald-400 font-bold">Opt: {item.optimizedGreen.toFixed(1)}s</span>
                          </div>
                        </div>

                        {/* Stacked Comparative Bars */}
                        <div className="space-y-1 text-[10px]">
                          {/* Demand Bar */}
                          <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                            <div
                              style={{ width: `${Math.min(100, item.demandPct)}%` }}
                              className="h-full bg-blue-500 rounded-full transition-all"
                            />
                          </div>
                          {/* Green Comparison Dual Bar */}
                          <div className="grid grid-cols-2 gap-2 pt-0.5">
                            <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                              <div
                                style={{ width: `${Math.min(100, item.baselineGreenPct)}%` }}
                                className="h-full bg-slate-500 rounded-full transition-all"
                              />
                            </div>
                            <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                              <div
                                style={{ width: `${Math.min(100, item.optimizedGreenPct)}%` }}
                                className="h-full bg-emerald-500 rounded-full transition-all"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Explainability & Mathematical Formulations Accordion */}
              <Card className="bg-slate-900/60 border-slate-800">
                <CardHeader
                  className="cursor-pointer py-3 hover:bg-slate-800/30 transition-all rounded-t-lg select-none"
                  onClick={() => setShowMathDetails(!showMathDetails)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                      <Info className="h-4 w-4 text-cyan-400" />
                      Mathematical Objectives, Constraints & Explainability
                    </div>
                    {showMathDetails ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                  </div>
                </CardHeader>
                {showMathDetails && (
                  <CardContent className="pt-2 text-xs text-slate-400 space-y-3 border-t border-slate-800/60">
                    <div>
                      <strong className="text-slate-200">1. Demand-Proportional Green Allocation:</strong>
                      <p className="mt-0.5">
                        Calculates critical flow ratio <code className="text-cyan-300">y_i = max(q_j / s_j)</code> for each phase. Green is allocated proportional to <code className="text-cyan-300">g_i = (y_i / Y) * G_avail</code>, subject to minimum green (<code className="text-cyan-300">g_min = 10s</code>) and maximum green (<code className="text-cyan-300">g_max = 65s</code>) bounds.
                      </p>
                    </div>
                    <div>
                      <strong className="text-slate-200">2. Webster&apos;s Delay Formulation Proxy:</strong>
                      <p className="mt-0.5">
                        <code className="text-emerald-300">d = [C*(1 - g/C)^2] / [2*(1 - (g/C)*x)] + [x^2] / [2*q*(1 - x)]</code> where <code className="text-slate-300">x = q / c</code> is the volume-to-capacity degree of saturation, transitioning gracefully into Highway Capacity Manual (HCM) incremental queue delay under peak congestion.
                      </p>
                    </div>
                    <div>
                      <strong className="text-slate-200">3. Provenance & Limitations:</strong>
                      <p className="mt-0.5">
                        Outputs represent simulated advisory metrics evaluated against deterministic queue proxies, rather than direct physical controller actuation.
                      </p>
                    </div>
                  </CardContent>
                )}
              </Card>
            </>
          ) : (
            <Card className="bg-slate-900/60 border-slate-800 p-12 text-center text-slate-400">
              <Sliders className="h-10 w-10 text-slate-600 mx-auto mb-3" />
              <div className="text-base font-medium text-slate-300">No Active Simulation Run</div>
              <p className="text-xs text-slate-500 mt-1">
                Configure intersection parameters and click &ldquo;Run Simulation&rdquo; to compute optimized signal timing.
              </p>
            </Card>
          )}
        </div>
      </div>

      {/* Historical Simulation Runs Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-primary-400" />
                <h3 className="text-base font-bold text-white">Historical Simulation Runs</h3>
              </div>
              <Button variant="outline" size="sm" onClick={() => setShowHistoryModal(false)}>
                Close
              </Button>
            </div>

            <div className="overflow-y-auto p-4 space-y-2 flex-1">
              {historyRuns.length > 0 ? (
                historyRuns.map((run) => (
                  <div
                    key={run.id}
                    onClick={() => handleLoadHistoryRun(run.id)}
                    className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 hover:border-primary-500/50 hover:bg-slate-800/40 transition-all cursor-pointer flex items-center justify-between text-xs"
                  >
                    <div className="space-y-1">
                      <div className="font-semibold text-white flex items-center gap-2">
                        {run.intersection_name}
                        <Badge variant="outline" className="text-[10px] py-0 border-slate-700 text-slate-400">
                          {run.algorithm_used.replace('_', ' ')}
                        </Badge>
                      </div>
                      <div className="text-slate-400 flex items-center gap-3">
                        <span>Cycle: {run.optimized_cycle_length.toFixed(0)}s</span>
                        <span>Delay: {run.optimized_delay_proxy.toFixed(1)}s (was {run.baseline_delay_proxy.toFixed(1)}s)</span>
                        <span className="text-emerald-400 font-medium">-{run.delay_reduction_pct.toFixed(1)}%</span>
                        <span>Source: {run.data_source}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-slate-500 text-[11px]">
                        {new Date(run.created_at).toLocaleTimeString()}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => handleDeleteHistoryRun(run.id, e)}
                        className="p-1.5 text-slate-500 hover:text-rose-400 transition-all"
                        title="Delete run"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-slate-500 text-xs">
                  No historical simulation runs found.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
