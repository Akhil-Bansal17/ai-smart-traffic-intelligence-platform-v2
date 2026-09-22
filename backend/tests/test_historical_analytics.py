"""
Unit and integration tests for Historical Traffic Intelligence & Trend Analysis.
Phase 22: Historical Traffic Intelligence & Trend Analysis.
"""
from datetime import datetime, timedelta, timezone
import uuid
from typing import Generator

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.core.exceptions import AppException
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import (
    AnalysisSession,
    LaneResultRecord,
    TrafficMetricsRecord,
)
from app.models.anomaly import AnomalyEvent
from app.models.camera_source import CameraSource, CameraSourceStatus, CameraSourceType
from app.models.video import Video
from app.schemas.historical_analytics import HistoricalFilterParams
from app.services.analytics.historical_analytics_service import (
    HistoricalAnalyticsService,
    SUPPORTED_VEHICLE_CLASSES,
    TIE_BREAKING_RULE_DESC,
)


from pathlib import Path
import tempfile

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


TEST_DB_PATH = Path(tempfile.gettempdir()) / f"test_phase22_hist_{uuid.uuid4().hex[:8]}.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)


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


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides isolated DB session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden database dependency."""
    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_mock_historical_data(db: Session, base_time: datetime) -> Dict[str, Any]:
    """Creates a deterministic multi-source, multi-session dataset for testing."""
    # 1. Real Camera Source
    camera_real = CameraSource(
        id=str(uuid.uuid4()),
        name="Main Intersection Camera",
        source_type="local_camera",
        connection_uri="http://camera.local/stream",
        status="connected",
        location_name="North Corridor",
    )
    # 2. Test Fixture Camera Source
    camera_fixture = CameraSource(
        id=str(uuid.uuid4()),
        name="Fixture Camera",
        source_type="test_fixture",
        connection_uri="fixture://test_stream",
        status="connected",
        location_name="Simulation Lab",
    )
    # 3. Verified Real-World Video
    video_real = Video(
        id=str(uuid.uuid4()),
        original_filename="arterial_peak.mp4",
        storage_path="/tmp/real_traffic.mp4",
        source_type="real_world",
        provenance_verified=True,
    )
    # 4. Synthetic Video
    video_synth = Video(
        id=str(uuid.uuid4()),
        original_filename="synthetic_sim.mp4",
        storage_path="/tmp/synthetic_test.mp4",
        source_type="synthetic_test",
        provenance_verified=False,
    )
    db.add_all([camera_real, camera_fixture, video_real, video_synth])
    db.commit()

    # Session 1: Real Camera, 1 hour ago, 30 vehicles over 600s (10 min)
    s1_time = base_time - timedelta(hours=2)
    s1 = AnalysisSession(
        id=str(uuid.uuid4()),
        camera_source_id=camera_real.id,
        session_mode="live_monitoring",
        status="completed",
        started_at=s1_time,
        completed_at=s1_time + timedelta(seconds=600),
        total_vehicles_counted=30,
        total_vehicles_detected=35,
    )
    db.add(s1)
    db.commit()

    m1 = TrafficMetricsRecord(
        analysis_session_id=s1.id,
        observation_duration_seconds=600.0,
        total_volume=30,
        flow_rate_per_minute=3.0,
        flow_rate_per_hour=180.0,
        is_extrapolated=True,
        class_distribution=[
            {"class_name": "car", "count": 20, "percentage": 66.7},
            {"class_name": "truck", "count": 6, "percentage": 20.0},
            {"class_name": "bus", "count": 4, "percentage": 13.3},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 18, "percentage": 60.0},
            {"direction": "outbound", "count": 12, "percentage": 40.0},
        ],
    )
    lr1_a = LaneResultRecord(
        analysis_session_id=s1.id,
        lane_id="lane_1",
        lane_name="Northbound Left",
        direction_hint="inbound",
        unique_vehicles_count=18,
        average_occupancy=2.5,
        peak_occupancy=5,
        image_space_density=0.00025,
        normalized_density_score=0.65,
        density_unit="vehicles/px²",
        density_calibration_warning="Uncalibrated image-space density",
    )
    lr1_b = LaneResultRecord(
        analysis_session_id=s1.id,
        lane_id="lane_2",
        lane_name="Northbound Right",
        direction_hint="inbound",
        unique_vehicles_count=12,
        average_occupancy=1.8,
        peak_occupancy=3,
        image_space_density=0.00015,
        normalized_density_score=0.45,
        density_unit="vehicles/px²",
        density_calibration_warning="Uncalibrated image-space density",
    )
    anom1 = AnomalyEvent(
        id=str(uuid.uuid4()),
        session_id=s1.id,
        anomaly_type="congestion",
        severity="medium",
        status="open",
        title="Localized Queue Buildup",
        description="Occupancy threshold exceeded on lane_1",
        metric_name="average_occupancy",
        trigger_value=5.0,
        threshold_value=4.0,
        lane_id="lane_1",
        duration_seconds=45.0,
    )
    db.add_all([m1, lr1_a, lr1_b, anom1])
    db.commit()

    # Session 2: Real Video, 30 min ago, 60 vehicles over 1200s (20 min)
    s2_time = base_time - timedelta(hours=1)
    s2 = AnalysisSession(
        id=str(uuid.uuid4()),
        video_id=video_real.id,
        session_mode="file_analysis",
        status="completed",
        started_at=s2_time,
        completed_at=s2_time + timedelta(seconds=1200),
        total_vehicles_counted=60,
        total_vehicles_detected=70,
    )
    db.add(s2)
    db.commit()

    m2 = TrafficMetricsRecord(
        analysis_session_id=s2.id,
        observation_duration_seconds=1200.0,
        total_volume=60,
        flow_rate_per_minute=3.0,
        flow_rate_per_hour=180.0,
        is_extrapolated=True,
        class_distribution=[
            {"class_name": "car", "count": 45, "percentage": 75.0},
            {"class_name": "motorcycle", "count": 10, "percentage": 16.7},
            {"class_name": "bicycle", "count": 5, "percentage": 8.3},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 30, "percentage": 50.0},
            {"direction": "outbound", "count": 30, "percentage": 50.0},
        ],
    )
    db.add(m2)
    db.commit()

    # Session 3: Fixture Camera (synthetic test fixture), 5 vehicles
    s3_time = base_time - timedelta(minutes=15)
    s3 = AnalysisSession(
        id=str(uuid.uuid4()),
        camera_source_id=camera_fixture.id,
        session_mode="live_monitoring",
        status="completed",
        started_at=s3_time,
        completed_at=s3_time + timedelta(seconds=300),
        total_vehicles_counted=5,
        total_vehicles_detected=5,
    )
    db.add(s3)
    db.commit()

    m3 = TrafficMetricsRecord(
        analysis_session_id=s3.id,
        observation_duration_seconds=300.0,
        total_volume=5,
        flow_rate_per_minute=1.0,
        flow_rate_per_hour=60.0,
        is_extrapolated=True,
        class_distribution=[{"class_name": "car", "count": 5, "percentage": 100.0}],
    )
    db.add(m3)
    db.commit()

    return {
        "camera_real": camera_real,
        "camera_fixture": camera_fixture,
        "video_real": video_real,
        "video_synth": video_synth,
        "s1": s1,
        "s2": s2,
        "s3": s3,
    }


# =============================================================================
# 1. Date Range & Bounds Validation Tests
# =============================================================================

def test_resolve_time_window_presets():
    """Verify that preset strings resolve to deterministic UTC time windows."""
    p24h = HistoricalFilterParams(time_preset="24h")
    s, e = HistoricalAnalyticsService.resolve_time_window(p24h)
    assert (e - s).total_seconds() == pytest.approx(86400, abs=5)

    p7d = HistoricalFilterParams(time_preset="7d")
    s7, e7 = HistoricalAnalyticsService.resolve_time_window(p7d)
    assert (e7 - s7).days == 7


def test_invalid_date_range_rejected():
    """Verify rejection when start_time > end_time."""
    now = utcnow()
    params = HistoricalFilterParams(
        time_preset="custom",
        start_time=now + timedelta(days=1),
        end_time=now,
    )
    with pytest.raises(AppException) as exc_info:
        HistoricalAnalyticsService.resolve_time_window(params)
    assert exc_info.value.code == "INVALID_DATE_RANGE"


def test_date_range_exceeds_max_limit_rejected():
    """Verify rejection when date range exceeds max_historical_range_days (90 days)."""
    now = utcnow()
    params = HistoricalFilterParams(
        time_preset="custom",
        start_time=now - timedelta(days=95),
        end_time=now,
    )
    with pytest.raises(AppException) as exc_info:
        HistoricalAnalyticsService.resolve_time_window(params)
    assert exc_info.value.code == "DATE_RANGE_EXCEEDS_LIMIT"


# =============================================================================
# 2. Aggregation Math & Flow Normalization Tests
# =============================================================================

def test_summary_aggregation_math(db_session: Session):
    """Verify sum of volume, duration, flow rates, and extrapolation flag."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    params = HistoricalFilterParams(
        time_preset="custom",
        start_time=now - timedelta(hours=3),
        end_time=now,
        include_synthetic=False,  # Excludes fixture session s3
    )
    summary = HistoricalAnalyticsService.get_summary(db_session, params)

    # s1: 30 veh, 600s; s2: 60 veh, 1200s -> total volume 90, total duration 1800s
    assert summary.total_observed_volume == 90
    assert summary.observation_duration_seconds == 1800.0
    # Flow rate per min: 90 / (1800 / 60) = 90 / 30 = 3.0 veh/min
    assert summary.flow_rate_per_minute == 3.0
    # Flow rate per hour: 90 / (1800 / 3600) = 90 / 0.5 = 180.0 veh/hr
    assert summary.flow_rate_per_hour == 180.0
    assert summary.is_extrapolated is True  # 1800s < 3600s
    assert summary.session_count == 2
    assert summary.source_count == 2  # 2 sources (s1 is camera_real, s2 is video_real)
    assert summary.provenance.camera_source_count == 1
    assert summary.anomaly_count == 1
    assert summary.provenance.provenance_label == "REAL DATA"


def test_empty_database_honest_insufficient_data(db_session: Session):
    """Verify clean empty/insufficient response without fake data when DB has no records."""
    now = utcnow()
    params = HistoricalFilterParams(time_preset="24h")
    summary = HistoricalAnalyticsService.get_summary(db_session, params)

    assert summary.total_observed_volume == 0
    assert summary.observation_duration_seconds == 0.0
    assert summary.flow_rate_per_minute == 0.0
    assert summary.flow_rate_per_hour == 0.0
    assert summary.session_count == 0
    assert summary.data_status == "insufficient"
    assert summary.provenance.provenance_label == "UNAVAILABLE"


# =============================================================================
# 3. Time-Series Bucketing Tests
# =============================================================================

def test_timeseries_hourly_bucketing(db_session: Session):
    """Verify non-interpolated time-series bucketing across hours."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    params = HistoricalFilterParams(
        time_preset="custom",
        start_time=now - timedelta(hours=3),
        end_time=now,
        bucket_interval="hourly",
        include_synthetic=False,
    )
    ts = HistoricalAnalyticsService.get_timeseries(db_session, params)

    assert ts.bucket_interval == "hourly"
    assert ts.bucket_interval_seconds == 3600
    assert len(ts.buckets) == 3

    # Total observed volume across all buckets must equal 90
    total_bucketed_volume = sum(b.observed_volume for b in ts.buckets)
    assert total_bucketed_volume == 90

    for b in ts.buckets:
        assert b.start_time < b.end_time
        assert isinstance(b.vehicle_composition, dict)


# =============================================================================
# 4. Vehicle Composition & Supported Classes Tests
# =============================================================================

def test_vehicle_composition_strict_supported_classes(db_session: Session):
    """Verify that only genuine supported vehicle classes are present and counts are exact."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    params = HistoricalFilterParams(
        time_preset="custom",
        start_time=now - timedelta(hours=3),
        end_time=now,
        include_synthetic=False,
    )
    vc = HistoricalAnalyticsService.get_vehicle_composition(db_session, params)

    assert vc.total_vehicles == 90
    returned_classes = {c.class_name.lower() for c in vc.classes}
    assert returned_classes == set(SUPPORTED_VEHICLE_CLASSES)

    class_dict = {c.class_name.lower(): c.count for c in vc.classes}
    # s1: 20 car, 6 truck, 4 bus; s2: 45 car, 10 motorcycle, 5 bicycle
    assert class_dict["car"] == 65
    assert class_dict["truck"] == 6
    assert class_dict["bus"] == 4
    assert class_dict["motorcycle"] == 10
    assert class_dict["bicycle"] == 5


# =============================================================================
# 5. Directional Flow & Ratio Tests
# =============================================================================

def test_directional_flow_trends(db_session: Session):
    """Verify inbound vs outbound counts and directional ratio."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    params = HistoricalFilterParams(
        time_preset="custom",
        start_time=now - timedelta(hours=3),
        end_time=now,
        include_synthetic=False,
    )
    df = HistoricalAnalyticsService.get_directions(db_session, params)

    # s1: 18 in, 12 out; s2: 30 in, 30 out -> total 48 inbound, 42 outbound
    assert df.inbound_count == 48
    assert df.outbound_count == 42
    assert df.total_vehicles == 90
    assert df.directional_ratio == pytest.approx(1.14, abs=0.02)


# =============================================================================
# 6. Lane Intelligence & Uncalibrated Density Tests
# =============================================================================

def test_lane_intelligence_and_calibration_warning(db_session: Session):
    """Verify lane metrics aggregation and explicit preservation of calibration warning."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    params = HistoricalFilterParams(
        time_preset="custom",
        start_time=now - timedelta(hours=3),
        end_time=now,
        include_synthetic=False,
    )
    lanes_resp = HistoricalAnalyticsService.get_lanes(db_session, params)

    assert lanes_resp.total_lanes == 2
    l1 = next(l for l in lanes_resp.lanes if l.lane_id == "lane_1")
    assert l1.total_volume == 18
    assert l1.peak_occupancy == 5
    assert l1.density_unit == "vehicles/px²"
    assert "Uncalibrated" in l1.density_calibration_warning


# =============================================================================
# 7. Deterministic Peak Analysis & Tie-Breaking Tests
# =============================================================================

def test_peak_analysis_and_tie_breaking(db_session: Session):
    """Verify deterministic peak calculation and tie-breaking rule documentation."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    params = HistoricalFilterParams(
        time_preset="custom",
        start_time=now - timedelta(hours=3),
        end_time=now,
        include_synthetic=False,
    )
    peaks = HistoricalAnalyticsService.get_peaks(db_session, params)

    assert peaks.peak_flow.value == 180.0
    assert peaks.peak_volume.value == 60.0
    assert peaks.peak_density.lane_name == "Northbound Left"
    assert peaks.tie_breaking_rule == TIE_BREAKING_RULE_DESC


# =============================================================================
# 8. Strict Provenance & Mixed Dataset Detection Tests
# =============================================================================

def test_provenance_isolation_and_mixed_detection(db_session: Session):
    """Verify strict real vs synthetic isolation and explicit MIXED badge when requested."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    # Case A: Real data only (default)
    p_real = HistoricalFilterParams(
        time_preset="custom",
        start_time=now - timedelta(hours=3),
        end_time=now,
        include_synthetic=False,
    )
    sum_real = HistoricalAnalyticsService.get_summary(db_session, p_real)
    assert sum_real.provenance.provenance_label == "REAL DATA"
    assert sum_real.provenance.is_mixed is False

    # Case B: Include synthetic -> dataset contains real + test fixture -> MIXED
    p_mixed = HistoricalFilterParams(
        time_preset="custom",
        start_time=now - timedelta(hours=3),
        end_time=now,
        include_synthetic=True,
    )
    sum_mixed = HistoricalAnalyticsService.get_summary(db_session, p_mixed)
    assert sum_mixed.provenance.provenance_label == "MIXED"
    assert sum_mixed.provenance.is_mixed is True
    assert sum_mixed.provenance.mix_warning is not None
    assert sum_mixed.total_observed_volume == 95  # 90 real + 5 fixture


# =============================================================================
# 9. REST API Integration Tests via FastAPI TestClient
# =============================================================================

def test_api_historical_summary(client: TestClient, db_session: Session):
    """Verify GET /api/v1/historical-analytics/summary."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    resp = client.get("/api/v1/historical-analytics/summary?time_preset=7d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_observed_volume"] == 90
    assert data["flow_rate_per_hour"] == 180.0
    assert data["provenance"]["provenance_label"] == "REAL DATA"


def test_api_historical_timeseries(client: TestClient, db_session: Session):
    """Verify GET /api/v1/historical-analytics/timeseries."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    resp = client.get("/api/v1/historical-analytics/timeseries?time_preset=24h&bucket_interval=hourly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["bucket_interval"] == "hourly"
    assert len(data["buckets"]) > 0


def test_api_historical_endpoints_roundtrip(client: TestClient, db_session: Session):
    """Verify all remaining analytical endpoints return 200 OK and valid schemas."""
    now = utcnow()
    create_mock_historical_data(db_session, now)

    endpoints = [
        "/api/v1/historical-analytics/vehicle-composition",
        "/api/v1/historical-analytics/directions",
        "/api/v1/historical-analytics/lanes",
        "/api/v1/historical-analytics/peaks",
        "/api/v1/historical-analytics/anomalies",
        "/api/v1/historical-analytics/sources",
        "/api/v1/historical-analytics/compare",
    ]
    for ep in endpoints:
        r = client.get(f"{ep}?time_preset=7d")
        assert r.status_code == 200, f"Endpoint {ep} failed with {r.status_code}: {r.text}"
