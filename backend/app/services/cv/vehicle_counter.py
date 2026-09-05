"""
Vehicle Counting Service implementing track-based virtual line crossing detection.

Architecture:
    VideoSource -> Detector -> DetectionResult -> Tracker -> TrackedObject -> VehicleCounter -> CountingResult

Strict Phase 7 boundaries:
- Consumes TrackedObject outputs from Tracker (Phase 6).
- Deduplicates vehicle counts strictly by persistent track_id.
- Mathematical line-crossing detection with direction classification.
- Exactly-once counting per unique vehicle trajectory.
- NO frame-based counting, NO raw detection counting, NO lane polygon analysis (Phase 8), NO congestion scoring (Phase 9).
"""
import base64
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

from app.config.settings import settings
from app.core.logging import get_logger
from app.services.cv.detector import Detector
from app.services.cv.tracker import ByteTrackVehicleTracker, TrackedObject, Tracker
from app.services.cv.video_source import VideoSource

logger = get_logger(__name__)


@dataclass
class Point2D:
    """2D point coordinate (supports relative [0.0, 1.0] or absolute pixels)."""
    x: float
    y: float

    def to_pixel(self, width: int, height: int) -> Tuple[int, int]:
        """Converts coordinates to absolute pixel coordinates if normalized."""
        px = int(self.x * width) if 0.0 <= self.x <= 1.0 and width > 1 else int(self.x)
        py = int(self.y * height) if 0.0 <= self.y <= 1.0 and height > 1 else int(self.y)
        return (max(0, min(width - 1, px)), max(0, min(height - 1, py)))


@dataclass
class CountingLine:
    """Virtual tripwire line configuration for vehicle crossing detection."""
    p1: Point2D
    p2: Point2D
    label: str = "main_line"
    direction_a_to_b: str = "inbound"
    direction_b_to_a: str = "outbound"
    min_movement_px: float = 2.0

    @classmethod
    def default_from_settings(cls) -> "CountingLine":
        """Creates a default horizontal counting line centered in frame from settings."""
        p1_x = getattr(settings, "counting_line_p1_x", 0.0)
        p1_y = getattr(settings, "counting_line_p1_y", 0.5)
        p2_x = getattr(settings, "counting_line_p2_x", 1.0)
        p2_y = getattr(settings, "counting_line_p2_y", 0.5)
        min_mov = getattr(settings, "counting_min_movement_px", 2.0)
        return cls(
            p1=Point2D(x=p1_x, y=p1_y),
            p2=Point2D(x=p2_x, y=p2_y),
            label="main_tripwire",
            direction_a_to_b="inbound",
            direction_b_to_a="outbound",
            min_movement_px=min_mov,
        )


@dataclass
class CrossingEvent:
    """Record of a single vehicle crossing event."""
    track_id: int
    class_name: str
    frame_index: int
    timestamp_seconds: float
    direction: str
    crossing_point: Tuple[float, float]
    line_label: str = "main_line"


@dataclass
class FrameCountingResult:
    """Counting results for a single sampled frame."""
    frame_index: int
    timestamp_seconds: float
    active_tracks_count: int
    new_crossings: List[CrossingEvent] = field(default_factory=list)


@dataclass
class VideoCountingOutput:
    """Aggregated vehicle counting results across an entire video."""
    video_id: Optional[str]
    original_filename: Optional[str]
    pipeline_stage: str = "counting-run"
    detector_model: str = "yolov8n"
    tracker_name: str = "ByteTrack-Kalman-IoU"
    counting_line: CountingLine = field(default_factory=CountingLine.default_from_settings)
    total_frames_processed: int = 0
    total_detections_count: int = 0
    total_unique_tracks: int = 0
    total_counted_vehicles: int = 0
    counts_by_class: Dict[str, int] = field(default_factory=dict)
    counts_by_direction: Dict[str, int] = field(default_factory=dict)
    counted_track_ids: List[int] = field(default_factory=list)
    crossing_events: List[CrossingEvent] = field(default_factory=list)
    frames: List[FrameCountingResult] = field(default_factory=list)
    processing_time_ms: float = 0.0
    annotated_preview_base64: Optional[str] = None


class VehicleCounter(ABC):
    """
    Abstract Base Class for vehicle counting engines.
    Operates strictly on TrackedObject streams, maintaining deduplication per track ID.
    """

    @abstractmethod
    def update(
        self,
        tracked_objects: List[TrackedObject],
        frame_index: int,
        timestamp_seconds: float,
        frame_width: int = 1280,
        frame_height: int = 720,
    ) -> List[CrossingEvent]:
        """Evaluates tracked objects in the current frame and returns new crossing events."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets all internal count state, deduplication sets, and history."""
        pass

    @property
    @abstractmethod
    def total_count(self) -> int:
        """Total unique vehicles counted."""
        pass

    @property
    @abstractmethod
    def counts_by_class(self) -> Dict[str, int]:
        """Vehicle counts categorized by class."""
        pass

    @property
    @abstractmethod
    def counts_by_direction(self) -> Dict[str, int]:
        """Vehicle counts categorized by crossing direction."""
        pass


class LineCrossingCounter(VehicleCounter):
    """
    Directional virtual-line crossing counter with strict track-ID deduplication.

    Mathematical Algorithm:
    - Counting line is defined by segment endpoints P1(x1, y1) and P2(x2, y2).
    - Given vector L = P2 - P1, and centroid C(x, y), vector V = C - P1.
    - Signed 2D cross product:
        cp = L_x * V_y - L_y * V_x = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
    - Side A: cp > 0, Side B: cp < 0.
    - Crossing occurs when a vehicle's centroid transitions from Side A to Side B or Side B to Side A,
      subject to minimum trajectory movement threshold and bounding segment intersection.
    - Track ID Deduplication: Each track_id is counted at most once during its entire lifetime.
    """

    def __init__(self, line: Optional[CountingLine] = None):
        self.line = line or CountingLine.default_from_settings()
        self._counted_track_ids: Set[int] = set()
        self._track_previous_positions: Dict[int, Tuple[float, float]] = {}
        self._track_previous_signs: Dict[int, float] = {}
        self._crossing_events: List[CrossingEvent] = []
        self._counts_by_class: Dict[str, int] = {}
        self._counts_by_direction: Dict[str, int] = {
            self.line.direction_a_to_b: 0,
            self.line.direction_b_to_a: 0,
        }

        logger.info(
            "LineCrossingCounter initialized with line: P1=(%.2f, %.2f) P2=(%.2f, %.2f) label='%s'",
            self.line.p1.x,
            self.line.p1.y,
            self.line.p2.x,
            self.line.p2.y,
            self.line.label,
        )

    @property
    def total_count(self) -> int:
        return len(self._counted_track_ids)

    @property
    def counts_by_class(self) -> Dict[str, int]:
        return dict(self._counts_by_class)

    @property
    def counts_by_direction(self) -> Dict[str, int]:
        return dict(self._counts_by_direction)

    @property
    def counted_track_ids(self) -> List[int]:
        return sorted(list(self._counted_track_ids))

    @property
    def crossing_events(self) -> List[CrossingEvent]:
        return list(self._crossing_events)

    def reset(self) -> None:
        """Clears all counters, history, and deduplication records."""
        self._counted_track_ids.clear()
        self._track_previous_positions.clear()
        self._track_previous_signs.clear()
        self._crossing_events.clear()
        self._counts_by_class.clear()
        self._counts_by_direction = {
            self.line.direction_a_to_b: 0,
            self.line.direction_b_to_a: 0,
        }
        logger.debug("LineCrossingCounter state reset.")

    @staticmethod
    def _compute_cross_product(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        pt: Tuple[float, float],
    ) -> float:
        """
        Computes 2D signed cross product of vector (P2 - P1) with vector (pt - P1):
        cp = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        """
        return (p2[0] - p1[0]) * (pt[1] - p1[1]) - (p2[1] - p1[1]) * (pt[0] - p1[0])

    @staticmethod
    def _segments_intersect(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        p4: Tuple[float, float],
    ) -> bool:
        """
        Determines if line segment [P1, P2] intersects line segment [P3, P4].
        """
        def ccw(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
            return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

        cp1 = ccw(p1, p2, p3)
        cp2 = ccw(p1, p2, p4)
        cp3 = ccw(p3, p4, p1)
        cp4 = ccw(p3, p4, p2)

        # Segments intersect if endpoints of each segment straddle the line of the other
        return ((cp1 * cp2) <= 0.0) and ((cp3 * cp4) <= 0.0)

    def update(
        self,
        tracked_objects: List[TrackedObject],
        frame_index: int,
        timestamp_seconds: float,
        frame_width: int = 1280,
        frame_height: int = 720,
    ) -> List[CrossingEvent]:
        """
        Processes tracked vehicles for the current frame, identifies new line crossings,
        enforces single-count deduplication, and records crossing events.
        """
        new_events: List[CrossingEvent] = []

        # Convert line coordinates to frame pixel space
        l_p1 = self.line.p1.to_pixel(frame_width, frame_height)
        l_p2 = self.line.p2.to_pixel(frame_width, frame_height)

        p1_f = (float(l_p1[0]), float(l_p1[1]))
        p2_f = (float(l_p2[0]), float(l_p2[1]))

        # Line segment length
        line_len = math.hypot(p2_f[0] - p1_f[0], p2_f[1] - p1_f[1])
        if line_len < 1e-3:
            logger.warning("Degenerate counting line configured (zero length). No crossings can be detected.")
            return []

        for obj in tracked_objects:
            tid = obj.track_id
            curr_pos = obj.center

            # Calculate current side relative to line
            curr_cp = self._compute_cross_product(p1_f, p2_f, curr_pos)

            # Skip if track already counted (Strict Exactly-Once Rule)
            if tid in self._counted_track_ids:
                self._track_previous_positions[tid] = curr_pos
                self._track_previous_signs[tid] = curr_cp
                continue

            prev_pos = self._track_previous_positions.get(tid)
            prev_cp = self._track_previous_signs.get(tid)

            # If this is the track's first appearance, register position and sign
            if prev_pos is None or prev_cp is None:
                self._track_previous_positions[tid] = curr_pos
                self._track_previous_signs[tid] = curr_cp
                continue

            # Minimum movement filter to eliminate stationary centroid jitter
            move_dist = math.hypot(curr_pos[0] - prev_pos[0], curr_pos[1] - prev_pos[1])
            if move_dist < self.line.min_movement_px:
                continue

            # Check for sign transition across line:
            # Side A -> Side B (cp < 0 -> cp > 0) or Side B -> Side A (cp > 0 -> cp < 0)
            crossed = False
            direction = self.line.direction_a_to_b

            # Use small epsilon tolerance to avoid false triggers exactly on line
            eps = 1e-4

            if prev_cp < -eps and curr_cp > eps:
                # Transitioned Top/Side A -> Bottom/Side B (Inbound)
                crossed = True
                direction = self.line.direction_a_to_b
            elif prev_cp > eps and curr_cp < -eps:
                # Transitioned Bottom/Side B -> Top/Side A (Outbound)
                crossed = True
                direction = self.line.direction_b_to_a

            # Validate that trajectory segment intersects the line segment
            if crossed:
                # Check segment intersection
                intersects = self._segments_intersect(p1_f, p2_f, prev_pos, curr_pos)
                if not intersects:
                    # If line endpoints are near frame borders, accept infinite line crossing
                    is_full_width = (
                        (abs(p1_f[0]) <= 5 or abs(p1_f[0] - frame_width) <= 5) and
                        (abs(p2_f[0]) <= 5 or abs(p2_f[0] - frame_width) <= 5)
                    ) or (
                        (abs(p1_f[1]) <= 5 or abs(p1_f[1] - frame_height) <= 5) and
                        (abs(p2_f[1]) <= 5 or abs(p2_f[1] - frame_height) <= 5)
                    )
                    if not is_full_width:
                        crossed = False

            if crossed:
                # Record unique count for this track
                self._counted_track_ids.add(tid)
                self._counts_by_class[obj.class_name] = self._counts_by_class.get(obj.class_name, 0) + 1
                self._counts_by_direction[direction] = self._counts_by_direction.get(direction, 0) + 1

                event = CrossingEvent(
                    track_id=tid,
                    class_name=obj.class_name,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    direction=direction,
                    crossing_point=(round(curr_pos[0], 1), round(curr_pos[1], 1)),
                    line_label=self.line.label,
                )
                self._crossing_events.append(event)
                new_events.append(event)

                logger.info(
                    "Vehicle counted! Track #%d (%s) crossed line '%s' [%s] at frame %d (%.2fs)",
                    tid,
                    obj.class_name,
                    self.line.label,
                    direction,
                    frame_index,
                    timestamp_seconds,
                )

            # Update history
            self._track_previous_positions[tid] = curr_pos
            self._track_previous_signs[tid] = curr_cp

        return new_events

    def count_video(
        self,
        video_source: VideoSource,
        detector: Detector,
        tracker: Tracker,
        max_frames: Optional[int] = None,
        target_fps: Optional[int] = None,
        video_id: Optional[str] = None,
        original_filename: Optional[str] = None,
    ) -> VideoCountingOutput:
        """
        Executes end-to-end counting pipeline:
        VideoSource -> Detector -> Tracker -> LineCrossingCounter.
        """
        start_time = time.perf_counter()
        self.reset()
        tracker.reset()

        frame_results: List[FrameCountingResult] = []
        total_detections = 0
        preview_frame_b64: Optional[str] = None
        preview_captured = False

        effective_max_frames = min(max_frames if max_frames is not None else 50, 300)
        fps = target_fps or settings.processing_fps

        width = 1280
        height = 720

        # Initialize all target vehicle classes to 0 count
        for cls_name in sorted(detector.target_classes):
            if cls_name not in self._counts_by_class:
                self._counts_by_class[cls_name] = 0

        for frame_idx, timestamp_sec, frame in video_source.extract_frames(
            target_fps=fps,
            max_frames=effective_max_frames,
        ):
            h, w = frame.shape[:2]
            width, height = w, h

            # 1. Detection (Phase 5)
            detections = detector.detect(
                frame=frame,
                frame_index=frame_idx,
                timestamp_seconds=timestamp_sec,
            )
            total_detections += len(detections)

            # 2. Tracking (Phase 6)
            tracked_objects = tracker.update(
                detections=detections,
                frame_index=frame_idx,
                timestamp_seconds=timestamp_sec,
            )

            # 3. Counting (Phase 7)
            new_crossings = self.update(
                tracked_objects=tracked_objects,
                frame_index=frame_idx,
                timestamp_seconds=timestamp_sec,
                frame_width=w,
                frame_height=h,
            )

            frame_result = FrameCountingResult(
                frame_index=frame_idx,
                timestamp_seconds=timestamp_sec,
                active_tracks_count=len(tracked_objects),
                new_crossings=new_crossings,
            )
            frame_results.append(frame_result)

            # Capture visual annotated preview on first frame with crossing or active tracks
            if not preview_captured and (new_crossings or (tracked_objects and frame_idx >= 5) or frame_idx == 0):
                preview_frame_b64 = self._generate_annotated_preview(
                    frame=frame,
                    tracked_objects=tracked_objects,
                    frame_width=w,
                    frame_height=h,
                )
                if new_crossings:
                    preview_captured = True

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return VideoCountingOutput(
            video_id=video_id,
            original_filename=original_filename,
            pipeline_stage="counting-run",
            detector_model=detector.model_name,
            tracker_name=tracker.tracker_name,
            counting_line=self.line,
            total_frames_processed=len(frame_results),
            total_detections_count=total_detections,
            total_unique_tracks=tracker.total_unique_tracks_count if hasattr(tracker, "total_unique_tracks_count") else len(self._track_previous_positions),
            total_counted_vehicles=self.total_count,
            counts_by_class=self.counts_by_class,
            counts_by_direction=self.counts_by_direction,
            counted_track_ids=self.counted_track_ids,
            crossing_events=self.crossing_events,
            frames=frame_results,
            processing_time_ms=elapsed_ms,
            annotated_preview_base64=preview_frame_b64,
        )

    def _generate_annotated_preview(
        self,
        frame: np.ndarray,
        tracked_objects: List[TrackedObject],
        frame_width: int,
        frame_height: int,
    ) -> str:
        """
        Renders counting tripwire line, direction markers, vehicle bounding boxes,
        and count HUD overlay onto a frame copy.
        """
        preview = frame.copy()

        # Convert line endpoints
        p1 = self.line.p1.to_pixel(frame_width, frame_height)
        p2 = self.line.p2.to_pixel(frame_width, frame_height)

        # 1. Draw virtual counting line (Glowing Cyan / Amber)
        cv2.line(preview, p1, p2, (0, 220, 255), 3, cv2.LINE_AA)
        cv2.circle(preview, p1, 6, (0, 165, 255), -1)
        cv2.circle(preview, p2, 6, (0, 165, 255), -1)

        # Line label
        mid_x = (p1[0] + p2[0]) // 2
        mid_y = (p1[1] + p2[1]) // 2
        line_tag = f"COUNTING LINE: {self.line.label.upper()} ({self.line.direction_a_to_b.upper()} / {self.line.direction_b_to_a.upper()})"
        cv2.putText(
            preview,
            line_tag,
            (max(20, mid_x - 140), max(25, mid_y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 220, 255),
            2,
            cv2.LINE_AA,
        )

        # 2. Draw vehicle bounding boxes & badges
        colors = [
            (255, 128, 0),
            (0, 255, 128),
            (255, 0, 255),
            (0, 215, 255),
            (255, 50, 50),
        ]

        for obj in tracked_objects:
            color = colors[obj.track_id % len(colors)]
            bbox = obj.bbox
            x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)

            is_counted = obj.track_id in self._counted_track_ids
            box_color = (0, 255, 0) if is_counted else color
            thickness = 3 if is_counted else 2

            cv2.rectangle(preview, (x1, y1), (x2, y2), box_color, thickness)

            # Draw trajectory trail
            if len(obj.trajectory) > 1:
                pts = np.array([[int(pt[0]), int(pt[1])] for pt in obj.trajectory[-15:]], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(preview, [pts], False, box_color, 2)

            # Draw centroid point
            c_x, c_y = int(obj.center[0]), int(obj.center[1])
            cv2.circle(preview, (c_x, c_y), 4, (0, 255, 255), -1)

            # Label
            status_tag = " [COUNTED]" if is_counted else ""
            label = f"ID #{obj.track_id} {obj.class_name}{status_tag}"
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(
                preview,
                (x1, max(0, y1 - text_h - 6)),
                (x1 + text_w + 6, max(text_h + 6, y1)),
                box_color,
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

        # 3. Draw top HUD Banner
        hud_h = 45
        cv2.rectangle(preview, (0, 0), (frame_width, hud_h), (15, 23, 42), -1)
        cv2.line(preview, (0, hud_h), (frame_width, hud_h), (0, 180, 220), 2)

        hud_text = f"TOTAL COUNTED: {self.total_count}  |  CARS: {self._counts_by_class.get('car', 0)}  TRUCKS: {self._counts_by_class.get('truck', 0)}  BUSES: {self._counts_by_class.get('bus', 0)}  |  IN: {self._counts_by_direction.get(self.line.direction_a_to_b, 0)}  OUT: {self._counts_by_direction.get(self.line.direction_b_to_a, 0)}"
        cv2.putText(
            preview,
            hud_text,
            (20, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # Resize if width > 800 for efficient payload transfer
        if frame_width > 800:
            scale = 800 / frame_width
            preview = cv2.resize(preview, (800, int(frame_height * scale)), interpolation=cv2.INTER_AREA)

        ret, buffer = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            return ""
        return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
