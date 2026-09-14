/**
 * TypeScript definitions for Traffic Decision Intelligence & Explainable Insights.
 * Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.
 */

export type InsightCategory =
  | 'CONGESTION'
  | 'FLOW_DEGRADATION'
  | 'LANE_IMBALANCE'
  | 'DENSITY_SPIKE'
  | 'TRAFFIC_SURGE'
  | 'UNDERUTILIZED_LANE'
  | 'OPERATIONAL_RECOMMENDATION';

export type InsightSeverity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type InsightStatus = 'NEW' | 'ACTIVE' | 'RECOVERED' | 'DISMISSED';

export type RecommendationType =
  | 'signal_retiming'
  | 'lane_management'
  | 'corridor_coordination'
  | 'capacity_warning'
  | 'monitoring_only'
  | 'none';

export interface ObservedFactor {
  label: string; // 'Observed'
  statement: string;
  metric: string;
  value: any;
  unit?: string | null;
}

export interface InferredFactor {
  label: string; // 'Inferred'
  statement: string;
  rationale: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface SimulationReference {
  simulation_id: string;
  simulation_type: 'signal_optimization' | 'emergency_corridor';
  intersection_name?: string;
  corridor_name?: string;
  algorithm_used?: string;
  vehicle_type?: string;
  delay_reduction_pct?: number;
  queue_reduction_pct?: number;
  time_saved_seconds?: number;
  travel_time_reduction_pct?: number;
  baseline_los?: string;
  optimized_los?: string;
  is_simulation: boolean;
  provenance: string;
  disclaimer: string;
}

export interface PredictionEvidence {
  is_available: boolean;
  sample_count_available?: number;
  sample_threshold_required?: number;
  status_code?: string;
  reason: string;
}

export interface EvidencePackage {
  metrics_summary?: {
    total_volume: number;
    flow_rate_per_minute: number;
    flow_rate_per_hour: number;
    is_extrapolated: boolean;
    observation_duration_seconds: number;
    total_vehicles_counted: number;
    total_vehicles_detected: number;
  };
  lane_metrics?: Array<{
    lane_id: string;
    lane_name: string;
    unique_vehicles_count: number;
    peak_occupancy: number;
    average_occupancy: number;
    normalized_density_score: number;
    image_space_density: number;
    density_unit: string;
  }>;
  anomaly_event_ids: string[];
  simulation_references: SimulationReference[];
  prediction_evidence: PredictionEvidence;
  unavailable_evidence: string[];
}

export interface TrafficInsight {
  id: string;
  session_id?: string | null;
  job_id?: string | null;
  insight_type: string;
  category: InsightCategory;
  severity: InsightSeverity;
  status: InsightStatus;
  title: string;
  summary: string;
  start_timestamp_seconds: number;
  end_timestamp_seconds?: number | null;
  duration_seconds: number;
  affected_lane_id?: string | null;
  affected_lane_name?: string | null;
  root_cause_observed?: ObservedFactor[] | null;
  root_cause_inferred?: InferredFactor[] | null;
  recommendation?: string | null;
  recommendation_rationale?: string | null;
  recommendation_type?: RecommendationType | null;
  evidence_package?: EvidencePackage | null;
  limitations?: string[] | null;
  provenance_category: string;
  is_synthetic: boolean;
  dedup_signature: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
}

export interface TrafficInsightListResponse {
  total: number;
  active_count: number;
  limit: number;
  offset: number;
  items: TrafficInsight[];
  provenance_breakdown: Record<string, number>;
}

export interface TrafficInsightDetailResponse {
  insight: TrafficInsight;
}

export interface InsightGenerateResponse {
  session_id: string;
  insights_generated: number;
  insights: TrafficInsight[];
  processing_time_ms: number;
}

export interface InsightCategoryInfo {
  category: string;
  description: string;
  supported_signals: string[];
  sample_title: string;
}

export interface InsightSeverityInfo {
  severity: string;
  criteria: string;
  color_hint: string;
}

export interface InsightInfoResponse {
  categories: InsightCategoryInfo[];
  severity_levels: InsightSeverityInfo[];
  architectural_boundaries: Record<string, string>;
  anti_fabrication_policies: string[];
}
