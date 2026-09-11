import React from 'react';
import { EmergencyCorridorSection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { ShieldAlert, ArrowUpRight, AlertTriangle, Zap, Route } from 'lucide-react';
import { Link } from 'react-router-dom';

interface EmergencyCorridorWidgetProps {
  data: EmergencyCorridorSection;
}

export const EmergencyCorridorWidget: React.FC<EmergencyCorridorWidgetProps> = ({ data }) => {
  const {
    disclaimer,
    latest_run_id,
    corridor_name,
    corridor_nodes_count,
    vehicle_type,
    priority_strategy,
    baseline_travel_time_seconds,
    priority_travel_time_seconds,
    travel_time_savings_seconds,
    travel_time_savings_pct,
    emergency_delay_reduction_pct,
    cross_street_delay_impact_pct,
  } = data;

  const hasRun = !!latest_run_id;

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-rose-950/60 border border-rose-800/50 text-rose-400">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>Emergency Corridor Simulation</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              {hasRun
                ? `Latest Run: ${corridor_name} (${vehicle_type}, ${corridor_nodes_count} intersections, ${priority_strategy?.replace(/_/g, ' ')})`
                : 'No emergency corridor simulations recorded'}
            </p>

          </div>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge provenance={data.provenance} size="sm" />
          <Link
            to="/emergency-simulation"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Open Emergency Corridor Simulation"
          >
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {/* Simulation Disclaimer Banner */}
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-rose-950/30 border border-rose-800/50 text-rose-300 text-xs">
          <AlertTriangle className="h-4 w-4 text-rose-400 mt-0.5 flex-shrink-0" />
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
                <div className="text-[10px] text-slate-400 font-sans">Time Savings</div>
                <div className="text-base font-bold text-emerald-400 mt-0.5 flex items-center justify-center gap-0.5">
                  <Zap className="h-3.5 w-3.5" />
                  {travel_time_savings_pct !== null ? `${travel_time_savings_pct.toFixed(1)}%` : '--'}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  -{travel_time_savings_seconds?.toFixed(0)}s transit
                </div>
              </div>

              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                <div className="text-[10px] text-slate-400 font-sans">Delay Reduction</div>
                <div className="text-base font-bold text-cyan-400 mt-0.5">
                  {emergency_delay_reduction_pct !== null
                    ? `${emergency_delay_reduction_pct.toFixed(1)}%`
                    : '--'}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">at intersections</div>
              </div>

              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
                <div className="text-[10px] text-slate-400 font-sans">Cross-Street Delay</div>
                <div className="text-base font-bold text-amber-400 mt-0.5">
                  {cross_street_delay_impact_pct !== null
                    ? `${cross_street_delay_impact_pct.toFixed(1)}s`
                    : '--'}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">avg side delay</div>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono px-1">
              <span>Baseline: {baseline_travel_time_seconds?.toFixed(1)}s</span>
              <span className="text-emerald-400 font-bold">
                Priority Corridor: {priority_travel_time_seconds?.toFixed(1)}s
              </span>
            </div>
          </div>
        ) : (
          <div className="p-5 text-center text-xs text-slate-400 rounded-xl bg-slate-950/40 border border-slate-800/60 flex flex-col items-center gap-2">
            <Route className="h-6 w-6 text-slate-400" />
            <span>Simulate multi-intersection emergency priority paths on the Emergency Simulation page.</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
