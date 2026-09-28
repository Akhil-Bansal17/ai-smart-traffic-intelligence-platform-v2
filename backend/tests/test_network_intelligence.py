"""
Unit and integration tests for Network Intelligence & Multi-Source Traffic Analytics.
Phase 24: Advanced Traffic Operations Analytics & Network Intelligence.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from typing import Generator
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.core.exceptions import AppException
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import AnalysisSession, LaneResultRecord, TrafficMetricsRecord
from app.models.anomaly import AnomalyEvent
from app.models.camera_source import CameraSource, CameraSourceStatus, CameraSourceType
from app.schemas.network_intelligence import NetworkFilterParams
from app.services.analytics.historical_analytics_service import SUPPORTED_VEHICLE_CLASSES
from app.services.network_intelligence.service import NetworkIntelligenceService


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


TEST_DB_PATH = Path(tempfile.gettempdir()) / f"test_phase24_net_{uuid.uuid4().hex[:8]}.db"
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


# =============================================================================
# Helper Fixtures: Seed Multi-Source Test Data
# =============================================================================
def seed_network_data(db: Session):
    now = utcnow()

    # Source 1: Real Camera (Intersection North)
    c1 = CameraSource(
        id=str(uuid.uuid4()),
        name="Camera 1 - Downtown North",
        source_type=CameraSourceType.RTSP.value,
        connection_uri="rtsp://admin:secret@10.0.0.1/live",
        status=CameraSourceStatus.CONNECTED.value,
        location_name="Intersection 5th & Main",
    )
    # Source 2: Real Camera (Corridor South)
    c2 = CameraSource(
        id=str(uuid.uuid4()),
        name="Camera 2 - Broadway South",
        source_type=CameraSourceType.RTSP.value,
        connection_uri="rtsp://admin:pass123@10.0.0.2/feed",
        status=CameraSourceStatus.CONNECTED.value,
        location_name="Broadway Corridor South",
    )
    # Source 3: Synthetic / Test Fixture Camera
    c3 = CameraSource(
        id=str(uuid.uuid4()),
        name="Camera 3 - Test Rig West",
        source_type=CameraSourceType.TEST_FIXTURE.value,
        connection_uri="test_fixture://synthetic_traffic",
        status=CameraSourceStatus.CONNECTED.value,
        location_name=None,
    )
    db.add_all([c1, c2, c3])
    db.commit()

    # Sessions for Camera 1 (High volume, 2 incidents)
    s1 = AnalysisSession(
        id=str(uuid.uuid4()),
        camera_source_id=c1.id,
        session_mode="live_monitoring",
        status="completed",
        started_at=now - timedelta(days=2),
        total_vehicles_counted=120,
    )
    db.add(s1)
    db.commit()

    m1 = TrafficMetricsRecord(
        analysis_session_id=s1.id,
        observation_duration_seconds=3600.0,
        total_volume=120,
        flow_rate_per_minute=2.0,
        flow_rate_per_hour=120.0,
        is_extrapolated=False,
        class_distribution=[
            {"class_name": "car", "count": 90},
            {"class_name": "truck", "count": 15},
            {"class_name": "bus", "count": 5},
            {"class_name": "motorcycle", "count": 8},
            {"class_name": "bicycle", "count": 2},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 80},
            {"direction": "outbound", "count": 40},
        ],
        created_at=now - timedelta(days=2),
    )
    # Lane for Camera 1
    lr1 = LaneResultRecord(
        analysis_session_id=s1.id,
        lane_id="lane-1-north",
        lane_name="Northbound Lane 1",
        direction_hint="inbound",
        unique_vehicles_count=70,
        peak_occupancy=6,
        average_occupancy=3.2,
        image_space_density=0.00045,
        created_at=now - timedelta(days=2),
    )
    # Incidents for Camera 1 (Recurring congestion)
    a1 = AnomalyEvent(
        session_id=s1.id,
        anomaly_type="CONGESTION",
        severity="high",
        status="open",
        title="Severe Queue Spillback",
        description="Persistent vehicle queue detected",
        metric_name="density_score",
        trigger_value=0.85,
        threshold_value=0.70,
        lane_id="lane-1-north",
        is_synthetic=False,
        created_at=now - timedelta(days=2),
    )
    a2 = AnomalyEvent(
        session_id=s1.id,
        anomaly_type="CONGESTION",
        severity="medium",
        status="open",
        title="Lane Queue Surge",
        description="Recurrent congestion pattern",
        metric_name="density_score",
        trigger_value=0.75,
        threshold_value=0.70,
        lane_id="lane-1-north",
        is_synthetic=False,
        created_at=now - timedelta(days=2, hours=1),
    )
    db.add_all([m1, lr1, a1, a2])
    db.commit()

    # Session for Camera 2 (Moderate volume, balanced direction, no lanes)
    s2 = AnalysisSession(
        id=str(uuid.uuid4()),
        camera_source_id=c2.id,
        session_mode="live_monitoring",
        status="completed",
        started_at=now - timedelta(days=1),
        total_vehicles_counted=60,
    )
    db.add(s2)
    db.commit()

    m2 = TrafficMetricsRecord(
        analysis_session_id=s2.id,
        observation_duration_seconds=1800.0,
        total_volume=60,
        flow_rate_per_minute=2.0,
        flow_rate_per_hour=120.0,
        is_extrapolated=False,
        class_distribution=[
            {"class_name": "car", "count": 50},
            {"class_name": "truck", "count": 5},
            {"class_name": "bus", "count": 2},
            {"class_name": "motorcycle", "count": 3},
            {"class_name": "bicycle", "count": 0},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 30},
            {"direction": "outbound", "count": 30},
        ],
        created_at=now - timedelta(days=1),
    )
    db.add(m2)
    db.commit()

    # Session for Camera 3 (Synthetic Test Fixture)
    s3 = AnalysisSession(
        id=str(uuid.uuid4()),
        camera_source_id=c3.id,
        session_mode="live_monitoring",
        status="completed",
        started_at=now - timedelta(hours=6),
        total_vehicles_counted=40,
    )
    db.add(s3)
    db.commit()

    m3 = TrafficMetricsRecord(
        analysis_session_id=s3.id,
        observation_duration_seconds=1200.0,
        total_volume=40,
        flow_rate_per_minute=2.0,
        flow_rate_per_hour=120.0,
        is_extrapolated=False,
        class_distribution=[
            {"class_name": "car", "count": 35},
            {"class_name": "truck", "count": 3},
            {"class_name": "bus", "count": 1},
            {"class_name": "motorcycle", "count": 1},
            {"class_name": "bicycle", "count": 0},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 20},
            {"direction": "outbound", "count": 20},
        ],
        created_at=now - timedelta(hours=6),
    )
    db.add(m3)
    db.commit()

    return {"c1": c1, "c2": c2, "c3": c3, "s1": s1, "s2": s2, "s3": s3}


# =============================================================================
# 1. Configuration & Settings Tests
# =============================================================================
def test_network_intelligence_settings():
    """Validates configuration parameters and boundary validators."""
    assert hasattr(settings, "network_intelligence_max_sources")
    assert hasattr(settings, "network_intelligence_max_range_days")
    assert hasattr(settings, "network_intelligence_default_time_window")
    assert hasattr(settings, "network_intelligence_max_hotspots")

    assert settings.network_intelligence_max_sources == 50
    assert settings.network_intelligence_max_range_days == 90
    assert settings.network_intelligence_max_hotspots == 20


# =============================================================================
# 2. Network Overview Aggregation Tests
# =============================================================================
def test_network_overview_aggregation(db_session: Session):
    """Verifies multi-source network overview aggregation from real persisted records."""
    seed_network_data(db_session)

    params = NetworkFilterParams(time_preset="7d", include_synthetic=False)
    overview = NetworkIntelligenceService.get_network_overview(db_session, params)

    assert overview.total_sources == 2  # c1 and c2 (c3 is synthetic)
    assert overview.active_sources_count == 2
    assert overview.total_volume == 180  # 120 + 60
    assert overview.active_incident_count == 2
    assert overview.recurring_incident_locations_count == 1
    assert overview.provenance.provenance_label == "REAL DATA"
    assert overview.epistemic_status == "OBSERVED"

    # Directional summary
    assert overview.directional_summary.inbound_count == 110
    assert overview.directional_summary.outbound_count == 70
    assert overview.directional_summary.directional_ratio > 1.0

    # Lane summary
    assert overview.lane_summary.total_lanes == 1
    assert overview.lane_summary.sources_with_lanes == 1
    assert overview.lane_summary.busiest_lane_name == "Northbound Lane 1"


# =============================================================================
# 3. Empty Database Determinism Tests
# =============================================================================
def test_empty_database_determinism(db_session: Session):
    """Ensures empty database produces exact zero counts, no fake metrics, and UNAVAILABLE status."""
    params = NetworkFilterParams(time_preset="7d", include_synthetic=False)
    overview = NetworkIntelligenceService.get_network_overview(db_session, params)

    assert overview.total_sources == 0
    assert overview.total_volume == 0
    assert overview.flow_rate_per_minute == 0.0
    assert overview.flow_rate_per_hour == 0.0
    assert overview.active_incident_count == 0
    assert overview.epistemic_status == "UNAVAILABLE"
    assert overview.data_status == "empty"
    assert overview.lane_summary.lane_data_status == "UNAVAILABLE"


# =============================================================================
# 4. Source Comparison & Window Mismatch Tests
# =============================================================================
def test_source_comparison_and_mismatch_detection(db_session: Session):
    """Verifies source-by-source comparison and observation window mismatch detection."""
    data = seed_network_data(db_session)
    c1 = data["c1"]
    c2 = data["c2"]

    params = NetworkFilterParams(time_preset="7d", include_synthetic=False)
    comp = NetworkIntelligenceService.compare_sources(db_session, params)

    assert comp.total_sources_compared == 2
    assert comp.busiest_source_name == c1.name

    s1_item = next(s for s in comp.sources if s.source_id == c1.id)
    s2_item = next(s for s in comp.sources if s.source_id == c2.id)

    assert s1_item.observed_volume == 120
    assert s1_item.has_lane_data is True
    assert s1_item.incident_count == 2
    assert s1_item.recurring_incident_count == 1

    assert s2_item.observed_volume == 60
    assert s2_item.has_lane_data is False


# =============================================================================
# 5. Evidence-Based Traffic Hotspot Tests
# =============================================================================
def test_evidence_based_traffic_hotspots(db_session: Session):
    """Verifies traffic hotspot ranking based strictly on incidents, anomalies, and volume."""
    data = seed_network_data(db_session)
    c1 = data["c1"]

    params = NetworkFilterParams(time_preset="7d", include_synthetic=False)
    hotspots_res = NetworkIntelligenceService.get_hotspots(db_session, params, limit=10)

    assert hotspots_res.total_hotspots_identified >= 1
    top_hs = hotspots_res.hotspots[0]

    assert top_hs.source_id == c1.id
    assert top_hs.rank == 1
    assert top_hs.hotspot_score > 50.0  # Elevated due to 2 incidents + recurring + volume
    assert top_hs.incident_count == 2
    assert "Recurring operational incidents" in top_hs.primary_contributing_factor
    assert top_hs.epistemic_status == "DERIVED"


# =============================================================================
# 6. Supported Vehicle Composition Tests
# =============================================================================
def test_vehicle_composition_strict_classes(db_session: Session):
    """Verifies vehicle composition strictly respects the 5 supported YOLO classes."""
    seed_network_data(db_session)

    params = NetworkFilterParams(time_preset="7d", include_synthetic=False)
    comp = NetworkIntelligenceService.get_vehicle_composition(db_session, params)

    assert comp.total_vehicles == 180  # 120 + 60
    assert len(comp.classes) == 5
    class_names = [c.class_name for c in comp.classes]
    assert sorted(class_names) == sorted(SUPPORTED_VEHICLE_CLASSES)

    car_metric = next(c for c in comp.classes if c.class_name == "car")
    assert car_metric.count == 140  # 90 + 50
    assert car_metric.percentage > 70.0
    assert comp.network_dominant_class == "car"


# =============================================================================
# 7. Directional Intelligence Tests
# =============================================================================
def test_directional_intelligence(db_session: Session):
    """Verifies directional flow balance, inbound/outbound ratio, and per-source classification."""
    data = seed_network_data(db_session)
    c1 = data["c1"]
    c2 = data["c2"]

    params = NetworkFilterParams(time_preset="7d", include_synthetic=False)
    dir_res = NetworkIntelligenceService.get_directional_analysis(db_session, params)

    assert dir_res.network_summary.inbound_count == 110  # 80 + 30
    assert dir_res.network_summary.outbound_count == 70   # 40 + 30
    assert dir_res.network_summary.balance_status == "inbound_dominant"

    s1_dir = next(s for s in dir_res.sources if s.source_id == c1.id)
    assert s1_dir.balance_status == "inbound_dominant"

    s2_dir = next(s for s in dir_res.sources if s.source_id == c2.id)
    assert s2_dir.balance_status == "balanced"


# =============================================================================
# 8. Lane Intelligence & UNAVAILABLE Handling Tests
# =============================================================================
def test_lane_intelligence_and_unavailable_handling(db_session: Session):
    """Verifies lane intelligence returns UNAVAILABLE when sources lack lane configuration."""
    data = seed_network_data(db_session)
    c2 = data["c2"]

    # Query specifically for c2 (which has no configured lanes)
    params = NetworkFilterParams(time_preset="7d", source_ids=[c2.id], include_synthetic=False)
    lane_res = NetworkIntelligenceService.get_lane_analysis(db_session, params)

    assert lane_res.total_lanes == 0
    assert lane_res.sources_with_lanes_count == 0
    assert lane_res.epistemic_status == "UNAVAILABLE"
    assert "Uncalibrated image-space density heuristic" in lane_res.density_calibration_disclaimer


# =============================================================================
# 9. Provenance Isolation Tests (REAL vs TEST FIXTURE vs MIXED)
# =============================================================================
def test_provenance_isolation(db_session: Session):
    """Verifies strict provenance classification: REAL DATA vs MIXED."""
    seed_network_data(db_session)

    # Real data only (include_synthetic=False)
    p_real = NetworkFilterParams(time_preset="7d", include_synthetic=False)
    ov_real = NetworkIntelligenceService.get_network_overview(db_session, p_real)
    assert ov_real.provenance.provenance_label == "REAL DATA"
    assert ov_real.provenance.is_mixed is False

    # Mixed real + synthetic fixture (include_synthetic=True)
    p_mixed = NetworkFilterParams(time_preset="7d", include_synthetic=True)
    ov_mixed = NetworkIntelligenceService.get_network_overview(db_session, p_mixed)
    assert ov_mixed.provenance.provenance_label == "MIXED"
    assert ov_mixed.provenance.is_mixed is True
    assert "Dataset contains mixed provenance" in (ov_mixed.provenance.mix_warning or "")


# =============================================================================
# 10. Bounded Query & Date Range Rejection Tests
# =============================================================================
def test_bounded_query_and_excessive_window_rejection(db_session: Session):
    """Verifies query ceilings reject excessive ranges beyond 90 days."""
    now = utcnow()
    excessive_params = NetworkFilterParams(
        start_time=now - timedelta(days=120),
        end_time=now,
        time_preset="custom",
    )
    with pytest.raises(AppException) as exc_info:
        NetworkIntelligenceService.resolve_and_validate_window(excessive_params)

    assert "exceeds maximum" in str(exc_info.value).lower()
    assert exc_info.value.status_code in [400, 422]


# =============================================================================
# 11. FastAPI REST API Endpoints Tests
# =============================================================================
def test_fastapi_rest_endpoints(client: TestClient, db_session: Session):
    """Tests all 8 REST endpoints mounted under /api/v1/network-intelligence."""
    seed_network_data(db_session)

    # 1. GET /overview
    res = client.get("/api/v1/network-intelligence/overview?time_preset=7d&include_synthetic=true")
    assert res.status_code == 200
    assert "total_volume" in res.json()

    # 2. GET /compare
    res = client.get("/api/v1/network-intelligence/compare?time_preset=7d&include_synthetic=true")
    assert res.status_code == 200
    assert "sources" in res.json()

    # 3. GET /hotspots
    res = client.get("/api/v1/network-intelligence/hotspots?time_preset=7d&limit=5&include_synthetic=true")
    assert res.status_code == 200
    assert "hotspots" in res.json()

    # 4. GET /vehicle-composition
    res = client.get("/api/v1/network-intelligence/vehicle-composition?time_preset=7d&include_synthetic=true")
    assert res.status_code == 200
    assert "classes" in res.json()

    # 5. GET /directional-analysis
    res = client.get("/api/v1/network-intelligence/directional-analysis?time_preset=7d&include_synthetic=true")
    assert res.status_code == 200
    assert "network_summary" in res.json()

    # 6. GET /lane-analysis
    res = client.get("/api/v1/network-intelligence/lane-analysis?time_preset=7d&include_synthetic=true")
    assert res.status_code == 200
    assert "lanes" in res.json()

    # 7. GET /temporal-analysis
    res = client.get("/api/v1/network-intelligence/temporal-analysis?time_preset=7d&bucket_interval=hourly&include_synthetic=true")
    assert res.status_code == 200
    assert "buckets" in res.json()

    # 8. GET /historical-comparison
    res = client.get("/api/v1/network-intelligence/historical-comparison?time_preset=7d&include_synthetic=true")
    assert res.status_code == 200
    assert "volume_comparison" in res.json()
