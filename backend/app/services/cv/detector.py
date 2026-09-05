"""
Detector interface and YOLO vehicle detection implementation.

Architecture:
    VideoSource (Phase 4) -> Frame -> Detector interface -> YOLOVehicleDetector -> Detection results

Strict Phase 5 boundaries:
- Vehicle detection and classification only.
- NO tracking (track_id is explicitly omitted; tracking begins in Phase 6).
- Centralized class mapping from real model labels.
- Policy-driven filtering of non-vehicle classes.
"""
import base64
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import cv2
import numpy as np
from ultralytics import YOLO

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.services.cv.video_source import VideoSource

logger = get_logger(__name__)

# Standard traffic vehicle classes present in COCO dataset
DEFAULT_VEHICLE_CLASSES: Set[str] = {
    "car",
    "motorcycle",
    "bus",
    "truck",
    "bicycle",
}


@dataclass(frozen=True)
class BoundingBox:
    """Bounding box in absolute pixel coordinates [x1, y1, x2, y2]."""
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    height: float

    @classmethod
    def from_xyxy(cls, x1: float, y1: float, x2: float, y2: float, frame_width: int, frame_height: int) -> "BoundingBox":
        """Constructs a validated, clamped bounding box within frame dimensions."""
        clamped_x1 = max(0.0, min(float(x1), float(frame_width)))
        clamped_y1 = max(0.0, min(float(y1), float(frame_height)))
        clamped_x2 = max(0.0, min(float(x2), float(frame_width)))
        clamped_y2 = max(0.0, min(float(y2), float(frame_height)))

        # Ensure non-negative dimensions
        width = max(0.0, clamped_x2 - clamped_x1)
        height = max(0.0, clamped_y2 - clamped_y1)

        return cls(
            x1=round(clamped_x1, 2),
            y1=round(clamped_y1, 2),
            x2=round(clamped_x2, 2),
            y2=round(clamped_y2, 2),
            width=round(width, 2),
            height=round(height, 2),
        )


@dataclass(frozen=True)
class DetectionResult:
    """
    Single object detection result.
    Explicitly carries NO tracking ID (track_id is Phase 6).
    """
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
    frame_index: Optional[int] = None
    timestamp_seconds: Optional[float] = None


@dataclass
class FrameDetections:
    """Detections for a single video frame."""
    frame_index: int
    timestamp_seconds: float
    detections: List[DetectionResult] = field(default_factory=list)

    @property
    def vehicle_count(self) -> int:
        return len(self.detections)


@dataclass
class VideoDetectionOutput:
    """Aggregated detection results across all processed video frames."""
    total_frames_processed: int
    total_detections_count: int
    detections_by_class: Dict[str, int]
    frames: List[FrameDetections]
    processing_time_ms: float
    annotated_preview_base64: Optional[str] = None


class Detector(ABC):
    """
    Abstract Detector interface.
    Enables swapping underlying models (YOLOv8, YOLOv10, RT-DETR, custom models)
    without modifying API or analytics consumers.
    """

    @abstractmethod
    def detect(
        self,
        frame: np.ndarray,
        frame_index: Optional[int] = None,
        timestamp_seconds: Optional[float] = None,
    ) -> List[DetectionResult]:
        """Runs object detection on a single frame."""
        pass

    @abstractmethod
    def detect_video(
        self,
        video_source: VideoSource,
        max_frames: Optional[int] = None,
        target_fps: Optional[int] = None,
    ) -> VideoDetectionOutput:
        """Runs detection sequentially on frames from a VideoSource."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name / identifier of the active model."""
        pass

    @property
    @abstractmethod
    def confidence_threshold(self) -> float:
        """Minimum confidence threshold for filtering."""
        pass

    @property
    @abstractmethod
    def device(self) -> str:
        """Inference device (cpu / cuda)."""
        pass

    @property
    @abstractmethod
    def target_classes(self) -> Set[str]:
        """Vehicle classes considered for traffic detection."""
        pass


class YOLOVehicleDetector(Detector):
    """
    Ultralytics YOLO implementation of the Detector interface.
    Specialized for vehicle detection in traffic footage.
    """

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        confidence_threshold: Optional[float] = None,
        device: Optional[str] = None,
        imgsz: Optional[int] = None,
        target_classes: Optional[Set[str]] = None,
    ):
        self._model_path_str = str(model_path) if model_path else settings.yolo_model_path
        self._confidence_threshold = (
            float(confidence_threshold)
            if confidence_threshold is not None
            else settings.default_confidence_threshold
        )
        self._device = device if device else getattr(settings, "yolo_device", "cpu")
        self._imgsz = imgsz if imgsz else getattr(settings, "yolo_imgsz", 640)
        self._target_classes = target_classes if target_classes is not None else set(DEFAULT_VEHICLE_CLASSES)

        self._model: Optional[YOLO] = None
        self._class_names: Dict[int, str] = {}
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Loads and initializes the YOLO model."""
        try:
            # Check if model path exists locally; if not and it's a standard name like yolov8n.pt, load it directly
            path_obj = Path(self._model_path_str)
            if path_obj.exists():
                self._model = YOLO(str(path_obj.resolve()))
            else:
                self._model = YOLO(self._model_path_str)

            # Read class names directly from model's internal metadata
            self._class_names = {int(k): str(v) for k, v in self._model.names.items()}
            logger.info(
                "YOLOVehicleDetector initialized with model '%s' on device '%s' (confidence: %.2f)",
                self._model_path_str,
                self._device,
                self._confidence_threshold,
            )
        except Exception as err:
            logger.error("Failed to initialize YOLO model '%s': %s", self._model_path_str, err)
            raise AppException(
                f"Failed to load detection model: {err}",
                code="model_load_failed",
                status_code=500,
            )

    @property
    def model_name(self) -> str:
        return Path(self._model_path_str).name

    @property
    def confidence_threshold(self) -> float:
        return self._confidence_threshold

    @property
    def device(self) -> str:
        return self._device

    @property
    def target_classes(self) -> Set[str]:
        return self._target_classes

    @property
    def all_model_classes(self) -> Dict[int, str]:
        """All classes supported natively by the underlying model."""
        return self._class_names

    def detect(
        self,
        frame: np.ndarray,
        frame_index: Optional[int] = None,
        timestamp_seconds: Optional[float] = None,
    ) -> List[DetectionResult]:
        """
        Executes YOLO inference on a single numpy image frame (BGR format).
        Returns filtered list of DetectionResult objects.
        """
        if frame is None or frame.size == 0:
            return []

        frame_height, frame_width = frame.shape[:2]

        try:
            results = self._model.predict(
                source=frame,
                conf=self._confidence_threshold,
                device=self._device,
                imgsz=self._imgsz,
                verbose=False,
            )
        except Exception as err:
            logger.error("Inference failed for frame %s: %s", frame_index, err)
            raise AppException(f"Frame inference error: {err}", code="inference_error", status_code=500)

        detections: List[DetectionResult] = []

        if not results:
            return detections

        first_res = results[0]
        if first_res.boxes is None or len(first_res.boxes) == 0:
            return detections

        for box in first_res.boxes:
            cls_id = int(box.cls[0].item())
            class_name = self._class_names.get(cls_id, f"class_{cls_id}")
            confidence = float(box.conf[0].item())

            # Policy: Filter for target traffic classes (e.g. car, motorcycle, bus, truck, bicycle)
            if self._target_classes and class_name not in self._target_classes:
                continue

            xyxy = box.xyxy[0].tolist()
            bbox = BoundingBox.from_xyxy(
                x1=xyxy[0],
                y1=xyxy[1],
                x2=xyxy[2],
                y2=xyxy[3],
                frame_width=frame_width,
                frame_height=frame_height,
            )

            # Discard degenerate bounding boxes
            if bbox.width <= 0 or bbox.height <= 0:
                continue

            detections.append(
                DetectionResult(
                    class_id=cls_id,
                    class_name=class_name,
                    confidence=round(confidence, 4),
                    bbox=bbox,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                )
            )

        return detections

    def detect_video(
        self,
        video_source: VideoSource,
        max_frames: Optional[int] = None,
        target_fps: Optional[int] = None,
    ) -> VideoDetectionOutput:
        """
        Runs frame-by-frame detection across frames yielded by VideoSource.
        Bounded by max_frames to ensure controlled resource consumption.
        """
        start_time = time.perf_counter()

        frame_results: List[FrameDetections] = []
        detections_by_class: Dict[str, int] = {cls: 0 for cls in sorted(self._target_classes)}
        total_detections = 0
        preview_frame_b64: Optional[str] = None
        preview_captured = False

        effective_max_frames = max_frames if max_frames is not None else 50
        # Hard cap to prevent CPU exhaustion
        effective_max_frames = min(effective_max_frames, 300)

        for frame_idx, timestamp_sec, frame in video_source.extract_frames(
            target_fps=target_fps,
            max_frames=effective_max_frames,
        ):
            detections = self.detect(
                frame=frame,
                frame_index=frame_idx,
                timestamp_seconds=timestamp_sec,
            )

            frame_result = FrameDetections(
                frame_index=frame_idx,
                timestamp_seconds=timestamp_sec,
                detections=detections,
            )
            frame_results.append(frame_result)

            for d in detections:
                detections_by_class[d.class_name] = detections_by_class.get(d.class_name, 0) + 1
                total_detections += 1

            # Capture the first frame with detections (or the first frame) as an annotated visual preview
            if not preview_captured and (detections or frame_idx == 0):
                preview_frame_b64 = self._generate_annotated_preview(frame, detections)
                preview_captured = True

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return VideoDetectionOutput(
            total_frames_processed=len(frame_results),
            total_detections_count=total_detections,
            detections_by_class=detections_by_class,
            frames=frame_results,
            processing_time_ms=elapsed_ms,
            annotated_preview_base64=preview_frame_b64,
        )

    def _generate_annotated_preview(
        self,
        frame: np.ndarray,
        detections: List[DetectionResult],
    ) -> str:
        """Renders bounding boxes and class/confidence labels onto a frame copy and encodes to base64 JPEG."""
        preview = frame.copy()

        # Class colors (BGR format)
        palette = {
            "car": (255, 128, 0),       # Cyan-ish blue
            "truck": (0, 165, 255),     # Orange
            "bus": (0, 255, 128),       # Light green
            "motorcycle": (255, 0, 255), # Magenta
            "bicycle": (0, 255, 255),   # Yellow
        }

        for det in detections:
            bbox = det.bbox
            color = palette.get(det.class_name, (0, 255, 0))
            x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)

            # Draw bounding box
            cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)

            # Draw label banner
            label = f"{det.class_name} {det.confidence:.2f}"
            (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(
                preview,
                (x1, max(0, y1 - text_h - 6)),
                (x1 + text_w + 4, max(text_h + 6, y1)),
                color,
                -1,
            )
            cv2.putText(
                preview,
                label,
                (x1 + 2, max(text_h + 2, y1 - 3)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        # Resize if overly large to keep payload lightweight (max width 800)
        h, w = preview.shape[:2]
        if w > 800:
            scale = 800 / w
            preview = cv2.resize(preview, (800, int(h * scale)), interpolation=cv2.INTER_AREA)

        ret, buffer = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            return ""
        return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
