"""
Comprehensive unit and integration test suite for Phase 5 YOLO Vehicle Detection.

Covers:
1. Detector initialization with configured model
2. Detection inference on known frame
3. DetectionResult schema correctness (all fields present, correctly typed)
4. Confidence scores within valid range [0, 1]
5. Bounding box validity (coordinates within frame dimensions, non-degenerate)
6. Vehicle class mapping correctness against model's real labels
7. Non-vehicle class filtering policy
8. Empty / blank frame handling (empty result, not an error)
9. Rejection of invalid/nonexistent video ID with 404
10. Response schema conformance for detection endpoint
11. Isolation of server-side filesystem paths (no leakage)
12. Resource bounding (max_frames enforcement)
13. Model info endpoint (/api/v1/detection/info)
"""
import io
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.v1.detection import get_detector
from app.config.settings import settings
from app.db.session import Base, engine, get_db
from app.main import app
from app.models.video import Video
from app.services.cv.detector import (
    DEFAULT_VEHICLE_CLASSES,
    BoundingBox,
    DetectionResult,
    Detector,
    YOLOVehicleDetector,
)
from app.services.cv.video_source import VideoSource


@pytest.fixture(scope="module")
def shared_detector():
    """Shared YOLOVehicleDetector instance for testing."""
    return get_detector()


@pytest.fixture(scope="module")
def sample_traffic_frame():
    """Generates a synthetic traffic frame containing simulated vehicle geometries."""
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 120
    # Draw simulated road
    cv2.rectangle(frame, (50, 100), (590, 450), (60, 60, 60), -1)
    # Draw road markings
    for y in range(120, 440, 60):
        cv2.rectangle(frame, (315, y), (325, y + 30), (255, 255, 255), -1)
    return frame


@pytest.fixture(scope="module")
def test_video_file(tmp_path_factory):
    """Creates a deterministic 1-second 640x480 test MP4 video."""
    temp_dir = tmp_path_factory.mktemp("test_videos")
    video_path = temp_dir / "test_detector_video.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 10.0
    width, height = 640, 480
    out = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

    for i in range(10):  # 10 frames = 1.0 second at 10 fps
        frame = np.ones((height, width, 3), dtype=np.uint8) * 100
        # Draw road
        cv2.rectangle(frame, (40, 80), (600, 440), (50, 50, 50), -1)
        # Moving box simulating vehicle
        x_pos = int(100 + i * 20)
        cv2.rectangle(frame, (x_pos, 200), (x_pos + 80, 300), (0, 0, 200), -1)
        out.write(frame)

    out.release()
    return video_path


# --- 1. Detector Initialization ---
def test_detector_initialization(shared_detector):
    """Test 1: Detector initializes correctly with model name, device, and confidence threshold."""
    assert isinstance(shared_detector, Detector)
    assert shared_detector.model_name.endswith(".pt") or "yolo" in shared_detector.model_name.lower()
    assert shared_detector.device in ["cpu", "cuda"]
    assert 0.0 < shared_detector.confidence_threshold < 1.0
    assert "car" in shared_detector.target_classes
    assert "bus" in shared_detector.target_classes
    assert len(shared_detector.all_model_classes) >= 5


# --- 2. Inference on Known Frame ---
def test_detector_inference_on_known_frame(shared_detector, sample_traffic_frame):
    """Test 2: Inference runs without exceptions and returns a list of DetectionResults."""
    results = shared_detector.detect(sample_traffic_frame, frame_index=0, timestamp_seconds=0.0)
    assert isinstance(results, list)
    for res in results:
        assert isinstance(res, DetectionResult)


# --- 3. Schema Correctness ---
def test_detection_result_schema(shared_detector):
    """Test 3: DetectionResult has all required attributes and types (without track_id)."""
    bbox = BoundingBox(x1=10.0, y1=20.0, x2=110.0, y2=120.0, width=100.0, height=100.0)
    result = DetectionResult(
        class_id=2,
        class_name="car",
        confidence=0.89,
        bbox=bbox,
        frame_index=1,
        timestamp_seconds=0.2,
    )

    assert result.class_id == 2
    assert result.class_name == "car"
    assert result.confidence == 0.89
    assert result.bbox.width == 100.0
    assert result.bbox.height == 100.0
    assert result.frame_index == 1
    assert result.timestamp_seconds == 0.2
    # Ensure no track_id exists in DetectionResult (Phase 5 boundary rule)
    assert not hasattr(result, "track_id")


# --- 4. Confidence Values Valid Range ---
def test_confidence_values_valid_range(shared_detector, sample_traffic_frame):
    """Test 4: Confidence scores must fall strictly within [0.0, 1.0]."""
    results = shared_detector.detect(sample_traffic_frame)
    for res in results:
        assert 0.0 <= res.confidence <= 1.0
        assert res.confidence >= shared_detector.confidence_threshold


# --- 5. Bounding Boxes Validity ---
def test_bounding_boxes_validity():
    """Test 5: Bounding box constructor clamps to frame dimensions and prevents degenerate boxes."""
    # Test valid clamp
    box = BoundingBox.from_xyxy(x1=-10, y1=-5, x2=700, y2=500, frame_width=640, frame_height=480)
    assert box.x1 == 0.0
    assert box.y1 == 0.0
    assert box.x2 == 640.0
    assert box.y2 == 480.0
    assert box.width == 640.0
    assert box.height == 480.0

    # Test coordinate ordering
    normal_box = BoundingBox.from_xyxy(x1=50.456, y1=60.123, x2=150.789, y2=200.456, frame_width=640, frame_height=480)
    assert normal_box.x1 < normal_box.x2
    assert normal_box.y1 < normal_box.y2
    assert normal_box.width > 0
    assert normal_box.height > 0


# --- 6. Vehicle Class Mapping ---
def test_vehicle_class_mapping(shared_detector):
    """Test 6: Vehicle class names map correctly to COCO labels."""
    all_classes = shared_detector.all_model_classes
    # COCO standard vehicle classes
    assert all_classes.get(2) == "car"
    assert all_classes.get(3) == "motorcycle"
    assert all_classes.get(5) == "bus"
    assert all_classes.get(7) == "truck"
    assert all_classes.get(1) == "bicycle"


# --- 7. Non-Vehicle Class Filtering Policy ---
def test_non_vehicle_class_filtering_policy():
    """Test 7: Default policy filters non-vehicle classes; custom target classes include requested ones."""
    # Detector with standard vehicle classes
    vehicle_detector = YOLOVehicleDetector(target_classes={"car", "bus", "truck"})
    assert "person" not in vehicle_detector.target_classes
    assert "car" in vehicle_detector.target_classes

    # Detector with all classes allowed
    all_detector = YOLOVehicleDetector(target_classes=set(vehicle_detector.all_model_classes.values()))
    assert "person" in all_detector.target_classes
    assert "traffic light" in all_detector.target_classes


# --- 8. Empty / Blank Frame Handling ---
def test_empty_blank_frame_handled_safely(shared_detector):
    """Test 8: Solid black image produces empty detection list without crashing."""
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = shared_detector.detect(blank_frame)
    assert isinstance(results, list)
    assert len(results) == 0


# --- 9. Invalid Video ID Rejected ---
def test_detect_endpoint_invalid_video_rejected():
    """Test 9: Calling detect endpoint with invalid/nonexistent video ID returns 404."""
    client = TestClient(app)
    res = client.post("/api/v1/detection/videos/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "video_not_found"


# --- 10 & 11. Response Schema & No Leaked Paths ---
def test_detect_endpoint_success_schema_and_path_isolation(test_video_file):
    """Test 10 & 11: End-to-end detection on ingested video returns valid schema without server paths."""
    client = TestClient(app)

    # Ingest video via upload endpoint first
    with open(test_video_file, "rb") as vf:
        upload_res = client.post(
            "/api/v1/videos/upload",
            files={"file": ("test_run_detector.mp4", vf, "video/mp4")},
        )
    assert upload_res.status_code == 201
    video_id = upload_res.json()["id"]

    # Run detection
    detect_res = client.post(
        f"/api/v1/detection/videos/{video_id}",
        json={"max_frames": 5, "confidence_threshold": 0.25},
    )
    assert detect_res.status_code == 200
    data = detect_res.json()

    # Validate response schema
    assert data["video_id"] == video_id
    assert data["original_filename"] == "test_run_detector.mp4"
    assert data["pipeline_stage"] == "detections-run"
    assert data["total_frames_processed"] > 0
    assert isinstance(data["total_detections_count"], int)
    assert isinstance(data["detections_by_class"], dict)
    assert isinstance(data["frames"], list)
    assert data["processing_time_ms"] > 0
    assert "preview_frame_base64" in data

    # Security check: Ensure storage path is NOT leaked
    res_text = detect_res.text
    assert "storage_path" not in data
    assert "uploads" not in res_text
    assert str(test_video_file) not in res_text


# --- 12. Bounded Frames Enforcement ---
def test_detect_endpoint_bounded_frames(test_video_file):
    """Test 12: max_frames parameter bounds frame processing count."""
    client = TestClient(app)

    with open(test_video_file, "rb") as vf:
        upload_res = client.post(
            "/api/v1/videos/upload",
            files={"file": ("test_bounds.mp4", vf, "video/mp4")},
        )
    video_id = upload_res.json()["id"]

    # Request with max_frames = 2
    detect_res = client.post(
        f"/api/v1/detection/videos/{video_id}",
        json={"max_frames": 2},
    )
    assert detect_res.status_code == 200
    data = detect_res.json()
    assert data["total_frames_processed"] <= 2


# --- 13. Model Info Endpoint ---
def test_model_info_endpoint():
    """Test 13: GET /api/v1/detection/info returns active model metadata."""
    client = TestClient(app)
    res = client.get("/api/v1/detection/info")
    assert res.status_code == 200
    data = res.json()
    assert "model_name" in data
    assert "device" in data
    assert "confidence_threshold" in data
    assert "target_classes" in data
    assert "supported_classes" in data
    assert isinstance(data["target_classes"], list)
