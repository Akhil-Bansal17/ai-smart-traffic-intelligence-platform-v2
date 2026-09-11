import React from 'react';
import { PredictionStatusSection } from '@/types/dashboard';
import { ProvenanceBadge } from './ProvenanceBadge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Sparkles, AlertTriangle, ArrowUpRight, CheckCircle2, Database } from 'lucide-react';
import { Link } from 'react-router-dom';

interface PredictionAvailabilityWidgetProps {
  data: PredictionStatusSection;
}

export const PredictionAvailabilityWidget: React.FC<PredictionAvailabilityWidgetProps> = ({ data }) => {
  const {
    is_ready,
    real_sample_count,
    synthetic_sample_count,
    threshold,
    readiness_message,
    latest_run_id,
    latest_model_name,
    latest_rmse,
    latest_mae,
    latest_r2,
    latest_horizon_minutes,
  } = data;

  const progressPct = Math.min((real_sample_count / threshold) * 100, 100);

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2">
              <span>Traffic Prediction & Forecasting Readiness</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              Phase 11 ML forecasting capability benchmarked against the 20-observation readiness threshold
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge provenance={data.provenance} size="sm" />
          <Link
            to="/predictions"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Open Predictions Page"
          >
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Real-World Observations Progress Bar */}
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-200">
                Real-World Observation Buckets
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold font-mono text-cyan-300">
                {real_sample_count} / {threshold}
              </span>
              <Badge variant={is_ready ? 'success' : 'warning'} size="sm">
                {is_ready ? 'Ready for ML' : 'Insufficient Real Data'}
              </Badge>
            </div>
          </div>

          <div className="h-2.5 w-full rounded-full bg-slate-900 border border-slate-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                is_ready ? 'bg-emerald-500' : 'bg-gradient-to-r from-amber-500 to-cyan-500'
              }`}
              style={{ width: `${progressPct}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
            <span>Genuine Camera Video Observations: {real_sample_count}</span>
            <span>Synthetic Pipeline Tests: {synthetic_sample_count}</span>
          </div>
        </div>

        {/* Readiness Message Disclaimer */}
        <div
          className={`flex items-start gap-2.5 p-3 rounded-lg border text-xs leading-relaxed ${
            is_ready
              ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-300'
              : 'bg-amber-950/30 border-amber-800/40 text-amber-300'
          }`}
        >
          {is_ready ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 flex-shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
          )}
          <div>
            <span className="font-semibold">Dataset Status: </span>
            <span>{readiness_message}</span>
          </div>
        </div>

        {/* Latest Trained Model Snapshot (if any) */}
        {latest_run_id && (
          <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400 font-medium">Latest Model Run:</span>
              <span className="text-white font-mono font-semibold">{latest_model_name}</span>
            </div>

            <div className="grid grid-cols-4 gap-2 text-center font-mono">
              <div className="bg-slate-900/80 p-1.5 rounded-lg border border-slate-800/60">
                <div className="text-[10px] text-slate-400">Horizon</div>
                <div className="text-xs font-bold text-slate-200 mt-0.5">
                  {latest_horizon_minutes}m
                </div>
              </div>

              <div className="bg-slate-900/80 p-1.5 rounded-lg border border-slate-800/60">
                <div className="text-[10px] text-slate-400">MAE</div>
                <div className="text-xs font-bold text-slate-200 mt-0.5">
                  {latest_mae !== null ? latest_mae.toFixed(3) : '--'}
                </div>
              </div>

              <div className="bg-slate-900/80 p-1.5 rounded-lg border border-slate-800/60">
                <div className="text-[10px] text-slate-400">RMSE</div>
                <div className="text-xs font-bold text-cyan-300 mt-0.5">
                  {latest_rmse !== null ? latest_rmse.toFixed(3) : '--'}
                </div>
              </div>

              <div className="bg-slate-900/80 p-1.5 rounded-lg border border-slate-800/60">
                <div className="text-[10px] text-slate-400">R² Score</div>
                <div className="text-xs font-bold text-emerald-300 mt-0.5">
                  {latest_r2 !== null ? latest_r2.toFixed(3) : '--'}
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
