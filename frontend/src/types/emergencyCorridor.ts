/**
 * TypeScript definitions for Emergency Corridor Simulation & Signal Priority.
 * Phase 13: Emergency Corridor Simulation.
 */
import { LevelOfService, SignalPlan } from './signalOptimization';

export type EmergencyVehicleType = 'ambulance' | 'fire_truck' | 'police' | 'rescue';

export type PriorityStrategyType = 'green_extension_early_green' | 'green_wave_progression';

export type RecoveryStrategyType = 'smooth_compensation' | 'immediate_resume';

export type SignalPriorityAction = 'none' | 'green_extension' | 'early_green' | 'hold_green' | 'recovery';

export interface CorridorNodeConfig {
  node_id: string;
  intersection: {
    intersection_id: string;
    name: string;
    intersection_type: string;
    approaches: Array<{
      approach_id: string;
      name: string;
      lanes: number;
      saturation_flow_rate_per_lane: number;
      target_speed_kmh: number;
    }>;
    phases: Array<{
      phase_id: string;
      name: string;
      controlled_approaches: string[];
      min_green_seconds: number;
      max_green_seconds: number;
      yellow_seconds: number;
      all_red_seconds: number;
    }>;
    cycle_length_min_seconds: number;
    cycle_length_max_seconds: number;
    target_cycle_length_seconds?: number;
  };
  corridor_approach_id: string;
  exit_approach_id: string;
  corridor_phase_id: string;
  distance_to_next_node_m: number;
  free_flow_speed_kmh: number;
  demands?: Array<{
    approach_id: string;
    vehicle_flow_rate_vph: number;
    vehicle_count: number;
    inbound_count: number;
    outbound_count: number;
    heavy_vehicle_percentage: number;
    data_provenance: string;
  }>;
}

export interface EmergencyVehicleConfig {
  vehicle_id: string;
  vehicle_type: EmergencyVehicleType;
  origin_node_id: string;
  destination_node_id: string;
  dispatch_time_seconds: number;
  cruising_speed_kmh: number;
  priority_level: string;
  vehicle_length_m: number;
  data_provenance: string;
}

export interface CorridorConfig {
  corridor_id: string;
  name: string;
  description: string;
  node_count?: number;
  total_distance_meters?: number;
  nodes: CorridorNodeConfig[];
}

export interface PriorityWindow {
  node_id: string;
  estimated_arrival_seconds: number;
  queue_clearance_lead_time_seconds: number;
  clearance_window_seconds: number;
  priority_start_seconds: number;
  priority_end_seconds: number;
  action_applied: SignalPriorityAction;
  green_extension_seconds: number;
  early_green_seconds: number;
  recovery_duration_seconds: number;
  max_priority_green_cap_seconds: number;
}

export interface NodeSimulationTimeline {
  node_id: string;
  intersection_id: string;
  intersection_name: string;
  sequence_index: number;
  distance_from_origin_m: number;
  estimated_arrival_seconds: number;
  estimated_departure_seconds: number;
  baseline_signal_state_at_arrival: 'green' | 'yellow' | 'red';
  priority_signal_state_at_arrival: string;
  baseline_delay_seconds: number;
  priority_delay_seconds: number;
  delay_savings_seconds: number;
  cross_street_baseline_delay: number;
  cross_street_priority_delay: number;
  cross_street_delay_delta: number;
  queue_cleared_vehicles: number;
  priority_window: PriorityWindow;
  recovery_cycles_needed: number;
  baseline_plan: SignalPlan;
  priority_plan: SignalPlan;
  recovery_plan: SignalPlan;
}

export interface CorridorPerformanceMetrics {
  total_distance_meters: number;
  baseline_corridor_travel_time_seconds: number;
  priority_corridor_travel_time_seconds: number;
  travel_time_savings_seconds: number;
  travel_time_savings_pct: number;
  baseline_emergency_delay_seconds: number;
  priority_emergency_delay_seconds: number;
  emergency_delay_reduction_pct: number;
  baseline_cross_street_delay_avg: number;
  priority_cross_street_delay_avg: number;
  cross_street_delay_impact_pct: number;
  average_progression_speed_kmh_baseline: number;
  average_progression_speed_kmh_priority: number;
  total_interventions_count: number;
  total_recovery_duration_seconds: number;
  corridor_los_baseline: LevelOfService;
  corridor_los_priority: LevelOfService;
}

export interface EmergencyCorridorInfoResponse {
  service_name: string;
  version: string;
  is_simulation: boolean;
  disclaimer: string;
  supported_strategies: string[];
  supported_recovery_strategies: string[];
  supported_vehicle_types: string[];
  data_reality_policy: string;
}

export interface CorridorPresetItem {
  corridor_id: string;
  name: string;
  description: string;
  node_count: number;
  total_distance_meters: number;
  nodes: Array<{
    node_id: string;
    intersection_id: string;
    intersection_name: string;
    corridor_approach_id: string;
    exit_approach_id: string;
    corridor_phase_id: string;
    distance_to_next_node_m: number;
    free_flow_speed_kmh: number;
  }>;
}

export interface VehiclePresetItem {
  preset_id: string;
  name: string;
  vehicle_type: EmergencyVehicleType;
  cruising_speed_kmh: number;
  dispatch_time_seconds: number;
  priority_level: string;
  description: string;
}

export interface CorridorPresetsResponse {
  corridors: CorridorPresetItem[];
  vehicles: VehiclePresetItem[];
}

export interface EmergencyCorridorSimulationRequest {
  corridor?: CorridorConfig;
  corridor_preset_id?: string;
  vehicle?: Partial<EmergencyVehicleConfig>;
  vehicle_preset_id?: string;
  strategy_type?: PriorityStrategyType;
  recovery_strategy?: RecoveryStrategyType;
  session_id?: string;
  save_to_history?: boolean;
}

export interface EmergencyCorridorDetailResponse {
  id: string;
  session_id?: string | null;
  corridor_name: string;
  corridor_nodes_count: number;
  total_distance_meters: number;
  vehicle_type: string;
  priority_strategy: string;
  recovery_strategy: string;
  data_source: string;
  baseline_travel_time_seconds: number;
  priority_travel_time_seconds: number;
  travel_time_savings_seconds: number;
  travel_time_savings_pct: number;
  baseline_emergency_delay_seconds: number;
  priority_emergency_delay_seconds: number;
  emergency_delay_reduction_pct: number;
  baseline_cross_street_delay_avg: number;
  priority_cross_street_delay_avg: number;
  cross_street_delay_impact_pct: number;
  total_recovery_duration_seconds: number;
  total_interventions_count: number;
  execution_time_ms: number;
  corridor_config: any;
  vehicle_scenario: any;
  node_timelines: NodeSimulationTimeline[];
  metrics_summary: CorridorPerformanceMetrics;
  simulation_notes?: string[] | null;
  created_at: string;
}

export interface EmergencyCorridorSummary {
  id: string;
  session_id?: string | null;
  corridor_name: string;
  corridor_nodes_count: number;
  total_distance_meters: number;
  vehicle_type: string;
  priority_strategy: string;
  recovery_strategy: string;
  data_source: string;
  baseline_travel_time_seconds: number;
  priority_travel_time_seconds: number;
  travel_time_savings_pct: number;
  cross_street_delay_impact_pct: number;
  execution_time_ms: number;
  created_at: string;
}

export interface EmergencyCorridorListResponse {
  items: EmergencyCorridorSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
