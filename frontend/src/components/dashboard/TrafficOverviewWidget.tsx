import React from 'react';
import { TrafficOverviewSection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Car, Clock, ArrowUpRight, Gauge, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

interface TrafficOverviewWidgetProps {
  data: TrafficOverviewSection;
}

export const TrafficOverviewWidget: React.FC<TrafficOverviewWidgetProps> = ({ data }) => {
  const {
    active_session_id,
    video_filename,
    total_vehicles_counted,
    total_vehicles_detected,
    observation_duration_seconds,
    flow_rate_per_minute,
    flow_rate_per_hour,
    is_extrapolated,
    extrapolation_note,
  } = data;

  const hasSession = !!active_session_id;

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800/50 text-emerald-400">
            <Car className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>Traffic Overview & Live Flow Rates</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              {hasSession && video_filename
                ? `Active Session: ${video_filename} (${observation_duration_seconds.toFixed(1)}s)`
                : 'No active session loaded'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge provenance={data.provenance} size="sm" />
          <Link
            to="/video-analysis"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Open Video Analysis"
          >
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* KPI Cards Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <div className="text-[11px] text-slate-400 font-medium flex items-center gap-1.5">
              <Car className="h-3.5 w-3.5 text-emerald-400" />
              <span>Counted Vehicles</span>
            </div>
            <div className="text-2xl font-bold font-mono text-slate-100 mt-1">
              {hasSession ? total_vehicles_counted.toLocaleString() : '--'}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              {hasSession ? `Detected: ${total_vehicles_detected}` : 'Awaiting input'}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <div className="text-[11px] text-slate-400 font-medium flex items-center gap-1.5">
              <Gauge className="h-3.5 w-3.5 text-cyan-400" />
              <span>Flow / Minute</span>
            </div>
            <div className="text-2xl font-bold font-mono text-cyan-300 mt-1">
              {hasSession ? flow_rate_per_minute.toFixed(1) : '--'}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">veh / min</div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 relative overflow-hidden">
            <div className="flex items-center justify-between">
              <div className="text-[11px] text-slate-400 font-medium flex items-center gap-1.5">
                <Gauge className="h-3.5 w-3.5 text-amber-400" />
                <span>Flow / Hour</span>
              </div>
              {is_extrapolated && (
                <Badge variant="warning" size="sm" className="text-[9px] px-1.5 py-0 font-mono">
                  EXTRAPOLATED
                </Badge>
              )}
            </div>
            <div className="text-2xl font-bold font-mono text-amber-300 mt-1">
              {hasSession ? flow_rate_per_hour.toFixed(0) : '--'}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              {is_extrapolated ? 'Scaled from <1h sample' : 'Measured 1h flow'}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <div className="text-[11px] text-slate-400 font-medium flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              <span>Observed Duration</span>
            </div>
            <div className="text-2xl font-bold font-mono text-slate-100 mt-1">
              {hasSession ? `${observation_duration_seconds.toFixed(1)}s` : '--'}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              {hasSession ? `${(observation_duration_seconds / 60).toFixed(1)} minutes` : 'No duration'}
            </div>
          </div>
        </div>

        {/* Extrapolation Anti-Fabrication Warning Banner */}
        {is_extrapolated && extrapolation_note && (
          <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-300 text-xs">
            <AlertCircle className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
            <div>
              <span className="font-semibold">Anti-Fabrication Notice: </span>
              <span>{extrapolation_note}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
