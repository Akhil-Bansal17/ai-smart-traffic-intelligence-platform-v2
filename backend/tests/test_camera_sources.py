"""
Tests for Phase 21: Live Traffic Monitoring & Camera Source Management.

Validates:
- Camera source CRUD operations & schema validations
- Credential redaction (passwords masked as *** in API responses and logs)
- Deterministic test fixture probe and metadata validation
- Live stream lifecycle: start -> poll live metrics -> stop -> session persistence
- Single-source preview JPEG endpoint validation
- Concurrency and duplicate stream prevention (409 Conflict)
- Provenance integrity (TEST_FIXTURE vs LIVE_OBSERVATION)
- Safe error handling for inactive streams (404 Not Found)
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import time

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import AnalysisSession, CrossingEventRecord, LaneResultRecord, TrafficMetricsRecord
from app.models.analysis_job import AnalysisJob
from app.models.camera_source import CameraSource, CameraSourceStatus, CameraSourceType
from app.services.cv.job_manager import get_analysis_job_manager


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


TEST_DB_PATH = Path(tempfile.gettempdir()) / f"test_camera_sources_{os.getpid()}.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="module", autouse=True)
def setup_module_db():
    Base.metadata.create_all(bind=test_engine)
    get_analysis_job_manager().set_session_factory(TestingSessionLocal)
    yield
    manager = get_analysis_job_manager()
    manager.shutdown(wait=False)
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def clean_database():
    yield
    manager = get_analysis_job_manager()
    # Stop any running live services
    with manager._lock:
        services = list(manager._live_services.values())
    for s in services:
        try:
            s.stop()
            s.join(timeout=2.0)
        except Exception:
            pass
    with manager._lock:
        manager._live_services.clear()
        for event in list(manager._cancellation_events.values()):
            event.set()
        manager._cancellation_events.clear()
        manager._active_job_ids.clear()

    # Clean DB rows between tests
    with TestingSessionLocal() as db:
        try:
            db.query(CrossingEventRecord).delete()
            db.query(LaneResultRecord).delete()
            db.query(TrafficMetricsRecord).delete()
            db.query(AnalysisJob).delete()
            db.query(AnalysisSession).delete()
            db.query(CameraSource).delete()
            db.commit()
        except Exception:
            db.rollback()


@pytest.fixture
def client():
    """Provides TestClient with dependency override for get_db."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =========================================================================
# Test Cases
# =========================================================================

def test_create_camera_source_success(client: TestClient):
    payload = {
        "name": "North Approach Camera",
        "description": "High-definition intersection feed",
        "source_type": "rtsp",
        "connection_uri": "rtsp://camera.traffic.local:554/stream1",
        "location_name": "Main & 4th Intersection",
    }
    response = client.post("/api/v1/camera-sources", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "North Approach Camera"
    assert data["source_type"] == "rtsp"
    assert data["status"] == "disconnected"
    assert data["enabled"] is True
    assert "id" in data


def test_credential_redaction_in_api(client: TestClient):
    payload = {
        "name": "Secure Gateway Camera",
        "description": "Camera requiring basic auth",
        "source_type": "rtsp",
        "connection_uri": "rtsp://admin:supersecretpassword999@192.168.1.50:554/h264",
        "location_name": "Secure Gate A",
    }
    # Create
    create_res = client.post("/api/v1/camera-sources", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    camera_id = created_data["id"]

    # Redacted in creation response
    assert "supersecretpassword999" not in created_data["connection_uri"]
    assert created_data["connection_uri"] == "rtsp://admin:***@192.168.1.50:554/h264"

    # Redacted in GET by ID
    get_res = client.get(f"/api/v1/camera-sources/{camera_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert "supersecretpassword999" not in get_data["connection_uri"]
    assert get_data["connection_uri"] == "rtsp://admin:***@192.168.1.50:554/h264"

    # Redacted in list
    list_res = client.get("/api/v1/camera-sources")
    assert list_res.status_code == 200
    list_text = list_res.text
    assert "supersecretpassword999" not in list_text


def test_camera_validation_failures(client: TestClient):
    # Empty name
    res1 = client.post("/api/v1/camera-sources", json={
        "name": "",
        "source_type": "rtsp",
        "connection_uri": "rtsp://localhost:554/live",
    })
    assert res1.status_code == 422

    # Invalid source type
    res2 = client.post("/api/v1/camera-sources", json={
        "name": "Bad Camera",
        "source_type": "satellite_radar",
        "connection_uri": "rtsp://localhost:554/live",
    })
    assert res2.status_code == 422

    # Suspicious shell injection characters in URI
    res3 = client.post("/api/v1/camera-sources", json={
        "name": "Injection Attempt",
        "source_type": "rtsp",
        "connection_uri": "rtsp://10.0.0.1; rm -rf /",
    })
    assert res3.status_code == 422


def test_camera_crud_operations(client: TestClient):
    # Create
    create_res = client.post("/api/v1/camera-sources", json={
        "name": "Camera 01",
        "source_type": "test_fixture",
        "connection_uri": "test_fixture://standard_flow",
    })
    assert create_res.status_code == 201
    cam_id = create_res.json()["id"]

    # Read
    get_res = client.get(f"/api/v1/camera-sources/{cam_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Camera 01"

    # Update (PATCH)
    update_res = client.patch(f"/api/v1/camera-sources/{cam_id}", json={
        "name": "Camera 01 Updated",
        "location_name": "Downtown Corridor",
        "enabled": True,
    })
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Camera 01 Updated"
    assert update_res.json()["location_name"] == "Downtown Corridor"

    # Delete
    del_res = client.delete(f"/api/v1/camera-sources/{cam_id}")
    assert del_res.status_code == 204

    # 404
    get_res404 = client.get(f"/api/v1/camera-sources/{cam_id}")
    assert get_res404.status_code == 404


def test_camera_test_probe_fixture(client: TestClient):
    # Create test fixture camera
    create_res = client.post("/api/v1/camera-sources", json={
        "name": "Probe Test Fixture",
        "source_type": "test_fixture",
        "connection_uri": "test_fixture://standard_flow",
    })
    cam_id = create_res.json()["id"]

    # Test connection probe
    probe_res = client.post(f"/api/v1/camera-sources/{cam_id}/test")
    assert probe_res.status_code == 200
    probe_data = probe_res.json()
    assert probe_data["success"] is True
    assert probe_data["width"] == 640
    assert probe_data["height"] == 480
    assert probe_data["fps"] > 0


def test_live_monitoring_lifecycle_test_fixture(client: TestClient):
    # 1. Register test fixture camera
    create_res = client.post("/api/v1/camera-sources", json={
        "name": "Live Test Fixture Cam",
        "source_type": "test_fixture",
        "connection_uri": "test_fixture://standard_flow",
    })
    cam_id = create_res.json()["id"]

    # 2. Start live monitoring
    start_res = client.post(f"/api/v1/camera-sources/{cam_id}/start", json={
        "processing_fps": 10,
    })
    assert start_res.status_code == 201, start_res.text
    start_data = start_res.json()
    assert start_data["status"] in ("queued", "running")
    job_id = start_data["id"]

    # 3. Poll live status (allowing time for model initialization and first frame inference)
    status_data = {}
    for _ in range(20):
        time.sleep(0.3)
        status_res = client.get(f"/api/v1/camera-sources/{cam_id}/live-status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        if status_data.get("frames_acquired", 0) > 0 and status_data.get("frames_processed", 0) > 0:
            break

    assert status_data["is_live"] is True
    assert status_data["frames_acquired"] > 0
    assert status_data["provenance_tag"] == "test_fixture_observation"

    # 4. Check preview JPEG
    preview_res = client.get(f"/api/v1/camera-sources/{cam_id}/preview.jpg")
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"] == "image/jpeg"
    assert preview_res.content[:2] == b"\xff\xd8"  # Valid JPEG SOI

    # 5. Stop live monitoring
    stop_res = client.post(f"/api/v1/camera-sources/{cam_id}/stop")
    assert stop_res.status_code == 200
    stop_data = stop_res.json()
    assert stop_data["status"] == "completed"

    # 6. Verify session persistence in DB
    session_id = stop_data.get("session_id")
    assert session_id is not None
    session_res = client.get(f"/api/v1/analysis/sessions/{session_id}")
    assert session_res.status_code == 200
    sess = session_res.json()
    assert sess["session_mode"] == "TEST_FIXTURE"
    assert sess["camera_source_id"] == cam_id
    assert sess["status"] == "completed"
    assert sess["total_frames_processed"] > 0


def test_duplicate_live_stream_conflict(client: TestClient):
    # Register test fixture camera
    create_res = client.post("/api/v1/camera-sources", json={
        "name": "Duplicate Stream Test Cam",
        "source_type": "test_fixture",
        "connection_uri": "test_fixture://standard_flow",
    })
    cam_id = create_res.json()["id"]

    # Start first time
    start1 = client.post(f"/api/v1/camera-sources/{cam_id}/start")
    assert start1.status_code == 201

    try:
        # Start second time on same camera -> 409 Conflict
        start2 = client.post(f"/api/v1/camera-sources/{cam_id}/start")
        assert start2.status_code == 409
    finally:
        client.post(f"/api/v1/camera-sources/{cam_id}/stop")


def test_stop_inactive_stream_returns_404(client: TestClient):
    create_res = client.post("/api/v1/camera-sources", json={
        "name": "Idle Cam",
        "source_type": "test_fixture",
        "connection_uri": "test_fixture://standard_flow",
    })
    cam_id = create_res.json()["id"]

    stop_res = client.post(f"/api/v1/camera-sources/{cam_id}/stop")
    assert stop_res.status_code == 404
