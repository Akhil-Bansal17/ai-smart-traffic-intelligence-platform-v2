"""
Domain models and dataclasses for Emergency Corridor Simulation & Signal Priority.
Phase 13: Emergency Corridor Simulation.

Defines corridor topology, emergency vehicle configuration, signal priority windows,
multi-intersection coordination timelines, and trade-off performance metrics.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.services.simulation.models import (
    ApproachConfig,
    ApproachDemand,
    IntersectionConfig,
    LevelOfService,
    PhaseTiming,
    SignalPhaseConfig,
    SignalPlan,
    compute_los,
)


class EmergencyVehicleType(str, Enum):
    AMBULANCE = "ambulance"
    FIRE_TRUCK = "fire_truck"
    POLICE = "police"
    RESCUE = "rescue"


class PriorityStrategyType(str, Enum):
    GREEN_EXTENSION_EARLY_GREEN = "green_extension_early_green"
    GREEN_WAVE_PROGRESSION = "green_wave_progression"


class RecoveryStrategyType(str, Enum):
    SMOOTH_COMPENSATION = "smooth_compensation"
    IMMEDIATE_RESUME = "immediate_resume"


class SignalPriorityAction(str, Enum):
    NONE = "none"
    GREEN_EXTENSION = "green_extension"
    EARLY_GREEN = "early_green"
    HOLD_GREEN = "hold_green"
    RECOVERY = "recovery"


@dataclass
class CorridorNodeConfig:
    """Configuration for a single intersection along an emergency corridor."""
    node_id: str  # e.g. "node_1", "node_int_A"
    intersection: IntersectionConfig
    corridor_approach_id: str  # Entry approach along corridor (e.g. "south" for Northbound travel)
    exit_approach_id: str  # Exit approach along corridor (e.g. "north")
    corridor_phase_id: str  # Signal phase serving the corridor movement (e.g. "phase_A_NS")
    distance_to_next_node_m: float = 0.0  # Distance in meters to next intersection (0 for terminus)
    free_flow_speed_kmh: float = 50.0  # Segment free-flow speed limit
    demands: List[ApproachDemand] = field(default_factory=list)

    def get_corridor_approach(self) -> Optional[ApproachConfig]:
        return self.intersection.get_approach(self.corridor_approach_id)

    def get_corridor_phase(self) -> Optional[SignalPhaseConfig]:
        for phase in self.intersection.phases:
            if phase.phase_id == self.corridor_phase_id:
                return phase
        return None

    def get_conflicting_phases(self) -> List[SignalPhaseConfig]:
        return [p for p in self.intersection.phases if p.phase_id != self.corridor_phase_id]


@dataclass
class EmergencyVehicleConfig:
    """Simulated emergency vehicle properties and response scenario."""
    vehicle_id: str = "EMV-MED-01"
    vehicle_type: EmergencyVehicleType = EmergencyVehicleType.AMBULANCE
    origin_node_id: str = "node_1"
    destination_node_id: str = "node_3"
    dispatch_time_seconds: float = 0.0  # Time offset when vehicle starts trip
    cruising_speed_kmh: float = 60.0  # Target cruise speed without signal delay
    priority_level: str = "high"  # "high", "critical"
    vehicle_length_m: float = 6.5
    data_provenance: str = "simulation_configured"  # Never labeled as real detected vehicle


@dataclass
class CorridorConfig:
    """Full corridor definition consisting of ordered sequence of intersection nodes."""
    corridor_id: str
    name: str
    description: str = ""
    nodes: List[CorridorNodeConfig] = field(default_factory=list)

    @property
    def total_distance_meters(self) -> float:
        return sum(node.distance_to_next_node_m for node in self.nodes)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    def get_node(self, node_id: str) -> Optional[CorridorNodeConfig]:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None


@dataclass
class PriorityWindow:
    """Computed signal priority activation window for a single intersection node."""
    node_id: str
    estimated_arrival_seconds: float
    queue_clearance_lead_time_seconds: float
    clearance_window_seconds: float
    priority_start_seconds: float
    priority_end_seconds: float
    action_applied: SignalPriorityAction
    green_extension_seconds: float = 0.0
    early_green_seconds: float = 0.0
    recovery_duration_seconds: float = 0.0
    max_priority_green_cap_seconds: float = 80.0


@dataclass
class NodeSimulationTimeline:
    """Detailed simulation timeline and performance comparison for a single corridor node."""
    node_id: str
    intersection_id: str
    intersection_name: str
    sequence_index: int
    distance_from_origin_m: float
    estimated_arrival_seconds: float
    estimated_departure_seconds: float
    baseline_signal_state_at_arrival: str  # "green", "yellow", "red"
    priority_signal_state_at_arrival: str  # "green"
    baseline_delay_seconds: float
    priority_delay_seconds: float
    delay_savings_seconds: float
    cross_street_baseline_delay: float
    cross_street_priority_delay: float
    cross_street_delay_delta: float
    queue_cleared_vehicles: float
    priority_window: PriorityWindow
    recovery_cycles_needed: int
    baseline_plan: SignalPlan
    priority_plan: SignalPlan
    recovery_plan: SignalPlan


@dataclass
class CorridorPerformanceMetrics:
    """Aggregate baseline vs emergency priority performance metrics and trade-off KPIs."""
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
    cross_street_delay_impact_pct: float  # Percentage change in cross-street delay (honest trade-off)
    average_progression_speed_kmh_baseline: float
    average_progression_speed_kmh_priority: float
    total_interventions_count: int
    total_recovery_duration_seconds: float
    corridor_los_baseline: LevelOfService
    corridor_los_priority: LevelOfService


@dataclass
class CorridorSimulationResult:
    """Complete output of an Emergency Corridor Simulation run."""
    run_id: str
    corridor_config: CorridorConfig
    vehicle_scenario: EmergencyVehicleConfig
    strategy_type: PriorityStrategyType
    recovery_strategy: RecoveryStrategyType
    data_source: str
    metrics: CorridorPerformanceMetrics
    node_timelines: List[NodeSimulationTimeline]
    simulation_notes: List[str]
    execution_time_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
