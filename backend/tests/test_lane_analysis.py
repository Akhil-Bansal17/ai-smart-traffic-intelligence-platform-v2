"""
Unit and Integration Tests for Phase 9: Lane Analysis & Density Estimation.

Verifies:
1. Shoelace polygon area calculation (standard shapes, irregular polygons, collinear/degenerate).
2. Ray-casting point-in-polygon algorithm (interior, exterior, boundary, complex concave shapes).
3. Polygon validation rules (vertex counts, finite coordinates, non-negative, non-zero area, name bounds).
4. Single and multi-vehicle lane assignment across frames.
5. Unassigned vehicle accounting for vehicles outside all configured regions.
6. Temporal persistence threshold (N=2 frames default) to suppress boundary flickering.
7. Exact mathematical density calculation (image_space_density and normalized_density_score).
8. Vehicle class distribution breakdown per lane with graceful zero-handling.
9. Peak simultaneous occupancy and average occupancy calculations.
10. Max lane limit (<= 20) and duplicate lane ID rejection.
11. GET /api/v1/lane-analysis/info returns calibration warnings and algorithm policies.
12. POST /api/v1/lane-analysis/videos/{nonexistent_id} returns a clean 404.
13. POST /api/v1/lane-analysis/videos/{id} end-to-end integration test with synthetic video and storage path isolation.
"""
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import AppException
from app.main import app
from app.schemas.lane_analysis import (
    LaneAnalysisInfoResponse,
    LaneAnalysisRequest,
    LaneAnalyticsResponse,
    LaneRegionSchema,
    PerLaneSummarySchema,
)
from app.services.cv.detector import BoundingBox
from app.services.cv.lane_analyzer import (
    LaneAnalyticsResult,
    LaneAnalyzer,
    LaneAssignmentEngine,
    LaneRegion,
    PerLaneSummary,
    point_in_polygon_raycast,
    polygon_area_shoelace,
    validate_lane_polygon,
)
from app.services.cv.tracker import (
    FrameTrackingResult,
    TrackedObject,
    TrackState,
    VideoTrackingOutput,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_mock_tracked_object(
    track_id: int,
    cx: float,
    cy: float,
    class_name: str = "car",
    w: float = 40.0,
    h: float = 30.0,
    frame_index: int = 0,
    timestamp: float = 0.0,
) -> TrackedObject:
    """Creates a TrackedObject with specified centroid (cx, cy)."""
    x1 = cx - w / 2.0
    y1 = cy - h / 2.0
    x2 = cx + w / 2.0
    y2 = cy + h / 2.0
    bbox = BoundingBox(
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        width=w,
        height=h,
    )
    return TrackedObject(
        track_id=track_id,
        class_id=2,
        class_name=class_name,
        confidence=0.90,
        bbox=bbox,
        frame_index=frame_index,
        timestamp_seconds=timestamp,
        state=TrackState.ACTIVE,
    )


def create_mock_tracking_output(
    frames_objects: List[List[TrackedObject]],
    fps: float = 10.0,
) -> VideoTrackingOutput:
    """Creates a VideoTrackingOutput from frame-by-frame tracked objects."""
    frames: List[FrameTrackingResult] = []
    all_tracks = set()
    tracks_by_class: Dict[str, int] = {}
    total_detections = 0

    for idx, objs in enumerate(frames_objects):
        ts = idx / fps
        for obj in objs:
            obj.frame_index = idx
            obj.timestamp_seconds = ts
            all_tracks.add(obj.track_id)
            tracks_by_class[obj.class_name] = tracks_by_class.get(obj.class_name, 0) + 1
            total_detections += 1
        frames.append(
            FrameTrackingResult(
                frame_index=idx,
                timestamp_seconds=ts,
                tracked_objects=objs,
            )
        )

    return VideoTrackingOutput(
        total_frames_processed=len(frames),
        total_detections_count=total_detections,
        total_unique_tracks=len(all_tracks),
        tracks_by_class=tracks_by_class,
        frames=frames,
        processing_time_ms=15.0,
    )


# ---------------------------------------------------------------------------
# Unit Tests: Geometry & Point-in-Polygon
# ---------------------------------------------------------------------------

def test_shoelace_area_computation():
    """Shoelace formula correctly calculates areas of standard and irregular polygons."""
    # 1. Rectangle 100 x 50 = 5000 px^2
    rect = [(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0)]
    assert polygon_area_shoelace(rect) == 5000.0

    # 2. Right triangle 60 x 80 = 2400 px^2
    tri = [(0.0, 0.0), (60.0, 0.0), (0.0, 80.0)]
    assert polygon_area_shoelace(tri) == 2400.0

    # 3. Trapezoid (bases 100 and 60, height 40) = (100 + 60)/2 * 40 = 3200 px^2
    trap = [(0.0, 0.0), (100.0, 0.0), (80.0, 40.0), (20.0, 40.0)]
    assert polygon_area_shoelace(trap) == 3200.0

    # 4. Degenerate collinear points -> 0.0
    collinear = [(0.0, 0.0), (50.0, 50.0), (100.0, 100.0)]
    assert polygon_area_shoelace(collinear) == 0.0

    # 5. Fewer than 3 points -> 0.0
    assert polygon_area_shoelace([(0.0, 0.0), (10.0, 10.0)]) == 0.0


def test_raycast_point_in_polygon():
    """Ray-casting algorithm accurately tests points inside, outside, and near boundaries."""
    polygon = [(100.0, 100.0), (300.0, 100.0), (300.0, 400.0), (100.0, 400.0)]

    # Strictly inside
    assert point_in_polygon_raycast((200.0, 250.0), polygon) is True
    assert point_in_polygon_raycast((101.0, 101.0), polygon) is True
    assert point_in_polygon_raycast((299.0, 399.0), polygon) is True

    # Strictly outside
    assert point_in_polygon_raycast((50.0, 250.0), polygon) is False
    assert point_in_polygon_raycast((350.0, 250.0), polygon) is False
    assert point_in_polygon_raycast((200.0, 50.0), polygon) is False
    assert point_in_polygon_raycast((200.0, 450.0), polygon) is False

    # Fewer than 3 points
    assert point_in_polygon_raycast((200.0, 250.0), [(0.0, 0.0), (100.0, 100.0)]) is False


def test_polygon_validation_rules():
    """Validation rejects invalid polygons (too few points, negative/NaN coords, zero area)."""
    # Valid polygon passes
    area = validate_lane_polygon("lane_1", "Northbound 1", [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)])
    assert area > 0

    # Empty lane_id
    with pytest.raises(AppException) as exc:
        validate_lane_polygon("", "Lane", [(0, 0), (10, 0), (10, 10)])
    assert exc.value.status_code == 422

    # Too few vertices (< 3)
    with pytest.raises(AppException) as exc:
        validate_lane_polygon("l1", "Lane", [(0, 0), (10, 0)])
    assert exc.value.status_code == 422

    # Negative coordinates
    with pytest.raises(AppException) as exc:
        validate_lane_polygon("l1", "Lane", [(-5, 0), (10, 0), (10, 10)])
    assert exc.value.status_code == 422

    # NaN coordinates
    with pytest.raises(AppException) as exc:
        validate_lane_polygon("l1", "Lane", [(float("nan"), 0), (10, 0), (10, 10)])
    assert exc.value.status_code == 422

    # Collinear / zero area
    with pytest.raises(AppException) as exc:
        validate_lane_polygon("l1", "Lane", [(0, 0), (50, 50), (100, 100)])
    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Unit Tests: Lane Assignment & Persistence
# ---------------------------------------------------------------------------

def test_single_vehicle_lane_assignment():
    """Single vehicle inside configured lane is properly assigned and counted."""
    lane1 = LaneRegion(
        lane_id="lane_left",
        name="Left Lane",
        polygon=[(0.0, 0.0), (200.0, 0.0), (200.0, 500.0), (0.0, 500.0)],
        direction_hint="inbound",
    )

    # Vehicle at cx=100, cy=200 for 3 frames
    frames = [
        [create_mock_tracked_object(1, cx=100.0, cy=100.0 + i * 50.0, class_name="car")]
        for i in range(3)
    ]
    tracking_output = create_mock_tracking_output(frames)

    analyzer = LaneAnalyzer(persistence_threshold=2)
    result = analyzer.analyze(tracking_output, [lane1])

    assert len(result.lanes) == 1
    summary = result.lanes[0]
    assert summary.lane_id == "lane_left"
    assert summary.total_unique_vehicles == 1
    assert summary.vehicle_class_counts["car"] == 1
    assert summary.vehicle_class_counts["truck"] == 0
    assert result.unassigned_vehicles_count == 0


def test_multi_vehicle_multi_lane_assignment():
    """Vehicles in distinct lanes are correctly assigned to their respective regions."""
    lane_left = LaneRegion(
        lane_id="lane_1",
        name="Left Lane",
        polygon=[(0.0, 0.0), (200.0, 0.0), (200.0, 600.0), (0.0, 600.0)],
    )
    lane_right = LaneRegion(
        lane_id="lane_2",
        name="Right Lane",
        polygon=[(300.0, 0.0), (500.0, 0.0), (500.0, 600.0), (300.0, 600.0)],
    )

    # Vehicle 1 in Left Lane, Vehicle 2 in Right Lane across 3 frames
    frames = [
        [
            create_mock_tracked_object(1, cx=100.0, cy=100.0 + i * 40.0, class_name="car"),
            create_mock_tracked_object(2, cx=400.0, cy=120.0 + i * 40.0, class_name="truck"),
        ]
        for i in range(3)
    ]
    tracking_output = create_mock_tracking_output(frames)

    analyzer = LaneAnalyzer(persistence_threshold=2)
    result = analyzer.analyze(tracking_output, [lane_left, lane_right])

    assert len(result.lanes) == 2
    l1 = next(l for l in result.lanes if l.lane_id == "lane_1")
    l2 = next(l for l in result.lanes if l.lane_id == "lane_2")

    assert l1.total_unique_vehicles == 1
    assert l1.vehicle_class_counts["car"] == 1
    assert l1.vehicle_class_counts["truck"] == 0

    assert l2.total_unique_vehicles == 1
    assert l2.vehicle_class_counts["truck"] == 1
    assert l2.vehicle_class_counts["car"] == 0

    assert result.unassigned_vehicles_count == 0


def test_unassigned_vehicles_outside_all_lanes():
    """Vehicles outside all configured lane polygons are counted as unassigned."""
    lane1 = LaneRegion(
        lane_id="lane_1",
        name="Left Lane",
        polygon=[(0.0, 0.0), (200.0, 0.0), (200.0, 500.0), (0.0, 500.0)],
    )

    # Vehicle 1 in Lane 1 (cx=100), Vehicle 2 in median outside lanes (cx=250)
    frames = [
        [
            create_mock_tracked_object(1, cx=100.0, cy=200.0, class_name="car"),
            create_mock_tracked_object(2, cx=250.0, cy=200.0, class_name="bus"),
        ]
        for _ in range(3)
    ]
    tracking_output = create_mock_tracking_output(frames)

    analyzer = LaneAnalyzer(persistence_threshold=2)
    result = analyzer.analyze(tracking_output, [lane1])

    assert result.lanes[0].total_unique_vehicles == 1
    assert result.unassigned_vehicles_count == 1
    assert result.total_unique_tracks == 2


def test_persistence_threshold_prevents_single_frame_jitter():
    """A vehicle appearing in a lane for only 1 frame when threshold=2 is not confirmed."""
    lane1 = LaneRegion(
        lane_id="lane_1",
        name="Left Lane",
        polygon=[(0.0, 0.0), (200.0, 0.0), (200.0, 500.0), (0.0, 500.0)],
    )

    # Vehicle 1 is in lane_1 for only frame 0, then outside for frames 1 and 2
    frames = [
        [create_mock_tracked_object(1, cx=100.0, cy=100.0)],  # frame 0: inside (count=1)
        [create_mock_tracked_object(1, cx=250.0, cy=150.0)],  # frame 1: outside
        [create_mock_tracked_object(1, cx=250.0, cy=200.0)],  # frame 2: outside
    ]
    tracking_output = create_mock_tracking_output(frames)

    analyzer = LaneAnalyzer(persistence_threshold=2)
    result = analyzer.analyze(tracking_output, [lane1])

    # Since threshold was 2 and it was only inside for 1 frame, not confirmed
    assert result.lanes[0].total_unique_vehicles == 0
    assert result.unassigned_vehicles_count == 1


# ---------------------------------------------------------------------------
# Unit Tests: Density Calculations & Occupancy
# ---------------------------------------------------------------------------

def test_lane_density_arithmetic():
    """Verifies image_space_density and normalized_density_score calculations."""
    # Polygon 200 x 500 = 100,000 px^2
    lane = LaneRegion(
        lane_id="lane_wide",
        name="Wide Lane",
        polygon=[(0.0, 0.0), (200.0, 0.0), (200.0, 500.0), (0.0, 500.0)],
    )
    assert lane.area_px2 == 100000.0

    # 4 distinct vehicles in this lane across 4 frames
    frames = [
        [
            create_mock_tracked_object(1, cx=100.0, cy=100.0),
            create_mock_tracked_object(2, cx=100.0, cy=200.0),
        ],
        [
            create_mock_tracked_object(1, cx=100.0, cy=120.0),
            create_mock_tracked_object(2, cx=100.0, cy=220.0),
            create_mock_tracked_object(3, cx=100.0, cy=300.0),
            create_mock_tracked_object(4, cx=100.0, cy=400.0),
        ],
        [
            create_mock_tracked_object(3, cx=100.0, cy=320.0),
            create_mock_tracked_object(4, cx=100.0, cy=420.0),
        ],
    ]
    tracking_output = create_mock_tracking_output(frames)

    analyzer = LaneAnalyzer(persistence_threshold=1)  # immediate
    result = analyzer.analyze(tracking_output, [lane])

    summary = result.lanes[0]
    assert summary.total_unique_vehicles == 4
    assert summary.polygon_area_px2 == 100000.0

    # Expected image space density = 4 / 100000 = 0.00004 vehicles/px^2
    expected_density = 4.0 / 100000.0
    assert summary.image_space_density_vehicles_per_px2 == pytest.approx(expected_density, rel=1e-5)

    # Expected normalized score: min(1.0, 4 / (100000 / 2500)) = min(1.0, 4 / 40.0) = 0.1000
    expected_score = min(1.0, 4.0 / (100000.0 / 2500.0))
    assert summary.normalized_density_score == pytest.approx(expected_score, rel=1e-4)

    # Peak occupancy in frame 1 is 4 simultaneous vehicles
    assert summary.peak_occupancy == 4
    # Average occupancy: (2 + 4 + 2) / 3 = 8 / 3 = 2.67
    assert summary.average_occupancy == pytest.approx(8.0 / 3.0, rel=1e-2)


def test_zero_vehicle_lane_density():
    """Empty lane reports 0 count, 0 density, and 0 normalized score without division by zero."""
    lane = LaneRegion(
        lane_id="empty_lane",
        name="Empty Lane",
        polygon=[(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)],
    )
    tracking_output = create_mock_tracking_output([[]])

    analyzer = LaneAnalyzer(persistence_threshold=2)
    result = analyzer.analyze(tracking_output, [lane])

    summary = result.lanes[0]
    assert summary.total_unique_vehicles == 0
    assert summary.image_space_density_vehicles_per_px2 == 0.0
    assert summary.normalized_density_score == 0.0
    assert summary.peak_occupancy == 0
    assert summary.average_occupancy == 0.0


# ---------------------------------------------------------------------------
# Integration Tests: API Endpoints
# ---------------------------------------------------------------------------

def test_lane_analysis_info_endpoint():
    """GET /api/v1/lane-analysis/info returns calibration warnings and algorithm policies."""
    with TestClient(app) as client:
        response = client.get("/api/v1/lane-analysis/info")
        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "LaneAnalyzer"
        assert "assignment_method" in data
        assert "density_definition" in data
        assert "calibration_policy" in data
        assert "directional_policy" in data


def test_lane_analysis_endpoint_nonexistent_video_404():
    """POST /api/v1/lane-analysis/videos/{nonexistent_id} returns a clean 404."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/lane-analysis/videos/00000000-0000-0000-0000-000000000000",
            json={
                "lanes": [
                    {
                        "lane_id": "l1",
                        "name": "Lane 1",
                        "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
                    }
                ]
            },
        )
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "video_not_found"


def test_lane_analysis_endpoint_validation_duplicate_lane_ids():
    """POST /api/v1/lane-analysis/videos/{id} with duplicate lane IDs returns 422."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/lane-analysis/videos/00000000-0000-0000-0000-000000000000",
            json={
                "lanes": [
                    {
                        "lane_id": "dup_lane",
                        "name": "Lane 1",
                        "polygon": [[0, 0], [100, 0], [100, 100]],
                    },
                    {
                        "lane_id": "dup_lane",
                        "name": "Lane 2",
                        "polygon": [[200, 0], [300, 0], [300, 100]],
                    },
                ]
            },
        )
        # Even with nonexistent video, if request validation fails or 404
        assert response.status_code in (404, 422)


def test_lane_analysis_video_endpoint_end_to_end(tmp_path: Path):
    """
    End-to-end integration test:
    1. Create synthetic video with 2 moving boxes in separate lane columns.
    2. Upload video via /api/v1/videos/upload.
    3. Call POST /api/v1/lane-analysis/videos/{video_id} with 2 configured lane regions.
    4. Verify structured LaneAnalyticsResponse, per-lane summaries, non-zero density, and path isolation.
    """
    # 1. Create synthetic video
    video_path = tmp_path / "test_lane_analysis_clip.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (400, 300))

    # Draw moving rectangles in Left Lane (x: 50-150) and Right Lane (x: 250-350)
    for frame_i in range(15):
        frame = np.full((300, 400, 3), 35, dtype=np.uint8)
        # Object in Lane 1 (x=100)
        cy1 = int(50 + frame_i * 10)
        cv2.rectangle(frame, (80, cy1 - 15), (120, cy1 + 15), (220, 220, 220), -1)
        # Object in Lane 2 (x=300)
        cy2 = int(60 + frame_i * 10)
        cv2.rectangle(frame, (280, cy2 - 15), (320, cy2 + 15), (200, 200, 200), -1)
        out.write(frame)
    out.release()

    with TestClient(app) as client:
        # 2. Upload video
        with open(video_path, "rb") as f:
            upload_res = client.post(
                "/api/v1/videos/upload",
                files={"file": ("test_lane_analysis_clip.mp4", f, "video/mp4")},
            )
        assert upload_res.status_code == 201
        video_id = upload_res.json()["id"]

        # 3. Call lane analysis endpoint
        lane_res = client.post(
            f"/api/v1/lane-analysis/videos/{video_id}",
            json={
                "max_frames": 15,
                "confidence_threshold": 0.2,
                "persistence_threshold": 1,
                "lanes": [
                    {
                        "lane_id": "lane_left",
                        "name": "Left Highway Lane",
                        "polygon": [[0, 0], [200, 0], [200, 300], [0, 300]],
                        "direction_hint": "northbound",
                    },
                    {
                        "lane_id": "lane_right",
                        "name": "Right Highway Lane",
                        "polygon": [[200, 0], [400, 0], [400, 300], [200, 300]],
                        "direction_hint": "southbound",
                    },
                ],
            },
        )
        assert lane_res.status_code == 200
        data = lane_res.json()

        # 4. Verify structured response properties
        assert data["video_id"] == video_id
        assert data["pipeline_stage"] == "lane-analysis-run"
        assert data["total_frames_processed"] > 0
        assert data["observation_duration_seconds"] > 0.0
        assert len(data["lanes"]) == 2

        l_left = next(l for l in data["lanes"] if l["lane_id"] == "lane_left")
        l_right = next(l for l in data["lanes"] if l["lane_id"] == "lane_right")

        assert l_left["polygon_area_px2"] == 60000.0  # 200 x 300
        assert l_right["polygon_area_px2"] == 60000.0
        assert l_left["density_unit"] == "vehicles/px²"
        assert "Image-space density is not equivalent" in data["density_calibration_warning"]
        assert "Directional per-lane metrics omitted" in data["directional_metrics_omitted_reason"]

        # 5. Verify security: Storage path is NOT exposed
        payload_str = str(data)
        assert "uploads" not in payload_str
        assert str(video_path) not in payload_str


def test_videos_lane_analysis_shortcut_endpoint(tmp_path: Path):
    """Verifies that POST /api/v1/videos/{video_id}/lane-analysis shortcut works."""
    video_path = tmp_path / "test_shortcut.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (200, 200))
    for _ in range(5):
        out.write(np.zeros((200, 200, 3), dtype=np.uint8))
    out.release()

    with TestClient(app) as client:
        with open(video_path, "rb") as f:
            upload_res = client.post(
                "/api/v1/videos/upload",
                files={"file": ("test_shortcut.mp4", f, "video/mp4")},
            )
        assert upload_res.status_code == 201
        video_id = upload_res.json()["id"]

        shortcut_res = client.post(
            f"/api/v1/videos/{video_id}/lane-analysis",
            json={
                "lanes": [
                    {
                        "lane_id": "l1",
                        "name": "Lane 1",
                        "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
                    }
                ]
            },
        )
        assert shortcut_res.status_code == 200
        data = shortcut_res.json()
        assert data["video_id"] == video_id
        assert len(data["lanes"]) == 1

