"""
Unit and Integration Tests for Phase 8: Traffic Analytics & Flow Metrics Engine.

Verifies:
1. Zero vehicles counted -> 0 flow rate, safe 0.0% class/direction distributions, no zero-division.
2. Single vehicle counted -> exact mathematical flow rates (N / T_obs).
3. Multi-vehicle class distribution -> exact counts and percentages summing to 100.0%.
4. Directional distribution -> exact inbound vs outbound counts and percentages.
5. Observation duration < 3600s -> clearly labeled is_extrapolated = True.
6. Observation duration >= 3600s -> is_extrapolated = False.
7. Division-by-zero protection when observation duration is zero or frames = 0.
8. Non-interpolated time-series volume bucketing partitions crossing events accurately.
9. Time-series bucketing with boundary timestamps (exact edge placement).
10. Time-series bucketing caps max buckets to 500 to prevent unbounded memory usage.
11. Analytics schema validation and server storage path isolation.
12. GET /api/v1/analytics/info returns definitions and data honesty policy.
13. POST /api/v1/analytics/videos/{nonexistent_id} returns a clean 404.
14. POST /api/v1/analytics/videos/{id} end-to-end integration test with synthetic video.
15. POST /api/v1/videos/{id}/analytics shortcut endpoint integration test.
"""
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.v1.analytics import get_analytics_engine
from app.main import app
from app.schemas.analytics import (
    AnalyticsInfoResponse,
    AnalyticsRequest,
    ClassMetricItem,
    DirectionMetricItem,
    TimeSeriesBucketSchema,
    TrafficMetricsResponse,
)
from app.schemas.counting import CountingLineSchema, Point2DSchema
from app.services.cv.traffic_metrics_engine import (
    ClassMetric,
    DirectionMetric,
    TimeSeriesBucket,
    TrafficMetricsEngine,
    TrafficMetricsResult,
)
from app.services.cv.vehicle_counter import (
    CountingLine,
    CrossingEvent,
    Point2D,
    VideoCountingOutput,
)


def create_mock_counting_output(
    total_counted: int = 0,
    counts_by_class: Dict[str, int] = None,
    counts_by_direction: Dict[str, int] = None,
    crossing_events: List[CrossingEvent] = None,
    total_frames: int = 100,
    total_detections: int = 0,
    unique_tracks: int = 0,
    line_label: str = "main_tripwire",
) -> VideoCountingOutput:
    """Helper to create a VideoCountingOutput for testing."""
    line = CountingLine(
        p1=Point2D(x=0.0, y=0.5),
        p2=Point2D(x=1.0, y=0.5),
        label=line_label,
    )
    return VideoCountingOutput(
        video_id="mock-video-id",
        original_filename="mock_video.mp4",
        counting_line=line,
        total_frames_processed=total_frames,
        total_detections_count=total_detections,
        total_unique_tracks=unique_tracks,
        total_counted_vehicles=total_counted,
        counts_by_class=counts_by_class or {},
        counts_by_direction=counts_by_direction or {"inbound": 0, "outbound": 0},
        counted_track_ids=list(range(1, total_counted + 1)),
        crossing_events=crossing_events or [],
        frames=[],
        processing_time_ms=10.0,
    )


# ---------------------------------------------------------------------------
# Unit Tests: TrafficMetricsEngine Mathematics
# ---------------------------------------------------------------------------


def test_metrics_engine_zero_vehicles():
    """Engine computes zero counts and safe 0.0% distributions with zero vehicles."""
    engine = TrafficMetricsEngine()
    counting_output = create_mock_counting_output(
        total_counted=0,
        counts_by_class={},
        counts_by_direction={"inbound": 0, "outbound": 0},
        crossing_events=[],
        total_frames=100,
    )
    result = engine.compute_metrics(
        counting_output=counting_output,
        observation_duration_seconds=10.0,
        time_bucket_seconds=5.0,
    )

    assert result.total_vehicles == 0
    assert result.observation_duration_seconds == 10.0
    assert result.flow_rate_per_minute == 0.0
    assert result.flow_rate_per_hour_extrapolated == 0.0
    assert result.is_extrapolated is True
    assert result.inbound_count == 0
    assert result.outbound_count == 0
    assert result.inbound_percentage == 0.0
    assert result.outbound_percentage == 0.0
    assert result.class_distribution == []
    assert len(result.time_series) == 2  # [0-5s), [5-10s)
    assert all(b.vehicle_count == 0 for b in result.time_series)


def test_metrics_engine_single_vehicle_math():
    """
    Verifies exact flow rate arithmetic for 1 vehicle in a 10s observation window.
    Flow rate / min = 1 / (10 / 60) = 6.0 veh/min
    Flow rate / hr = 1 / (10 / 3600) = 360.0 veh/hr (extrapolated)
    """
    engine = TrafficMetricsEngine()
    event = CrossingEvent(
        track_id=1,
        class_name="car",
        frame_index=25,
        timestamp_seconds=2.5,
        direction="inbound",
        crossing_point=(320.0, 240.0),
        line_label="main_tripwire",
    )

    counting_output = create_mock_counting_output(
        total_counted=1,
        counts_by_class={"car": 1},
        counts_by_direction={"inbound": 1, "outbound": 0},
        crossing_events=[event],
        total_frames=100,
        total_detections=10,
        unique_tracks=1,
    )

    result = engine.compute_metrics(
        counting_output=counting_output,
        observation_duration_seconds=10.0,
        time_bucket_seconds=5.0,
    )

    assert result.total_vehicles == 1
    assert result.observation_duration_seconds == 10.0
    assert pytest.approx(result.flow_rate_per_minute, rel=1e-4) == 6.0
    assert pytest.approx(result.flow_rate_per_hour_extrapolated, rel=1e-4) == 360.0
    assert result.is_extrapolated is True
    assert result.inbound_count == 1
    assert result.outbound_count == 0
    assert pytest.approx(result.inbound_percentage, rel=1e-4) == 100.0
    assert pytest.approx(result.outbound_percentage, rel=1e-4) == 0.0

    assert len(result.class_distribution) == 1
    assert result.class_distribution[0].class_name == "car"
    assert result.class_distribution[0].count == 1
    assert pytest.approx(result.class_distribution[0].percentage, rel=1e-4) == 100.0


def test_metrics_engine_multiple_vehicles_class_distribution():
    """
    Verifies class percentages and directional distributions across 10 vehicles:
    5 cars (50%), 3 trucks (30%), 2 buses (20%).
    7 inbound (70%), 3 outbound (30%).
    Observation duration: 60 seconds (1 minute).
    Flow rate / min = 10 / 1.0 = 10.0 veh/min
    Flow rate / hr = 10 / (60 / 3600) = 600.0 veh/hr (extrapolated)
    """
    engine = TrafficMetricsEngine()
    events: List[CrossingEvent] = []

    # 5 Cars (all inbound)
    for i in range(1, 6):
        events.append(
            CrossingEvent(
                track_id=i,
                class_name="car",
                frame_index=i * 10,
                timestamp_seconds=float(i * 2),
                direction="inbound",
                crossing_point=(320.0, 240.0),
                line_label="line1",
            )
        )

    # 3 Trucks (2 inbound, 1 outbound)
    for i, dir_name in enumerate(["inbound", "inbound", "outbound"], start=6):
        events.append(
            CrossingEvent(
                track_id=i,
                class_name="truck",
                frame_index=i * 10,
                timestamp_seconds=float(i * 3),
                direction=dir_name,
                crossing_point=(320.0, 240.0),
                line_label="line1",
            )
        )

    # 2 Buses (all outbound)
    for i in range(9, 11):
        events.append(
            CrossingEvent(
                track_id=i,
                class_name="bus",
                frame_index=i * 10,
                timestamp_seconds=float(i * 4),
                direction="outbound",
                crossing_point=(320.0, 240.0),
                line_label="line1",
            )
        )

    counting_output = create_mock_counting_output(
        total_counted=10,
        counts_by_class={"car": 5, "truck": 3, "bus": 2},
        counts_by_direction={"inbound": 7, "outbound": 3},
        crossing_events=events,
        total_frames=600,
        total_detections=120,
        unique_tracks=10,
        line_label="line1",
    )

    result = engine.compute_metrics(
        counting_output=counting_output,
        observation_duration_seconds=60.0,
        time_bucket_seconds=10.0,
    )

    assert result.total_vehicles == 10
    assert pytest.approx(result.flow_rate_per_minute, rel=1e-4) == 10.0
    assert pytest.approx(result.flow_rate_per_hour_extrapolated, rel=1e-4) == 600.0
    assert result.is_extrapolated is True

    # Check Class Breakdown
    class_map = {item.class_name: item for item in result.class_distribution}
    assert class_map["car"].count == 5
    assert pytest.approx(class_map["car"].percentage, rel=1e-4) == 50.0

    assert class_map["truck"].count == 3
    assert pytest.approx(class_map["truck"].percentage, rel=1e-4) == 30.0

    assert class_map["bus"].count == 2
    assert pytest.approx(class_map["bus"].percentage, rel=1e-4) == 20.0

    total_pct = sum(item.percentage for item in result.class_distribution)
    assert pytest.approx(total_pct, rel=1e-4) == 100.0

    # Check Direction Breakdown
    assert result.inbound_count == 7
    assert result.outbound_count == 3
    assert pytest.approx(result.inbound_percentage, rel=1e-4) == 70.0
    assert pytest.approx(result.outbound_percentage, rel=1e-4) == 30.0


def test_extrapolation_flagging_threshold():
    """
    Observation duration < 3600s must set is_extrapolated = True.
    Observation duration >= 3600s must set is_extrapolated = False.
    """
    engine = TrafficMetricsEngine()

    # Case A: 3599 seconds -> Extrapolated
    out_a = create_mock_counting_output(total_counted=0, total_frames=35990)
    res_a = engine.compute_metrics(
        counting_output=out_a,
        observation_duration_seconds=3599.0,
    )
    assert res_a.is_extrapolated is True

    # Case B: 3600 seconds -> Measured, not extrapolated
    out_b = create_mock_counting_output(total_counted=0, total_frames=36000)
    res_b = engine.compute_metrics(
        counting_output=out_b,
        observation_duration_seconds=3600.0,
    )
    assert res_b.is_extrapolated is False


def test_division_by_zero_prevention():
    """Observation duration of 0 seconds handles safely without ZeroDivisionError."""
    engine = TrafficMetricsEngine()
    out = create_mock_counting_output(total_counted=0, total_frames=0)
    result = engine.compute_metrics(
        counting_output=out,
        observation_duration_seconds=0.0,
    )
    assert result.flow_rate_per_minute == 0.0
    assert result.flow_rate_per_hour_extrapolated == 0.0
    assert result.observation_duration_seconds == 0.0


def test_time_series_bucketing_discrete_bins():
    """
    Verifies time-series bucketing into discrete non-interpolated bins.
    Events at t = 1.0s, 3.5s (Bucket 0: [0, 5s)), t = 6.2s (Bucket 1: [5, 10s)), t = 12.0s (Bucket 2: [10, 15s)).
    """
    engine = TrafficMetricsEngine()
    events = [
        CrossingEvent(track_id=1, class_name="car", frame_index=10, timestamp_seconds=1.0, direction="inbound", crossing_point=(0, 0), line_label="l"),
        CrossingEvent(track_id=2, class_name="truck", frame_index=35, timestamp_seconds=3.5, direction="outbound", crossing_point=(0, 0), line_label="l"),
        CrossingEvent(track_id=3, class_name="car", frame_index=62, timestamp_seconds=6.2, direction="inbound", crossing_point=(0, 0), line_label="l"),
        CrossingEvent(track_id=4, class_name="motorcycle", frame_index=120, timestamp_seconds=12.0, direction="inbound", crossing_point=(0, 0), line_label="l"),
    ]

    buckets = engine.generate_time_series_buckets(
        crossing_events=events,
        total_duration_seconds=15.0,
        bucket_seconds=5.0,
    )

    assert len(buckets) == 3
    # Bucket 0: [0.0, 5.0)
    assert buckets[0].bucket_index == 0
    assert buckets[0].start_time_seconds == 0.0
    assert buckets[0].end_time_seconds == 5.0
    assert buckets[0].vehicle_count == 2
    assert buckets[0].class_counts == {"car": 1, "truck": 1}
    assert buckets[0].inbound_count == 1
    assert buckets[0].outbound_count == 1

    # Bucket 1: [5.0, 10.0)
    assert buckets[1].bucket_index == 1
    assert buckets[1].start_time_seconds == 5.0
    assert buckets[1].end_time_seconds == 10.0
    assert buckets[1].vehicle_count == 1
    assert buckets[1].class_counts == {"car": 1}
    assert buckets[1].inbound_count == 1
    assert buckets[1].outbound_count == 0

    # Bucket 2: [10.0, 15.0)
    assert buckets[2].bucket_index == 2
    assert buckets[2].start_time_seconds == 10.0
    assert buckets[2].end_time_seconds == 15.0
    assert buckets[2].vehicle_count == 1
    assert buckets[2].class_counts == {"motorcycle": 1}
    assert buckets[2].inbound_count == 1
    assert buckets[2].outbound_count == 0

    total_in_buckets = sum(b.vehicle_count for b in buckets)
    assert total_in_buckets == len(events) == 4


def test_time_series_boundary_timestamps():
    """Event occurring exactly at bucket boundary t=5.0 falls into bucket [5.0, 10.0)."""
    engine = TrafficMetricsEngine()
    event_edge = CrossingEvent(
        track_id=1,
        class_name="car",
        frame_index=50,
        timestamp_seconds=5.0,
        direction="inbound",
        crossing_point=(0, 0),
        line_label="l",
    )

    buckets = engine.generate_time_series_buckets(
        crossing_events=[event_edge],
        total_duration_seconds=10.0,
        bucket_seconds=5.0,
    )

    assert len(buckets) == 2
    assert buckets[0].vehicle_count == 0
    assert buckets[1].vehicle_count == 1
    assert buckets[1].start_time_seconds == 5.0


def test_time_series_max_bucket_cap():
    """Engine caps maximum buckets to prevent memory exhaustion on long durations with small Δt."""
    engine = TrafficMetricsEngine()
    # 10,000 seconds with 1-second buckets would create 10,000 buckets; cap is 500
    buckets = engine.generate_time_series_buckets(
        crossing_events=[],
        total_duration_seconds=10000.0,
        bucket_seconds=1.0,
    )
    assert len(buckets) <= 500


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------


def test_analytics_info_endpoint():
    """GET /api/v1/analytics/info returns mathematical formulas and data honesty policy."""
    with TestClient(app) as client:
        response = client.get("/api/v1/analytics/info")
        assert response.status_code == 200
        data = response.json()
        assert data["engine_name"] == "TrafficMetricsEngine"
        assert "metric_definitions" in data
        assert "flow_rate_per_minute" in data["metric_definitions"]
        assert "flow_rate_per_hour_extrapolated" in data["metric_definitions"]
        assert "extrapolation_policy" in data


def test_analytics_endpoint_nonexistent_video_404():
    """POST /api/v1/analytics/videos/{nonexistent_id} returns a clean 404."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analytics/videos/00000000-0000-0000-0000-000000000000",
            json={"max_frames": 10},
        )
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "video_not_found"


def test_analytics_video_endpoint_end_to_end(tmp_path: Path):
    """
    End-to-end integration test:
    1. Create synthetic video with a moving rectangular object crossing the middle line.
    2. Upload video via /api/v1/videos/upload.
    3. Call POST /api/v1/analytics/videos/{video_id}.
    4. Verify structured TrafficMetricsResponse, mathematically defined metrics, and storage path isolation.
    """
    # 1. Create synthetic video file
    video_path = tmp_path / "test_analytics_clip.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (320, 240))

    # Draw moving rectangular object crossing the middle line (y = 120)
    for frame_i in range(15):
        frame = np.full((240, 320, 3), 35, dtype=np.uint8)
        # Vehicle moving downward: y from 60 to 180 (crosses y=120 around frame 7)
        cy = int(60 + frame_i * 8)
        cx = 160
        cv2.rectangle(frame, (cx - 20, cy - 15), (cx + 20, cy + 15), (220, 220, 220), -1)
        out.write(frame)
    out.release()

    with TestClient(app) as client:
        # 2. Upload video
        with open(video_path, "rb") as f:
            upload_res = client.post(
                "/api/v1/videos/upload",
                files={"file": ("test_analytics_clip.mp4", f, "video/mp4")},
            )
        assert upload_res.status_code == 201
        video_id = upload_res.json()["id"]

        # 3. Call analytics endpoint
        analytics_res = client.post(
            f"/api/v1/analytics/videos/{video_id}",
            json={
                "max_frames": 15,
                "confidence_threshold": 0.2,
                "time_bucket_seconds": 2.0,
                "counting_line": {
                    "p1": {"x": 0.0, "y": 0.5},
                    "p2": {"x": 1.0, "y": 0.5},
                    "label": "mid_line",
                    "direction_a_to_b": "inbound",
                    "direction_b_to_a": "outbound",
                    "min_movement_px": 2.0,
                },
            },
        )
        assert analytics_res.status_code == 200
        data = analytics_res.json()

        # 4. Verify structured response properties
        assert data["video_id"] == video_id
        assert data["pipeline_stage"] == "analytics-run"
        assert data["total_frames_processed"] > 0
        assert data["observation_duration_seconds"] > 0.0
        assert isinstance(data["total_vehicles"], int)
        assert isinstance(data["flow_rate_per_minute"], float)
        assert isinstance(data["flow_rate_per_hour_extrapolated"], float)
        assert isinstance(data["is_extrapolated"], bool)
        assert "class_distribution" in data
        assert "directional_distribution" in data
        assert "time_series" in data
        assert isinstance(data["time_series"], list)
        assert data["counting_line_label"] == "mid_line"

        # 5. Verify security: Storage path is NOT exposed
        payload_str = str(data)
        assert "uploads" not in payload_str
        assert str(video_path) not in payload_str


def test_videos_analytics_shortcut_endpoint(tmp_path: Path):
    """
    Verifies shortcut POST /api/v1/videos/{video_id}/analytics returns equivalent response.
    """
    video_path = tmp_path / "test_shortcut_clip.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (320, 240))
    for _ in range(10):
        frame = np.full((240, 320, 3), 40, dtype=np.uint8)
        out.write(frame)
    out.release()

    with TestClient(app) as client:
        with open(video_path, "rb") as f:
            upload_res = client.post(
                "/api/v1/videos/upload",
                files={"file": ("test_shortcut_clip.mp4", f, "video/mp4")},
            )
        assert upload_res.status_code == 201
        video_id = upload_res.json()["id"]

        shortcut_res = client.post(
            f"/api/v1/videos/{video_id}/analytics",
            json={"max_frames": 10},
        )
        assert shortcut_res.status_code == 200
        data = shortcut_res.json()
        assert data["video_id"] == video_id
        assert data["pipeline_stage"] == "analytics-run"
