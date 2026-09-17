/**
 * Types for Business-Grade Traffic Reporting & Export.
 * Phase 19: Business-Grade Traffic Reporting & Export.
 */

export type TruthLabel =
  | 'OBSERVED'
  | 'INFERRED'
  | 'PREDICTED'
  | 'SIMULATED'
  | 'RECOMMENDED/ADVISORY'
  | 'UNAVAILABLE';

export type ReportType = 'traffic_analysis';
export type ReportScopeType = 'session' | 'time_range';
export type ReportStatus = 'pending' | 'generating' | 'completed' | 'failed';
export type ReportFormat = 'pdf' | 'csv' | 'json';

export interface ScopeMetadata {
  report_id: string;
  report_type: string;
  scope_type: ReportScopeType;
  session_id?: string;
  time_range_start?: string;
  time_range_end?: string;
  video_id?: string;
  video_filename?: string;
  video_source_type: string;
  video_duration_seconds: number;
  video_fps: number;
  total_frames: number;
  provenance_category: string;
  is_synthetic: boolean;
  provenance_verified: boolean;
  generated_at: string;
}

export interface ExecutiveSummary {
  total_vehicles_detected: number;
  total_vehicles_counted: number;
  flow_rate_vph: number;
  dominant_vehicle_class: string;
  dominant_class_pct: number;
  primary_flow_direction: string;
  primary_direction_pct: number;
  detected_anomalies_count: number;
  active_insights_count: number;
  signal_optimization_status: string;
  emergency_corridor_status: string;
  ml_prediction_status: string;
  provenance_tier: string;
  high_level_assessment: string;
}

export interface TrafficOverviewSection {
  label: TruthLabel;
  total_vehicles_detected: number;
  total_vehicles_counted: number;
  observation_duration_seconds: number;
  overall_flow_rate_vph: number;
  is_extrapolated: boolean;
  inbound_count: number;
  outbound_count: number;
}

export interface VehicleClassItem {
  class_name: string;
  count: number;
  percentage: number;
  label: TruthLabel;
}

export interface DirectionalFlowItem {
  direction: string;
  count: number;
  percentage: number;
  flow_rate_vph: number;
  label: TruthLabel;
}

export interface TimeSeriesBucketItem {
  bucket_index: number;
  start_time_seconds: number;
  end_time_seconds: number;
  vehicle_count: number;
  flow_rate_vph: number;
  label: TruthLabel;
}

export interface LaneMetricItem {
  lane_id: string;
  lane_name: string;
  vehicles_detected: number;
  occupancy_rate: number;
  density_px2: number;
  normalized_density_score: number;
  polygon_area_px2: number;
  vehicle_counts_by_class: Record<string, number>;
  observed_label: TruthLabel;
  inferred_label: TruthLabel;
}

export interface AnomalyReportItem {
  id: string;
  anomaly_type: string;
  severity: string;
  title: string;
  description: string;
  start_time_seconds: number;
  end_time_seconds?: number;
  duration_seconds: number;
  metric_name: string;
  trigger_value: number;
  threshold_value: number;
  lane_id?: string;
  label: TruthLabel;
}

export interface InsightReportItem {
  id: string;
  category: string;
  severity: string;
  title: string;
  summary: string;
  start_time_seconds: number;
  duration_seconds: number;
  affected_lane_name?: string;
  root_cause_observed: string[];
  root_cause_inferred: string[];
  recommendation?: string;
  recommendation_type: string;
  recommendation_rationale?: string;
  limitations: string[];
  dedup_signature: string;
  inferred_label: TruthLabel;
  advisory_label: TruthLabel;
}

export interface PredictionStatusSection {
  is_available: boolean;
  status: string;
  reason: string;
  sample_count: number;
  sample_threshold: number;
  model_name?: string;
  mae?: number;
  rmse?: number;
  r2?: number;
  forecast_steps: Array<{
    step: number;
    predicted_flow_rate_vph: number;
    lower_bound_vph: number;
    upper_bound_vph: number;
  }>;
  label: TruthLabel;
}

export interface SignalOptimizationSection {
  is_available: boolean;
  algorithm_used?: string;
  intersection_name?: string;
  baseline_avg_delay_s?: number;
  optimized_avg_delay_s?: number;
  delay_reduction_pct?: number;
  baseline_los?: string;
  optimized_los?: string;
  optimal_cycle_length_s?: number;
  timing_summary: any[];
  disclaimer: string;
  label: TruthLabel;
}

export interface EmergencyCorridorSection {
  is_available: boolean;
  corridor_name?: string;
  vehicle_type?: string;
  baseline_travel_time_s?: number;
  priority_travel_time_s?: number;
  travel_time_saved_s?: number;
  travel_time_reduction_pct?: number;
  cross_street_delay_impact_s?: number;
  disclaimer: string;
  label: TruthLabel;
}

export interface ProvenanceReportSection {
  provenance_category: string;
  video_source_type: string;
  video_source_reference?: string;
  video_license_reference?: string;
  provenance_verified: boolean;
  captured_at?: string;
  provenance_tier_description: string;
  is_synthetic: boolean;
  label: TruthLabel;
}

export interface DisclaimersSection {
  simulation_notice: string;
  decision_support_notice: string;
  density_calibration_notice: string;
  prediction_boundary_notice: string;
  reproducibility_notice: string;
}

export interface TrafficAnalysisReportData {
  version: string;
  report_id: string;
  title: string;
  generated_at: string;
  scope: ScopeMetadata;
  executive_summary: ExecutiveSummary;
  traffic_overview: TrafficOverviewSection;
  vehicle_composition: {
    label: TruthLabel;
    items: VehicleClassItem[];
    total_counted: number;
  };
  directional_flow: {
    label: TruthLabel;
    items: DirectionalFlowItem[];
    inbound_ratio: number;
    outbound_ratio: number;
  };
  time_series_flow: TimeSeriesBucketItem[];
  lane_analysis: {
    is_available: boolean;
    items: LaneMetricItem[];
    uncalibrated_warning: string;
  };
  anomalies: {
    is_available: boolean;
    total_anomalies: number;
    items: AnomalyReportItem[];
    label: TruthLabel;
  };
  insights: {
    is_available: boolean;
    total_insights: number;
    items: InsightReportItem[];
    label: TruthLabel;
  };
  prediction_status: PredictionStatusSection;
  signal_optimization: SignalOptimizationSection;
  emergency_corridor: EmergencyCorridorSection;
  provenance: ProvenanceReportSection;
  disclaimers: DisclaimersSection;
}

export interface ReportSummary {
  id: string;
  report_type: ReportType;
  scope_type: ReportScopeType;
  session_id?: string;
  time_range_start?: string;
  time_range_end?: string;
  title: string;
  status: ReportStatus;
  format: ReportFormat;
  file_size_bytes?: number;
  provenance_summary?: any;
  created_at: string;
  completed_at?: string;
  processing_time_ms?: number;
  error_message?: string;
}

export interface ReportDetail extends ReportSummary {
  report_data?: TrafficAnalysisReportData;
  artifact_metadata?: {
    sha256: string;
    format: string;
    file_size_bytes: number;
    filename: string;
  };
}

export interface ReportListResponse {
  items: ReportSummary[];
  total: number;
  skip: number;
  limit: number;
}

export interface CreateReportRequest {
  report_type?: string;
  scope_type?: 'session' | 'time_range';
  session_id?: string;
  time_range_start?: string;
  time_range_end?: string;
  format?: 'pdf' | 'csv' | 'json';
  title?: string;
}

export interface ReportInfoResponse {
  name: string;
  version: string;
  supported_report_types: string[];
  supported_formats: string[];
  truth_label_taxonomy: Record<string, string>;
  max_time_range_days: number;
}
