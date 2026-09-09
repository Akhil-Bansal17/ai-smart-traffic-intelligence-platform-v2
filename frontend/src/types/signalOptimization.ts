/**
 * TypeScript types for Phase 12 — Traffic Signal Optimization Simulation.
 */

export type IntersectionType = 'four_way' | 'three_way_t' | 'custom';

export type OptimizationAlgorithm =
  | 'demand_proportional'
  | 'webster_optimal'
  | 'constrained_delay_minimization';

export type LevelOfService = 'A' | 'B' | 'C' | 'D' | 'E' | 'F';

export interface ApproachConfig {
  approach_id: string;
  name: string;
  lanes: number;
  saturation_flow_rate_per_lane: number;
  target_speed_kmh: number;
}

export interface ApproachDemand {
  approach_id: string;
  vehicle_flow_rate_vph: number;
  vehicle_count?: number;
  inbound_count?: number;
  outbound_count?: number;
  heavy_vehicle_percentage?: number;
  data_provenance: string;
}

export interface SignalPhaseConfig {
  phase_id: string;
  name: string;
  controlled_approaches: string[];
  min_green_seconds: number;
  max_green_seconds: number;
  yellow_seconds: number;
  all_red_seconds: number;
}

export interface IntersectionConfig {
  intersection_id: string;
  name: string;
  intersection_type: IntersectionType;
  approaches: ApproachConfig[];
  phases: SignalPhaseConfig[];
  cycle_length_min_seconds: number;
  cycle_length_max_seconds: number;
  target_cycle_length_seconds?: number | null;
}

export interface PhaseTiming {
  phase_id: string;
  name: string;
  controlled_approaches: string[];
  green_seconds: number;
  yellow_seconds: number;
  all_red_seconds: number;
  total_phase_seconds: number;
  split_percentage: number;
}

export interface SignalPlan {
  plan_id: string;
  plan_type: 'baseline' | 'optimized';
  cycle_length_seconds: number;
  total_green_seconds: number;
  total_lost_seconds: number;
  phase_timings: PhaseTiming[];
  algorithm_name: string;
  description: string;
}

export interface ApproachPerformance {
  approach_id: string;
  name: string;
  demand_flow_rate_vph: number;
  allocated_green_seconds: number;
  cycle_length_seconds: number;
  green_ratio: number;
  capacity_vph: number;
  degree_of_saturation_x: number;
  estimated_delay_seconds: number;
  estimated_queue_vehicles: number;
  los_grade: LevelOfService;
}

export interface SimulationMetrics {
  cycle_length_seconds: number;
  total_green_seconds: number;
  average_delay_seconds_per_vehicle: number;
  total_queue_vehicles: number;
  throughput_capacity_vph: number;
  critical_v_c_ratio: number;
  intersection_los: LevelOfService;
  objective_score: number;
  approach_performances: ApproachPerformance[];
}

export interface PhaseComparison {
  phase_id: string;
  name: string;
  controlled_approaches: string[];
  baseline_green_seconds: number;
  optimized_green_seconds: number;
  green_delta_seconds: number;
  baseline_split_pct: number;
  optimized_split_pct: number;
  split_delta_pct: number;
}

export interface ApproachComparison {
  approach_id: string;
  name: string;
  demand_vph: number;
  baseline_green_seconds: number;
  optimized_green_seconds: number;
  baseline_delay_seconds: number;
  optimized_delay_seconds: number;
  delay_delta_seconds: number;
  delay_reduction_pct: number;
  baseline_queue_vehicles: number;
  optimized_queue_vehicles: number;
  queue_delta_vehicles: number;
  baseline_los: LevelOfService;
  optimized_los: LevelOfService;
}

export interface SignalOptimizationInfoResponse {
  service_name: string;
  version: string;
  is_simulation: boolean;
  disclaimer: string;
  supported_algorithms: OptimizationAlgorithm[];
  default_algorithm: OptimizationAlgorithm;
  objective_function_description: string;
  data_reality_policy: string;
}

export interface IntersectionPresetSummary {
  id: string;
  name: string;
  type: string;
  description: string;
  approaches_count: number;
  phases_count: number;
  default_cycle: number;
}

export interface ScenarioPresetSummary {
  id: string;
  name: string;
  description: string;
}

export interface PresetsResponse {
  intersections: IntersectionPresetSummary[];
  scenarios: ScenarioPresetSummary[];
}

export interface SignalSimulationRequest {
  intersection?: IntersectionConfig;
  intersection_preset_id?: string;
  demands?: ApproachDemand[];
  demand_scenario_id?: string;
  session_id?: string;
  algorithm?: OptimizationAlgorithm;
  target_cycle_length?: number;
  save_to_history?: boolean;
}

export interface SignalSimulationDetailResponse {
  id: string;
  session_id?: string | null;
  intersection_name: string;
  intersection_type: string;
  data_source: string;
  algorithm_used: OptimizationAlgorithm;
  baseline_cycle_length: number;
  optimized_cycle_length: number;
  baseline_delay_proxy: number;
  optimized_delay_proxy: number;
  delay_reduction_pct: number;
  baseline_queue_proxy: number;
  optimized_queue_proxy: number;
  queue_reduction_pct: number;
  baseline_throughput_proxy: number;
  optimized_throughput_proxy: number;
  throughput_increase_pct: number;
  objective_improvement_pct: number;
  execution_time_ms: number;
  intersection_config: any;
  demand_input: ApproachDemand[];
  baseline_plan: SignalPlan;
  optimized_plan: SignalPlan;
  baseline_metrics: SimulationMetrics;
  optimized_metrics: SimulationMetrics;
  phase_comparisons: PhaseComparison[];
  approach_comparisons: ApproachComparison[];
  simulation_notes?: string[];
  created_at: string;
}

export interface SignalSimulationSummary {
  id: string;
  session_id?: string | null;
  intersection_name: string;
  intersection_type: string;
  data_source: string;
  algorithm_used: string;
  baseline_cycle_length: number;
  optimized_cycle_length: number;
  baseline_delay_proxy: number;
  optimized_delay_proxy: number;
  delay_reduction_pct: number;
  objective_improvement_pct: number;
  execution_time_ms: number;
  created_at: string;
}

export interface SignalSimulationListResponse {
  items: SignalSimulationSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
