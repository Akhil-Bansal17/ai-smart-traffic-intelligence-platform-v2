import React from 'react';
import { TrafficInsight } from '@/types/insight';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  X,
  Lightbulb,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  Layers,
  Activity,
  ShieldAlert,
  Cpu,
  HelpCircle,
} from 'lucide-react';

interface InsightDetailModalProps {
  insight: TrafficInsight | null;
  onClose: () => void;
  onUpdateStatus?: (insightId: string, status: string) => Promise<void>;
}

export const InsightDetailModal: React.FC<InsightDetailModalProps> = ({
  insight,
  onClose,
  onUpdateStatus,
}) => {
  if (!insight) return null;

  const getSeverityBadgeVariant = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return 'danger';
      case 'HIGH':
        return 'warning';
      case 'MEDIUM':
        return 'info';
      case 'LOW':
        return 'default';
      default:
        return 'default';
    }
  };

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'CONGESTION':
        return 'text-rose-400 bg-rose-950/40 border-rose-800/60';
      case 'FLOW_DEGRADATION':
        return 'text-amber-400 bg-amber-950/40 border-amber-800/60';
      case 'LANE_IMBALANCE':
        return 'text-cyan-400 bg-cyan-950/40 border-cyan-800/60';
      case 'DENSITY_SPIKE':
        return 'text-purple-400 bg-purple-950/40 border-purple-800/60';
      case 'TRAFFIC_SURGE':
        return 'text-emerald-400 bg-emerald-950/40 border-emerald-800/60';
      case 'UNDERUTILIZED_LANE':
        return 'text-blue-400 bg-blue-950/40 border-blue-800/60';
      case 'OPERATIONAL_RECOMMENDATION':
        return 'text-indigo-400 bg-indigo-950/40 border-indigo-800/60';
      default:
        return 'text-slate-400 bg-slate-800/50 border-slate-700';
    }
  };

  const renderProvenanceTag = (cat: string) => {
    if (cat === 'real_database_metrics' || cat === 'real_world') {
      return (
        <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 font-mono flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          REAL DATA
        </span>
      );
    }
    return (
      <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-950/60 border border-amber-800/60 text-amber-300 font-mono flex items-center gap-1">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
        {cat.toUpperCase()}
      </span>
    );
  };

  const ep = insight.evidence_package;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-slate-800 bg-slate-950/60">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={getSeverityBadgeVariant(insight.severity)}>
                {insight.severity}
              </Badge>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-mono border font-medium ${getCategoryColor(
                  insight.category
                )}`}
              >
                {insight.category}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                {insight.status}
              </span>
              {renderProvenanceTag(insight.provenance_category)}
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              {insight.title}
            </h2>
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5 text-cyan-400" />
                Window: {insight.start_timestamp_seconds.toFixed(1)}s –{' '}
                {insight.end_timestamp_seconds?.toFixed(1) || insight.duration_seconds.toFixed(1)}s (
                {insight.duration_seconds.toFixed(1)}s)
              </span>
              {insight.affected_lane_name && (
                <span className="flex items-center gap-1">
                  <Layers className="h-3.5 w-3.5 text-indigo-400" />
                  Lane: {insight.affected_lane_name}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1 text-sm text-slate-300">
          {/* Section: Executive Summary */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-cyan-400" />
              <span>What Happened (Summary)</span>
            </h3>
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 leading-relaxed text-slate-200">
              {insight.summary}
            </div>
          </div>

          {/* Section: Root Cause Reasoning (Strict Observed vs Inferred) */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
              <span>Why the System Believes This (Root-Cause Reasoning)</span>
            </h3>

            {/* Observed Facts */}
            {insight.root_cause_observed && insight.root_cause_observed.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-medium text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Empirical Measurements (Observed)</span>
                </div>
                <div className="space-y-1.5">
                  {insight.root_cause_observed.map((obs, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-900/40 text-xs text-emerald-200 flex items-start gap-2"
                    >
                      <span className="px-1.5 py-0.5 rounded bg-emerald-900/60 text-[10px] font-bold tracking-wide uppercase text-emerald-300 font-mono">
                        Observed
                      </span>
                      <span className="flex-1 leading-relaxed">{obs.statement}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Inferred Deductions */}
            {insight.root_cause_inferred && insight.root_cause_inferred.length > 0 && (
              <div className="space-y-2 pt-1">
                <div className="text-xs font-medium text-amber-400 flex items-center gap-1">
                  <HelpCircle className="h-3.5 w-3.5" />
                  <span>Deductive Inferences (Inferred)</span>
                </div>
                <div className="space-y-1.5">
                  {insight.root_cause_inferred.map((inf, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-lg bg-amber-950/20 border border-amber-900/40 text-xs text-amber-200 flex items-start gap-2"
                    >
                      <span className="px-1.5 py-0.5 rounded bg-amber-900/60 text-[10px] font-bold tracking-wide uppercase text-amber-300 font-mono">
                        Inferred
                      </span>
                      <div className="flex-1 space-y-1">
                        <div className="leading-relaxed font-medium">{inf.statement}</div>
                        {inf.rationale && (
                          <div className="text-[11px] text-amber-300/80 italic">
                            Rationale: {inf.rationale}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Section: Advisory Recommendation */}
          {insight.recommendation && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Lightbulb className="h-3.5 w-3.5 text-cyan-400" />
                <span>Recommended Operational Action (Advisory Only)</span>
              </h3>
              <div className="p-4 rounded-xl bg-gradient-to-br from-cyan-950/30 via-slate-900 to-indigo-950/30 border border-cyan-800/40 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                    Action Type: {insight.recommendation_type || 'advisory'}
                  </span>
                  <span className="text-[11px] text-slate-400 font-mono">
                    Physical signal control: Disabled / Not Connected
                  </span>
                </div>
                <p className="text-sm font-medium text-white leading-relaxed">
                  {insight.recommendation}
                </p>
                {insight.recommendation_rationale && (
                  <p className="text-xs text-slate-300/90 leading-relaxed border-t border-slate-800/80 pt-2 mt-2">
                    <span className="font-semibold text-slate-200">Operational Rationale:</span>{' '}
                    {insight.recommendation_rationale}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Section: Structured Evidence Package */}
          {ep && (
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5 text-indigo-400" />
                <span>Supporting Evidence Package</span>
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {/* Metrics Summary Snapshot */}
                {ep.metrics_summary && (
                  <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
                    <div className="font-semibold text-slate-200 border-b border-slate-800 pb-1">
                      Session Traffic Metrics Snapshot
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>Total Volume:</span>
                      <span className="font-mono text-white">{ep.metrics_summary.total_volume} veh</span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>Flow Rate (min):</span>
                      <span className="font-mono text-cyan-400">
                        {ep.metrics_summary.flow_rate_per_minute} veh/min
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>Flow Rate (hr):</span>
                      <span className="font-mono text-slate-400">
                        {ep.metrics_summary.flow_rate_per_hour} veh/h{' '}
                        {ep.metrics_summary.is_extrapolated && '(extrapolated)'}
                      </span>
                    </div>
                  </div>
                )}

                {/* Prediction Evidence Status (Honest Boundary) */}
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
                  <div className="font-semibold text-slate-200 border-b border-slate-800 pb-1 flex items-center justify-between">
                    <span>ML Forecast Evidence</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-amber-400 font-mono">
                      Unavailable
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    {ep.prediction_evidence?.reason ||
                      'Forecast unavailable due to insufficient verified real-world samples (Phase 11 trust boundary).'}
                  </p>
                </div>
              </div>

              {/* Simulation References (if any) */}
              {ep.simulation_references && ep.simulation_references.length > 0 && (
                <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-900/40 space-y-2">
                  <div className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5">
                    <Info className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Correlated Simulation Evidence (Explicitly Labeled Model Projections)</span>
                  </div>
                  {ep.simulation_references.map((sim, idx) => (
                    <div
                      key={idx}
                      className="text-xs text-indigo-200 bg-slate-950/80 p-2.5 rounded border border-indigo-900/50 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-white">
                          {sim.simulation_type === 'signal_optimization'
                            ? `Signal Optimization: ${sim.intersection_name || 'Intersection'}`
                            : `Emergency Corridor: ${sim.corridor_name || 'Corridor'}`}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-900/60 text-indigo-300 font-mono">
                          Simulated
                        </span>
                      </div>
                      <div className="text-[11px] text-indigo-300/90">
                        {sim.simulation_type === 'signal_optimization' ? (
                          <span>
                            Algorithm: {sim.algorithm_used} | Delay Reduction:{' '}
                            <span className="font-bold text-emerald-400">{sim.delay_reduction_pct}%</span> | LOS:{' '}
                            {sim.baseline_los} → {sim.optimized_los}
                          </span>
                        ) : (
                          <span>
                            Vehicle: {sim.vehicle_type} | Time Saved:{' '}
                            <span className="font-bold text-emerald-400">{sim.time_saved_seconds}s</span> (
                            {sim.travel_time_reduction_pct}%)
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-500 italic">
                        {sim.disclaimer}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Section: Technical Limitations & Caveats */}
          {insight.limitations && insight.limitations.length > 0 && (
            <div className="space-y-1.5 p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
              <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3 text-amber-400" />
                <span>Technical Limitations & Anti-Fabrication Declarations</span>
              </h4>
              <ul className="list-disc list-inside text-xs text-slate-400 space-y-1">
                {insight.limitations.map((lim, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {lim}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between p-4 border-t border-slate-800 bg-slate-950/80">
          <div className="text-xs text-slate-500 font-mono">
            ID: {insight.id.slice(0, 8)}... | Dedup: {insight.dedup_signature.slice(0, 8)}
          </div>
          <div className="flex items-center gap-2">
            {onUpdateStatus && insight.status === 'ACTIVE' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onUpdateStatus(insight.id, 'DISMISSED')}
                className="text-xs bg-slate-900 border-slate-700 hover:bg-slate-800 text-slate-300"
              >
                Dismiss Insight
              </Button>
            )}
            <Button variant="primary" size="sm" onClick={onClose} className="text-xs">
              Close Detail
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
