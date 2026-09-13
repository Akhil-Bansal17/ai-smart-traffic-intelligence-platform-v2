import { useState, useEffect, useCallback } from 'react';
import {
  History,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  Clock,
  Car,
  Trash2,
  Eye,
  X,
  Layers,
  Activity,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  FileVideo,
  BarChart3,
  Check,
  Copy,
} from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import {
  getAnalysisSessions,
  getAnalysisSessionDetail,
  deleteAnalysisSession,
  listAnalysisJobs,
  cancelAnalysisJob,
} from '@/api/analysis';
import {
  AnalysisSessionSummary,
  AnalysisSessionDetail,
  AnalysisJob,
} from '@/types/analysis';
import { Link } from 'react-router-dom';
import {
  Cpu,
} from 'lucide-react';

export function HistoryPage() {
  const [sessions, setSessions] = useState<AnalysisSessionSummary[]>([]);
  const [totalSessions, setTotalSessions] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  // Selected Session Detail Modal
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<AnalysisSessionDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Delete State
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Active Tab: sessions vs jobs
  const [activeTab, setActiveTab] = useState<'sessions' | 'jobs'>('sessions');

  // Background Analysis Jobs State
  const [jobs, setJobs] = useState<AnalysisJob[]>([]);
  const [totalJobs, setTotalJobs] = useState<number>(0);
  const [isLoadingJobs, setIsLoadingJobs] = useState<boolean>(false);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [cancellingJobId, setCancellingJobId] = useState<string | null>(null);
  const [jobStatusFilter, setJobStatusFilter] = useState<string>('all');

  const fetchJobs = useCallback(async () => {
    setIsLoadingJobs(true);
    setJobsError(null);
    try {
      const response = await listAnalysisJobs(100, 0, jobStatusFilter);
      setJobs(response.jobs || []);
      setTotalJobs(response.total || 0);
    } catch (err: any) {
      console.error('Failed to load analysis jobs:', err);
      setJobsError(err?.message || 'Failed to fetch analysis jobs from database.');
    } finally {
      setIsLoadingJobs(false);
    }
  }, [jobStatusFilter]);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getAnalysisSessions(1, 100);
      setSessions(response.sessions || []);
      setTotalSessions(response.total || 0);
    } catch (err: any) {
      console.error('Failed to load analysis sessions:', err);
      setError(err?.message || 'Failed to fetch analysis sessions from database.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    fetchJobs();
  }, [fetchSessions, fetchJobs]);

  const handleCancelJobInHistory = async (jobId: string) => {
    setCancellingJobId(jobId);
    try {
      await cancelAnalysisJob(jobId);
      await fetchJobs();
    } catch (err: any) {
      alert(`Failed to cancel job: ${err?.message || 'Server error'}`);
    } finally {
      setCancellingJobId(null);
    }
  };

  const handleOpenDetail = async (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setIsLoadingDetail(true);
    setDetailError(null);
    setSessionDetail(null);
    try {
      const detail = await getAnalysisSessionDetail(sessionId);
      setSessionDetail(detail);
    } catch (err: any) {
      console.error('Failed to fetch session detail:', err);
      setDetailError(err?.message || 'Failed to retrieve session detail.');
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedSessionId(null);
    setSessionDetail(null);
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!window.confirm('Are you sure you want to delete this analysis session? This will permanently remove all associated flow metrics, lane results, and crossing events from the database.')) {
      return;
    }
    setDeletingId(sessionId);
    try {
      await deleteAnalysisSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      setTotalSessions((prev) => Math.max(0, prev - 1));
      if (selectedSessionId === sessionId) {
        handleCloseDetail();
      }
    } catch (err: any) {
      alert(`Failed to delete session: ${err?.message || 'Server error'}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Filter sessions
  const filteredSessions = sessions.filter((s) => {
    const matchesSearch =
      (s.video_filename && s.video_filename.toLowerCase().includes(searchTerm.toLowerCase())) ||
      s.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.video_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || s.status.toLowerCase() === statusFilter.toLowerCase();
    const matchesType = typeFilter === 'all' || s.analysis_type.toLowerCase() === typeFilter.toLowerCase();
    return matchesSearch && matchesStatus && matchesType;
  });

  // Calculate high-level summary KPIs
  const totalVehiclesCounted = sessions.reduce((acc, s) => acc + (s.total_vehicles_counted || 0), 0);
  const completedCount = sessions.filter((s) => s.status === 'completed').length;
  const avgProcessingTime =
    sessions.length > 0
      ? (sessions.reduce((acc, s) => acc + (s.processing_time_ms || 0), 0) / sessions.length).toFixed(0)
      : '0';

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-[#0c1322] to-cyan-950/20 shadow-lg shadow-black/30">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <History className="h-6 w-6 text-cyan-400" />
              Analysis History & Database Persistence
            </h1>
            <Badge variant="info" size="sm">Phase 10</Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
            Query and inspect persisted video analysis runs from the database. Every session records full CV outputs,
            flow rates, time-series bucketing, lane density polygons, and deduplicated crossing events.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto">
          <button
            onClick={() => {
              if (activeTab === 'sessions') fetchSessions();
              else fetchJobs();
            }}
            disabled={isLoading || isLoadingJobs}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-cyan-400 ${(isLoading || isLoadingJobs) ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <Link
            to="/video-analysis"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold transition-colors shadow-sm"
          >
            <Activity className="h-3.5 w-3.5" />
            <span>Launch Analysis</span>
          </Link>
        </div>
      </div>

      {/* Tab Navigation Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('sessions')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'sessions'
              ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <History className="h-4 w-4" />
          <span>Historical Sessions ({totalSessions})</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('jobs');
            fetchJobs();
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'jobs'
              ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <Cpu className="h-4 w-4" />
          <span>Background Analysis Jobs ({totalJobs})</span>
          <Badge variant="info" size="sm">Phase 17</Badge>
        </button>
      </div>

      {activeTab === 'jobs' ? (
        /* Analysis Jobs Tab Content */
        <div className="space-y-4">
          <Card className="border-slate-800 bg-slate-900/60 p-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <Filter className="h-3.5 w-3.5 text-cyan-400" />
                <span>Filter by Status:</span>
                <select
                  value={jobStatusFilter}
                  onChange={(e) => setJobStatusFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-200 text-xs focus:outline-none"
                >
                  <option value="all">All Statuses</option>
                  <option value="queued">Queued</option>
                  <option value="running">Running</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              <span className="text-xs text-slate-400">
                Showing {jobs.length} jobs (In-process bounded worker pool)
              </span>
            </div>
          </Card>

          {jobsError && (
            <div className="p-4 rounded-xl border border-red-500/30 bg-red-950/30 text-red-300 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
                <span>{jobsError}</span>
              </div>
              <button
                onClick={fetchJobs}
                className="px-2.5 py-1 bg-red-900/40 hover:bg-red-800/60 rounded border border-red-700/50 text-red-200 text-[11px]"
              >
                Retry
              </button>
            </div>
          )}

          <Card className="border-slate-800 bg-slate-900/60 overflow-hidden">
            <CardHeader className="border-b border-slate-800 px-6 py-4 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                <Cpu className="h-4 w-4 text-cyan-400" />
                Analysis Jobs Queue & Execution History ({jobs.length})
              </CardTitle>
              <span className="text-[11px] text-slate-400 font-mono">MAX_CONCURRENT_JOBS: 2</span>
            </CardHeader>

            {isLoadingJobs ? (
              <div className="p-12 text-center space-y-3">
                <RefreshCw className="h-7 w-7 text-cyan-400 animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Loading analysis jobs...</p>
              </div>
            ) : jobs.length === 0 ? (
              <div className="p-12 text-center space-y-3">
                <Cpu className="h-8 w-8 text-slate-600 mx-auto" />
                <p className="text-sm font-medium text-slate-300">No analysis jobs found</p>
                <p className="text-xs text-slate-500">Submit a background analysis job from the Video Analysis page to see it orchestrated here.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-medium">
                    <tr>
                      <th className="px-5 py-3">Job ID</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Progress</th>
                      <th className="px-4 py-3">Frames</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Created</th>
                      <th className="px-5 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {jobs.map((job) => (
                      <tr key={job.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-5 py-3 font-mono text-cyan-400">
                          <div className="flex items-center gap-1.5">
                            <span>{job.id.slice(0, 8)}...</span>
                            <button
                              onClick={() => handleCopyId(job.id)}
                              className="text-slate-500 hover:text-white"
                              title="Copy ID"
                            >
                              {copiedId === job.id ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                            </button>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={
                              job.status === 'completed'
                                ? 'success'
                                : job.status === 'running'
                                ? 'default'
                                : job.status === 'queued'
                                ? 'warning'
                                : job.status === 'failed'
                                ? 'danger'
                                : 'outline'
                            }
                            size="sm"
                          >
                            {job.status === 'running' && <RefreshCw className="h-3 w-3 mr-1 animate-spin" />}
                            {job.status.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="w-28 space-y-1">
                            <div className="flex justify-between text-[10px] font-mono">
                              <span>
                                {job.progress !== null && job.progress !== undefined
                                  ? `${(job.progress * 100).toFixed(0)}%`
                                  : job.status === 'queued'
                                  ? 'Queued'
                                  : 'Indeterminate'}
                              </span>
                            </div>
                            <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
                              <div
                                className={`h-full ${
                                  job.status === 'completed'
                                    ? 'bg-emerald-400'
                                    : job.status === 'failed'
                                    ? 'bg-red-500'
                                    : job.status === 'cancelled'
                                    ? 'bg-slate-600'
                                    : 'bg-cyan-400 animate-pulse'
                                }`}
                                style={{
                                  width:
                                    job.progress !== null && job.progress !== undefined
                                      ? `${Math.max(5, Math.min(100, job.progress * 100))}%`
                                      : job.status === 'queued'
                                      ? '10%'
                                      : '100%',
                                }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {job.frames_processed} / {job.total_frames ?? '--'}
                        </td>
                        <td className="px-4 py-3 text-slate-300">{job.analysis_type}</td>
                        <td className="px-4 py-3 text-slate-400 text-[11px]">
                          {new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {(job.status === 'queued' || job.status === 'running') && (
                              <button
                                onClick={() => handleCancelJobInHistory(job.id)}
                                disabled={cancellingJobId === job.id}
                                className="px-2 py-1 rounded bg-red-950/60 hover:bg-red-900 border border-red-800/60 text-red-300 text-[11px] font-medium transition-colors"
                              >
                                {cancellingJobId === job.id ? 'Cancelling...' : 'Cancel'}
                              </button>
                            )}
                            {job.status === 'completed' && job.session_id && (
                              <button
                                onClick={() => handleOpenDetail(job.session_id!)}
                                className="px-2.5 py-1 rounded bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-800/60 text-cyan-300 text-[11px] font-medium transition-colors flex items-center gap-1"
                              >
                                <Eye className="h-3 w-3" />
                                <span>Results</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      ) : (
        /* Historical Sessions Tab Content */
        <>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Total Saved Sessions</p>
              <p className="text-2xl font-bold text-white mt-1">{totalSessions}</p>
            </div>
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <History className="h-5 w-5" />
            </div>
          </div>
        </Card>

        <Card className="border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Completed Runs</p>
              <p className="text-2xl font-bold text-emerald-400 mt-1">{completedCount}</p>
            </div>
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </div>
        </Card>

        <Card className="border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Total Counted Vehicles</p>
              <p className="text-2xl font-bold text-amber-400 mt-1">{totalVehiclesCounted.toLocaleString()}</p>
            </div>
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <Car className="h-5 w-5" />
            </div>
          </div>
        </Card>

        <Card className="border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Avg Execution Time</p>
              <p className="text-2xl font-bold text-cyan-300 mt-1">{avgProcessingTime} <span className="text-xs font-normal text-slate-400">ms</span></p>
            </div>
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Clock className="h-5 w-5" />
            </div>
          </div>
        </Card>
      </div>

      {/* Filter & Search Bar */}
      <Card className="border-slate-800 bg-slate-900/60 p-4">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by video filename, session ID, or video ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-xs bg-slate-950/70 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <div className="flex items-center gap-1.5 bg-slate-950/70 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300">
              <Filter className="h-3.5 w-3.5 text-slate-400" />
              <span>Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
              >
                <option value="all" className="bg-slate-900">All</option>
                <option value="completed" className="bg-slate-900">Completed</option>
                <option value="processing" className="bg-slate-900">Processing</option>
                <option value="failed" className="bg-slate-900">Failed</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 bg-slate-950/70 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300">
              <Layers className="h-3.5 w-3.5 text-slate-400" />
              <span>Type:</span>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
              >
                <option value="all" className="bg-slate-900">All Types</option>
                <option value="full_pipeline" className="bg-slate-900">Full Pipeline</option>
                <option value="analytics" className="bg-slate-900">Analytics</option>
                <option value="lane_analysis" className="bg-slate-900">Lane Analysis</option>
                <option value="counting" className="bg-slate-900">Counting</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl border border-red-500/30 bg-red-950/30 text-red-300 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchSessions}
            className="px-2.5 py-1 bg-red-900/40 hover:bg-red-800/60 rounded border border-red-700/50 text-red-200 text-[11px]"
          >
            Retry
          </button>
        </div>
      )}

      {/* Sessions Table / Empty State */}
      <Card className="border-slate-800 bg-slate-900/60 overflow-hidden">
        <CardHeader className="border-b border-slate-800 px-6 py-4 flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-cyan-400" />
            Persisted Analysis Sessions ({filteredSessions.length})
          </CardTitle>
          <span className="text-[11px] text-slate-400">Strict zero-fake-data persistence</span>
        </CardHeader>

        {isLoading ? (
          <div className="p-12 text-center space-y-3">
            <RefreshCw className="h-7 w-7 text-cyan-400 animate-spin mx-auto" />
            <p className="text-xs text-slate-400">Loading analysis history from database...</p>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="p-12 text-center space-y-4 max-w-md mx-auto">
            <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 text-slate-500 w-fit mx-auto">
              <FileVideo className="h-8 w-8 text-slate-400" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-white">No Analysis Sessions Found</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                {sessions.length === 0
                  ? "No video analyses have been executed or persisted yet. Run your first video through the CV analysis pipeline to store historical records in the database."
                  : "No sessions matched your current filter criteria."}
              </p>
            </div>
            {sessions.length === 0 && (
              <Link
                to="/video-analysis"
                className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-medium transition-colors"
              >
                <span>Go to Video Analysis</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-4 py-3">Session & Video</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Counted</th>
                  <th className="px-4 py-3 text-right">Detected</th>
                  <th className="px-4 py-3 text-right">Frames</th>
                  <th className="px-4 py-3 text-right">Processing</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredSessions.map((session) => (
                  <tr
                    key={session.id}
                    className="hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <FileVideo className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                          <span className="font-medium text-slate-200 truncate max-w-[180px]">
                            {session.video_filename || 'Video ' + session.video_id.substring(0, 8)}
                          </span>
                        </div>
                        <div className="flex items-center gap-1 text-[10px] text-slate-500 font-mono">
                          <span>{session.id.substring(0, 8)}...</span>
                          <button
                            onClick={() => handleCopyId(session.id)}
                            className="hover:text-slate-300"
                            title="Copy full UUID"
                          >
                            {copiedId === session.id ? (
                              <Check className="h-3 w-3 text-emerald-400" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </button>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950/50 text-cyan-300 border border-cyan-800/50">
                        {session.analysis_type}
                      </span>
                    </td>

                    <td className="px-4 py-3">
                      {session.status === 'completed' ? (
                        <Badge variant="success" size="sm">Completed</Badge>
                      ) : session.status === 'failed' ? (
                        <Badge variant="danger" size="sm">Failed</Badge>
                      ) : (
                        <Badge variant="warning" size="sm">Processing</Badge>
                      )}
                    </td>

                    <td className="px-4 py-3 text-right font-semibold text-amber-300">
                      {session.total_vehicles_counted}
                    </td>

                    <td className="px-4 py-3 text-right text-slate-300 font-mono">
                      {session.total_vehicles_detected}
                    </td>

                    <td className="px-4 py-3 text-right text-slate-400 font-mono">
                      {session.total_frames_processed}
                    </td>

                    <td className="px-4 py-3 text-right text-slate-400 font-mono">
                      {session.processing_time_ms ? `${session.processing_time_ms.toFixed(0)}ms` : '-'}
                    </td>

                    <td className="px-4 py-3 text-slate-400 text-[11px] whitespace-nowrap">
                      {new Date(session.started_at).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>

                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => handleOpenDetail(session.id)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-cyan-400 border border-slate-700 transition-colors"
                          title="View Full Breakdown"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteSession(session.id)}
                          disabled={deletingId === session.id}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-red-900/40 text-slate-400 hover:text-red-400 border border-slate-700 transition-colors disabled:opacity-50"
                          title="Delete Session"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      </>
      )}

      {/* Session Detail Modal */}
      {selectedSessionId && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-cyan-400" />
                <h2 className="text-sm font-semibold text-white">Analysis Session Detail</h2>
                <span className="text-xs font-mono text-slate-400">({selectedSessionId.substring(0, 8)}...)</span>
              </div>
              <button
                onClick={handleCloseDetail}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6">
              {isLoadingDetail ? (
                <div className="p-12 text-center space-y-3">
                  <RefreshCw className="h-6 w-6 text-cyan-400 animate-spin mx-auto" />
                  <p className="text-xs text-slate-400">Loading session details from database...</p>
                </div>
              ) : detailError ? (
                <div className="p-4 rounded-xl border border-red-500/30 bg-red-950/30 text-red-300 text-xs">
                  {detailError}
                </div>
              ) : sessionDetail ? (
                <>
                  {/* Session Overview Stats */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                      <p className="text-[11px] text-slate-400">Status</p>
                      <div className="mt-1">
                        <Badge variant={sessionDetail.status === 'completed' ? 'success' : 'danger'} size="sm">
                          {sessionDetail.status}
                        </Badge>
                      </div>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                      <p className="text-[11px] text-slate-400">Vehicles Counted</p>
                      <p className="text-lg font-bold text-amber-300 mt-1">{sessionDetail.total_vehicles_counted}</p>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                      <p className="text-[11px] text-slate-400">Detections / Frames</p>
                      <p className="text-sm font-mono text-slate-200 mt-1">
                        {sessionDetail.total_vehicles_detected} / {sessionDetail.total_frames_processed}
                      </p>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                      <p className="text-[11px] text-slate-400">Execution Time</p>
                      <p className="text-sm font-mono text-cyan-300 mt-1">
                        {sessionDetail.processing_time_ms ? `${sessionDetail.processing_time_ms.toFixed(1)}ms` : '-'}
                      </p>
                    </div>
                  </div>

                  {/* Traffic Metrics Section */}
                  {sessionDetail.traffic_metrics && (
                    <div className="space-y-3">
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <TrendingUp className="h-3.5 w-3.5 text-cyan-400" />
                        <span>Traffic Flow & Directional Metrics</span>
                      </h3>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-xl bg-slate-950/40 border border-slate-800">
                        <div>
                          <span className="text-[11px] text-slate-400">Total Volume:</span>
                          <p className="text-base font-bold text-white mt-0.5">{sessionDetail.traffic_metrics.total_volume} vehicles</p>
                        </div>
                        <div>
                          <span className="text-[11px] text-slate-400">Flow Rate (Vehicles/hr):</span>
                          <p className="text-base font-bold text-cyan-300 mt-0.5">
                            {sessionDetail.traffic_metrics.flow_rate_per_hour.toFixed(1)}
                            {sessionDetail.traffic_metrics.is_extrapolated && (
                              <span className="text-[10px] text-amber-400 ml-1 font-normal">(extrapolated)</span>
                            )}
                          </p>
                        </div>
                        <div>
                          <span className="text-[11px] text-slate-400">Observation Time:</span>
                          <p className="text-base font-mono text-slate-300 mt-0.5">
                            {sessionDetail.traffic_metrics.observation_duration_seconds.toFixed(1)}s
                          </p>
                        </div>
                      </div>

                      {/* Class & Direction breakdown */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800">
                          <p className="text-[11px] font-semibold text-slate-300 mb-2">Vehicle Class Distribution</p>
                          <div className="space-y-1.5">
                            {sessionDetail.traffic_metrics.class_distribution.length > 0 ? (
                              sessionDetail.traffic_metrics.class_distribution.map((c) => (
                                <div key={c.class_name} className="flex items-center justify-between text-xs">
                                  <span className="capitalize text-slate-400">{c.class_name}</span>
                                  <span className="font-mono text-slate-200">
                                    {c.count} ({c.percentage.toFixed(1)}%)
                                  </span>
                                </div>
                              ))
                            ) : (
                              <p className="text-[11px] text-slate-500">No vehicle classes recorded.</p>
                            )}
                          </div>
                        </div>

                        <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800">
                          <p className="text-[11px] font-semibold text-slate-300 mb-2">Directional Distribution</p>
                          <div className="space-y-1.5">
                            {sessionDetail.traffic_metrics.direction_distribution.length > 0 ? (
                              sessionDetail.traffic_metrics.direction_distribution.map((d) => (
                                <div key={d.direction} className="flex items-center justify-between text-xs">
                                  <span className="capitalize text-slate-400">{d.direction}</span>
                                  <span className="font-mono text-slate-200">
                                    {d.count} ({d.percentage.toFixed(1)}%)
                                  </span>
                                </div>
                              ))
                            ) : (
                              <p className="text-[11px] text-slate-500">No directional distribution recorded.</p>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Lane Results Section */}
                  {sessionDetail.lane_results && sessionDetail.lane_results.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <Layers className="h-3.5 w-3.5 text-cyan-400" />
                        <span>Lane Density & Geometry Analysis</span>
                      </h3>

                      <div className="overflow-x-auto rounded-xl border border-slate-800">
                        <table className="w-full text-left text-xs text-slate-300">
                          <thead className="bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                            <tr>
                              <th className="px-3 py-2.5">Lane ID / Name</th>
                              <th className="px-3 py-2.5 text-right">Shoelace Area (px²)</th>
                              <th className="px-3 py-2.5 text-right">Vehicles</th>
                              <th className="px-3 py-2.5 text-right">Peak Occ</th>
                              <th className="px-3 py-2.5 text-right">Density (veh/px²)</th>
                              <th className="px-3 py-2.5 text-right">Normalized Score</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60">
                            {sessionDetail.lane_results.map((lane) => (
                              <tr key={lane.id} className="hover:bg-slate-800/20">
                                <td className="px-3 py-2.5">
                                  <div>
                                    <span className="font-medium text-slate-200">{lane.lane_name}</span>
                                    <span className="text-[10px] text-slate-500 block font-mono">({lane.lane_id})</span>
                                  </div>
                                </td>
                                <td className="px-3 py-2.5 text-right font-mono text-slate-400">
                                  {lane.polygon_area_px2.toLocaleString()}
                                </td>
                                <td className="px-3 py-2.5 text-right font-semibold text-cyan-300">
                                  {lane.unique_vehicles_count}
                                </td>
                                <td className="px-3 py-2.5 text-right font-mono text-slate-300">
                                  {lane.peak_occupancy}
                                </td>
                                <td className="px-3 py-2.5 text-right font-mono text-amber-300">
                                  {lane.image_space_density.toExponential(3)}
                                </td>
                                <td className="px-3 py-2.5 text-right font-mono text-emerald-400">
                                  {lane.normalized_density_score.toFixed(3)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-800/40 text-amber-300 text-[11px] flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-400" />
                        <span>
                          Notice: Image-space density is not equivalent to vehicles/km² without camera calibration.
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Crossing Events Section */}
                  {sessionDetail.crossing_events && sessionDetail.crossing_events.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <Car className="h-3.5 w-3.5 text-cyan-400" />
                        <span>Deduplicated Line Crossing Events ({sessionDetail.crossing_events.length})</span>
                      </h3>

                      <div className="max-h-48 overflow-y-auto rounded-xl border border-slate-800">
                        <table className="w-full text-left text-xs text-slate-300">
                          <thead className="bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800 sticky top-0">
                            <tr>
                              <th className="px-3 py-2">Track ID</th>
                              <th className="px-3 py-2">Class</th>
                              <th className="px-3 py-2">Direction</th>
                              <th className="px-3 py-2 text-right">Frame</th>
                              <th className="px-3 py-2 text-right">Timestamp</th>
                              <th className="px-3 py-2 text-right">Position (X, Y)</th>
                              <th className="px-3 py-2">Line Label</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60">
                            {sessionDetail.crossing_events.map((event) => (
                              <tr key={event.id} className="hover:bg-slate-800/20 font-mono text-[11px]">
                                <td className="px-3 py-2 text-cyan-400 font-bold">#{event.track_id}</td>
                                <td className="px-3 py-2 text-slate-200 capitalize font-sans">{event.class_name}</td>
                                <td className="px-3 py-2">
                                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${event.direction === 'inbound' ? 'bg-emerald-950/50 text-emerald-300 border border-emerald-800/50' : 'bg-indigo-950/50 text-indigo-300 border border-indigo-800/50'}`}>
                                    {event.direction}
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-right text-slate-400">{event.frame_index}</td>
                                <td className="px-3 py-2 text-right text-slate-300">{event.timestamp_seconds.toFixed(2)}s</td>
                                <td className="px-3 py-2 text-right text-slate-400">
                                  ({event.centroid_x.toFixed(0)}, {event.centroid_y.toFixed(0)})
                                </td>
                                <td className="px-3 py-2 text-slate-400 font-sans">{event.line_label}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-800 flex justify-end bg-slate-950/60">
              <button
                onClick={handleCloseDetail}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
