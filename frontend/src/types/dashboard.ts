/**
 * TypeScript type definitions for Phase 14: System-Wide Traffic Intelligence Dashboard.
 */

export type ProvenanceState = 'REAL DATA' | 'SIMULATION' | 'PREDICTION' | 'SYNTHETIC' | 'UNAVAILABLE';

export interface SectionProvenanceDetail {
  state: ProvenanceState;
  category: string;
  badge_variant: 'success' | 'info' | 'warning' | 'primary' | 'neutral';
  description: string;
}

export interface SubsystemStatusItem {
  phase: number;
  name: string;
  status: 'available' | 'degraded' | 'insufficient' | 'unavailable';
  provenance_type: string;
  note: string;
}

export interface SystemHealthSection {
  provenance: SectionProvenanceDetail;
  backend_online: boolean;
  database_connected: boolean;
  database_latency_ms: number;
  last_successful_session_at: string | null;
  last_session_id: string | null;
  subsystems: SubsystemStatusItem[];
}

export interface TrafficOverviewSection {
  provenance: SectionProvenanceDetail;
  active_session_id: string | null;
  video_filename: string | null;
  total_sessions_count: number;
  total_videos_count: number;
  total_vehicles_counted: number;
  total_vehicles_detected: number;
  observation_duration_seconds: number;
  flow_rate_per_minute: number;
  flow_rate_per_hour: number;
  is_extrapolated: boolean;
  extrapolation_note: string | null;
  started_at: string | null;
}

export interface ClassDistributionItem {
  class_name: string;
  count: number;
  percentage: number;
}

export interface VehicleCompositionSection {
  provenance: SectionProvenanceDetail;
  total_counted: number;
  class_distribution: ClassDistributionItem[];
}

export interface TimeSeriesBucketItem {
  bucket_index: number;
  start_time_seconds: number;
  end_time_seconds: number;
  count: number;
  flow_rate_per_minute: number;
}

export interface TrafficFlowSection {
  provenance: SectionProvenanceDetail;
  bucket_interval_seconds: number;
  is_extrapolated: boolean;
  time_series_buckets: TimeSeriesBucketItem[];
}

export interface LaneResultSummaryItem {
  lane_id: string;
  lane_name: string;
  direction_hint: string | null;
  unique_vehicles_count: number;
  peak_occupancy: number;
  average_occupancy: number;
  image_space_density: number;
  normalized_density_score: number;
  polygon_area_px2: number;
  vehicle_class_counts: Record<string, number> | null;
}

export interface LaneDensitySection {
  provenance: SectionProvenanceDetail;
  total_lanes_analyzed: number;
  density_unit: string;
  calibration_warning: string;
  lanes: LaneResultSummaryItem[];
}

export interface PredictionStatusSection {
  provenance: SectionProvenanceDetail;
  is_ready: boolean;
  status_code: string;
  real_sample_count: number;
  synthetic_sample_count: number;
  threshold: number;
  readiness_message: string;
  latest_run_id: string | null;
  latest_model_name: string | null;
  latest_rmse: number | null;
  latest_mae: number | null;
  latest_r2: number | null;
  latest_horizon_minutes: number | null;
  latest_created_at: string | null;
}

export interface SignalOptimizationSection {
  provenance: SectionProvenanceDetail;
  disclaimer: string;
  latest_run_id: string | null;
  intersection_name: string | null;
  intersection_type: string | null;
  algorithm_used: string | null;
  baseline_cycle_length: number | null;
  optimized_cycle_length: number | null;
  baseline_delay_proxy: number | null;
  optimized_delay_proxy: number | null;
  delay_reduction_pct: number | null;
  queue_reduction_pct: number | null;
  throughput_increase_pct: number | null;
  created_at: string | null;
}

export interface EmergencyCorridorSection {
  provenance: SectionProvenanceDetail;
  disclaimer: string;
  latest_run_id: string | null;
  corridor_name: string | null;
  corridor_nodes_count: number | null;
  vehicle_type: string | null;
  priority_strategy: string | null;
  baseline_travel_time_seconds: number | null;
  priority_travel_time_seconds: number | null;
  travel_time_savings_seconds: number | null;
  travel_time_savings_pct: number | null;
  emergency_delay_reduction_pct: number | null;
  cross_street_delay_impact_pct: number | null;
  created_at: string | null;
}

export interface HistorySessionSummaryItem {
  id: string;
  video_id: string;
  original_filename: string;
  source_type: string;
  provenance_verified: boolean;
  total_vehicles_counted: number;
  started_at: string;
  status: string;
  processing_time_ms: number | null;
}

export interface RecentHistorySection {
  provenance: SectionProvenanceDetail;
  total_sessions_count: number;
  sessions: HistorySessionSummaryItem[];
}

export interface DataProvenanceSection {
  provenance: SectionProvenanceDetail;
  active_session_id: string | null;
  video_id: string | null;
  video_filename: string | null;
  source_type: string;
  provenance_verified: boolean;
  source_reference: string | null;
  license_reference: string | null;
  provenance_note: string | null;
  captured_at: string | null;
  uploaded_at: string | null;
}

export interface DashboardSummaryResponse {
  timestamp: string;
  execution_time_ms: number;
  system_health: SystemHealthSection;
  traffic_overview: TrafficOverviewSection;
  vehicle_composition: VehicleCompositionSection;
  traffic_flow_metrics: TrafficFlowSection;
  lane_density: LaneDensitySection;
  prediction_availability: PredictionStatusSection;
  signal_optimization: SignalOptimizationSection;
  emergency_corridor: EmergencyCorridorSection;
  recent_history: RecentHistorySection;
  data_provenance: DataProvenanceSection;
}

export interface DashboardInfoResponse {
  version: string;
  phase: string;
  description: string;
  provenance_categories: string[];
  anti_trigger_guarantee: string;
}
