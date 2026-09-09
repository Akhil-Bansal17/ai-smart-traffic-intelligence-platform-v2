"""
Pydantic v2 Schemas for Traffic Signal Optimization Simulation.
Phase 12: Traffic Signal Optimization Simulation.

Ensures rigorous validation, type safety, and clean JSON serialization
without exposing server paths or raw exceptions.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.services.simulation.models import (
    IntersectionType,
    LevelOfService,
    OptimizationAlgorithm,
)


class ApproachConfigSchema(BaseModel):
    """Configuration for a single intersection approach direction."""
    model_config = ConfigDict(from_attributes=True)

    approach_id: str = Field(..., description="Unique approach identifier (e.g. north, south, east, west)")
    name: str = Field(..., description="Human-readable name of the approach")
    lanes: int = Field(default=1, ge=1, le=8, description="Number of active lanes")
    saturation_flow_rate_per_lane: float = Field(
        default=1800.0,
        ge=500.0,
        le=2400.0,
        description="Saturation flow rate per lane (veh/hr/lane)",
    )
    target_speed_kmh: float = Field(default=50.0, ge=10.0, le=120.0, description="Approach design speed (km/h)")


class ApproachDemandSchema(BaseModel):
    """Traffic arrival volume for an approach."""
    model_config = ConfigDict(from_attributes=True)

    approach_id: str = Field(..., description="Approach identifier")
    vehicle_flow_rate_vph: float = Field(..., ge=0.0, le=10000.0, description="Arrival flow rate in vehicles/hour")
    vehicle_count: int = Field(default=0, ge=0, description="Deduplicated vehicle count")
    inbound_count: int = Field(default=0, ge=0, description="Inbound crossing count")
    outbound_count: int = Field(default=0, ge=0, description="Outbound crossing count")
    heavy_vehicle_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Heavy vehicle percentage (bus/truck)")
    data_provenance: str = Field(
        default="simulation_configured",
        description="Provenance: 'real_database_metrics', 'synthetic_pipeline_metrics', 'simulation_configured', or 'synthetic_fixture'",
    )


class SignalPhaseConfigSchema(BaseModel):
    """Signal phase timing parameters and controlled approach movements."""
    model_config = ConfigDict(from_attributes=True)

    phase_id: str = Field(..., description="Phase identifier (e.g. phase_A_NS, phase_B_EW)")
    name: str = Field(..., description="Descriptive name of the phase")
    controlled_approaches: List[str] = Field(..., min_length=1, description="List of approach IDs served by this phase")
    min_green_seconds: float = Field(default=10.0, ge=5.0, le=60.0, description="Minimum safe green duration")
    max_green_seconds: float = Field(default=65.0, ge=10.0, le=180.0, description="Maximum allowable green duration")
    yellow_seconds: float = Field(default=4.0, ge=2.0, le=10.0, description="Yellow change clearance duration")
    all_red_seconds: float = Field(default=2.0, ge=0.0, le=10.0, description="All-red intersection clearance duration")


class IntersectionConfigSchema(BaseModel):
    """Full geometric and phase specification of an intersection."""
    model_config = ConfigDict(from_attributes=True)

    intersection_id: str = Field(default="int_custom", description="Intersection identifier")
    name: str = Field(default="Custom Intersection", description="Intersection name")
    intersection_type: IntersectionType = Field(default=IntersectionType.FOUR_WAY)
    approaches: List[ApproachConfigSchema] = Field(..., min_length=1, max_length=8)
    phases: List[SignalPhaseConfigSchema] = Field(..., min_length=2, max_length=8)
    cycle_length_min_seconds: float = Field(default=45.0, ge=30.0, le=180.0)
    cycle_length_max_seconds: float = Field(default=120.0, ge=45.0, le=240.0)
    target_cycle_length_seconds: Optional[float] = Field(default=90.0, ge=30.0, le=240.0)


class PhaseTimingSchema(BaseModel):
    """Duration allocation for a phase in a signal plan."""
    model_config = ConfigDict(from_attributes=True)

    phase_id: str
    name: str
    controlled_approaches: List[str]
    green_seconds: float
    yellow_seconds: float
    all_red_seconds: float
    total_phase_seconds: float
    split_percentage: float


class SignalPlanSchema(BaseModel):
    """Timing plan representing cycle length, green split, and lost times."""
    model_config = ConfigDict(from_attributes=True)

    plan_id: str
    plan_type: str  # "baseline" or "optimized"
    cycle_length_seconds: float
    total_green_seconds: float
    total_lost_seconds: float
    phase_timings: List[PhaseTimingSchema]
    algorithm_name: str
    description: str = ""


class ApproachPerformanceSchema(BaseModel):
    """Performance evaluation for an approach."""
    model_config = ConfigDict(from_attributes=True)

    approach_id: str
    name: str
    demand_flow_rate_vph: float
    allocated_green_seconds: float
    cycle_length_seconds: float
    green_ratio: float
    capacity_vph: float
    degree_of_saturation_x: float
    estimated_delay_seconds: float
    estimated_queue_vehicles: float
    los_grade: LevelOfService


class SimulationMetricsSchema(BaseModel):
    """Aggregated performance metrics across all approaches."""
    model_config = ConfigDict(from_attributes=True)

    cycle_length_seconds: float
    total_green_seconds: float
    average_delay_seconds_per_vehicle: float
    total_queue_vehicles: float
    throughput_capacity_vph: float
    critical_v_c_ratio: float
    intersection_los: LevelOfService
    objective_score: float
    approach_performances: List[ApproachPerformanceSchema]


class PhaseComparisonSchema(BaseModel):
    """Granular comparison of baseline vs optimized green time per phase."""
    model_config = ConfigDict(from_attributes=True)

    phase_id: str
    name: str
    controlled_approaches: List[str]
    baseline_green_seconds: float
    optimized_green_seconds: float
    green_delta_seconds: float
    baseline_split_pct: float
    optimized_split_pct: float
    split_delta_pct: float


class ApproachComparisonSchema(BaseModel):
    """Granular before/after comparison of approach delay, queue, and LOS."""
    model_config = ConfigDict(from_attributes=True)

    approach_id: str
    name: str
    demand_vph: float
    baseline_green_seconds: float
    optimized_green_seconds: float
    baseline_delay_seconds: float
    optimized_delay_seconds: float
    delay_delta_seconds: float
    delay_reduction_pct: float
    baseline_queue_vehicles: float
    optimized_queue_vehicles: float
    queue_delta_vehicles: float
    baseline_los: LevelOfService
    optimized_los: LevelOfService


class SignalOptimizationInfoResponse(BaseModel):
    """Pipeline metadata, supported algorithms, mathematical objective descriptions, and safety disclaimers."""
    service_name: str = "TrafficSignalOptimizationEngine"
    version: str = "0.1.0"
    is_simulation: bool = True
    disclaimer: str = "This system provides traffic signal optimization simulation and decision support; it does not directly control physical traffic signals."
    supported_algorithms: List[str] = Field(
        default_factory=lambda: [
            "demand_proportional",
            "webster_optimal",
            "constrained_delay_minimization",
        ]
    )
    default_algorithm: str = "demand_proportional"
    objective_function_description: str = (
        "Webster's Delay Proxy: d = C*(1-g/C)^2 / [2*(1-(g/C)*x)] + x^2 / [2*q*(1-x)] "
        "with standard Highway Capacity Manual (HCM) oversaturation transition and queue estimation."
    )
    data_reality_policy: str = (
        "Strict separation of measured video analytics and simulation assumptions. "
        "Approaches outside camera FOV are transparently tagged as simulation_configured."
    )


class PresetsResponse(BaseModel):
    """Available intersection geometries and traffic demand scenarios."""
    intersections: List[Dict[str, Any]]
    scenarios: List[Dict[str, Any]]


class SignalSimulationRequest(BaseModel):
    """Request payload to execute signal optimization and simulation."""
    intersection: Optional[IntersectionConfigSchema] = None
    intersection_preset_id: Optional[str] = Field(None, description="Preset ID: 'int_4way_standard', 'int_4way_dual_lane', or 'int_3way_t_junction'")
    demands: Optional[List[ApproachDemandSchema]] = None
    demand_scenario_id: Optional[str] = Field(None, description="Demand preset ID: 'balanced_moderate', 'arterial_rush_ns', 'cross_street_surge_ew', etc.")
    session_id: Optional[str] = Field(None, description="AnalysisSession UUID to bridge measured video traffic flow")
    algorithm: OptimizationAlgorithm = Field(
        default=OptimizationAlgorithm.DEMAND_PROPORTIONAL,
        description="Optimization strategy: 'demand_proportional', 'webster_optimal', or 'constrained_delay_minimization'",
    )
    target_cycle_length: Optional[float] = Field(None, ge=30.0, le=240.0, description="Override cycle length (seconds)")
    save_to_history: bool = Field(default=True, description="Whether to persist this simulation run in history")


class SignalSimulationDetailResponse(BaseModel):
    """Complete detail response of an executed signal optimization simulation run."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: Optional[str] = None
    intersection_name: str
    intersection_type: str
    data_source: str
    algorithm_used: str
    baseline_cycle_length: float
    optimized_cycle_length: float
    baseline_delay_proxy: float
    optimized_delay_proxy: float
    delay_reduction_pct: float
    baseline_queue_proxy: float
    optimized_queue_proxy: float
    queue_reduction_pct: float
    baseline_throughput_proxy: float
    optimized_throughput_proxy: float
    throughput_increase_pct: float
    objective_improvement_pct: float
    execution_time_ms: float
    intersection_config: Dict[str, Any]
    demand_input: List[Dict[str, Any]]
    baseline_plan: Dict[str, Any]
    optimized_plan: Dict[str, Any]
    baseline_metrics: Dict[str, Any]
    optimized_metrics: Dict[str, Any]
    phase_comparisons: List[Dict[str, Any]]
    approach_comparisons: List[Dict[str, Any]]
    simulation_notes: Optional[List[str]] = None
    created_at: datetime


class SignalSimulationSummarySchema(BaseModel):
    """Overview summary for historical simulation runs list."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: Optional[str] = None
    intersection_name: str
    intersection_type: str
    data_source: str
    algorithm_used: str
    baseline_cycle_length: float
    optimized_cycle_length: float
    baseline_delay_proxy: float
    optimized_delay_proxy: float
    delay_reduction_pct: float
    objective_improvement_pct: float
    execution_time_ms: float
    created_at: datetime


class SignalSimulationListResponse(BaseModel):
    """Paginated list of historical signal optimization runs."""
    model_config = ConfigDict(from_attributes=True)

    items: List[SignalSimulationSummarySchema]
    total: int
    page: int
    page_size: int
    pages: int
