"""
Unit and integration tests for Phase 15: Traffic Anomaly & Congestion Incident Detection.
Covers all 4 statistical detection rules, event lifecycle state tracking, provenance inheritance,
idempotent re-execution, REST API filtering, status updates, and anti-fabrication policies.
"""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import AnalysisSession, LaneResultRecord, TrafficMetricsRecord
from app.models.anomaly import AnomalyEvent
from app.models.video import Video
from app.services.anomaly.detector import AnomalyDetectionService


def utcnow():
    return datetime.now(timezone.utc)


# Isolated SQLite test database
TEST_DB_PATH = Path(tempfile.gettempdir()) / "test_phase15_anomalies.db"
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
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


def test_anomaly_info_endpoint(client: TestClient):
    """Verifies metadata endpoint returns 4 transparent rules and anti-fabrication policy."""
    resp = client.get("/api/v1/anomalies/info")
    assert resp.status_code == 200
    data = resp.json()

    assert data["version"] == "1.0.0"
    assert "Phase 15" in data["phase"]
    assert "Zero synthetic fabrication" in data["anti_fabrication_policy"]
    assert len(data["rules"]) == 4

    rule_types = {r["anomaly_type"] for r in data["rules"]}
    assert "congestion_buildup" in rule_types
    assert "abnormal_flow_drop" in rule_types
    assert "lane_imbalance" in rule_types
    assert "density_spike" in rule_types


def test_detect_congestion_buildup(db_session: Session):
    """Rule 1: Sustained occupancy above threshold creates congestion buildup event."""
    video = Video(
        id="vid_real_001",
        original_filename="real_traffic_junction.mp4",
        storage_path="uploads/vid_real_001.mp4",
        source_type="real_world",
        provenance_verified=True,
        source_reference="Urban DOT Cam 12",
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_cong_001",
        video_id="vid_real_001",
        total_vehicles_counted=45,
        total_vehicles_detected=50,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    # Lane 1 has peak occupancy 9 and avg 7.2 (exceeding default threshold of 5)
    lane = LaneResultRecord(
        analysis_session_id="sess_cong_001",
        lane_id="lane_north_01",
        lane_name="Northbound Lane 1",
        direction_hint="North",
        unique_vehicles_count=25,
        peak_occupancy=9,
        average_occupancy=7.2,
        image_space_density=0.0001,
        normalized_density_score=0.75,
        polygon_area_px2=50000.0,
    )
    db_session.add(lane)
    db_session.commit()

    service = AnomalyDetectionService()
    events = service.detect_and_persist_for_session(db_session, "sess_cong_001")

    assert len(events) >= 1
    cong_event = next(e for e in events if e.anomaly_type == "congestion_buildup")
    assert cong_event.session_id == "sess_cong_001"
    assert cong_event.lane_id == "lane_north_01"
    assert cong_event.trigger_value == 9.0
    assert cong_event.threshold_value == 5.0
    assert cong_event.deviation_pct == pytest.approx(80.0, 0.1)
    assert cong_event.severity in ["medium", "high"]
    assert cong_event.is_synthetic is False
    assert cong_event.provenance_category == "real_database_metrics"
    assert "Northbound Lane 1" in cong_event.title


def test_detect_abnormal_flow_drop(db_session: Session):
    """Rule 2: Flow collapse >= 50% relative to baseline triggers flow drop event."""
    video = Video(
        id="vid_synth_001",
        original_filename="synthetic_test.mp4",
        storage_path="uploads/vid_synth_001.mp4",
        source_type="synthetic_pipeline",
        provenance_verified=False,
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_flow_drop_001",
        video_id="vid_synth_001",
        total_vehicles_counted=30,
        total_vehicles_detected=35,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    # Buckets: steady flow at 60 veh/min, then sharp collapse to 12 veh/min (80% drop)
    buckets = [
        {"bucket_index": 0, "start_time_seconds": 0.0, "end_time_seconds": 10.0, "count": 10, "flow_rate_per_minute": 60.0},
        {"bucket_index": 1, "start_time_seconds": 10.0, "end_time_seconds": 20.0, "count": 10, "flow_rate_per_minute": 60.0},
        {"bucket_index": 2, "start_time_seconds": 20.0, "end_time_seconds": 30.0, "count": 2, "flow_rate_per_minute": 12.0},
    ]

    metrics = TrafficMetricsRecord(
        analysis_session_id="sess_flow_drop_001",
        total_volume=30,
        flow_rate_per_minute=44.0,
        flow_rate_per_hour=2640.0,
        observation_duration_seconds=30.0,
        time_series_buckets=buckets,
    )
    db_session.add(metrics)
    db_session.commit()

    service = AnomalyDetectionService()
    events = service.detect_and_persist_for_session(db_session, "sess_flow_drop_001")

    flow_event = next(e for e in events if e.anomaly_type == "abnormal_flow_drop")
    assert flow_event.session_id == "sess_flow_drop_001"
    assert flow_event.trigger_value == 2.0
    assert flow_event.threshold_value == 50.0  # 50% drop threshold
    assert flow_event.deviation_pct == pytest.approx(80.0, 0.1)
    assert flow_event.severity in ["high", "critical"]
    assert flow_event.is_synthetic is True
    assert flow_event.provenance_category == "synthetic_pipeline_metrics"
    assert flow_event.start_timestamp_seconds == 20.0


def test_detect_lane_imbalance(db_session: Session):
    """Rule 3: Occupancy ratio between max and min lane >= 3.0x triggers lane imbalance."""
    video = Video(
        id="vid_real_002",
        original_filename="arterial_corridor.mp4",
        storage_path="uploads/vid_real_002.mp4",
        source_type="real_world",
        provenance_verified=True,
        source_reference="City DOT Arterial Camera",
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_imbal_001",
        video_id="vid_real_002",
        total_vehicles_counted=60,
        total_vehicles_detected=70,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    # Lane 1 unique vehicles: 30, Lane 2 unique vehicles: 5 -> ratio = 6.0x
    l1 = LaneResultRecord(
        analysis_session_id="sess_imbal_001",
        lane_id="lane_left",
        lane_name="Left Turn Lane",
        unique_vehicles_count=30,
        peak_occupancy=10,
        average_occupancy=8.0,
        image_space_density=0.0001,
        normalized_density_score=0.8,
        polygon_area_px2=40000.0,
    )
    l2 = LaneResultRecord(
        analysis_session_id="sess_imbal_001",
        lane_id="lane_thru",
        lane_name="Through Lane",
        unique_vehicles_count=5,
        peak_occupancy=2,
        average_occupancy=1.6,
        image_space_density=0.00002,
        normalized_density_score=0.2,
        polygon_area_px2=40000.0,
    )
    db_session.add_all([l1, l2])
    db_session.commit()

    service = AnomalyDetectionService()
    events = service.detect_and_persist_for_session(db_session, "sess_imbal_001")

    imbal_event = next(e for e in events if e.anomaly_type == "lane_imbalance")
    assert imbal_event.session_id == "sess_imbal_001"
    assert imbal_event.trigger_value == pytest.approx(6.0, 0.1)
    assert imbal_event.severity in ["medium", "high", "critical"]
    assert "Left Turn Lane" in imbal_event.title or "Through Lane" in imbal_event.title


def test_detect_density_spike(db_session: Session):
    """Rule 4: Image-space density exceeding threshold triggers density spike with uncalibrated notice."""
    video = Video(
        id="vid_synth_002",
        original_filename="synthetic_density.mp4",
        storage_path="uploads/vid_synth_002.mp4",
        source_type="synthetic_pipeline",
        provenance_verified=False,
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_dens_001",
        video_id="vid_synth_002",
        total_vehicles_counted=15,
        total_vehicles_detected=20,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    # Image-space density: 0.0006 veh/px2 (exceeding default 0.00035)
    lane = LaneResultRecord(
        analysis_session_id="sess_dens_001",
        lane_id="lane_narrow",
        lane_name="Narrow Lane",
        peak_occupancy=6,
        average_occupancy=4.0,
        image_space_density=0.0006,
        normalized_density_score=0.9,
        polygon_area_px2=10000.0,
    )
    db_session.add(lane)
    db_session.commit()

    service = AnomalyDetectionService()
    events = service.detect_and_persist_for_session(db_session, "sess_dens_001")

    dens_event = next(e for e in events if e.anomaly_type == "density_spike")
    assert dens_event.session_id == "sess_dens_001"
    assert dens_event.trigger_value == 0.0006
    assert dens_event.threshold_value == 0.00035
    assert "uncalibrated camera perspective" in dens_event.description


def test_detector_idempotency_and_continuation(db_session: Session):
    """Running detector multiple times on same session updates rather than duplicates rows."""
    video = Video(
        id="vid_idem_001",
        original_filename="test_video.mp4",
        storage_path="uploads/vid_idem_001.mp4",
        source_type="real_world",
        provenance_verified=True,
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_idem_001",
        video_id="vid_idem_001",
        total_vehicles_counted=40,
        total_vehicles_detected=45,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    lane = LaneResultRecord(
        analysis_session_id="sess_idem_001",
        lane_id="lane_01",
        lane_name="Lane 1",
        peak_occupancy=8,
        average_occupancy=6.5,
        image_space_density=0.0001,
        normalized_density_score=0.7,
        polygon_area_px2=50000.0,
    )
    db_session.add(lane)
    db_session.commit()

    service = AnomalyDetectionService()

    # Pass 1
    events1 = service.detect_and_persist_for_session(db_session, "sess_idem_001")

    # Pass 2
    events2 = service.detect_and_persist_for_session(db_session, "sess_idem_001")
    all_events = list(db_session.scalars(select(AnomalyEvent).where(AnomalyEvent.session_id == "sess_idem_001")).all())

    assert len(events1) == len(events2)
    assert len(all_events) == len(events1)  # No duplicates created
    assert all_events[0].id == events1[0].id


def test_rest_api_events_filter_status_and_delete(client: TestClient, db_session: Session):
    """Tests REST API endpoints: GET /events, GET /events/{id}, PATCH /events/{id}/status, DELETE /events/{id}."""
    video = Video(
        id="vid_api_001",
        original_filename="api_test_feed.mp4",
        storage_path="uploads/vid_api_001.mp4",
        source_type="real_world",
        provenance_verified=True,
        source_reference="Traffic Monitoring Cam #4",
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_api_001",
        video_id="vid_api_001",
        total_vehicles_counted=50,
        total_vehicles_detected=55,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    lane = LaneResultRecord(
        analysis_session_id="sess_api_001",
        lane_id="lane_fast",
        lane_name="Fast Lane",
        peak_occupancy=10,
        average_occupancy=7.5,
        image_space_density=0.0001,
        normalized_density_score=0.8,
        polygon_area_px2=45000.0,
    )
    db_session.add(lane)
    db_session.commit()

    # 1. Trigger detection via POST /api/v1/anomalies/detect/{session_id}
    det_resp = client.post(f"/api/v1/anomalies/detect/sess_api_001")
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    assert det_data["anomalies_detected"] >= 1
    event_id = det_data["events"][0]["id"]

    # 2. List events via GET /api/v1/anomalies/events
    list_resp = client.get("/api/v1/anomalies/events?session_id=sess_api_001")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert list_data["active_count"] >= 1
    assert "real_database_metrics" in list_data["provenance_breakdown"]

    # 3. Get detail via GET /api/v1/anomalies/events/{id} with lineage
    detail_resp = client.get(f"/api/v1/anomalies/events/{event_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["video_id"] == "vid_api_001"
    assert detail["video_filename"] == "api_test_feed.mp4"
    assert detail["provenance_verified"] is True
    assert detail["source_reference"] == "Traffic Monitoring Cam #4"

    # 4. Acknowledge event via PATCH /api/v1/anomalies/events/{id}/status
    patch_resp = client.patch(
        f"/api/v1/anomalies/events/{event_id}/status",
        json={"status": "acknowledged", "note": "Operator dispatched signal check"},
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["status"] == "acknowledged"
    assert patch_data["details_json"]["operator_note"] == "Operator dispatched signal check"

    # 5. Resolve event
    resolve_resp = client.patch(
        f"/api/v1/anomalies/events/{event_id}/status",
        json={"status": "resolved", "note": "Traffic cleared"},
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"

    # 6. Delete event via DELETE /api/v1/anomalies/events/{id}
    del_resp = client.delete(f"/api/v1/anomalies/events/{event_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Verify 404 on deleted event
    assert client.get(f"/api/v1/anomalies/events/{event_id}").status_code == 404


def test_anti_fabrication_empty_session(db_session: Session):
    """Sessions with normal metrics or empty data produce 0 anomaly events (never fabricated)."""
    video = Video(
        id="vid_norm_001",
        original_filename="normal_traffic.mp4",
        storage_path="uploads/vid_norm_001.mp4",
        source_type="real_world",
        provenance_verified=True,
        source_reference="Camera 1",
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_norm_001",
        video_id="vid_norm_001",
        total_vehicles_counted=10,
        total_vehicles_detected=12,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    # Normal occupancy (avg: 2.0 < 5.0) and normal density
    lane = LaneResultRecord(
        analysis_session_id="sess_norm_001",
        lane_id="lane_norm",
        lane_name="Normal Lane",
        peak_occupancy=3,
        average_occupancy=2.0,
        image_space_density=0.00005,
        normalized_density_score=0.2,
        polygon_area_px2=40000.0,
    )
    db_session.add(lane)
    db_session.commit()

    service = AnomalyDetectionService()
    events = service.detect_and_persist_for_session(db_session, "sess_norm_001")

    assert len(events) == 0  # Zero fabricated events


def test_dynamic_configuration_changes_detection_behavior(db_session: Session):
    """Prove that passing different configuration parameters changes detection without code modifications."""
    video = Video(
        id="vid_cfg_001",
        original_filename="config_test.mp4",
        storage_path="uploads/vid_cfg_001.mp4",
        source_type="real_world",
        provenance_verified=True,
        source_reference="Config Test Cam",
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_cfg_001",
        video_id="vid_cfg_001",
        total_vehicles_counted=30,
        total_vehicles_detected=30,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    # Lane peak occupancy is 4
    lane = LaneResultRecord(
        analysis_session_id="sess_cfg_001",
        lane_id="lane_cfg",
        lane_name="Config Lane",
        peak_occupancy=4,
        average_occupancy=3.0,
        image_space_density=0.00005,
        normalized_density_score=0.3,
        polygon_area_px2=40000.0,
    )
    db_session.add(lane)
    db_session.commit()

    # Standard threshold 5 -> 0 events
    default_service = AnomalyDetectionService(congestion_occupancy_threshold=5)
    candidates_default = default_service.detect_for_session(session)
    assert len(candidates_default) == 0

    # Custom threshold 4 -> 1 event detected dynamically
    custom_service = AnomalyDetectionService(congestion_occupancy_threshold=4)
    candidates_custom = custom_service.detect_for_session(session)
    assert len(candidates_custom) == 1
    assert candidates_custom[0]["trigger_value"] == 4.0


def test_boundary_conditions_and_insufficient_data(db_session: Session):
    """Verifies exact threshold boundary, just below boundary, and insufficient data conditions."""
    video = Video(
        id="vid_bound_001",
        original_filename="boundary_test.mp4",
        storage_path="uploads/vid_bound_001.mp4",
        source_type="real_world",
        provenance_verified=True,
        source_reference="Boundary Cam",
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_bound_001",
        video_id="vid_bound_001",
        total_vehicles_counted=4,
        total_vehicles_detected=4,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    # Case 1: Lane imbalance with low total volume (< min_volume=5) -> insufficient data -> 0 events
    l1 = LaneResultRecord(
        analysis_session_id="sess_bound_001",
        lane_id="lane_b1",
        lane_name="Lane 1",
        unique_vehicles_count=3,
        peak_occupancy=3,
        average_occupancy=2.0,
        image_space_density=0.00002,
        normalized_density_score=0.2,
        polygon_area_px2=40000.0,
    )
    l2 = LaneResultRecord(
        analysis_session_id="sess_bound_001",
        lane_id="lane_b2",
        lane_name="Lane 2",
        unique_vehicles_count=0,
        peak_occupancy=0,
        average_occupancy=0.0,
        image_space_density=0.0,
        normalized_density_score=0.0,
        polygon_area_px2=40000.0,
    )
    db_session.add_all([l1, l2])
    db_session.commit()

    service = AnomalyDetectionService()
    candidates = service.detect_for_session(session)
    imbalance_events = [c for c in candidates if c["anomaly_type"] == "lane_imbalance"]
    assert len(imbalance_events) == 0, "Low total volume should not trigger lane imbalance"

    # Case 2: Exact boundary test for congestion (peak occupancy == 5) -> triggers low severity event
    l1.peak_occupancy = 5
    db_session.commit()
    candidates = service.detect_for_session(session)
    cong_events = [c for c in candidates if c["anomaly_type"] == "congestion_buildup"]
    assert len(cong_events) == 1
    assert cong_events[0]["trigger_value"] == 5.0
    assert cong_events[0]["severity"] == "low"

    # Case 3: Just below boundary test (peak occupancy == 4, density < 0.7) -> 0 events
    l1.peak_occupancy = 4
    l1.normalized_density_score = 0.69
    db_session.commit()
    candidates = service.detect_for_session(session)
    cong_events = [c for c in candidates if c["anomaly_type"] == "congestion_buildup"]
    assert len(cong_events) == 0


def test_five_stage_idempotency_and_condition_lifecycle(db_session: Session):
    """
    Proves all 5 lifecycle and idempotency stages with database evidence:
    A. First detection -> exactly 1 event created.
    B. Same session detected again -> still exactly 1 event.
    C. Continued condition -> same event ID updated with ongoing state.
    D. Recovery -> same event receives condition_state='recovered'.
    E. Recurrence at a later start time -> exactly 1 additional event created.
    """
    video = Video(
        id="vid_life_001",
        original_filename="lifecycle_test.mp4",
        storage_path="uploads/vid_life_001.mp4",
        source_type="real_world",
        provenance_verified=True,
        source_reference="Lifecycle Cam #1",
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_life_001",
        video_id="vid_life_001",
        total_vehicles_counted=50,
        total_vehicles_detected=55,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    lane = LaneResultRecord(
        analysis_session_id="sess_life_001",
        lane_id="lane_life_01",
        lane_name="Main Lane",
        peak_occupancy=6,
        average_occupancy=4.5,
        image_space_density=0.0001,
        normalized_density_score=0.6,
        polygon_area_px2=40000.0,
    )
    db_session.add(lane)
    db_session.commit()

    service = AnomalyDetectionService()

    # Stage A: First detection -> exactly 1 event
    events_a = service.detect_and_persist_for_session(db_session, "sess_life_001")
    assert len(events_a) == 1
    event_id = events_a[0].id

    # Stage B: Same session detected again -> still exactly 1 event
    events_b = service.detect_and_persist_for_session(db_session, "sess_life_001")
    all_b = list(db_session.scalars(select(AnomalyEvent).where(AnomalyEvent.session_id == "sess_life_001")).all())
    assert len(all_b) == 1
    assert all_b[0].id == event_id

    # Stage C: Continued anomaly -> same event ID updated to ongoing state
    lane.peak_occupancy = 8  # Severity increases
    db_session.commit()
    events_c = service.detect_and_persist_for_session(db_session, "sess_life_001")
    all_c = list(db_session.scalars(select(AnomalyEvent).where(AnomalyEvent.session_id == "sess_life_001")).all())
    assert len(all_c) == 1
    assert all_c[0].id == event_id
    assert all_c[0].trigger_value == 8.0
    assert all_c[0].details_json["condition_state"] == "ongoing"

    # Stage D: Recovery -> condition drops below threshold
    lane.peak_occupancy = 2
    lane.normalized_density_score = 0.2
    db_session.commit()
    events_d = service.detect_and_persist_for_session(db_session, "sess_life_001")
    all_d = list(db_session.scalars(select(AnomalyEvent).where(AnomalyEvent.session_id == "sess_life_001")).all())
    assert len(all_d) == 1
    assert all_d[0].id == event_id
    assert all_d[0].details_json["condition_state"] == "recovered"
    assert "recovered_at" in all_d[0].details_json

    # Stage E: Recurrence -> new session or recurrence creates a 2nd distinct event
    session2 = AnalysisSession(
        id="sess_life_002",
        video_id="vid_life_001",
        total_vehicles_counted=60,
        total_vehicles_detected=65,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session2)
    lane2 = LaneResultRecord(
        analysis_session_id="sess_life_002",
        lane_id="lane_life_01",
        lane_name="Main Lane",
        peak_occupancy=9,
        average_occupancy=6.0,
        image_space_density=0.0001,
        normalized_density_score=0.8,
        polygon_area_px2=40000.0,
    )
    db_session.add(lane2)
    db_session.commit()

    events_e = service.detect_and_persist_for_session(db_session, "sess_life_002")
    assert len(events_e) == 1
    assert events_e[0].id != event_id  # Brand new event created for recurrence


def test_provenance_inheritance_mix(db_session: Session):
    """
    Verifies that provenance is strictly inherited and unverified/unknown data never becomes real:
    - Real + Verified + Source Reference -> 'real_database_metrics', is_synthetic=False
    - Real + Unverified -> 'synthetic_fixture', is_synthetic=True
    - Synthetic Pipeline -> 'synthetic_pipeline_metrics', is_synthetic=True
    """
    service = AnomalyDetectionService()

    # 1. Real verified
    v_real = Video(
        id="v_real", original_filename="a.mp4", storage_path="a.mp4",
        source_type="real_world", provenance_verified=True, source_reference="DOT Cam 1", status="ready"
    )
    s_real = AnalysisSession(id="s_real", video_id="v_real", status="completed", started_at=utcnow(), completed_at=utcnow())
    s_real.video = v_real
    cat, synth = service._resolve_provenance(s_real)
    assert cat == "real_database_metrics"
    assert synth is False

    # 2. Real unverified (missing provenance_verified or source_reference) -> NEVER REAL
    v_unver = Video(
        id="v_unver", original_filename="b.mp4", storage_path="b.mp4",
        source_type="real_world", provenance_verified=False, status="ready"
    )
    s_unver = AnalysisSession(id="s_unver", video_id="v_unver", status="completed", started_at=utcnow(), completed_at=utcnow())
    s_unver.video = v_unver
    cat, synth = service._resolve_provenance(s_unver)
    assert cat != "real_database_metrics"
    assert synth is True

    # 3. Synthetic pipeline
    v_synth = Video(
        id="v_synth", original_filename="c.mp4", storage_path="c.mp4",
        source_type="synthetic_pipeline", provenance_verified=False, status="ready"
    )
    s_synth = AnalysisSession(id="s_synth", video_id="v_synth", status="completed", started_at=utcnow(), completed_at=utcnow())
    s_synth.video = v_synth
    cat, synth = service._resolve_provenance(s_synth)
    assert cat == "synthetic_pipeline_metrics"
    assert synth is True


def test_dashboard_access_has_zero_side_effects(client: TestClient, db_session: Session):
    """
    Accessing the Dashboard summary endpoint must NEVER trigger anomaly detection,
    CV models, or create new database records.
    """
    video = Video(
        id="vid_dash_001",
        original_filename="dash_test.mp4",
        storage_path="uploads/vid_dash_001.mp4",
        source_type="real_world",
        provenance_verified=True,
        source_reference="Dash Cam",
        status="ready",
    )
    db_session.add(video)
    db_session.commit()

    session = AnalysisSession(
        id="sess_dash_001",
        video_id="vid_dash_001",
        total_vehicles_counted=20,
        total_vehicles_detected=25,
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    db_session.add(session)
    db_session.commit()

    # Pre-check: 0 anomaly events in database
    pre_events = list(db_session.scalars(select(AnomalyEvent)).all())
    assert len(pre_events) == 0

    # Query Dashboard Summary
    resp = client.get("/api/v1/dashboard/summary?session_id=sess_dash_001")
    assert resp.status_code == 200

    # Post-check: Still 0 anomaly events in database (read-only aggregation)
    post_events = list(db_session.scalars(select(AnomalyEvent)).all())
    assert len(post_events) == 0

