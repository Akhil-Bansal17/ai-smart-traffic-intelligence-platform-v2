import { HistoricalProvenanceSummary } from './historicalAnalytics';
import { TrafficInsight } from './insight';

export type CameraHealthStatus = 'ONLINE' | 'OFFLINE' | 'CONNECTING' | 'DEGRADED' | 'UNKNOWN';

export interface OperationsCameraOverviewItem {
  id: string;
  name: string;
  source_type: string;
  connection_uri_redacted: string;
  health_status: CameraHealthStatus;
  is_active: boolean;
  active_job_id?: string | null;
  fps: number;
  processing_fps: number;
  frames_acquired: number;
  frames_processed: number;
  dropped_frames: number;
  reconnect_count: number;
  current_vehicle_count: number;
  active_tracks_count: number;
  lane_occupancies: Record<string, number>;
  lane_densities: Record<string, number>;
  class_distribution: Record<string, number>;
  active_anomalies_count: number;
  provenance_tag: string;
  last_frame_timestamp?: number | null;
  last_updated?: string | null;
  error_message?: string | null;
  has_preview: boolean;
}

export interface OperationsIncidentItem {
  id: string;
  session_id: string;
  camera_source_id?: string | null;
  camera_name?: string | null;
  video_id?: string | null;
  video_filename?: string | null;
  anomaly_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'acknowledged' | 'resolved';
  title: string;
  description: string;
  metric_name: string;
  trigger_value: number;
  baseline_value?: number | null;
  threshold_value: number;
  deviation_pct?: number | null;
  lane_id?: string | null;
  duration_seconds: number;
  provenance_category: string;
  is_synthetic: boolean;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  details_json?: Record<string, any> | null;
  operator_note?: string | null;
}

export interface OperationsTrafficSnapshot {
  active_sources_count: number;
  total_active_tracks: number;
  observed_vehicle_volume: number;
  flow_rate_per_minute: number;
  flow_rate_per_hour: number;
  flow_rate_tag: 'OBSERVED' | 'EXTRAPOLATED' | 'UNAVAILABLE';
  class_distribution: Record<string, number>;
  directional_split: Record<string, number>;
  directional_ratio?: number | null;
  active_incidents_count: number;
  average_lane_occupancy: number;
  peak_lane_occupancy: number;
  observation_duration_seconds: number;
  data_status: 'OBSERVED' | 'EXTRAPOLATED' | 'UNAVAILABLE';
  traffic_density_state: 'normal' | 'moderate' | 'congested' | 'critical' | 'unavailable';
}

export interface OperationsTimelineEvent {
  id: string;
  event_type: string;
  timestamp: string;
  title: string;
  description: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  source_id?: string | null;
  source_name?: string | null;
  source_type?: string | null;
  reference_id?: string | null;
  provenance_tag: string;
}

export interface OperationsHistoricalContextResponse {
  source_id: string;
  source_name: string;
  source_type: string;
  time_window: string;
  total_volume: number;
  total_sessions: number;
  observation_duration_seconds: number;
  peak_flow_rate?: number | null;
  peak_flow_time?: string | null;
  anomaly_count: number;
  dominant_vehicle_class?: string | null;
  dominant_vehicle_share_pct?: number | null;
  inbound_outbound_ratio?: number | null;
  provenance_summary: HistoricalProvenanceSummary;
  forecast_status: string;
  forecast_reason: string;
}

export interface OperationsOverviewResponse {
  timestamp: string;
  system_health: 'healthy' | 'degraded' | 'offline';
  database_connected: boolean;
  database_latency_ms: number;
  active_cameras_count: number;
  total_cameras_count: number;
  active_incidents_count: number;
  critical_incidents_count: number;
  active_insights_count: number;
  cameras: OperationsCameraOverviewItem[];
  active_incidents: OperationsIncidentItem[];
  traffic_snapshot: OperationsTrafficSnapshot;
  insights: TrafficInsight[];
  timeline: OperationsTimelineEvent[];
  provenance_summary: HistoricalProvenanceSummary;
  simulation_support: Record<string, any>;
  prediction_support: Record<string, any>;
}

export interface OperationsIncidentListResponse {
  incidents: OperationsIncidentItem[];
  total: number;
  active_count: number;
  limit: number;
  offset: number;
}

export interface OperationsTimelineResponse {
  events: OperationsTimelineEvent[];
  total: number;
  limit: number;
}

export interface UpdateIncidentStatusRequest {
  status: 'open' | 'acknowledged' | 'resolved';
  note?: string;
}
