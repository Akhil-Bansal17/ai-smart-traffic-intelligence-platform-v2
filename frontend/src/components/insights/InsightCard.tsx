import React, { useState } from 'react';
import { TrafficInsight } from '@/types/insight';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  Lightbulb,
  Clock,
  Layers,
  ChevronDown,
  ChevronUp,
  Maximize2,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react';

interface InsightCardProps {
  insight: TrafficInsight;
  onSelect: (insight: TrafficInsight) => void;
  onUpdateStatus?: (insightId: string, status: string) => Promise<void>;
}

export const InsightCard: React.FC<InsightCardProps> = ({
  insight,
  onSelect,
  onUpdateStatus,
}) => {
  const [expanded, setExpanded] = useState<boolean>(false);

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
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 font-mono flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          REAL DATA
        </span>
      );
    }
    return (
      <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-950/60 border border-amber-800/60 text-amber-300 font-mono flex items-center gap-1">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
        {cat.toUpperCase()}
      </span>
    );
  };

  const isCriticalOrHigh = ['CRITICAL', 'HIGH'].includes(insight.severity.toUpperCase());

  return (
    <Card
      className={`border transition-all duration-200 ${
        isCriticalOrHigh
          ? 'border-slate-700/80 bg-slate-900/90 shadow-md shadow-black/30'
          : 'border-slate-800/70 bg-slate-900/60 hover:border-slate-700'
      }`}
    >
      <CardContent className="p-4 space-y-3">
        {/* Top Header Row */}
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={getSeverityBadgeVariant(insight.severity)}>
              {insight.severity}
            </Badge>
            <span
              className={`text-[11px] px-2.5 py-0.5 rounded-full font-mono border font-medium ${getCategoryColor(
                insight.category
              )}`}
            >
              {insight.category}
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
              {insight.status}
            </span>
            {renderProvenanceTag(insight.provenance_category)}
          </div>

          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onSelect(insight)}
              className="h-7 px-2 text-xs text-slate-400 hover:text-cyan-400 hover:bg-slate-800"
              title="Inspect Full Evidence Package"
            >
              <Maximize2 className="h-3.5 w-3.5 mr-1" />
              <span>Evidence</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              className="h-7 w-7 p-0 text-slate-400 hover:text-white"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        {/* Title & Timing */}
        <div>
          <h4 className="text-sm font-semibold text-white tracking-tight leading-snug">
            {insight.title}
          </h4>
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3 text-cyan-400" />
              Window: {insight.start_timestamp_seconds.toFixed(1)}s –{' '}
              {insight.end_timestamp_seconds?.toFixed(1) || insight.duration_seconds.toFixed(1)}s
            </span>
            {insight.affected_lane_name && (
              <span className="flex items-center gap-1">
                <Layers className="h-3 w-3 text-indigo-400" />
                Lane: {insight.affected_lane_name}
              </span>
            )}
          </div>
        </div>

        {/* Summary */}
        <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60">
          {insight.summary}
        </p>

        {/* Advisory Recommendation Box */}
        {insight.recommendation && (
          <div className="p-3 rounded-lg bg-cyan-950/20 border border-cyan-900/40 space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-400">
              <Lightbulb className="h-3.5 w-3.5" />
              <span>Advisory Recommendation ({insight.recommendation_type || 'action'})</span>
            </div>
            <p className="text-xs text-cyan-100 leading-relaxed">
              {insight.recommendation}
            </p>
          </div>
        )}

        {/* Expandable Root-Cause Breakdown */}
        {expanded && (
          <div className="space-y-3 pt-2 border-t border-slate-800/80 animate-in fade-in duration-150">
            {/* Observed Factors */}
            {insight.root_cause_observed && insight.root_cause_observed.length > 0 && (
              <div className="space-y-1.5">
                <div className="text-[11px] font-semibold text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  <span>Observed Measurements</span>
                </div>
                <div className="space-y-1">
                  {insight.root_cause_observed.map((obs, idx) => (
                    <div
                      key={idx}
                      className="text-[11px] p-2 rounded bg-emerald-950/20 border border-emerald-900/30 text-emerald-200 flex items-start gap-1.5"
                    >
                      <span className="px-1 py-0.2 rounded bg-emerald-900/50 text-[9px] font-bold text-emerald-300 font-mono">
                        Observed
                      </span>
                      <span>{obs.statement}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Inferred Factors */}
            {insight.root_cause_inferred && insight.root_cause_inferred.length > 0 && (
              <div className="space-y-1.5">
                <div className="text-[11px] font-semibold text-amber-400 flex items-center gap-1">
                  <HelpCircle className="h-3 w-3" />
                  <span>Inferred Deductions</span>
                </div>
                <div className="space-y-1">
                  {insight.root_cause_inferred.map((inf, idx) => (
                    <div
                      key={idx}
                      className="text-[11px] p-2 rounded bg-amber-950/20 border border-amber-900/30 text-amber-200 flex items-start gap-1.5"
                    >
                      <span className="px-1 py-0.2 rounded bg-amber-900/50 text-[9px] font-bold text-amber-300 font-mono">
                        Inferred
                      </span>
                      <span>{inf.statement}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Status Action Buttons */}
            {onUpdateStatus && insight.status === 'ACTIVE' && (
              <div className="flex justify-end pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onUpdateStatus(insight.id, 'DISMISSED')}
                  className="h-6 text-[10px] text-slate-400 hover:text-slate-200"
                >
                  Dismiss Insight
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
