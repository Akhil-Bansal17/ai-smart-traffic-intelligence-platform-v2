"""
Lane Analysis & Density Estimation Service.

Architecture:
    VideoTrackingOutput + List[LaneRegion] -> LaneAnalyzer -> LaneAnalyticsResult -> API / UI

Strict Phase 9 boundaries:
- Configured-region assignment based on user-defined polygons (no autonomous lane detection).
- Ray-casting point-in-polygon test using vehicle centroid (TrackedObject.center).
- Multi-frame persistence threshold (N=2 frames default) to prevent boundary flickering.
- Image-space density (vehicles / polygon_area_px2) using Shoelace area calculation.
- Normalized density score min(1.0, count / (area_px2 / 2500)).
- Directional per-lane metrics explicitly omitted (decoupled from line crossing).
- Transparent calibration warnings and honest arithmetic.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import time
from typing import Dict, List, Optional, Set, Tuple

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.services.cv.detector import DEFAULT_VEHICLE_CLASSES
from app.services.cv.tracker import (
    TrackedObject,
    TrackState,
    VideoTrackingOutput,
)

logger = get_logger(__name__)

# Constants and limits
MAX_LANES_PER_REQUEST = 20
MAX_POINTS_PER_POLYGON = 50
MIN_POINTS_PER_POLYGON = 3
REFERENCE_CELL_AREA_PX2 = 2500.0  # 50x50 pixel cell reference for normalized density score


def polygon_area_shoelace(points: List[Tuple[float, float]]) -> float:
    """
    Computes the 2D polygon area in pixel^2 using the Shoelace formula (Gauss's area formula).
    
    Area = 0.5 * |sum_{i=0}^{n-1} (x_i * y_{i+1} - x_{i+1} * y_i)|
    where (x_n, y_n) wraps around to (x_0, y_0).
    """
    n = len(points)
    if n < 3:
        return 0.0

    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]

    return abs(area) / 2.0


def point_in_polygon_raycast(
    point: Tuple[float, float],
    polygon: List[Tuple[float, float]],
) -> bool:
    """
    Tests whether a 2D point (px, py) lies strictly inside or on the boundary of a polygon
    using the Ray-Casting algorithm (Jordan curve theorem).
    
    Casts a horizontal ray from (px, py) towards +infinity in x.
    Counts the number of edge intersections. Odd count -> inside, even count -> outside.
    """
    n = len(polygon)
    if n < 3:
        return False

    px, py = point
    inside = False

    for i in range(n):
        j = (i + 1) % n
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        # Check if the horizontal ray at y = py crosses the segment (xi, yi) - (xj, yj)
        # One endpoint must be above py and one strictly below/at py
        if ((yi > py) != (yj > py)):
            # Compute x-coordinate of intersection
            denom = yj - yi
            if abs(denom) > 1e-9:
                intersect_x = (xj - xi) * (py - yi) / denom + xi
                if px < intersect_x:
                    inside = not inside

    return inside


def validate_lane_polygon(
    lane_id: str,
    name: str,
    polygon: List[Tuple[float, float]],
) -> float:
    """
    Validates polygon coordinates, boundary rules, point counts, and non-zero area.
    Returns the calculated polygon area in px^2.
    Raises AppException on validation failures.
    """
    if not lane_id or not lane_id.strip():
        raise AppException("Lane ID cannot be empty.", status_code=422)
    if not name or not name.strip() or len(name) > 100:
        raise AppException(
            f"Lane '{lane_id}' name must be non-empty and <= 100 characters.",
            status_code=422,
        )

    if len(polygon) < MIN_POINTS_PER_POLYGON:
        raise AppException(
            f"Lane '{lane_id}' polygon must have at least {MIN_POINTS_PER_POLYGON} vertices, got {len(polygon)}.",
            status_code=422,
        )

    if len(polygon) > MAX_POINTS_PER_POLYGON:
        raise AppException(
            f"Lane '{lane_id}' polygon exceeds max limit of {MAX_POINTS_PER_POLYGON} vertices, got {len(polygon)}.",
            status_code=422,
        )

    for idx, pt in enumerate(polygon):
        if len(pt) != 2:
            raise AppException(
                f"Lane '{lane_id}' point at index {idx} must be a 2D coordinate [x, y].",
                status_code=422,
            )
        x, y = pt
        if math.isnan(x) or math.isnan(y) or math.isinf(x) or math.isinf(y):
            raise AppException(
                f"Lane '{lane_id}' contains invalid non-finite coordinates at index {idx}.",
                status_code=422,
            )
        if x < 0 or y < 0:
            raise AppException(
                f"Lane '{lane_id}' contains negative coordinates ({x}, {y}) at index {idx}.",
                status_code=422,
            )

    area = polygon_area_shoelace(polygon)
    if area <= 1e-6:
        raise AppException(
            f"Lane '{lane_id}' polygon is degenerate or collinear (area = {area:.2f} px^2 <= 0).",
            status_code=422,
        )

    return area


@dataclass
class LaneRegion:
    """Configured polygon region representing a traffic lane or zone."""
    lane_id: str
    name: str
    polygon: List[Tuple[float, float]]
    direction_hint: Optional[str] = None
    area_px2: float = 0.0

    def __post_init__(self):
        if self.area_px2 <= 0.0 and len(self.polygon) >= 3:
            self.area_px2 = polygon_area_shoelace(self.polygon)


@dataclass
class PerLaneSummary:
    """Aggregated traffic metrics and density for a single lane."""
    lane_id: str
    lane_name: str
    polygon: List[Tuple[float, float]]
    polygon_area_px2: float
    total_unique_vehicles: int
    vehicle_class_counts: Dict[str, int]
    direction_hint: Optional[str] = None
    image_space_density_vehicles_per_px2: float = 0.0
    normalized_density_score: float = 0.0
    density_unit: str = "vehicles/px²"
    density_formula: str = "total_unique_vehicles / polygon_area_px2 (image-space uncalibrated)"
    peak_occupancy: int = 0
    average_occupancy: float = 0.0


@dataclass
class LaneAnalyticsResult:
    """Comprehensive lane analysis and density estimation output."""
    video_id: Optional[str]
    original_filename: Optional[str]
    pipeline_stage: str = "lane-analysis-run"
    observation_duration_seconds: float = 0.0
    total_frames_processed: int = 0
    total_unique_tracks: int = 0
    lanes: List[PerLaneSummary] = field(default_factory=list)
    unassigned_vehicles_count: int = 0
    density_calibration_warning: str = (
        "Image-space density is not equivalent to vehicles/km² without camera calibration."
    )
    directional_metrics_omitted_reason: str = (
        "Directional per-lane metrics omitted: tripwire crossing events are decoupled from lane polygons in this phase."
    )
    processing_time_ms: float = 0.0
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class LaneAssignmentEngine:
    """
    Stateful engine tracking vehicle lane assignments across video frames.
    
    Applies persistence threshold (N consecutive frames) to prevent boundary flickering:
    - When a track centroid is observed in lane L for N consecutive frames, it is confirmed in lane L.
    - If a vehicle moves between lanes, it must persist in the new lane for N frames.
    - Computes peak simultaneous occupancy and mean frame occupancy per lane.
    """

    def __init__(
        self,
        lanes: List[LaneRegion],
        persistence_threshold: int = 2,
    ):
        self.lanes = lanes
        self.lane_map = {l.lane_id: l for l in lanes}
        self.persistence_threshold = max(1, persistence_threshold)

        # Track state: track_id -> confirmed_lane_id
        self.confirmed_assignments: Dict[int, str] = {}
        # Track candidate state: track_id -> (candidate_lane_id, consecutive_count)
        self.candidate_assignments: Dict[int, Tuple[Optional[str], int]] = {}
        # Per-track class mapping
        self.track_classes: Dict[int, str] = {}
        # Cumulative unique vehicles per lane: lane_id -> set of track_ids
        self.lane_unique_tracks: Dict[str, Set[int]] = {
            l.lane_id: set() for l in lanes
        }
        # Frame occupancy history: lane_id -> list of occupancy counts per frame
        self.lane_occupancy_history: Dict[str, List[int]] = {
            l.lane_id: [] for l in lanes
        }
        # Set of all seen track IDs
        self.all_seen_tracks: Set[int] = set()

    def process_frame(
        self,
        frame_index: int,
        tracked_objects: List[TrackedObject],
    ) -> Dict[str, List[TrackedObject]]:
        """
        Processes a single frame's tracked objects and updates lane assignments.
        Returns mapping of lane_id -> list of active TrackedObjects in that lane for this frame.
        """
        # Lane occupancy for this specific frame
        frame_lane_occupants: Dict[str, List[TrackedObject]] = {
            l.lane_id: [] for l in self.lanes
        }
        active_track_ids_in_frame: Set[int] = set()

        for obj in tracked_objects:
            if obj.state == TrackState.TERMINATED:
                continue

            track_id = obj.track_id
            self.all_seen_tracks.add(track_id)
            active_track_ids_in_frame.add(track_id)
            self.track_classes[track_id] = obj.class_name

            # Centroid point-in-polygon test
            center = obj.center
            current_raw_lane_id: Optional[str] = None

            for lane in self.lanes:
                if point_in_polygon_raycast(center, lane.polygon):
                    current_raw_lane_id = lane.lane_id
                    break  # First matching lane (first configured priority)

            # Update persistence candidate
            prev_candidate, count = self.candidate_assignments.get(
                track_id, (None, 0)
            )

            if current_raw_lane_id == prev_candidate:
                new_count = count + 1
            else:
                prev_candidate = current_raw_lane_id
                new_count = 1

            self.candidate_assignments[track_id] = (prev_candidate, new_count)

            # Check if threshold reached
            if new_count >= self.persistence_threshold:
                if prev_candidate is not None:
                    self.confirmed_assignments[track_id] = prev_candidate
                    self.lane_unique_tracks[prev_candidate].add(track_id)
                else:
                    # Vehicle confirmed outside any lane
                    self.confirmed_assignments.pop(track_id, None)

            # Assign to current frame occupancy based on confirmed or immediate assignment
            confirmed_lane = self.confirmed_assignments.get(track_id)
            # If persistence_threshold == 1, confirmed immediately
            if self.persistence_threshold == 1 and current_raw_lane_id is not None:
                confirmed_lane = current_raw_lane_id
                self.lane_unique_tracks[confirmed_lane].add(track_id)

            if confirmed_lane and confirmed_lane in frame_lane_occupants:
                frame_lane_occupants[confirmed_lane].append(obj)

        # Record occupancy counts for this frame
        for lane_id, occupants in frame_lane_occupants.items():
            self.lane_occupancy_history[lane_id].append(len(occupants))

        return frame_lane_occupants

    def compute_summaries(self) -> List[PerLaneSummary]:
        """
        Computes the final PerLaneSummary for each configured lane region.
        """
        summaries: List[PerLaneSummary] = []

        for lane in self.lanes:
            lane_id = lane.lane_id
            unique_tracks = self.lane_unique_tracks[lane_id]
            total_unique = len(unique_tracks)

            # Class count breakdown
            class_counts: Dict[str, int] = {
                cls_name: 0 for cls_name in DEFAULT_VEHICLE_CLASSES
            }
            for tid in unique_tracks:
                cls_name = self.track_classes.get(tid, "car")
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

            # Image-space density: total_unique_vehicles / polygon_area_px2
            area = max(1e-6, lane.area_px2)
            density_px2 = total_unique / area

            # Normalized density score: min(1.0, count / (area / REFERENCE_CELL_AREA_PX2))
            ref_capacity = max(1e-6, area / REFERENCE_CELL_AREA_PX2)
            normalized_score = min(1.0, max(0.0, total_unique / ref_capacity))

            # Occupancy statistics
            occupancy_hist = self.lane_occupancy_history.get(lane_id, [])
            peak_occ = max(occupancy_hist) if occupancy_hist else 0
            avg_occ = (
                sum(occupancy_hist) / len(occupancy_hist) if occupancy_hist else 0.0
            )

            summary = PerLaneSummary(
                lane_id=lane.lane_id,
                lane_name=lane.name,
                polygon=lane.polygon,
                polygon_area_px2=round(lane.area_px2, 2),
                total_unique_vehicles=total_unique,
                vehicle_class_counts=class_counts,
                direction_hint=lane.direction_hint,
                image_space_density_vehicles_per_px2=round(density_px2, 8),
                normalized_density_score=round(normalized_score, 4),
                density_unit="vehicles/px²",
                density_formula="total_unique_vehicles / polygon_area_px2 (image-space uncalibrated)",
                peak_occupancy=peak_occ,
                average_occupancy=round(avg_occ, 2),
            )
            summaries.append(summary)

        return summaries


class LaneAnalyzer:
    """
    Stateless service executing lane assignment and density estimation.
    """

    def __init__(self, persistence_threshold: int = 2):
        self.persistence_threshold = max(1, int(persistence_threshold))

    def analyze(
        self,
        tracking_output: VideoTrackingOutput,
        lanes: List[LaneRegion],
        video_id: Optional[str] = None,
        original_filename: Optional[str] = None,
        processing_time_ms: float = 0.0,
    ) -> LaneAnalyticsResult:
        """
        Executes lane assignment across all frames in VideoTrackingOutput.
        
        Args:
            tracking_output: Aggregated tracking output from ByteTrackVehicleTracker.
            lanes: List of validated LaneRegion configurations.
            video_id: Video identifier.
            original_filename: Ingested file name.
            processing_time_ms: Upstream execution duration to include.
            
        Returns:
            LaneAnalyticsResult with per-lane summaries, density, and unassigned vehicle counts.
        """
        start_time = time.perf_counter()

        if len(lanes) > MAX_LANES_PER_REQUEST:
            raise AppException(
                f"Exceeded maximum allowed lanes ({MAX_LANES_PER_REQUEST}), got {len(lanes)}.",
                status_code=422,
            )

        # Validate unique lane IDs
        lane_ids = [l.lane_id for l in lanes]
        if len(lane_ids) != len(set(lane_ids)):
            raise AppException(
                "Duplicate lane IDs detected in request.",
                status_code=422,
            )

        # Validate individual lane regions
        validated_lanes: List[LaneRegion] = []
        for lane in lanes:
            area = validate_lane_polygon(lane.lane_id, lane.name, lane.polygon)
            validated_lanes.append(
                LaneRegion(
                    lane_id=lane.lane_id,
                    name=lane.name,
                    polygon=lane.polygon,
                    direction_hint=lane.direction_hint,
                    area_px2=area,
                )
            )

        # Run stateful assignment engine across frames
        engine = LaneAssignmentEngine(
            lanes=validated_lanes,
            persistence_threshold=self.persistence_threshold,
        )

        for frame in tracking_output.frames:
            engine.process_frame(
                frame_index=frame.frame_index,
                tracked_objects=frame.tracked_objects,
            )

        summaries = engine.compute_summaries()

        # Compute unassigned vehicles count
        assigned_track_ids: Set[int] = set()
        for lane_tracks in engine.lane_unique_tracks.values():
            assigned_track_ids.update(lane_tracks)

        unassigned_count = max(
            0, len(engine.all_seen_tracks) - len(assigned_track_ids)
        )

        total_proc_ms = processing_time_ms + (
            (time.perf_counter() - start_time) * 1000.0
        )

        # Calculate observation duration
        obs_duration = 0.0
        if tracking_output.frames:
            timestamps = [f.timestamp_seconds for f in tracking_output.frames]
            obs_duration = max(0.0, max(timestamps) - min(timestamps))
            if obs_duration == 0.0 and len(tracking_output.frames) > 1:
                # Estimate from frame count if timestamps identical
                obs_duration = len(tracking_output.frames) / 30.0

        return LaneAnalyticsResult(
            video_id=video_id,
            original_filename=original_filename,
            pipeline_stage="lane-analysis-run",
            observation_duration_seconds=round(obs_duration, 2),
            total_frames_processed=tracking_output.total_frames_processed,
            total_unique_tracks=tracking_output.total_unique_tracks,
            lanes=summaries,
            unassigned_vehicles_count=unassigned_count,
            density_calibration_warning=(
                "Image-space density is not equivalent to vehicles/km² without camera calibration."
            ),
            directional_metrics_omitted_reason=(
                "Directional per-lane metrics omitted: tripwire crossing events are decoupled from lane polygons in this phase."
            ),
            processing_time_ms=round(total_proc_ms, 2),
        )
