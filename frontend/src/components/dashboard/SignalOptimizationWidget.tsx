import React from 'react';
import { SignalOptimizationSection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { TrafficCone, ArrowUpRight, AlertTriangle, Cpu, TrendingDown } from 'lucide-react';
import { Link } from 'react-router-dom';

interface SignalOptimizationWidgetProps {
  data: SignalOptimizationSection;
}

export const SignalOptimizationWidget: React.FC<SignalOptimizationWidgetProps> = ({ data }) => {
  const {
    disclaimer,
    latest_run_id,
    intersection_name,
    algorithm_used,
    baseline_cycle_length,
    optimized_cycle_length,
    delay_reduction_pct,
    queue_reduction_pct,
    throughput_increase_pct,
  } = data;

  const hasRun = !!latest_run_id;

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-950/60 border border-indigo-800/50 text-indigo-400">
            <TrafficCone className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>Signal Optimization Simulation</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              {hasRun
                ? `Latest Run: ${intersection_name} (${algorithm_used})`
                : 'No signal optimization simulations recorded'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge provenance={data.provenance} size="sm" />
          <Link
            to="/signal-optimization"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Open Signal Optimization"
          >
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {/* Simulation Disclaimer Banner */}
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-800/50 text-indigo-300 text-xs">
          <AlertTriangle className="h-4 w-4 text-indigo-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-semibold">Notice: </span>
            <span>{disclaimer}</span>
          </div>
        </div>

        {hasRun ? (
          <div className="space-y-3">
            {/* KPI Performance Metrics */}
            <div className="grid grid-cols-3 gap-2 text-center font-mono">
              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                <div className="text-[10px] text-slate-400 font-sans">Delay Reduction</div>
                <div className="text-base font-bold text-emerald-400 mt-0.5 flex items-center justify-center gap-0.5">
                  <TrendingDown className="h-3.5 w-3.5" />
                  {delay_reduction_pct !== null ? `${delay_reduction_pct.toFixed(1)}%` : '--'}
                </div>
              </div>

              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                <div className="text-[10px] text-slate-400 font-sans">Queue Reduction</div>
                <div className="text-base font-bold text-cyan-400 mt-0.5">
                  {queue_reduction_pct !== null ? `${queue_reduction_pct.toFixed(1)}%` : '--'}
                </div>
              </div>

              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                <div className="text-[10px] text-slate-400 font-sans">Throughput Gain</div>
                <div className="text-base font-bold text-indigo-300 mt-0.5">
                  {throughput_increase_pct !== null ? `+${throughput_increase_pct.toFixed(1)}%` : '--'}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono px-1">
              <span>Baseline Cycle: {baseline_cycle_length?.toFixed(0)}s</span>
              <span className="text-indigo-300">Optimized Cycle: {optimized_cycle_length?.toFixed(0)}s</span>
            </div>
          </div>
        ) : (
          <div className="p-5 text-center text-xs text-slate-400 rounded-xl bg-slate-950/40 border border-slate-800/60 flex flex-col items-center gap-2">
            <Cpu className="h-6 w-6 text-slate-400" />
            <span>Launch a Webster / Green Split simulation on the Signal Optimization page.</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
