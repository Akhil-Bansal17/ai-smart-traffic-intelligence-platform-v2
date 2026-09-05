/**
 * Traffic Analytics & Flow Metrics TypeScript definitions.
 */
import { CountingLineConfig } from './counting';

export interface ClassMetricItem {
  class_name: string;
  count: number;
  percentage: number;
}

export interface DirectionMetricItem {
  direction: string;
  count: number;
  percentage: number;
}

export interface TimeSeriesBucket {
  bucket_index: number;
  start_time_seconds: number;
  end_time_seconds: number;
  vehicle_count: number;
  class_counts: Record<string, number>;
  inbound_count: number;
  outbound_count: number;
}

export interface TrafficMetricsResponse {
  video_id: string;
  original_filename: string;
  pipeline_stage: string;
  observation_duration_seconds: number;
  total_vehicles: number;
  flow_rate_per_minute: number;
  flow_rate_per_hour_extrapolated: number;
  is_extrapolated: boolean;
  inbound_count: number;
  outbound_count: number;
  inbound_percentage: number;
  outbound_percentage: number;
  class_distribution: ClassMetricItem[];
  directional_distribution: DirectionMetricItem[];
  time_series: TimeSeriesBucket[];
  total_frames_processed: number;
  total_detections: number;
  unique_tracks: number;
  counting_line_label: string;
  processing_time_ms: number;
  generated_at: string;
}

export interface AnalyticsRequestParams {
  confidence_threshold?: number;
  iou_threshold?: number;
  max_frames?: number;
  target_fps?: number;
  counting_line?: CountingLineConfig;
  time_bucket_seconds?: number;
}

export interface AnalyticsInfoResponse {
  engine_name: string;
  metric_definitions: Record<string, string>;
  extrapolation_policy: string;
}
