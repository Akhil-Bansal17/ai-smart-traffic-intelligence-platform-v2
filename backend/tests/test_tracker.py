"""
Comprehensive unit and integration test suite for Phase 6 Object Tracking.

Covers:
1. Tracker initialization with configured parameters
2. Single detection creates a new track
3. Track ID continuity across consecutive frames (same moving object retains identical track ID)
4. Multiple simultaneous objects receive distinct track IDs
5. Different vehicle classes tracked independently without identity swaps
6. New object receives an incremental new track ID (not reused)
7. Temporary missed detection (occlusion) is preserved in LOST state and recovered
8. Terminated track does not resurrect after max_lost_frames expiration
9. TrackingResult schema correctness
10. Invalid/nonexistent video ID returns 404 with structured error
11. Pipeline stage distinction (tracking-run vs detections-run)
12. Storage path isolation (no server paths leaked in API responses)
13. End-to-end video tracking endpoint execution
14. Tracker info endpoint (/api/v1/tracking/info)
"""
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.v1.tracking import get_tracker
from app.main import app
from app.services.cv.detector import BoundingBox, DetectionResult
from app.services.cv.tracker import (
    ByteTrackVehicleTracker,
    TrackedObject,
    Tracker,
    TrackState,
)


@pytest.fixture
def fresh_tracker():
    """Provides a freshly instantiated tracker with reset state."""
    tracker = ByteTrackVehicleTracker(iou_threshold=0.3, max_lost_frames=5, min_hits=1)
    tracker.reset()
    return tracker


@pytest.fixture(scope="module")
def test_tracking_video(tmp_path_factory):
    """Creates a deterministic 2-second 640x480 video with multiple moving vehicles."""
    temp_dir = tmp_path_factory.mktemp("tracking_videos")
    video_path = temp_dir / "test_tracking_video.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 10.0
    width, height = 640, 480
    out = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

    for i in range(20):  # 20 frames = 2.0s
        frame = np.ones((height, width, 3), dtype=np.uint8) * 80
        # Simulated road
        cv2.rectangle(frame, (40, 80), (600, 440), (45, 45, 45), -1)

        # Vehicle 1 moving left to right
        car1_x = int(60 + i * 18)
        cv2.rectangle(frame, (car1_x, 150), (car1_x + 80, 220), (0, 0, 200), -1)

        # Vehicle 2 moving right to left
        car2_x = int(500 - i * 15)
        cv2.rectangle(frame, (car2_x, 280), (car2_x + 90, 370), (200, 100, 0), -1)

        out.write(frame)

    out.release()
    return video_path


# --- 1. Tracker Initialization ---
def test_tracker_initialization(fresh_tracker):
    """Test 1: Tracker initializes correctly with parameters."""
    assert isinstance(fresh_tracker, Tracker)
    assert fresh_tracker.tracker_name == "ByteTrack-Kalman-IoU"
    assert fresh_tracker.iou_threshold == 0.3
    assert fresh_tracker.max_lost_frames == 5
    assert fresh_tracker.total_unique_tracks_count == 0


# --- 2. Single Detection Creates New Track ---
def test_single_detection_creates_new_track(fresh_tracker):
    """Test 2: A single detection creates an initial track with track_id = 1."""
    box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0, width=100.0, height=100.0)
    det = DetectionResult(class_id=2, class_name="car", confidence=0.90, bbox=box, frame_index=0, timestamp_seconds=0.0)

    tracks = fresh_tracker.update([det], frame_index=0, timestamp_seconds=0.0)
    assert len(tracks) == 1
    assert tracks[0].track_id == 1
    assert tracks[0].class_name == "car"
    assert tracks[0].confidence == 0.90
    assert tracks[0].hits == 1
    assert fresh_tracker.total_unique_tracks_count == 1


# --- 3. Track ID Continuity Across Consecutive Frames ---
def test_track_id_continuity_across_consecutive_frames(fresh_tracker):
    """Test 3: Same moving vehicle across frames keeps the identical track ID."""
    # Frame 0
    b0 = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0, width=100.0, height=100.0)
    d0 = DetectionResult(class_id=2, class_name="car", confidence=0.88, bbox=b0, frame_index=0, timestamp_seconds=0.0)
    t0 = fresh_tracker.update([d0], frame_index=0, timestamp_seconds=0.0)
    assert len(t0) == 1
    track_id_initial = t0[0].track_id

    # Frame 1: moved slightly (x + 10)
    b1 = BoundingBox(x1=110.0, y1=100.0, x2=210.0, y2=200.0, width=100.0, height=100.0)
    d1 = DetectionResult(class_id=2, class_name="car", confidence=0.89, bbox=b1, frame_index=1, timestamp_seconds=0.2)
    t1 = fresh_tracker.update([d1], frame_index=1, timestamp_seconds=0.2)
    assert len(t1) == 1
    assert t1[0].track_id == track_id_initial
    assert t1[0].hits == 2

    # Frame 2: moved further (x + 20)
    b2 = BoundingBox(x1=120.0, y1=100.0, x2=220.0, y2=200.0, width=100.0, height=100.0)
    d2 = DetectionResult(class_id=2, class_name="car", confidence=0.91, bbox=b2, frame_index=2, timestamp_seconds=0.4)
    t2 = fresh_tracker.update([d2], frame_index=2, timestamp_seconds=0.4)
    assert len(t2) == 1
    assert t2[0].track_id == track_id_initial
    assert t2[0].hits == 3
    assert fresh_tracker.total_unique_tracks_count == 1


# --- 4. Multiple Simultaneous Objects Receive Distinct Track IDs ---
def test_multiple_simultaneous_objects_distinct_ids(fresh_tracker):
    """Test 4: Multiple simultaneous vehicles receive distinct, unique track IDs."""
    b_car1 = BoundingBox(x1=50.0, y1=50.0, x2=150.0, y2=150.0, width=100.0, height=100.0)
    b_car2 = BoundingBox(x1=300.0, y1=200.0, x2=400.0, y2=300.0, width=100.0, height=100.0)

    d1 = DetectionResult(class_id=2, class_name="car", confidence=0.85, bbox=b_car1, frame_index=0, timestamp_seconds=0.0)
    d2 = DetectionResult(class_id=2, class_name="car", confidence=0.87, bbox=b_car2, frame_index=0, timestamp_seconds=0.0)

    tracks = fresh_tracker.update([d1, d2], frame_index=0, timestamp_seconds=0.0)
    assert len(tracks) == 2
    track_ids = {t.track_id for t in tracks}
    assert len(track_ids) == 2
    assert fresh_tracker.total_unique_tracks_count == 2


# --- 5. Different Object Classes Tracked Independently ---
def test_different_classes_tracked_independently(fresh_tracker):
    """Test 5: Different vehicle classes (e.g. car and bus) maintain independent tracks."""
    b_car = BoundingBox(x1=50.0, y1=50.0, x2=150.0, y2=150.0, width=100.0, height=100.0)
    b_bus = BoundingBox(x1=300.0, y1=200.0, x2=500.0, y2=350.0, width=200.0, height=150.0)

    d_car = DetectionResult(class_id=2, class_name="car", confidence=0.90, bbox=b_car, frame_index=0, timestamp_seconds=0.0)
    d_bus = DetectionResult(class_id=5, class_name="bus", confidence=0.85, bbox=b_bus, frame_index=0, timestamp_seconds=0.0)

    tracks = fresh_tracker.update([d_car, d_bus], frame_index=0, timestamp_seconds=0.0)
    classes_by_id = {t.track_id: t.class_name for t in tracks}

    # Frame 1: Move both
    b_car_f1 = BoundingBox(x1=60.0, y1=50.0, x2=160.0, y2=150.0, width=100.0, height=100.0)
    b_bus_f1 = BoundingBox(x1=310.0, y1=200.0, x2=510.0, y2=350.0, width=200.0, height=150.0)
    d_car_f1 = DetectionResult(class_id=2, class_name="car", confidence=0.91, bbox=b_car_f1, frame_index=1, timestamp_seconds=0.2)
    d_bus_f1 = DetectionResult(class_id=5, class_name="bus", confidence=0.87, bbox=b_bus_f1, frame_index=1, timestamp_seconds=0.2)

    tracks_f1 = fresh_tracker.update([d_car_f1, d_bus_f1], frame_index=1, timestamp_seconds=0.2)
    for t in tracks_f1:
        assert classes_by_id[t.track_id] == t.class_name


# --- 6. New Object Receives New Track ID ---
def test_new_object_receives_new_track_id(fresh_tracker):
    """Test 6: A new vehicle appearing in a later frame receives a new unique track ID."""
    b0 = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0, width=100.0, height=100.0)
    d0 = DetectionResult(class_id=2, class_name="car", confidence=0.88, bbox=b0, frame_index=0, timestamp_seconds=0.0)
    t0 = fresh_tracker.update([d0], frame_index=0, timestamp_seconds=0.0)
    first_tid = t0[0].track_id

    # Frame 1: first car continues, new car appears in distinct location
    b1_car1 = BoundingBox(x1=110.0, y1=100.0, x2=210.0, y2=200.0, width=100.0, height=100.0)
    b1_car2 = BoundingBox(x1=400.0, y1=300.0, x2=500.0, y2=400.0, width=100.0, height=100.0)
    d1_car1 = DetectionResult(class_id=2, class_name="car", confidence=0.89, bbox=b1_car1, frame_index=1, timestamp_seconds=0.2)
    d1_car2 = DetectionResult(class_id=7, class_name="truck", confidence=0.82, bbox=b1_car2, frame_index=1, timestamp_seconds=0.2)

    t1 = fresh_tracker.update([d1_car1, d1_car2], frame_index=1, timestamp_seconds=0.2)
    assert len(t1) == 2
    tids = [t.track_id for t in t1]
    assert first_tid in tids
    new_tid = [tid for tid in tids if tid != first_tid][0]
    assert new_tid > first_tid
    assert fresh_tracker.total_unique_tracks_count == 2


# --- 7. Temporary Missed Detection (Occlusion) Preserved ---
def test_temporary_missed_detection_preserves_track(fresh_tracker):
    """Test 7: A track missed for 1-2 frames is preserved in LOST state and recovered when redetected."""
    # Frame 0: Track initialized
    b0 = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0, width=100.0, height=100.0)
    d0 = DetectionResult(class_id=2, class_name="car", confidence=0.90, bbox=b0, frame_index=0, timestamp_seconds=0.0)
    t0 = fresh_tracker.update([d0], frame_index=0, timestamp_seconds=0.0)
    initial_tid = t0[0].track_id

    # Frame 1: Occlusion / missed detection (0 detections)
    t1 = fresh_tracker.update([], frame_index=1, timestamp_seconds=0.2)
    assert len(t1) == 0  # No active tracks in current frame
    assert initial_tid in fresh_tracker._tracks  # Still preserved in internal state
    assert fresh_tracker._tracks[initial_tid].state == TrackState.LOST

    # Frame 2: Vehicle reappears near predicted location
    b2 = BoundingBox(x1=105.0, y1=100.0, x2=205.0, y2=200.0, width=100.0, height=100.0)
    d2 = DetectionResult(class_id=2, class_name="car", confidence=0.92, bbox=b2, frame_index=2, timestamp_seconds=0.4)
    t2 = fresh_tracker.update([d2], frame_index=2, timestamp_seconds=0.4)

    assert len(t2) == 1
    assert t2[0].track_id == initial_tid
    assert t2[0].state == TrackState.ACTIVE
    assert fresh_tracker.total_unique_tracks_count == 1


# --- 8. Terminated Track Not Resurrected ---
def test_terminated_track_not_incorrectly_resurrected(fresh_tracker):
    """Test 8: After exceeding max_lost_frames, track terminates and new vehicle gets a fresh ID."""
    # Frame 0
    b0 = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0, width=100.0, height=100.0)
    d0 = DetectionResult(class_id=2, class_name="car", confidence=0.90, bbox=b0, frame_index=0, timestamp_seconds=0.0)
    t0 = fresh_tracker.update([d0], frame_index=0, timestamp_seconds=0.0)
    tid_1 = t0[0].track_id

    # Miss for 6 frames (max_lost_frames = 5)
    for f in range(1, 7):
        fresh_tracker.update([], frame_index=f, timestamp_seconds=f * 0.2)

    # Initial track should now be completely terminated and removed from active pool
    assert tid_1 not in fresh_tracker._tracks

    # An object appears in the same area later
    b_new = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0, width=100.0, height=100.0)
    d_new = DetectionResult(class_id=2, class_name="car", confidence=0.90, bbox=b_new, frame_index=8, timestamp_seconds=1.6)
    t_new = fresh_tracker.update([d_new], frame_index=8, timestamp_seconds=1.6)

    assert len(t_new) == 1
    assert t_new[0].track_id != tid_1
    assert t_new[0].track_id > tid_1


# --- 9. Tracking Result Schema Correctness ---
def test_tracking_result_schema():
    """Test 9: TrackedObject has all expected fields properly typed."""
    box = BoundingBox(x1=50.0, y1=50.0, x2=150.0, y2=150.0, width=100.0, height=100.0)
    obj = TrackedObject(
        track_id=1,
        class_id=2,
        class_name="car",
        confidence=0.95,
        bbox=box,
        frame_index=3,
        timestamp_seconds=0.6,
        state=TrackState.ACTIVE,
        age_frames=4,
        hits=4,
    )

    assert obj.track_id == 1
    assert obj.class_id == 2
    assert obj.class_name == "car"
    assert obj.confidence == 0.95
    assert obj.bbox.width == 100.0
    assert obj.state == TrackState.ACTIVE
    assert obj.age_frames == 4
    assert obj.hits == 4
    assert obj.center == (100.0, 100.0)


# --- 10. Nonexistent Video ID Rejected ---
def test_tracking_endpoint_invalid_video_rejected():
    """Test 10: Calling tracking endpoint with invalid video ID returns 404."""
    client = TestClient(app)
    res = client.post("/api/v1/tracking/videos/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "video_not_found"


# --- 11 & 12 & 13. End-to-End Tracking & Path Isolation ---
def test_track_video_endpoint_end_to_end(test_tracking_video):
    """Test 11, 12, 13: Full tracking pipeline on ingested video returns valid schema without path leaks."""
    client = TestClient(app)

    # Ingest video
    with open(test_tracking_video, "rb") as vf:
        upload_res = client.post(
            "/api/v1/videos/upload",
            files={"file": ("test_run_tracking.mp4", vf, "video/mp4")},
        )
    assert upload_res.status_code == 201
    video_id = upload_res.json()["id"]

    # Run tracking
    track_res = client.post(
        f"/api/v1/tracking/videos/{video_id}",
        json={"max_frames": 10, "confidence_threshold": 0.25},
    )
    assert track_res.status_code == 200
    data = track_res.json()

    # Schema & pipeline stage validation
    assert data["video_id"] == video_id
    assert data["original_filename"] == "test_run_tracking.mp4"
    assert data["pipeline_stage"] == "tracking-run"
    assert "detector_model" in data
    assert "tracker_name" in data
    assert data["total_frames_processed"] > 0
    assert isinstance(data["total_unique_tracks"], int)
    assert isinstance(data["tracks_by_class"], dict)
    assert isinstance(data["frames"], list)
    assert data["processing_time_ms"] > 0
    assert "preview_frame_base64" in data

    # Verify TrackedItem fields
    if data["frames"] and data["frames"][0]["tracked_objects"]:
        first_obj = data["frames"][0]["tracked_objects"][0]
        assert "track_id" in first_obj
        assert "class_name" in first_obj
        assert "confidence" in first_obj
        assert "bbox" in first_obj
        assert "state" in first_obj

    # Security: No filesystem paths leaked
    res_text = track_res.text
    assert "storage_path" not in data
    assert "uploads" not in res_text
    assert str(test_tracking_video) not in res_text


# --- 14. Tracker Info Endpoint ---
def test_tracker_info_endpoint():
    """Test 14: GET /api/v1/tracking/info returns active tracker metadata and lifecycle description."""
    client = TestClient(app)
    res = client.get("/api/v1/tracking/info")
    assert res.status_code == 200
    data = res.json()
    assert "tracker_name" in data
    assert "iou_threshold" in data
    assert "max_lost_frames" in data
    assert "track_lifecycle" in data
    assert "active" in data["track_lifecycle"]
    assert "terminated" in data["track_lifecycle"]
