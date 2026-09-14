import React, { useState, useEffect, useCallback } from 'react';
import { listInsights, generateInsights, updateInsightStatus } from '@/api/insights';
import { TrafficInsight } from '@/types/insight';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { InsightCard } from './InsightCard';
import { InsightDetailModal } from './InsightDetailModal';
import {
  Brain,
  Sparkles,
  RotateCw,
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  Filter,
  ShieldCheck,
} from 'lucide-react';

interface InsightsWidgetProps {
  activeSessionId?: string | null;
  videoFilename?: string | null;
  isSyntheticSession?: boolean;
}

export const InsightsWidget: React.FC<InsightsWidgetProps> = ({
  activeSessionId,
  videoFilename,
}) => {
  const [insights, setInsights] = useState<TrafficInsight[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [activeCount, setActiveCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedInsight, setSelectedInsight] = useState<TrafficInsight | null>(null);

  const fetchInsights = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { limit: 100 };
      if (activeSessionId) {
        params.session_id = activeSessionId;
      }
      if (filterSeverity !== 'all') {
        params.severity = filterSeverity;
      }
      if (filterCategory !== 'all') {
        params.category = filterCategory;
      }
      if (filterStatus !== 'all') {
        params.status = filterStatus;
      }

      const res = await listInsights(params);
      setInsights(res.items || []);
      setTotalCount(res.total || 0);
      setActiveCount(res.active_count || 0);
    } catch (err) {
      console.error('Failed to load decision intelligence insights', err);
    } finally {
      setLoading(false);
    }
  }, [activeSessionId, filterSeverity, filterCategory, filterStatus]);

  useEffect(() => {
    fetchInsights();
  }, [fetchInsights]);

  const handleGenerate = async () => {
    if (!activeSessionId) return;
    setGenerating(true);
    try {
      await generateInsights(activeSessionId);
      await fetchInsights();
    } catch (err) {
      console.error('Failed to generate insights', err);
    } finally {
      setGenerating(false);
    }
  };

  const handleUpdateStatus = async (insightId: string, status: string) => {
    try {
      await updateInsightStatus(insightId, status);
      await fetchInsights();
      if (selectedInsight && selectedInsight.id === insightId) {
        setSelectedInsight(null);
      }
    } catch (err) {
      console.error('Failed to update insight status', err);
    }
  };

  // Compute summary stats
  const highSeverityCount = insights.filter((i) =>
    ['CRITICAL', 'HIGH'].includes(i.severity.toUpperCase())
  ).length;
  const recommendationCount = insights.filter((i) => !!i.recommendation).length;

  return (
    <Card className="border border-slate-800 bg-slate-900/80 shadow-xl shadow-black/30 overflow-hidden">
      {/* Header */}
      <CardHeader className="p-6 border-b border-slate-800/80 bg-gradient-to-r from-slate-900 via-slate-900/90 to-cyan-950/30">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
                <Brain className="h-5 w-5" />
              </div>
              <CardTitle className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                <span>Traffic Decision Intelligence & Explainable Insights</span>
                <Badge variant="info" size="sm">Phase 18</Badge>
              </CardTitle>
            </div>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Deterministic interpretation layer synthesizing observed telemetry into explainable root causes (Observed vs Inferred),
              advisory operational guidance, and structured evidence packages with honest boundary declarations.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
            {activeSessionId && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleGenerate}
                disabled={generating}
                className="flex items-center gap-1.5 text-xs bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold"
                title="Evaluate persisted session records into decision insights (zero heavy CV calls)"
              >
                <Sparkles className={`h-3.5 w-3.5 ${generating ? 'animate-spin' : ''}`} />
                <span>{generating ? 'Interpreting...' : 'Generate Insights'}</span>
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={fetchInsights}
              disabled={loading}
              className="h-8 px-2.5 bg-slate-950 border-slate-800 hover:bg-slate-800 text-slate-300"
              title="Refresh insight list"
            >
              <RotateCw className={`h-3.5 w-3.5 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* KPI Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-slate-800/60 mt-4">
          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
              Total Generated
            </div>
            <div className="text-lg font-bold text-white font-mono mt-0.5">{totalCount}</div>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="text-[10px] font-medium uppercase tracking-wider text-amber-400 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              <span>High / Critical</span>
            </div>
            <div className="text-lg font-bold text-amber-400 font-mono mt-0.5">{highSeverityCount}</div>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="text-[10px] font-medium uppercase tracking-wider text-cyan-400 flex items-center gap-1">
              <Lightbulb className="h-3 w-3" />
              <span>Advisory Actions</span>
            </div>
            <div className="text-lg font-bold text-cyan-400 font-mono mt-0.5">{recommendationCount}</div>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="text-[10px] font-medium uppercase tracking-wider text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" />
              <span>Active State</span>
            </div>
            <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">{activeCount}</div>
          </div>
        </div>
      </CardHeader>

      {/* Filter Bar */}
      <div className="p-4 border-b border-slate-800 bg-slate-950/40 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-400 flex items-center gap-1 font-medium">
            <Filter className="h-3 w-3 text-cyan-400" />
            Filters:
          </span>

          {/* Severity Filter */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-md px-2 py-1 text-slate-200 focus:outline-none focus:border-cyan-500 text-xs"
          >
            <option value="all">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
            <option value="INFO">Info</option>
          </select>

          {/* Category Filter */}
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-md px-2 py-1 text-slate-200 focus:outline-none focus:border-cyan-500 text-xs"
          >
            <option value="all">All Categories</option>
            <option value="CONGESTION">Congestion</option>
            <option value="FLOW_DEGRADATION">Flow Degradation</option>
            <option value="LANE_IMBALANCE">Lane Imbalance</option>
            <option value="DENSITY_SPIKE">Density Spike</option>
            <option value="TRAFFIC_SURGE">Traffic Surge</option>
            <option value="UNDERUTILIZED_LANE">Underutilized Lane</option>
            <option value="OPERATIONAL_RECOMMENDATION">Operational Recommendation</option>
          </select>

          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-md px-2 py-1 text-slate-200 focus:outline-none focus:border-cyan-500 text-xs"
          >
            <option value="all">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="NEW">New</option>
            <option value="RECOVERED">Recovered</option>
            <option value="DISMISSED">Dismissed</option>
          </select>
        </div>

        {activeSessionId && (
          <div className="text-[11px] text-slate-500 font-mono">
            Active Session: {activeSessionId.slice(0, 8)}... {videoFilename && `(${videoFilename})`}
          </div>
        )}
      </div>

      {/* Insights List Body */}
      <CardContent className="p-6">
        {loading && insights.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            <RotateCw className="h-6 w-6 animate-spin mx-auto text-cyan-400 mb-2" />
            <span>Loading decision intelligence records...</span>
          </div>
        ) : insights.length === 0 ? (
          <div className="py-12 text-center text-slate-400 space-y-2">
            <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto" />
            <div className="text-sm font-semibold text-white">No Matching Traffic Insights</div>
            <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
              {activeSessionId
                ? 'No decision insights currently recorded for this session. Click "Generate Insights" above to evaluate persisted metrics.'
                : 'No insights matching the selected filters across the database.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.map((ins) => (
              <InsightCard
                key={ins.id}
                insight={ins}
                onSelect={(selected) => setSelectedInsight(selected)}
                onUpdateStatus={handleUpdateStatus}
              />
            ))}
          </div>
        )}
      </CardContent>

      {/* Full Detail Modal */}
      {selectedInsight && (
        <InsightDetailModal
          insight={selectedInsight}
          onClose={() => setSelectedInsight(null)}
          onUpdateStatus={handleUpdateStatus}
        />
      )}
    </Card>
  );
};
