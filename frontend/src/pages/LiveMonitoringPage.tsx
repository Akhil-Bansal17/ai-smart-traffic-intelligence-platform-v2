import { useEffect, useState, useCallback, useRef } from 'react';
import {
  Radio,
  Camera,
  Play,
  Square,
  RefreshCw,
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Layers,
  ShieldCheck,
  TrendingUp,
  Cpu,
  Wifi,
  WifiOff,
  Video,
  Eye,
  Sliders,
  X,
} from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import {
  listCameraSources,
  createCameraSource,
  deleteCameraSource,
  testCameraConnection,
  startLiveMonitoring,
  stopLiveMonitoring,
  getLiveMonitoringStatus,
  getCameraPreviewUrl,
} from '@/api/cameraSources';
import {
  CameraSource,
  CameraSourceCreatePayload,
  CameraSourceTestResponse,
  LiveMonitoringStatus,
} from '@/types/camera';

export function LiveMonitoringPage() {
  const [sources, setSources] = useState<CameraSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Live stream status & preview state
  const [liveStatus, setLiveStatus] = useState<LiveMonitoringStatus | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [previewError, setPreviewError] = useState<boolean>(false);

  // Test connection feedback
  const [testResult, setTestResult] = useState<CameraSourceTestResponse | null>(null);
  const [isTesting, setIsTesting] = useState<boolean>(false);

  // Modal for adding a camera
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [newCamera, setNewCamera] = useState<CameraSourceCreatePayload>({
    name: '',
    description: '',
    source_type: 'test_fixture',
    connection_uri: 'test_fixture',
    enabled: true,
    location_name: 'Main Intersection North',
  });

  // Polling intervals
  const statusPollRef = useRef<number | null>(null);
  const previewPollRef = useRef<number | null>(null);

  // Load camera sources list
  const loadSources = useCallback(async (preferredId?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await listCameraSources();
      setSources(res.items);
      if (res.items.length > 0) {
        const targetId = preferredId || (selectedSourceId && res.items.some(s => s.id === selectedSourceId))
          ? (preferredId || selectedSourceId)
          : res.items[0].id;
        setSelectedSourceId(targetId);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load camera sources.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedSourceId]);

  useEffect(() => {
    loadSources();
  }, []);

  // Poll live status for selected camera
  const fetchLiveStatus = useCallback(async (cameraId: string) => {
    try {
      const statusRes = await getLiveMonitoringStatus(cameraId);
      setLiveStatus(statusRes);
    } catch (err) {
      console.debug('Status poll error:', err);
    }
  }, []);

  // Set up polling when source changes or stream starts
  useEffect(() => {
    if (!selectedSourceId) return;

    fetchLiveStatus(selectedSourceId);

    // Poll live status every 1.5s
    statusPollRef.current = window.setInterval(() => {
      fetchLiveStatus(selectedSourceId);
    }, 1500);

    return () => {
      if (statusPollRef.current) clearInterval(statusPollRef.current);
    };
  }, [selectedSourceId, fetchLiveStatus]);

  // Set up preview image polling when running
  useEffect(() => {
    if (!selectedSourceId || liveStatus?.status !== 'running') {
      setPreviewUrl('');
      if (previewPollRef.current) clearInterval(previewPollRef.current);
      return;
    }

    const refreshPreview = () => {
      setPreviewUrl(getCameraPreviewUrl(selectedSourceId));
      setPreviewError(false);
    };

    refreshPreview();
    previewPollRef.current = window.setInterval(refreshPreview, 1000);

    return () => {
      if (previewPollRef.current) clearInterval(previewPollRef.current);
    };
  }, [selectedSourceId, liveStatus?.status]);

  const selectedSource = sources.find((s) => s.id === selectedSourceId);

  // Handle start live monitoring
  const handleStartMonitoring = async () => {
    if (!selectedSourceId) return;
    setIsActionLoading(true);
    setError(null);
    try {
      await startLiveMonitoring(selectedSourceId);
      await fetchLiveStatus(selectedSourceId);
    } catch (err: any) {
      setError(err?.message || 'Failed to start live monitoring.');
    } finally {
      setIsActionLoading(false);
    }
  };

  // Handle stop live monitoring
  const handleStopMonitoring = async () => {
    if (!selectedSourceId) return;
    setIsActionLoading(true);
    setError(null);
    try {
      await stopLiveMonitoring(selectedSourceId);
      await fetchLiveStatus(selectedSourceId);
    } catch (err: any) {
      setError(err?.message || 'Failed to stop live monitoring.');
    } finally {
      setIsActionLoading(false);
    }
  };

  // Handle test camera connection probe
  const handleTestConnection = async () => {
    if (!selectedSourceId) return;
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testCameraConnection(selectedSourceId);
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err?.message || 'Probe failed.',
        source_type: selectedSource?.source_type || 'unknown',
        connection_uri: selectedSource?.connection_uri || '',
        error: err?.message,
      });
    } finally {
      setIsTesting(false);
    }
  };

  // Handle create camera
  const handleCreateCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsActionLoading(true);
    setError(null);
    try {
      const created = await createCameraSource(newCamera);
      setIsAddModalOpen(false);
      setNewCamera({
        name: '',
        description: '',
        source_type: 'test_fixture',
        connection_uri: 'test_fixture',
        enabled: true,
        location_name: 'Main Intersection North',
      });
      await loadSources(created.id);
    } catch (err: any) {
      setError(err?.message || 'Failed to register camera source.');
    } finally {
      setIsActionLoading(false);
    }
  };

  // Handle delete camera
  const handleDeleteCamera = async () => {
    if (!selectedSourceId || !selectedSource) return;
    if (!confirm(`Are you sure you want to delete camera source "${selectedSource.name}"?`)) return;

    setIsActionLoading(true);
    try {
      await deleteCameraSource(selectedSourceId);
      await loadSources();
    } catch (err: any) {
      setError(err?.message || 'Failed to delete camera source.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const isStreamRunning = liveStatus?.status === 'running';

  if (isLoading && sources.length === 0) {
    return (
      <div className="py-20">
        <LoadingState message="Connecting to camera registry and synchronizing live streams..." />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-[#0a0f1d] to-cyan-950/30 shadow-xl shadow-black/40">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-cyan-600/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-sm">
              <Radio className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-100">Live Traffic Monitoring</h1>
                <Badge variant="outline" className="border-cyan-500/40 text-cyan-300 bg-cyan-950/40">
                  Phase 21
                </Badge>
                {selectedSource?.source_type === 'test_fixture' ? (
                  <Badge variant="outline" className="border-amber-500/40 text-amber-300 bg-amber-950/40 font-mono text-[10px]">
                    TEST FIXTURE
                  </Badge>
                ) : (
                  <Badge variant="outline" className="border-emerald-500/40 text-emerald-300 bg-emerald-950/40 font-mono text-[10px]">
                    LIVE STREAM
                  </Badge>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Continuous frame acquisition, vehicle tracking, line crossing counter, and lane density monitoring.
              </p>
            </div>
          </div>
        </div>

        {/* Global Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAddModalOpen(true)}
            className="border-slate-700 bg-slate-800/60 hover:bg-slate-700 text-xs"
          >
            <Plus className="h-3.5 w-3.5 mr-1.5 text-cyan-400" />
            Add Camera
          </Button>

          <Button
            variant="outline"
            size="sm"
            disabled={!selectedSourceId || isTesting || isStreamRunning}
            onClick={handleTestConnection}
            className="border-slate-700 bg-slate-800/60 hover:bg-slate-700 text-xs"
          >
            <Wifi className={`h-3.5 w-3.5 mr-1.5 ${isTesting ? 'animate-spin text-cyan-400' : 'text-slate-300'}`} />
            {isTesting ? 'Probing...' : 'Probe Source'}
          </Button>

          {isStreamRunning ? (
            <Button
              variant="outline"
              size="sm"
              disabled={isActionLoading}
              onClick={handleStopMonitoring}
              className="border-rose-800/80 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs font-semibold"
            >
              <Square className="h-3.5 w-3.5 mr-1.5 fill-rose-400 text-rose-400" />
              Stop Monitoring
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              disabled={!selectedSourceId || isActionLoading || !selectedSource?.enabled}
              onClick={handleStartMonitoring}
              className="border-emerald-700/80 bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 text-xs font-semibold"
            >
              <Play className="h-3.5 w-3.5 mr-1.5 fill-emerald-400 text-emerald-400" />
              Start Monitoring
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => loadSources()}
            className="text-slate-400 hover:text-slate-200"
            title="Refresh sources"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {error && (
        <ErrorState
          title="Live Stream Error"
          message={error}
          onRetry={() => {
            setError(null);
            loadSources();
          }}
        />
      )}

      {/* Connection Probe Feedback Banner */}
      {testResult && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 transition-all ${
            testResult.success
              ? 'bg-emerald-950/20 border-emerald-800/50 text-emerald-200'
              : 'bg-rose-950/20 border-rose-800/50 text-rose-200'
          }`}
        >
          {testResult.success ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          )}
          <div className="flex-1 text-xs">
            <div className="font-semibold text-sm">
              {testResult.success ? 'Camera Probe Successful' : 'Connection Failed'}
            </div>
            <p className="mt-0.5 text-slate-300">{testResult.message}</p>
            {testResult.width && testResult.height && (
              <div className="mt-2 flex gap-4 font-mono text-[11px] text-slate-400">
                <span>Resolution: {testResult.width}x{testResult.height}</span>
                <span>FPS: {testResult.fps}</span>
                <span>Type: {testResult.source_type}</span>
              </div>
            )}
            {testResult.error && (
              <p className="mt-1 font-mono text-rose-300 text-[11px]">{testResult.error}</p>
            )}
          </div>
          <button
            onClick={() => setTestResult(null)}
            className="text-slate-400 hover:text-slate-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Camera Selection & Status Ribbon */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-4 rounded-xl border border-slate-800 bg-[#0c1322]">
        <div className="flex flex-1 items-center gap-3">
          <Camera className="h-5 w-5 text-cyan-400 shrink-0" />
          <div className="flex-1 max-w-xs">
            <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
              Active Camera Feed
            </label>
            <select
              value={selectedSourceId}
              onChange={(e) => setSelectedSourceId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-medium"
            >
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.source_type})
                </option>
              ))}
            </select>
          </div>

          {selectedSource && (
            <div className="hidden md:flex flex-col text-[11px] text-slate-400 pl-4 border-l border-slate-800">
              <span className="font-mono text-slate-300 truncate max-w-sm">
                URI: {selectedSource.connection_uri}
              </span>
              <span className="text-[10px] text-slate-400">
                Location: {selectedSource.location_name || 'Unspecified'} | Status: {selectedSource.status}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 justify-end">
          {selectedSource && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDeleteCamera}
              className="text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 text-xs"
              title="Delete this camera source"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Real-Time Operational KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="bg-[#0b101d] border-slate-800/80 p-3.5 flex flex-col justify-between">
          <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
            <span>Processing FPS</span>
            <Activity className="h-3.5 w-3.5 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono text-slate-100">
              {liveStatus?.processing_fps?.toFixed(1) || '0.0'}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              / {liveStatus?.source_fps ? liveStatus.source_fps.toFixed(0) : '30'} FPS
            </span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400">
            Target: 5.0 FPS sampling
          </div>
        </Card>

        <Card className="bg-[#0b101d] border-slate-800/80 p-3.5 flex flex-col justify-between">
          <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
            <span>Total Volume</span>
            <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
          </div>
          <div className="mt-2">
            <span className="text-xl font-bold font-mono text-emerald-400">
              {liveStatus?.total_volume || 0}
            </span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400 font-mono">
            In: {liveStatus?.inbound_volume || 0} | Out: {liveStatus?.outbound_volume || 0}
          </div>
        </Card>

        <Card className="bg-[#0b101d] border-slate-800/80 p-3.5 flex flex-col justify-between">
          <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
            <span>Active Tracks</span>
            <Eye className="h-3.5 w-3.5 text-cyan-400" />
          </div>
          <div className="mt-2">
            <span className="text-xl font-bold font-mono text-cyan-300">
              {liveStatus?.active_tracks_count || 0}
            </span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400 truncate">
            Kalman state tracks
          </div>
        </Card>

        <Card className="bg-[#0b101d] border-slate-800/80 p-3.5 flex flex-col justify-between">
          <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
            <span>Frames Handled</span>
            <Cpu className="h-3.5 w-3.5 text-indigo-400" />
          </div>
          <div className="mt-2">
            <span className="text-xl font-bold font-mono text-slate-100">
              {liveStatus?.frames_processed || 0}
            </span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400 font-mono">
            Acquired: {liveStatus?.frames_acquired || 0}
          </div>
        </Card>

        <Card className="bg-[#0b101d] border-slate-800/80 p-3.5 flex flex-col justify-between">
          <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
            <span>Frame Dropped</span>
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
          </div>
          <div className="mt-2">
            <span className="text-xl font-bold font-mono text-amber-400">
              {liveStatus?.dropped_frames || 0}
            </span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400">
            Backpressure queue drop
          </div>
        </Card>

        <Card className="bg-[#0b101d] border-slate-800/80 p-3.5 flex flex-col justify-between">
          <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
            <span>Reconnects</span>
            <Wifi className="h-3.5 w-3.5 text-slate-400" />
          </div>
          <div className="mt-2">
            <span className="text-xl font-bold font-mono text-slate-200">
              {liveStatus?.reconnect_count || 0}
            </span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400 truncate">
            Bounded recovery
          </div>
        </Card>
      </div>

      {/* Main Two-Column View: Live Preview + Real-time Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Live Annotated Frame Preview */}
        <div className="lg:col-span-8 space-y-4">
          <Card className="bg-[#0b101d] border-slate-800 overflow-hidden">
            <CardHeader className="py-3 px-4 border-b border-slate-800 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <Video className="h-4 w-4 text-cyan-400" />
                <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Live Annotated Video Feed
                </CardTitle>
              </div>

              <div className="flex items-center gap-2">
                {isStreamRunning ? (
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-950/70 border border-emerald-600/50 text-emerald-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                    LIVE PIPELINE
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
                    MONITORING OFFLINE
                  </span>
                )}
              </div>
            </CardHeader>

            <div className="relative aspect-video bg-[#050811] flex items-center justify-center overflow-hidden">
              {isStreamRunning && previewUrl && !previewError ? (
                <img
                  src={previewUrl}
                  alt="Live Traffic Feed"
                  className="w-full h-full object-contain"
                  onError={() => setPreviewError(true)}
                />
              ) : (
                <div className="flex flex-col items-center justify-center p-8 text-center text-slate-500 space-y-3">
                  <div className="h-14 w-14 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-center justify-center text-slate-600 shadow-inner">
                    <WifiOff className="h-7 w-7 text-slate-600" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-300">
                      {isStreamRunning ? 'Waiting for first processed frame...' : 'Live Monitoring is Inactive'}
                    </h3>
                    <p className="text-xs text-slate-500 max-w-sm mt-1">
                      {isStreamRunning
                        ? 'Acquiring video stream and extracting initial frames.'
                        : 'Click "Start Monitoring" above to start the computer vision pipeline on this camera source.'}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Preview Footer / Provenance info */}
            <div className="py-2.5 px-4 bg-slate-950/60 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-[11px] text-slate-400">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
                <span>
                  Source: <strong className="text-slate-200">{selectedSource?.name}</strong>
                </span>
                <span className="text-slate-600">|</span>
                <span>
                  Type: <strong className="text-slate-200">{selectedSource?.source_type}</strong>
                </span>
              </div>
              <div>
                <span>Last Updated: {liveStatus?.last_updated ? new Date(liveStatus.last_updated).toLocaleTimeString() : 'N/A'}</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Right Column: Real-time Vehicle Composition & Lane Analytics */}
        <div className="lg:col-span-4 space-y-4">
          {/* Vehicle Class Breakdown */}
          <Card className="bg-[#0b101d] border-slate-800">
            <CardHeader className="py-3 px-4 border-b border-slate-800">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center justify-between">
                <span>Vehicle Class Split</span>
                <Layers className="h-3.5 w-3.5 text-cyan-400" />
              </CardTitle>
            </CardHeader>
            <div className="p-4 space-y-3">
              {liveStatus?.class_distribution && Object.keys(liveStatus.class_distribution).length > 0 ? (
                Object.entries(liveStatus.class_distribution).map(([cls, count]) => {
                  const total = liveStatus.total_volume || 1;
                  const pct = Math.round((count / total) * 100);
                  return (
                    <div key={cls} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium">
                        <span className="capitalize text-slate-300">{cls}</span>
                        <span className="font-mono text-cyan-300">
                          {count} ({pct}%)
                        </span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-full"
                          style={{ width: `${Math.min(100, Math.max(5, pct))}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-6 text-xs text-slate-500">
                  No vehicle crossings recorded yet in this session.
                </div>
              )}
            </div>
          </Card>

          {/* Lane Occupancy & Density */}
          <Card className="bg-[#0b101d] border-slate-800">
            <CardHeader className="py-3 px-4 border-b border-slate-800">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center justify-between">
                <span>Lane Occupancy</span>
                <Sliders className="h-3.5 w-3.5 text-indigo-400" />
              </CardTitle>
            </CardHeader>
            <div className="p-4 space-y-3">
              {liveStatus?.lane_occupancies && Object.keys(liveStatus.lane_occupancies).length > 0 ? (
                Object.entries(liveStatus.lane_occupancies).map(([laneId, count]) => {
                  const dens = liveStatus.lane_densities?.[laneId] || 0.0;
                  return (
                    <div key={laneId} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-slate-300 truncate max-w-[120px]">{laneId}</span>
                        <span className="font-mono text-indigo-300">{count} vehicles</span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        Density: {dens.toFixed(6)} veh/px²
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-6 text-xs text-slate-500">
                  No lane geometry configured for this camera stream.
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Modal: Register New Camera Source */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0c1322] border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Camera className="h-5 w-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-slate-100">Register Camera Source</h3>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCamera} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Camera Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. North Approach Camera"
                  value={newCamera.name}
                  onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Source Type *</label>
                <select
                  value={newCamera.source_type}
                  onChange={(e) => setNewCamera({ ...newCamera, source_type: e.target.value as any })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                >
                  <option value="test_fixture">Deterministic Test Fixture (Simulated)</option>
                  <option value="local_camera">Local Camera Device (OpenCV index)</option>
                  <option value="rtsp">RTSP Network Stream</option>
                  <option value="http_stream">HTTP / MJPEG Video Stream</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Connection URI / Device Index *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. rtsp://user:pass@192.168.1.100/stream or 0 for local"
                  value={newCamera.connection_uri}
                  onChange={(e) => setNewCamera({ ...newCamera, connection_uri: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500 font-mono text-[11px]"
                />
                <p className="text-[10px] text-slate-400 mt-1">
                  Passwords in URIs are automatically redacted in responses and logs.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Location Metadata</label>
                <input
                  type="text"
                  placeholder="e.g. Main St & 4th Ave Intersection"
                  value={newCamera.location_name || ''}
                  onChange={(e) => setNewCamera({ ...newCamera, location_name: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsAddModalOpen(false)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isActionLoading}
                  className="bg-cyan-600 hover:bg-cyan-500 text-white font-medium"
                >
                  {isActionLoading ? 'Saving...' : 'Register Camera'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
