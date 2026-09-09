"""
Domain models and dataclasses for Traffic Signal Optimization Simulation.
Phase 12: Traffic Signal Optimization Simulation.

Defines core geometric, signal phase, demand, and evaluation models for decision-support simulation.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class IntersectionType(str, Enum):
    FOUR_WAY = "four_way"
    THREE_WAY_T = "three_way_t"
    CUSTOM = "custom"


class OptimizationAlgorithm(str, Enum):
    DEMAND_PROPORTIONAL = "demand_proportional"
    WEBSTER_OPTIMAL = "webster_optimal"
    CONSTRAINED_DELAY_MINIMIZATION = "constrained_delay_minimization"


class LevelOfService(str, Enum):
    LOS_A = "A"  # <= 10s delay
    LOS_B = "B"  # 10s - 20s delay
    LOS_C = "C"  # 20s - 35s delay
    LOS_D = "D"  # 35s - 55s delay
    LOS_E = "E"  # 55s - 80s delay
    LOS_F = "F"  # > 80s delay (oversaturated)


def compute_los(delay_seconds: float) -> LevelOfService:
    """Classifies delay into standard Highway Capacity Manual (HCM) signalized Level of Service proxy."""
    if delay_seconds <= 10.0:
        return LevelOfService.LOS_A
    elif delay_seconds <= 20.0:
        return LevelOfService.LOS_B
    elif delay_seconds <= 35.0:
        return LevelOfService.LOS_C
    elif delay_seconds <= 55.0:
        return LevelOfService.LOS_D
    elif delay_seconds <= 80.0:
        return LevelOfService.LOS_E
    else:
        return LevelOfService.LOS_F


@dataclass
class ApproachConfig:
    """Configuration for a single intersection approach direction."""
    approach_id: str  # e.g. "north", "south", "east", "west"
    name: str  # e.g. "Northbound Approach (Main St)"
    lanes: int = 1
    saturation_flow_rate_per_lane: float = 1800.0  # veh/hr/lane (standard saturation flow rate)
    target_speed_kmh: float = 50.0

    def get_total_saturation_flow(self) -> float:
        """Total saturation flow rate across all lanes on this approach (veh/hr)."""
        return max(100.0, float(self.lanes) * self.saturation_flow_rate_per_lane)


@dataclass
class ApproachDemand:
    """Traffic demand arriving at an approach."""
    approach_id: str
    vehicle_flow_rate_vph: float  # Equivalent hourly vehicle volume (veh/hr)
    vehicle_count: int = 0
    inbound_count: int = 0
    outbound_count: int = 0
    heavy_vehicle_percentage: float = 0.0
    data_provenance: str = "simulation_configured"  # real_database_metrics, synthetic_pipeline_metrics, simulation_configured, synthetic_fixture


@dataclass
class SignalPhaseConfig:
    """Configuration for a single signal phase controlling one or more approaches."""
    phase_id: str  # e.g. "phase_A_NS", "phase_B_EW"
    name: str  # e.g. "North-South Through/Right"
    controlled_approaches: List[str]  # e.g. ["north", "south"]
    min_green_seconds: float = 10.0  # Minimum safe pedestrian/vehicle green time
    max_green_seconds: float = 60.0  # Maximum green time cap
    yellow_seconds: float = 4.0  # Change interval (yellow clearance)
    all_red_seconds: float = 2.0  # Intersection clearance (all-red)

    @property
    def lost_time_seconds(self) -> float:
        """Total lost clearance time for this phase per cycle."""
        return self.yellow_seconds + self.all_red_seconds


@dataclass
class IntersectionConfig:
    """Full geometric and phase structure of a signalized intersection."""
    intersection_id: str
    name: str
    intersection_type: IntersectionType = IntersectionType.FOUR_WAY
    approaches: List[ApproachConfig] = field(default_factory=list)
    phases: List[SignalPhaseConfig] = field(default_factory=list)
    cycle_length_min_seconds: float = 45.0
    cycle_length_max_seconds: float = 120.0
    target_cycle_length_seconds: Optional[float] = 90.0

    def get_approach(self, approach_id: str) -> Optional[ApproachConfig]:
        for app in self.approaches:
            if app.approach_id == approach_id:
                return app
        return None

    def get_total_lost_time(self) -> float:
        """Total clearance lost time across all phases in a cycle."""
        return sum(p.lost_time_seconds for p in self.phases)

    def get_total_min_green(self) -> float:
        """Sum of minimum greens for all phases."""
        return sum(p.min_green_seconds for p in self.phases)


@dataclass
class PhaseTiming:
    """Specific timing duration allocated to a phase within a signal plan."""
    phase_id: str
    name: str
    controlled_approaches: List[str]
    green_seconds: float
    yellow_seconds: float
    all_red_seconds: float
    total_phase_seconds: float
    split_percentage: float  # (total_phase_seconds / cycle_length) * 100

    @property
    def effective_green_seconds(self) -> float:
        return self.green_seconds


@dataclass
class SignalPlan:
    """Complete cycle timing plan for an intersection."""
    plan_id: str
    plan_type: str  # "baseline" or "optimized"
    cycle_length_seconds: float
    total_green_seconds: float
    total_lost_seconds: float
    phase_timings: List[PhaseTiming] = field(default_factory=list)
    algorithm_name: str = "fixed_equal_baseline"
    description: str = ""

    def get_phase_timing(self, phase_id: str) -> Optional[PhaseTiming]:
        for pt in self.phase_timings:
            if pt.phase_id == phase_id:
                return pt
        return None


@dataclass
class ApproachPerformance:
    """Simulated performance metrics for a single approach under a signal plan."""
    approach_id: str
    name: str
    demand_flow_rate_vph: float
    allocated_green_seconds: float
    cycle_length_seconds: float
    green_ratio: float  # g / C
    capacity_vph: float  # s * (g / C)
    degree_of_saturation_x: float  # demand / capacity
    estimated_delay_seconds: float  # Webster delay proxy (sec/veh)
    estimated_queue_vehicles: float  # Max queue proxy per cycle
    los_grade: LevelOfService


@dataclass
class SimulationMetrics:
    """Aggregated intersection-wide performance metrics."""
    cycle_length_seconds: float
    total_green_seconds: float
    average_delay_seconds_per_vehicle: float
    total_queue_vehicles: float
    throughput_capacity_vph: float
    critical_v_c_ratio: float  # max degree of saturation across all approaches
    intersection_los: LevelOfService
    objective_score: float
    approach_performances: List[ApproachPerformance] = field(default_factory=list)


@dataclass
class PhaseComparison:
    """Comparison of baseline vs optimized green-time for a single phase."""
    phase_id: str
    name: str
    controlled_approaches: List[str]
    baseline_green_seconds: float
    optimized_green_seconds: float
    green_delta_seconds: float
    baseline_split_pct: float
    optimized_split_pct: float
    split_delta_pct: float


@dataclass
class ApproachComparison:
    """Comparison of baseline vs optimized performance for a single approach."""
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


@dataclass
class SignalSimulationResult:
    """Complete output of a signal optimization and simulation run."""
    run_id: str
    intersection: IntersectionConfig
    demands: List[ApproachDemand]
    data_source: str
    algorithm_used: OptimizationAlgorithm
    baseline_plan: SignalPlan
    optimized_plan: SignalPlan
    baseline_metrics: SimulationMetrics
    optimized_metrics: SimulationMetrics
    phase_comparisons: List[PhaseComparison]
    approach_comparisons: List[ApproachComparison]
    delay_reduction_pct: float
    queue_reduction_pct: float
    throughput_increase_pct: float
    objective_improvement_pct: float
    execution_time_ms: float
    data_provenance_summary: str
    simulation_notes: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
