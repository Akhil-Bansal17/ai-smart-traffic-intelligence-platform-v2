"""
Unit and Integration Tests for Phase 7: Vehicle Counting Engine.

Verifies:
1. One object crosses the line -> count 1
2. An object that never crosses -> count 0
3. The same track ID crossing near line across multiple frames -> counted exactly once
4. Multiple distinct vehicles -> distinct, correct counts
5. Per-class counts are correct
6. Direction is correctly detected (inbound vs outbound)
7. Reverse-direction crossing is handled cleanly (no duplicate count)
8. Arbitrarily-oriented line is handled correctly (not just horizontal)
9. Track starting near/on line does not misfire
10. Temporarily-missing track resumes and counts on genuine crossing
11. Terminated track does not get miscounted
12. Duplicate-track-ID protection holds under adversarial synthetic input
13. Counting result schema validation and storage path isolation
14. Count endpoint invalid video ID rejected cleanly (404)
15. Count video endpoint end-to-end integration test
16. Counting info endpoint returns configuration
"""
import io
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.v1.counting import get_counter
from app.api.v1.detection import get_detector
from app.api.v1.tracking import get_tracker
from app.config.settings import settings
from app.main import app
from app.models.video import Video
from app.schemas.counting import (
    CountingInfoResponse,
    CountingLineSchema,
    CountingRequest,
    Point2DSchema,
    VideoCountingResponse,
)
from app.services.cv.detector import BoundingBox, DetectionResult, YOLOVehicleDetector
from app.services.cv.tracker import ByteTrackVehicleTracker, TrackedObject, TrackState
from app.services.cv.vehicle_counter import (
    CountingLine,
    CrossingEvent,
    LineCrossingCounter,
    Point2D,
    VideoCountingOutput,
)
from app.services.cv.video_source import VideoSource


def create_mock_tracked_object(
    track_id: int,
    class_id: int = 2,
    class_name: str = "car",
    cx: float = 640.0,
    cy: float = 200.0,
    width: float = 60.0,
    height: float = 40.0,
    state: TrackState = TrackState.ACTIVE,
) -> TrackedObject:
    """Helper to create a synthetic TrackedObject at a given centroid."""
    bbox = BoundingBox.from_xyxy(
        x1=cx - width / 2.0,
        y1=cy - height / 2.0,
        x2=cx + width / 2.0,
        y2=cy + height / 2.0,
        frame_width=1280,
        frame_height=720,
    )
    return TrackedObject(
        track_id=track_id,
        class_id=class_id,
        class_name=class_name,
        confidence=0.88,
        bbox=bbox,
        state=state,
        age_frames=1,
        hits=1,
        trajectory=[(cx, cy)],
    )


# ---------------------------------------------------------------------------
# Unit Tests: LineCrossingCounter
# ---------------------------------------------------------------------------


def test_counter_initialization():
    """Counter initializes with default line, zero counts, and empty history."""
    counter = LineCrossingCounter()
    assert counter.total_count == 0
    assert len(counter.counted_track_ids) == 0
    assert len(counter.crossing_events) == 0
    assert counter.line.direction_a_to_b == "inbound"
    assert counter.line.direction_b_to_a == "outbound"


def test_single_vehicle_crosses_line_counts_one():
    """One vehicle crossing from top (Side A) to bottom (Side B) triggers exactly 1 count."""
    # Line at y = 0.5 (y = 360 in 720p frame)
    line = CountingLine(
        p1=Point2D(x=0.0, y=0.5),
        p2=Point2D(x=1.0, y=0.5),
        label="center_line",
    )
    counter = LineCrossingCounter(line=line)

    # Frame 1: Vehicle above line (cy = 300)
    obj_f1 = create_mock_tracked_object(track_id=1, cx=640, cy=300)
    events_f1 = counter.update([obj_f1], frame_index=0, timestamp_seconds=0.0, frame_width=1280, frame_height=720)
    assert len(events_f1) == 0
    assert counter.total_count == 0

    # Frame 2: Vehicle crosses below line (cy = 420)
    obj_f2 = create_mock_tracked_object(track_id=1, cx=640, cy=420)
    events_f2 = counter.update([obj_f2], frame_index=1, timestamp_seconds=0.2, frame_width=1280, frame_height=720)

    assert len(events_f2) == 1
    assert events_f2[0].track_id == 1
    assert events_f2[0].class_name == "car"
    assert events_f2[0].direction == "inbound"
    assert counter.total_count == 1
    assert counter.counted_track_ids == [1]
    assert counter.counts_by_class == {"car": 1}
    assert counter.counts_by_direction == {"inbound": 1, "outbound": 0}


def test_vehicle_never_crosses_line_counts_zero():
    """Vehicle moving around on one side of the line produces 0 counts."""
    line = CountingLine(p1=Point2D(x=0.0, y=0.5), p2=Point2D(x=1.0, y=0.5))
    counter = LineCrossingCounter(line=line)

    for i in range(10):
        # Always above line (cy from 100 to 250)
        obj = create_mock_tracked_object(track_id=1, cx=640 + i * 5, cy=100 + i * 15)
        events = counter.update([obj], frame_index=i, timestamp_seconds=i * 0.2, frame_width=1280, frame_height=720)
        assert len(events) == 0

    assert counter.total_count == 0
    assert len(counter.counted_track_ids) == 0


def test_duplicate_counting_prevention_same_track_multiple_frames():
    """Same track ID crossing and moving near the line for 10 frames is counted strictly once."""
    line = CountingLine(p1=Point2D(x=0.0, y=0.5), p2=Point2D(x=1.0, y=0.5))
    counter = LineCrossingCounter(line=line)

    # Frame 0: above line
    counter.update([create_mock_tracked_object(1, cy=300)], frame_index=0, timestamp_seconds=0.0)
    # Frame 1: crosses below line -> Count = 1
    events1 = counter.update([create_mock_tracked_object(1, cy=400)], frame_index=1, timestamp_seconds=0.2)
    assert len(events1) == 1
    assert counter.total_count == 1

    # Frames 2-10: Vehicle continues moving below line
    for f in range(2, 10):
        evts = counter.update([create_mock_tracked_object(1, cy=400 + f * 10)], frame_index=f, timestamp_seconds=f * 0.2)
        assert len(evts) == 0
        assert counter.total_count == 1

    assert counter.total_count == 1
    assert len(counter.crossing_events) == 1


def test_multiple_distinct_vehicles_counted_correctly():
    """Multiple tracks crossing independently are all counted accurately."""
    line = CountingLine(p1=Point2D(x=0.0, y=0.5), p2=Point2D(x=1.0, y=0.5))
    counter = LineCrossingCounter(line=line)

    # Frame 0: Track 1 and Track 2 above line
    counter.update(
        [
            create_mock_tracked_object(track_id=1, cx=400, cy=250),
            create_mock_tracked_object(track_id=2, cx=800, cy=280),
        ],
        frame_index=0,
        timestamp_seconds=0.0,
    )

    # Frame 1: Track 1 crosses, Track 2 moves closer
    events_f1 = counter.update(
        [
            create_mock_tracked_object(track_id=1, cx=400, cy=420),
            create_mock_tracked_object(track_id=2, cx=800, cy=340),
        ],
        frame_index=1,
        timestamp_seconds=0.2,
    )
    assert len(events_f1) == 1
    assert events_f1[0].track_id == 1
    assert counter.total_count == 1

    # Frame 2: Track 2 crosses, Track 3 appears above line
    events_f2 = counter.update(
        [
            create_mock_tracked_object(track_id=1, cx=400, cy=480),
            create_mock_tracked_object(track_id=2, cx=800, cy=410),
            create_mock_tracked_object(track_id=3, cx=600, cy=200),
        ],
        frame_index=2,
        timestamp_seconds=0.4,
    )
    assert len(events_f2) == 1
    assert events_f2[0].track_id == 2
    assert counter.total_count == 2
    assert counter.counted_track_ids == [1, 2]


def test_per_class_counts_breakdown():
    """Accurately tallies counts partitioned by vehicle class."""
    line = CountingLine(p1=Point2D(x=0.0, y=0.5), p2=Point2D(x=1.0, y=0.5))
    counter = LineCrossingCounter(line=line)

    # Initial frame above line
    counter.update(
        [
            create_mock_tracked_object(track_id=1, class_name="car", cy=200),
            create_mock_tracked_object(track_id=2, class_name="truck", cy=200),
            create_mock_tracked_object(track_id=3, class_name="bus", cy=200),
            create_mock_tracked_object(track_id=4, class_name="motorcycle", cy=200),
            create_mock_tracked_object(track_id=5, class_name="car", cy=200),
        ],
        frame_index=0,
        timestamp_seconds=0.0,
    )

    # All vehicles cross below line
    events = counter.update(
        [
            create_mock_tracked_object(track_id=1, class_name="car", cy=450),
            create_mock_tracked_object(track_id=2, class_name="truck", cy=450),
            create_mock_tracked_object(track_id=3, class_name="bus", cy=450),
            create_mock_tracked_object(track_id=4, class_name="motorcycle", cy=450),
            create_mock_tracked_object(track_id=5, class_name="car", cy=450),
        ],
        frame_index=1,
        timestamp_seconds=0.2,
    )

    assert len(events) == 5
    assert counter.total_count == 5
    assert counter.counts_by_class == {
        "car": 2,
        "truck": 1,
        "bus": 1,
        "motorcycle": 1,
    }


def test_direction_detection_inbound_vs_outbound():
    """Correctly assigns 'inbound' (A->B) and 'outbound' (B->A) directions."""
    line = CountingLine(
        p1=Point2D(x=0.0, y=0.5),
        p2=Point2D(x=1.0, y=0.5),
        direction_a_to_b="inbound",
        direction_b_to_a="outbound",
    )
    counter = LineCrossingCounter(line=line)

    # Track 1 is above (Side A: cy = 200), Track 2 is below (Side B: cy = 500)
    counter.update(
        [
            create_mock_tracked_object(track_id=1, cy=200),
            create_mock_tracked_object(track_id=2, cy=500),
        ],
        frame_index=0,
        timestamp_seconds=0.0,
    )

    # Track 1 moves down to Side B (inbound), Track 2 moves up to Side A (outbound)
    events = counter.update(
        [
            create_mock_tracked_object(track_id=1, cy=500),
            create_mock_tracked_object(track_id=2, cy=200),
        ],
        frame_index=1,
        timestamp_seconds=0.2,
    )

    assert len(events) == 2
    evt1 = next(e for e in events if e.track_id == 1)
    evt2 = next(e for e in events if e.track_id == 2)
    assert evt1.direction == "inbound"
    assert evt2.direction == "outbound"
    assert counter.counts_by_direction == {"inbound": 1, "outbound": 1}


def test_reverse_direction_crossing_handled_cleanly():
    """A vehicle that crosses once and then reverses direction is counted strictly once."""
    line = CountingLine(p1=Point2D(x=0.0, y=0.5), p2=Point2D(x=1.0, y=0.5))
    counter = LineCrossingCounter(line=line)

    # 1. Start above line
    counter.update([create_mock_tracked_object(1, cy=200)], frame_index=0, timestamp_seconds=0.0)
    # 2. Cross below line (Counted = 1)
    evts1 = counter.update([create_mock_tracked_object(1, cy=450)], frame_index=1, timestamp_seconds=0.2)
    assert len(evts1) == 1
    assert counter.total_count == 1

    # 3. Vehicle reverses and crosses back above line
    evts2 = counter.update([create_mock_tracked_object(1, cy=200)], frame_index=2, timestamp_seconds=0.4)
    assert len(evts2) == 0  # No second count!
    assert counter.total_count == 1
    assert len(counter.crossing_events) == 1


def test_arbitrarily_oriented_counting_line():
    """Handles diagonal and non-horizontal counting lines accurately via cross product."""
    # Diagonal line from top-left (0,0) to bottom-right (1,1)
    line = CountingLine(
        p1=Point2D(x=0.0, y=0.0),
        p2=Point2D(x=1.0, y=1.0),
        label="diagonal_tripwire",
        direction_a_to_b="south_east",
        direction_b_to_a="north_west",
    )
    counter = LineCrossingCounter(line=line)

    # Frame 0: Point at top-right (x=1000, y=200) -> on Side B (cp < 0)
    counter.update([create_mock_tracked_object(1, cx=1000, cy=200)], frame_index=0, timestamp_seconds=0.0)

    # Frame 1: Point at bottom-left (x=200, y=600) -> on Side A (cp > 0)
    events = counter.update([create_mock_tracked_object(1, cx=200, cy=600)], frame_index=1, timestamp_seconds=0.2)

    assert len(events) == 1
    assert events[0].track_id == 1
    assert events[0].direction == "south_east"
    assert counter.total_count == 1


def test_track_starting_near_or_on_line_does_not_misfire():
    """Track initialized directly on or near the line without significant crossing movement does not trigger count."""
    line = CountingLine(p1=Point2D(x=0.0, y=0.5), p2=Point2D(x=1.0, y=0.5))
    counter = LineCrossingCounter(line=line)

    # Track appears exactly on the line (cy = 360 in 720p)
    evts0 = counter.update([create_mock_tracked_object(1, cy=360)], frame_index=0, timestamp_seconds=0.0)
    assert len(evts0) == 0

    # Slight jitter of 0.5px (below min_movement_px)
    evts1 = counter.update([create_mock_tracked_object(1, cy=360.5)], frame_index=1, timestamp_seconds=0.2)
    assert len(evts1) == 0
    assert counter.total_count == 0


def test_temporarily_lost_track_resumes_and_counts():
    """A track that goes LOST and reappears before crossing triggers count upon genuine crossing."""
    line = CountingLine(p1=Point2D(x=0.0, y=0.5), p2=Point2D(x=1.0, y=0.5))
    counter = LineCrossingCounter(line=line)

    # Frame 0: Active above line
    counter.update([create_mock_tracked_object(1, cy=200, state=TrackState.ACTIVE)], frame_index=0, timestamp_seconds=0.0)

    # Frame 1-2: Track is LOST (missed detection), but still remembered
    counter.update([create_mock_tracked_object(1, cy=280, state=TrackState.LOST)], frame_index=1, timestamp_seconds=0.2)

    # Frame 3: Track returns ACTIVE and crosses below line (cy = 450)
    events = counter.update([create_mock_tracked_object(1, cy=450, state=TrackState.ACTIVE)], frame_index=3, timestamp_seconds=0.6)

    assert len(events) == 1
    assert events[0].track_id == 1
    assert counter.total_count == 1


def test_terminated_track_not_miscounted():
    """A terminated track that disappears before crossing produces 0 counts."""
    line = CountingLine(p1=Point2D(x=0.0, y=0.5), p2=Point2D(x=1.0, y=0.5))
    counter = LineCrossingCounter(line=line)

    # Frame 0: Active above line
    counter.update([create_mock_tracked_object(1, cy=200)], frame_index=0, timestamp_seconds=0.0)
    # Track terminates / deleted from stream
    counter.update([], frame_index=1, timestamp_seconds=0.2)

    assert counter.total_count == 0


def test_adversarial_duplicate_track_id_protection():
    """Adversarial input feeding duplicate track IDs never produces duplicate counts."""
    line = CountingLine(p1=Point2D(x=0.0, y=0.5), p2=Point2D(x=1.0, y=0.5))
    counter = LineCrossingCounter(line=line)

    counter.update([create_mock_tracked_object(1, cy=200)], frame_index=0, timestamp_seconds=0.0)
    counter.update([create_mock_tracked_object(1, cy=450)], frame_index=1, timestamp_seconds=0.2)
    assert counter.total_count == 1

    # Inject duplicate objects with same track_id in the same and subsequent frames
    for _ in range(5):
        counter.update([create_mock_tracked_object(1, cy=460), create_mock_tracked_object(1, cy=200)], frame_index=2, timestamp_seconds=0.4)

    assert counter.total_count == 1
    assert len(counter.crossing_events) == 1


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------


def test_counting_info_endpoint():
    """GET /api/v1/counting/info returns algorithm metadata and default line geometry."""
    with TestClient(app) as client:
        response = client.get("/api/v1/counting/info")
        assert response.status_code == 200
        data = response.json()
        assert data["counter_name"] == "LineCrossingCounter"
        assert "default_line" in data
        assert data["default_line"]["label"] == "main_tripwire"
        assert "crossing_semantics" in data


def test_count_endpoint_invalid_video_rejected():
    """POST /api/v1/counting/videos/{nonexistent_id} returns a clean 404."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/counting/videos/00000000-0000-0000-0000-000000000000",
            json={"max_frames": 10},
        )
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "video_not_found"


def test_count_video_endpoint_end_to_end(tmp_path: Path):
    """
    End-to-end integration test: Upload a synthetic video, run counting endpoint,
    and verify structured response schema and path isolation.
    """
    # 1. Create synthetic video file
    video_path = tmp_path / "test_count_clip.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (320, 240))

    # Draw moving rectangular object crossing the middle line (y = 120)
    for frame_i in range(15):
        frame = np.full((240, 320, 3), 40, dtype=np.uint8)
        # Vehicle moving downward: y from 60 to 180 (crosses y=120 around frame 7)
        cy = int(60 + frame_i * 8)
        cx = 160
        cv2.rectangle(frame, (cx - 20, cy - 15), (cx + 20, cy + 15), (200, 200, 200), -1)
        out.write(frame)
    out.release()

    with TestClient(app) as client:
        # 2. Upload video
        with open(video_path, "rb") as f:
            upload_res = client.post(
                "/api/v1/videos/upload",
                files={"file": ("test_count_clip.mp4", f, "video/mp4")},
            )
        assert upload_res.status_code == 201
        video_id = upload_res.json()["id"]

        # 3. Call counting endpoint
        count_res = client.post(
            f"/api/v1/counting/videos/{video_id}",
            json={
                "max_frames": 15,
                "confidence_threshold": 0.2,
                "counting_line": {
                    "p1": {"x": 0.0, "y": 0.5},
                    "p2": {"x": 1.0, "y": 0.5},
                    "label": "test_line",
                    "direction_a_to_b": "inbound",
                    "direction_b_to_a": "outbound",
                    "min_movement_px": 2.0,
                },
            },
        )
        assert count_res.status_code == 200
        data = count_res.json()

        # 4. Verify structured response properties
        assert data["video_id"] == video_id
        assert data["pipeline_stage"] == "counting-run"
        assert data["total_frames_processed"] > 0
        assert "counts_by_class" in data
        assert "counts_by_direction" in data
        assert "crossing_events" in data
        assert "frames" in data
        assert isinstance(data["total_counted_vehicles"], int)

        # 5. Verify security: Storage path is NOT exposed
        payload_str = str(data)
        assert "uploads" not in payload_str
        assert str(video_path) not in payload_str
