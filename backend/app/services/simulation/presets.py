"""
Pre-configured Intersection Geometries and Demand Scenarios.
Phase 12: Traffic Signal Optimization Simulation.

Provides standard, realistic intersection topologies and traffic flow scenarios
for interactive exploration, testing, and benchmarking.
"""
from typing import Dict, List, Tuple

from app.services.simulation.models import (
    ApproachConfig,
    ApproachDemand,
    IntersectionConfig,
    IntersectionType,
    SignalPhaseConfig,
)


def get_standard_4way_intersection() -> IntersectionConfig:
    """Standard 4-way intersection (1 lane per approach, 2-phase signal control)."""
    return IntersectionConfig(
        intersection_id="int_4way_standard",
        name="Main St & 1st Ave (4-Way Standard)",
        intersection_type=IntersectionType.FOUR_WAY,
        approaches=[
            ApproachConfig(
                approach_id="north",
                name="Northbound (Main St)",
                lanes=1,
                saturation_flow_rate_per_lane=1800.0,
                target_speed_kmh=50.0,
            ),
            ApproachConfig(
                approach_id="south",
                name="Southbound (Main St)",
                lanes=1,
                saturation_flow_rate_per_lane=1800.0,
                target_speed_kmh=50.0,
            ),
            ApproachConfig(
                approach_id="east",
                name="Eastbound (1st Ave)",
                lanes=1,
                saturation_flow_rate_per_lane=1800.0,
                target_speed_kmh=45.0,
            ),
            ApproachConfig(
                approach_id="west",
                name="Westbound (1st Ave)",
                lanes=1,
                saturation_flow_rate_per_lane=1800.0,
                target_speed_kmh=45.0,
            ),
        ],
        phases=[
            SignalPhaseConfig(
                phase_id="phase_A_NS",
                name="Phase 1: North-South Through",
                controlled_approaches=["north", "south"],
                min_green_seconds=10.0,
                max_green_seconds=65.0,
                yellow_seconds=4.0,
                all_red_seconds=2.0,
            ),
            SignalPhaseConfig(
                phase_id="phase_B_EW",
                name="Phase 2: East-West Through",
                controlled_approaches=["east", "west"],
                min_green_seconds=10.0,
                max_green_seconds=65.0,
                yellow_seconds=4.0,
                all_red_seconds=2.0,
            ),
        ],
        cycle_length_min_seconds=45.0,
        cycle_length_max_seconds=120.0,
        target_cycle_length_seconds=90.0,
    )


def get_dual_lane_4way_intersection() -> IntersectionConfig:
    """High-capacity 4-way intersection (2 lanes per approach, 2-phase control)."""
    return IntersectionConfig(
        intersection_id="int_4way_dual_lane",
        name="Grand Blvd & Central Way (4-Way Dual Lane)",
        intersection_type=IntersectionType.FOUR_WAY,
        approaches=[
            ApproachConfig(
                approach_id="north",
                name="Northbound (Grand Blvd)",
                lanes=2,
                saturation_flow_rate_per_lane=1850.0,
                target_speed_kmh=60.0,
            ),
            ApproachConfig(
                approach_id="south",
                name="Southbound (Grand Blvd)",
                lanes=2,
                saturation_flow_rate_per_lane=1850.0,
                target_speed_kmh=60.0,
            ),
            ApproachConfig(
                approach_id="east",
                name="Eastbound (Central Way)",
                lanes=2,
                saturation_flow_rate_per_lane=1800.0,
                target_speed_kmh=50.0,
            ),
            ApproachConfig(
                approach_id="west",
                name="Westbound (Central Way)",
                lanes=2,
                saturation_flow_rate_per_lane=1800.0,
                target_speed_kmh=50.0,
            ),
        ],
        phases=[
            SignalPhaseConfig(
                phase_id="phase_A_NS",
                name="Phase 1: North-South Arterial",
                controlled_approaches=["north", "south"],
                min_green_seconds=15.0,
                max_green_seconds=80.0,
                yellow_seconds=4.5,
                all_red_seconds=2.5,
            ),
            SignalPhaseConfig(
                phase_id="phase_B_EW",
                name="Phase 2: East-West Collector",
                controlled_approaches=["east", "west"],
                min_green_seconds=10.0,
                max_green_seconds=60.0,
                yellow_seconds=4.0,
                all_red_seconds=2.0,
            ),
        ],
        cycle_length_min_seconds=50.0,
        cycle_length_max_seconds=140.0,
        target_cycle_length_seconds=100.0,
    )


def get_3way_t_intersection() -> IntersectionConfig:
    """3-way T-junction (East-West through corridor with North stem approach)."""
    return IntersectionConfig(
        intersection_id="int_3way_t_junction",
        name="Harbor Hwy & Pier Access Rd (3-Way T-Junction)",
        intersection_type=IntersectionType.THREE_WAY_T,
        approaches=[
            ApproachConfig(
                approach_id="east",
                name="Eastbound (Harbor Hwy)",
                lanes=2,
                saturation_flow_rate_per_lane=1900.0,
                target_speed_kmh=60.0,
            ),
            ApproachConfig(
                approach_id="west",
                name="Westbound (Harbor Hwy)",
                lanes=2,
                saturation_flow_rate_per_lane=1900.0,
                target_speed_kmh=60.0,
            ),
            ApproachConfig(
                approach_id="north",
                name="Southbound (Pier Access Rd)",
                lanes=1,
                saturation_flow_rate_per_lane=1700.0,
                target_speed_kmh=40.0,
            ),
        ],
        phases=[
            SignalPhaseConfig(
                phase_id="phase_EW_THRU",
                name="Phase 1: Harbor Hwy East-West Through",
                controlled_approaches=["east", "west"],
                min_green_seconds=15.0,
                max_green_seconds=75.0,
                yellow_seconds=4.0,
                all_red_seconds=2.0,
            ),
            SignalPhaseConfig(
                phase_id="phase_N_STEM",
                name="Phase 2: Pier Access Stem Ingress",
                controlled_approaches=["north"],
                min_green_seconds=10.0,
                max_green_seconds=45.0,
                yellow_seconds=3.5,
                all_red_seconds=2.0,
            ),
        ],
        cycle_length_min_seconds=40.0,
        cycle_length_max_seconds=110.0,
        target_cycle_length_seconds=80.0,
    )


# Standard demand scenarios
SCENARIO_DEMANDS: Dict[str, Dict[str, float]] = {
    "balanced_moderate": {
        "north": 450.0,
        "south": 450.0,
        "east": 450.0,
        "west": 450.0,
    },
    "arterial_rush_ns": {
        "north": 1150.0,
        "south": 980.0,
        "east": 240.0,
        "west": 210.0,
    },
    "cross_street_surge_ew": {
        "north": 280.0,
        "south": 310.0,
        "east": 1220.0,
        "west": 1140.0,
    },
    "asymmetric_bottleneck": {
        "north": 1380.0,
        "south": 350.0,
        "east": 200.0,
        "west": 180.0,
    },
    "low_volume_night": {
        "north": 110.0,
        "south": 95.0,
        "east": 80.0,
        "west": 85.0,
    },
}


def build_demand_list(
    scenario_key: str,
    approach_ids: List[str],
    provenance: str = "simulation_configured",
) -> List[ApproachDemand]:
    """Builds a list of ApproachDemand objects for the specified scenario and approach set."""
    flow_map = SCENARIO_DEMANDS.get(scenario_key, SCENARIO_DEMANDS["balanced_moderate"])
    demands: List[ApproachDemand] = []

    for a_id in approach_ids:
        flow = flow_map.get(a_id, 300.0)
        demands.append(
            ApproachDemand(
                approach_id=a_id,
                vehicle_flow_rate_vph=flow,
                vehicle_count=int(flow / 12),  # Equivalent 5-minute count
                inbound_count=int(flow / 12),
                outbound_count=0,
                heavy_vehicle_percentage=4.0,
                data_provenance=provenance,
            )
        )

    return demands


def get_all_intersection_presets() -> List[Dict[str, any]]:
    """Returns metadata for all available intersection presets."""
    return [
        {
            "id": "int_4way_standard",
            "name": "Main St & 1st Ave (4-Way Standard)",
            "type": "four_way",
            "description": "Standard 4-approach urban collector with 1 lane per approach and 2-phase timing.",
            "approaches_count": 4,
            "phases_count": 2,
            "default_cycle": 90.0,
        },
        {
            "id": "int_4way_dual_lane",
            "name": "Grand Blvd & Central Way (4-Way Dual Lane)",
            "type": "four_way",
            "description": "High-capacity suburban arterial intersection with 2 lanes per approach.",
            "approaches_count": 4,
            "phases_count": 2,
            "default_cycle": 100.0,
        },
        {
            "id": "int_3way_t_junction",
            "name": "Harbor Hwy & Pier Access Rd (3-Way T-Junction)",
            "type": "three_way_t",
            "description": "3-approach T-junction prioritizing high-speed East-West highway flow.",
            "approaches_count": 3,
            "phases_count": 2,
            "default_cycle": 80.0,
        },
    ]


def get_all_scenario_presets() -> List[Dict[str, any]]:
    """Returns metadata for all available demand scenario presets."""
    return [
        {
            "id": "balanced_moderate",
            "name": "Balanced Moderate Traffic (450 vph / approach)",
            "description": "Equal traffic distribution across all approaches; tests baseline parity.",
        },
        {
            "id": "arterial_rush_ns",
            "name": "North-South Morning Peak (~1100 vph N/S vs ~220 vph E/W)",
            "description": "Heavy commuter volume along primary corridor requiring expanded green allocation.",
        },
        {
            "id": "cross_street_surge_ew",
            "name": "East-West Surge (~1200 vph E/W vs ~300 vph N/S)",
            "description": "Cross-street surge demanding reallocation of major street green time.",
        },
        {
            "id": "asymmetric_bottleneck",
            "name": "Asymmetric Bottleneck (1380 vph North vs off-peak others)",
            "description": "Severe single-direction congestion testing boundary constraint enforcement.",
        },
        {
            "id": "low_volume_night",
            "name": "Off-Peak Night Flow (~100 vph / approach)",
            "description": "Light traffic demonstrating minimum-green constraint preservation and cycle shortening.",
        },
    ]
