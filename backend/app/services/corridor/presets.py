"""
Pre-configured Corridor Topologies and Emergency Vehicle Scenarios.
Phase 13: Emergency Corridor Simulation.

Provides realistic multi-intersection corridor geometries, vehicle dispatch scenarios,
and traffic demand distributions for exploration, testing, and benchmarking.
"""
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from app.services.corridor.models import (
    CorridorConfig,
    CorridorNodeConfig,
    EmergencyVehicleConfig,
    EmergencyVehicleType,
)
from app.services.simulation.models import (
    ApproachConfig,
    ApproachDemand,
    IntersectionConfig,
    IntersectionType,
    SignalPhaseConfig,
)
from app.services.simulation.presets import (
    build_demand_list,
    get_3way_t_intersection,
    get_dual_lane_4way_intersection,
    get_standard_4way_intersection,
)


def get_3node_medical_corridor() -> CorridorConfig:
    """3-intersection arterial corridor: Main St South -> Central Hospital."""
    int_1 = get_standard_4way_intersection()
    int_1.intersection_id = "int_node_1_1st_ave"
    int_1.name = "Main St & 1st Ave"

    int_2 = get_standard_4way_intersection()
    int_2.intersection_id = "int_node_2_2nd_ave"
    int_2.name = "Main St & 2nd Ave"

    int_3 = get_dual_lane_4way_intersection()
    int_3.intersection_id = "int_node_3_hospital"
    int_3.name = "Main St & Hospital Blvd"

    node_1 = CorridorNodeConfig(
        node_id="node_1",
        intersection=int_1,
        corridor_approach_id="south",
        exit_approach_id="north",
        corridor_phase_id="phase_A_NS",
        distance_to_next_node_m=450.0,
        free_flow_speed_kmh=50.0,
        demands=build_demand_list("balanced_moderate", ["north", "south", "east", "west"]),
    )

    node_2 = CorridorNodeConfig(
        node_id="node_2",
        intersection=int_2,
        corridor_approach_id="south",
        exit_approach_id="north",
        corridor_phase_id="phase_A_NS",
        distance_to_next_node_m=500.0,
        free_flow_speed_kmh=50.0,
        demands=build_demand_list("cross_street_surge_ew", ["north", "south", "east", "west"]),
    )

    node_3 = CorridorNodeConfig(
        node_id="node_3",
        intersection=int_3,
        corridor_approach_id="south",
        exit_approach_id="north",
        corridor_phase_id="phase_A_NS",
        distance_to_next_node_m=0.0,
        free_flow_speed_kmh=50.0,
        demands=build_demand_list("arterial_rush_ns", ["north", "south", "east", "west"]),
    )

    return CorridorConfig(
        corridor_id="corridor_3node_medical",
        name="Metro Hospital Trauma Corridor (3 Intersections)",
        description="Arterial corridor connecting South Entrance to Regional Hospital Trauma Unit with heavy cross-traffic on 2nd Ave.",
        nodes=[node_1, node_2, node_3],
    )


def get_4node_downtown_corridor() -> CorridorConfig:
    """4-intersection downtown corridor: Fire Station 4 -> Downtown Commercial District."""
    int_1 = get_standard_4way_intersection()
    int_1.intersection_id = "int_dt_1_10th"
    int_1.name = "Grand Blvd & 10th St"

    int_2 = get_dual_lane_4way_intersection()
    int_2.intersection_id = "int_dt_2_central"
    int_2.name = "Grand Blvd & Central Way"

    int_3 = get_standard_4way_intersection()
    int_3.intersection_id = "int_dt_3_market"
    int_3.name = "Grand Blvd & Market St"

    int_4 = get_3way_t_intersection()
    int_4.intersection_id = "int_dt_4_pier"
    int_4.name = "Grand Blvd & Harbor Access"

    node_1 = CorridorNodeConfig(
        node_id="node_1",
        intersection=int_1,
        corridor_approach_id="south",
        exit_approach_id="north",
        corridor_phase_id="phase_A_NS",
        distance_to_next_node_m=400.0,
        free_flow_speed_kmh=60.0,
        demands=build_demand_list("balanced_moderate", ["north", "south", "east", "west"]),
    )

    node_2 = CorridorNodeConfig(
        node_id="node_2",
        intersection=int_2,
        corridor_approach_id="south",
        exit_approach_id="north",
        corridor_phase_id="phase_A_NS",
        distance_to_next_node_m=550.0,
        free_flow_speed_kmh=60.0,
        demands=build_demand_list("arterial_rush_ns", ["north", "south", "east", "west"]),
    )

    node_3 = CorridorNodeConfig(
        node_id="node_3",
        intersection=int_3,
        corridor_approach_id="south",
        exit_approach_id="north",
        corridor_phase_id="phase_A_NS",
        distance_to_next_node_m=450.0,
        free_flow_speed_kmh=60.0,
        demands=build_demand_list("cross_street_surge_ew", ["north", "south", "east", "west"]),
    )

    node_4 = CorridorNodeConfig(
        node_id="node_4",
        intersection=int_4,
        corridor_approach_id="west",
        exit_approach_id="east",
        corridor_phase_id="phase_A_EW",
        distance_to_next_node_m=0.0,
        free_flow_speed_kmh=50.0,
        demands=build_demand_list("balanced_moderate", ["north", "east", "west"]),
    )

    return CorridorConfig(
        corridor_id="corridor_4node_downtown",
        name="Downtown Central Fire Rescue Route (4 Intersections)",
        description="High-capacity 4-intersection commercial corridor connecting Fire Station to waterfront commercial district.",
        nodes=[node_1, node_2, node_3, node_4],
    )


def get_2node_express_corridor() -> CorridorConfig:
    """2-intersection suburban expressway connector."""
    int_1 = get_dual_lane_4way_intersection()
    int_1.intersection_id = "int_exp_1_ramp"
    int_1.name = "Expressway Ramp & Arterial Way"

    int_2 = get_standard_4way_intersection()
    int_2.intersection_id = "int_exp_2_clinic"
    int_2.name = "Arterial Way & Clinic Access"

    node_1 = CorridorNodeConfig(
        node_id="node_1",
        intersection=int_1,
        corridor_approach_id="west",
        exit_approach_id="east",
        corridor_phase_id="phase_B_EW",
        distance_to_next_node_m=850.0,
        free_flow_speed_kmh=70.0,
        demands=build_demand_list("arterial_rush_ns", ["north", "south", "east", "west"]),
    )

    node_2 = CorridorNodeConfig(
        node_id="node_2",
        intersection=int_2,
        corridor_approach_id="west",
        exit_approach_id="east",
        corridor_phase_id="phase_B_EW",
        distance_to_next_node_m=0.0,
        free_flow_speed_kmh=60.0,
        demands=build_demand_list("balanced_moderate", ["north", "south", "east", "west"]),
    )

    return CorridorConfig(
        corridor_id="corridor_2node_express",
        name="Suburban Expressway Connector (2 Intersections)",
        description="Fast 2-intersection connector between Expressway Exit 12 and suburban emergency medical center.",
        nodes=[node_1, node_2],
    )


def get_all_corridor_presets() -> List[Dict[str, Any]]:
    """Returns serialized metadata of all corridor presets."""
    corridors = [
        get_3node_medical_corridor(),
        get_4node_downtown_corridor(),
        get_2node_express_corridor(),
    ]
    result = []
    for c in corridors:
        result.append({
            "corridor_id": c.corridor_id,
            "name": c.name,
            "description": c.description,
            "node_count": c.node_count,
            "total_distance_meters": c.total_distance_meters,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "intersection_id": n.intersection.intersection_id,
                    "intersection_name": n.intersection.name,
                    "corridor_approach_id": n.corridor_approach_id,
                    "exit_approach_id": n.exit_approach_id,
                    "corridor_phase_id": n.corridor_phase_id,
                    "distance_to_next_node_m": n.distance_to_next_node_m,
                    "free_flow_speed_kmh": n.free_flow_speed_kmh,
                }
                for n in c.nodes
            ],
        })
    return result


def get_all_vehicle_presets() -> List[Dict[str, Any]]:
    """Returns pre-configured emergency vehicle presets."""
    return [
        {
            "preset_id": "ambulance_code_3",
            "name": "Ambulance (Code 3 Emergency)",
            "vehicle_type": "ambulance",
            "cruising_speed_kmh": 65.0,
            "dispatch_time_seconds": 0.0,
            "priority_level": "high",
            "description": "Standard medical emergency transport with sirens/lights active.",
        },
        {
            "preset_id": "fire_truck_heavy",
            "name": "Fire Engine (Heavy Rescue Response)",
            "vehicle_type": "fire_truck",
            "cruising_speed_kmh": 55.0,
            "dispatch_time_seconds": 5.0,
            "priority_level": "critical",
            "description": "Heavy apparatus emergency dispatch with queue pre-clearance.",
        },
        {
            "preset_id": "police_pursuit",
            "name": "Police Interceptor (Urgent Call)",
            "vehicle_type": "police",
            "cruising_speed_kmh": 75.0,
            "dispatch_time_seconds": 0.0,
            "priority_level": "high",
            "description": "Fast agile response unit navigating arterial corridor.",
        },
    ]


def get_preset_corridor_by_id(corridor_id: str) -> Optional[CorridorConfig]:
    """Retrieves a corridor config by preset ID."""
    if corridor_id == "corridor_3node_medical":
        return get_3node_medical_corridor()
    elif corridor_id == "corridor_4node_downtown":
        return get_4node_downtown_corridor()
    elif corridor_id == "corridor_2node_express":
        return get_2node_express_corridor()
    return None
