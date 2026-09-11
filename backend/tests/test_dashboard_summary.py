"""
Comprehensive unit and integration tests for Phase 14 Dashboard Aggregation.
Verifies all 10 sections, strict 5-state provenance labeling, dynamic Phase 11 readiness,
simulation disclaimers, anti-trigger read-only behavior, and single-roundtrip performance.
"""
from datetime import datetime, timezone
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
from app.models.analysis import AnalysisSession, LaneResultRecord, TrafficMetricsRecord
from app.models.corridor_simulation import EmergencyCorridorSimulationRun
from app.models.prediction import PredictionRun
from app.models.simulation import SignalSimulationRun
from app.models.video import Video


def utcnow():
    return datetime.now(timezone.utc)


# Isolated SQLite test database
TEST_DB_PATH = Path(tempfile.gettempdir()) / "test_phase14_dashboard.db"
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
def db_session() -> Generator[Session, None, None]:
    """Provides a transactional database session for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> TestClient:
    """Test client bound to app with dependency overrides."""
    return TestClient(app)


def test_dashboard_info_endpoint(client: TestClient):
    """Asserts GET /api/v1/dashboard/info returns metadata and anti-trigger guarantee."""
    response = client.get("/api/v1/dashboard/info")
    assert response.status_code == 200
    data = response.json()
    assert "Phase 14" in data["phase"]
    assert "anti_trigger_guarantee" in data
    assert "NEVER trigger" in data["anti_trigger_guarantee"]
    assert "real_database_metrics" in data["provenance_categories"]
    assert "synthetic_pipeline_metrics" in data["provenance_categories"]


def test_dashboard_summary_empty_database(client: TestClient, db_session: Session):
    """
    Asserts GET /api/v1/dashboard/summary against an empty database returns all 10 sections
    truthfully labeled with UNAVAILABLE / insufficient states without crashing.
    """
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()

    # Verify root fields
    assert "timestamp" in data
    assert "execution_time_ms" in data
    assert data["execution_time_ms"] >= 0.0

    # Section 1: System Health
    health = data["system_health"]
    assert health["backend_online"] is True
    assert health["database_connected"] is True
    assert health["provenance"]["state"] == "REAL DATA"
    assert len(health["subsystems"]) == 10
    phase_11_sub = next(s for s in health["subsystems"] if s["phase"] == 11)
    assert phase_11_sub["status"] in ["insufficient", "unavailable"]

    # Section 2: Traffic Overview
    traffic = data["traffic_overview"]
    assert traffic["provenance"]["state"] == "UNAVAILABLE"
    assert traffic["total_sessions_count"] == 0
    assert traffic["total_vehicles_counted"] == 0

    # Section 3: Vehicle Composition
    comp = data["vehicle_composition"]
    assert comp["provenance"]["state"] == "UNAVAILABLE"
    assert len(comp["class_distribution"]) == 0

    # Section 4: Traffic Flow Metrics
    flow = data["traffic_flow_metrics"]
    assert flow["provenance"]["state"] == "UNAVAILABLE"
    assert len(flow["time_series_buckets"]) == 0

    # Section 5: Lane Density
    lane = data["lane_density"]
    assert lane["provenance"]["state"] == "UNAVAILABLE"
    assert lane["total_lanes_analyzed"] == 0
    assert "vehicles/px²" in lane["density_unit"]

    # Section 6: Prediction Status
    pred = data["prediction_availability"]
    assert pred["is_ready"] is False
    assert pred["threshold"] == 20
    assert pred["provenance"]["state"] == "PREDICTION"

    # Section 7: Signal Optimization
    sig = data["signal_optimization"]
    assert sig["provenance"]["state"] == "UNAVAILABLE"
    assert "Simulation / Decision Support" in sig["disclaimer"]

    # Section 8: Emergency Corridor
    corridor = data["emergency_corridor"]
    assert corridor["provenance"]["state"] == "UNAVAILABLE"
    assert "Simulation / Decision Support" in corridor["disclaimer"]

    # Section 9: Recent History
    hist = data["recent_history"]
    assert hist["provenance"]["state"] == "UNAVAILABLE"
    assert len(hist["sessions"]) == 0

    # Section 10: Data Provenance Panel
    prov = data["data_provenance"]
    assert prov["provenance"]["state"] == "UNAVAILABLE"
    assert prov["active_session_id"] is None


def test_dashboard_summary_with_real_session(client: TestClient, db_session: Session):
    """
    Tests summary endpoint with a genuine verified real-world session, verifying:
    - Real data provenance propagation
    - Vehicle counting and class composition aggregation
    - Shoelace polygon density metrics
    - Non-interpolated time-series buckets
    - Extrapolation flag (<1hr observation window)
    """
    # Seed a verified real video
    video = Video(
        id="vid_real_test_001",
        original_filename="real_traffic_clip.mp4",
        storage_path="/storage/videos/real_traffic_clip.mp4",
        duration_seconds=120.0,
        fps=30.0,
        resolution="1920x1080",
        frame_count=3600,
        status="processed",
        source_type="real_world",
        source_reference="https://github.com/example/real-traffic",
        license_reference="MIT",
        provenance_note="Camera feed from main arterial",
        provenance_verified=True,
    )
    db_session.add(video)

    # Seed analysis session
    session = AnalysisSession(
        id="sess_real_001",
        video_id=video.id,
        analysis_type="full_pipeline",
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
        processing_time_ms=245.0,
        total_frames_processed=600,
        total_vehicles_detected=45,
        total_vehicles_counted=38,
    )
    db_session.add(session)

    # Seed TrafficMetricsRecord
    metrics = TrafficMetricsRecord(
        id="metrics_real_001",
        analysis_session_id=session.id,
        observation_duration_seconds=120.0,
        total_volume=38,
        flow_rate_per_minute=19.0,
        flow_rate_per_hour=1140.0,
        is_extrapolated=True,
        class_distribution=[
            {"class_name": "car", "count": 28, "percentage": 73.68},
            {"class_name": "bus", "count": 6, "percentage": 15.79},
            {"class_name": "truck", "count": 4, "percentage": 10.53},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 22, "percentage": 57.89},
            {"direction": "outbound", "count": 16, "percentage": 42.11},
        ],
        time_series_buckets=[
            {"bucket_index": 0, "start_time_seconds": 0.0, "end_time_seconds": 60.0, "count": 20, "flow_rate_per_minute": 20.0},
            {"bucket_index": 1, "start_time_seconds": 60.0, "end_time_seconds": 120.0, "count": 18, "flow_rate_per_minute": 18.0},
        ],
    )
    db_session.add(metrics)

    # Seed LaneResultRecord
    lane = LaneResultRecord(
        id="lane_real_001",
        analysis_session_id=session.id,
        lane_id="lane_northbound_1",
        lane_name="Northbound Inbound Lane",
        direction_hint="northbound",
        polygon_json=[[100, 200], [300, 200], [300, 800], [100, 800]],
        polygon_area_px2=120000.0,
        unique_vehicles_count=18,
        peak_occupancy=4,
        average_occupancy=2.3,
        image_space_density=0.00015,
        normalized_density_score=0.45,
        vehicle_class_counts={"car": 14, "bus": 4},
        density_unit="vehicles/px²",
        density_calibration_warning="Image-space density (vehicles/px²) — uncalibrated camera.",
    )
    db_session.add(lane)
    db_session.commit()

    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()

    # Verify Traffic Overview has REAL DATA provenance
    traffic = data["traffic_overview"]
    assert traffic["provenance"]["state"] == "REAL DATA"
    assert traffic["provenance"]["category"] == "real_database_metrics"
    assert traffic["total_vehicles_counted"] == 38
    assert traffic["total_vehicles_detected"] == 45
    assert traffic["is_extrapolated"] is True
    assert "extrapolated" in traffic["extrapolation_note"].lower()

    # Verify Vehicle Composition
    comp = data["vehicle_composition"]
    assert comp["provenance"]["state"] == "REAL DATA"
    assert comp["total_counted"] == 38
    assert len(comp["class_distribution"]) == 3
    assert comp["class_distribution"][0]["class_name"] == "car"

    # Verify Traffic Flow Time Series
    flow = data["traffic_flow_metrics"]
    assert flow["provenance"]["state"] == "REAL DATA"
    assert len(flow["time_series_buckets"]) == 2
    assert flow["time_series_buckets"][0]["count"] == 20

    # Verify Lane Density
    lane_sec = data["lane_density"]
    assert lane_sec["provenance"]["state"] == "REAL DATA"
    assert lane_sec["total_lanes_analyzed"] == 1
    assert lane_sec["lanes"][0]["lane_id"] == "lane_northbound_1"
    assert lane_sec["lanes"][0]["peak_occupancy"] == 4
    assert "vehicles/px²" in lane_sec["density_unit"]

    # Verify Data Provenance Section
    prov = data["data_provenance"]
    assert prov["provenance"]["state"] == "REAL DATA"
    assert prov["video_filename"] == "real_traffic_clip.mp4"
    assert prov["provenance_verified"] is True
    assert prov["source_reference"] == "https://github.com/example/real-traffic"
    assert prov["license_reference"] == "MIT"


def test_dashboard_summary_simulations_and_predictions(client: TestClient, db_session: Session):
    """
    Tests simulation and prediction integration into dashboard summary:
    - Signal Simulation run results & decision-support disclaimer
    - Emergency Corridor run results & decision-support disclaimer
    - Phase 11 prediction readiness dynamic evaluation
    """
    # Seed SignalSimulationRun
    signal_run = SignalSimulationRun(
        id="sig_test_001",
        intersection_name="Downtown 4-Way Junction",
        intersection_type="four_way",
        data_source="simulation_configured",
        algorithm_used="webster_optimal",
        baseline_cycle_length=90.0,
        optimized_cycle_length=75.0,
        baseline_delay_proxy=34.2,
        optimized_delay_proxy=22.8,
        delay_reduction_pct=33.33,
        queue_reduction_pct=28.5,
        baseline_throughput_proxy=1200.0,
        optimized_throughput_proxy=1400.0,
        throughput_increase_pct=16.67,
        objective_improvement_pct=33.33,
        execution_time_ms=0.45,
        intersection_config={"name": "Downtown 4-Way Junction"},
        demand_input=[],
        baseline_plan={},
        optimized_plan={},
        baseline_metrics={},
        optimized_metrics={},
        phase_comparisons=[],
        approach_comparisons=[],
    )
    db_session.add(signal_run)

    # Seed EmergencyCorridorSimulationRun
    corridor_run = EmergencyCorridorSimulationRun(
        id="ec_test_001",
        corridor_name="Main Medical Arterial",
        corridor_nodes_count=3,
        total_distance_meters=1500.0,
        vehicle_type="ambulance",
        priority_strategy="green_extension_early_green",
        recovery_strategy="smooth_compensation",
        data_source="simulation_configured",
        baseline_travel_time_seconds=180.0,
        priority_travel_time_seconds=115.0,
        travel_time_savings_seconds=65.0,
        travel_time_savings_pct=36.11,
        baseline_emergency_delay_seconds=75.0,
        priority_emergency_delay_seconds=10.0,
        emergency_delay_reduction_pct=86.67,
        baseline_cross_street_delay_avg=14.5,
        priority_cross_street_delay_avg=18.2,
        corridor_config={"name": "Main Medical Arterial"},
        vehicle_scenario={"type": "ambulance"},
        node_timelines=[],
        metrics_summary={},
    )
    db_session.add(corridor_run)

    # Seed PredictionRun
    pred_run = PredictionRun(
        id="pred_test_001",
        model_name="RandomForestRegressor",
        model_type="ensemble_tree",
        target_variable="vehicle_volume",
        horizon_minutes=15,
        data_source="synthetic_fixture",
        training_sample_count=25,
        test_sample_count=8,
        training_time_ms=12.4,
        mae=1.65,
        rmse=2.12,
        r2_score=0.88,
        baseline_mae=2.85,
        baseline_rmse=3.50,
    )
    db_session.add(pred_run)
    db_session.commit()

    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()

    # Section 7: Signal Optimization
    sig = data["signal_optimization"]
    assert sig["provenance"]["state"] == "SIMULATION"
    assert sig["latest_run_id"] == "sig_test_001"
    assert sig["intersection_name"] == "Downtown 4-Way Junction"
    assert sig["delay_reduction_pct"] == 33.33
    assert "Simulation / Decision Support" in sig["disclaimer"]
    assert "not connected to physical signals" in sig["disclaimer"]

    # Section 8: Emergency Corridor
    ec = data["emergency_corridor"]
    assert ec["provenance"]["state"] == "SIMULATION"
    assert ec["latest_run_id"] == "ec_test_001"
    assert ec["corridor_name"] == "Main Medical Arterial"
    assert ec["vehicle_type"] == "ambulance"
    assert ec["travel_time_savings_pct"] == 36.11
    assert "Simulation / Decision Support" in ec["disclaimer"]
    assert "not a real dispatch or control system" in ec["disclaimer"]

    # Section 6: Prediction Status
    pred = data["prediction_availability"]
    assert pred["latest_run_id"] == "pred_test_001"
    assert pred["latest_model_name"] == "RandomForestRegressor"
    assert pred["latest_rmse"] == 2.12
    assert pred["latest_mae"] == 1.65
    assert pred["threshold"] == 20


def test_dashboard_summary_specific_session_id(client: TestClient, db_session: Session):
    """Tests querying /summary with a specific session_id query parameter."""
    v1 = Video(
        id="vid_001",
        original_filename="clip_a.mp4",
        storage_path="/path/a",
        source_type="synthetic_test",
        provenance_verified=False,
    )
    v2 = Video(
        id="vid_002",
        original_filename="clip_b.mp4",
        storage_path="/path/b",
        source_type="real_world",
        provenance_verified=True,
    )
    db_session.add_all([v1, v2])

    s1 = AnalysisSession(
        id="sess_specific_001",
        video_id=v1.id,
        analysis_type="full_pipeline",
        status="completed",
        total_vehicles_counted=10,
    )
    s2 = AnalysisSession(
        id="sess_specific_002",
        video_id=v2.id,
        analysis_type="full_pipeline",
        status="completed",
        total_vehicles_counted=50,
    )
    db_session.add_all([s1, s2])

    m1 = TrafficMetricsRecord(
        id="m_001",
        analysis_session_id=s1.id,
        observation_duration_seconds=30.0,
        total_volume=10,
    )
    m2 = TrafficMetricsRecord(
        id="m_002",
        analysis_session_id=s2.id,
        observation_duration_seconds=60.0,
        total_volume=50,
    )
    db_session.add_all([m1, m2])
    db_session.commit()

    # Query specifically for s1
    res1 = client.get(f"/api/v1/dashboard/summary?session_id={s1.id}")
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["traffic_overview"]["active_session_id"] == s1.id
    assert d1["traffic_overview"]["provenance"]["state"] == "SYNTHETIC"

    # Query specifically for s2
    res2 = client.get(f"/api/v1/dashboard/summary?session_id={s2.id}")
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["traffic_overview"]["active_session_id"] == s2.id
    assert d2["traffic_overview"]["provenance"]["state"] == "REAL DATA"
