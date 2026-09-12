/**
 * TypeScript interfaces for Phase 15: Traffic Anomaly & Congestion Incident Detection.
 * Strictly typed with full provenance tracking, explainable rule triggers, and lifecycle states.
 */

export type AnomalyRuleType =
  | 'congestion_buildup'
  | 'flow_drop'
  | 'lane_imbalance'
  | 'density_spike';

export type AnomalySeverity = 'low' | 'medium' | 'high' | 'critical';

export type AnomalyStatus = 'open' | 'acknowledged' | 'resolved';

export interface AnomalyEvent {
  id: string;
  session_id: string;
  anomaly_type: AnomalyRuleType | string;
  severity: AnomalySeverity;
  status: AnomalyStatus;
  title: string;
  description: string;
  start_timestamp_seconds: number;
  end_timestamp_seconds?: number | null;
  duration_seconds: number;
  metric_name: string;
  trigger_value: number;
  baseline_value?: number | null;
  threshold_value: number;
  deviation_pct?: number | null;
  lane_id?: string | null;
  provenance_category: string;
  is_synthetic: boolean;
  details_json?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
}

export interface AnomalyEventListResponse {
  events: AnomalyEvent[];
  total: number;
  limit: number;
  offset: number;
  active_count: number;
  provenance_breakdown: Record<string, number>;
}

export interface AnomalyEventDetailResponse {
  event: AnomalyEvent;
  video_id?: string | null;
  video_filename?: string | null;
  video_source_type?: string | null;
  provenance_verified: boolean;
  source_reference?: string | null;
  license_reference?: string | null;
}

export interface AnomalyRuleConfigSchema {
  rule_name: string;
  anomaly_type: string;
  description: string;
  threshold_value: number;
  threshold_unit: string;
  condition_description: string;
  severity_criteria: Record<string, string>;
  caveats?: string | null;
}

export interface AnomalyInfoResponse {
  version: string;
  phase: string;
  description: string;
  terminology_disclaimer: string;
  anti_fabrication_policy: string;
  rules: AnomalyRuleConfigSchema[];
}

export interface DetectAnomaliesResponse {
  session_id: string;
  anomalies_detected: number;
  new_events_count: number;
  updated_events_count: number;
  events: AnomalyEvent[];
  execution_time_ms: number;
}

export interface UpdateAnomalyStatusRequest {
  status: AnomalyStatus;
  note?: string;
}

export interface AnomalyQueryParams {
  session_id?: string;
  anomaly_type?: string;
  severity?: string;
  status?: string;
  provenance_category?: string;
  is_synthetic?: boolean;
  limit?: number;
  offset?: number;
}
