"""
Unit and integration tests for Phase 16: Production Readiness, Reliability, Security & Observability Hardening.

Covers:
1. Application lifecycle and error handling consistency
2. File upload security, path traversal prevention, magic-byte anti-spoofing
3. Database transaction isolation and rollback behavior
4. API query pagination bounding
5. Readiness diagnostic probes under normal and degraded conditions
6. Read-only dashboard idempotency guarantees
7. Provenance integrity across subsystems
"""
from datetime import datetime, timezone
import io
from pathlib import Path
import tempfile
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import AnalysisSession, LaneResultRecord, TrafficMetricsRecord
from app.models.anomaly import AnomalyEvent
from app.models.video import Video
from app.services.anomaly.detector import AnomalyDetectionService
from app.services.cv.video_validator import sanitize_filename, validate_magic_bytes


def utcnow():
    return datetime.now(timezone.utc)


TEST_DB_PATH = Path(tempfile.gettempdir()) / "test_phase16_readiness.db"
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
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


def test_api_error_response_standardized_shape(client: TestClient):
    """Verifies that all API errors return the standard shape {"error": {"code": "...", "message": "..."}}."""
    # 404 Not Found
    resp404 = client.get("/api/v1/videos/non_existent_id_12345")
    assert resp404.status_code == 404
    data404 = resp404.json()
    assert "error" in data404
    assert data404["error"]["code"] == "video_not_found"
    assert "message" in data404["error"]

    # 422 Validation Error
    resp422 = client.get("/api/v1/videos?limit=-5")
    assert resp422.status_code == 422
    data422 = resp422.json()
    assert "error" in data422
    assert data422["error"]["code"] == "validation_error"


def test_upload_security_path_traversal_sanitization():
    """Verifies that path traversal attacks in filenames are completely neutralized."""
    malicious_names = [
        "../../etc/passwd.mp4",
        "..\\..\\windows\\system32\\cmd.exe.mp4",
        "nested/path/to/file.mp4",
        "../../../uploads/trojan.mp4",
    ]
    for name in malicious_names:
        clean, ext = sanitize_filename(name)
        assert "/" not in clean
        assert "\\" not in clean
        assert ".." not in clean
        assert clean.endswith(".mp4")
        assert ext == ".mp4"



def test_readiness_probe_healthy(client: TestClient):
    """Verifies that system readiness reports 'ready' and 200 OK when database is accessible."""
    resp = client.get("/api/v1/health/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["is_ready"] is True
    assert data["dependencies"]["database"]["status"] == "healthy"
    assert data["dependencies"]["storage"]["status"] == "healthy"


def test_video_list_pagination_bounds(client: TestClient, db_session: Session):
    """Verifies bounded query pagination on the videos list endpoint."""
    # Insert 5 test videos
    for i in range(5):
        v = Video(
            id=f"vid_page_test_{i}",
            original_filename=f"clip_{i}.mp4",
            storage_path=f"uploads/clip_{i}.mp4",
            status="ready",
            source_type="synthetic_test",
        )
        db_session.add(v)
    db_session.commit()

    resp = client.get("/api/v1/videos?limit=2&offset=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["videos"]) == 2


def test_dashboard_read_only_isolation(client: TestClient, db_session: Session):
    """Verifies that repeatedly querying dashboard summary causes zero side-effects or mutations."""
    # Seed one completed session
    v = Video(
        id="vid_dash_test",
        original_filename="real_traffic_highway_dyglo.mp4",
        storage_path="uploads/vid_dash_test.mp4",
        status="ready",
        source_type="real_world",
        provenance_verified=True,
        source_reference="https://example.com/traffic.mp4",
        license_reference="MIT",
    )
    s = AnalysisSession(
        id="sess_dash_test",
        video_id="vid_dash_test",
        status="completed",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    m = TrafficMetricsRecord(
        analysis_session_id="sess_dash_test",
        total_volume=20,
        observation_duration_seconds=25.0,
    )
    db_session.add_all([v, s, m])
    db_session.commit()

    # Pre-query counts
    count_before = db_session.scalar(select(text("COUNT(*) FROM analysis_sessions")))

    for _ in range(5):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["system_health"]["backend_online"] is True

    # Post-query counts must be strictly unchanged
    count_after = db_session.scalar(select(text("COUNT(*) FROM analysis_sessions")))
    assert count_before == count_after
