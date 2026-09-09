"""
Comprehensive unit and integration tests for Phase 12: Traffic Signal Optimization Simulation.
Tests signal phase models, baseline generation, explainable optimization algorithms,
mathematical objective functions, safety constraints, dynamic demand sensitivity,
database persistence, and REST API endpoints.
"""
import math
from pathlib import Path
import tempfile
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.simulation.baseline import BaselineSignalStrategy
from app.services.simulation.data_bridge import TrafficDataBridge
from app.services.simulation.engine import SignalSimulationEngine
from app.services.simulation.models import (
    ApproachConfig,
    ApproachDemand,
    IntersectionConfig,
    IntersectionType,
    LevelOfService,
    OptimizationAlgorithm,
    SignalPhaseConfig,
    SignalPlan,
    compute_los,
)
from app.services.simulation.objective import SimulationEvaluator
from app.services.simulation.optimizer import SignalOptimizer
from app.services.simulation.presets import (
    build_demand_list,
    get_3way_t_intersection,
    get_dual_lane_4way_intersection,
    get_standard_4way_intersection,
)

# Isolated SQLite test database
TEST_DB_PATH = Path(tempfile.gettempdir()) / "test_phase12_simulation.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create test tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except OSError:
            pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def standard_intersection() -> IntersectionConfig:
    return get_standard_4way_intersection()


@pytest.fixture
def dual_lane_intersection() -> IntersectionConfig:
    return get_dual_lane_4way_intersection()


@pytest.fixture
def t_junction_intersection() -> IntersectionConfig:
    return get_3way_t_intersection()


# ==============================================================================
# 1. Signal Phase & Intersection Model Tests
# ==============================================================================

def test_signal_phase_lost_time(standard_intersection):
    """Verifies that phase lost clearance time equals yellow + all_red."""
    p1 = standard_intersection.phases[0]
    assert p1.lost_time_seconds == p1.yellow_seconds + p1.all_red_seconds
    assert p1.lost_time_seconds == 6.0


def test_intersection_total_lost_time(standard_intersection):
    """Verifies intersection total lost clearance time across all phases."""
    total_lost = standard_intersection.get_total_lost_time()
    assert total_lost == 12.0  # 2 phases * 6.0s lost time


def test_level_of_service_classification():
    """Verifies Level of Service proxy thresholds based on delay."""
    assert compute_los(5.0) == LevelOfService.LOS_A
    assert compute_los(10.0) == LevelOfService.LOS_A
    assert compute_los(15.0) == LevelOfService.LOS_B
    assert compute_los(25.0) == LevelOfService.LOS_C
    assert compute_los(45.0) == LevelOfService.LOS_D
    assert compute_los(65.0) == LevelOfService.LOS_E
    assert compute_los(95.0) == LevelOfService.LOS_F


# ==============================================================================
# 2. Baseline Signal Plan Tests
# ==============================================================================

def test_deterministic_baseline_plan_generation(standard_intersection):
    """Verifies that baseline plan divides green time equally and deterministically."""
    strategy = BaselineSignalStrategy()
    plan1 = strategy.generate_baseline_plan(standard_intersection, target_cycle_length=90.0)
    plan2 = strategy.generate_baseline_plan(standard_intersection, target_cycle_length=90.0)

    assert plan1.plan_type == "baseline"
    assert plan1.cycle_length_seconds == 90.0
    assert plan1.total_lost_seconds == 12.0
    assert plan1.total_green_seconds == 78.0

    # 2 phases -> 78 / 2 = 39s green each
    assert len(plan1.phase_timings) == 2
    assert plan1.phase_timings[0].green_seconds == 39.0
    assert plan1.phase_timings[1].green_seconds == 39.0
    assert plan1.phase_timings[0].green_seconds == plan2.phase_timings[0].green_seconds


def test_baseline_plan_cycle_clamping(standard_intersection):
    """Verifies that requested cycle lengths below min or above max are safely clamped."""
    strategy = BaselineSignalStrategy()
    # Below min (30s < 45s min)
    plan_low = strategy.generate_baseline_plan(standard_intersection, target_cycle_length=20.0)
    assert plan_low.cycle_length_seconds >= standard_intersection.cycle_length_min_seconds

    # Above max (200s > 120s max)
    plan_high = strategy.generate_baseline_plan(standard_intersection, target_cycle_length=200.0)
    assert plan_high.cycle_length_seconds <= standard_intersection.cycle_length_max_seconds


# ==============================================================================
# 3. Optimization Algorithms & Dynamic Demand Sensitivity
# ==============================================================================

def test_demand_proportional_optimization_balanced(standard_intersection):
    """Under perfectly balanced demand, optimizer should allocate equal green splits."""
    optimizer = SignalOptimizer()
    demands = [
        ApproachDemand("north", 500.0),
        ApproachDemand("south", 500.0),
        ApproachDemand("east", 500.0),
        ApproachDemand("west", 500.0),
    ]
    plan = optimizer.optimize(
        standard_intersection,
        demands,
        algorithm=OptimizationAlgorithm.DEMAND_PROPORTIONAL,
        target_cycle_length=90.0,
    )
    assert plan.plan_type == "optimized"
    assert plan.cycle_length_seconds == 90.0
    g1 = plan.phase_timings[0].green_seconds
    g2 = plan.phase_timings[1].green_seconds
    assert abs(g1 - g2) < 1.0


def test_demand_proportional_optimization_asymmetric(standard_intersection):
    """Under heavy North-South demand, optimizer should allocate significantly more green to Phase 1."""
    optimizer = SignalOptimizer()
    demands = [
        ApproachDemand("north", 1200.0),
        ApproachDemand("south", 1100.0),
        ApproachDemand("east", 250.0),
        ApproachDemand("west", 200.0),
    ]
    plan = optimizer.optimize(
        standard_intersection,
        demands,
        algorithm=OptimizationAlgorithm.DEMAND_PROPORTIONAL,
        target_cycle_length=90.0,
    )
    g_ns = plan.phase_timings[0].green_seconds
    g_ew = plan.phase_timings[1].green_seconds

    # NS should receive substantially more green than EW
    assert g_ns > g_ew
    assert g_ns >= 50.0
    assert g_ew >= standard_intersection.phases[1].min_green_seconds
    assert round(g_ns + g_ew + plan.total_lost_seconds, 1) == 90.0


def test_dynamic_behavior_proof(standard_intersection):
    """
    PROVES dynamic behavior: different demand profiles produce genuinely distinct,
    dynamically calculated green allocations (not hard-coded constants).
    """
    optimizer = SignalOptimizer()

    # Input A: Heavy NS Rush
    demands_A = [
        ApproachDemand("north", 1300.0),
        ApproachDemand("south", 1200.0),
        ApproachDemand("east", 200.0),
        ApproachDemand("west", 200.0),
    ]
    plan_A = optimizer.optimize(
        standard_intersection, demands_A, OptimizationAlgorithm.DEMAND_PROPORTIONAL, target_cycle_length=90.0
    )

    # Input B: Heavy EW Surge
    demands_B = [
        ApproachDemand("north", 200.0),
        ApproachDemand("south", 200.0),
        ApproachDemand("east", 1300.0),
        ApproachDemand("west", 1200.0),
    ]
    plan_B = optimizer.optimize(
        standard_intersection, demands_B, OptimizationAlgorithm.DEMAND_PROPORTIONAL, target_cycle_length=90.0
    )

    g_ns_A = plan_A.phase_timings[0].green_seconds
    g_ew_A = plan_A.phase_timings[1].green_seconds

    g_ns_B = plan_B.phase_timings[0].green_seconds
    g_ew_B = plan_B.phase_timings[1].green_seconds

    # Assert dynamic responsiveness
    assert g_ns_A > g_ew_A, "Heavy NS input must give NS dominant green"
    assert g_ew_B > g_ns_B, "Heavy EW input must give EW dominant green"
    assert g_ns_A == g_ew_B, "Symmetric inputs should yield mirrored allocations"
    assert g_ew_A == g_ns_B


def test_webster_optimal_algorithm(standard_intersection):
    """Verifies Webster's optimal cycle length calculation and bounds."""
    optimizer = SignalOptimizer()
    demands = [
        ApproachDemand("north", 800.0),
        ApproachDemand("south", 750.0),
        ApproachDemand("east", 400.0),
        ApproachDemand("west", 350.0),
    ]
    plan = optimizer.optimize(
        standard_intersection,
        demands,
        algorithm=OptimizationAlgorithm.WEBSTER_OPTIMAL,
    )
    assert plan.plan_type == "optimized"
    assert plan.algorithm_name == "webster_optimal"
    assert standard_intersection.cycle_length_min_seconds <= plan.cycle_length_seconds <= standard_intersection.cycle_length_max_seconds


def test_constrained_delay_minimization_algorithm(standard_intersection):
    """Verifies constrained delay minimization search produces valid plan."""
    optimizer = SignalOptimizer()
    demands = [
        ApproachDemand("north", 1100.0),
        ApproachDemand("south", 900.0),
        ApproachDemand("east", 300.0),
        ApproachDemand("west", 250.0),
    ]
    plan = optimizer.optimize(
        standard_intersection,
        demands,
        algorithm=OptimizationAlgorithm.CONSTRAINED_DELAY_MINIMIZATION,
        target_cycle_length=90.0,
    )
    assert plan.plan_type == "optimized"
    assert plan.cycle_length_seconds == 90.0
    for pt in plan.phase_timings:
        assert pt.green_seconds >= 10.0  # min green respected


# ==============================================================================
# 4. Mathematical Objective & Simulation Evaluation Tests
# ==============================================================================

def test_webster_delay_formula_undersaturated(standard_intersection):
    """Verifies that Webster delay proxy calculates non-negative, plausible delay for undersaturated flow."""
    approach = standard_intersection.approaches[0]  # North, s = 1800 vph
    demand = ApproachDemand("north", 400.0)
    perf = SimulationEvaluator.compute_approach_performance(
        approach=approach,
        demand=demand,
        allocated_green=40.0,
        cycle_length=90.0,
    )
    assert perf.capacity_vph == pytest.approx(1800.0 * (40.0 / 90.0), rel=1e-2)
    assert perf.degree_of_saturation_x < 0.60
    assert 5.0 <= perf.estimated_delay_seconds <= 35.0
    assert perf.los_grade in (LevelOfService.LOS_B, LevelOfService.LOS_C)


def test_webster_delay_oversaturation_transition(standard_intersection):
    """Verifies smooth transition to HCM oversaturation delay without NaN or division by zero."""
    approach = standard_intersection.approaches[0]
    # Heavy oversaturation: demand 1500 vph with only 20s green on 90s cycle (capacity = 400 vph)
    demand = ApproachDemand("north", 1500.0)
    perf = SimulationEvaluator.compute_approach_performance(
        approach=approach,
        demand=demand,
        allocated_green=20.0,
        cycle_length=90.0,
    )
    assert perf.degree_of_saturation_x > 3.0
    assert not math.isnan(perf.estimated_delay_seconds)
    assert not math.isinf(perf.estimated_delay_seconds)
    assert perf.estimated_delay_seconds > 50.0
    assert perf.los_grade in (LevelOfService.LOS_E, LevelOfService.LOS_F)


def test_zero_demand_edge_case(standard_intersection):
    """Verifies that zero demand produces 0 delay proxy without numerical failure."""
    approach = standard_intersection.approaches[0]
    demand = ApproachDemand("north", 0.0)
    perf = SimulationEvaluator.compute_approach_performance(
        approach=approach,
        demand=demand,
        allocated_green=35.0,
        cycle_length=90.0,
    )
    assert perf.demand_flow_rate_vph == 0.0
    assert perf.estimated_delay_seconds == 0.0
    assert perf.estimated_queue_vehicles == 0.0


def test_baseline_vs_optimized_simulation_comparison(standard_intersection):
    """
    Executes full simulation comparison under asymmetric load, verifying delay reduction
    and that baseline vs optimized comparison metrics are computed properly.
    """
    engine = SignalSimulationEngine()
    demands = [
        ApproachDemand("north", 1150.0),
        ApproachDemand("south", 1050.0),
        ApproachDemand("east", 250.0),
        ApproachDemand("west", 200.0),
    ]
    res = engine.run_simulation(
        intersection=standard_intersection,
        demands=demands,
        algorithm=OptimizationAlgorithm.DEMAND_PROPORTIONAL,
        target_cycle_length=90.0,
    )

    assert res.run_id.startswith("sim_run_")
    assert res.baseline_metrics.average_delay_seconds_per_vehicle > 0
    assert res.optimized_metrics.average_delay_seconds_per_vehicle > 0

    # Under asymmetric load, optimization should reduce average delay
    assert res.optimized_metrics.average_delay_seconds_per_vehicle < res.baseline_metrics.average_delay_seconds_per_vehicle
    assert res.delay_reduction_pct > 0.0
    assert len(res.phase_comparisons) == 2
    assert len(res.approach_comparisons) == 4


# ==============================================================================
# 5. 3-Way T-Junction & Dual-Lane Topology Tests
# ==============================================================================

def test_3way_t_junction_simulation(t_junction_intersection):
    """Verifies that 3-way T-junction with asymmetrical approach count optimizes properly."""
    engine = SignalSimulationEngine()
    demands = [
        ApproachDemand("east", 1200.0),
        ApproachDemand("west", 1100.0),
        ApproachDemand("north", 300.0),
    ]
    res = engine.run_simulation(
        intersection=t_junction_intersection,
        demands=demands,
        algorithm=OptimizationAlgorithm.DEMAND_PROPORTIONAL,
        target_cycle_length=80.0,
    )
    assert len(res.phase_comparisons) == 2
    assert len(res.approach_comparisons) == 3
    # Highway EW phase should get more green than Pier access stem
    assert res.optimized_plan.phase_timings[0].green_seconds > res.optimized_plan.phase_timings[1].green_seconds


def test_dual_lane_4way_simulation(dual_lane_intersection):
    """Verifies multi-lane saturation capacity calculation and simulation."""
    engine = SignalSimulationEngine()
    demands = [
        ApproachDemand("north", 2200.0),  # Dual lane corridor
        ApproachDemand("south", 2100.0),
        ApproachDemand("east", 600.0),
        ApproachDemand("west", 550.0),
    ]
    res = engine.run_simulation(
        intersection=dual_lane_intersection,
        demands=demands,
        algorithm=OptimizationAlgorithm.DEMAND_PROPORTIONAL,
        target_cycle_length=100.0,
    )
    assert res.optimized_metrics.throughput_capacity_vph > res.baseline_metrics.throughput_capacity_vph


# ==============================================================================
# 6. Safety & Input Boundary Validation Tests
# ==============================================================================

def test_invalid_negative_demand_raises(standard_intersection):
    """Negative demand flow rates must be rejected."""
    optimizer = SignalOptimizer()
    with pytest.raises(ValueError, match="Invalid flow rate"):
        optimizer.optimize(
            standard_intersection,
            [ApproachDemand("north", -50.0), ApproachDemand("south", 100.0)],
        )


def test_invalid_phase_count_raises():
    """Intersections with fewer than 2 phases must be rejected."""
    bad_intersection = IntersectionConfig(
        intersection_id="bad",
        name="Bad",
        approaches=[ApproachConfig("north", "North")],
        phases=[SignalPhaseConfig("p1", "P1", ["north"])],
    )
    optimizer = SignalOptimizer()
    with pytest.raises(ValueError, match="at least 2 signal phases"):
        optimizer.optimize(bad_intersection, [ApproachDemand("north", 100.0)])


def test_unsafe_min_green_raises():
    """Phases with min green below 5.0 seconds must be rejected for safety."""
    bad_intersection = IntersectionConfig(
        intersection_id="bad",
        name="Bad",
        approaches=[ApproachConfig("north", "North"), ApproachConfig("south", "South")],
        phases=[
            SignalPhaseConfig("p1", "P1", ["north"], min_green_seconds=2.0),
            SignalPhaseConfig("p2", "P2", ["south"], min_green_seconds=10.0),
        ],
    )
    optimizer = SignalOptimizer()
    with pytest.raises(ValueError, match="min green must be >= 5.0 seconds"):
        optimizer.optimize(bad_intersection, [ApproachDemand("north", 100.0), ApproachDemand("south", 100.0)])


# ==============================================================================
# 7. REST API Endpoints Tests
# ==============================================================================

def test_api_signal_optimization_info(client):
    """GET /api/v1/signal-optimization/info returns service metadata and disclaimers."""
    res = client.get("/api/v1/signal-optimization/info")
    assert res.status_code == 200
    data = res.json()
    assert data["service_name"] == "TrafficSignalOptimizationEngine"
    assert data["is_simulation"] is True
    assert "does not directly control physical traffic signals" in data["disclaimer"]
    assert "demand_proportional" in data["supported_algorithms"]


def test_api_signal_optimization_presets(client):
    """GET /api/v1/signal-optimization/presets returns intersection and scenario presets."""
    res = client.get("/api/v1/signal-optimization/presets")
    assert res.status_code == 200
    data = res.json()
    assert len(data["intersections"]) >= 3
    assert len(data["scenarios"]) >= 4


def test_api_signal_simulation_execution_preset(client):
    """POST /api/v1/signal-optimization/simulate executes simulation and persists run."""
    payload = {
        "intersection_preset_id": "int_4way_standard",
        "demand_scenario_id": "arterial_rush_ns",
        "algorithm": "demand_proportional",
        "target_cycle_length": 90.0,
        "save_to_history": True,
    }
    res = client.post("/api/v1/signal-optimization/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert data["intersection_type"] == "four_way"
    assert data["algorithm_used"] == "demand_proportional"
    assert data["baseline_cycle_length"] == 90.0
    assert data["optimized_cycle_length"] == 90.0
    assert "baseline_delay_proxy" in data
    assert "optimized_delay_proxy" in data
    assert "phase_comparisons" in data
    assert "approach_comparisons" in data
    assert data["execution_time_ms"] > 0.0

    run_id = data["id"]

    # Retrieve run detail
    res_detail = client.get(f"/api/v1/signal-optimization/runs/{run_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == run_id

    # List historical runs
    res_list = client.get("/api/v1/signal-optimization/runs?page=1&page_size=10")
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # Delete historical run
    res_del = client.delete(f"/api/v1/signal-optimization/runs/{run_id}")
    assert res_del.status_code == 204

    # Confirm 404 after deletion
    res_after = client.get(f"/api/v1/signal-optimization/runs/{run_id}")
    assert res_after.status_code == 404


def test_api_signal_simulation_custom_intersection(client):
    """POST /api/v1/signal-optimization/simulate with custom intersection JSON payload."""
    payload = {
        "intersection": {
            "intersection_id": "custom_int_test",
            "name": "Custom Test Intersection",
            "intersection_type": "four_way",
            "approaches": [
                {"approach_id": "north", "name": "N", "lanes": 1, "saturation_flow_rate_per_lane": 1800.0, "target_speed_kmh": 50.0},
                {"approach_id": "south", "name": "S", "lanes": 1, "saturation_flow_rate_per_lane": 1800.0, "target_speed_kmh": 50.0},
                {"approach_id": "east", "name": "E", "lanes": 1, "saturation_flow_rate_per_lane": 1800.0, "target_speed_kmh": 45.0},
                {"approach_id": "west", "name": "W", "lanes": 1, "saturation_flow_rate_per_lane": 1800.0, "target_speed_kmh": 45.0},
            ],
            "phases": [
                {"phase_id": "p1", "name": "Phase 1", "controlled_approaches": ["north", "south"], "min_green_seconds": 10.0, "max_green_seconds": 60.0, "yellow_seconds": 4.0, "all_red_seconds": 2.0},
                {"phase_id": "p2", "name": "Phase 2", "controlled_approaches": ["east", "west"], "min_green_seconds": 10.0, "max_green_seconds": 60.0, "yellow_seconds": 4.0, "all_red_seconds": 2.0},
            ],
            "cycle_length_min_seconds": 45.0,
            "cycle_length_max_seconds": 120.0,
            "target_cycle_length_seconds": 90.0,
        },
        "demands": [
            {"approach_id": "north", "vehicle_flow_rate_vph": 1000.0, "data_provenance": "simulation_configured"},
            {"approach_id": "south", "vehicle_flow_rate_vph": 900.0, "data_provenance": "simulation_configured"},
            {"approach_id": "east", "vehicle_flow_rate_vph": 300.0, "data_provenance": "simulation_configured"},
            {"approach_id": "west", "vehicle_flow_rate_vph": 250.0, "data_provenance": "simulation_configured"},
        ],
        "algorithm": "webster_optimal",
        "save_to_history": False,
    }
    res = client.post("/api/v1/signal-optimization/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["intersection_name"] == "Custom Test Intersection"
    assert data["algorithm_used"] == "webster_optimal"
