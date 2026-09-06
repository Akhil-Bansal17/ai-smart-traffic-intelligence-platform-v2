/**
 * Lane Analysis & Density Estimation TypeScript definitions.
 */

export interface LaneRegionConfig {
  lane_id: string;
  name: string;
  polygon: [number, number][];
  direction_hint?: string;
}

export interface LaneAnalysisRequestParams {
  confidence_threshold?: number;
  iou_threshold?: number;
  max_frames?: number;
  target_fps?: number;
  persistence_threshold?: number;
  lanes: LaneRegionConfig[];
}

export interface PerLaneSummary {
  lane_id: string;
  lane_name: string;
  polygon: [number, number][];
  polygon_area_px2: number;
  total_unique_vehicles: number;
  vehicle_class_counts: Record<string, number>;
  direction_hint?: string;
  image_space_density_vehicles_per_px2: number;
  normalized_density_score: number;
  density_unit: string;
  density_formula: string;
  peak_occupancy: number;
  average_occupancy: number;
}

export interface LaneAnalyticsResponse {
  video_id: string;
  original_filename: string;
  pipeline_stage: string;
  observation_duration_seconds: number;
  total_frames_processed: number;
  total_unique_tracks: number;
  lanes: PerLaneSummary[];
  unassigned_vehicles_count: number;
  density_calibration_warning: string;
  directional_metrics_omitted_reason: string;
  processing_time_ms: number;
  generated_at: string;
}

export interface LaneAnalysisInfoResponse {
  service_name: string;
  assignment_method: string;
  density_definition: string;
  calibration_policy: string;
  directional_policy: string;
}
