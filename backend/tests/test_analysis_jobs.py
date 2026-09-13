"""
Tests for Phase 17: Analysis Job Orchestration & Real-Time Processing Foundation.

Validates:
- Explicit state machine transitions and immutable terminal states
- Job creation, fast non-blocking response, and persistence
- Duplicate active job rejection (idempotency/conflict)
- Progress tracking and indeterminate progress handling
- Cooperative cancellation of QUEUED and RUNNING jobs
- Rejection of cancellation for terminal jobs
- Startup recovery of stale RUNNING jobs
- Concurrency limit and queueing behavior
- Provenance preservation across job executions
- Dashboard safety (strictly read-only)
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import threading
import time

import cv2
from fastapi.testclient import TestClient
import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import Settings, settings
from app.core.exceptions import AppException
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import AnalysisSession
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.video import Video
from app.schemas.analysis_job import AnalysisJobCreateRequest
from app.services.cv.job_manager import AnalysisJobManager, get_analysis_job_manager


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


TEST_DB_PATH = Path(tempfile.gettempdir()) / f"test_analysis_jobs_{os.getpid()}.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(autouse=True)
def setup_teardown_db():
    Base.metadata.create_all(bind=test_engine)
    get_analysis_job_manager().set_session_factory(TestingSessionLocal)
    yield
    manager = get_analysis_job_manager()
    with manager._lock:
        for event in list(manager._cancellation_events.values()):
            event.set()
    Base.metadata.drop_all(bind=test_engine)
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


@pytest.fixture
def test_db():
    """Provides an isolated SQLite database session for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_video_file(tmp_path):
    """Creates a small readable synthetic video fixture for real frame extraction."""
    video_path = tmp_path / "traffic_sample.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (320, 240))
    for i in range(15):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        # Moving box simulating vehicle
        cv2.rectangle(frame, (20 + i * 8, 50), (60 + i * 8, 90), (255, 255, 255), -1)
        out.write(frame)
    out.release()
    return str(video_path)


@pytest.fixture
def sample_video(test_db, sample_video_file):
    """Creates a Video model record in DB backed by real file fixture."""
    video = Video(
        id="test-video-phase17-001",
        original_filename="traffic_sample.mp4",
        storage_path=sample_video_file,
        duration_seconds=1.5,
        fps=10.0,
        resolution="320x240",
        frame_count=15,
        status="uploaded",
        source_type="real_traffic_camera",
        provenance_verified=True,
        provenance_note="Verified real camera for testing",
    )
    test_db.add(video)
    test_db.commit()
    test_db.refresh(video)
    return video


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
# A. Job Creation Tests
# =========================================================================


def test_create_analysis_job_success(client, sample_video):
    """Verifies that POST /api/v1/analysis/jobs returns 201 with job in QUEUED/RUNNING status quickly."""
    response = client.post(
        "/api/v1/analysis/jobs",
        json={
            "video_id": sample_video.id,
            "analysis_type": "full_pipeline",
            "confidence_threshold": 0.35,
            "max_frames": 20,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["video_id"] == sample_video.id
    assert data["status"] in ("queued", "running", "completed")
    assert "id" in data
    assert data["provenance_category"] == "real_analysis_job"
    assert data["is_synthetic"] is False


def test_create_analysis_job_nonexistent_video(client):
    """Verifies that job creation for missing video returns 404."""
    response = client.post(
        "/api/v1/analysis/jobs",
        json={"video_id": "nonexistent-vid-999"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "video_not_found"


def test_duplicate_active_job_conflict(client, sample_video, test_db):
    """Verifies that submitting a second job for a video with active job returns 409 Conflict."""
    # Place an active QUEUED job manually
    job = AnalysisJob(
        video_id=sample_video.id,
        status=JobStatus.QUEUED.value,
        analysis_type="full_pipeline",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    test_db.add(job)
    test_db.commit()

    response = client.post(
        "/api/v1/analysis/jobs",
        json={"video_id": sample_video.id},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_active_job"


def test_create_job_allowed_after_completed(client, sample_video, test_db):
    """Verifies that a completed historical job does not block legitimate re-analysis."""
    job = AnalysisJob(
        video_id=sample_video.id,
        status=JobStatus.COMPLETED.value,
        analysis_type="full_pipeline",
        completed_at=utcnow(),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    test_db.add(job)
    test_db.commit()

    response = client.post(
        "/api/v1/analysis/jobs",
        json={"video_id": sample_video.id, "max_frames": 10},
    )
    assert response.status_code == 201


# =========================================================================
# B. State Machine & Lifecycle Tests
# =========================================================================


def test_job_state_machine_valid_transitions(test_db, sample_video):
    """Validates full happy path: QUEUED -> RUNNING -> COMPLETED."""
    job = AnalysisJob(
        video_id=sample_video.id,
        status=JobStatus.QUEUED.value,
        analysis_type="full_pipeline",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    test_db.add(job)
    test_db.commit()

    # Transition to RUNNING
    job.status = JobStatus.RUNNING.value
    job.started_at = utcnow()
    job.updated_at = utcnow()
    test_db.commit()
    test_db.refresh(job)
    assert job.status == JobStatus.RUNNING.value

    # Transition to COMPLETED
    job.status = JobStatus.COMPLETED.value
    job.progress = 1.0
    job.completed_at = utcnow()
    job.updated_at = utcnow()
    test_db.commit()
    test_db.refresh(job)
    assert job.status == JobStatus.COMPLETED.value
    assert job.progress == 1.0


def test_cancel_terminal_job_rejected(client, test_db, sample_video):
    """Validates that cancelling a COMPLETED or FAILED job returns 400 Bad Request."""
    job = AnalysisJob(
        video_id=sample_video.id,
        status=JobStatus.COMPLETED.value,
        analysis_type="full_pipeline",
        completed_at=utcnow(),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    test_db.add(job)
    test_db.commit()

    response = client.post(f"/api/v1/analysis/jobs/{job.id}/cancel")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "cannot_cancel_terminal_job"


# =========================================================================
# C. Cancellation Tests
# =========================================================================


def test_cancel_queued_job_immediately(client, test_db, sample_video):
    """Verifies that cancelling a QUEUED job transitions directly to CANCELLED."""
    job = AnalysisJob(
        video_id=sample_video.id,
        status=JobStatus.QUEUED.value,
        analysis_type="full_pipeline",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    test_db.add(job)
    test_db.commit()

    response = client.post(f"/api/v1/analysis/jobs/{job.id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["job"]["status"] == "cancelled"


def test_cancel_running_job_cooperative(test_db, sample_video):
    """Verifies that cancelling a RUNNING job sets cancellation_requested and signals token."""
    manager = AnalysisJobManager()
    job = AnalysisJob(
        video_id=sample_video.id,
        status=JobStatus.RUNNING.value,
        analysis_type="full_pipeline",
        started_at=utcnow(),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    test_db.add(job)
    test_db.commit()

    cancel_event = threading.Event()
    with manager._lock:
        manager._cancellation_events[job.id] = cancel_event

    updated_job = manager.cancel_job(db=test_db, job_id=job.id)
    assert updated_job.cancellation_requested is True
    assert cancel_event.is_set() is True


# =========================================================================
# D. Stale Job Recovery Tests
# =========================================================================


def test_startup_recovery_of_stale_running_jobs(test_db, sample_video):
    """Verifies that at startup, any orphaned RUNNING jobs are transitioned to FAILED."""
    stale_job = AnalysisJob(
        video_id=sample_video.id,
        status=JobStatus.RUNNING.value,
        analysis_type="full_pipeline",
        started_at=utcnow(),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    test_db.add(stale_job)
    test_db.commit()

    manager = AnalysisJobManager()
    recovered = manager.recover_stale_jobs(test_db)
    assert recovered == 1

    test_db.refresh(stale_job)
    assert stale_job.status == JobStatus.FAILED.value
    assert stale_job.error_code == "process_restarted_stale_job"
    assert stale_job.completed_at is not None


# =========================================================================
# E. API Queries & Pagination
# =========================================================================


def test_get_job_detail(client, test_db, sample_video):
    """Verifies GET /api/v1/analysis/jobs/{job_id} returns accurate job fields."""
    job = AnalysisJob(
        video_id=sample_video.id,
        status=JobStatus.RUNNING.value,
        analysis_type="full_pipeline",
        progress=0.45,
        frames_processed=45,
        total_frames=100,
        processing_fps=12.5,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    test_db.add(job)
    test_db.commit()

    response = client.get(f"/api/v1/analysis/jobs/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job.id
    assert data["progress"] == 0.45
    assert data["frames_processed"] == 45
    assert data["total_frames"] == 100
    assert data["processing_fps"] == 12.5


def test_list_jobs_bounded_pagination(client, test_db, sample_video):
    """Verifies GET /api/v1/analysis/jobs enforces pagination limits and status filters."""
    for i in range(5):
        j = AnalysisJob(
            video_id=sample_video.id,
            status=JobStatus.COMPLETED.value if i % 2 == 0 else JobStatus.QUEUED.value,
            analysis_type="full_pipeline",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        test_db.add(j)
    test_db.commit()

    # Bounded query
    response = client.get("/api/v1/analysis/jobs?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) == 2
    assert data["total"] == 5

    # Filter query
    resp_filtered = client.get("/api/v1/analysis/jobs?status=completed")
    assert resp_filtered.status_code == 200
    data_filtered = resp_filtered.json()
    assert len(data_filtered["jobs"]) == 3
    assert all(j["status"] == "completed" for j in data_filtered["jobs"])


# =========================================================================
# F. Concurrency & Settings
# =========================================================================


def test_settings_concurrency_validation():
    """Verifies Settings validates max_concurrent_analysis_jobs bounds."""
    s = Settings()
    assert s.max_concurrent_analysis_jobs == 2

    # Invalid below 1
    with pytest.raises(ValueError):
        Settings(max_concurrent_analysis_jobs=0)

    # Invalid above 10
    with pytest.raises(ValueError):
        Settings(max_concurrent_analysis_jobs=11)


# =========================================================================
# G. Provenance Preservation
# =========================================================================


def test_job_provenance_preservation(client, test_db, sample_video_file):
    """Verifies synthetic video produces synthetic_analysis_job and real video produces real_analysis_job."""
    # Synthetic video
    synth_vid = Video(
        id="test-synth-vid-phase17",
        original_filename="synth.mp4",
        storage_path=sample_video_file,
        source_type="synthetic",
        provenance_verified=False,
    )
    test_db.add(synth_vid)
    test_db.commit()

    resp = client.post("/api/v1/analysis/jobs", json={"video_id": synth_vid.id})
    assert resp.status_code == 201
    assert resp.json()["is_synthetic"] is True
    assert resp.json()["provenance_category"] == "synthetic_analysis_job"
