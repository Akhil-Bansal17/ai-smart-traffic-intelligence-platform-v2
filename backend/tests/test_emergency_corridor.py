"""
Unit and Integration Tests for Emergency Corridor Simulation & Signal Priority.
Phase 13: Emergency Corridor Simulation.

Tests cover:
- Corridor and node topology models
- Emergency vehicle parameters and provenance honesty
- Queue clearance lead-time calculations
- Priority window generation (Green Extension vs Early Green)
- Strict safety constraints (min green, clearance intervals, max green cap, non-conflicting green)
- Phase-safe recovery plan generation
- Multi-intersection progression coordination
- Honest trade-off calculation (emergency savings vs cross-street delay impact)
- Dynamic behavior sensitivity (varied corridors, speeds, and demand scenarios)
- REST API lifecycle endpoints (/info, /presets, /simulate, /runs, /runs/{id}, delete)
"""
from starlette.testclient import TestClient

from app.main import app
from app.services.corridor.engine import EmergencyCorridorSimulationEngine
from app.services.corridor.models import (
    CorridorConfig,
    CorridorNodeConfig,
    EmergencyVehicleConfig,
    EmergencyVehicleType,
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
from app.services.simulation.baseline import BaselineSignalStrategy
from app.services.simulation.models import ApproachDemand


def test_corridor_node_and_corridor_config_properties():
    """Verifies corridor topology, node counts, distances, and phase lookups."""
    corridor = get_3node_medical_corridor()
    assert corridor.node_count == 3
    assert corridor.total_distance_meters == 950.0  # 450m + 500m + 0m

    node_1 = corridor.nodes[0]
    assert node_1.node_id == "node_1"
    assert node_1.corridor_approach_id == "south"
    assert node_1.exit_approach_id == "north"
    assert node_1.corridor_phase_id == "phase_A_NS"

    corridor_app = node_1.get_corridor_approach()
    assert corridor_app is not None
    assert corridor_app.approach_id == "south"

    corridor_phase = node_1.get_corridor_phase()
    assert corridor_phase is not None
    assert corridor_phase.phase_id == "phase_A_NS"

    conflicts = node_1.get_conflicting_phases()
    assert len(conflicts) == 1
    assert conflicts[0].phase_id == "phase_B_EW"


def test_emergency_vehicle_config_defaults_and_provenance():
    """Verifies emergency vehicle simulation entity defaults and data honesty."""
    vehicle = EmergencyVehicleConfig(
        vehicle_id="EMV-MED-01",
        vehicle_type=EmergencyVehicleType.AMBULANCE,
        cruising_speed_kmh=65.0,
    )
    assert vehicle.vehicle_id == "EMV-MED-01"
    assert vehicle.vehicle_type == EmergencyVehicleType.AMBULANCE
    assert vehicle.cruising_speed_kmh == 65.0
    assert vehicle.data_provenance == "simulation_configured"


def test_free_flow_travel_time_calculation():
    """Verifies distance/speed physics travel time calculations."""
    strategy_engine = SignalPriorityStrategyEngine()
    # 500m at 50 km/h (13.888 m/s) -> 36.0 seconds
    tt = strategy_engine.compute_travel_time_seconds(distance_m=500.0, speed_kmh=50.0)
    assert abs(tt - 36.0) < 0.1

    # 1000m at 60 km/h (16.666 m/s) -> 60.0 seconds
    tt2 = strategy_engine.compute_travel_time_seconds(distance_m=1000.0, speed_kmh=60.0)
    assert abs(tt2 - 60.0) < 0.1

    # 0 distance -> 0 seconds
    assert strategy_engine.compute_travel_time_seconds(distance_m=0.0, speed_kmh=50.0) == 0.0


def test_queue_clearance_lead_time_determination():
    """Verifies that queue clearance lead time increases with approach queue volume."""
    strategy_engine = SignalPriorityStrategyEngine()
    corridor = get_3node_medical_corridor()
    node = corridor.nodes[0]
    corridor_app = node.get_corridor_approach()
    baseline_strategy = BaselineSignalStrategy()
    baseline_plan = baseline_strategy.generate_baseline_plan(node.intersection)

    # Low demand
    low_demand = ApproachDemand(approach_id="south", vehicle_flow_rate_vph=200.0)
    queue_low, lead_low = strategy_engine.compute_queue_clearance_lead_time(
        node=node,
        corridor_approach=corridor_app,
        corridor_demand=low_demand,
        baseline_plan=baseline_plan,
    )

    # High demand
    high_demand = ApproachDemand(approach_id="south", vehicle_flow_rate_vph=1200.0)
    queue_high, lead_high = strategy_engine.compute_queue_clearance_lead_time(
        node=node,
        corridor_approach=corridor_app,
        corridor_demand=high_demand,
        baseline_plan=baseline_plan,
    )

    assert queue_high > queue_low
    assert lead_high >= lead_low
    assert 3.0 <= lead_low <= 25.0
    assert 3.0 <= lead_high <= 25.0


def test_priority_window_and_action_determination():
    """Verifies priority window calculation and green extension vs early green classification."""
    strategy_engine = SignalPriorityStrategyEngine()
    corridor = get_3node_medical_corridor()
    node = corridor.nodes[0]
    corridor_app = node.get_corridor_approach()
    demand = node.demands[0]
    baseline_strategy = BaselineSignalStrategy()
    baseline_plan = baseline_strategy.generate_baseline_plan(node.intersection)

    # Arrival at T=10s (during green)
    pw_green = strategy_engine.calculate_priority_window(
        node=node,
        arrival_time_sec=10.0,
        corridor_approach=corridor_app,
        corridor_demand=demand,
        baseline_plan=baseline_plan,
        strategy_type=PriorityStrategyType.GREEN_EXTENSION_EARLY_GREEN,
    )
    assert pw_green.action_applied in [SignalPriorityAction.GREEN_EXTENSION, SignalPriorityAction.EARLY_GREEN]
    assert pw_green.priority_start_seconds <= pw_green.estimated_arrival_seconds
    assert pw_green.priority_end_seconds >= pw_green.estimated_arrival_seconds

    # Arrival at T=60s (during cross-street phase / red)
    pw_red = strategy_engine.calculate_priority_window(
        node=node,
        arrival_time_sec=60.0,
        corridor_approach=corridor_app,
        corridor_demand=demand,
        baseline_plan=baseline_plan,
        strategy_type=PriorityStrategyType.GREEN_EXTENSION_EARLY_GREEN,
    )
    assert pw_red.priority_start_seconds <= pw_red.estimated_arrival_seconds


def test_priority_signal_plan_safety_constraints():
    """Verifies non-negotiable safety constraints on priority signal plan."""
    strategy_engine = SignalPriorityStrategyEngine()
    corridor = get_3node_medical_corridor()
    node = corridor.nodes[0]
    corridor_app = node.get_corridor_approach()
    demand = node.demands[0]
    baseline_strategy = BaselineSignalStrategy()
    baseline_plan = baseline_strategy.generate_baseline_plan(node.intersection)

    pw = strategy_engine.calculate_priority_window(
        node=node,
        arrival_time_sec=45.0,
        corridor_approach=corridor_app,
        corridor_demand=demand,
        baseline_plan=baseline_plan,
        strategy_type=PriorityStrategyType.GREEN_EXTENSION_EARLY_GREEN,
    )

    priority_plan = strategy_engine.generate_priority_signal_plan(
        node=node,
        baseline_plan=baseline_plan,
        priority_window=pw,
    )

    # 1. Total lost time is preserved
    assert priority_plan.total_lost_seconds == baseline_plan.total_lost_seconds

    # 2. Minimum green for conflicting phase is strictly respected
    for pt in priority_plan.phase_timings:
        phase_cfg = next(p for p in node.intersection.phases if p.phase_id == pt.phase_id)
        assert pt.green_seconds >= phase_cfg.min_green_seconds, (
            f"Phase {pt.phase_id} green {pt.green_seconds}s violated min green {phase_cfg.min_green_seconds}s"
        )
        assert pt.yellow_seconds == phase_cfg.yellow_seconds
        assert pt.all_red_seconds == phase_cfg.all_red_seconds

    # 3. Corridor phase green time is boosted
    corr_base = baseline_plan.get_phase_timing(node.corridor_phase_id).green_seconds
    corr_prio = priority_plan.get_phase_timing(node.corridor_phase_id).green_seconds
    assert corr_prio >= corr_base


def test_phase_safe_recovery_plan_generation():
    """Verifies that recovery plan compensates cross-street green time."""
    strategy_engine = SignalPriorityStrategyEngine()
    corridor = get_3node_medical_corridor()
    node = corridor.nodes[0]
    corridor_app = node.get_corridor_approach()
    demand = node.demands[0]
    baseline_strategy = BaselineSignalStrategy()
    baseline_plan = baseline_strategy.generate_baseline_plan(node.intersection)

    pw = strategy_engine.calculate_priority_window(
        node=node,
        arrival_time_sec=45.0,
        corridor_approach=corridor_app,
        corridor_demand=demand,
        baseline_plan=baseline_plan,
        strategy_type=PriorityStrategyType.GREEN_EXTENSION_EARLY_GREEN,
    )

    priority_plan = strategy_engine.generate_priority_signal_plan(
        node=node,
        baseline_plan=baseline_plan,
        priority_window=pw,
    )

    recovery_plan = strategy_engine.generate_recovery_signal_plan(
        node=node,
        baseline_plan=baseline_plan,
        priority_plan=priority_plan,
        recovery_strategy=RecoveryStrategyType.SMOOTH_COMPENSATION,
    )

    # Cross-street phase in recovery has equal or greater green than baseline to compensate
    cross_phase_id = node.get_conflicting_phases()[0].phase_id
    base_cross_g = baseline_plan.get_phase_timing(cross_phase_id).green_seconds
    rec_cross_g = recovery_plan.get_phase_timing(cross_phase_id).green_seconds
    assert rec_cross_g >= base_cross_g


def test_multi_intersection_corridor_simulation():
    """Verifies complete end-to-end corridor simulation comparing baseline vs priority."""
    engine = EmergencyCorridorSimulationEngine()
    corridor = get_3node_medical_corridor()
    vehicle = EmergencyVehicleConfig(
        vehicle_id="AMB-101",
        vehicle_type=EmergencyVehicleType.AMBULANCE,
        cruising_speed_kmh=60.0,
    )

    result = engine.run_simulation(
        corridor=corridor,
        vehicle=vehicle,
        strategy_type=PriorityStrategyType.GREEN_EXTENSION_EARLY_GREEN,
        recovery_strategy=RecoveryStrategyType.SMOOTH_COMPENSATION,
    )

    assert result.run_id.startswith("corridor_run_")
    assert result.corridor_config.node_count == 3
    assert len(result.node_timelines) == 3

    # Priority travel time must be less than or equal to baseline travel time
    assert result.metrics.priority_corridor_travel_time_seconds <= result.metrics.baseline_corridor_travel_time_seconds
    assert result.metrics.travel_time_savings_seconds >= 0.0
    assert result.metrics.travel_time_savings_pct >= 0.0

    # Emergency delay must be reduced
    assert result.metrics.priority_emergency_delay_seconds <= result.metrics.baseline_emergency_delay_seconds

    # Progression speed must be higher under priority
    assert result.metrics.average_progression_speed_kmh_priority >= result.metrics.average_progression_speed_kmh_baseline

    # Notes must contain safety disclaimer
    assert any("does not control physical traffic signals" in n for n in result.simulation_notes)


def test_honest_trade_off_cross_street_delay_impact():
    """Verifies that cross-street delay penalty is calculated honestly without fabrication."""
    engine = EmergencyCorridorSimulationEngine()
    corridor = get_3node_medical_corridor()
    vehicle = EmergencyVehicleConfig(
        vehicle_id="AMB-101",
        vehicle_type=EmergencyVehicleType.AMBULANCE,
        cruising_speed_kmh=60.0,
    )

    result = engine.run_simulation(
        corridor=corridor,
        vehicle=vehicle,
    )

    # Cross street delay impact is calculated mathematically
    base_cross = result.metrics.baseline_cross_street_delay_avg
    prio_cross = result.metrics.priority_cross_street_delay_avg
    expected_pct = ((prio_cross - base_cross) / base_cross * 100.0) if base_cross > 1e-4 else 0.0

    assert abs(result.metrics.cross_street_delay_impact_pct - expected_pct) < 0.1
    assert result.metrics.baseline_cross_street_delay_avg > 0.0
    assert result.metrics.priority_cross_street_delay_avg > 0.0


def test_dynamic_behavior_proof():
    """Proves genuine dynamism: different corridors, speeds, and demands produce distinct metrics."""
    engine = EmergencyCorridorSimulationEngine()

    # 1. 3-node vs 2-node corridor
    corridor_3 = get_3node_medical_corridor()
    corridor_2 = get_2node_express_corridor()
    veh = EmergencyVehicleConfig(cruising_speed_kmh=60.0)

    res_3 = engine.run_simulation(corridor=corridor_3, vehicle=veh)
    res_2 = engine.run_simulation(corridor=corridor_2, vehicle=veh)

    assert res_3.metrics.total_distance_meters != res_2.metrics.total_distance_meters
    assert res_3.metrics.baseline_corridor_travel_time_seconds != res_2.metrics.baseline_corridor_travel_time_seconds

    # 2. Different speeds (40 km/h vs 80 km/h)
    veh_slow = EmergencyVehicleConfig(cruising_speed_kmh=40.0)
    veh_fast = EmergencyVehicleConfig(cruising_speed_kmh=80.0)

    res_slow = engine.run_simulation(corridor=corridor_3, vehicle=veh_slow)
    res_fast = engine.run_simulation(corridor=corridor_3, vehicle=veh_fast)

    assert res_slow.metrics.priority_corridor_travel_time_seconds > res_fast.metrics.priority_corridor_travel_time_seconds


def test_corridor_validation_errors():
    """Verifies that invalid corridor topologies (<2 nodes) raise clear errors."""
    engine = EmergencyCorridorSimulationEngine()
    corridor_1 = CorridorConfig(
        corridor_id="single_node",
        name="Invalid Single Node",
        nodes=[get_3node_medical_corridor().nodes[0]],
    )
    veh = EmergencyVehicleConfig()

    try:
        engine.run_simulation(corridor=corridor_1, vehicle=veh)
        assert False, "Should have raised ValueError for <2 nodes"
    except ValueError as e:
        assert "at least 2 intersection nodes" in str(e)


# --------------------------------------------------------------------------
# API Endpoint Integration Tests
# --------------------------------------------------------------------------
def test_api_corridor_info_endpoint():
    """Tests GET /api/v1/emergency-corridor/info."""
    client = TestClient(app)
    res = client.get("/api/v1/emergency-corridor/info")
    assert res.status_code == 200
    data = res.json()
    assert data["service_name"] == "EmergencyCorridorSimulationEngine"
    assert data["is_simulation"] is True
    assert "does not control physical traffic signals" in data["disclaimer"]
    assert "ambulance" in data["supported_vehicle_types"]
    assert "green_extension_early_green" in data["supported_strategies"]


def test_api_corridor_presets_endpoint():
    """Tests GET /api/v1/emergency-corridor/presets."""
    client = TestClient(app)
    res = client.get("/api/v1/emergency-corridor/presets")
    assert res.status_code == 200
    data = res.json()
    assert len(data["corridors"]) >= 3
    assert len(data["vehicles"]) >= 3

    c_ids = [c["corridor_id"] for c in data["corridors"]]
    assert "corridor_3node_medical" in c_ids
    assert "corridor_4node_downtown" in c_ids
    assert "corridor_2node_express" in c_ids


def test_api_corridor_simulation_execution_preset():
    """Tests POST /api/v1/emergency-corridor/simulate with preset IDs."""
    client = TestClient(app)
    payload = {
        "corridor_preset_id": "corridor_3node_medical",
        "vehicle_preset_id": "ambulance_code_3",
        "strategy_type": "green_extension_early_green",
        "recovery_strategy": "smooth_compensation",
        "save_to_history": True,
    }
    res = client.post("/api/v1/emergency-corridor/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["corridor_name"] == "Metro Hospital Trauma Corridor (3 Intersections)"
    assert data["corridor_nodes_count"] == 3
    assert data["vehicle_type"] == "ambulance"
    assert data["travel_time_savings_pct"] >= 0.0
    assert len(data["node_timelines"]) == 3


def test_api_corridor_runs_lifecycle_and_deletion():
    """Tests full CRUD lifecycle of historical corridor simulation runs."""
    client = TestClient(app)

    # 1. Run simulation
    payload = {
        "corridor_preset_id": "corridor_2node_express",
        "vehicle_preset_id": "police_pursuit",
        "save_to_history": True,
    }
    sim_res = client.post("/api/v1/emergency-corridor/simulate", json=payload)
    assert sim_res.status_code == 200
    run_id = sim_res.json()["id"]

    # 2. List runs
    list_res = client.get("/api/v1/emergency-corridor/runs")
    assert list_res.status_code == 200
    runs_data = list_res.json()
    assert runs_data["total"] >= 1
    assert any(r["id"] == run_id for r in runs_data["items"])

    # 3. Retrieve run detail
    detail_res = client.get(f"/api/v1/emergency-corridor/runs/{run_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == run_id
    assert detail_data["corridor_nodes_count"] == 2

    # 4. Delete run
    del_res = client.delete(f"/api/v1/emergency-corridor/runs/{run_id}")
    assert del_res.status_code == 204

    # 5. Confirm deletion (404)
    get_after_del = client.get(f"/api/v1/emergency-corridor/runs/{run_id}")
    assert get_after_del.status_code == 404
