import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { uploadVideo, listVideos } from '@/api/videos';
import { detectVideo } from '@/api/detection';
import { trackVideo } from '@/api/tracking';
import { countVideo } from '@/api/counting';
import { createAnalysisJob, getAnalysisJob, cancelAnalysisJob } from '@/api/analysis';
import { VideoMetadata } from '@/types/video';
import { VideoDetectionResponse } from '@/types/detection';
import { VideoTrackingResponse } from '@/types/tracking';
import { VideoCountingResponse } from '@/types/counting';
import { AnalysisJob } from '@/types/analysis';
import { ApiError } from '@/types/api';
import { Link } from 'react-router-dom';
import {
  Upload,
  FileVideo,
  CheckCircle2,
  Clock,
  HardDrive,
  RefreshCw,
  Crosshair,
  Car,
  Truck,
  Bus,
  Sliders,
  Eye,
  Info,
  Route,
  Activity,
  Calculator,
  ArrowRightLeft,
  Hash,
  ArrowDownRight,
  ArrowUpRight,
  Play,
  StopCircle,
  AlertCircle,
  ExternalLink,
  Sparkles,
  Copy,
  Check,
} from 'lucide-react';

type AnalysisMode = 'counting' | 'tracking' | 'detection';

export function VideoAnalysisPage() {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<ApiError | null>(null);
  const [currentVideo, setCurrentVideo] = useState<VideoMetadata | null>(null);
  const [recentVideos, setRecentVideos] = useState<VideoMetadata[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Active Mode: Counting (Phase 7) | Tracking (Phase 6) | Detection (Phase 5)
  const [activeMode, setActiveMode] = useState<AnalysisMode>('counting');

  // Detection states (Phase 5)
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionError, setDetectionError] = useState<ApiError | null>(null);
  const [detectionResult, setDetectionResult] = useState<VideoDetectionResponse | null>(null);

  // Tracking states (Phase 6)
  const [isTracking, setIsTracking] = useState(false);
  const [trackingError, setTrackingError] = useState<ApiError | null>(null);
  const [trackingResult, setTrackingResult] = useState<VideoTrackingResponse | null>(null);

  // Counting states (Phase 7)
  const [isCounting, setIsCounting] = useState(false);
  const [countingError, setCountingError] = useState<ApiError | null>(null);
  const [countingResult, setCountingResult] = useState<VideoCountingResponse | null>(null);

  // Parameters
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.35);
  const [maxFrames, setMaxFrames] = useState<number>(50);
  const [iouThreshold, setIouThreshold] = useState<number>(0.30);
  const [linePositionRatio, setLinePositionRatio] = useState<number>(0.50);

  // Phase 17: Background Analysis Job Orchestration state
  const [activeJob, setActiveJob] = useState<AnalysisJob | null>(null);
  const [isCreatingJob, setIsCreatingJob] = useState<boolean>(false);
  const [jobError, setJobError] = useState<string | null>(null);
  const [isCancellingJob, setIsCancellingJob] = useState<boolean>(false);
  const [jobAnalysisType, setJobAnalysisType] = useState<string>('full_pipeline');
  const [copiedJobId, setCopiedJobId] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Polling for active background job (1.5s interval with unmount cleanup)
  useEffect(() => {
    if (!activeJob || (activeJob.status !== 'queued' && activeJob.status !== 'running')) {
      return;
    }

    const intervalId = setInterval(async () => {
      try {
        const latest = await getAnalysisJob(activeJob.id);
        setActiveJob(latest);
      } catch (err) {
        console.warn('Background job polling error:', err);
      }
    }, 1500);

    return () => clearInterval(intervalId);
  }, [activeJob?.id, activeJob?.status]);

  const handleLaunchJob = async (videoId: string) => {
    if (!videoId) return;
    setIsCreatingJob(true);
    setJobError(null);
    try {
      const job = await createAnalysisJob({
        video_id: videoId,
        analysis_type: jobAnalysisType,
        confidence_threshold: confidenceThreshold,
        max_frames: maxFrames,
        iou_threshold: iouThreshold,
        counting_line: {
          p1: { x: 0.0, y: linePositionRatio },
          p2: { x: 1.0, y: linePositionRatio },
          label: 'main_tripwire',
          direction_a_to_b: 'inbound',
          direction_b_to_a: 'outbound',
          min_movement_px: 2.0,
        },
      });
      setActiveJob(job);
    } catch (err: any) {
      setJobError(err?.message || 'Failed to submit analysis job');
    } finally {
      setIsCreatingJob(false);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    if (!jobId) return;
    setIsCancellingJob(true);
    try {
      const res = await cancelAnalysisJob(jobId);
      setActiveJob(res.job);
    } catch (err: any) {
      setJobError(err?.message || 'Failed to cancel analysis job');
    } finally {
      setIsCancellingJob(false);
    }
  };

  const handleCopyJobId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedJobId(true);
    setTimeout(() => setCopiedJobId(false), 2000);
  };

  const fetchRecentVideos = async () => {
    setIsLoadingList(true);
    try {
      const response = await listVideos();
      setRecentVideos(response.videos);
      if (response.videos.length > 0 && !currentVideo) {
        setCurrentVideo(response.videos[0]);
      }
    } catch {
      // Non-critical background list failure
    } finally {
      setIsLoadingList(false);
    }
  };

  useEffect(() => {
    fetchRecentVideos();
  }, []);

  const handleFile = async (file: File) => {
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    setDetectionResult(null);
    setDetectionError(null);
    setTrackingResult(null);
    setTrackingError(null);
    setCountingResult(null);
    setCountingError(null);

    try {
      const result = await uploadVideo(file);
      setCurrentVideo(result);
      fetchRecentVideos();
    } catch (err) {
      if (err instanceof ApiError) {
        setUploadError(err);
      } else {
        setUploadError(new ApiError('Failed to upload video', 500));
      }
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleRunCounting = async (videoId: string) => {
    if (!videoId) return;

    setIsCounting(true);
    setCountingError(null);

    try {
      const result = await countVideo(videoId, {
        confidence_threshold: confidenceThreshold,
        max_frames: maxFrames,
        iou_threshold: iouThreshold,
        counting_line: {
          p1: { x: 0.0, y: linePositionRatio },
          p2: { x: 1.0, y: linePositionRatio },
          label: 'main_tripwire',
          direction_a_to_b: 'inbound',
          direction_b_to_a: 'outbound',
          min_movement_px: 2.0,
        },
      });
      setCountingResult(result);
      setActiveMode('counting');
    } catch (err) {
      if (err instanceof ApiError) {
        setCountingError(err);
      } else {
        setCountingError(new ApiError('Vehicle counting inference failed', 500));
      }
    } finally {
      setIsCounting(false);
    }
  };

  const handleRunTracking = async (videoId: string) => {
    if (!videoId) return;

    setIsTracking(true);
    setTrackingError(null);

    try {
      const result = await trackVideo(videoId, {
        confidence_threshold: confidenceThreshold,
        max_frames: maxFrames,
        iou_threshold: iouThreshold,
      });
      setTrackingResult(result);
      setActiveMode('tracking');
    } catch (err) {
      if (err instanceof ApiError) {
        setTrackingError(err);
      } else {
        setTrackingError(new ApiError('Object tracking inference failed', 500));
      }
    } finally {
      setIsTracking(false);
    }
  };

  const handleRunDetection = async (videoId: string) => {
    if (!videoId) return;

    setIsDetecting(true);
    setDetectionError(null);

    try {
      const result = await detectVideo(videoId, {
        confidence_threshold: confidenceThreshold,
        max_frames: maxFrames,
      });
      setDetectionResult(result);
      setActiveMode('detection');
    } catch (err) {
      if (err instanceof ApiError) {
        setDetectionError(err);
      } else {
        setDetectionError(new ApiError('Detection inference failed', 500));
      }
    } finally {
      setIsDetecting(false);
    }
  };

  const isPipelineBusy = isUploading || isDetecting || isTracking || isCounting;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border border-cyan-900/40 bg-gradient-to-r from-slate-900/90 via-slate-900/80 to-cyan-950/20 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <div className="p-3.5 rounded-xl bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
            <Calculator className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold tracking-tight text-white">Traffic Analysis & Vehicle Counting</h1>
              <Badge variant="success" size="sm">
                <CheckCircle2 className="h-3 w-3 mr-1" />
                Phase 7: Track-Based Vehicle Counting Active
              </Badge>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Transforms persistent <span className="font-mono text-cyan-300">ByteTrack</span> trajectories into deduplicated vehicle counts across virtual tripwires.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Badge variant="info" size="md">
            <Activity className="h-3 w-3 mr-1" />
            CV Pipeline Stage 3
          </Badge>
        </div>
      </div>

      {/* Upload & Ingestion Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Upload className="h-4 w-4 text-cyan-400" />
              <span>Traffic Camera Video Ingestion</span>
            </span>
            <span className="text-xs font-normal text-slate-400">
              Supported: <span className="font-mono text-slate-200">.mp4, .avi, .mov</span> (Max 500 MB)
            </span>
          </CardTitle>
          <CardDescription>
            Upload traffic camera footage for frame sampling, YOLO vehicle detection, multi-object tracking, and virtual-line crossing counting.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp4,.avi,.mov,video/mp4,video/x-msvideo,video/quicktime"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                handleFile(e.target.files[0]);
              }
            }}
          />

          {/* Dropzone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
              isDragging
                ? 'border-cyan-400 bg-cyan-950/30'
                : 'border-slate-800 hover:border-slate-700 bg-slate-950/40 hover:bg-slate-900/50'
            }`}
          >
            {isUploading ? (
              <LoadingState
                message="Validating container, uploading securely, and extracting metadata..."
                size="md"
              />
            ) : (
              <div className="text-center space-y-2">
                <div className="p-3 mx-auto w-fit rounded-full bg-slate-800/80 text-cyan-400 border border-slate-700/60 shadow-sm">
                  <Upload className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-slate-200">
                    Click to select or drag and drop a traffic video
                  </p>
                  <p className="text-xs text-slate-500">
                    MP4, AVI, or MOV up to 500 MB • Validated on upload
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-2 text-xs"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                >
                  Browse Local Files
                </Button>
              </div>
            )}
          </div>

          {/* Error display */}
          {uploadError && (
            <ErrorState
              title="Upload Validation Failed"
              message={uploadError.message}
              code={uploadError.code}
              onRetry={() => fileInputRef.current?.click()}
            />
          )}

          {/* Video Selected Card & Pipeline Actions */}
          {currentVideo && (
            <div className="p-5 rounded-xl border border-cyan-900/50 bg-slate-900/60 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
                    <FileVideo className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-white truncate max-w-md">
                      {currentVideo.original_filename}
                    </h4>
                    <p className="text-[11px] font-mono text-cyan-400">
                      ID: {currentVideo.id}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant="success" size="sm">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Ingested
                  </Badge>
                </div>
              </div>

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Resolution</span>
                  <span className="text-slate-200 font-semibold">{currentVideo.resolution}</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Frame Rate</span>
                  <span className="text-slate-200 font-semibold">{currentVideo.fps} FPS</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Duration</span>
                  <span className="text-slate-200 font-semibold">{currentVideo.duration_seconds}s</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Total Frames</span>
                  <span className="text-slate-200 font-semibold">{currentVideo.frame_count}</span>
                </div>
              </div>

              {/* Pipeline Tuning & Action Controls */}
              <div className="p-4 rounded-xl bg-slate-950/90 border border-cyan-900/40 space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-white">
                    <Sliders className="h-4 w-4 text-cyan-400" />
                    <span>Inference & Virtual Tripwire Controls</span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    Pipeline: <span className="text-cyan-300">YOLOv8n &rarr; ByteTrack &rarr; LineCrossingCounter</span>
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
                  <div>
                    <label className="text-slate-300 block mb-1 font-medium">
                      Confidence Threshold: <span className="font-mono text-cyan-400">{confidenceThreshold}</span>
                    </label>
                    <input
                      type="range"
                      min="0.10"
                      max="0.80"
                      step="0.05"
                      value={confidenceThreshold}
                      onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                    />
                  </div>
                  <div>
                    <label className="text-slate-300 block mb-1 font-medium">
                      Max Sampled Frames: <span className="font-mono text-cyan-400">{maxFrames}</span>
                    </label>
                    <input
                      type="range"
                      min="10"
                      max="150"
                      step="10"
                      value={maxFrames}
                      onChange={(e) => setMaxFrames(parseInt(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                    />
                  </div>
                  <div>
                    <label className="text-slate-300 block mb-1 font-medium">
                      IoU Matching: <span className="font-mono text-cyan-400">{iouThreshold}</span>
                    </label>
                    <input
                      type="range"
                      min="0.15"
                      max="0.70"
                      step="0.05"
                      value={iouThreshold}
                      onChange={(e) => setIouThreshold(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                    />
                  </div>
                  <div>
                    <label className="text-slate-300 block mb-1 font-medium">
                      Tripwire Y-Level: <span className="font-mono text-cyan-400">{(linePositionRatio * 100).toFixed(0)}%</span>
                    </label>
                    <input
                      type="range"
                      min="0.20"
                      max="0.80"
                      step="0.05"
                      value={linePositionRatio}
                      onChange={(e) => setLinePositionRatio(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                    />
                  </div>
                </div>

                {/* Pipeline Execution Buttons */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-800">
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <Info className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                    <span>Deduplicated counting: tracks crossing the virtual line are counted exactly once with direction.</span>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={isPipelineBusy}
                      onClick={() => handleRunDetection(currentVideo.id)}
                      className="text-xs"
                    >
                      {isDetecting ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                          Detecting...
                        </>
                      ) : (
                        <>
                          <Crosshair className="h-3.5 w-3.5 mr-1.5 text-cyan-400" />
                          Detection (Phase 5)
                        </>
                      )}
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={isPipelineBusy}
                      onClick={() => handleRunTracking(currentVideo.id)}
                      className="text-xs"
                    >
                      {isTracking ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                          Tracking...
                        </>
                      ) : (
                        <>
                          <Route className="h-3.5 w-3.5 mr-1.5 text-cyan-400" />
                          Tracking (Phase 6)
                        </>
                      )}
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={isPipelineBusy}
                      onClick={() => handleRunCounting(currentVideo.id)}
                      className="text-xs"
                    >
                      {isCounting ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                          Counting...
                        </>
                      ) : (
                        <>
                          <Calculator className="h-3.5 w-3.5 mr-1.5 text-cyan-400" />
                          Direct Counting
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Phase 17: Background Analysis Job Launcher */}
                <div className="pt-3 border-t border-cyan-900/50 bg-cyan-950/20 -mx-4 -mb-4 p-4 rounded-b-xl space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-cyan-400" />
                      <div>
                        <span className="text-xs font-semibold text-white">Background Analysis Job (Phase 17)</span>
                        <p className="text-[11px] text-slate-400">Non-blocking background worker with live progress, concurrency control & cancellation</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <select
                        value={jobAnalysisType}
                        onChange={(e) => setJobAnalysisType(e.target.value)}
                        className="bg-slate-900 border border-slate-700 text-xs rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                        disabled={Boolean(isCreatingJob || activeJob?.status === 'queued' || activeJob?.status === 'running')}
                      >
                        <option value="full_pipeline">Full Pipeline (All Stages)</option>
                        <option value="counting">Counting Tripwire</option>
                        <option value="lane_analysis">Lane Density</option>
                        <option value="analytics">Flow Analytics</option>
                      </select>

                      <Button
                        type="button"
                        variant="primary"
                        size="sm"
                        disabled={Boolean(isCreatingJob || activeJob?.status === 'queued' || activeJob?.status === 'running')}
                        onClick={() => handleLaunchJob(currentVideo.id)}
                        className="text-xs shadow-md shadow-cyan-950"
                      >
                        {isCreatingJob ? (
                          <>
                            <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                            Queuing Job...
                          </>
                        ) : (
                          <>
                            <Play className="h-3.5 w-3.5 mr-1.5 fill-current" />
                            Launch Background Job
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                  {jobError && (
                    <div className="p-3 rounded-lg bg-red-950/50 border border-red-900/60 text-xs text-red-200 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
                      <span>{jobError}</span>
                    </div>
                  )}

                  {/* Active Job Real-Time Card */}
                  {activeJob && (
                    <div className="p-4 rounded-xl border border-cyan-800/60 bg-slate-900/90 shadow-lg space-y-3">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-200">Active Job:</span>
                          <span className="font-mono text-xs text-cyan-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                            {activeJob.id.slice(0, 13)}...
                          </span>
                          <button
                            onClick={() => handleCopyJobId(activeJob.id)}
                            className="text-slate-400 hover:text-white transition-colors"
                            title="Copy full Job ID"
                          >
                            {copiedJobId ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                          </button>
                        </div>

                        <div className="flex items-center gap-2">
                          <Badge
                            variant={
                              activeJob.status === 'completed'
                                ? 'success'
                                : activeJob.status === 'running'
                                ? 'default'
                                : activeJob.status === 'queued'
                                ? 'warning'
                                : activeJob.status === 'failed'
                                ? 'danger'
                                : 'outline'
                            }
                            size="sm"
                          >
                            {activeJob.status === 'running' && <RefreshCw className="h-3 w-3 mr-1 animate-spin" />}
                            {activeJob.status === 'queued' && <Clock className="h-3 w-3 mr-1" />}
                            {activeJob.status === 'completed' && <CheckCircle2 className="h-3 w-3 mr-1" />}
                            {activeJob.status === 'failed' && <AlertCircle className="h-3 w-3 mr-1" />}
                            {activeJob.status === 'cancelled' && <StopCircle className="h-3 w-3 mr-1" />}
                            {activeJob.status.toUpperCase()}
                          </Badge>

                          {(activeJob.status === 'queued' || activeJob.status === 'running') && (
                            <Button
                              type="button"
                              variant="danger"
                              size="sm"
                              disabled={isCancellingJob}
                              onClick={() => handleCancelJob(activeJob.id)}
                              className="text-[11px] py-1 px-2.5 h-7"
                            >
                              {isCancellingJob ? (
                                <>
                                  <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                                  Cancelling...
                                </>
                              ) : (
                                <>
                                  <StopCircle className="h-3 w-3 mr-1" />
                                  Cancel Job
                                </>
                              )}
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-400">
                            {activeJob.status === 'running' && 'Processing frames outside HTTP request...'}
                            {activeJob.status === 'queued' && 'Queued in worker pool, waiting for slot...'}
                            {activeJob.status === 'completed' && 'Processing complete & persisted'}
                            {activeJob.status === 'failed' && 'Job failed with error'}
                            {activeJob.status === 'cancelled' && 'Job cancelled'}
                          </span>
                          <span className="font-mono text-cyan-400 font-semibold">
                            {activeJob.progress !== null && activeJob.progress !== undefined
                              ? `${(activeJob.progress * 100).toFixed(1)}%`
                              : 'Indeterminate'}
                          </span>
                        </div>

                        <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-800">
                          <div
                            className={`h-full transition-all duration-300 ${
                              activeJob.status === 'completed'
                                ? 'bg-gradient-to-r from-emerald-500 to-emerald-400'
                                : activeJob.status === 'failed'
                                ? 'bg-red-500'
                                : activeJob.status === 'cancelled'
                                ? 'bg-slate-600'
                                : 'bg-gradient-to-r from-cyan-500 to-blue-500 animate-pulse'
                            }`}
                            style={{
                              width:
                                activeJob.progress !== null && activeJob.progress !== undefined
                                  ? `${Math.max(5, Math.min(100, activeJob.progress * 100))}%`
                                  : activeJob.status === 'queued'
                                  ? '10%'
                                  : '100%',
                            }}
                          />
                        </div>
                      </div>

                      {/* Stats grid */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                        <div className="p-2 rounded bg-slate-950/70 border border-slate-800/80">
                          <span className="text-slate-500 block text-[10px]">FRAMES</span>
                          <span className="text-slate-200">
                            {activeJob.frames_processed} / {activeJob.total_frames ?? 'estimating'}
                          </span>
                        </div>
                        <div className="p-2 rounded bg-slate-950/70 border border-slate-800/80">
                          <span className="text-slate-500 block text-[10px]">SPEED</span>
                          <span className="text-slate-200">
                            {activeJob.processing_fps ? `${activeJob.processing_fps} FPS` : '--'}
                          </span>
                        </div>
                        <div className="p-2 rounded bg-slate-950/70 border border-slate-800/80">
                          <span className="text-slate-500 block text-[10px]">TYPE</span>
                          <span className="text-cyan-400">{activeJob.analysis_type}</span>
                        </div>
                        <div className="p-2 rounded bg-slate-950/70 border border-slate-800/80">
                          <span className="text-slate-500 block text-[10px]">PROVENANCE</span>
                          <span className="text-slate-200">{activeJob.provenance_category}</span>
                        </div>
                      </div>

                      {activeJob.error_message && (
                        <p className="text-xs text-red-300 font-mono bg-red-950/30 p-2 rounded border border-red-900/50">
                          Error: {activeJob.error_message}
                        </p>
                      )}

                      {activeJob.status === 'completed' && activeJob.session_id && (
                        <div className="pt-2 flex justify-end">
                          <Link
                            to={`/history`}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/60 border border-emerald-700/60 text-emerald-300 hover:text-emerald-200 hover:bg-emerald-900/50 text-xs font-medium transition-colors"
                          >
                            <span>View Result Analytics in History</span>
                            <ExternalLink className="h-3.5 w-3.5" />
                          </Link>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Error States */}
          {countingError && (
            <ErrorState
              title="Counting Inference Failed"
              message={countingError.message}
              code={countingError.code}
              onRetry={() => currentVideo && handleRunCounting(currentVideo.id)}
            />
          )}

          {trackingError && (
            <ErrorState
              title="Tracking Inference Failed"
              message={trackingError.message}
              code={trackingError.code}
              onRetry={() => currentVideo && handleRunTracking(currentVideo.id)}
            />
          )}

          {detectionError && (
            <ErrorState
              title="Detection Inference Failed"
              message={detectionError.message}
              code={detectionError.code}
              onRetry={() => currentVideo && handleRunDetection(currentVideo.id)}
            />
          )}

          {/* Loading States */}
          {isPipelineBusy && !isUploading && (
            <div className="p-8 rounded-xl bg-slate-900/80 border border-cyan-800/50">
              <LoadingState
                message={
                  isCounting
                    ? 'Decoding frames, evaluating YOLO detections, updating ByteTrack Kalman filter, and computing line crossings...'
                    : isTracking
                    ? 'Decoding frames, running YOLO detection, and associating bounding boxes with ByteTrack Kalman filter...'
                    : 'Decoding frames with VideoSource and computing YOLO vehicle detections...'
                }
                size="lg"
              />
            </div>
          )}

          {/* Mode Tabs if results exist */}
          {(countingResult || trackingResult || detectionResult) && !isPipelineBusy && (
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
              {countingResult && (
                <button
                  type="button"
                  onClick={() => setActiveMode('counting')}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    activeMode === 'counting'
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Calculator className="h-3.5 w-3.5" />
                  Vehicle Counting Results (Phase 7)
                </button>
              )}
              {trackingResult && (
                <button
                  type="button"
                  onClick={() => setActiveMode('tracking')}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    activeMode === 'tracking'
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Route className="h-3.5 w-3.5" />
                  Object Tracking (Phase 6)
                </button>
              )}
              {detectionResult && (
                <button
                  type="button"
                  onClick={() => setActiveMode('detection')}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    activeMode === 'detection'
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Crosshair className="h-3.5 w-3.5" />
                  Raw Detections (Phase 5)
                </button>
              )}
            </div>
          )}

          {/* Real Counting Results View (Phase 7) */}
          {activeMode === 'counting' && countingResult && !isPipelineBusy && (
            <div className="p-6 rounded-xl border border-cyan-800/80 bg-slate-900/90 space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">Vehicle Counting & Directional Flow</h3>
                    <Badge variant="success" size="sm">
                      <Calculator className="h-3 w-3 mr-1" />
                      Stage: Counting-Run
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Engine: <span className="font-mono text-cyan-300">LineCrossingCounter</span> • Tripwire: <span className="font-mono text-cyan-300">{countingResult.counting_line.label}</span> • Processed {countingResult.total_frames_processed} frames in <span className="font-mono text-emerald-400">{countingResult.processing_time_ms}ms</span>
                  </p>
                </div>
                <Badge variant="outline" size="sm" className="font-mono text-xs">
                  Tripwire Y = {(countingResult.counting_line.p1.y * 100).toFixed(0)}%
                </Badge>
              </div>

              {/* KPI Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-950 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-cyan-950 border border-cyan-800 text-cyan-400">
                    <Hash className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Counted</span>
                    <p className="text-xl font-bold text-white">{countingResult.total_counted_vehicles}</p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-950 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-emerald-950 border border-emerald-800 text-emerald-400">
                    <Car className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Cars Counted</span>
                    <p className="text-xl font-bold text-emerald-300">{countingResult.counts_by_class['car'] || 0}</p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-950 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-amber-950 border border-amber-800 text-amber-400">
                    <Truck className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Trucks Counted</span>
                    <p className="text-xl font-bold text-amber-300">{countingResult.counts_by_class['truck'] || 0}</p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-950 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-purple-950 border border-purple-800 text-purple-400">
                    <Bus className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Buses / Other</span>
                    <p className="text-xl font-bold text-purple-300">
                      {(countingResult.counts_by_class['bus'] || 0) +
                        (countingResult.counts_by_class['motorcycle'] || 0) +
                        (countingResult.counts_by_class['bicycle'] || 0)}
                    </p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-950 flex items-center gap-3 col-span-2 sm:col-span-1">
                  <div className="p-2 rounded-md bg-blue-950 border border-blue-800 text-blue-400">
                    <ArrowRightLeft className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Directional Flow</span>
                    <p className="text-xs font-mono text-slate-200 mt-0.5">
                      In: <span className="text-cyan-300 font-bold">{countingResult.counts_by_direction['inbound'] || 0}</span> | Out: <span className="text-amber-300 font-bold">{countingResult.counts_by_direction['outbound'] || 0}</span>
                    </p>
                  </div>
                </div>
              </div>

              {/* Annotated Preview with Virtual Tripwire & HUD */}
              {countingResult.preview_frame_base64 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <Eye className="h-4 w-4 text-cyan-400" />
                      Visual Tripwire Preview (with Line Crossing HUD)
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">Sampled Frame with Glowing Counting Line</span>
                  </div>
                  <div className="relative rounded-xl overflow-hidden border border-cyan-900/60 bg-black max-w-2xl mx-auto shadow-xl">
                    <img
                      src={countingResult.preview_frame_base64}
                      alt="Vehicle Counting Preview"
                      className="w-full h-auto object-contain"
                    />
                  </div>
                </div>
              )}

              {/* Crossing Events Chronological Audit Log */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Line Crossing Events Log ({countingResult.crossing_events.length} events)
                  </h4>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Deduplicated per persistent Track ID
                  </span>
                </div>

                {countingResult.crossing_events.length > 0 ? (
                  <div className="max-h-60 overflow-y-auto divide-y divide-slate-800/80 rounded-lg border border-slate-800 bg-slate-950/60 font-mono text-xs">
                    {countingResult.crossing_events.map((evt, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 hover:bg-slate-900/40 transition-colors flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-cyan-900/90 text-cyan-200 border border-cyan-700 text-[10px] font-bold">
                            Track #{evt.track_id}
                          </span>
                          <span className="text-slate-200 font-semibold uppercase text-[11px]">
                            {evt.class_name}
                          </span>
                          <Badge variant="outline" size="sm" className="text-[10px]">
                            Frame #{evt.frame_index} ({evt.timestamp_seconds.toFixed(2)}s)
                          </Badge>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-slate-400 text-[10px]">
                            Point: ({evt.crossing_point[0]}, {evt.crossing_point[1]})
                          </span>
                          <Badge
                            variant={evt.direction === 'inbound' ? 'info' : 'warning'}
                            size="sm"
                          >
                            {evt.direction === 'inbound' ? (
                              <ArrowDownRight className="h-3 w-3 mr-1" />
                            ) : (
                              <ArrowUpRight className="h-3 w-3 mr-1" />
                            )}
                            {evt.direction.toUpperCase()}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 rounded-lg border border-slate-800 bg-slate-950/60 text-center text-xs text-slate-500 font-mono">
                    No vehicles crossed the configured virtual line in this clip.
                  </div>
                )}
              </div>

              {/* Phase 8 Forward Note */}
              <div className="flex items-center gap-2 p-3 rounded-lg bg-cyan-950/30 border border-cyan-900/40 text-xs text-slate-300">
                <Clock className="h-4 w-4 text-cyan-400 shrink-0" />
                <span>
                  <strong className="text-white">Counting active:</strong> Genuine, deduplicated vehicle counts are computed per track ID. Lane-level spatial analysis will be added in Phase 8.
                </span>
              </div>
            </div>
          )}

          {/* Real Tracking Results View (Phase 6 fallback) */}
          {activeMode === 'tracking' && trackingResult && !isPipelineBusy && (
            <div className="p-6 rounded-xl border border-cyan-800/80 bg-slate-900/90 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">Multi-Object Tracking Results</h3>
                    <Badge variant="success" size="sm">
                      <Route className="h-3 w-3 mr-1" />
                      Stage: Tracking-Run
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Tracker: <span className="font-mono text-cyan-300">{trackingResult.tracker_name}</span> • Processed {trackingResult.total_frames_processed} frames in <span className="font-mono text-emerald-400">{trackingResult.processing_time_ms}ms</span>
                  </p>
                </div>
              </div>

              {trackingResult.preview_frame_base64 && (
                <div className="relative rounded-xl overflow-hidden border border-cyan-900/60 bg-black max-w-2xl mx-auto shadow-xl">
                  <img
                    src={trackingResult.preview_frame_base64}
                    alt="Tracking Preview"
                    className="w-full h-auto object-contain"
                  />
                </div>
              )}
            </div>
          )}

          {/* Raw Detections View (Phase 5 fallback) */}
          {activeMode === 'detection' && detectionResult && !isPipelineBusy && (
            <div className="p-6 rounded-xl border border-cyan-800/80 bg-slate-900/90 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">YOLO Vehicle Detections (Raw)</h3>
                    <Badge variant="info" size="sm">
                      <Crosshair className="h-3 w-3 mr-1" />
                      Stage: Detections-Run
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Model: <span className="font-mono text-cyan-300">{detectionResult.model_name}</span> • Processed {detectionResult.total_frames_processed} frames in <span className="font-mono text-emerald-400">{detectionResult.processing_time_ms}ms</span>
                  </p>
                </div>
              </div>

              {detectionResult.preview_frame_base64 && (
                <div className="relative rounded-xl overflow-hidden border border-cyan-900/60 bg-black max-w-2xl mx-auto shadow-xl">
                  <img
                    src={detectionResult.preview_frame_base64}
                    alt="Detection Preview"
                    className="w-full h-auto object-contain"
                  />
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Ingested Videos Registry */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-cyan-400" />
              <span>Ingested Videos Registry</span>
            </CardTitle>
            <CardDescription>
              Previously uploaded video sources ready for tracking and counting analysis
            </CardDescription>
          </div>
          <button
            onClick={fetchRecentVideos}
            disabled={isLoadingList}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Refresh list"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoadingList ? 'animate-spin' : ''}`} />
          </button>
        </CardHeader>
        <CardContent>
          {recentVideos.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500 font-mono">
              No videos uploaded yet. Upload a traffic video above to start.
            </div>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {recentVideos.map((vid) => (
                <div
                  key={vid.id}
                  className={`py-3 flex items-center justify-between text-xs px-3 rounded-lg transition-colors cursor-pointer ${
                    currentVideo?.id === vid.id ? 'bg-cyan-950/20 border border-cyan-900/40' : 'hover:bg-slate-900/40'
                  }`}
                  onClick={() => setCurrentVideo(vid)}
                >
                  <div className="flex items-center gap-3">
                    <FileVideo className="h-4 w-4 text-cyan-400 shrink-0" />
                    <div>
                      <p className="font-medium text-slate-200 truncate max-w-xs sm:max-w-md">
                        {vid.original_filename}
                      </p>
                      <p className="text-[11px] font-mono text-slate-500">
                        {vid.resolution} • {vid.fps} FPS • {vid.duration_seconds}s • {vid.frame_count} frames
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="text-xs py-1 px-2.5 h-auto"
                      onClick={(e) => {
                        e.stopPropagation();
                        setCurrentVideo(vid);
                        handleRunCounting(vid.id);
                      }}
                    >
                      <Calculator className="h-3 w-3 mr-1 text-cyan-400" />
                      Count
                    </Button>
                    <span className="font-mono text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/50 px-2 py-0.5 rounded hidden sm:inline">
                      {vid.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
