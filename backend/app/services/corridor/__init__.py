"""
Corridor simulation services package.
Phase 13: Emergency Corridor Simulation.
"""
from app.services.corridor.data_bridge import CorridorDataBridge
from app.services.corridor.engine import EmergencyCorridorSimulationEngine
from app.services.corridor.models import (
    CorridorConfig,
    CorridorNodeConfig,
    CorridorPerformanceMetrics,
    CorridorSimulationResult,
    EmergencyVehicleConfig,
    EmergencyVehicleType,
    NodeSimulationTimeline,
    PriorityStrategyType,
    PriorityWindow,
    RecoveryStrategyType,
    SignalPriorityAction,
)
from app.services.corridor.presets import (
    get_2node_express_corridor,
    get_3node_medical_corridor,
    get_4node_downtown_corridor,
    get_all_corridor_presets,
    get_all_vehicle_presets,
    get_preset_corridor_by_id,
)
from app.services.corridor.strategy import SignalPriorityStrategyEngine

__all__ = [
    "EmergencyVehicleType",
    "PriorityStrategyType",
    "RecoveryStrategyType",
    "SignalPriorityAction",
    "CorridorNodeConfig",
    "EmergencyVehicleConfig",
    "CorridorConfig",
    "PriorityWindow",
    "NodeSimulationTimeline",
    "CorridorPerformanceMetrics",
    "CorridorSimulationResult",
    "SignalPriorityStrategyEngine",
    "EmergencyCorridorSimulationEngine",
    "CorridorDataBridge",
    "get_3node_medical_corridor",
    "get_4node_downtown_corridor",
    "get_2node_express_corridor",
    "get_all_corridor_presets",
    "get_all_vehicle_presets",
    "get_preset_corridor_by_id",
]
