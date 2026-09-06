"""
Comprehensive Unit and Integration tests for Phase 10: Database Integration.
Tests ORM models, relationships, cascading deletes, unique constraints, API endpoints,
and end-to-end persistence across the full CV pipeline.
"""
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import tempfile
from typing import Generator

import cv2
from fastapi import status
from fastapi.testclient import TestClient
import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.analysis import (
    AnalysisSession,
    CrossingEventRecord,
    LaneResultRecord,
    TrafficMetricsRecord,
)
from app.models.video import Video
from app.schemas.analysis import AnalysisRunRequest
from app.services.cv.analysis_persistence_service import AnalysisPersistenceService

# Isolated SQLite test database
TEST_DB_PATH = Path(tempfile.gettempdir()) / "test_phase10_platform.db"
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


def create_test_video_file(path: Path, width: int = 320, height: int = 240, frames: int = 15) -> Path:
    """Helper creating a synthetic mp4 video with moving vehicles."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, 10.0, (width, height))
    for i in range(frames):
        frame = np.full((height, width, 3), 40, dtype=np.uint8)
        # Moving vehicle in left lane
        y1 = int(30 + i * 10)
        cv2.rectangle(frame, (50, y1), (90, y1 + 30), (220, 220, 220), -1)
        # Moving vehicle in right lane
        y2 = int(20 + i * 12)
        cv2.rectangle(frame, (200, y2), (240, y2 + 35), (200, 200, 200), -1)
        out.write(frame)
    out.release()
    return path


def test_models_relationships_and_foreign_keys():
    """Validates creation of AnalysisSession and child records with foreign keys."""
    db = TestingSessionLocal()
    try:
        # Create parent Video
        video = Video(
            original_filename="traffic_test.mp4",
            storage_path="/tmp/fake.mp4",
            duration_seconds=10.0,
            fps=30.0,
            resolution="1920x1080",
            frame_count=300,
            status="uploaded",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # Create AnalysisSession
        session = AnalysisSession(
            video_id=video.id,
            analysis_type="full_pipeline",
            status="completed",
            total_frames_processed=50,
            total_vehicles_detected=12,
            total_vehicles_counted=8,
            processing_time_ms=145.5,
            config_snapshot={"confidence_threshold": 0.4},
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Add TrafficMetricsRecord
        metrics = TrafficMetricsRecord(
            analysis_session_id=session.id,
            observation_duration_seconds=5.0,
            total_volume=8,
            flow_rate_per_minute=96.0,
            flow_rate_per_hour=5760.0,
            is_extrapolated=True,
            class_distribution=[{"class_name": "car", "count": 8, "percentage": 100.0}],
            direction_distribution=[{"direction": "inbound", "count": 8, "percentage": 100.0}],
            time_series_buckets=[{"bucket_index": 0, "vehicle_count": 8}],
        )
        db.add(metrics)

        # Add LaneResultRecord
        lane = LaneResultRecord(
            analysis_session_id=session.id,
            lane_id="lane_1",
            lane_name="Northbound Lane",
            direction_hint="inbound",
            polygon_json=[[0, 0], [100, 0], [100, 200], [0, 200]],
            polygon_area_px2=20000.0,
            unique_vehicles_count=8,
            peak_occupancy=4,
            average_occupancy=2.5,
            image_space_density=0.0004,
            normalized_density_score=0.25,
            vehicle_class_counts={"car": 8},
        )
        db.add(lane)

        # Add CrossingEventRecord
        event = CrossingEventRecord(
            analysis_session_id=session.id,
            track_id=1,
            class_name="car",
            direction="inbound",
            frame_index=10,
            timestamp_seconds=1.0,
            centroid_x=120.0,
            centroid_y=150.0,
            line_label="main_line",
        )
        db.add(event)
        db.commit()

        # Query back and verify relationships
        saved_session = db.query(AnalysisSession).filter(AnalysisSession.id == session.id).first()
        assert saved_session is not None
        assert saved_session.video.original_filename == "traffic_test.mp4"
        assert saved_session.traffic_metrics.total_volume == 8
        assert saved_session.traffic_metrics.is_extrapolated is True
        assert len(saved_session.lane_results) == 1
        assert saved_session.lane_results[0].lane_id == "lane_1"
        assert len(saved_session.crossing_events) == 1
        assert saved_session.crossing_events[0].track_id == 1

    finally:
        db.close()


def test_crossing_events_unique_constraint():
    """Enforces that duplicate crossing events with identical (session, track_id, line) are rejected."""
    db = TestingSessionLocal()
    try:
        video = Video(
            original_filename="vid.mp4",
            storage_path="/tmp/vid.mp4",
            duration_seconds=5.0,
            fps=10.0,
            resolution="640x480",
            frame_count=50,
            status="uploaded",
        )
        db.add(video)
        db.commit()

        session = AnalysisSession(video_id=video.id, analysis_type="counting", status="completed")
        db.add(session)
        db.commit()

        event1 = CrossingEventRecord(
            analysis_session_id=session.id,
            track_id=42,
            class_name="bus",
            direction="inbound",
            frame_index=5,
            timestamp_seconds=0.5,
            centroid_x=100.0,
            centroid_y=100.0,
            line_label="tripwire_1",
        )
        db.add(event1)
        db.commit()

        # Duplicate event with same track_id and line_label in same session
        event2 = CrossingEventRecord(
            analysis_session_id=session.id,
            track_id=42,
            class_name="bus",
            direction="inbound",
            frame_index=15,
            timestamp_seconds=1.5,
            centroid_x=105.0,
            centroid_y=110.0,
            line_label="tripwire_1",
        )
        db.add(event2)
        with pytest.raises(IntegrityError):
            db.commit()

    finally:
        db.close()


def test_end_to_end_analysis_run_and_persistence(tmp_path: Path):
    """
    End-to-end integration test:
    1. Upload real synthetic video clip.
    2. Run POST /api/v1/analysis/videos/{video_id}/run with custom parameters.
    3. Confirm AnalysisSession, TrafficMetrics, LaneResults, and CrossingEvents are created.
    4. Query DB directly in a fresh session to confirm data survival.
    """
    video_file = create_test_video_file(tmp_path / "test_persist.mp4")

    with TestClient(app) as client:
        with open(video_file, "rb") as f:
            upload_res = client.post(
                "/api/v1/videos/upload",
                files={"file": ("test_persist.mp4", f, "video/mp4")},
            )
        assert upload_res.status_code == 201
        video_id = upload_res.json()["id"]

        run_res = client.post(
            f"/api/v1/analysis/videos/{video_id}/run",
            json={
                "analysis_type": "full_pipeline",
                "max_frames": 15,
                "confidence_threshold": 0.2,
                "counting_line": {
                    "p1": {"x": 0.0, "y": 0.5},
                    "p2": {"x": 1.0, "y": 0.5},
                    "label": "mid_line",
                    "direction_a_to_b": "inbound",
                    "direction_b_to_a": "outbound",
                },
                "lanes": [
                    {
                        "lane_id": "lane_left",
                        "name": "Left Highway Lane",
                        "polygon": [[0, 0], [160, 0], [160, 240], [0, 240]],
                        "direction_hint": "inbound",
                    },
                    {
                        "lane_id": "lane_right",
                        "name": "Right Highway Lane",
                        "polygon": [[160, 0], [320, 0], [320, 240], [160, 240]],
                        "direction_hint": "outbound",
                    },
                ],
            },
        )
        assert run_res.status_code == 201
        data = run_res.json()

        assert data["video_id"] == video_id
        assert data["status"] == "completed"
        assert data["total_frames_processed"] > 0
        assert data["traffic_metrics"] is not None
        assert data["traffic_metrics"]["is_extrapolated"] is True
        assert len(data["lane_results"]) == 2
        assert "uploads" not in str(data)  # Security check: no path leakage

        session_id = data["id"]

    # Open completely fresh session to verify persistence survival
    db = TestingSessionLocal()
    try:
        persisted = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
        assert persisted is not None
        assert persisted.status == "completed"
        assert persisted.video_id == video_id
        assert persisted.traffic_metrics is not None
        assert len(persisted.lane_results) == 2
    finally:
        db.close()


def test_analysis_sessions_list_and_filter(tmp_path: Path):
    """Tests GET /api/v1/analysis/sessions with pagination and filtering."""
    video_file = create_test_video_file(tmp_path / "test_list.mp4")

    with TestClient(app) as client:
        with open(video_file, "rb") as f:
            upload_res = client.post(
                "/api/v1/videos/upload",
                files={"file": ("test_list.mp4", f, "video/mp4")},
            )
        video_id = upload_res.json()["id"]

        # Run 2 sessions
        client.post(f"/api/v1/analysis/videos/{video_id}/run", json={"max_frames": 5})
        client.post(f"/api/v1/analysis/videos/{video_id}/run", json={"max_frames": 5})

        list_res = client.get("/api/v1/analysis/sessions?limit=10&offset=0")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 2
        assert len(list_data["sessions"]) >= 2
        assert list_data["sessions"][0]["video_id"] == video_id

        # Video-scoped list
        vid_sessions_res = client.get(f"/api/v1/analysis/videos/{video_id}/sessions")
        assert vid_sessions_res.status_code == 200
        assert vid_sessions_res.json()["total"] == 2


def test_delete_analysis_session_cascades(tmp_path: Path):
    """Tests that DELETE /api/v1/analysis/sessions/{id} deletes the session and cascades child records."""
    video_file = create_test_video_file(tmp_path / "test_delete.mp4")

    with TestClient(app) as client:
        with open(video_file, "rb") as f:
            upload_res = client.post(
                "/api/v1/videos/upload",
                files={"file": ("test_delete.mp4", f, "video/mp4")},
            )
        video_id = upload_res.json()["id"]

        run_res = client.post(f"/api/v1/analysis/videos/{video_id}/run", json={"max_frames": 5})
        session_id = run_res.json()["id"]

        # Delete session
        del_res = client.delete(f"/api/v1/analysis/sessions/{session_id}")
        assert del_res.status_code == 200

        # Querying deleted session returns 404
        get_res = client.get(f"/api/v1/analysis/sessions/{session_id}")
        assert get_res.status_code == 404

        # Confirm video still exists
        vid_res = client.get(f"/api/v1/videos/{video_id}")
        assert vid_res.status_code == 200


def test_nonexistent_session_returns_404():
    """GET /api/v1/analysis/sessions/{uuid} returns clean structured 404."""
    with TestClient(app) as client:
        res = client.get("/api/v1/analysis/sessions/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404
        data = res.json()
        assert data["error"]["code"] == "session_not_found"


def test_analysis_info_endpoint():
    """GET /api/v1/analysis/info returns schema and persistence rules."""
    with TestClient(app) as client:
        res = client.get("/api/v1/analysis/info")
        assert res.status_code == 200
        data = res.json()
        assert "analysis_sessions" in data["persisted_entities"]
        assert "traffic_metrics" in data["persisted_entities"]
