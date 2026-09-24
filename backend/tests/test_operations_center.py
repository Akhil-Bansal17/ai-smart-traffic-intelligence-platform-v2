"""
Unit and integration tests for Unified Traffic Operations Center.
Phase 23: Unified Traffic Operations Center & Real-Time Incident Response.
"""
from datetime import datetime, timedelta, timezone
from typing import Generator
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import AnalysisSession, TrafficMetricsRecord
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.anomaly import AnomalyEvent
from app.models.camera_source import CameraSource, CameraSourceStatus, CameraSourceType
from app.models.insight import InsightCategory, InsightSeverity, InsightStatus, TrafficInsight
from app.models.report import Report, ReportFormat, ReportScopeType, ReportStatus
from app.models.video import Video
from app.schemas.operations import CameraHealthStatus
from app.services.cv.live_analysis_service import LiveMetricsSnapshot
from app.services.operations.service import OperationsCenterService


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


import tempfile
from pathlib import Path

TEST_DB_PATH = Path(tempfile.gettempdir()) / f"test_phase23_ops_{uuid.uuid4().hex[:8]}.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine, future=True)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink(missing_ok=True)
        except Exception:
            pass


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class MockJobManager:
    """Mock job manager for simulating live stream telemetry."""
    def __init__(self, snapshots=None, previews=None):
        self._snapshots = snapshots or {}
        self._previews = previews or {}

    def get_live_status(self, camera_source_id: str):
        return self._snapshots.get(camera_source_id)

    def get_preview_jpeg(self, camera_source_id: str):
        return self._previews.get(camera_source_id)


def test_operations_overview_empty_db(db_session: Session, client: TestClient):
    """Test Operations Center overview on empty database with zero records."""
    res = client.get("/api/v1/operations/overview")
    assert res.status_code == 200
    data = res.json()

    assert data["system_health"] == "healthy"
    assert data["database_connected"] is True
    assert data["active_cameras_count"] == 0
    assert data["total_cameras_count"] == 0
    assert data["active_incidents_count"] == 0
    assert data["critical_incidents_count"] == 0
    assert data["active_insights_count"] == 0
    assert len(data["cameras"]) == 0
    assert len(data["active_incidents"]) == 0
    assert data["traffic_snapshot"]["data_status"] == "UNAVAILABLE"
    assert data["traffic_snapshot"]["flow_rate_tag"] == "UNAVAILABLE"
    assert data["provenance_summary"]["provenance_label"] == "UNAVAILABLE"

    # Simulation and forecasting boundary assertions
    assert data["simulation_support"]["signal_optimization"]["is_simulation_only"] is True
    assert data["simulation_support"]["emergency_corridor"]["is_simulation_only"] is True
    assert data["prediction_support"]["status"] == "unavailable"
    assert "insufficient" in data["prediction_support"]["message"].lower()


def test_operations_overview_camera_telemetry_and_redaction(db_session: Session, client: TestClient):
    """Verify live camera telemetry aggregation, health states, and credential redaction."""
    now = utcnow()

    # Create real RTSP camera with sensitive embedded credentials
    cam_rtsp = CameraSource(
        id=str(uuid.uuid4()),
        name="Northway Expressway Cam 01",
        source_type=CameraSourceType.RTSP.value,
        connection_uri="rtsp://admin:superSecret99@10.0.0.50:554/stream1",
        status=CameraSourceStatus.CONNECTED.value,
        enabled=True,
        fps=30.0,
    )
    # Create disconnected local camera
    cam_local = CameraSource(
        id=str(uuid.uuid4()),
        name="Main St Intersection Local Cam",
        source_type=CameraSourceType.LOCAL_CAMERA.value,
        connection_uri="0",
        status=CameraSourceStatus.DISCONNECTED.value,
        enabled=True,
        fps=15.0,
    )
    # Create test fixture camera
    cam_fixture = CameraSource(
        id=str(uuid.uuid4()),
        name="Downtown Test Fixture Cam",
        source_type=CameraSourceType.TEST_FIXTURE.value,
        connection_uri="fixture://synthetic_downtown_loop",
        status=CameraSourceStatus.STOPPED.value,
        enabled=True,
    )
    db_session.add_all([cam_rtsp, cam_local, cam_fixture])
    db_session.commit()

    # Set up mock live telemetry for the RTSP camera
    mock_snapshot = LiveMetricsSnapshot(
        camera_source_id=cam_rtsp.id,
        job_id="job-live-001",
        job_status="running",
        is_live=True,
        source_type=cam_rtsp.source_type,
        source_fps=30.0,
        processing_fps=5.0,
        frames_acquired=150,
        frames_processed=150,
        dropped_frames=0,
        reconnect_count=0,
        total_volume=42,
        inbound_volume=25,
        outbound_volume=17,
        active_tracks_count=8,
        class_distribution={"car": 35, "truck": 5, "bus": 2},
        direction_distribution={"inbound": 25, "outbound": 17},
        lane_occupancies={"lane_1": 4, "lane_2": 2},
        lane_densities={"lane_1": 0.00015, "lane_2": 0.00008},
        provenance_tag="live_observation",
        last_frame_timestamp=100.5,
        last_updated=now,
    )

    overview = OperationsCenterService.get_overview(
        db=db_session,
        manager=MockJobManager(snapshots={cam_rtsp.id: mock_snapshot}, previews={cam_rtsp.id: b"fake_jpeg"}),
    )

    assert overview.total_cameras_count == 3
    assert overview.active_cameras_count == 1

    # Check RTSP camera properties
    rtsp_item = next(c for c in overview.cameras if c.id == cam_rtsp.id)
    assert rtsp_item.health_status == CameraHealthStatus.ONLINE
    assert "superSecret99" not in rtsp_item.connection_uri_redacted
    assert "***" in rtsp_item.connection_uri_redacted
    assert rtsp_item.current_vehicle_count == 42
    assert rtsp_item.active_tracks_count == 8
    assert rtsp_item.has_preview is True

    # Check local camera is OFFLINE
    local_item = next(c for c in overview.cameras if c.id == cam_local.id)
    assert local_item.health_status == CameraHealthStatus.OFFLINE
    assert local_item.is_active is False

    # Check traffic snapshot aggregated live data
    assert overview.traffic_snapshot.active_sources_count == 1
    assert overview.traffic_snapshot.total_active_tracks == 8
    assert overview.traffic_snapshot.observed_vehicle_volume == 42
    assert overview.traffic_snapshot.directional_split == {"inbound": 25, "outbound": 17}
    assert overview.traffic_snapshot.flow_rate_tag in ("OBSERVED", "EXTRAPOLATED")


def test_operations_incident_panel_and_filtering(db_session: Session, client: TestClient):
    """Verify active incident listing, critical incident counts, and multi-parameter filtering."""
    now = utcnow()

    # Parent video and analysis session
    video = Video(
        id=str(uuid.uuid4()),
        original_filename="traffic_corridor_test.mp4",
        storage_path="/tmp/traffic_corridor_test.mp4",
        source_type="real_world",
        provenance_verified=True,
    )
    cam = CameraSource(
        id=str(uuid.uuid4()),
        name="Harbor Bridge Northbound",
        source_type=CameraSourceType.RTSP.value,
        connection_uri="rtsp://10.0.0.10:554/live",
    )
    session = AnalysisSession(
        id=str(uuid.uuid4()),
        video_id=video.id,
        camera_source_id=cam.id,
        session_mode="live_monitoring",
        status="completed",
    )
    db_session.add_all([video, cam, session])
    db_session.commit()

    # Create 3 incidents: 1 critical open, 1 medium acknowledged, 1 low resolved
    inc_crit = AnomalyEvent(
        id=str(uuid.uuid4()),
        session_id=session.id,
        anomaly_type="congestion_buildup",
        severity="critical",
        status="open",
        title="Severe Gridlock on Harbor Bridge",
        description="Sustained queueing exceeding 25 vehicles",
        start_timestamp_seconds=10.0,
        duration_seconds=45.0,
        metric_name="queue_length",
        trigger_value=28.0,
        threshold_value=15.0,
        lane_id="lane_fast",
        provenance_category="real_database_metrics",
        is_synthetic=False,
    )
    inc_med = AnomalyEvent(
        id=str(uuid.uuid4()),
        session_id=session.id,
        anomaly_type="lane_imbalance",
        severity="medium",
        status="acknowledged",
        title="Lane 1 vs Lane 2 Imbalance",
        description="Lane skew ratio 4.2x",
        start_timestamp_seconds=20.0,
        duration_seconds=30.0,
        metric_name="lane_volume_ratio",
        trigger_value=4.2,
        threshold_value=3.0,
        lane_id="lane_slow",
        provenance_category="real_database_metrics",
        is_synthetic=False,
        details_json={"operator_note": "Investigating construction barrier"},
    )
    inc_res = AnomalyEvent(
        id=str(uuid.uuid4()),
        session_id=session.id,
        anomaly_type="density_spike",
        severity="low",
        status="resolved",
        title="Transient Density Surge",
        description="Brief platoon spike",
        start_timestamp_seconds=5.0,
        duration_seconds=10.0,
        metric_name="vehicle_density",
        trigger_value=0.00045,
        threshold_value=0.00035,
        resolved_at=now,
    )
    db_session.add_all([inc_crit, inc_med, inc_res])
    db_session.commit()

    # 1. Overview should list only OPEN and ACKNOWLEDGED incidents (total 2)
    overview_res = client.get("/api/v1/operations/overview")
    assert overview_res.status_code == 200
    overview_data = overview_res.json()

    assert overview_data["active_incidents_count"] == 2
    assert overview_data["critical_incidents_count"] == 1
    active_ids = [inc["id"] for inc in overview_data["active_incidents"]]
    assert inc_crit.id in active_ids
    assert inc_med.id in active_ids
    assert inc_res.id not in active_ids

    # 2. Filter incidents list by status=resolved
    res_filt = client.get("/api/v1/operations/incidents?status=resolved")
    assert res_filt.status_code == 200
    data_filt = res_filt.json()
    assert data_filt["total"] == 1
    assert data_filt["incidents"][0]["id"] == inc_res.id

    # 3. Filter incidents list by severity=critical
    res_crit = client.get("/api/v1/operations/incidents?severity=critical")
    assert res_crit.status_code == 200
    data_crit = res_crit.json()
    assert data_crit["total"] == 1
    assert data_crit["incidents"][0]["id"] == inc_crit.id
    assert data_crit["incidents"][0]["camera_name"] == "Harbor Bridge Northbound"


def test_operations_incident_detail_and_status_mutation(db_session: Session, client: TestClient):
    """Test incident detail inspection and operator status transition (Phase 15 lifecycle)."""
    session = AnalysisSession(
        id=str(uuid.uuid4()),
        session_mode="file_analysis",
        status="completed",
    )
    db_session.add(session)
    db_session.commit()

    inc = AnomalyEvent(
        id=str(uuid.uuid4()),
        session_id=session.id,
        anomaly_type="abnormal_flow_drop",
        severity="high",
        status="open",
        title="Sudden Traffic Halt",
        description="Flow collapsed by 70%",
        metric_name="flow_rate",
        trigger_value=5.0,
        threshold_value=20.0,
        duration_seconds=35.0,
    )
    db_session.add(inc)
    db_session.commit()

    # 1. Detail endpoint
    detail_res = client.get(f"/api/v1/operations/incidents/{inc.id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == inc.id
    assert detail["title"] == "Sudden Traffic Halt"
    assert detail["status"] == "open"

    # 2. Acknowledge with operator note
    patch_ack = client.patch(
        f"/api/v1/operations/incidents/{inc.id}/status",
        json={"status": "acknowledged", "note": "Dispatching patrol unit to verify obstruction"},
    )
    assert patch_ack.status_code == 200
    ack_data = patch_ack.json()
    assert ack_data["status"] == "acknowledged"
    assert ack_data["operator_note"] == "Dispatching patrol unit to verify obstruction"

    # 3. Resolve incident
    patch_res = client.patch(
        f"/api/v1/operations/incidents/{inc.id}/status",
        json={"status": "resolved", "note": "Stalled vehicle cleared, normal flow resumed"},
    )
    assert patch_res.status_code == 200
    res_data = patch_res.json()
    assert res_data["status"] == "resolved"
    assert res_data["resolved_at"] is not None

    # 4. Reject invalid status
    patch_bad = client.patch(
        f"/api/v1/operations/incidents/{inc.id}/status",
        json={"status": "invalid_status_xyz"},
    )
    assert patch_bad.status_code == 400


def test_operations_event_timeline(db_session: Session, client: TestClient):
    """Verify chronological event aggregation from authoritative records with zero fabrication."""
    now = utcnow()

    # 1. Anomaly event
    session = AnalysisSession(id=str(uuid.uuid4()), session_mode="file_analysis", status="completed")
    db_session.add(session)
    db_session.commit()

    inc = AnomalyEvent(
        id=str(uuid.uuid4()),
        session_id=session.id,
        anomaly_type="congestion_buildup",
        severity="medium",
        status="acknowledged",
        title="Approaching Tunnel Congestion",
        description="Queue building up",
        metric_name="occupancy",
        trigger_value=12.0,
        threshold_value=8.0,
        created_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=5),
    )
    # 2. Analysis Job
    job = AnalysisJob(
        id=str(uuid.uuid4()),
        job_mode="file_analysis",
        status=JobStatus.COMPLETED.value,
        frames_processed=100,
        created_at=now - timedelta(minutes=15),
        completed_at=now - timedelta(minutes=14),
    )
    # 3. Traffic Insight
    insight = TrafficInsight(
        id=str(uuid.uuid4()),
        session_id=session.id,
        insight_type="CONGESTION_APPROACH",
        category=InsightCategory.CONGESTION.value,
        severity=InsightSeverity.HIGH.value,
        status=InsightStatus.ACTIVE.value,
        title="High Density Alert on Tunnel Approach",
        summary="Sustained queueing observed on approach lanes.",
        dedup_signature="sig-timeline-test-001",
        created_at=now - timedelta(minutes=8),
    )
    # 4. Report
    rep = Report(
        id=str(uuid.uuid4()),
        session_id=session.id,
        title="Shift Summary PDF Report",
        format=ReportFormat.PDF.value,
        scope_type=ReportScopeType.SESSION.value,
        status=ReportStatus.COMPLETED.value,
        created_at=now - timedelta(minutes=2),
    )
    db_session.add_all([inc, job, insight, rep])
    db_session.commit()

    timeline_res = client.get("/api/v1/operations/timeline?limit=20")
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()["events"]

    assert len(timeline) >= 4
    # Chronological sort: newest first
    timestamps = [datetime.fromisoformat(ev["timestamp"]) for ev in timeline]
    assert timestamps == sorted(timestamps, reverse=True)

    event_types = [ev["event_type"] for ev in timeline]
    assert "report_generated" in event_types
    assert "insight_generated" in event_types
    assert "incident_started" in event_types
    assert "job_completed" in event_types


def test_operations_historical_context_endpoint(db_session: Session, client: TestClient):
    """Test retrospective historical context retrieval via Phase 22 service."""
    cam = CameraSource(
        id=str(uuid.uuid4()),
        name="Airport Expressway Camera",
        source_type=CameraSourceType.TEST_FIXTURE.value,
        connection_uri="fixture://airport_cam",
    )
    db_session.add(cam)
    db_session.commit()

    res = client.get(f"/api/v1/operations/context/{cam.id}?time_window=7d")
    assert res.status_code == 200
    ctx = res.json()

    assert ctx["source_id"] == cam.id
    assert ctx["source_name"] == "Airport Expressway Camera"
    assert ctx["time_window"] == "7d"
    assert ctx["forecast_status"] == "UNAVAILABLE"
    assert "20" in ctx["forecast_reason"]  # Phase 11 threshold N=20


def test_operations_provenance_isolation_and_fixture_warning(db_session: Session):
    """Test strict epistemic isolation: test fixtures produce TEST FIXTURE or MIXED provenance label."""
    now = utcnow()

    # Case 1: All cameras are test fixtures
    cam_fixture = CameraSource(
        id=str(uuid.uuid4()),
        name="Synthetic Camera 01",
        source_type=CameraSourceType.TEST_FIXTURE.value,
        connection_uri="fixture://test1",
    )
    db_session.add(cam_fixture)
    db_session.commit()

    overview = OperationsCenterService.get_overview(db=db_session, manager=MockJobManager())
    assert overview.provenance_summary.provenance_label == "TEST FIXTURE"
    assert overview.provenance_summary.is_synthetic is True
    assert overview.provenance_summary.mix_warning is not None
    assert "test fixture" in overview.provenance_summary.mix_warning.lower()

    # Case 2: Add a real RTSP camera -> turns into MIXED
    cam_real = CameraSource(
        id=str(uuid.uuid4()),
        name="Real Harbor RTSP Cam",
        source_type=CameraSourceType.RTSP.value,
        connection_uri="rtsp://10.0.0.1/live",
    )
    db_session.add(cam_real)
    db_session.commit()

    overview_mixed = OperationsCenterService.get_overview(db=db_session, manager=MockJobManager())
    assert overview_mixed.provenance_summary.provenance_label == "MIXED"
    assert overview_mixed.provenance_summary.is_mixed is True


def test_operations_camera_degraded_and_connecting_health(db_session: Session):
    """Test camera health determination: DEGRADED on frame drops/errors, CONNECTING when queued."""
    now = utcnow()

    # Camera 1: High dropped frames -> DEGRADED
    cam_drop = CameraSource(
        id=str(uuid.uuid4()),
        name="Degraded Camera (High Drops)",
        source_type=CameraSourceType.RTSP.value,
        connection_uri="rtsp://10.0.0.2/stream",
        enabled=True,
    )
    # Camera 2: Queued job -> CONNECTING
    cam_queue = CameraSource(
        id=str(uuid.uuid4()),
        name="Queued Camera",
        source_type=CameraSourceType.HTTP_STREAM.value,
        connection_uri="http://10.0.0.3/video.mjpg",
        enabled=True,
    )
    job_queue = AnalysisJob(
        id=str(uuid.uuid4()),
        camera_source_id=cam_queue.id,
        job_mode="live_analysis",
        status=JobStatus.QUEUED.value,
    )
    db_session.add_all([cam_drop, cam_queue, job_queue])
    db_session.commit()

    snapshot_drop = LiveMetricsSnapshot(
        camera_source_id=cam_drop.id,
        job_id="job-drop",
        job_status="running",
        is_live=True,
        source_type="rtsp",
        source_fps=25.0,
        processing_fps=4.0,
        frames_acquired=200,
        frames_processed=160,
        dropped_frames=40,  # > 20 threshold
        reconnect_count=0,
        total_volume=10,
        inbound_volume=5,
        outbound_volume=5,
        active_tracks_count=2,
        class_distribution={},
        direction_distribution={},
        lane_occupancies={},
        lane_densities={},
        provenance_tag="live_observation",
        last_frame_timestamp=100.0,
        last_updated=now,
    )

    overview = OperationsCenterService.get_overview(
        db=db_session,
        manager=MockJobManager(snapshots={cam_drop.id: snapshot_drop}),
    )

    drop_item = next(c for c in overview.cameras if c.id == cam_drop.id)
    assert drop_item.health_status == CameraHealthStatus.DEGRADED

    queue_item = next(c for c in overview.cameras if c.id == cam_queue.id)
    assert queue_item.health_status == CameraHealthStatus.CONNECTING


def test_operations_timeline_filtering_and_bounds(db_session: Session, client: TestClient):
    """Test timeline event_type filtering and maximum limit bounds."""
    now = utcnow()
    session = AnalysisSession(id=str(uuid.uuid4()), session_mode="file_analysis", status="completed")
    db_session.add(session)
    db_session.commit()

    # Create 3 incidents
    for i in range(3):
        db_session.add(
            AnomalyEvent(
                id=str(uuid.uuid4()),
                session_id=session.id,
                anomaly_type=f"congestion_buildup_{i}",
                severity="medium",
                status="open",
                title=f"Incident {i}",
                description=f"Description {i}",
                metric_name="occupancy",
                trigger_value=10.0 + i,
                threshold_value=5.0,
                created_at=now - timedelta(minutes=i),
            )
        )
    # Create 1 report
    db_session.add(
        Report(
            id=str(uuid.uuid4()),
            session_id=session.id,
            title="Periodic Audit Report",
            format=ReportFormat.CSV.value,
            scope_type=ReportScopeType.SESSION.value,
            status=ReportStatus.COMPLETED.value,
            created_at=now - timedelta(minutes=10),
        )
    )
    db_session.commit()

    # Filter by incident_started
    res_inc = client.get("/api/v1/operations/timeline?event_type=incident_started")
    assert res_inc.status_code == 200
    events_inc = res_inc.json()["events"]
    assert all(ev["event_type"] == "incident_started" for ev in events_inc)

    # Filter by report_generated
    res_rep = client.get("/api/v1/operations/timeline?event_type=report_generated")
    assert res_rep.status_code == 200
    events_rep = res_rep.json()["events"]
    assert len(events_rep) == 1
    assert events_rep[0]["event_type"] == "report_generated"

