"""
Traffic Signal Optimization Simulation services.
Phase 12: Traffic Signal Optimization Simulation.
"""
from app.services.simulation.baseline import BaselineSignalStrategy
from app.services.simulation.data_bridge import TrafficDataBridge
from app.services.simulation.engine import SignalSimulationEngine
from app.services.simulation.models import (
    ApproachComparison,
    ApproachConfig,
    ApproachDemand,
    ApproachPerformance,
    IntersectionConfig,
    IntersectionType,
    LevelOfService,
    OptimizationAlgorithm,
    PhaseComparison,
    PhaseTiming,
    SignalPhaseConfig,
    SignalPlan,
    SignalSimulationResult,
    SimulationMetrics,
    compute_los,
)
from app.services.simulation.objective import SimulationEvaluator
from app.services.simulation.optimizer import SignalOptimizer
from app.services.simulation.presets import (
    build_demand_list,
    get_3way_t_intersection,
    get_all_intersection_presets,
    get_all_scenario_presets,
    get_dual_lane_4way_intersection,
    get_standard_4way_intersection,
)

__all__ = [
    "IntersectionType",
    "OptimizationAlgorithm",
    "LevelOfService",
    "compute_los",
    "ApproachConfig",
    "ApproachDemand",
    "SignalPhaseConfig",
    "IntersectionConfig",
    "PhaseTiming",
    "SignalPlan",
    "ApproachPerformance",
    "SimulationMetrics",
    "PhaseComparison",
    "ApproachComparison",
    "SignalSimulationResult",
    "BaselineSignalStrategy",
    "SignalOptimizer",
    "SimulationEvaluator",
    "SignalSimulationEngine",
    "TrafficDataBridge",
    "get_standard_4way_intersection",
    "get_dual_lane_4way_intersection",
    "get_3way_t_intersection",
    "get_all_intersection_presets",
    "get_all_scenario_presets",
    "build_demand_list",
]
