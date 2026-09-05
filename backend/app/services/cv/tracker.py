"""
Tracker interface and ByteTrack-style Kalman/IoU multi-object tracking implementation.

Architecture:
    VideoSource -> Detector -> DetectionResult -> Tracker -> TrackingResult

Strict Phase 6 boundaries:
- Object tracking and persistent track ID assignment across frames.
- Consumes DetectionResults from Phase 5 (never calls YOLO directly).
- Explicit track lifecycle state machine: NEW -> ACTIVE -> LOST -> TERMINATED.
- NO counting (vehicle counting is Phase 7).
- NO lane assignment (Phase 8) or traffic metrics (Phase 9).
"""
import base64
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.services.cv.detector import BoundingBox, DetectionResult, Detector
from app.services.cv.video_source import VideoSource

logger = get_logger(__name__)


class TrackState(str, Enum):
    """Lifecycle states of a tracked object."""
    NEW = "new"              # Just initialized in current frame
    ACTIVE = "active"        # Actively matched and confirmed
    LOST = "lost"            # Missed in current frame (within max_lost_frames tolerance)
    TERMINATED = "terminated"# Inactive for > max_lost_frames; identity retired


def compute_iou(box1: Tuple[float, float, float, float], box2: Tuple[float, float, float, float]) -> float:
    """Computes Intersection over Union (IoU) between two [x1, y1, x2, y2] bounding boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0.0 else 0.0


class KalmanBoxTracker:
    """
    Linear Kalman filter tracking 2D bounding box state [cx, cy, s, r, vx, vy, vs, vr]:
    - (cx, cy): Box center position
    - s: Box scale (area = width * height)
    - r: Aspect ratio (width / height)
    - (vx, vy, vs, vr): State velocities
    """

    def __init__(self, bbox: BoundingBox):
        # 8 state variables, 4 measurement variables (cx, cy, s, r)
        self.kf = cv2.KalmanFilter(8, 4)
        self.kf.measurementMatrix = np.array(
            [
                [1, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, 0, 0, 0, 0],
            ],
            dtype=np.float32,
        )

        # Transition matrix assuming constant velocity motion
        self.kf.transitionMatrix = np.array(
            [
                [1, 0, 0, 0, 1, 0, 0, 0],
                [0, 1, 0, 0, 0, 1, 0, 0],
                [0, 0, 1, 0, 0, 0, 1, 0],
                [0, 0, 0, 1, 0, 0, 0, 1],
                [0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 0, 0, 1],
            ],
            dtype=np.float32,
        )

        self.kf.processNoiseCov = np.eye(8, dtype=np.float32) * 1e-2
        self.kf.processNoiseCov[4:, 4:] *= 5.0
        self.kf.measurementNoiseCov = np.eye(4, dtype=np.float32) * 1e-1
        self.kf.errorCovPost = np.eye(8, dtype=np.float32) * 1.0

        # Initialize state with measured box
        z = self._convert_bbox_to_z(bbox)
        self.kf.statePost = np.array([z[0], z[1], z[2], z[3], 0, 0, 0, 0], dtype=np.float32).reshape((8, 1))

    @staticmethod
    def _convert_bbox_to_z(bbox: BoundingBox) -> np.ndarray:
        w = max(1.0, bbox.width)
        h = max(1.0, bbox.height)
        cx = bbox.x1 + w / 2.0
        cy = bbox.y1 + h / 2.0
        s = w * h
        r = w / h
        return np.array([cx, cy, s, r], dtype=np.float32)

    def predict(self) -> Tuple[float, float, float, float]:
        """Advances state vector and returns predicted [x1, y1, x2, y2] bounding box."""
        if self.kf.statePost[2, 0] + self.kf.statePost[6, 0] <= 0:
            self.kf.statePost[6, 0] = 0.0

        pred = self.kf.predict()
        return self._convert_x_to_bbox(pred)

    def update(self, bbox: BoundingBox) -> None:
        """Updates internal Kalman state using observed bounding box measurement."""
        z = self._convert_bbox_to_z(bbox)
        self.kf.correct(z.reshape((4, 1)))

    def get_current_bbox(self) -> Tuple[float, float, float, float]:
        """Returns current state estimate converted to [x1, y1, x2, y2]."""
        return self._convert_x_to_bbox(self.kf.statePost)

    @staticmethod
    def _convert_x_to_bbox(state: np.ndarray) -> Tuple[float, float, float, float]:
        cx = float(state[0, 0])
        cy = float(state[1, 0])
        s = max(1.0, float(state[2, 0]))
        r = max(0.01, float(state[3, 0]))

        w = np.sqrt(s * r)
        h = s / w if w > 0 else 1.0

        x1 = cx - w / 2.0
        y1 = cy - h / 2.0
        x2 = cx + w / 2.0
        y2 = cy + h / 2.0
        return (x1, y1, x2, y2)


@dataclass
class TrackedObject:
    """
    Tracked vehicle instance with a persistent track_id across frames.
    """
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
    frame_index: Optional[int] = None
    timestamp_seconds: Optional[float] = None
    state: TrackState = TrackState.NEW
    age_frames: int = 1
    hits: int = 1
    time_since_update: int = 0
    trajectory: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def center(self) -> Tuple[float, float]:
        return (self.bbox.x1 + self.bbox.width / 2.0, self.bbox.y1 + self.bbox.height / 2.0)


@dataclass
class FrameTrackingResult:
    """Tracking results for a single video frame."""
    frame_index: int
    timestamp_seconds: float
    tracked_objects: List[TrackedObject] = field(default_factory=list)

    @property
    def active_tracks_count(self) -> int:
        return len(self.tracked_objects)


@dataclass
class VideoTrackingOutput:
    """Aggregated tracking results across all video frames."""
    total_frames_processed: int
    total_detections_count: int
    total_unique_tracks: int
    tracks_by_class: Dict[str, int]
    frames: List[FrameTrackingResult]
    processing_time_ms: float
    annotated_preview_base64: Optional[str] = None


class Tracker(ABC):
    """
    Abstract Tracker interface.
    Consumes DetectionResult objects from Phase 5 and associates them into persistent tracks.
    """

    @abstractmethod
    def update(
        self,
        detections: List[DetectionResult],
        frame_index: Optional[int] = None,
        timestamp_seconds: Optional[float] = None,
    ) -> List[TrackedObject]:
        """Associates detections in the current frame and returns active TrackedObjects."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets all internal track state and ID counter."""
        pass

    @abstractmethod
    def track_video(
        self,
        video_source: VideoSource,
        detector: Detector,
        max_frames: Optional[int] = None,
        target_fps: Optional[int] = None,
    ) -> VideoTrackingOutput:
        """Runs end-to-end detection and tracking over frames from a VideoSource."""
        pass

    @property
    @abstractmethod
    def tracker_name(self) -> str:
        """Identifier of the tracking algorithm."""
        pass

    @property
    @abstractmethod
    def max_lost_frames(self) -> int:
        """Maximum frames a lost track is retained before termination."""
        pass

    @property
    @abstractmethod
    def iou_threshold(self) -> float:
        """IoU spatial matching threshold."""
        pass


class ByteTrackVehicleTracker(Tracker):
    """
    Kalman-filter and IoU-association multi-object tracker tailored for traffic vehicles.
    Maintains persistent track IDs, handles temporary occlusions (missed detections),
    and enforces explicit track lifecycle management.
    """

    def __init__(
        self,
        iou_threshold: Optional[float] = None,
        max_lost_frames: Optional[int] = None,
        min_hits: Optional[int] = None,
    ):
        self._iou_threshold = (
            float(iou_threshold)
            if iou_threshold is not None
            else getattr(settings, "tracker_iou_threshold", 0.3)
        )
        self._max_lost_frames = (
            int(max_lost_frames)
            if max_lost_frames is not None
            else getattr(settings, "tracker_max_lost_frames", 15)
        )
        self._min_hits = (
            int(min_hits)
            if min_hits is not None
            else getattr(settings, "tracker_min_hits", 1)
        )

        self._next_track_id: int = 1
        self._tracks: Dict[int, TrackedObject] = {}
        self._kalman_filters: Dict[int, KalmanBoxTracker] = {}
        self._all_created_track_ids: Set[int] = set()

        logger.info(
            "ByteTrackVehicleTracker initialized (iou_threshold=%.2f, max_lost_frames=%d, min_hits=%d)",
            self._iou_threshold,
            self._max_lost_frames,
            self._min_hits,
        )

    @property
    def tracker_name(self) -> str:
        return "ByteTrack-Kalman-IoU"

    @property
    def max_lost_frames(self) -> int:
        return self._max_lost_frames

    @property
    def iou_threshold(self) -> float:
        return self._iou_threshold

    @property
    def total_unique_tracks_count(self) -> int:
        return len(self._all_created_track_ids)

    def reset(self) -> None:
        """Clears all active and lost tracks and resets ID counter."""
        self._next_track_id = 1
        self._tracks.clear()
        self._kalman_filters.clear()
        self._all_created_track_ids.clear()
        logger.debug("Tracker state reset.")

    def update(
        self,
        detections: List[DetectionResult],
        frame_index: Optional[int] = None,
        timestamp_seconds: Optional[float] = None,
    ) -> List[TrackedObject]:
        """
        Associates detections with existing tracks using Kalman motion prediction and IoU association.
        Returns list of active TrackedObjects for the current frame.
        """
        # Step 1: Predict positions for all existing tracks
        predicted_boxes: Dict[int, Tuple[float, float, float, float]] = {}
        for track_id, kf in list(self._kalman_filters.items()):
            track = self._tracks.get(track_id)
            if track and track.state != TrackState.TERMINATED:
                predicted_boxes[track_id] = kf.predict()

        # Step 2: Associate detections with existing tracks via IoU
        matched_track_ids: Set[int] = set()
        matched_detection_indices: Set[int] = set()
        active_track_ids = [
            tid for tid, t in self._tracks.items()
            if t.state in (TrackState.ACTIVE, TrackState.NEW, TrackState.LOST)
        ]

        if active_track_ids and detections:
            # Build IoU cost matrix
            cost_matrix = np.zeros((len(active_track_ids), len(detections)), dtype=np.float32)
            for r, tid in enumerate(active_track_ids):
                pred_box = predicted_boxes.get(tid)
                if pred_box is None:
                    continue
                for c, det in enumerate(detections):
                    det_box = (det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2)
                    cost_matrix[r, c] = compute_iou(pred_box, det_box)

            # Greedy bipartite matching from highest IoU down to iou_threshold
            flat_indices = np.argsort(-cost_matrix, axis=None)
            for flat_idx in flat_indices:
                r = int(flat_idx // len(detections))
                c = int(flat_idx % len(detections))
                iou_val = cost_matrix[r, c]

                if iou_val < self._iou_threshold:
                    break

                tid = active_track_ids[r]
                if tid in matched_track_ids or c in matched_detection_indices:
                    continue

                det = detections[c]
                # Class consistency check: prefer matching same class
                matched_track = self._tracks[tid]
                if matched_track.class_id != det.class_id:
                    # Allow matching across minor class misclassifications only if IoU is very high (> 0.6)
                    if iou_val < 0.6:
                        continue

                # Record match
                matched_track_ids.add(tid)
                matched_detection_indices.add(c)

                # Update Kalman filter and TrackedObject
                self._kalman_filters[tid].update(det.bbox)
                matched_track.bbox = det.bbox
                matched_track.class_id = det.class_id
                matched_track.class_name = det.class_name
                matched_track.confidence = det.confidence
                matched_track.frame_index = frame_index
                matched_track.timestamp_seconds = timestamp_seconds
                matched_track.state = TrackState.ACTIVE
                matched_track.hits += 1
                matched_track.age_frames += 1
                matched_track.time_since_update = 0
                matched_track.trajectory.append(matched_track.center)

        # Step 3: Handle unmatched active/lost tracks -> increment time_since_update
        for tid in active_track_ids:
            if tid not in matched_track_ids:
                track = self._tracks[tid]
                track.time_since_update += 1
                track.age_frames += 1

                # Update bounding box from Kalman prediction
                if tid in predicted_boxes:
                    p = predicted_boxes[tid]
                    track.bbox = BoundingBox.from_xyxy(
                        x1=p[0], y1=p[1], x2=p[2], y2=p[3],
                        frame_width=int(max(p[2], 10000)),
                        frame_height=int(max(p[3], 10000)),
                    )

                if track.time_since_update > self._max_lost_frames:
                    track.state = TrackState.TERMINATED
                else:
                    track.state = TrackState.LOST

        # Step 4: Initialize new tracks for unmatched detections
        for c, det in enumerate(detections):
            if c not in matched_detection_indices:
                new_tid = self._next_track_id
                self._next_track_id += 1

                new_track = TrackedObject(
                    track_id=new_tid,
                    class_id=det.class_id,
                    class_name=det.class_name,
                    confidence=det.confidence,
                    bbox=det.bbox,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    state=TrackState.ACTIVE if self._min_hits <= 1 else TrackState.NEW,
                    age_frames=1,
                    hits=1,
                    time_since_update=0,
                    trajectory=[(det.bbox.x1 + det.bbox.width / 2.0, det.bbox.y1 + det.bbox.height / 2.0)],
                )

                self._tracks[new_tid] = new_track
                self._kalman_filters[new_tid] = KalmanBoxTracker(det.bbox)
                self._all_created_track_ids.add(new_tid)

        # Step 5: Clean up terminated tracks
        terminated_ids = [tid for tid, t in self._tracks.items() if t.state == TrackState.TERMINATED]
        for tid in terminated_ids:
            # We keep track in memory for history if needed, or remove from active tracking
            del self._tracks[tid]
            if tid in self._kalman_filters:
                del self._kalman_filters[tid]

        # Return currently active tracks
        active_results = [t for t in self._tracks.values() if t.state == TrackState.ACTIVE]
        return active_results

    def track_video(
        self,
        video_source: VideoSource,
        detector: Detector,
        max_frames: Optional[int] = None,
        target_fps: Optional[int] = None,
    ) -> VideoTrackingOutput:
        """
        Executes pipeline: VideoSource -> Detector -> DetectionResult -> Tracker.
        Returns structured VideoTrackingOutput with persistent track IDs.
        """
        start_time = time.perf_counter()
        self.reset()

        frame_results: List[FrameTrackingResult] = []
        total_detections = 0
        preview_frame_b64: Optional[str] = None
        preview_captured = False

        effective_max_frames = min(max_frames if max_frames is not None else 50, 300)

        for frame_idx, timestamp_sec, frame in video_source.extract_frames(
            target_fps=target_fps,
            max_frames=effective_max_frames,
        ):
            # Phase 5 detector produces DetectionResults (no track_id)
            detections = detector.detect(
                frame=frame,
                frame_index=frame_idx,
                timestamp_seconds=timestamp_sec,
            )
            total_detections += len(detections)

            # Phase 6 tracker assigns persistent track_ids
            tracked_objects = self.update(
                detections=detections,
                frame_index=frame_idx,
                timestamp_seconds=timestamp_sec,
            )

            frame_result = FrameTrackingResult(
                frame_index=frame_idx,
                timestamp_seconds=timestamp_sec,
                tracked_objects=tracked_objects,
            )
            frame_results.append(frame_result)

            # Capture visual annotated preview on first frame with active tracks (or frame 0)
            if not preview_captured and (tracked_objects or frame_idx == 0):
                preview_frame_b64 = self._generate_annotated_preview(frame, tracked_objects)
                preview_captured = True

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Calculate tracks by vehicle class
        tracks_by_class: Dict[str, int] = {cls_name: 0 for cls_name in sorted(detector.target_classes)}
        for f in frame_results:
            for obj in f.tracked_objects:
                tracks_by_class[obj.class_name] = tracks_by_class.get(obj.class_name, 0) + 1

        return VideoTrackingOutput(
            total_frames_processed=len(frame_results),
            total_detections_count=total_detections,
            total_unique_tracks=self.total_unique_tracks_count,
            tracks_by_class=tracks_by_class,
            frames=frame_results,
            processing_time_ms=elapsed_ms,
            annotated_preview_base64=preview_frame_b64,
        )

    def _generate_annotated_preview(
        self,
        frame: np.ndarray,
        tracked_objects: List[TrackedObject],
    ) -> str:
        """Renders bounding boxes with Track ID labels and trajectory trails onto a frame copy."""
        preview = frame.copy()

        # Color palette by track ID for distinct visual identification
        colors = [
            (255, 128, 0),   # Cyan/Orange
            (0, 255, 128),   # Green
            (255, 0, 255),   # Magenta
            (0, 215, 255),   # Yellow/Gold
            (255, 50, 50),   # Bright Blue
            (50, 255, 255),  # Yellow
            (180, 105, 255), # Pink/Purple
        ]

        for obj in tracked_objects:
            color = colors[obj.track_id % len(colors)]
            bbox = obj.bbox
            x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)

            # Draw bounding box
            cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)

            # Draw trajectory trail
            if len(obj.trajectory) > 1:
                pts = np.array([[int(pt[0]), int(pt[1])] for pt in obj.trajectory[-15:]], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(preview, [pts], False, color, 2)

            # Draw label banner with Track ID: e.g. "ID: 1 | car (0.89)"
            label = f"ID: #{obj.track_id} {obj.class_name} {obj.confidence:.2f}"
            (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(
                preview,
                (x1, max(0, y1 - text_h - 6)),
                (x1 + text_w + 6, max(text_h + 6, y1)),
                color,
                -1,
            )
            cv2.putText(
                preview,
                label,
                (x1 + 3, max(text_h + 2, y1 - 3)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        # Resize if width > 800 for efficient payload transfer
        h, w = preview.shape[:2]
        if w > 800:
            scale = 800 / w
            preview = cv2.resize(preview, (800, int(h * scale)), interpolation=cv2.INTER_AREA)

        ret, buffer = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            return ""
        return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
