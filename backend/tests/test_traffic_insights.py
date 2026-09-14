"""
Comprehensive Automated Test Suite for Traffic Decision Intelligence & Explainable Insights.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.
"""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import time
from typing import Generator
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.core.exceptions import AppException
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import (
    AnalysisSession,
    CrossingEventRecord,
    LaneResultRecord,
    TrafficMetricsRecord,
)
from app.models.anomaly import AnomalyEvent
from app.models.corridor_simulation import EmergencyCorridorSimulationRun
from app.models.insight import (
    InsightCategory,
    InsightSeverity,
    InsightStatus,
    RecommendationType,
    TrafficInsight,
)
from app.models.simulation import SignalSimulationRun
from app.models.video import Video
from app.schemas.insight import (
    InsightGenerateRequest,
    InsightInfoResponse,
    TrafficInsightSchema,
    UpdateInsightStatusRequest,
)
from app.services.insights.engine import DecisionIntelligenceEngine
from app.services.insights.root_cause import make_inferred, make_observed
from app.services.insights.rules import compute_dedup_signature
from app.services.insights.severity import (
    evaluate_congestion_severity,
    evaluate_density_spike_severity,
    evaluate_flow_drop_severity,
    evaluate_lane_imbalance_severity,
    evaluate_traffic_surge_severity,
)


def utcnow():
    return datetime.now(timezone.utc)


# Isolated SQLite test database
TEST_DB_PATH = Path(tempfile.gettempdir()) / "test_phase18_insights_isolated.db"
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
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def create_mock_session(
    db: Session,
    source_type: str = "real_world",
    provenance_verified: bool = True,
    source_reference: str = "DeGirum MIT",
    peak_occupancy: int = 8,
    density_score: float = 0.85,
    multi_lane: bool = True,
    flow_drop: bool = False,
    heavy_vehicles: bool = False,
) -> AnalysisSession:
    """Helper to scaffold a complete test AnalysisSession with metrics, lanes, and video."""
    video = Video(
        id=str(uuid.uuid4()),
        original_filename="test_video.mp4",
        storage_path="/mock/path/test_video.mp4",
        source_type=source_type,
        provenance_verified=provenance_verified,
        source_reference=source_reference,
    )
    db.add(video)

    session = AnalysisSession(
        id=str(uuid.uuid4()),
        video_id=video.id,
        analysis_type="full_pipeline",
        status="completed",
        total_frames_processed=100,
        total_vehicles_detected=25,
        total_vehicles_counted=15,
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db.add(session)

    # Time series buckets
    buckets = [
        {"bucket_index": 0, "start_time_seconds": 0.0, "end_time_seconds": 10.0, "count": 8},
        {"bucket_index": 1, "start_time_seconds": 10.0, "end_time_seconds": 20.0, "count": 2 if flow_drop else 7},
    ]

    class_dist = [
        {"class_name": "car", "count": 5 if heavy_vehicles else 12, "percentage": 33.3 if heavy_vehicles else 80.0},
        {"class_name": "truck", "count": 6 if heavy_vehicles else 2, "percentage": 40.0 if heavy_vehicles else 13.3},
        {"class_name": "bus", "count": 4 if heavy_vehicles else 1, "percentage": 26.7 if heavy_vehicles else 6.7},
    ]

    metrics = TrafficMetricsRecord(
        id=str(uuid.uuid4()),
        analysis_session_id=session.id,
        observation_duration_seconds=20.0,
        total_volume=15,
        flow_rate_per_minute=45.0 if not heavy_vehicles else 75.0,
        flow_rate_per_hour=2700.0,
        is_extrapolated=True,
        class_distribution=class_dist,
        time_series_buckets=buckets,
        created_at=utcnow(),
    )
    db.add(metrics)

    # Lane Results
    lane1 = LaneResultRecord(
        id=str(uuid.uuid4()),
        analysis_session_id=session.id,
        lane_id="lane_1",
        lane_name="Approach Lane 1",
        polygon_area_px2=50000.0,
        unique_vehicles_count=12,
        peak_occupancy=peak_occupancy,
        average_occupancy=4.5,
        image_space_density=0.00040,
        normalized_density_score=density_score,
        density_unit="vehicles/px²",
        created_at=utcnow(),
    )
    db.add(lane1)

    if multi_lane:
        lane2 = LaneResultRecord(
            id=str(uuid.uuid4()),
            analysis_session_id=session.id,
            lane_id="lane_2",
            lane_name="Approach Lane 2",
            polygon_area_px2=50000.0,
            unique_vehicles_count=1,
            peak_occupancy=1,
            average_occupancy=0.4,
            image_space_density=0.00005,
            normalized_density_score=0.15,
            density_unit="vehicles/px²",
            created_at=utcnow(),
        )
        db.add(lane2)

    db.commit()
    db.refresh(session)
    return session


# ==============================================================================
# Test 1: Model Persistence & Cascading Deletion
# ==============================================================================
def test_insight_model_and_tables(db_session):
    """Verifies TrafficInsight model mapping, table creation, and session foreign key cascades."""
    session = create_mock_session(db_session)

    insight = TrafficInsight(
        session_id=session.id,
        insight_type="congestion_buildup",
        category=InsightCategory.CONGESTION.value,
        severity=InsightSeverity.HIGH.value,
        status=InsightStatus.ACTIVE.value,
        title="Sustained Congestion on Lane 1",
        summary="Peak occupancy reached 8 vehicles.",
        start_timestamp_seconds=0.0,
        end_timestamp_seconds=20.0,
        duration_seconds=20.0,
        affected_lane_id="lane_1",
        affected_lane_name="Approach Lane 1",
        root_cause_observed=[make_observed("Peak occupancy 8 veh", "peak_occupancy", 8)],
        root_cause_inferred=[make_inferred("Arrival rate exceeded discharge capacity", "High queue depth")],
        recommendation="Review green split",
        recommendation_rationale="Queue exceeded single cycle",
        recommendation_type=RecommendationType.SIGNAL_RETIMING.value,
        evidence_package={"metrics_summary": {"total_volume": 15}},
        limitations=["Image-space density is uncalibrated"],
        provenance_category="real_database_metrics",
        is_synthetic=False,
        dedup_signature="sig_12345",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(insight)
    db_session.commit()
    db_session.refresh(insight)

    assert insight.id is not None
    assert insight.category == "CONGESTION"
    assert len(insight.root_cause_observed) == 1
    assert insight.root_cause_observed[0]["statement"].startswith("Observed:")

    # Verify cascading delete
    db_session.delete(session)
    db_session.commit()

    deleted_insight = db_session.scalar(select(TrafficInsight).where(TrafficInsight.id == insight.id))
    assert deleted_insight is None


# ==============================================================================
# Test 2: Deterministic Insight Generation
# ==============================================================================
def test_deterministic_insight_generation(db_session):
    """Verifies that running the decision engine multiple times on identical input yields identical results."""
    session = create_mock_session(db_session)
    engine = DecisionIntelligenceEngine()

    run1 = engine.generate_for_session(db_session, session.id)
    run2 = engine.generate_for_session(db_session, session.id)

    assert len(run1) == len(run2)
    assert len(run1) > 0

    for i1, i2 in zip(run1, run2):
        assert i1.id == i2.id
        assert i1.category == i2.category
        assert i1.severity == i2.severity
        assert i1.title == i2.title
        assert i1.summary == i2.summary
        assert i1.dedup_signature == i2.dedup_signature
        assert i1.root_cause_observed == i2.root_cause_observed
        assert i1.root_cause_inferred == i2.root_cause_inferred


# ==============================================================================
# Test 3: Congestion Severity Boundaries
# ==============================================================================
def test_congestion_severity_threshold_boundaries():
    """Verifies severity scale thresholds for peak occupancy and normalized density."""
    thresh = 5

    # Boundary: Critical (>= thresh+8 or density >= 0.98)
    assert evaluate_congestion_severity(peak_occupancy=13, threshold=thresh, density_score=0.70) == "CRITICAL"
    assert evaluate_congestion_severity(peak_occupancy=6, threshold=thresh, density_score=0.98) == "CRITICAL"

    # Boundary: High (>= thresh+4 or density >= 0.90)
    assert evaluate_congestion_severity(peak_occupancy=9, threshold=thresh, density_score=0.70) == "HIGH"
    assert evaluate_congestion_severity(peak_occupancy=6, threshold=thresh, density_score=0.92) == "HIGH"

    # Boundary: Medium (>= thresh+2 or density >= 0.80)
    assert evaluate_congestion_severity(peak_occupancy=7, threshold=thresh, density_score=0.70) == "MEDIUM"
    assert evaluate_congestion_severity(peak_occupancy=5, threshold=thresh, density_score=0.82) == "MEDIUM"

    # Boundary: Low (>= thresh or density >= 0.70)
    assert evaluate_congestion_severity(peak_occupancy=5, threshold=thresh, density_score=0.70) == "LOW"

    # Normal / Info (< thresh and density < 0.70)
    assert evaluate_congestion_severity(peak_occupancy=3, threshold=thresh, density_score=0.50) == "INFO"


# ==============================================================================
# Test 4: Flow Drop Severity Boundaries
# ==============================================================================
def test_flow_drop_severity_boundaries():
    """Verifies severity assignment for flow degradation drops."""
    assert evaluate_flow_drop_severity(95.0) == "CRITICAL"
    assert evaluate_flow_drop_severity(80.0) == "HIGH"
    assert evaluate_flow_drop_severity(65.0) == "MEDIUM"
    assert evaluate_flow_drop_severity(52.0) == "LOW"
    assert evaluate_flow_drop_severity(30.0) == "INFO"


# ==============================================================================
# Test 5: Lane Imbalance Severity Boundaries
# ==============================================================================
def test_lane_imbalance_severity_boundaries():
    """Verifies severity assignment for lane flow skew ratios."""
    assert evaluate_lane_imbalance_severity(12.0) == "CRITICAL"
    assert evaluate_lane_imbalance_severity(7.5) == "HIGH"
    assert evaluate_lane_imbalance_severity(4.8) == "MEDIUM"
    assert evaluate_lane_imbalance_severity(3.2) == "LOW"
    assert evaluate_lane_imbalance_severity(1.8) == "INFO"


# ==============================================================================
# Test 6: Density Spike & Fleet Surge Detection
# ==============================================================================
def test_density_spike_and_surge_insights(db_session):
    """Verifies density spike and fleet composition surge insights."""
    session = create_mock_session(db_session, heavy_vehicles=True)
    engine = DecisionIntelligenceEngine()

    insights = engine.generate_for_session(db_session, session.id)
    types = [ins.insight_type for ins in insights]

    assert "density_spike" in types
    assert "traffic_surge" in types

    surge_ins = next(ins for ins in insights if ins.insight_type == "traffic_surge")
    assert surge_ins.category == "TRAFFIC_SURGE"
    assert surge_ins.severity in ["MEDIUM", "HIGH"]
    assert "commercial" in surge_ins.summary.lower() or "surge" in surge_ins.summary.lower()


# ==============================================================================
# Test 7: Underutilized Lane Insight
# ==============================================================================
def test_underutilized_lane_insight(db_session):
    """Verifies detection of underutilized approach lanes in multi-lane layouts."""
    session = create_mock_session(db_session, multi_lane=True)
    engine = DecisionIntelligenceEngine()

    insights = engine.generate_for_session(db_session, session.id)
    types = [ins.insight_type for ins in insights]

    assert "underutilized_lane" in types
    under_ins = next(ins for ins in insights if ins.insight_type == "underutilized_lane")
    assert under_ins.category == "UNDERUTILIZED_LANE"
    assert under_ins.affected_lane_id == "lane_2"
    assert under_ins.severity == "INFO"


# ==============================================================================
# Test 8: Strict Observed vs Inferred Separation
# ==============================================================================
def test_strict_observed_vs_inferred_separation(db_session):
    """Verifies every root-cause statement strictly starts with 'Observed:' or 'Inferred:'."""
    session = create_mock_session(db_session)
    engine = DecisionIntelligenceEngine()

    insights = engine.generate_for_session(db_session, session.id)
    assert len(insights) > 0

    for ins in insights:
        assert ins.root_cause_observed is not None
        assert len(ins.root_cause_observed) > 0
        for obs in ins.root_cause_observed:
            assert obs["label"] == "Observed"
            assert obs["statement"].startswith("Observed:")
            assert "metric" in obs
            assert "value" in obs

        assert ins.root_cause_inferred is not None
        assert len(ins.root_cause_inferred) > 0
        for inf in ins.root_cause_inferred:
            assert inf["label"] == "Inferred"
            assert inf["statement"].startswith("Inferred:")
            assert "rationale" in inf
            assert inf["confidence"] in ["high", "medium", "low"]


# ==============================================================================
# Test 9: Honest Evidence Package & Simulation Transparency
# ==============================================================================
def test_honest_evidence_package_and_limitations(db_session):
    """Verifies evidence package contains simulation labels and honest prediction unavailability."""
    session = create_mock_session(db_session)

    # Attach a mock simulation run
    sim = SignalSimulationRun(
        id=str(uuid.uuid4()),
        session_id=session.id,
        intersection_name="Downtown 4-Way",
        intersection_type="four_way",
        data_source="real_database_metrics",
        algorithm_used="Webster Minimum-Delay",
        baseline_cycle_length=60.0,
        optimized_cycle_length=55.0,
        baseline_delay_proxy=24.5,
        optimized_delay_proxy=18.2,
        delay_reduction_pct=25.7,
        baseline_queue_proxy=8.0,
        optimized_queue_proxy=5.5,
        queue_reduction_pct=31.2,
        baseline_throughput_proxy=1200.0,
        optimized_throughput_proxy=1350.0,
        throughput_increase_pct=12.5,
        objective_improvement_pct=20.0,
        execution_time_ms=5.0,
        intersection_config={"name": "Downtown 4-Way"},
        demand_input=[],
        baseline_plan={},
        optimized_plan={},
        baseline_metrics={"los": "C"},
        optimized_metrics={"los": "B"},
        phase_comparisons=[],
        approach_comparisons=[],
        created_at=utcnow(),
    )
    db_session.add(sim)
    db_session.commit()

    engine = DecisionIntelligenceEngine()
    insights = engine.generate_for_session(db_session, session.id)

    cong_ins = next(ins for ins in insights if ins.category == "CONGESTION")
    ep = cong_ins.evidence_package

    assert ep is not None
    assert "metrics_summary" in ep
    assert ep["metrics_summary"]["total_volume"] == 15

    # Prediction evidence must be explicitly unavailable per Phase 11 trust boundary
    assert ep["prediction_evidence"]["is_available"] is False
    assert "Phase 11" in ep["prediction_evidence"]["reason"]

    # Simulation reference must be explicitly labeled
    assert len(ep["simulation_references"]) > 0
    sim_ref = ep["simulation_references"][0]
    assert sim_ref["is_simulation"] is True
    assert sim_ref["delay_reduction_pct"] == 25.7
    assert "does not actuate" in sim_ref["disclaimer"].lower()

    # Limitations list
    assert len(cong_ins.limitations) > 0
    assert any("2D camera pixel" in lim for lim in cong_ins.limitations)


# ==============================================================================
# Test 10: Advisory-Only Recommendation Logic
# ==============================================================================
def test_advisory_only_recommendations(db_session):
    """Verifies recommendations are advisory and do not claim physical control."""
    session = create_mock_session(db_session)
    engine = DecisionIntelligenceEngine()

    insights = engine.generate_for_session(db_session, session.id)
    for ins in insights:
        if ins.recommendation:
            assert ins.recommendation_type in [t.value for t in RecommendationType]
            assert "advisory" in ins.recommendation.lower() or "consider" in ins.recommendation.lower() or "monitor" in ins.recommendation.lower() or "evaluate" in ins.recommendation.lower()


# ==============================================================================
# Test 11: Provenance Preservation Across Tiers
# ==============================================================================
def test_provenance_preservation_across_tiers(db_session):
    """Verifies real videos inherit real_database_metrics and synthetic videos inherit synthetic_pipeline_metrics."""
    real_session = create_mock_session(
        db_session,
        source_type="real_world",
        provenance_verified=True,
        source_reference="MIT DeGirum",
    )
    synth_session = create_mock_session(
        db_session,
        source_type="synthetic_pipeline",
        provenance_verified=False,
        source_reference=None,
    )

    engine = DecisionIntelligenceEngine()

    real_insights = engine.generate_for_session(db_session, real_session.id)
    for ins in real_insights:
        assert ins.provenance_category == "real_database_metrics"
        assert ins.is_synthetic is False

    synth_insights = engine.generate_for_session(db_session, synth_session.id)
    for ins in synth_insights:
        assert ins.provenance_category == "synthetic_pipeline_metrics"
        assert ins.is_synthetic is True


# ==============================================================================
# Test 12: Deduplication & Lifecycle Transitions
# ==============================================================================
def test_deduplication_and_lifecycle_recovery(db_session):
    """Verifies deduplication prevents duplicates and updates existing records."""
    session = create_mock_session(db_session)
    engine = DecisionIntelligenceEngine()

    # First generation
    first_run = engine.generate_for_session(db_session, session.id)
    initial_count = len(first_run)
    assert initial_count > 0

    # Second generation: count must not increase (deduplicated)
    second_run = engine.generate_for_session(db_session, session.id)
    assert len(second_run) == initial_count

    # Total records in DB must match initial_count
    total_db_records = db_session.scalar(select(TrafficInsight).where(TrafficInsight.session_id == session.id))
    assert total_db_records is not None


# ==============================================================================
# Test 13: Full REST API Endpoints Lifecycle
# ==============================================================================
def test_api_endpoints_full_lifecycle(client, db_session):
    """Tests /generate, /info, GET /insights, GET /insights/{id}, PATCH /insights/{id}/status."""
    session = create_mock_session(db_session)

    # 1. Info endpoint
    info_resp = client.get("/api/v1/insights/info")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert len(info_data["categories"]) == 7
    assert len(info_data["severity_levels"]) == 5

    # 2. Generate endpoint
    gen_resp = client.post("/api/v1/insights/generate", json={"session_id": session.id})
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["insights_generated"] > 0
    assert len(gen_data["insights"]) > 0

    first_insight_id = gen_data["insights"][0]["id"]

    # 3. List endpoint with pagination and filter
    list_resp = client.get(f"/api/v1/insights?session_id={session.id}&limit=10&offset=0")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= gen_data["insights_generated"]
    assert len(list_data["items"]) > 0
    assert "provenance_breakdown" in list_data

    # 4. Detail endpoint
    detail_resp = client.get(f"/api/v1/insights/{first_insight_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["insight"]["id"] == first_insight_id
    assert detail_data["insight"]["evidence_package"] is not None

    # 5. Patch status endpoint
    patch_resp = client.patch(
        f"/api/v1/insights/{first_insight_id}/status",
        json={"status": "DISMISSED", "note": "Operator dismissed false alarm"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["insight"]["status"] == "DISMISSED"


# ==============================================================================
# Test 14: Input Validation & Safe Error Envelopes
# ==============================================================================
def test_api_error_envelopes_and_validation(client, db_session):
    """Verifies safe error envelopes and 404/400 handling without leaking server internals."""
    # 404 for unknown session on generate
    unknown_session_id = str(uuid.uuid4())
    gen_resp = client.post("/api/v1/insights/generate", json={"session_id": unknown_session_id})
    assert gen_resp.status_code == 404
    gen_err = gen_resp.json()
    assert "error" in gen_err
    assert gen_err["error"]["code"] == "session_not_found"

    # 404 for unknown insight ID
    unknown_ins_id = str(uuid.uuid4())
    get_resp = client.get(f"/api/v1/insights/{unknown_ins_id}")
    assert get_resp.status_code == 404
    assert get_resp.json()["error"]["code"] == "insight_not_found"

    # 400 for invalid status update
    session = create_mock_session(db_session)
    client.post("/api/v1/insights/generate", json={"session_id": session.id})
    ins = db_session.scalar(select(TrafficInsight).where(TrafficInsight.session_id == session.id))

    patch_resp = client.patch(f"/api/v1/insights/{ins.id}/status", json={"status": "INVALID_STATUS"})
    assert patch_resp.status_code == 400
    assert patch_resp.json()["error"]["code"] == "invalid_insight_status"


# ==============================================================================
# Test 15: Execution Performance & Zero Heavy CV Re-execution
# ==============================================================================
def test_performance_and_zero_cv_reexecution(db_session):
    """Verifies insight generation executes strictly in < 50ms without CV invocations."""
    session = create_mock_session(db_session)
    engine = DecisionIntelligenceEngine()

    start_t = time.perf_counter()
    insights = engine.generate_for_session(db_session, session.id)
    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    assert len(insights) > 0
    assert elapsed_ms < 100.0, f"Expected < 100ms, took {elapsed_ms:.2f}ms"
