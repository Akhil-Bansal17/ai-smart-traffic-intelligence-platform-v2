import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { uploadVideo, listVideos } from '@/api/videos';
import { detectVideo } from '@/api/detection';
import { trackVideo } from '@/api/tracking';
import { VideoMetadata } from '@/types/video';
import { VideoDetectionResponse } from '@/types/detection';
import { VideoTrackingResponse } from '@/types/tracking';
import { ApiError } from '@/types/api';
import {
  Upload,
  FileVideo,
  CheckCircle2,
  Clock,
  HardDrive,
  RefreshCw,
  Play,
  Crosshair,
  Car,
  Truck,
  Bus,
  Sliders,
  Eye,
  Info,
  Route,
  Activity,
} from 'lucide-react';

type AnalysisMode = 'detection' | 'tracking';

export function VideoAnalysisPage() {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<ApiError | null>(null);
  const [currentVideo, setCurrentVideo] = useState<VideoMetadata | null>(null);
  const [recentVideos, setRecentVideos] = useState<VideoMetadata[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Mode state: Detection (Phase 5) vs Tracking (Phase 6)
  const [activeMode, setActiveMode] = useState<AnalysisMode>('tracking');

  // Detection states
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionError, setDetectionError] = useState<ApiError | null>(null);
  const [detectionResult, setDetectionResult] = useState<VideoDetectionResponse | null>(null);

  // Tracking states
  const [isTracking, setIsTracking] = useState(false);
  const [trackingError, setTrackingError] = useState<ApiError | null>(null);
  const [trackingResult, setTrackingResult] = useState<VideoTrackingResponse | null>(null);

  // Parameters
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.35);
  const [maxFrames, setMaxFrames] = useState<number>(50);
  const [iouThreshold, setIouThreshold] = useState<number>(0.30);

  const fileInputRef = useRef<HTMLInputElement>(null);

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

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border border-cyan-900/40 bg-gradient-to-r from-slate-900/90 via-slate-900/80 to-cyan-950/20 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <div className="p-3.5 rounded-xl bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
            <Route className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold tracking-tight text-white">Video Ingestion & Object Tracking</h1>
              <Badge variant="success" size="sm">
                <CheckCircle2 className="h-3 w-3 mr-1" />
                Phase 6: Multi-Object Tracking Active
              </Badge>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Connects <span className="font-mono text-cyan-300">Detector (YOLOv8n)</span> to <span className="font-mono text-cyan-300">ByteTrack (Kalman/IoU)</span> for persistent vehicle track IDs.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Badge variant="info" size="md">
            <Activity className="h-3 w-3 mr-1" />
            CV Pipeline Stage 2
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
            Upload traffic camera footage for frame sampling, YOLO vehicle detection, and multi-object tracking.
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
                    <span>Inference & Tracking Controls</span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    Detector: <span className="text-cyan-300">YOLOv8n</span> • Tracker: <span className="text-cyan-300">ByteTrack-Kalman-IoU</span>
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
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
                      IoU Matching Threshold: <span className="font-mono text-cyan-400">{iouThreshold}</span>
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
                </div>

                {/* Pipeline Execution Buttons */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-800">
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <Info className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                    <span>Tracking maintains persistent Track IDs across video frames using Kalman motion association.</span>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={isDetecting || isTracking}
                      onClick={() => handleRunDetection(currentVideo.id)}
                      className="w-full sm:w-auto text-xs"
                    >
                      {isDetecting ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                          Detecting...
                        </>
                      ) : (
                        <>
                          <Crosshair className="h-3.5 w-3.5 mr-1.5 text-cyan-400" />
                          Detection Only (Phase 5)
                        </>
                      )}
                    </Button>

                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      disabled={isDetecting || isTracking}
                      onClick={() => handleRunTracking(currentVideo.id)}
                      className="w-full sm:w-auto text-xs"
                    >
                      {isTracking ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                          Tracking...
                        </>
                      ) : (
                        <>
                          <Play className="h-3.5 w-3.5 mr-1.5 fill-current" />
                          Run Object Tracking (Phase 6)
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error States */}
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
          {(isTracking || isDetecting) && (
            <div className="p-8 rounded-xl bg-slate-900/80 border border-cyan-800/50">
              <LoadingState
                message={
                  isTracking
                    ? 'Decoding frames, running YOLO detection, and associating bounding boxes with ByteTrack Kalman filter...'
                    : 'Decoding frames with VideoSource and computing YOLO vehicle detections...'
                }
                size="lg"
              />
            </div>
          )}

          {/* Mode Tabs if results exist */}
          {(trackingResult || detectionResult) && !isTracking && !isDetecting && (
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
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
                  Object Tracking Results (Phase 6)
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

          {/* Real Tracking Results View (Phase 6) */}
          {activeMode === 'tracking' && trackingResult && !isTracking && (
            <div className="p-6 rounded-xl border border-cyan-800/80 bg-slate-900/90 space-y-6">
              {/* Header */}
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
                    Tracker: <span className="font-mono text-cyan-300">{trackingResult.tracker_name}</span> • Model: <span className="font-mono text-cyan-300">{trackingResult.detector_model}</span> • Processed {trackingResult.total_frames_processed} frames in <span className="font-mono text-emerald-400">{trackingResult.processing_time_ms}ms</span>
                  </p>
                </div>
                <Badge variant="outline" size="sm" className="font-mono text-xs">
                  IoU &ge; {iouThreshold} @ {trackingResult.target_fps} FPS
                </Badge>
              </div>

              {/* KPI Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-950 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-cyan-950 border border-cyan-800 text-cyan-400">
                    <Route className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Unique Tracks</span>
                    <p className="text-lg font-bold text-white">{trackingResult.total_unique_tracks}</p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-950 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-emerald-950 border border-emerald-800 text-emerald-400">
                    <Car className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Cars Tracked</span>
                    <p className="text-lg font-bold text-emerald-300">{trackingResult.tracks_by_class['car'] || 0}</p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-950 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-amber-950 border border-amber-800 text-amber-400">
                    <Truck className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Trucks Tracked</span>
                    <p className="text-lg font-bold text-amber-300">{trackingResult.tracks_by_class['truck'] || 0}</p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-950 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-purple-950 border border-purple-800 text-purple-400">
                    <Bus className="h-5 w-5" />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Buses / Other</span>
                    <p className="text-lg font-bold text-purple-300">
                      {(trackingResult.tracks_by_class['bus'] || 0) +
                        (trackingResult.tracks_by_class['motorcycle'] || 0) +
                        (trackingResult.tracks_by_class['bicycle'] || 0)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Annotated Tracking Preview with Visible Track IDs */}
              {trackingResult.preview_frame_base64 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <Eye className="h-4 w-4 text-cyan-400" />
                      Visual Tracking Preview (with Persistent Track IDs)
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">Sampled Frame with ID & Trajectory Labels</span>
                  </div>
                  <div className="relative rounded-xl overflow-hidden border border-cyan-900/60 bg-black max-w-2xl mx-auto shadow-xl">
                    <img
                      src={trackingResult.preview_frame_base64}
                      alt="Object Tracking Preview"
                      className="w-full h-auto object-contain"
                    />
                  </div>
                </div>
              )}

              {/* Frame-by-Frame Track ID Continuity Inspector */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Track ID Continuity Timeline ({trackingResult.frames.length} frames)
                  </h4>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Track ID · Class · Confidence · State
                  </span>
                </div>

                <div className="max-h-72 overflow-y-auto divide-y divide-slate-800/80 rounded-lg border border-slate-800 bg-slate-950/60 font-mono text-xs">
                  {trackingResult.frames.map((frame, idx) => (
                    <div
                      key={idx}
                      className="p-3 hover:bg-slate-900/40 transition-colors space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-cyan-300">
                          Frame #{frame.frame_index} ({frame.timestamp_seconds}s)
                        </span>
                        <Badge
                          variant={frame.active_tracks_count > 0 ? 'info' : 'outline'}
                          size="sm"
                        >
                          {frame.active_tracks_count} {frame.active_tracks_count === 1 ? 'active track' : 'active tracks'}
                        </Badge>
                      </div>

                      {frame.tracked_objects.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                          {frame.tracked_objects.map((obj, oIdx) => (
                            <div
                              key={oIdx}
                              className="p-2 rounded bg-slate-900/80 border border-slate-800/80 flex items-center justify-between text-[11px]"
                            >
                              <div className="flex items-center gap-1.5">
                                <span className="px-2 py-0.5 rounded bg-cyan-900/90 text-cyan-200 border border-cyan-700 text-[10px] font-bold font-mono">
                                  Track #{obj.track_id}
                                </span>
                                <span className="text-slate-300 uppercase font-semibold text-[10px]">
                                  {obj.class_name}
                                </span>
                                <span className="text-emerald-400 font-medium text-[10px]">
                                  {(obj.confidence * 100).toFixed(1)}%
                                </span>
                              </div>
                              <span className="text-slate-400 text-[10px]">
                                Age: {obj.age_frames}f ({obj.state.toUpperCase()})
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-[11px] text-slate-600 italic">No active tracks in this frame</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Phase 7 Forward Note */}
              <div className="flex items-center gap-2 p-3 rounded-lg bg-cyan-950/30 border border-cyan-900/40 text-xs text-slate-300">
                <Clock className="h-4 w-4 text-cyan-400 shrink-0" />
                <span>
                  <strong className="text-white">Tracking active:</strong> Persistent Track IDs are maintained across frames. Vehicle counting (line/zone crossing) will be added in Phase 7.
                </span>
              </div>
            </div>
          )}

          {/* Raw Detections View (Phase 5 fallback) */}
          {activeMode === 'detection' && detectionResult && !isDetecting && (
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
              Previously uploaded video sources ready for tracking and analysis
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
                        handleRunTracking(vid.id);
                      }}
                    >
                      <Route className="h-3 w-3 mr-1 text-cyan-400" />
                      Track
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
