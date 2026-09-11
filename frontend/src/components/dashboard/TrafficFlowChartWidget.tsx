import React from 'react';
import { TrafficFlowSection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { BarChart3 } from 'lucide-react';

interface TrafficFlowChartWidgetProps {
  data: TrafficFlowSection;
}

export const TrafficFlowChartWidget: React.FC<TrafficFlowChartWidgetProps> = ({ data }) => {
  const { bucket_interval_seconds, time_series_buckets } = data;

  const hasBuckets = time_series_buckets && time_series_buckets.length > 0;
  const maxCount = hasBuckets ? Math.max(...time_series_buckets.map((b) => b.count), 1) : 1;

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>Traffic Flow Metrics (Discrete Time-Series)</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              {hasBuckets
                ? `${time_series_buckets.length} non-interpolated time intervals (${bucket_interval_seconds}s per bucket)`
                : 'No time-series buckets'}
            </p>
          </div>
        </div>

        <ProvenanceBadge provenance={data.provenance} size="sm" />
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {hasBuckets ? (
          <div className="space-y-3">
            {/* Discrete Bucket Visualizer */}
            <div className="flex items-end gap-2 h-36 p-3 rounded-xl bg-slate-950/60 border border-slate-800 overflow-x-auto">
              {time_series_buckets.map((bucket) => {
                const heightPct = Math.max((bucket.count / maxCount) * 100, 8);
                return (
                  <div
                    key={bucket.bucket_index}
                    className="flex-1 min-w-[36px] max-w-[64px] flex flex-col items-center justify-end h-full group relative"
                  >
                    {/* Tooltip on hover */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-10 bg-slate-800 text-white text-[10px] rounded px-1.5 py-0.5 border border-slate-700 whitespace-nowrap pointer-events-none z-10 shadow-lg">
                      {bucket.count} veh ({bucket.flow_rate_per_minute.toFixed(1)}/min)
                    </div>

                    <div className="text-[10px] font-mono text-cyan-400 mb-1 font-bold">
                      {bucket.count}
                    </div>

                    <div
                      className="w-full rounded-t-md bg-gradient-to-t from-cyan-600 to-cyan-400 group-hover:from-cyan-500 group-hover:to-cyan-300 transition-all shadow-md shadow-cyan-950/50"
                      style={{ height: `${heightPct}%` }}
                    />

                    <div className="text-[9px] font-mono text-slate-400 mt-1 truncate">
                      {bucket.start_time_seconds.toFixed(0)}s
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 px-1 font-mono">
              <span>Bucket size: {bucket_interval_seconds}s discrete</span>
              <span>Discrete intervals — zero spline interpolation</span>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-slate-400 rounded-xl bg-slate-950/40 border border-slate-800/60 flex flex-col items-center gap-2">
            <BarChart3 className="h-6 w-6 text-slate-400" />
            <span>No discrete time-series flow records found for active session.</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
