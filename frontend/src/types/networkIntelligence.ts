import { HistoricalProvenanceSummary, LaneIntelligenceItem, PeriodComparisonResponse } from './historicalAnalytics';

export type EpistemicStatus = 'OBSERVED' | 'DERIVED' | 'EXTRAPOLATED' | 'UNAVAILABLE';
export type ProvenanceLabel = 'REAL DATA' | 'TEST FIXTURE' | 'MIXED' | 'UNAVAILABLE';
export type DirectionalBalance = 'balanced' | 'inbound_dominant' | 'outbound_dominant';

export interface NetworkFilterParams {
  time_preset?: string;
  start_time?: string;
  end_time?: string;
  source_ids?: string[];
  include_synthetic?: boolean;
  bucket_interval?: string;
}

export interface NetworkVehicleClassItem {
  class_name: string;
  count: number;
  percentage: number;
  rate_per_hour: number;
  epistemic_status: string;
}

export interface NetworkDirectionalSummary {
  inbound_count: number;
  outbound_count: number;
  inbound_percentage: number;
  outbound_percentage: number;
  directional_ratio: number;
  balance_status: DirectionalBalance;
  epistemic_status: string;
}

export interface NetworkLaneSummary {
  total_lanes: number;
  sources_with_lanes: number;
  busiest_lane_name?: string | null;
  highest_density_lane_name?: string | null;
  average_density: number;
  density_unit: string;
  density_warning: string;
  lane_data_status: string;
  epistemic_status: string;
}

export interface NetworkOverviewResponse {
  time_range_start: string;
  time_range_end: string;
  total_sources: number;
  selected_sources_count: number;
  active_sources_count: number;
  total_volume: number;
  flow_rate_per_minute: number;
  flow_rate_per_hour: number;
  observation_duration_seconds: number;
  session_count: number;
  active_incident_count: number;
  recurring_incident_locations_count: number;
  vehicle_classes: NetworkVehicleClassItem[];
  directional_summary: NetworkDirectionalSummary;
  lane_summary: NetworkLaneSummary;
  top_hotspot_source_name?: string | null;
  epistemic_status: EpistemicStatus;
  data_status: 'observed' | 'sparse' | 'empty' | string;
  data_message: string;
  provenance: HistoricalProvenanceSummary;
}

export interface NetworkSourceComparisonItem {
  source_id: string;
  source_name: string;
  source_type: string;
  location_name?: string | null;
  status: string;
  observed_volume: number;
  flow_rate_per_hour: number;
  observation_duration_seconds: number;
  session_count: number;
  vehicle_composition: Record<string, number>;
  dominant_vehicle_class?: string | null;
  inbound_count: number;
  outbound_count: number;
  directional_balance: DirectionalBalance;
  has_lane_data: boolean;
  lane_count: number;
  average_lane_density?: number | null;
  busiest_lane_name?: string | null;
  incident_count: number;
  anomaly_count: number;
  recurring_incident_count: number;
  provenance_label: ProvenanceLabel;
  epistemic_status: EpistemicStatus;
  observation_window_start?: string | null;
  observation_window_end?: string | null;
  window_mismatch: boolean;
  window_mismatch_details?: string | null;
}

export interface NetworkSourceComparisonResponse {
  time_range_start: string;
  time_range_end: string;
  total_sources_compared: number;
  busiest_source_name?: string | null;
  highest_incident_source_name?: string | null;
  sources: NetworkSourceComparisonItem[];
  window_mismatch_detected: boolean;
  comparison_notes?: string | null;
  epistemic_status: string;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface NetworkHotspotItem {
  rank: number;
  source_id: string;
  source_name: string;
  location_name?: string | null;
  hotspot_type: 'source_hotspot' | 'intersection_hotspot' | string;
  hotspot_score: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  incident_count: number;
  recurring_incident_count: number;
  anomaly_count: number;
  observed_volume: number;
  flow_rate_per_hour: number;
  average_lane_density?: number | null;
  primary_contributing_factor: string;
  contributing_factors: string[];
  epistemic_status: string;
  provenance_label: string;
}

export interface NetworkHotspotResponse {
  time_range_start: string;
  time_range_end: string;
  total_hotspots_identified: number;
  hotspots: NetworkHotspotItem[];
  epistemic_note: string;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface NetworkVehicleCompositionResponse {
  time_range_start: string;
  time_range_end: string;
  total_vehicles: number;
  heavy_vehicle_percentage: number;
  network_dominant_class?: string | null;
  classes: NetworkVehicleClassItem[];
  source_composition: Record<string, Record<string, number>>;
  source_dominant_classes: Record<string, string>;
  epistemic_status: string;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface NetworkDirectionalSourceItem {
  source_id: string;
  source_name: string;
  location_name?: string | null;
  inbound_count: number;
  outbound_count: number;
  inbound_percentage: number;
  outbound_percentage: number;
  directional_ratio: number;
  balance_status: DirectionalBalance;
}

export interface NetworkDirectionalResponse {
  time_range_start: string;
  time_range_end: string;
  network_summary: NetworkDirectionalSummary;
  sources: NetworkDirectionalSourceItem[];
  inbound_dominant_count: number;
  outbound_dominant_count: number;
  balanced_count: number;
  epistemic_status: string;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface NetworkLaneResponse {
  time_range_start: string;
  time_range_end: string;
  total_lanes: number;
  sources_with_lanes_count: number;
  sources_without_lanes_count: number;
  lanes: LaneIntelligenceItem[];
  busiest_lane_name?: string | null;
  highest_density_lane_name?: string | null;
  density_calibration_disclaimer: string;
  epistemic_status: string;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export interface NetworkTemporalBucketSourceItem {
  source_id: string;
  source_name: string;
  volume: number;
  flow_rate_per_hour: number;
}

export interface NetworkTemporalBucket {
  bucket_index: number;
  start_time: string;
  end_time: string;
  total_volume: number;
  sources: NetworkTemporalBucketSourceItem[];
  active_sources_count: number;
  is_network_peak: boolean;
}

export interface NetworkTemporalAnalysisResponse {
  time_range_start: string;
  time_range_end: string;
  bucket_interval: string;
  total_buckets: number;
  buckets: NetworkTemporalBucket[];
  synchronized_peak_buckets_count: number;
  epistemic_note: string;
  epistemic_status: string;
  data_status: string;
  provenance: HistoricalProvenanceSummary;
}

export type { PeriodComparisonResponse };
