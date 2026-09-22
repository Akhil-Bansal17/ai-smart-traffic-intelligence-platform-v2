/**
 * TypeScript definitions for Historical Traffic Intelligence & Trend Analysis.
 * Phase 22: Historical Traffic Intelligence & Trend Analysis.
 */

export interface HistoricalFilterParams {
  start_time?: string;
  end_time?: string;
  time_preset?: '24h' | '7d' | '30d' | '90d' | 'custom' | string;
  camera_source_id?: string;
  session_mode?: 'file_analysis' | 'live_monitoring' | string;
  include_synthetic?: boolean;
  bucket_interval?: '15m' | '30m' | 'hourly' | 'daily' | 'weekly' | string;
}

export interface HistoricalProvenanceSummary {
  source_types: string[];
  provenance_category: string;
  provenance_label: 'REAL DATA' | 'SYNTHETIC' | 'TEST FIXTURE' | 'MIXED' | 'UNAVAILABLE' | string;
  provenance_badge_variant: 'success' | 'warning' | 'danger' | 'purple' | 'neutral' | string;
  is_synthetic: boolean;
  is_mixed: boolean;
  is_extrapolated: boolean;
  observation_duration_seconds: number;
  session_count: number;
  camera_source_count: number;
  description: string;
  mix_warning?: string | null;
}

export interface VehicleClassMetricItem {
  class_name: string;
  count: number;
  percentage: number;
  trend: 'increasing' | 'decreasing' | 'stable' | 'insufficient' | string;
  rate_per_hour: number;
}

export interface DirectionalFlowMetric {
  direction: string;
  count: number;
  percentage: number;
  flow_rate_per_hour: number;
}

export interface HistoricalBucketItem {
  bucket_index: number;
  start_time: string;
  end_time: string;
  observation_duration_seconds: number;
  observed_volume: number;
  flow_rate_per_minute: number;
  flow_rate_per_hour: number;
  is_extrapolated: boolean;
  vehicle_composition: Record<string, number>;
  inbound_count: number;
  outbound_count: number;
  session_count: number;
  source_count: number;
  provenance_type: string;
  data_status: 'observed' | 'sparse' | 'empty' | string;
}

export interface PeakPeriodItem {
  peak_type: string;
  title: string;
  start_time?: string | null;
  end_time?: string | null;
  value: number;
  unit: string;
  is_extrapolated: boolean;
  observation_duration_seconds: number;
  session_id?: string | null;
  source_name?: string | null;
  lane_name?: string | null;
  tie_breaking_applied: boolean;
  details?: string | null;
}

export interface LaneIntelligenceItem {
  lane_id: string;
  lane_name: string;
  direction_hint?: string | null;
  total_volume: number;
  average_occupancy: number;
  peak_occupancy: number;
  average_density: number;
  normalized_density_score: number;
  density_unit: string;
  density_calibration_warning?: string | null;
  volume_share_pct: number;
  session_count: number;
}

export interface AnomalyHistoryItem {
  id: string;
  anomaly_type: string;
  severity: string;
  status: string;
  title: string;
  description: string;
  metric_name: string;
  trigger_value: number;
  threshold_value: number;
  deviation_pct?: number | null;
  lane_id?: string | null;
  session_id: string;
  source_name?: string | null;
  duration_seconds: number;
  is_synthetic: boolean;
  created_at: string;
}

export interface SourceMetricItem {
  source_id: string;
  source_name: string;
  source_type: string;
  location_name?: string | null;
  session_count: number;
  total_volume: number;
  total_duration_seconds: number;
  average_flow_rate_vph: number;
  is_extrapolated: boolean;
  anomaly_count: number;
  provenance_label: string;
  is_synthetic: boolean;
}

export interface PeriodDeltaMetric {
  metric_name: string;
  current_value: number;
  previous_value: number;
  absolute_change: number;
  percentage_change?: number | null;
  trend_direction: 'up' | 'down' | 'neutral' | 'insufficient' | string;
}

export interface HistoricalSummaryResponse {
  time_range_start: string;
  time_range_end: string;
  observation_duration_seconds: number;
  total_observed_volume: number;
  flow_rate_per_minute: number;
  flow_rate_per_hour: number;
  is_extrapolated: boolean;
  inbound_volume: number;
  outbound_volume: number;
  inbound_percentage: number;
  outbound_percentage: number;
  session_count: number;
  source_count: number;
  anomaly_count: number;
  insight_count: number;
  peak_flow_rate_vph: number;
  peak_flow_period?: string | null;
  data_status: 'observed' | 'insufficient' | 'empty' | string;
  data_message: string;
  provenance: HistoricalProvenanceSummary;
}

export interface HistoricalTimeSeriesResponse {
  time_range_start: string;
  time_range_end: string;
  bucket_interval: string;
  bucket_interval_seconds: number;
  total_buckets: number;
  buckets: HistoricalBucketItem[];
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface VehicleCompositionTrendResponse {
  time_range_start: string;
  time_range_end: string;
  total_vehicles: number;
  classes: VehicleClassMetricItem[];
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface DirectionalTrendResponse {
  time_range_start: string;
  time_range_end: string;
  total_vehicles: number;
  inbound_count: number;
  outbound_count: number;
  inbound_percentage: number;
  outbound_percentage: number;
  directional_ratio: number;
  trend_direction: string;
  directions: DirectionalFlowMetric[];
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface LaneIntelligenceResponse {
  time_range_start: string;
  time_range_end: string;
  total_lanes: number;
  lanes: LaneIntelligenceItem[];
  busiest_lane_name?: string | null;
  highest_density_lane_name?: string | null;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface PeakPeriodsResponse {
  time_range_start: string;
  time_range_end: string;
  peak_flow: PeakPeriodItem;
  peak_volume: PeakPeriodItem;
  peak_density: PeakPeriodItem;
  tie_breaking_rule: string;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface AnomalyHistoryResponse {
  time_range_start: string;
  time_range_end: string;
  total_anomalies: number;
  active_anomalies: number;
  resolved_anomalies: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  incidents: AnomalyHistoryItem[];
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface SourceComparisonResponse {
  time_range_start: string;
  time_range_end: string;
  total_sources: number;
  sources: SourceMetricItem[];
  busiest_source_name?: string | null;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface PeriodComparisonResponse {
  current_start: string;
  current_end: string;
  previous_start: string;
  previous_end: string;
  volume_comparison: PeriodDeltaMetric;
  flow_rate_comparison: PeriodDeltaMetric;
  duration_comparison: PeriodDeltaMetric;
  anomaly_comparison: PeriodDeltaMetric;
  session_comparison: PeriodDeltaMetric;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}
