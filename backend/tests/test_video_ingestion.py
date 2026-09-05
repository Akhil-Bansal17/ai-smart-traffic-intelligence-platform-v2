"""
Unit and integration tests for Phase 4 Video Ingestion pipeline.
Tests all 15 categories mandated in Phase 4 specification:
1. Valid video upload succeeds end-to-end
2. Unsupported extension rejected
3. Spoofed MIME / extension rejected
4. Oversized file rejected
5. Malicious / path-traversal filename handled safely
6. Empty file rejected
7. Corrupted video rejected
8. Metadata extraction validation
9. Frame extraction sampling validation
10. API response shape validation (no storage path leaked)
11. Centralized error shape validation
12. Cleanup behavior (zero orphaned files on error)
13. Video retrieval by ID and 404 behavior
14. Video list endpoint
15. Sampling rate (target_fps) bounds
"""
import io
import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.video import Video
from app.services.cv.video_source import VideoSource
from app.services.cv.video_validator import (
    get_secure_storage_path,
    sanitize_filename,
    validate_extension,
    validate_magic_bytes,
)

# Test DB engine using temporary SQLite database for full isolation
TEST_DB_PATH = Path(tempfile.gettempdir()) / "test_traffic_platform.db"
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
def setup_test_db_and_uploads():
    """Create test tables and isolated temporary upload directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="test_uploads_")
    old_upload_dir = settings.upload_dir
    settings.upload_dir = temp_dir

    # Create tables in test DB engine
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    yield

    # Clean up tables, overrides, and test upload dir
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    settings.upload_dir = old_upload_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except OSError:
            pass


def create_synthetic_video(
    file_path: Path,
    width: int = 320,
    height: int = 240,
    fps: int = 10,
    num_frames: int = 30,
) -> Path:
    """Creates a deterministic synthetic test video using OpenCV."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(file_path), fourcc, float(fps), (width, height))
    for i in range(num_frames):
        # Create a frame with a colored rectangle moving across
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        x = int((i / num_frames) * (width - 40))
        cv2.rectangle(frame, (x, 50), (x + 40, 90), (0, 255, 128), -1)
        out.write(frame)
    out.release()
    return file_path


# ============================================================================
# Unit Tests: Sanitization, Magic Bytes & VideoSource
# ============================================================================

def test_sanitize_filename_traversal():
    """Category 5: Path traversal sequences in filenames are safely stripped."""
    safe_name, ext = sanitize_filename("../../etc/passwd.mp4")
    assert safe_name == "passwd.mp4"
    assert ext == ".mp4"

    safe_name_win, ext_win = sanitize_filename("..\\..\\windows\\system32\\test.avi")
    assert safe_name_win == "test.avi"
    assert ext_win == ".avi"

    # Null byte attack
    safe_name_null, ext_null = sanitize_filename("malicious\x00.mp4")
    assert "\x00" not in safe_name_null
    assert ext_null == ".mp4"


def test_validate_extension_whitelist():
    """Category 2: Unsupported extensions raise unsupported_format."""
    validate_extension(".mp4")
    validate_extension(".avi")
    validate_extension(".mov")

    with pytest.raises(Exception) as exc_info:
        validate_extension(".exe")
    assert exc_info.value.code == "unsupported_format"

    with pytest.raises(Exception) as exc_info:
        validate_extension(".txt")
    assert exc_info.value.code == "unsupported_format"


def test_magic_bytes_anti_spoofing():
    """Category 3: Non-video files disguised with .mp4 extension are detected."""
    # Real MP4 header typically contains 'ftyp' at index 4
    fake_header = b"This is just plain text, not an MP4!"
    assert not validate_magic_bytes(fake_header, ".mp4")

    # Real MP4 header mockup
    valid_mp4_header = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41"
    assert validate_magic_bytes(valid_mp4_header, ".mp4")


def test_metadata_extraction_unit(tmp_path: Path):
    """Category 8: VideoSource accurately extracts width, height, fps, duration."""
    video_path = tmp_path / "test_synth.mp4"
    create_synthetic_video(video_path, width=320, height=240, fps=10, num_frames=30)

    with VideoSource(video_path) as src:
        meta = src.read_metadata()
        assert meta.width == 320
        assert meta.height == 240
        assert meta.resolution == "320x240"
        assert meta.fps == 10.0
        assert meta.frame_count == 30
        assert meta.duration_seconds == 3.0


def test_frame_extraction_sampling(tmp_path: Path):
    """Category 9 & 15: Frame extraction samples at target_fps."""
    video_path = tmp_path / "test_synth.mp4"
    create_synthetic_video(video_path, width=320, height=240, fps=10, num_frames=30)

    with VideoSource(video_path) as src:
        # Source is 10 FPS (30 frames total = 3 sec). Sampling at 5 FPS should yield ~15 frames.
        frames = list(src.extract_frames(target_fps=5))
        assert len(frames) == 15

        for frame_idx, timestamp_sec, frame_bgr in frames:
            assert isinstance(frame_idx, int)
            assert isinstance(timestamp_sec, float)
            assert frame_bgr.shape == (240, 320, 3)
            assert frame_bgr.dtype == np.uint8


# ============================================================================
# Integration Tests: End-to-End API Endpoints
# ============================================================================

def test_valid_video_upload_success(tmp_path: Path):
    """Category 1 & 10: Valid upload succeeds and returns sanitized response without storage paths."""
    client = TestClient(app)
    video_path = tmp_path / "traffic_sample.mp4"
    create_synthetic_video(video_path, width=640, height=480, fps=15, num_frames=45)

    with open(video_path, "rb") as f:
        response = client.post(
            "/api/v1/videos/upload",
            files={"file": ("traffic_sample.mp4", f, "video/mp4")},
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["original_filename"] == "traffic_sample.mp4"
    assert data["resolution"] == "640x480"
    assert data["fps"] == 15.0
    assert data["frame_count"] == 45
    assert data["duration_seconds"] == 3.0
    assert data["status"] == "uploaded"

    # Security rule: server storage_path must NOT be leaked
    assert "storage_path" not in data
    assert "/uploads/" not in str(data)


def test_unsupported_extension_rejected():
    """Category 2 & 11: Uploading a .txt file returns structured error."""
    client = TestClient(app)
    fake_file = io.BytesIO(b"Unauthorized text content")

    response = client.post(
        "/api/v1/videos/upload",
        files={"file": ("document.txt", fake_file, "text/plain")},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "unsupported_format"


def test_spoofed_mime_and_extension_rejected():
    """Category 3: Uploading a text file renamed to .mp4 is caught by magic byte check."""
    client = TestClient(app)
    fake_mp4 = io.BytesIO(b"Hello, I am pretending to be an MP4 video file!")

    response = client.post(
        "/api/v1/videos/upload",
        files={"file": ("spoofed.mp4", fake_mp4, "video/mp4")},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "invalid_video_content"


def test_oversized_file_rejected():
    """Category 4: File exceeding max_upload_size_mb is rejected with 413."""
    client = TestClient(app)
    old_limit = settings.max_upload_size_mb
    settings.max_upload_size_mb = 1  # 1 MB limit for test

    try:
        # Create 1.5 MB payload
        large_payload = io.BytesIO(b"0" * (1536 * 1024))
        response = client.post(
            "/api/v1/videos/upload",
            files={"file": ("huge_file.mp4", large_payload, "video/mp4")},
        )
        assert response.status_code == 413
        data = response.json()
        assert data["error"]["code"] == "file_too_large"
    finally:
        settings.max_upload_size_mb = old_limit


def test_empty_file_rejected():
    """Category 6: 0-byte upload is rejected cleanly."""
    client = TestClient(app)
    empty_file = io.BytesIO(b"")

    response = client.post(
        "/api/v1/videos/upload",
        files={"file": ("empty.mp4", empty_file, "video/mp4")},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "empty_file"


def test_corrupted_video_rejected():
    """Category 7: Video with valid magic bytes but corrupted frame stream is rejected."""
    client = TestClient(app)
    # Valid MP4 box header followed by random garbage that OpenCV cannot decode
    corrupted_data = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41" + b"\xFF" * 1024
    corrupted_file = io.BytesIO(corrupted_data)

    response = client.post(
        "/api/v1/videos/upload",
        files={"file": ("corrupted.mp4", corrupted_file, "video/mp4")},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"]["code"] == "corrupted_video"


def test_cleanup_on_failed_upload():
    """Category 12: Rejected uploads leave no orphaned files in upload directory."""
    client = TestClient(app)
    upload_dir_path = Path(settings.upload_dir)

    initial_files = set(os.listdir(upload_dir_path)) if upload_dir_path.exists() else set()

    fake_file = io.BytesIO(b"Rejected content")
    client.post(
        "/api/v1/videos/upload",
        files={"file": ("bad_file.mp4", fake_file, "video/mp4")},
    )

    after_files = set(os.listdir(upload_dir_path)) if upload_dir_path.exists() else set()
    assert initial_files == after_files, "Orphaned files remained in upload directory after failure!"


def test_get_and_list_videos(tmp_path: Path):
    """Category 13 & 14: Retrieve video by ID and list all uploaded videos."""
    client = TestClient(app)
    video_path = tmp_path / "traffic_session.mp4"
    create_synthetic_video(video_path, width=320, height=240, fps=10, num_frames=20)

    with open(video_path, "rb") as f:
        upload_resp = client.post(
            "/api/v1/videos/upload",
            files={"file": ("traffic_session.mp4", f, "video/mp4")},
        )
    assert upload_resp.status_code == status.HTTP_201_CREATED
    video_id = upload_resp.json()["id"]

    # 1. Retrieve by ID
    get_resp = client.get(f"/api/v1/videos/{video_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["id"] == video_id
    assert get_resp.json()["original_filename"] == "traffic_session.mp4"

    # 2. Nonexistent ID -> 404
    nonexistent_resp = client.get("/api/v1/videos/00000000-0000-0000-0000-000000000000")
    assert nonexistent_resp.status_code == status.HTTP_404_NOT_FOUND
    assert nonexistent_resp.json()["error"]["code"] == "video_not_found"

    # 3. List all videos
    list_resp = client.get("/api/v1/videos")
    assert list_resp.status_code == status.HTTP_200_OK
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(v["id"] == video_id for v in list_data["videos"])
