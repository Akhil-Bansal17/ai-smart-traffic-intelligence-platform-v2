"""
Pydantic v2 Schemas for Emergency Corridor Simulation & Signal Priority.
Phase 13: Emergency Corridor Simulation.

Ensures rigorous validation, type safety, and clean JSON serialization
without exposing server paths or raw exceptions.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.services.corridor.models import (
    EmergencyVehicleType,
    PriorityStrategyType,
    RecoveryStrategyType,
    SignalPriorityAction,
)
from app.services.simulation.models import LevelOfService
from app.schemas.signal_optimization import (
    ApproachConfigSchema,
    ApproachDemandSchema,
    IntersectionConfigSchema,
    PhaseTimingSchema,
    SignalPlanSchema,
)


class CorridorNodeConfigSchema(BaseModel):
    """Configuration for a single intersection node in a corridor."""
    model_config = ConfigDict(from_attributes=True)

    node_id: str = Field(..., description="Unique node identifier (e.g. node_1)")
    intersection: IntersectionConfigSchema
    corridor_approach_id: str = Field(..., description="Entry approach ID along corridor")
    exit_approach_id: str = Field(..., description="Exit approach ID along corridor")
    corridor_phase_id: str = Field(..., description="Signal phase ID serving the corridor")
    distance_to_next_node_m: float = Field(default=0.0, ge=0.0, le=50000.0, description="Distance to next intersection (m)")
    free_flow_speed_kmh: float = Field(default=50.0, ge=20.0, le=120.0, description="Segment speed limit (km/h)")
    demands: Optional[List[ApproachDemandSchema]] = Field(default=None, description="Approach traffic demand arriving at this intersection")


class EmergencyVehicleConfigSchema(BaseModel):
    """Simulated emergency vehicle parameters and response scenario."""
    model_config = ConfigDict(from_attributes=True)

    vehicle_id: str = Field(default="EMV-MED-01", description="Vehicle identifier")
    vehicle_type: EmergencyVehicleType = Field(default=EmergencyVehicleType.AMBULANCE)
    origin_node_id: str = Field(default="node_1", description="Origin node identifier")
    destination_node_id: str = Field(default="node_3", description="Destination node identifier")
    dispatch_time_seconds: float = Field(default=0.0, ge=0.0, le=3600.0, description="Trip start offset in seconds")
    cruising_speed_kmh: float = Field(default=60.0, ge=20.0, le=140.0, description="Cruising speed without signal delay (km/h)")
    priority_level: str = Field(default="high", description="Priority level: 'high' or 'critical'")
    vehicle_length_m: float = Field(default=6.5, ge=3.0, le=25.0, description="Vehicle length (meters)")
    data_provenance: str = Field(
        default="simulation_configured",
        description="Provenance: 'simulation_configured', 'synthetic_fixture', 'real_database_metrics'",
    )


class CorridorConfigSchema(BaseModel):
    """Full corridor specification consisting of ordered intersection nodes."""
    model_config = ConfigDict(from_attributes=True)

    corridor_id: str = Field(default="corridor_custom", description="Corridor identifier")
    name: str = Field(default="Custom Emergency Corridor", description="Corridor name")
    description: str = Field(default="", description="Corridor description")
    nodes: List[CorridorNodeConfigSchema] = Field(..., min_length=2, max_length=10, description="Ordered sequence of intersection nodes")


class PriorityWindowSchema(BaseModel):
    """Signal priority activation window for an intersection node."""
    model_config = ConfigDict(from_attributes=True)

    node_id: str
    estimated_arrival_seconds: float
    queue_clearance_lead_time_seconds: float
    clearance_window_seconds: float
    priority_start_seconds: float
    priority_end_seconds: float
    action_applied: SignalPriorityAction
    green_extension_seconds: float
    early_green_seconds: float
    recovery_duration_seconds: float
    max_priority_green_cap_seconds: float


class NodeSimulationTimelineSchema(BaseModel):
    """Granular simulation timeline and baseline vs priority metrics for a single node."""
    model_config = ConfigDict(from_attributes=True)

    node_id: str
    intersection_id: str
    intersection_name: str
    sequence_index: int
    distance_from_origin_m: float
    estimated_arrival_seconds: float
    estimated_departure_seconds: float
    baseline_signal_state_at_arrival: str
    priority_signal_state_at_arrival: str
    baseline_delay_seconds: float
    priority_delay_seconds: float
    delay_savings_seconds: float
    cross_street_baseline_delay: float
    cross_street_priority_delay: float
    cross_street_delay_delta: float
    queue_cleared_vehicles: float
    priority_window: PriorityWindowSchema
    recovery_cycles_needed: int
    baseline_plan: SignalPlanSchema
    priority_plan: SignalPlanSchema
    recovery_plan: SignalPlanSchema


class CorridorPerformanceMetricsSchema(BaseModel):
    """Aggregated baseline vs emergency priority metrics and trade-off KPIs."""
    model_config = ConfigDict(from_attributes=True)

    total_distance_meters: float
    baseline_corridor_travel_time_seconds: float
    priority_corridor_travel_time_seconds: float
    travel_time_savings_seconds: float
    travel_time_savings_pct: float
    baseline_emergency_delay_seconds: float
    priority_emergency_delay_seconds: float
    emergency_delay_reduction_pct: float
    baseline_cross_street_delay_avg: float
    priority_cross_street_delay_avg: float
    cross_street_delay_impact_pct: float
    average_progression_speed_kmh_baseline: float
    average_progression_speed_kmh_priority: float
    total_interventions_count: int
    total_recovery_duration_seconds: float
    corridor_los_baseline: LevelOfService
    corridor_los_priority: LevelOfService


class EmergencyCorridorInfoResponse(BaseModel):
    """Emergency Corridor simulation pipeline metadata, supported strategies, and safety disclaimers."""
    service_name: str = "EmergencyCorridorSimulationEngine"
    version: str = "0.1.0"
    is_simulation: bool = True
    disclaimer: str = (
        "This system provides emergency corridor simulation and decision support; "
        "it does not control physical traffic signals, emergency vehicles, or emergency infrastructure."
    )
    supported_strategies: List[str] = Field(
        default_factory=lambda: [
            "green_extension_early_green",
            "green_wave_progression",
        ]
    )
    supported_recovery_strategies: List[str] = Field(
        default_factory=lambda: [
            "smooth_compensation",
            "immediate_resume",
        ]
    )
    supported_vehicle_types: List[str] = Field(
        default_factory=lambda: [
            "ambulance",
            "fire_truck",
            "police",
            "rescue",
        ]
    )
    data_reality_policy: str = (
        "Strict segregation: Emergency vehicle scenarios are simulation inputs by default. "
        "Outputs are labeled as simulation proxies, never as physical control commands."
    )


class CorridorPresetsResponse(BaseModel):
    """Available pre-configured corridor geometries and emergency vehicle scenarios."""
    corridors: List[Dict[str, Any]]
    vehicles: List[Dict[str, Any]]


class EmergencyCorridorSimulationRequest(BaseModel):
    """Request payload to execute an Emergency Corridor Simulation."""
    corridor: Optional[CorridorConfigSchema] = None
    corridor_preset_id: Optional[str] = Field(None, description="Preset ID: 'corridor_3node_medical', 'corridor_4node_downtown', or 'corridor_2node_express'")
    vehicle: Optional[EmergencyVehicleConfigSchema] = None
    vehicle_preset_id: Optional[str] = Field(None, description="Vehicle preset ID: 'ambulance_code_3', 'fire_truck_heavy', or 'police_pursuit'")
    strategy_type: PriorityStrategyType = Field(
        default=PriorityStrategyType.GREEN_EXTENSION_EARLY_GREEN,
        description="Signal priority strategy",
    )
    recovery_strategy: RecoveryStrategyType = Field(
        default=RecoveryStrategyType.SMOOTH_COMPENSATION,
        description="Recovery timing strategy",
    )
    session_id: Optional[str] = Field(None, description="AnalysisSession UUID to bridge recorded video traffic metrics")
    save_to_history: bool = Field(default=True, description="Whether to persist simulation run to database history")


class EmergencyCorridorDetailResponse(BaseModel):
    """Complete detail response of an executed Emergency Corridor Simulation run."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: Optional[str] = None
    corridor_name: str
    corridor_nodes_count: int
    total_distance_meters: float
    vehicle_type: str
    priority_strategy: str
    recovery_strategy: str
    data_source: str
    baseline_travel_time_seconds: float
    priority_travel_time_seconds: float
    travel_time_savings_seconds: float
    travel_time_savings_pct: float
    baseline_emergency_delay_seconds: float
    priority_emergency_delay_seconds: float
    emergency_delay_reduction_pct: float
    baseline_cross_street_delay_avg: float
    priority_cross_street_delay_avg: float
    cross_street_delay_impact_pct: float
    total_recovery_duration_seconds: float
    total_interventions_count: int
    execution_time_ms: float
    corridor_config: Dict[str, Any]
    vehicle_scenario: Dict[str, Any]
    node_timelines: List[Dict[str, Any]]
    metrics_summary: Dict[str, Any]
    simulation_notes: Optional[List[str]] = None
    created_at: datetime


class EmergencyCorridorSummarySchema(BaseModel):
    """Overview summary for historical corridor simulation runs list."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: Optional[str] = None
    corridor_name: str
    corridor_nodes_count: int
    total_distance_meters: float
    vehicle_type: str
    priority_strategy: str
    recovery_strategy: str
    data_source: str
    baseline_travel_time_seconds: float
    priority_travel_time_seconds: float
    travel_time_savings_pct: float
    cross_street_delay_impact_pct: float
    execution_time_ms: float
    created_at: datetime


class EmergencyCorridorListResponse(BaseModel):
    """Paginated list of historical corridor simulation runs."""
    model_config = ConfigDict(from_attributes=True)

    items: List[EmergencyCorridorSummarySchema]
    total: int
    page: int
    page_size: int
    pages: int
