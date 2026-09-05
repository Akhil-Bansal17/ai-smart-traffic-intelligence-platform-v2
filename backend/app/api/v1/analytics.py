"""
Traffic Analytics & Flow Metrics API endpoints: /api/v1/analytics.

Handles:
- POST /api/v1/analytics/videos/{video_id} — Run end-to-end detection, tracking, counting, and compute traffic metrics
- GET  /api/v1/analytics/info — Inspect active metrics calculation formulas and extrapolation transparency policy
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.counting import get_counter
from app.api.v1.detection import get_detector
from app.api.v1.tracking import get_tracker
from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.video import Video
from app.schemas.analytics import (
    AnalyticsInfoResponse,
    AnalyticsRequest,
    ClassMetricItem,
    DirectionMetricItem,
    TimeSeriesBucketSchema,
    TrafficMetricsResponse,
)
from app.services.cv.detector import YOLOVehicleDetector
from app.services.cv.tracker import ByteTrackVehicleTracker
from app.services.cv.traffic_metrics_engine import TrafficMetricsEngine
from app.services.cv.vehicle_counter import CountingLine, LineCrossingCounter, Point2D
from app.services.cv.video_source import VideoSource

router = APIRouter()
logger = get_logger(__name__)

# Module-level singleton engine instance
_engine_instance: Optional[TrafficMetricsEngine] = None


def get_analytics_engine() -> TrafficMetricsEngine:
    """Returns a singleton TrafficMetricsEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TrafficMetricsEngine()
    return _engine_instance


@router.get(
    "/info",
    response_model=AnalyticsInfoResponse,
    summary="Get traffic analytics formulas and definitions",
    description="Returns mathematical formulas, metric definitions, and data honesty extrapolation policies.",
)
def get_analytics_info() -> AnalyticsInfoResponse:
    return AnalyticsInfoResponse(
        engine_name="TrafficMetricsEngine",
        metric_definitions={
            "observation_duration_seconds": "Actual processed video duration (frames_evaluated / fps)",
            "total_vehicles": "Deduplicated unique vehicle track IDs crossing virtual tripwire",
            "flow_rate_per_minute": "total_vehicles / (observation_duration_seconds / 60.0)",
            "flow_rate_per_hour_extrapolated": "total_vehicles / (observation_duration_seconds / 3600.0)",
            "class_percentage": "(class_count / total_vehicles) * 100.0",
            "inbound_percentage": "(inbound_count / total_vehicles) * 100.0",
            "outbound_percentage": "(outbound_count / total_vehicles) * 100.0",
            "time_series_buckets": "Non-interpolated discrete vehicle counts grouped by [k*dt, (k+1)*dt)",
        },
        extrapolation_policy=(
            "Hourly flow rates derived from short video clips are explicitly flagged with is_extrapolated=True "
            "and labeled as ESTIMATED in API and UI alongside the underlying observation duration."
        ),
    )


@router.post(
    "/videos/{video_id}",
    response_model=TrafficMetricsResponse,
    summary="Compute traffic flow analytics on an ingested video",
    description=(
        "Executes the full CV pipeline (VideoSource -> Detector -> Tracker -> VehicleCounter -> TrafficMetricsEngine). "
        "Calculates volume, flow rates, class breakdown, directional flow, and time-series volume distribution "
        "strictly from genuine tracking and crossing events without leaking server storage paths."
    ),
)
def analyze_video_traffic(
    video_id: str,
    request_params: Optional[AnalyticsRequest] = None,
    db: Session = Depends(get_db),
    detector: YOLOVehicleDetector = Depends(get_detector),
    tracker: ByteTrackVehicleTracker = Depends(get_tracker),
    counter: LineCrossingCounter = Depends(get_counter),
    engine: TrafficMetricsEngine = Depends(get_analytics_engine),
) -> TrafficMetricsResponse:
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
    req = request_params or AnalyticsRequest()
    confidence = req.confidence_threshold or detector.confidence_threshold
    max_frames = req.max_frames or 50
    target_fps = req.target_fps or settings.processing_fps
    iou_thresh = req.iou_threshold or tracker.iou_threshold
    time_bucket_sec = req.time_bucket_seconds or 5.0

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

    # Configure active counting line
    active_line = counter.line
    if req.counting_line is not None:
        active_line = CountingLine(
            p1=Point2D(x=req.counting_line.p1.x, y=req.counting_line.p1.y),
            p2=Point2D(x=req.counting_line.p2.x, y=req.counting_line.p2.y),
            label=req.counting_line.label or "custom_tripwire",
            direction_a_to_b=req.counting_line.direction_a_to_b or "inbound",
            direction_b_to_a=req.counting_line.direction_b_to_a or "outbound",
            min_movement_px=req.counting_line.min_movement_px or 2.0,
        )
    active_counter = LineCrossingCounter(line=active_line)

    # 4. Open VideoSource and run analytics pipeline
    logger.info(
        "Starting traffic analytics on video %s (max_frames=%s, fps=%s, conf=%.2f, iou=%.2f, bucket=%.1fs)",
        video.id, max_frames, target_fps, confidence, iou_thresh, time_bucket_sec,
    )

    with VideoSource(storage_path) as source:
        result = engine.analyze_video(
            video_source=source,
            detector=active_detector,
            tracker=active_tracker,
            counter=active_counter,
            max_frames=max_frames,
            target_fps=target_fps,
            time_bucket_seconds=time_bucket_sec,
            video_id=video.id,
            original_filename=video.original_filename,
        )

    # 5. Build structured response
    class_items = [
        ClassMetricItem(
            class_name=m.class_name,
            count=m.count,
            percentage=m.percentage,
        )
        for m in result.class_distribution
    ]

    dir_items = [
        DirectionMetricItem(
            direction=m.direction,
            count=m.count,
            percentage=m.percentage,
        )
        for m in result.directional_distribution
    ]

    bucket_items = [
        TimeSeriesBucketSchema(
            bucket_index=b.bucket_index,
            start_time_seconds=b.start_time_seconds,
            end_time_seconds=b.end_time_seconds,
            vehicle_count=b.vehicle_count,
            class_counts=b.class_counts,
            inbound_count=b.inbound_count,
            outbound_count=b.outbound_count,
        )
        for b in result.time_series
    ]

    return TrafficMetricsResponse(
        video_id=video.id,
        original_filename=video.original_filename,
        pipeline_stage="analytics-run",
        observation_duration_seconds=result.observation_duration_seconds,
        total_vehicles=result.total_vehicles,
        flow_rate_per_minute=result.flow_rate_per_minute,
        flow_rate_per_hour_extrapolated=result.flow_rate_per_hour_extrapolated,
        is_extrapolated=result.is_extrapolated,
        inbound_count=result.inbound_count,
        outbound_count=result.outbound_count,
        inbound_percentage=result.inbound_percentage,
        outbound_percentage=result.outbound_percentage,
        class_distribution=class_items,
        directional_distribution=dir_items,
        time_series=bucket_items,
        total_frames_processed=result.total_frames_processed,
        total_detections=result.total_detections,
        unique_tracks=result.unique_tracks,
        counting_line_label=result.counting_line_label,
        processing_time_ms=result.processing_time_ms,
        generated_at=result.generated_at,
    )
