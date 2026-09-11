import React from 'react';
import { LaneDensitySection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Layers, AlertCircle, ArrowUpRight, Compass } from 'lucide-react';
import { Link } from 'react-router-dom';

interface LaneDensityWidgetProps {
  data: LaneDensitySection;
}

export const LaneDensityWidget: React.FC<LaneDensityWidgetProps> = ({ data }) => {
  const { total_lanes_analyzed, density_unit, calibration_warning, lanes } = data;

  const hasLanes = lanes && lanes.length > 0;

  const getDensityBadge = (score: number) => {
    if (score < 0.3) return <Badge variant="success" size="sm">Fluid</Badge>;
    if (score < 0.7) return <Badge variant="warning" size="sm">Moderate</Badge>;
    return <Badge variant="danger" size="sm">Heavy</Badge>;
  };

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-950/60 border border-indigo-800/50 text-indigo-400">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>Lane & Density Intelligence</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              {hasLanes
                ? `${total_lanes_analyzed} configured lane polygon regions evaluated`
                : 'No polygonal lane regions evaluated'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge provenance={data.provenance} size="sm" />
          <Link
            to="/traffic-analytics"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Open Traffic Analytics"
          >
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {hasLanes ? (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {lanes.map((lane) => (
                <div
                  key={lane.lane_id}
                  className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-white">{lane.lane_name}</span>
                      {lane.direction_hint && (
                        <span className="text-[10px] text-cyan-400 font-mono flex items-center gap-0.5">
                          <Compass className="h-3 w-3" />
                          {lane.direction_hint}
                        </span>
                      )}
                    </div>
                    {getDensityBadge(lane.normalized_density_score)}
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-800/60 text-center font-mono">
                    <div className="bg-slate-900/80 p-1.5 rounded-lg border border-slate-800/60">
                      <div className="text-[10px] text-slate-400">Unique Veh</div>
                      <div className="text-sm font-bold text-slate-200 mt-0.5">
                        {lane.unique_vehicles_count}
                      </div>
                    </div>

                    <div className="bg-slate-900/80 p-1.5 rounded-lg border border-slate-800/60">
                      <div className="text-[10px] text-slate-400">Peak Occ</div>
                      <div className="text-sm font-bold text-slate-200 mt-0.5">{lane.peak_occupancy}</div>
                    </div>

                    <div className="bg-slate-900/80 p-1.5 rounded-lg border border-slate-800/60">
                      <div className="text-[10px] text-slate-400">Avg Occ</div>
                      <div className="text-sm font-bold text-slate-200 mt-0.5">
                        {lane.average_occupancy.toFixed(1)}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1">
                    <span>Shoelace Area: {Math.round(lane.polygon_area_px2).toLocaleString()} px²</span>
                    <span className="text-indigo-300">
                      {(lane.image_space_density * 1000).toFixed(4)} k{density_unit}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Calibration Warning */}
            <div className="flex items-start gap-2 p-2 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-slate-400">
              <AlertCircle className="h-3.5 w-3.5 text-indigo-400 mt-0.5 flex-shrink-0" />
              <span>{calibration_warning}</span>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-slate-400 rounded-xl bg-slate-950/40 border border-slate-800/60 flex flex-col items-center gap-2">
            <Layers className="h-6 w-6 text-slate-400" />
            <span>No polygon lane regions evaluated for active session.</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
