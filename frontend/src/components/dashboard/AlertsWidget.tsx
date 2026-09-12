import React, { useState, useEffect, useCallback } from 'react';
import {
  listAnomalyEvents,
  triggerAnomalyDetection,
  updateAnomalyStatus,
  deleteAnomalyEvent,
} from '@/api/anomalies';
import { AnomalyEvent, AnomalySeverity, AnomalyStatus } from '@/types/anomaly';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Zap,
  RotateCw,
  Info,
  Check,
  Trash2,
  ChevronDown,
  ChevronUp,
  Layers,
} from 'lucide-react';

interface AlertsWidgetProps {
  activeSessionId?: string | null;
  videoFilename?: string | null;
  isSyntheticSession?: boolean;
}

export const AlertsWidget: React.FC<AlertsWidgetProps> = ({
  activeSessionId,
}) => {
  const [events, setEvents] = useState<AnomalyEvent[]>([]);
  const [activeCount, setActiveCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [detecting, setDetecting] = useState<boolean>(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');
  const [showNoteModalId, setShowNoteModalId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState<string>('');
  const [actionTargetStatus, setActionTargetStatus] = useState<AnomalyStatus>('acknowledged');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { limit: 100 };
      if (activeSessionId) {
        params.session_id = activeSessionId;
      }
      if (filterStatus !== 'all') {
        params.status = filterStatus;
      }
      if (filterSeverity !== 'all') {
        params.severity = filterSeverity;
      }
      if (filterType !== 'all') {
        params.anomaly_type = filterType;
      }

      const res = await listAnomalyEvents(params);
      setEvents(res.events || []);
      setActiveCount(res.active_count || 0);
    } catch (err) {
      console.error('Failed to load anomaly events', err);
    } finally {
      setLoading(false);
    }
  }, [activeSessionId, filterStatus, filterSeverity, filterType]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handleTriggerDetection = async () => {
    if (!activeSessionId) return;
    setDetecting(true);
    try {
      await triggerAnomalyDetection(activeSessionId);
      await fetchEvents();
    } catch (err) {
      console.error('Failed to run anomaly detection', err);
    } finally {
      setDetecting(false);
    }
  };

  const handleUpdateStatus = async (eventId: string, status: AnomalyStatus, note?: string) => {
    setActionLoadingId(eventId);
    try {
      await updateAnomalyStatus(eventId, { status, note });
      setShowNoteModalId(null);
      setNoteText('');
      await fetchEvents();
    } catch (err) {
      console.error(`Failed to update status to ${status}`, err);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDelete = async (eventId: string) => {
    if (!window.confirm('Are you sure you want to delete this anomaly record?')) return;
    setActionLoadingId(eventId);
    try {
      await deleteAnomalyEvent(eventId);
      await fetchEvents();
    } catch (err) {
      console.error('Failed to delete anomaly event', err);
    } finally {
      setActionLoadingId(null);
    }
  };

  const getSeverityBadge = (severity: AnomalySeverity) => {
    switch (severity) {
      case 'critical':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-rose-950/80 text-rose-300 border border-rose-600/60 animate-pulse">
            CRITICAL
          </span>
        );
      case 'high':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-amber-950/80 text-amber-300 border border-amber-600/60">
            HIGH
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-yellow-950/60 text-yellow-300 border border-yellow-700/50">
            MEDIUM
          </span>
        );
      case 'low':
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-cyan-950/60 text-cyan-300 border border-cyan-700/50">
            LOW
          </span>
        );
    }
  };

  const getStatusBadge = (status: AnomalyStatus) => {
    switch (status) {
      case 'open':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-ping" />
            Open
          </span>
        );
      case 'acknowledged':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            Acknowledged
          </span>
        );
      case 'resolved':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3 w-3" />
            Resolved
          </span>
        );
    }
  };

  const formatTypeName = (type: string) => {
    switch (type) {
      case 'congestion_buildup':
        return 'Congestion Buildup';
      case 'flow_drop':
        return 'Abnormal Flow Drop';
      case 'lane_imbalance':
        return 'Lane Imbalance';
      case 'density_spike':
        return 'Density Spike';
      default:
        return type.replace(/_/g, ' ');
    }
  };

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-xl">
      {/* Widget Header */}
      <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-rose-950/60 border border-rose-800/50 text-rose-400">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white flex items-center gap-2 flex-wrap">
              <span>Traffic Anomaly & Incident Detection</span>
              <Badge variant="danger" size="sm">Phase 15</Badge>
              {activeCount > 0 && (
                <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                  {activeCount} Active
                </span>
              )}
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              Explainable rule-based statistical anomaly monitoring with lifecycle state tracking
            </p>
          </div>
        </div>

        {/* Action Buttons & Manual Run */}
        <div className="flex items-center gap-2 flex-wrap">
          {activeSessionId && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleTriggerDetection}
              disabled={detecting}
              className="bg-rose-950/40 border-rose-800/60 hover:bg-rose-900/50 text-rose-200 text-xs flex items-center gap-1.5"
              title="Execute idempotent rule detection over this session's metrics"
            >
              <Zap className={`h-3.5 w-3.5 text-rose-400 ${detecting ? 'animate-spin' : ''}`} />
              <span>{detecting ? 'Evaluating Rules...' : 'Run Detection'}</span>
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={fetchEvents}
            disabled={loading}
            className="text-slate-400 hover:text-white p-1.5"
            title="Refresh alerts list"
          >
            <RotateCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Filter Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
            <span className="text-slate-400 font-medium mr-1 hidden sm:inline">Status:</span>
            {['all', 'open', 'acknowledged', 'resolved'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-2.5 py-1 rounded-lg font-medium transition-all capitalize ${
                  filterStatus === st
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          {/* Severity & Type Selectors */}
          <div className="flex items-center gap-2">
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              aria-label="Filter by Severity"
              className="bg-slate-900 border border-slate-700 text-slate-200 rounded-lg px-2 py-1 text-xs focus:outline-none focus:border-rose-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              aria-label="Filter by Rule Type"
              className="bg-slate-900 border border-slate-700 text-slate-200 rounded-lg px-2 py-1 text-xs focus:outline-none focus:border-rose-500"
            >
              <option value="all">All Rule Types</option>
              <option value="congestion_buildup">Congestion Buildup</option>
              <option value="flow_drop">Abnormal Flow Drop</option>
              <option value="lane_imbalance">Lane Imbalance</option>
              <option value="density_spike">Density Spike</option>
            </select>
          </div>
        </div>

        {/* Alerts List */}
        {loading && events.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
            <RotateCw className="h-5 w-5 text-rose-400 animate-spin" />
            <span>Scanning persisted operational metrics...</span>
          </div>
        ) : events.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-slate-950/40 border border-slate-800/60 flex flex-col items-center gap-2">
            <CheckCircle2 className="h-8 w-8 text-emerald-400/80 mb-1" />
            <div className="text-sm font-semibold text-slate-200">
              No Anomaly Incidents Detected
            </div>
            <p className="text-xs text-slate-400 max-w-md">
              {activeSessionId
                ? 'Persisted occupancy, flow rate, lane balance, and image-space density are within normal operational thresholds.'
                : 'No anomaly records found for current filter criteria.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {events.map((ev) => {
              const isExpanded = expandedEventId === ev.id;
              const isActionLoading = actionLoadingId === ev.id;

              return (
                <div
                  key={ev.id}
                  className={`p-4 rounded-xl border transition-all ${
                    ev.severity === 'critical'
                      ? 'bg-rose-950/20 border-rose-800/70 shadow-lg shadow-rose-950/20'
                      : ev.severity === 'high'
                      ? 'bg-amber-950/20 border-amber-800/60'
                      : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  {/* Event Top Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      {getSeverityBadge(ev.severity)}
                      {getStatusBadge(ev.status)}
                      <span className="text-xs font-semibold text-slate-300">
                        {formatTypeName(ev.anomaly_type)}
                      </span>
                      {ev.lane_id && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/60 text-indigo-300 border border-indigo-800/50 flex items-center gap-1">
                          <Layers className="h-2.5 w-2.5" />
                          {ev.lane_id}
                        </span>
                      )}
                    </div>

                    {/* Timestamp & Duration */}
                    <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-cyan-400" />
                        T={ev.start_timestamp_seconds.toFixed(1)}s
                      </span>
                      {ev.duration_seconds > 0 ? (
                        <span className="text-slate-400">
                          ({ev.duration_seconds.toFixed(1)}s span)
                        </span>
                      ) : (
                        <span className="text-rose-400">(ongoing)</span>
                      )}
                    </div>
                  </div>

                  {/* Title & Description */}
                  <div className="mt-2">
                    <div className="text-sm font-semibold text-white">{ev.title}</div>
                    <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">
                      {ev.description}
                    </p>
                  </div>

                  {/* Quantitative Trigger Metric Chips */}
                  <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                    <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                      <div className="text-slate-400 text-[10px]">Metric</div>
                      <div className="text-slate-200 font-semibold truncate capitalize">
                        {ev.metric_name.replace(/_/g, ' ')}
                      </div>
                    </div>

                    <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                      <div className="text-slate-400 text-[10px]">Trigger Value</div>
                      <div className="text-rose-300 font-bold">
                        {typeof ev.trigger_value === 'number'
                          ? ev.trigger_value.toFixed(2)
                          : ev.trigger_value}
                      </div>
                    </div>

                    <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                      <div className="text-slate-400 text-[10px]">Threshold</div>
                      <div className="text-slate-300 font-semibold">
                        {typeof ev.threshold_value === 'number'
                          ? ev.threshold_value.toFixed(2)
                          : ev.threshold_value}
                      </div>
                    </div>

                    <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                      <div className="text-slate-400 text-[10px]">Deviation / Ratio</div>
                      <div className="text-amber-300 font-bold">
                        {ev.deviation_pct !== null && ev.deviation_pct !== undefined
                          ? ev.anomaly_type === 'flow_drop'
                            ? `-${ev.deviation_pct.toFixed(1)}%`
                            : `${ev.deviation_pct.toFixed(2)}x`
                          : 'N/A'}
                      </div>
                    </div>
                  </div>

                  {/* Operator Note if Present */}
                  {ev.details_json?.operator_note && (
                    <div className="mt-2 p-2 rounded-lg bg-amber-950/30 border border-amber-800/40 text-xs text-amber-200 flex items-start gap-2">
                      <Info className="h-3.5 w-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <span className="font-semibold">Operator Note: </span>
                        {ev.details_json.operator_note}
                      </div>
                    </div>
                  )}

                  {/* Provenance & Action Bar */}
                  <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                    {/* Provenance Stamp */}
                    <div className="flex items-center gap-2 flex-wrap text-[11px] text-slate-400">
                      {ev.is_synthetic ? (
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          Synthetic Pipeline Metrics
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                          <Check className="h-3 w-3" />
                          Real Database Metrics
                        </span>
                      )}
                      <span className="font-mono text-slate-400">
                        Session: {ev.session_id.substring(0, 8)}...
                      </span>
                    </div>

                    {/* Interactive Lifecycle Actions */}
                    <div className="flex items-center gap-2">
                      {ev.status === 'open' && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={isActionLoading}
                          onClick={() => {
                            setActionTargetStatus('acknowledged');
                            setShowNoteModalId(ev.id);
                          }}
                          className="text-xs bg-amber-950/40 border-amber-700/60 hover:bg-amber-900/60 text-amber-200 py-1 px-2.5 h-auto"
                        >
                          Acknowledge
                        </Button>
                      )}

                      {ev.status !== 'resolved' && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={isActionLoading}
                          onClick={() => {
                            setActionTargetStatus('resolved');
                            setShowNoteModalId(ev.id);
                          }}
                          className="text-xs bg-emerald-950/40 border-emerald-700/60 hover:bg-emerald-900/60 text-emerald-200 py-1 px-2.5 h-auto flex items-center gap-1"
                        >
                          <Check className="h-3 w-3" />
                          Resolve
                        </Button>
                      )}

                      {/* Expand / Details Toggle */}
                      <button
                        onClick={() => setExpandedEventId(isExpanded ? null : ev.id)}
                        className="text-slate-400 hover:text-slate-200 p-1"
                        title="Toggle event details"
                      >
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>

                      {/* Delete */}
                      <button
                        onClick={() => handleDelete(ev.id)}
                        disabled={isActionLoading}
                        className="text-slate-500 hover:text-rose-400 p-1 transition-colors"
                        title="Delete event record"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Expanded Technical Details */}
                  {isExpanded && (
                    <div className="mt-3 p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-xs font-mono space-y-2">
                      <div className="text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                        Detailed Payload Breakdown
                      </div>
                      <pre className="text-slate-300 text-[11px] overflow-x-auto p-2 rounded bg-black/40 border border-slate-800">
                        {JSON.stringify(ev.details_json || {}, null, 2)}
                      </pre>
                      <div className="text-[10px] text-slate-400 flex items-center justify-between">
                        <span>Event ID: {ev.id}</span>
                        <span>Created: {new Date(ev.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                  )}

                  {/* Operator Note Dialog Modal inline */}
                  {showNoteModalId === ev.id && (
                    <div className="mt-3 p-3 rounded-xl bg-slate-900 border border-cyan-500/40 space-y-2">
                      <div className="text-xs font-semibold text-cyan-300 flex items-center gap-1.5">
                        <Info className="h-3.5 w-3.5" />
                        <span>
                          {actionTargetStatus === 'resolved' ? 'Resolve Incident' : 'Acknowledge Incident'} - Add Operator Note (Optional)
                        </span>
                      </div>
                      <input
                        type="text"
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                        placeholder="e.g. Signal timing adjusted / Cleared downstream bottleneck"
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                        autoFocus
                      />
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setShowNoteModalId(null);
                            setNoteText('');
                          }}
                          className="text-xs text-slate-400 hover:text-white py-1 px-2.5 h-auto"
                        >
                          Cancel
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleUpdateStatus(ev.id, actionTargetStatus, noteText)}
                          disabled={isActionLoading}
                          className="text-xs py-1 px-3 h-auto"
                        >
                          Confirm {actionTargetStatus}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Explainable Anti-Fabrication Notice */}
        <div className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-400 leading-relaxed">
          <Info className="h-4 w-4 text-cyan-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-semibold text-slate-300">Rule-Based Anomaly Qualification: </span>
            Incidents are identified purely by mathematical deviations on persisted flow, occupancy, and image-space density.
            Zero black-box ML inference or hallucinated collision detection.
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
