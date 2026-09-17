import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  FileText,
  FileSpreadsheet,
  Download,
  Trash2,
  Eye,
  Plus,
  RotateCw,
  Layers,
  ShieldCheck,
  AlertTriangle,
  Sparkles,
  CheckCircle2,
  FileCode,
  X,
} from 'lucide-react';
import {
  createReport,
  listReports,
  getReportDetail,
  downloadReportFile,
  deleteReport,
} from '@/api/reports';
import { getAnalysisSessions } from '@/api/analysis';
import {
  ReportSummary,
  ReportDetail,
  ReportFormat,
  ReportScopeType,
  TruthLabel,
} from '@/types/report';
import { AnalysisSessionSummary } from '@/types/analysis';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

export function ReportsPage() {
  const [searchParams] = useSearchParams();
  const preselectedSessionId = searchParams.get('sessionId') || '';

  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [sessions, setSessions] = useState<AnalysisSessionSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedReportDetail, setSelectedReportDetail] = useState<ReportDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  // Form State
  const [scopeType, setScopeType] = useState<ReportScopeType>('session');
  const [selectedSessionId, setSelectedSessionId] = useState<string>(preselectedSessionId);
  const [timeRangeStart, setTimeRangeStart] = useState<string>('');
  const [timeRangeEnd, setTimeRangeEnd] = useState<string>('');
  const [exportFormat, setExportFormat] = useState<ReportFormat>('pdf');
  const [customTitle, setCustomTitle] = useState<string>('');
  const [formFeedback, setFormFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reportsRes, sessionsRes] = await Promise.all([
        listReports(0, 50),
        getAnalysisSessions(1, 50),
      ]);
      setReports(reportsRes.items);
      setSessions(sessionsRes.sessions);

      if (!selectedSessionId && sessionsRes.sessions.length > 0) {
        setSelectedSessionId(preselectedSessionId || sessionsRes.sessions[0].id);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load reports and analysis sessions.');
    } finally {
      setLoading(false);
    }
  }, [preselectedSessionId, selectedSessionId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    setGenerating(true);
    setFormFeedback(null);

    try {
      const payload = {
        report_type: 'traffic_analysis',
        scope_type: scopeType,
        session_id: scopeType === 'session' ? selectedSessionId : undefined,
        time_range_start: scopeType === 'time_range' && timeRangeStart ? new Date(timeRangeStart).toISOString() : undefined,
        time_range_end: scopeType === 'time_range' && timeRangeEnd ? new Date(timeRangeEnd).toISOString() : undefined,
        format: exportFormat,
        title: customTitle.trim() || undefined,
      };

      const newReport = await createReport(payload);
      setFormFeedback({
        type: 'success',
        message: `Report "${newReport.title}" generated successfully in ${newReport.processing_time_ms}ms!`,
      });
      // Refresh list
      const updatedList = await listReports(0, 50);
      setReports(updatedList.items);
      setCustomTitle('');
    } catch (err: any) {
      setFormFeedback({
        type: 'error',
        message: err?.message || 'Failed to generate report.',
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (reportId: string) => {
    try {
      await downloadReportFile(reportId);
    } catch (err: any) {
      alert(`Download failed: ${err?.message || 'Unknown error'}`);
    }
  };

  const handleDelete = async (reportId: string) => {
    if (!window.confirm('Are you sure you want to delete this generated report and its file artifact?')) {
      return;
    }
    try {
      await deleteReport(reportId);
      setReports((prev) => prev.filter((r) => r.id !== reportId));
      if (selectedReportDetail?.id === reportId) {
        setSelectedReportDetail(null);
      }
    } catch (err: any) {
      alert(`Delete failed: ${err?.message || 'Unknown error'}`);
    }
  };

  const handleInspect = async (reportId: string) => {
    setDetailLoading(true);
    try {
      const detail = await getReportDetail(reportId);
      setSelectedReportDetail(detail);
    } catch (err: any) {
      alert(`Failed to load report detail: ${err?.message}`);
    } finally {
      setDetailLoading(false);
    }
  };

  const renderTruthBadge = (label?: TruthLabel | string) => {
    if (!label) return null;
    let extraClass = 'bg-slate-800 text-slate-300 border-slate-700';

    switch (label) {
      case 'OBSERVED':
        extraClass = 'bg-sky-950/80 text-sky-300 border-sky-800/80';
        break;
      case 'INFERRED':
        extraClass = 'bg-purple-950/80 text-purple-300 border-purple-800/80';
        break;
      case 'PREDICTED':
        extraClass = 'bg-teal-950/80 text-teal-300 border-teal-800/80';
        break;
      case 'SIMULATED':
        extraClass = 'bg-indigo-950/80 text-indigo-300 border-indigo-800/80';
        break;
      case 'RECOMMENDED/ADVISORY':
        extraClass = 'bg-amber-950/80 text-amber-300 border-amber-800/80';
        break;
      case 'UNAVAILABLE':
        extraClass = 'bg-slate-900 text-slate-400 border-slate-800';
        break;
    }

    return (
      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold border ${extraClass}`}>
        [{label}]
      </span>
    );
  };

  if (loading && reports.length === 0 && sessions.length === 0) {
    return (
      <div className="py-16">
        <LoadingState message="Loading business reporting system and authoritative traffic records..." />
      </div>
    );
  }

  if (error && reports.length === 0) {
    return (
      <div className="py-16">
        <ErrorState
          title="Reporting Subsystem Unavailable"
          message={error}
          onRetry={loadData}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-16">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-[#0c1322] to-cyan-950/40 shadow-xl shadow-black/40">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                <FileText className="h-6 w-6 text-cyan-400" />
                <span>Business-Grade Traffic Reporting & Export</span>
              </h1>
              <Badge variant="info" size="sm">Phase 19</Badge>
              <Badge variant="success" size="sm" className="hidden sm:inline-flex items-center gap-1 font-mono">
                <ShieldCheck className="h-3 w-3" />
                Deterministic Output
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
              Generate structured, reproducible, and verifiable operational reports in PDF and tabular CSV format.
              Every metric originates from authoritative database records with strict epistemic truth labeling.
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            className="self-start md:self-auto flex items-center gap-1.5 bg-slate-900/80 border-slate-700 hover:bg-slate-800 text-slate-200"
          >
            <RotateCw className="h-3.5 w-3.5 text-cyan-400" />
            <span>Refresh Reports</span>
          </Button>
        </div>

        {/* Epistemic Truth Taxonomy Legend Bar */}
        <div className="mt-6 pt-4 border-t border-slate-800/80 flex flex-wrap items-center gap-3 text-xs text-slate-400">
          <span className="font-semibold text-slate-300 uppercase text-[10px] tracking-wider">
            Truth Classification:
          </span>
          {renderTruthBadge('OBSERVED')}
          <span className="text-[11px] text-slate-400">CV Measurement</span>
          {renderTruthBadge('INFERRED')}
          <span className="text-[11px] text-slate-400">Analytical Deduction</span>
          {renderTruthBadge('PREDICTED')}
          <span className="text-[11px] text-slate-400">ML Forecast</span>
          {renderTruthBadge('SIMULATED')}
          <span className="text-[11px] text-slate-400">Signal/Corridor Model</span>
          {renderTruthBadge('RECOMMENDED/ADVISORY')}
          <span className="text-[11px] text-slate-400">Operator Advisory</span>
          {renderTruthBadge('UNAVAILABLE')}
          <span className="text-[11px] text-slate-400">Insufficient Data</span>
        </div>
      </div>

      {/* Main Grid: Generator Form & History Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Report Generation Form */}
        <div className="lg:col-span-1 space-y-6">
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/70 shadow-lg space-y-5">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Plus className="h-4 w-4 text-cyan-400" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                Generate New Report
              </h2>
            </div>

            <form onSubmit={handleGenerateReport} className="space-y-4 text-xs">
              {/* Scope Mode Selector */}
              <div>
                <label className="block text-slate-300 font-medium mb-1.5">
                  Analysis Scope Mode
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setScopeType('session')}
                    className={`px-3 py-2 rounded-lg font-medium border text-center transition-all ${
                      scopeType === 'session'
                        ? 'bg-cyan-600/20 border-cyan-500/50 text-cyan-300 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Single Session
                  </button>
                  <button
                    type="button"
                    onClick={() => setScopeType('time_range')}
                    className={`px-3 py-2 rounded-lg font-medium border text-center transition-all ${
                      scopeType === 'time_range'
                        ? 'bg-cyan-600/20 border-cyan-500/50 text-cyan-300 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Date / Time Range
                  </button>
                </div>
              </div>

              {/* Session Selector (when scope_type === 'session') */}
              {scopeType === 'session' ? (
                <div>
                  <label className="block text-slate-300 font-medium mb-1.5">
                    Target Analysis Session
                  </label>
                  <select
                    value={selectedSessionId}
                    onChange={(e) => setSelectedSessionId(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono text-xs"
                  >
                    {sessions.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.video_filename || s.id.slice(0, 8)} ({s.total_vehicles_counted} counted, {new Date(s.started_at).toLocaleDateString()})
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-[11px] text-slate-400">
                    Pulls authoritative counts, lane metrics, anomalies, and insights for this session.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Start Date & Time</label>
                    <input
                      type="datetime-local"
                      value={timeRangeStart}
                      onChange={(e) => setTimeRangeStart(e.target.value)}
                      required
                      className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">End Date & Time</label>
                    <input
                      type="datetime-local"
                      value={timeRangeEnd}
                      onChange={(e) => setTimeRangeEnd(e.target.value)}
                      required
                      className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 text-xs"
                    />
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Aggregates sessions across bounded date range (&le; 30 days).
                  </p>
                </div>
              )}

              {/* Format Selector */}
              <div>
                <label className="block text-slate-300 font-medium mb-1.5">
                  Export Format
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setExportFormat('pdf')}
                    className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-center transition-all ${
                      exportFormat === 'pdf'
                        ? 'bg-rose-950/40 border-rose-500/50 text-rose-300 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <FileText className="h-4 w-4 mb-1 text-rose-400" />
                    <span className="text-[11px] font-semibold">PDF Document</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setExportFormat('csv')}
                    className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-center transition-all ${
                      exportFormat === 'csv'
                        ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <FileSpreadsheet className="h-4 w-4 mb-1 text-emerald-400" />
                    <span className="text-[11px] font-semibold">CSV Tabular</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setExportFormat('json')}
                    className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-center transition-all ${
                      exportFormat === 'json'
                        ? 'bg-cyan-950/40 border-cyan-500/50 text-cyan-300 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <FileCode className="h-4 w-4 mb-1 text-cyan-400" />
                    <span className="text-[11px] font-semibold">JSON Schema</span>
                  </button>
                </div>
              </div>

              {/* Custom Title Input */}
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Custom Report Title <span className="text-slate-400 font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g., Arterial Corridor Morning Peak Audit"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 text-xs"
                />
              </div>

              {/* Feedback Alert */}
              {formFeedback && (
                <div
                  className={`p-3 rounded-lg border text-xs flex items-start gap-2 ${
                    formFeedback.type === 'success'
                      ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
                      : 'bg-rose-950/40 border-rose-800/60 text-rose-300'
                  }`}
                >
                  {formFeedback.type === 'success' ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                  )}
                  <span>{formFeedback.message}</span>
                </div>
              )}

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={generating || (scopeType === 'session' && !selectedSessionId)}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold py-2.5 shadow-md shadow-cyan-950/50"
              >
                {generating ? (
                  <>
                    <RotateCw className="h-4 w-4 animate-spin text-white" />
                    <span>Assembling Report...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 text-cyan-200" />
                    <span>Generate & Export Report</span>
                  </>
                )}
              </Button>
            </form>
          </div>
        </div>

        {/* Right Column: Generated Reports History Table */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/70 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-cyan-400" />
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                  Report Archive & Artifacts
                </h2>
                <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/60">
                  {reports.length} Reports
                </span>
              </div>
            </div>

            {reports.length === 0 ? (
              <EmptyState
                title="No Reports Generated Yet"
                description="Select an analysis session or date range on the left to generate your first structured operational traffic report."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead>
                    <tr className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 bg-slate-950/40">
                      <th className="py-2.5 px-3">Title & Scope</th>
                      <th className="py-2.5 px-3">Format</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Size / Latency</th>
                      <th className="py-2.5 px-3">Created</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {reports.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-3">
                          <div className="font-semibold text-slate-100">{r.title}</div>
                          <div className="text-[10px] font-mono text-slate-400">
                            {r.scope_type === 'session' ? `Session ${r.session_id?.slice(0, 8)}...` : 'Time Range'}
                          </div>
                        </td>

                        <td className="py-3 px-3">
                          <span className={`inline-flex items-center gap-1 font-mono font-bold uppercase text-[10px] px-2 py-0.5 rounded border ${
                            r.format === 'pdf'
                              ? 'bg-rose-950/60 text-rose-300 border-rose-800/60'
                              : r.format === 'csv'
                              ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                              : 'bg-cyan-950/60 text-cyan-300 border-cyan-800/60'
                          }`}>
                            {r.format === 'pdf' && <FileText className="h-3 w-3" />}
                            {r.format === 'csv' && <FileSpreadsheet className="h-3 w-3" />}
                            {r.format === 'json' && <FileCode className="h-3 w-3" />}
                            {r.format}
                          </span>
                        </td>

                        <td className="py-3 px-3">
                          {r.status === 'completed' && (
                            <Badge variant="success" size="sm">Completed</Badge>
                          )}
                          {r.status === 'generating' && (
                            <Badge variant="warning" size="sm">Generating</Badge>
                          )}
                          {r.status === 'failed' && (
                            <Badge variant="danger" size="sm">Failed</Badge>
                          )}
                        </td>

                        <td className="py-3 px-3 font-mono text-[11px] text-slate-400">
                          {r.file_size_bytes ? `${(r.file_size_bytes / 1024).toFixed(1)} KB` : '—'}
                          {r.processing_time_ms && (
                            <span className="block text-[10px] text-slate-400">{r.processing_time_ms}ms</span>
                          )}
                        </td>

                        <td className="py-3 px-3 text-slate-400 text-[11px]">
                          {new Date(r.created_at).toLocaleString()}
                        </td>

                        <td className="py-3 px-3 text-right space-x-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleInspect(r.id)}
                            title="Inspect structured report data"
                            className="p-1.5 h-7 w-7 text-slate-300 hover:text-cyan-400 hover:bg-slate-800"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>

                          {r.status === 'completed' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDownload(r.id)}
                              title="Download report artifact"
                              className="p-1.5 h-7 w-7 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-950/50"
                            >
                              <Download className="h-3.5 w-3.5" />
                            </Button>
                          )}

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(r.id)}
                            title="Delete report"
                            className="p-1.5 h-7 w-7 text-rose-400 hover:text-rose-300 hover:bg-rose-950/50"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Report Inspection Modal */}
      {selectedReportDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md overflow-y-auto">
          <div className="bg-[#0f172a] border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-cyan-400" />
                  <h3 className="text-base font-bold text-white">
                    {selectedReportDetail.title}
                  </h3>
                  <Badge variant="info" size="sm">{selectedReportDetail.format.toUpperCase()}</Badge>
                </div>
                <div className="text-[11px] font-mono text-slate-400">
                  ID: {selectedReportDetail.id} • Created: {new Date(selectedReportDetail.created_at).toUTCString()}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {selectedReportDetail.status === 'completed' && (
                  <Button
                    size="sm"
                    onClick={() => handleDownload(selectedReportDetail.id)}
                    className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white"
                  >
                    <Download className="h-3.5 w-3.5" />
                    <span>Download {selectedReportDetail.format.toUpperCase()}</span>
                  </Button>
                )}
                <button
                  onClick={() => setSelectedReportDetail(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Modal Content Scrollable Area */}
            <div className="p-6 overflow-y-auto space-y-6 text-xs text-slate-300">
              {detailLoading ? (
                <LoadingState message="Loading assembled report content..." />
              ) : selectedReportDetail.report_data ? (
                <>
                  {/* 1. Executive Summary KPIs */}
                  <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                      <span className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
                        1. Executive Summary & Core Telemetry
                      </span>
                      {renderTruthBadge('OBSERVED')}
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
                      <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-[10px] text-slate-400 uppercase">Vehicles Counted</div>
                        <div className="text-base font-bold text-white">
                          {selectedReportDetail.report_data.executive_summary.total_vehicles_counted}
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-[10px] text-slate-400 uppercase">Flow Rate (vph)</div>
                        <div className="text-base font-bold text-cyan-300">
                          {selectedReportDetail.report_data.executive_summary.flow_rate_vph.toFixed(1)}
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-[10px] text-slate-400 uppercase">Dominant Class</div>
                        <div className="text-base font-bold text-emerald-300">
                          {selectedReportDetail.report_data.executive_summary.dominant_vehicle_class} ({selectedReportDetail.report_data.executive_summary.dominant_class_pct.toFixed(1)}%)
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-[10px] text-slate-400 uppercase">Active Insights</div>
                        <div className="text-base font-bold text-amber-300">
                          {selectedReportDetail.report_data.executive_summary.active_insights_count}
                        </div>
                      </div>
                    </div>

                    <p className="text-slate-300 text-xs leading-relaxed pt-1">
                      {selectedReportDetail.report_data.executive_summary.high_level_assessment}
                    </p>
                  </div>

                  {/* 2. Vehicle Composition & Modal Split */}
                  <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                      <span className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
                        2. Vehicle Composition & Modal Split
                      </span>
                      {renderTruthBadge(selectedReportDetail.report_data.vehicle_composition.label)}
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                      {selectedReportDetail.report_data.vehicle_composition.items.map((item) => (
                        <div key={item.class_name} className="p-2 rounded bg-slate-900 border border-slate-800/80 flex items-center justify-between">
                          <span className="text-slate-200 font-medium">{item.class_name}</span>
                          <span className="font-mono text-slate-400 font-bold">{item.count} ({item.percentage.toFixed(1)}%)</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 3. Lane Analysis & Density */}
                  {selectedReportDetail.report_data.lane_analysis.items.length > 0 && (
                    <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                        <span className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
                          3. Lane Spatial Occupancy & Density
                        </span>
                        <div className="flex gap-1.5">
                          {renderTruthBadge('OBSERVED')}
                          {renderTruthBadge('INFERRED')}
                        </div>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-[11px] font-mono">
                          <thead>
                            <tr className="border-b border-slate-800 text-slate-400">
                              <th className="py-1.5">Lane</th>
                              <th className="py-1.5">Vehicles (Obs)</th>
                              <th className="py-1.5">Occupancy (Obs)</th>
                              <th className="py-1.5">Density px⁻² (Inf)</th>
                              <th className="py-1.5">Score (Inf)</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/50">
                            {selectedReportDetail.report_data.lane_analysis.items.map((lr) => (
                              <tr key={lr.lane_id}>
                                <td className="py-1.5 text-slate-200 font-semibold">{lr.lane_name}</td>
                                <td className="py-1.5">{lr.vehicles_detected}</td>
                                <td className="py-1.5">{(lr.occupancy_rate * 100).toFixed(1)}%</td>
                                <td className="py-1.5">{lr.density_px2.toFixed(6)}</td>
                                <td className="py-1.5 text-cyan-300 font-bold">{lr.normalized_density_score.toFixed(2)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="text-[10px] text-slate-400 italic">
                        {selectedReportDetail.report_data.lane_analysis.uncalibrated_warning}
                      </p>
                    </div>
                  )}

                  {/* 4. Decision Intelligence Insights */}
                  {selectedReportDetail.report_data.insights.items.length > 0 && (
                    <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                        <span className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
                          4. Decision Intelligence Insights
                        </span>
                        <div className="flex gap-1.5">
                          {renderTruthBadge('INFERRED')}
                          {renderTruthBadge('RECOMMENDED/ADVISORY')}
                        </div>
                      </div>
                      <div className="space-y-2.5">
                        {selectedReportDetail.report_data.insights.items.map((ins) => (
                          <div key={ins.id} className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-slate-100">
                                [{ins.category}] {ins.title}
                              </span>
                              <Badge variant={ins.severity === 'CRITICAL' ? 'danger' : 'warning'} size="sm">
                                {ins.severity}
                              </Badge>
                            </div>
                            <p className="text-slate-400 text-xs">{ins.summary}</p>
                            {ins.recommendation && (
                              <div className="p-2 rounded bg-amber-950/20 border border-amber-900/40 text-[11px] text-amber-200">
                                <b>Advisory Guidance ({ins.recommendation_type}):</b> {ins.recommendation}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 5. ML Forecast Readiness & Provenance Audit */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-2">
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                        <span className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
                          5. ML Forecast Status
                        </span>
                        {renderTruthBadge(selectedReportDetail.report_data.prediction_status.label)}
                      </div>
                      <p className="text-slate-300 text-xs">
                        {selectedReportDetail.report_data.prediction_status.reason}
                      </p>
                      <div className="text-[11px] font-mono text-slate-400">
                        Samples: {selectedReportDetail.report_data.prediction_status.sample_count} / Threshold: {selectedReportDetail.report_data.prediction_status.sample_threshold}
                      </div>
                    </div>

                    <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-2">
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                        <span className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
                          6. Provenance & Quality Audit
                        </span>
                        {renderTruthBadge(selectedReportDetail.report_data.provenance.label)}
                      </div>
                      <p className="text-slate-300 text-xs">
                        {selectedReportDetail.report_data.provenance.provenance_tier_description}
                      </p>
                      <div className="text-[11px] font-mono text-slate-400">
                        Verified Real-World: <b>{selectedReportDetail.report_data.provenance.provenance_verified ? 'YES' : 'NO'}</b>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  No normalized report content available for this record.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ReportsPage;
