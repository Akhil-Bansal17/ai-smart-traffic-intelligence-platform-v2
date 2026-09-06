"""
Lane Analysis & Density Estimation API endpoints: /api/v1/lane-analysis.

Handles:
- POST /api/v1/lane-analysis/videos/{video_id} — Run detection, tracking, and configured lane assignment/density analysis
- GET  /api/v1/lane-analysis/info — Inspect active lane assignment methods and density calculation policies
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.detection import get_detector
from app.api.v1.tracking import get_tracker
from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.video import Video
from app.schemas.lane_analysis import (
    LaneAnalysisInfoResponse,
    LaneAnalysisRequest,
    LaneAnalyticsResponse,
    PerLaneSummarySchema,
)
from app.services.cv.detector import YOLOVehicleDetector
from app.services.cv.lane_analyzer import LaneAnalyzer, LaneRegion
from app.services.cv.tracker import ByteTrackVehicleTracker
from app.services.cv.video_source import VideoSource

router = APIRouter()
logger = get_logger(__name__)

# Module-level singleton analyzer instance
_analyzer_instance: Optional[LaneAnalyzer] = None


def get_lane_analyzer() -> LaneAnalyzer:
    """Returns a singleton LaneAnalyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = LaneAnalyzer(persistence_threshold=2)
    return _analyzer_instance


@router.get(
    "/info",
    response_model=LaneAnalysisInfoResponse,
    summary="Get lane analysis algorithms and definitions",
    description="Returns lane assignment rules, point-in-polygon algorithm details, and density calibration transparency policies.",
)
def get_lane_analysis_info() -> LaneAnalysisInfoResponse:
    return LaneAnalysisInfoResponse(
        service_name="LaneAnalyzer",
        assignment_method="Centroid ray-casting point-in-polygon with N-frame temporal persistence threshold",
        density_definition="Image-space density = total_unique_vehicles / shoelace_polygon_area_px2 (vehicles/px²)",
        calibration_policy=(
            "Image-space density is strictly pixel-space and is not equivalent to physical density "
            "(vehicles/km²) without homography or camera calibration matrices."
        ),
        directional_policy=(
            "Directional metrics per lane are omitted because line-crossing events are decoupled from "
            "polygonal lane zones in Phase 9."
        ),
    )


@router.post(
    "/videos/{video_id}",
    response_model=LaneAnalyticsResponse,
    summary="Execute lane assignment and density analysis on an ingested video",
    description=(
        "Executes the CV pipeline (VideoSource -> Detector -> Tracker -> LaneAnalyzer). "
        "Assigns tracked vehicles to user-defined polygonal lane zones, computing volume, class distribution, "
        "and image-space density without leaking server storage paths."
    ),
)
def analyze_video_lanes(
    video_id: str,
    request_params: LaneAnalysisRequest,
    db: Session = Depends(get_db),
    detector: YOLOVehicleDetector = Depends(get_detector),
    tracker: ByteTrackVehicleTracker = Depends(get_tracker),
    analyzer: LaneAnalyzer = Depends(get_lane_analyzer),
) -> LaneAnalyticsResponse:
    # 1. Fetch video record from DB
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise AppException(
            f"Video with ID '{video_id}' not found.",
            code="video_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 2. Check storage path existence
    storage_path = Path(video.storage_path)
    if not storage_path.exists():
        raise AppException(
            "Underlying video file is missing from storage.",
            code="file_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 3. Resolve parameters
    req = request_params
    confidence = req.confidence_threshold or detector.confidence_threshold
    max_frames = req.max_frames or 50
    target_fps = req.target_fps or settings.processing_fps
    iou_thresh = req.iou_threshold or tracker.iou_threshold
    persistence = req.persistence_threshold or 2

    # Configure active detector
    active_detector = detector
    if confidence != detector.confidence_threshold:
        active_detector = YOLOVehicleDetector(confidence_threshold=confidence)

    # Configure active tracker
    active_tracker = tracker
    if iou_thresh != tracker.iou_threshold:
        active_tracker = ByteTrackVehicleTracker(iou_threshold=iou_thresh)
    else:
        active_tracker.reset()

    # Configure active analyzer
    active_analyzer = LaneAnalyzer(persistence_threshold=persistence)

    # Convert request lanes to domain LaneRegion objects
    lane_regions = [
        LaneRegion(
            lane_id=l.lane_id,
            name=l.name,
            polygon=[(float(p[0]), float(p[1])) for p in l.polygon],
            direction_hint=l.direction_hint,
        )
        for l in req.lanes
    ]

    # 4. Open VideoSource and run detection & tracking
    logger.info(
        "Starting lane analysis on video %s (%d lanes, max_frames=%s, fps=%s, conf=%.2f, iou=%.2f, persistence=%d)",
        video.id, len(lane_regions), max_frames, target_fps, confidence, iou_thresh, persistence,
    )

    with VideoSource(storage_path) as source:
        tracking_output = active_tracker.track_video(
            video_source=source,
            detector=active_detector,
            max_frames=max_frames,
            target_fps=target_fps,
        )

    # 5. Execute lane analysis
    result = active_analyzer.analyze(
        tracking_output=tracking_output,
        lanes=lane_regions,
        video_id=video.id,
        original_filename=video.original_filename,
        processing_time_ms=tracking_output.processing_time_ms,
    )

    # 6. Build structured response
    per_lane_schemas = [
        PerLaneSummarySchema(
            lane_id=s.lane_id,
            lane_name=s.lane_name,
            polygon=[[float(p[0]), float(p[1])] for p in s.polygon],
            polygon_area_px2=s.polygon_area_px2,
            total_unique_vehicles=s.total_unique_vehicles,
            vehicle_class_counts=s.vehicle_class_counts,
            direction_hint=s.direction_hint,
            image_space_density_vehicles_per_px2=s.image_space_density_vehicles_per_px2,
            normalized_density_score=s.normalized_density_score,
            density_unit=s.density_unit,
            density_formula=s.density_formula,
            peak_occupancy=s.peak_occupancy,
            average_occupancy=s.average_occupancy,
        )
        for s in result.lanes
    ]

    return LaneAnalyticsResponse(
        video_id=video.id,
        original_filename=video.original_filename,
        pipeline_stage="lane-analysis-run",
        observation_duration_seconds=result.observation_duration_seconds,
        total_frames_processed=result.total_frames_processed,
        total_unique_tracks=result.total_unique_tracks,
        lanes=per_lane_schemas,
        unassigned_vehicles_count=result.unassigned_vehicles_count,
        density_calibration_warning=result.density_calibration_warning,
        directional_metrics_omitted_reason=result.directional_metrics_omitted_reason,
        processing_time_ms=result.processing_time_ms,
        generated_at=result.generated_at,
    )
