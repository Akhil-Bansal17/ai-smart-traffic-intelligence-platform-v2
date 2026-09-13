/**
 * TypeScript interface definitions for Analysis Persistence and History.
 * Matches backend schemas in backend/app/schemas/analysis.py.
 */

import { TimeSeriesBucket } from './analytics';

export interface ClassMetric {
  class_name: string;
  count: number;
  percentage: number;
}

export interface DirectionMetric {
  direction: string;
  count: number;
  percentage: number;
}

export interface TrafficMetricsRecord {
  id: string;
  analysis_session_id: string;
  observation_duration_seconds: number;
  total_volume: number;
  flow_rate_per_minute: number;
  flow_rate_per_hour: number;
  is_extrapolated: boolean;
  class_distribution: ClassMetric[];
  direction_distribution: DirectionMetric[];
  time_series_buckets: TimeSeriesBucket[];
  created_at: string;
}

export interface LaneResultRecord {
  id: string;
  analysis_session_id: string;
  lane_id: string;
  lane_name: string;
  direction_hint?: string | null;
  polygon_json: number[][];
  polygon_area_px2: number;
  unique_vehicles_count: number;
  peak_occupancy: number;
  average_occupancy: number;
  image_space_density: number;
  normalized_density_score: number;
  vehicle_class_counts?: Record<string, number> | null;
  density_unit: string;
  density_calibration_warning?: string | null;
  created_at: string;
}

export interface CrossingEventRecord {
  id: string;
  analysis_session_id: string;
  track_id: number;
  class_name: string;
  direction: string;
  frame_index: number;
  timestamp_seconds: number;
  centroid_x: number;
  centroid_y: number;
  line_label: string;
  created_at: string;
}

export interface AnalysisSessionSummary {
  id: string;
  video_id: string;
  video_filename?: string | null;
  analysis_type: string;
  status: string;
  started_at: string;
  completed_at?: string | null;
  processing_time_ms?: number | null;
  total_frames_processed: number;
  total_vehicles_detected: number;
  total_vehicles_counted: number;
  error_message?: string | null;
}

export interface AnalysisSessionDetail extends AnalysisSessionSummary {
  config_snapshot?: Record<string, any> | null;
  traffic_metrics?: TrafficMetricsRecord | null;
  lane_results: LaneResultRecord[];
  crossing_events: CrossingEventRecord[];
}

export interface AnalysisSessionListResponse {
  total: number;
  limit: number;
  offset: number;
  sessions: AnalysisSessionSummary[];
}

export interface AnalysisInfoResponse {
  service_name: string;
  version: string;
  persisted_entities: string[];
  supported_analysis_types: string[];
  deduplication_policy: string;
  extrapolation_policy: string;
  density_policy: string;
}

// =========================================================================
// Phase 17: Analysis Job Orchestration Types
// =========================================================================

export type AnalysisJobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface AnalysisJob {
  id: string;
  video_id: string;
  session_id?: string | null;
  status: AnalysisJobStatus;
  analysis_type: string;
  progress?: number | null;
  frames_processed: number;
  total_frames?: number | null;
  processing_fps?: number | null;
  cancellation_requested: boolean;
  error_code?: string | null;
  error_message?: string | null;
  provenance_category: string;
  is_synthetic: boolean;
  config_snapshot?: Record<string, any> | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  updated_at: string;
}

export interface AnalysisJobCreateRequest {
  video_id: string;
  analysis_type?: string;
  confidence_threshold?: number;
  processing_fps?: number;
  max_frames?: number;
  iou_threshold?: number;
  counting_line?: any;
  lanes?: any[];
  persistence_threshold?: number;
}

export interface AnalysisJobListResponse {
  total: number;
  limit: number;
  offset: number;
  jobs: AnalysisJob[];
}

export interface AnalysisJobCancelResponse {
  status: string;
  message: string;
  job: AnalysisJob;
}
