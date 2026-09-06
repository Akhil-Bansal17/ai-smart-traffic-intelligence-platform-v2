import { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp,
  BrainCircuit,
  Cpu,
  RefreshCw,
  Play,
  Database,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  BarChart3,
  ShieldCheck,
  Zap,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  getPredictionInfo,
  getDatasetReadiness,
  trainAndForecast,
  getPredictionRuns,
  getPredictionRunDetail,
  generateSyntheticFixtures,
} from '@/api/predictions';
import {
  PredictionInfoResponse,
  DatasetReadinessResponse,
  PredictionRunDetailResponse,
  PredictionRunSummary,
  ModelType,
} from '@/types/prediction';

export function PredictionsPage() {
  // State: Pipeline Info & Readiness
  const [pipelineInfo, setPipelineInfo] = useState<PredictionInfoResponse | null>(null);
  const [readiness, setReadiness] = useState<DatasetReadinessResponse | null>(null);
  const [isLoadingReadiness, setIsLoadingReadiness] = useState<boolean>(true);

  // State: Training Controls
  const [selectedModel, setSelectedModel] = useState<ModelType>('random_forest');
  const [selectedHorizon, setSelectedHorizon] = useState<number>(3);
  const [useSyntheticFallback, setUseSyntheticFallback] = useState<boolean>(true);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [trainError, setTrainError] = useState<string | null>(null);

  // State: Active/Latest Prediction Result
  const [activeRun, setActiveRun] = useState<PredictionRunDetailResponse | null>(null);

  // State: Historical Runs
  const [runs, setRuns] = useState<PredictionRunSummary[]>([]);
  const [isLoadingRuns, setIsLoadingRuns] = useState<boolean>(false);

  // State: Synthetic Fixture Generator
  const [isGeneratingFixtures, setIsGeneratingFixtures] = useState<boolean>(false);
  const [fixturePattern, setFixturePattern] = useState<'rush_hour_surge' | 'sine_wave_normal' | 'weekend_calm'>('rush_hour_surge');
  const [fixtureMessage, setFixtureMessage] = useState<string | null>(null);

  // Fetch initial metadata and readiness
  const refreshReadinessAndInfo = useCallback(async () => {
    setIsLoadingReadiness(true);
    try {
      const [infoRes, readyRes] = await Promise.all([
        getPredictionInfo(),
        getDatasetReadiness(),
      ]);
      setPipelineInfo(infoRes);
      setReadiness(readyRes);
    } catch (err: any) {
      console.error('Failed to fetch prediction metadata:', err);
    } finally {
      setIsLoadingReadiness(false);
    }
  }, []);

  // Fetch runs history
  const fetchRuns = useCallback(async () => {
    setIsLoadingRuns(true);
    try {
      const runsRes = await getPredictionRuns(1, 20);
      setRuns(runsRes.items || []);
      // If no active run selected yet and runs exist, load latest run detail
      if (!activeRun && runsRes.items && runsRes.items.length > 0) {
        const latestDetail = await getPredictionRunDetail(runsRes.items[0].id);
        setActiveRun(latestDetail);
      }
    } catch (err: any) {
      console.error('Failed to fetch prediction runs:', err);
    } finally {
      setIsLoadingRuns(false);
    }
  }, [activeRun]);

  useEffect(() => {
    refreshReadinessAndInfo();
    fetchRuns();
  }, [refreshReadinessAndInfo, fetchRuns]);

  // Handle Train and Forecast trigger
  const handleTrainAndForecast = async () => {
    setIsTraining(true);
    setTrainError(null);
    try {
      const result = await trainAndForecast({
        model_type: selectedModel,
        horizon_steps: selectedHorizon,
        time_step_seconds: 300,
        use_synthetic_if_empty: useSyntheticFallback,
      });
      setActiveRun(result);
      // Refresh readiness and runs table
      await Promise.all([refreshReadinessAndInfo(), fetchRuns()]);
    } catch (err: any) {
      console.error('Training failed:', err);
      setTrainError(err?.message || 'Model training failed.');
    } finally {
      setIsTraining(false);
    }
  };

  // Handle Generate Synthetic Fixtures
  const handleGenerateFixtures = async () => {
    setIsGeneratingFixtures(true);
    setFixtureMessage(null);
    try {
      const res = await generateSyntheticFixtures({
        sample_count: 50,
        pattern: fixturePattern,
        noise_level: 0.15,
      });
      setFixtureMessage(res.message);
      await refreshReadinessAndInfo();
    } catch (err: any) {
      console.error('Fixture generation failed:', err);
      setFixtureMessage(err?.message || 'Failed to generate fixtures.');
    } finally {
      setIsGeneratingFixtures(false);
    }
  };

  // Handle selecting a run from history table
  const handleSelectRun = async (runId: string) => {
    try {
      const detail = await getPredictionRunDetail(runId);
      setActiveRun(detail);
      window.scrollTo({ top: 400, behavior: 'smooth' });
    } catch (err: any) {
      console.error('Failed to load run detail:', err);
    }
  };

  const getDensityBadgeVariant = (state: string): 'success' | 'info' | 'warning' | 'danger' => {
    switch (state.toLowerCase()) {
      case 'low':
        return 'success';
      case 'medium':
        return 'info';
      case 'high':
        return 'warning';
      case 'severe':
        return 'danger';
      default:
        return 'info';
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-[#0c1322] to-cyan-950/25 shadow-xl shadow-black/40">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
              <BrainCircuit className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                  Traffic Prediction & Forecasting Engine
                </h1>
                <Badge variant="info" size="sm">Phase 11 Active</Badge>
              </div>
              <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                Scikit-Learn multi-step traffic volume forecasting evaluated on chronologically split empirical data.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              refreshReadinessAndInfo();
              fetchRuns();
            }}
            disabled={isLoadingReadiness}
            className="text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isLoadingReadiness ? 'animate-spin' : ''}`} />
            Refresh State
          </Button>
        </div>
      </div>

      {/* Dataset Reality & Readiness Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card className="lg:col-span-2 border-slate-800 bg-slate-900/60">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-200">
                <Database className="h-4 w-4 text-cyan-400" />
                <span>Dataset Readiness & Reality State</span>
              </CardTitle>
              {readiness?.is_ready ? (
                <Badge variant="success" size="sm">
                  <CheckCircle2 className="h-3 w-3 mr-1" /> Ready for Real Training
                </Badge>
              ) : (
                <Badge variant="warning" size="sm">
                  <AlertTriangle className="h-3 w-3 mr-1" /> Insufficient Real Data (&lt; 20)
                </Badge>
              )}
            </div>
            <CardDescription className="text-xs text-slate-400">
              Per strict data reality policy, ML models require at least 20 real historical observations for non-leaking chronological evaluation.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                <div className="text-[11px] text-slate-500">Real DB Observations</div>
                <div className="text-xl font-bold font-mono text-slate-200 mt-0.5">
                  {readiness?.sample_count ?? 0}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">Min required: 20</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                <div className="text-[11px] text-slate-500">Analysis Sessions</div>
                <div className="text-xl font-bold font-mono text-cyan-400 mt-0.5">
                  {readiness?.session_count ?? 0}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">CV pipelines run</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                <div className="text-[11px] text-slate-500">Min Threshold</div>
                <div className="text-xl font-bold font-mono text-cyan-400 mt-0.5">
                  {readiness?.threshold ?? 20}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">Observations</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
                <div className="text-[11px] text-slate-500">Readiness State</div>
                <div className="text-xs font-bold font-mono text-slate-300 mt-1.5 truncate uppercase">
                  {readiness?.status_code?.replace(/_/g, ' ') || 'CHECKING'}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">
                  {readiness?.data_source === 'real_observations' ? 'Real Observations' : 'Insufficient Real Data'}
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/90 border border-slate-800 text-xs text-slate-300 flex items-start gap-2.5">
              <Info className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">Status Message: </span>
                <span className="text-slate-400">{readiness?.message || 'Checking database...'}</span>
              </div>
            </div>

            {pipelineInfo?.features_used && pipelineInfo.features_used.length > 0 && (
              <div className="pt-2 border-t border-slate-800/80">
                <div className="text-[11px] text-slate-400 mb-1.5 font-medium">Engineered Pipeline Features:</div>
                <div className="flex flex-wrap gap-1.5">
                  {pipelineInfo.features_used.map((f) => (
                    <span
                      key={f}
                      className="px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 text-[10px] font-mono text-cyan-400"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Development Fixture Generator */}
        <Card className="border-slate-800 bg-slate-900/60">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-200">
              <Sparkles className="h-4 w-4 text-amber-400" />
              <span>Development Fixtures</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Generate labeled synthetic traffic data when real CV video recordings are not yet populated.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1.5 font-medium">Traffic Pattern</label>
              <select
                value={fixturePattern}
                onChange={(e) => setFixturePattern(e.target.value as any)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="rush_hour_surge">Rush Hour Surge (Bimodal 8am/5pm)</option>
                <option value="sine_wave_normal">Sine Wave Normal (Smooth flow)</option>
                <option value="weekend_calm">Weekend Calm (Low variance)</option>
              </select>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerateFixtures}
              disabled={isGeneratingFixtures}
              className="w-full text-xs border-amber-800/60 text-amber-300 hover:bg-amber-950/40"
            >
              <Zap className={`h-3.5 w-3.5 mr-1.5 ${isGeneratingFixtures ? 'animate-spin' : ''}`} />
              {isGeneratingFixtures ? 'Generating 50 Samples...' : 'Generate 50 Synthetic Samples'}
            </Button>

            {fixtureMessage && (
              <div className="p-2 rounded-lg bg-amber-950/30 border border-amber-800/40 text-[11px] text-amber-300">
                {fixtureMessage}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Model Training & Forecasting Controls */}
      <Card className="border-slate-800 bg-slate-900/80 shadow-lg">
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-100">
            <Cpu className="h-4 w-4 text-cyan-400" />
            <span>Model Training & Forecast Execution</span>
          </CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Select a regression architecture, target forecasting horizon, and trigger model fitting.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Model Architecture Selection */}
            <div>
              <label className="text-xs text-slate-300 block mb-1.5 font-medium">Model Architecture</label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value as ModelType)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="random_forest">Random Forest (50 Estimators Ensembling)</option>
                <option value="hist_gradient_boosting">Histogram Gradient Boosting (Fast Trees)</option>
                <option value="ridge">Ridge Regression (L2 Regularized Linear)</option>
                <option value="naive_persistence">Naive Persistence Baseline (t = t-1)</option>
              </select>
            </div>

            {/* Forecast Horizon */}
            <div>
              <label className="text-xs text-slate-300 block mb-1.5 font-medium">Forecast Horizon</label>
              <select
                value={selectedHorizon}
                onChange={(e) => setSelectedHorizon(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value={1}>1 Step (5 minutes forward)</option>
                <option value={2}>2 Steps (10 minutes forward)</option>
                <option value={3}>3 Steps (15 minutes forward - Default)</option>
                <option value={6}>6 Steps (30 minutes forward)</option>
              </select>
            </div>

            {/* Fallback Checkbox & Action Button */}
            <div className="flex flex-col justify-end space-y-2">
              <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useSyntheticFallback}
                  onChange={(e) => setUseSyntheticFallback(e.target.checked)}
                  className="rounded border-slate-800 bg-slate-950 text-cyan-500 focus:ring-0"
                />
                <span>Allow synthetic fallback if DB &lt; 20 samples</span>
              </label>

              <Button
                variant="primary"
                onClick={handleTrainAndForecast}
                disabled={isTraining}
                className="w-full text-xs font-semibold py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 shadow-md shadow-cyan-900/30"
              >
                <Play className={`h-4 w-4 mr-2 ${isTraining ? 'animate-spin' : ''}`} />
                {isTraining ? 'Training Model & Forecasting...' : 'Train Model & Generate Forecast'}
              </Button>
            </div>
          </div>

          {trainError && (
            <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/60 text-xs text-red-300 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
              <span>{trainError}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active Run Forecast Inspection */}
      {activeRun && (
        <div className="space-y-6">
          {/* KPI Metrics Summary */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <Card className="border-slate-800 bg-slate-900/70">
              <CardContent className="pt-5 pb-4">
                <div className="text-xs text-slate-400 font-medium">Model Architecture</div>
                <div className="text-base font-bold font-mono text-cyan-400 mt-1 uppercase">
                  {activeRun.model_type.replace(/_/g, ' ')}
                </div>
                <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                  <span>Samples: {activeRun.sample_count}</span>
                  <span>({activeRun.train_samples} tr / {activeRun.test_samples} te)</span>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-900/70">
              <CardContent className="pt-5 pb-4">
                <div className="text-xs text-slate-400 font-medium">Next Horizon (Step 1)</div>
                <div className="text-2xl font-bold font-mono text-white mt-1">
                  {activeRun.predictions[0]?.predicted_volume.toFixed(1) ?? '--'} <span className="text-xs text-slate-400 font-normal">veh/5m</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Interval: [{activeRun.predictions[0]?.lower_bound.toFixed(1)}, {activeRun.predictions[0]?.upper_bound.toFixed(1)}]
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-900/70">
              <CardContent className="pt-5 pb-4">
                <div className="text-xs text-slate-400 font-medium">Evaluation MAE / RMSE</div>
                <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                  {activeRun.mae.toFixed(2)} <span className="text-xs text-slate-400 font-normal">/ {activeRun.rmse.toFixed(2)}</span>
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  R² Score: {activeRun.r2_score.toFixed(3)}
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-900/70">
              <CardContent className="pt-5 pb-4">
                <div className="text-xs text-slate-400 font-medium">Baseline Improvement</div>
                <div className="text-2xl font-bold font-mono text-cyan-300 mt-1">
                  {activeRun.baseline_improvement_pct >= 0 ? `+${activeRun.baseline_improvement_pct.toFixed(1)}%` : `${activeRun.baseline_improvement_pct.toFixed(1)}%`}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  vs Naive MAE ({activeRun.baseline_mae.toFixed(2)})
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-900/70">
              <CardContent className="pt-5 pb-4">
                <div className="text-xs text-slate-400 font-medium">Data Provenance</div>
                <div className="mt-2">
                  {activeRun.data_source === 'real_observations' ? (
                    <Badge variant="success" size="sm">
                      <CheckCircle2 className="h-3 w-3 mr-1" /> Real Observations
                    </Badge>
                  ) : (
                    <Badge variant="warning" size="sm">
                      <Sparkles className="h-3 w-3 mr-1" /> Synthetic Fixture
                    </Badge>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 mt-2 truncate font-mono">
                  ID: {activeRun.id.slice(0, 12)}...
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Multi-step Forecast Timeline */}
          <Card className="border-slate-800 bg-slate-900/80 shadow-lg">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-100">
                  <TrendingUp className="h-4 w-4 text-cyan-400" />
                  <span>Multi-Step Forecast Trajectory & Residual Uncertainty Bands</span>
                </CardTitle>
                <Badge variant="info" size="sm">
                  {activeRun.horizon_steps} Steps ({activeRun.horizon_steps * 5} min horizon)
                </Badge>
              </div>
              <CardDescription className="text-xs text-slate-400">
                Forward predictions with expanding uncertainty bounds derived from empirical test-split residuals.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {activeRun.predictions.map((item) => (
                  <div
                    key={item.id || item.step}
                    className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/90 relative overflow-hidden group hover:border-cyan-800/50 transition-all"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-cyan-400 font-mono">
                        Step {item.step} (+{Math.round(item.forecast_horizon_seconds / 60)} min)
                      </span>
                      <Badge variant={getDensityBadgeVariant(item.predicted_density_state)} size="sm">
                        {item.predicted_density_state.toUpperCase()}
                      </Badge>
                    </div>

                    <div className="my-3">
                      <div className="text-2xl font-bold font-mono text-white">
                        {item.predicted_volume.toFixed(1)} <span className="text-xs text-slate-400 font-normal">veh</span>
                      </div>
                      <div className="text-xs text-slate-400 flex items-center gap-3 mt-1">
                        <span>In: <strong className="text-slate-300 font-mono">{item.predicted_inbound.toFixed(1)}</strong></span>
                        <span>Out: <strong className="text-slate-300 font-mono">{item.predicted_outbound.toFixed(1)}</strong></span>
                      </div>
                    </div>

                    {/* Uncertainty Bar */}
                    <div className="mt-3 pt-3 border-t border-slate-800/80 text-[11px] space-y-1">
                      <div className="flex justify-between text-slate-400">
                        <span>Prediction Interval:</span>
                        <span className="font-mono text-slate-300">[{item.lower_bound.toFixed(1)} – {item.upper_bound.toFixed(1)}]</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
                        <div
                          className="bg-cyan-500/80 h-full rounded-full"
                          style={{
                            width: `${Math.min(100, Math.max(10, (item.predicted_volume / (item.upper_bound || 1)) * 100))}%`,
                          }}
                        />
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono truncate mt-1">
                        Target: {new Date(item.target_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Model Diagnostics: Feature Importance & Residual Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Feature Importance */}
            <Card className="border-slate-800 bg-slate-900/80">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-100">
                  <BarChart3 className="h-4 w-4 text-cyan-400" />
                  <span>Feature Importance Breakdown</span>
                </CardTitle>
                <CardDescription className="text-xs text-slate-400">
                  Relative contribution of lag variables, rolling statistics, and temporal features.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {Object.keys(activeRun.feature_importance).length > 0 ? (
                  Object.entries(activeRun.feature_importance)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 7)
                    .map(([feature, score]) => (
                      <div key={feature} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="font-mono text-slate-300">{feature}</span>
                          <span className="font-mono text-cyan-400">{(score * 100).toFixed(1)}%</span>
                        </div>
                        <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                          <div
                            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full rounded-full transition-all duration-500"
                            style={{ width: `${Math.max(2, score * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))
                ) : (
                  <div className="text-xs text-slate-500 italic p-4 text-center">
                    Feature importances not applicable or available for baseline model.
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Model vs Baseline Honest Comparison */}
            <Card className="border-slate-800 bg-slate-900/80">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-100">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span>Model vs. Naive Baseline Validation</span>
                </CardTitle>
                <CardDescription className="text-xs text-slate-400">
                  Transparent error comparison against zero-assumption persistence baseline (t = t-1).
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
                    <div className="text-xs text-slate-400 font-medium">Trained Model MAE</div>
                    <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                      {activeRun.mae.toFixed(3)}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">Test split held out</div>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
                    <div className="text-xs text-slate-400 font-medium">Baseline MAE</div>
                    <div className="text-xl font-bold font-mono text-slate-400 mt-1">
                      {activeRun.baseline_mae.toFixed(3)}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">Persistence model</div>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800/80 space-y-2 text-xs">
                  <div className="flex justify-between text-slate-300">
                    <span className="text-slate-400">Root Mean Squared Error (RMSE):</span>
                    <span className="font-mono text-cyan-400">{activeRun.rmse.toFixed(3)} (vs Base: {activeRun.baseline_rmse.toFixed(3)})</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span className="text-slate-400">Coefficient of Determination (R²):</span>
                    <span className="font-mono text-cyan-400">{activeRun.r2_score.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span className="text-slate-400">Chronological Split:</span>
                    <span className="font-mono text-slate-400">{activeRun.train_samples} train / {activeRun.test_samples} test (75%/25%)</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Historical Prediction Runs Table */}
      <Card className="border-slate-800 bg-slate-900/80 shadow-lg">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-100">
              <Clock className="h-4 w-4 text-cyan-400" />
              <span>Historical Prediction Runs</span>
            </CardTitle>
            <span className="text-xs text-slate-400">{runs.length} runs recorded</span>
          </div>
          <CardDescription className="text-xs text-slate-400">
            Database history of trained models, validation metrics, and forecasts.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingRuns ? (
            <div className="p-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-cyan-400" />
              <span>Loading prediction runs from database...</span>
            </div>
          ) : runs.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 italic">
              No prediction runs found in database. Click "Train Model & Generate Forecast" above to run your first model.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                    <th className="py-2.5 px-3">Run Time</th>
                    <th className="py-2.5 px-3">Model Type</th>
                    <th className="py-2.5 px-3">Data Source</th>
                    <th className="py-2.5 px-3">Samples</th>
                    <th className="py-2.5 px-3">Horizon</th>
                    <th className="py-2.5 px-3">MAE</th>
                    <th className="py-2.5 px-3">R² Score</th>
                    <th className="py-2.5 px-3">Improvement</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {runs.map((run) => (
                    <tr
                      key={run.id}
                      className={`hover:bg-slate-800/40 transition-colors ${activeRun?.id === run.id ? 'bg-cyan-950/20' : ''}`}
                    >
                      <td className="py-2.5 px-3 text-slate-300">
                        {new Date(run.created_at).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-2.5 px-3 text-cyan-400 font-semibold uppercase">
                        {run.model_type.replace(/_/g, ' ')}
                      </td>
                      <td className="py-2.5 px-3">
                        {run.data_source === 'real_observations' ? (
                          <Badge variant="success" size="sm">Real DB</Badge>
                        ) : (
                          <Badge variant="warning" size="sm">Synthetic</Badge>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {run.sample_count} ({run.train_samples}/{run.test_samples})
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {run.horizon_steps} steps ({run.horizon_steps * 5}m)
                      </td>
                      <td className="py-2.5 px-3 text-emerald-400 font-semibold">
                        {run.mae.toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {run.r2_score.toFixed(3)}
                      </td>
                      <td className="py-2.5 px-3 text-cyan-300">
                        {run.baseline_improvement_pct >= 0 ? `+${run.baseline_improvement_pct.toFixed(1)}%` : `${run.baseline_improvement_pct.toFixed(1)}%`}
                      </td>
                      <td className="py-2.5 px-3 text-right font-sans">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSelectRun(run.id)}
                          className="text-[11px] h-7 px-2.5 text-cyan-400 hover:text-cyan-300 hover:bg-cyan-950/40"
                        >
                          Inspect <ChevronRight className="h-3 w-3 ml-1" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
