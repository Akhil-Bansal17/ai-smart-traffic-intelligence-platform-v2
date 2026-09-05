import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { uploadVideo, listVideos } from '@/api/videos';
import { analyzeTraffic } from '@/api/analytics';
import { VideoMetadata } from '@/types/video';
import { TrafficMetricsResponse } from '@/types/analytics';
import { ApiError } from '@/types/api';
import {
  Upload,
  FileVideo,
  CheckCircle2,
  Clock,
  HardDrive,
  RefreshCw,
  BarChart3,
  Car,
  Truck,
  Bus,
  Sliders,
  Info,
  Activity,
  ArrowRightLeft,
  ArrowDownRight,
  ArrowUpRight,
  TrendingUp,
  AlertTriangle,
  Layers,
  Timer,
  Hash,
} from 'lucide-react';

export function TrafficAnalyticsPage() {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<ApiError | null>(null);
  const [currentVideo, setCurrentVideo] = useState<VideoMetadata | null>(null);
  const [recentVideos, setRecentVideos] = useState<VideoMetadata[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Analytics states (Phase 8)
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<ApiError | null>(null);
  const [analyticsResult, setAnalyticsResult] = useState<TrafficMetricsResponse | null>(null);

  // Parameters
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.35);
  const [maxFrames, setMaxFrames] = useState<number>(100);
  const [iouThreshold, setIouThreshold] = useState<number>(0.30);
  const [linePositionRatio, setLinePositionRatio] = useState<number>(0.50);
  const [timeBucketSeconds, setTimeBucketSeconds] = useState<number>(5.0);

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
    setAnalyticsResult(null);
    setAnalyticsError(null);

    try {
      const uploadedVideo = await uploadVideo(file);
      setCurrentVideo(uploadedVideo);
      await fetchRecentVideos();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setUploadError(apiErr);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleRunAnalytics = async () => {
    if (!currentVideo) return;

    setIsAnalyzing(true);
    setAnalyticsError(null);

    try {
      const response = await analyzeTraffic(currentVideo.id, {
        confidence_threshold: confidenceThreshold,
        max_frames: maxFrames > 0 ? maxFrames : undefined,
        iou_threshold: iouThreshold,
        counting_line: {
          p1: { x: 0.0, y: linePositionRatio },
          p2: { x: 1.0, y: linePositionRatio },
          label: `horizontal-line-${Math.round(linePositionRatio * 100)}pct`,
          direction_a_to_b: 'inbound',
          direction_b_to_a: 'outbound',
          min_movement_px: 2.0,
        },
        time_bucket_seconds: timeBucketSeconds,
      });
      setAnalyticsResult(response);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setAnalyticsError(apiErr);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getClassIcon = (className: string) => {
    const name = className.toLowerCase();
    if (name === 'car') return <Car className="h-4 w-4 text-cyan-400" />;
    if (name === 'truck') return <Truck className="h-4 w-4 text-emerald-400" />;
    if (name === 'bus') return <Bus className="h-4 w-4 text-amber-400" />;
    return <Car className="h-4 w-4 text-indigo-400" />;
  };

  const getClassColor = (className: string) => {
    const name = className.toLowerCase();
    if (name === 'car') return 'from-cyan-500 to-blue-600';
    if (name === 'truck') return 'from-emerald-500 to-teal-600';
    if (name === 'bus') return 'from-amber-500 to-orange-600';
    if (name === 'motorcycle') return 'from-purple-500 to-indigo-600';
    return 'from-slate-500 to-slate-700';
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-[#0c1322] to-cyan-950/20 shadow-lg shadow-black/30">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <BarChart3 className="h-6 w-6 text-cyan-400" />
              <span>Traffic Analytics & Flow Engine</span>
            </h1>
            <Badge variant="info" size="sm">Phase 8</Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
            Derives mathematically rigorous traffic flow metrics from deduplicated vehicle trajectories and crossing events.
            Includes flow rates, class breakdowns, directional distribution, and non-interpolated time-series volume bucketing.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto">
          <Badge variant="success" size="sm" className="px-3 py-1">
            <Activity className="h-3.5 w-3.5 mr-1.5 text-emerald-400" />
            Zero-Fabrication Guarantee
          </Badge>
        </div>
      </div>

      {/* Main Grid: Upload/Source + Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Video Ingestion & Selection */}
        <div className="space-y-6 lg:col-span-1">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <FileVideo className="h-4 w-4 text-cyan-400" />
                  Video Source
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={fetchRecentVideos}
                  disabled={isLoadingList}
                  className="h-7 px-2 text-slate-400 hover:text-white"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${isLoadingList ? 'animate-spin' : ''}`} />
                </Button>
              </CardTitle>
              <CardDescription className="text-xs">
                Select an existing video or upload an MP4/AVI feed.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Dropzone */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all ${
                  isDragging
                    ? 'border-cyan-500 bg-cyan-950/30'
                    : 'border-slate-700/80 hover:border-slate-600 bg-slate-900/40'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/mp4,video/avi,video/quicktime,video/x-matroska"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFile(e.target.files[0]);
                    }
                  }}
                />
                <div className="flex flex-col items-center justify-center gap-2 py-2">
                  <div className="p-2.5 rounded-full bg-slate-800 text-cyan-400 border border-slate-700">
                    <Upload className="h-5 w-5" />
                  </div>
                  <div className="text-xs font-medium text-slate-200">
                    {isUploading ? 'Uploading & Validating...' : 'Drop video here or click to browse'}
                  </div>
                  <p className="text-[11px] text-slate-500">Supports MP4, AVI, MOV up to 500MB</p>
                </div>
              </div>

              {uploadError && (
                <ErrorState
                  title="Upload Failed"
                  message={uploadError.message}
                  code={uploadError.code}
                  onRetry={() => fileInputRef.current?.click()}
                  className="py-2"
                />
              )}

              {/* Active Video Info */}
              {currentVideo && (
                <div className="p-3.5 rounded-xl border border-cyan-900/40 bg-cyan-950/20 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-cyan-300 flex items-center gap-1.5 truncate">
                      <CheckCircle2 className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                      <span className="truncate">{currentVideo.original_filename}</span>
                    </span>
                    <Badge variant="info" size="sm">Active</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 font-mono">
                    <div className="flex items-center gap-1">
                      <HardDrive className="h-3 w-3 text-slate-500" />
                      <span>{currentVideo.frame_count} frames</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-slate-500" />
                      <span>{currentVideo.duration_seconds ? `${currentVideo.duration_seconds.toFixed(1)}s` : 'N/A'}</span>
                    </div>
                    <div>
                      <span>Res: {currentVideo.resolution || 'N/A'}</span>
                    </div>
                    <div>
                      <span>FPS: {currentVideo.fps?.toFixed(1) || 'N/A'}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Recent Videos Picker */}
              {recentVideos.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-slate-800/80">
                  <label className="text-xs font-medium text-slate-400">Recent Videos</label>
                  <div className="max-h-36 overflow-y-auto space-y-1.5 pr-1">
                    {recentVideos.map((vid) => (
                      <button
                        key={vid.id}
                        onClick={() => {
                          setCurrentVideo(vid);
                          setAnalyticsResult(null);
                        }}
                        className={`w-full text-left p-2 rounded-lg text-xs transition-colors flex items-center justify-between ${
                          currentVideo?.id === vid.id
                            ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-800/60'
                            : 'bg-slate-800/40 hover:bg-slate-800 text-slate-300 border border-slate-700/50'
                        }`}
                      >
                        <span className="truncate max-w-[170px]">{vid.original_filename}</span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {vid.duration_seconds ? `${vid.duration_seconds.toFixed(0)}s` : ''}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Engine Parameters Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Sliders className="h-4 w-4 text-cyan-400" />
                Pipeline & Metric Controls
              </CardTitle>
              <CardDescription className="text-xs">
                Fine-tune detection, tracking, counting line, and time binning.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              {/* Line Position Ratio */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-medium">Counting Line (Y-Ratio)</span>
                  <span className="font-mono text-cyan-400 font-semibold">{linePositionRatio.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.90"
                  step="0.05"
                  value={linePositionRatio}
                  onChange={(e) => setLinePositionRatio(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
              </div>

              {/* Time Bucket Size */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-medium">Time Series Bucket Size</span>
                  <span className="font-mono text-cyan-400 font-semibold">{timeBucketSeconds.toFixed(1)}s</span>
                </div>
                <input
                  type="range"
                  min="1.0"
                  max="30.0"
                  step="1.0"
                  value={timeBucketSeconds}
                  onChange={(e) => setTimeBucketSeconds(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
                <p className="text-[10px] text-slate-500">Discrete aggregation interval (no interpolation)</p>
              </div>

              {/* Confidence Threshold */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-medium">Detector Confidence</span>
                  <span className="font-mono text-cyan-400 font-semibold">{confidenceThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.90"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
              </div>

              {/* Tracker IOU Threshold */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-medium">Tracker Match IOU</span>
                  <span className="font-mono text-cyan-400 font-semibold">{iouThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.80"
                  step="0.05"
                  value={iouThreshold}
                  onChange={(e) => setIouThreshold(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
              </div>

              {/* Max Frames */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-medium">Max Frames</span>
                  <span className="font-mono text-cyan-400 font-semibold">{maxFrames}</span>
                </div>
                <input
                  type="number"
                  min="10"
                  max="500"
                  step="10"
                  value={maxFrames}
                  onChange={(e) => setMaxFrames(Math.max(10, parseInt(e.target.value) || 10))}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Run Analytics Button */}
              <Button
                variant="primary"
                onClick={handleRunAnalytics}
                disabled={!currentVideo || isAnalyzing}
                className="w-full mt-3 py-2.5 font-semibold text-xs tracking-wide bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 shadow-md shadow-cyan-950/50"
              >
                {isAnalyzing ? (
                  <span className="flex items-center gap-2">
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Computing Traffic Analytics...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Run Flow Analytics Engine
                  </span>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Analytics Results & Visualizations */}
        <div className="space-y-6 lg:col-span-2">
          {isAnalyzing && (
            <Card>
              <CardContent className="py-16">
                <LoadingState
                  message="Evaluating frames through YOLO detector, ByteTrack tracker, trajectory crossing counter, and mathematical flow metrics engine..."
                />
              </CardContent>
            </Card>
          )}

          {analyticsError && (
            <ErrorState
              title="Analytics Execution Failed"
              message={analyticsError.message}
              code={analyticsError.code}
              onRetry={handleRunAnalytics}
            />
          )}

          {!isAnalyzing && !analyticsError && !analyticsResult && (
            <Card className="border-dashed border-slate-800 bg-slate-900/30">
              <CardContent className="py-20 text-center space-y-4">
                <div className="mx-auto w-12 h-12 rounded-2xl bg-cyan-950/60 border border-cyan-800/40 flex items-center justify-center text-cyan-400">
                  <BarChart3 className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-sm font-semibold text-slate-200">No Analytics Run Yet</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Select a video feed and click &quot;Run Flow Analytics Engine&quot; to compute vehicle counts, flow rates, class distributions, and time-series histograms.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {analyticsResult && !isAnalyzing && (
            <div className="space-y-6">
              {/* Data Honesty Alert / Banner */}
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 shadow-md space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Info className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                    <span className="text-xs font-semibold text-slate-200">
                      Observation Baseline & Extrapolation Transparency
                    </span>
                  </div>
                  {analyticsResult.is_extrapolated ? (
                    <Badge variant="warning" size="sm" className="font-mono">
                      <AlertTriangle className="h-3 w-3 mr-1" />
                      Hourly Flow Extrapolated (Clip Duration &lt; 1h)
                    </Badge>
                  ) : (
                    <Badge variant="success" size="sm" className="font-mono">
                      True Measured Hourly Rate
                    </Badge>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Metrics derived from <span className="font-mono text-slate-200">{analyticsResult.total_frames_processed}</span> evaluated frames
                  over an observation duration of <span className="font-mono text-cyan-300">{analyticsResult.observation_duration_seconds.toFixed(2)}s</span>.
                  Hourly flow rate is extrapolated using formula <span className="font-mono text-slate-300">N / (T_obs / 3600)</span> and clearly flagged.
                </p>
              </div>

              {/* KPI Metrics Summary Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
                {/* Total Volume */}
                <Card className="bg-slate-900/60 border-slate-800">
                  <CardContent className="p-4 space-y-1">
                    <div className="text-[11px] font-medium text-slate-400 flex items-center justify-between">
                      <span>Total Volume</span>
                      <Hash className="h-3.5 w-3.5 text-cyan-400" />
                    </div>
                    <div className="text-2xl font-bold font-mono text-cyan-300">
                      {analyticsResult.total_vehicles}
                    </div>
                    <p className="text-[10px] text-slate-500">Deduplicated vehicles</p>
                  </CardContent>
                </Card>

                {/* Observation Duration */}
                <Card className="bg-slate-900/60 border-slate-800">
                  <CardContent className="p-4 space-y-1">
                    <div className="text-[11px] font-medium text-slate-400 flex items-center justify-between">
                      <span>Duration (T_obs)</span>
                      <Timer className="h-3.5 w-3.5 text-blue-400" />
                    </div>
                    <div className="text-2xl font-bold font-mono text-slate-100">
                      {analyticsResult.observation_duration_seconds.toFixed(1)}<span className="text-xs font-normal text-slate-400">s</span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-mono">
                      {analyticsResult.total_frames_processed} frames
                    </p>
                  </CardContent>
                </Card>

                {/* Flow Rate / Min */}
                <Card className="bg-slate-900/60 border-slate-800">
                  <CardContent className="p-4 space-y-1">
                    <div className="text-[11px] font-medium text-slate-400 flex items-center justify-between">
                      <span>Flow Rate / min</span>
                      <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                    </div>
                    <div className="text-2xl font-bold font-mono text-emerald-400">
                      {analyticsResult.flow_rate_per_minute.toFixed(1)}
                    </div>
                    <p className="text-[10px] text-slate-500">Vehicles / min</p>
                  </CardContent>
                </Card>

                {/* Flow Rate / Hour */}
                <Card className="bg-slate-900/60 border-slate-800">
                  <CardContent className="p-4 space-y-1">
                    <div className="text-[11px] font-medium text-slate-400 flex items-center justify-between">
                      <span>Flow Rate / hr</span>
                      <Activity className="h-3.5 w-3.5 text-amber-400" />
                    </div>
                    <div className="text-2xl font-bold font-mono text-amber-300">
                      {analyticsResult.flow_rate_per_hour_extrapolated.toFixed(0)}
                    </div>
                    <p className="text-[10px] text-amber-400/80 font-mono">
                      {analyticsResult.is_extrapolated ? 'Extrapolated' : 'Measured'}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Class & Directional Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Vehicle Class Distribution */}
                <Card className="border-slate-800 bg-slate-900/70">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                      <Car className="h-4 w-4 text-cyan-400" />
                      Vehicle Class Breakdown
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3.5">
                    {analyticsResult.class_distribution.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No vehicles counted</p>
                    ) : (
                      analyticsResult.class_distribution.map((cls) => (
                        <div key={cls.class_name} className="space-y-1.5">
                          <div className="flex items-center justify-between text-xs">
                            <span className="flex items-center gap-2 font-medium capitalize text-slate-200">
                              {getClassIcon(cls.class_name)}
                              {cls.class_name}
                            </span>
                            <div className="flex items-center gap-2 font-mono">
                              <span className="font-semibold text-white">{cls.count}</span>
                              <span className="text-slate-400 text-[11px]">({cls.percentage.toFixed(1)}%)</span>
                            </div>
                          </div>
                          {/* Progress Bar */}
                          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className={`h-full rounded-full bg-gradient-to-r ${getClassColor(cls.class_name)} transition-all duration-500`}
                              style={{ width: `${Math.max(cls.percentage, 2)}%` }}
                            />
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>

                {/* Directional Distribution */}
                <Card className="border-slate-800 bg-slate-900/70">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                      <ArrowRightLeft className="h-4 w-4 text-emerald-400" />
                      Directional Flow Split
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {analyticsResult.directional_distribution.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No crossing directions recorded</p>
                    ) : (
                      <>
                        <div className="grid grid-cols-2 gap-3">
                          {analyticsResult.directional_distribution.map((dir) => (
                            <div
                              key={dir.direction}
                              className="p-3 rounded-xl border border-slate-800 bg-slate-800/40 space-y-1.5"
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-semibold capitalize text-slate-300 flex items-center gap-1.5">
                                  {dir.direction === 'inbound' ? (
                                    <ArrowDownRight className="h-3.5 w-3.5 text-cyan-400" />
                                  ) : (
                                    <ArrowUpRight className="h-3.5 w-3.5 text-emerald-400" />
                                  )}
                                  {dir.direction}
                                </span>
                                <span className="text-xs font-mono font-bold text-white">{dir.count}</span>
                              </div>
                              <div className="text-[11px] font-mono text-slate-400">
                                {dir.percentage.toFixed(1)}% of total
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Visual Split Bar */}
                        <div className="space-y-1 pt-1">
                          <div className="w-full h-2.5 rounded-full bg-slate-800 flex overflow-hidden">
                            {analyticsResult.directional_distribution.map((dir) => (
                              <div
                                key={dir.direction}
                                className={`h-full transition-all duration-500 ${
                                  dir.direction === 'inbound'
                                    ? 'bg-cyan-500'
                                    : 'bg-emerald-500'
                                }`}
                                style={{ width: `${dir.percentage}%` }}
                                title={`${dir.direction}: ${dir.count} (${dir.percentage.toFixed(1)}%)`}
                              />
                            ))}
                          </div>
                          <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                            <span>Inbound (Downward)</span>
                            <span>Outbound (Upward)</span>
                          </div>
                        </div>
                      </>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Time-Series Flow Histogram */}
              <Card className="border-slate-800 bg-slate-900/70">
                <CardHeader className="pb-3">
                  <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Layers className="h-4 w-4 text-cyan-400" />
                      Time-Series Flow Histogram (Discrete Bins)
                    </span>
                    <Badge variant="info" size="sm" className="font-mono">
                      Δt = {analyticsResult.time_series && analyticsResult.time_series.length > 0 ? `${(analyticsResult.time_series[0].end_time_seconds - analyticsResult.time_series[0].start_time_seconds).toFixed(1)}s` : `${timeBucketSeconds}s`}
                    </Badge>
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Non-interpolated discrete time buckets tracking vehicle passage timestamps.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {!analyticsResult.time_series || analyticsResult.time_series.length === 0 ? (
                    <p className="text-xs text-slate-500 italic py-4 text-center">No time buckets available</p>
                  ) : (
                    <div className="space-y-2">
                      <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto pr-1">
                        {analyticsResult.time_series.map((bucket, idx) => {
                          const maxBucketCount = Math.max(
                            1,
                            ...analyticsResult.time_series.map((b) => b.vehicle_count)
                          );
                          const barWidthPct = (bucket.vehicle_count / maxBucketCount) * 100;
                          const bucketDurationMin = Math.max(0.001, (bucket.end_time_seconds - bucket.start_time_seconds) / 60.0);
                          const bucketFlowRate = bucket.vehicle_count / bucketDurationMin;

                          return (
                            <div
                              key={idx}
                              className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-800/30 flex items-center gap-3 text-xs"
                            >
                              {/* Time Range */}
                              <div className="font-mono text-slate-400 w-24 flex-shrink-0 text-[11px]">
                                [{bucket.start_time_seconds.toFixed(1)}s - {bucket.end_time_seconds.toFixed(1)}s]
                              </div>

                              {/* Visual Bar */}
                              <div className="flex-1">
                                <div className="w-full h-3 rounded bg-slate-800/80 overflow-hidden flex">
                                  <div
                                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                                    style={{ width: `${Math.max(barWidthPct, bucket.vehicle_count > 0 ? 5 : 0)}%` }}
                                  />
                                </div>
                              </div>

                              {/* Count & Flow Rate */}
                              <div className="flex items-center gap-3 text-right flex-shrink-0 font-mono">
                                <span className="font-bold text-white min-w-[24px]">
                                  {bucket.vehicle_count} <span className="text-[10px] font-normal text-slate-400">veh</span>
                                </span>
                                <span className="text-cyan-400 text-[11px] min-w-[55px]">
                                  {bucketFlowRate.toFixed(1)}/m
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Raw Pipeline & Counting Summary */}
              <Card className="border-slate-800 bg-slate-900/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                    <Activity className="h-3.5 w-3.5 text-cyan-400" />
                    Pipeline Verification Metadata
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                    <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/50">
                      <span className="text-slate-500 block text-[10px]">TOTAL TRACKS</span>
                      <span className="text-slate-200 font-semibold">{analyticsResult.unique_tracks}</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/50">
                      <span className="text-slate-500 block text-[10px]">TOTAL COUNTED</span>
                      <span className="text-cyan-300 font-semibold">{analyticsResult.total_vehicles}</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/50">
                      <span className="text-slate-500 block text-[10px]">COUNTING LINE</span>
                      <span className="text-slate-200 font-semibold truncate block">{analyticsResult.counting_line_label}</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/50">
                      <span className="text-slate-500 block text-[10px]">PROCESSING TIME</span>
                      <span className="text-emerald-400 font-semibold">{analyticsResult.processing_time_ms.toFixed(1)}ms</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
