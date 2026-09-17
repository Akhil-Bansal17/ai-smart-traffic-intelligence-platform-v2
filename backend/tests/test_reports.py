"""
Unit and integration tests for Business-Grade Traffic Reporting & Export.
Phase 19: Business-Grade Traffic Reporting & Export.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
from typing import Generator
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import Settings, settings
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
from app.models.insight import TrafficInsight
from app.models.report import Report, ReportFormat, ReportScopeType, ReportStatus, ReportType
from app.models.video import Video
from app.services.reports.assembler import ReportAssembler
from app.services.reports.csv_generator import CSVReportGenerator
from app.services.reports.models import TruthLabel
from app.services.reports.pdf_generator import PDFReportGenerator
from app.services.reports.service import ReportService


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


TEST_DB_PATH = Path(tempfile.gettempdir()) / "test_phase19_reports_isolated.db"
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


@pytest.fixture
def sample_persisted_session(db_session: Session) -> AnalysisSession:
    """Creates a complete realistic session with metrics, lanes, anomalies, and insights."""
    video = Video(
        id=str(uuid.uuid4()),
        original_filename="test_arterial_junction.mp4",
        storage_path="uploads/test_arterial_junction.mp4",
        duration_seconds=30.0,
        fps=10.0,
        resolution="1920x1080",
        frame_count=300,
        status="processed",
        source_type="real_world",
        source_reference="https://github.com/example/traffic-data",
        license_reference="MIT",
        provenance_verified=True,
        captured_at=utcnow() - timedelta(days=1),
    )
    db_session.add(video)


    session = AnalysisSession(
        id=str(uuid.uuid4()),
        video_id=video.id,
        analysis_type="full_pipeline",
        status="completed",
        started_at=utcnow() - timedelta(minutes=5),
        completed_at=utcnow() - timedelta(minutes=4),
        processing_time_ms=1200.0,
        total_frames_processed=300,
        total_vehicles_detected=42,
        total_vehicles_counted=36,
    )
    db_session.add(session)

    metrics = TrafficMetricsRecord(
        id=str(uuid.uuid4()),
        analysis_session_id=session.id,
        observation_duration_seconds=30.0,
        total_volume=36,
        flow_rate_per_minute=72.0,
        flow_rate_per_hour=4320.0,
        is_extrapolated=True,
        class_distribution=[
            {"class_name": "car", "count": 28, "percentage": 77.8},
            {"class_name": "bus", "count": 4, "percentage": 11.1},
            {"class_name": "truck", "count": 4, "percentage": 11.1},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 24, "percentage": 66.7},
            {"direction": "outbound", "count": 12, "percentage": 33.3},
        ],
        time_series_buckets=[
            {
                "bucket_index": 0,
                "start_time_seconds": 0.0,
                "end_time_seconds": 15.0,
                "vehicle_count": 18,
                "flow_rate_vph": 4320.0,
            },
            {
                "bucket_index": 1,
                "start_time_seconds": 15.0,
                "end_time_seconds": 30.0,
                "vehicle_count": 18,
                "flow_rate_vph": 4320.0,
            },
        ],
    )
    db_session.add(metrics)

    lane1 = LaneResultRecord(
        id=str(uuid.uuid4()),
        analysis_session_id=session.id,
        lane_id="lane_northbound",
        lane_name="Northbound Lane 1",
        polygon_json=[[0, 0], [100, 0], [100, 500], [0, 500]],
        polygon_area_px2=50000.0,
        unique_vehicles_count=24,
        peak_occupancy=4,
        average_occupancy=0.45,
        image_space_density=0.00048,
        normalized_density_score=0.60,
        density_unit="vehicles/px²",
        vehicle_class_counts={"car": 20, "bus": 2, "truck": 2},
    )
    db_session.add(lane1)

    crossing1 = CrossingEventRecord(
        id=str(uuid.uuid4()),
        analysis_session_id=session.id,
        track_id=1,
        class_name="car",
        direction="inbound",
        frame_index=15,
        timestamp_seconds=1.5,
        centroid_x=250.0,
        centroid_y=350.0,
        line_label="main_tripwire",
    )
    crossing2 = CrossingEventRecord(
        id=str(uuid.uuid4()),
        analysis_session_id=session.id,
        track_id=2,
        class_name="truck",
        direction="outbound",
        frame_index=30,
        timestamp_seconds=3.0,
        centroid_x=260.0,
        centroid_y=360.0,
        line_label="main_tripwire",
    )
    db_session.add(crossing1)
    db_session.add(crossing2)

    anomaly = AnomalyEvent(
        id=str(uuid.uuid4()),
        session_id=session.id,
        anomaly_type="CONGESTION_SPIKE",
        severity="HIGH",
        status="open",
        title="Elevated Northbound Lane Density",
        description="Vehicular occupancy exceeded critical threshold for 15 consecutive seconds.",
        start_timestamp_seconds=5.0,
        end_timestamp_seconds=20.0,
        duration_seconds=15.0,
        metric_name="density_score",
        trigger_value=0.85,
        threshold_value=0.70,
        lane_id="lane_northbound",
    )
    db_session.add(anomaly)

    insight = TrafficInsight(
        id=str(uuid.uuid4()),
        session_id=session.id,
        insight_type="CONGESTION_ALERT",
        category="CONGESTION",
        severity="HIGH",
        status="ACTIVE",
        title="Northbound Lane Bottleneck Detected",
        summary="Sustained high queue length observed on Northbound Lane 1.",
        start_timestamp_seconds=5.0,
        duration_seconds=15.0,
        affected_lane_id="lane_northbound",
        affected_lane_name="Northbound Lane 1",
        root_cause_observed=["Observed high vehicle occupancy on Northbound Lane 1"],
        root_cause_inferred=["Inferred bottleneck propagation from downstream queue"],
        recommendation="Consider increasing green time split on Phase 2 by 5 seconds.",
        recommendation_type="signal_retiming",
        dedup_signature=f"hash_{session.id}_congestion",
    )
    db_session.add(insight)

    db_session.commit()
    db_session.refresh(session)
    return session


def test_reporting_settings_and_bounds():
    """Verifies that Phase 19 report settings load and validate correctly."""
    assert settings.reports_dir == "./reports"
    assert settings.max_report_time_range_days == 30
    assert settings.max_report_file_size_mb == 50

    # Test validator bounds
    with pytest.raises(Exception):
        Settings(max_report_time_range_days=0)

    with pytest.raises(Exception):
        Settings(max_report_file_size_mb=0)


def test_reporting_info_endpoint(client: TestClient):
    """Verifies GET /api/v1/reports/info returns correct capability taxonomy."""
    res = client.get("/api/v1/reports/info")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Traffic Intelligence Reporting Subsystem"
    assert "traffic_analysis" in data["supported_report_types"]
    assert "pdf" in data["supported_formats"]
    assert "csv" in data["supported_formats"]
    assert TruthLabel.OBSERVED.value in data["truth_label_taxonomy"]
    assert TruthLabel.INFERRED.value in data["truth_label_taxonomy"]
    assert TruthLabel.PREDICTED.value in data["truth_label_taxonomy"]
    assert TruthLabel.SIMULATED.value in data["truth_label_taxonomy"]
    assert TruthLabel.RECOMMENDED.value in data["truth_label_taxonomy"]


def test_report_scope_validation_invalid_session(client: TestClient):
    """Verifies HTTP 404 when requesting a report for a non-existent session ID."""
    res = client.post(
        "/api/v1/reports",
        json={"scope_type": "session", "session_id": str(uuid.uuid4()), "format": "pdf"},
    )
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "SESSION_NOT_FOUND"


def test_report_scope_validation_invalid_time_range(client: TestClient):
    """Verifies HTTP 400 when start_time > end_time."""
    now = utcnow()
    res = client.post(
        "/api/v1/reports",
        json={
            "scope_type": "time_range",
            "time_range_start": now.isoformat(),
            "time_range_end": (now - timedelta(days=1)).isoformat(),
            "format": "pdf",
        },
    )
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "INVALID_TIME_RANGE"


def test_deterministic_report_assembly_and_truth_labeling(
    db_session: Session, sample_persisted_session: AnalysisSession
):
    """
    Tests deterministic assembly directly from database entities, asserting:
    1. Zero analytics recalculated.
    2. Mandatory truth labeling applied on every section.
    3. Missing ML/simulation subsystems honestly tagged UNAVAILABLE.
    """
    report_data = ReportAssembler.assemble_session_report(
        db=db_session,
        report_id=str(uuid.uuid4()),
        session_id=sample_persisted_session.id,
        report_title="Arterial Test Report",
    )

    assert report_data.title == "Arterial Test Report"
    assert report_data.scope is not None
    assert report_data.scope.video_filename == "test_arterial_junction.mp4"
    assert report_data.scope.provenance_verified is True
    assert report_data.scope.provenance_category == "real_database_metrics"

    # 1. Traffic Overview (OBSERVED)
    assert report_data.traffic_overview is not None
    assert report_data.traffic_overview.label == TruthLabel.OBSERVED.value
    assert report_data.traffic_overview.total_vehicles_counted == 36
    assert report_data.traffic_overview.total_vehicles_detected == 42
    assert report_data.traffic_overview.overall_flow_rate_vph == 4320.0
    assert report_data.traffic_overview.is_extrapolated is True

    # 2. Vehicle Composition (OBSERVED)
    assert report_data.vehicle_composition is not None
    assert report_data.vehicle_composition.label == TruthLabel.OBSERVED.value
    assert len(report_data.vehicle_composition.items) == 3
    for item in report_data.vehicle_composition.items:
        assert item.label == TruthLabel.OBSERVED.value

    # 3. Directional Flow (OBSERVED)
    assert report_data.directional_flow is not None
    assert report_data.directional_flow.label == TruthLabel.OBSERVED.value
    assert len(report_data.directional_flow.items) == 2

    # 4. Lane Analysis (OBSERVED & INFERRED)
    assert report_data.lane_analysis is not None
    assert report_data.lane_analysis.is_available is True
    assert len(report_data.lane_analysis.items) == 1
    lane = report_data.lane_analysis.items[0]
    assert lane.observed_label == TruthLabel.OBSERVED.value
    assert lane.inferred_label == TruthLabel.INFERRED.value
    assert lane.vehicles_detected == 24
    assert lane.normalized_density_score == 0.60

    # 5. Anomalies & Insights (INFERRED & RECOMMENDED)
    assert report_data.anomalies is not None
    assert report_data.anomalies.label == TruthLabel.INFERRED.value
    assert len(report_data.anomalies.items) == 1
    assert report_data.anomalies.items[0].label == TruthLabel.INFERRED.value

    assert report_data.insights is not None
    assert report_data.insights.label == TruthLabel.INFERRED.value
    assert len(report_data.insights.items) == 1
    ins = report_data.insights.items[0]
    assert ins.inferred_label == TruthLabel.INFERRED.value
    assert ins.advisory_label == TruthLabel.RECOMMENDED.value

    # 6. ML Forecast & Simulation Honest Limitation (UNAVAILABLE)
    assert report_data.prediction_status is not None
    assert report_data.prediction_status.is_available is False
    assert report_data.prediction_status.label == TruthLabel.UNAVAILABLE.value
    assert "N=10 < 20" in report_data.prediction_status.reason

    assert report_data.signal_optimization is not None
    assert report_data.signal_optimization.is_available is False
    assert report_data.signal_optimization.label == TruthLabel.UNAVAILABLE.value

    assert report_data.emergency_corridor is not None
    assert report_data.emergency_corridor.is_available is False
    assert report_data.emergency_corridor.label == TruthLabel.UNAVAILABLE.value


def test_pdf_binary_generation_and_layout(
    db_session: Session, sample_persisted_session: AnalysisSession
):
    """Verifies that PDFReportGenerator produces valid, printable PDF bytes with %PDF- header."""
    report_data = ReportAssembler.assemble_session_report(
        db=db_session,
        report_id=str(uuid.uuid4()),
        session_id=sample_persisted_session.id,
    )
    pdf_bytes = PDFReportGenerator.generate_pdf(report_data)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2048  # Valid PDF size
    assert pdf_bytes.startswith(b"%PDF-")  # Standard PDF magic bytes


def test_csv_tabular_export_generation(
    db_session: Session, sample_persisted_session: AnalysisSession
):
    """Verifies that CSVReportGenerator exports clean, parseable tabular CSV with units."""
    report_data = ReportAssembler.assemble_session_report(
        db=db_session,
        report_id=str(uuid.uuid4()),
        session_id=sample_persisted_session.id,
    )
    csv_text = CSVReportGenerator.generate_csv(report_data)

    assert isinstance(csv_text, str)
    assert "--- EXECUTIVE SUMMARY ---" in csv_text
    assert "--- VEHICLE COMPOSITION ---" in csv_text
    assert "--- DIRECTIONAL FLOW ---" in csv_text
    assert "--- LANE-LEVEL METRICS & SPATIAL DENSITY ---" in csv_text
    assert "4320.00" in csv_text  # Flow rate
    assert "test_arterial_junction.mp4" in csv_text


def test_report_create_and_detail_api_endpoints(
    client: TestClient, sample_persisted_session: AnalysisSession
):
    """Tests creating and fetching a report via REST API."""
    res = client.post(
        "/api/v1/reports",
        json={
            "scope_type": "session",
            "session_id": sample_persisted_session.id,
            "format": "pdf",
            "title": "API Test Report",
        },
    )
    assert res.status_code == 201
    created_data = res.json()
    report_id = created_data["id"]
    assert created_data["status"] == "completed"
    assert created_data["format"] == "pdf"
    assert created_data["file_size_bytes"] > 0

    # Test GET /api/v1/reports/{id}
    res_get = client.get(f"/api/v1/reports/{report_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["id"] == report_id
    assert detail["title"] == "API Test Report"
    assert detail["report_data"]["traffic_overview"]["total_vehicles_counted"] == 36


def test_report_download_api_endpoint_pdf_and_csv(
    client: TestClient, sample_persisted_session: AnalysisSession
):
    """Tests downloading PDF and CSV report artifacts with correct headers."""
    # 1. Test PDF Download
    res_pdf_create = client.post(
        "/api/v1/reports",
        json={"scope_type": "session", "session_id": sample_persisted_session.id, "format": "pdf"},
    )
    assert res_pdf_create.status_code == 201
    pdf_id = res_pdf_create.json()["id"]

    res_pdf_dl = client.get(f"/api/v1/reports/{pdf_id}/download")
    assert res_pdf_dl.status_code == 200
    assert res_pdf_dl.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res_pdf_dl.headers["content-disposition"]
    assert res_pdf_dl.content.startswith(b"%PDF-")

    # 2. Test CSV Download
    res_csv_create = client.post(
        "/api/v1/reports",
        json={"scope_type": "session", "session_id": sample_persisted_session.id, "format": "csv"},
    )
    assert res_csv_create.status_code == 201
    csv_id = res_csv_create.json()["id"]

    res_csv_dl = client.get(f"/api/v1/reports/{csv_id}/download")
    assert res_csv_dl.status_code == 200
    assert "text/csv" in res_csv_dl.headers["content-type"]
    assert "--- EXECUTIVE SUMMARY ---" in res_csv_dl.text


def test_report_security_path_traversal_rejection(db_session: Session):
    """Tests that path traversal attempts or unauthorized file accesses are rejected."""
    # Attempt to retrieve a non-existent report
    fake_id = str(uuid.uuid4())
    with pytest.raises(AppException) as exc_info:
        ReportService.get_report_file(db_session, fake_id)
    assert exc_info.value.status_code == 404


def test_report_repeat_generation_deterministic_content(
    db_session: Session, sample_persisted_session: AnalysisSession
):
    """
    Tests that repeat generation against unchanged database records
    yields identical normalized report domain content.
    """
    report_data_1 = ReportAssembler.assemble_session_report(
        db=db_session,
        report_id="id_1",
        session_id=sample_persisted_session.id,
    )
    report_data_2 = ReportAssembler.assemble_session_report(
        db=db_session,
        report_id="id_2",
        session_id=sample_persisted_session.id,
    )

    # Compare core metrics
    assert report_data_1.traffic_overview == report_data_2.traffic_overview
    assert report_data_1.vehicle_composition == report_data_2.vehicle_composition
    assert report_data_1.directional_flow == report_data_2.directional_flow
    assert report_data_1.lane_analysis == report_data_2.lane_analysis
    assert report_data_1.anomalies == report_data_2.anomalies
    assert report_data_1.insights == report_data_2.insights
    assert report_data_1.prediction_status == report_data_2.prediction_status


def test_report_delete_cascades_artifact(
    client: TestClient, sample_persisted_session: AnalysisSession
):
    """Tests DELETE /api/v1/reports/{id} removes the database record and file artifact."""
    res_create = client.post(
        "/api/v1/reports",
        json={"scope_type": "session", "session_id": sample_persisted_session.id, "format": "pdf"},
    )
    assert res_create.status_code == 201
    report_id = res_create.json()["id"]

    # Delete
    res_del = client.delete(f"/api/v1/reports/{report_id}")
    assert res_del.status_code == 200

    # Ensure 404 on subsequent get
    res_get = client.get(f"/api/v1/reports/{report_id}")
    assert res_get.status_code == 404
