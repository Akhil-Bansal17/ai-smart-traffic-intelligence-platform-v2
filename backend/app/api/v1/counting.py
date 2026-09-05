"""
Vehicle Counting API endpoints: /api/v1/counting.

Handles:
- POST /api/v1/counting/videos/{video_id} — Run detection, tracking, and line-crossing vehicle counting on an ingested video
- GET  /api/v1/counting/info — Inspect active counting algorithm, default virtual tripwire, and mathematical semantics
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
from app.schemas.counting import (
    CountingInfoResponse,
    CountingLineSchema,
    CountingRequest,
    CrossingEventSchema,
    FrameCountingResultSchema,
    Point2DSchema,
    VideoCountingResponse,
)
from app.services.cv.detector import YOLOVehicleDetector
from app.services.cv.tracker import ByteTrackVehicleTracker
from app.services.cv.vehicle_counter import CountingLine, LineCrossingCounter, Point2D
from app.services.cv.video_source import VideoSource

router = APIRouter()
logger = get_logger(__name__)

# Module-level singleton counter instance
_counter_instance: Optional[LineCrossingCounter] = None


def get_counter() -> LineCrossingCounter:
    """Returns a singleton LineCrossingCounter instance with default settings."""
    global _counter_instance
    if _counter_instance is None:
        _counter_instance = LineCrossingCounter()
    return _counter_instance


@router.get(
    "/info",
    response_model=CountingInfoResponse,
    summary="Get active vehicle counting configuration",
    description="Returns configuration parameters, default tripwire coordinates, and mathematical crossing semantics.",
)
def get_counting_info(
    counter: LineCrossingCounter = Depends(get_counter),
) -> CountingInfoResponse:
    line = counter.line
    return CountingInfoResponse(
        counter_name="LineCrossingCounter",
        default_line=CountingLineSchema(
            p1=Point2DSchema(x=line.p1.x, y=line.p1.y),
            p2=Point2DSchema(x=line.p2.x, y=line.p2.y),
            label=line.label,
            direction_a_to_b=line.direction_a_to_b,
            direction_b_to_a=line.direction_b_to_a,
            min_movement_px=line.min_movement_px,
        ),
        crossing_semantics=(
            "Mathematical 2D signed cross-product transition test with line segment intersection. "
            "Track IDs are deduplicated strictly so each unique vehicle trajectory is counted at most once."
        ),
        direction_rules={
            line.direction_a_to_b: "Trajectory transitioned from Side A (cross > 0) to Side B (cross < 0)",
            line.direction_b_to_a: "Trajectory transitioned from Side B (cross < 0) to Side A (cross > 0)",
        },
    )


@router.post(
    "/videos/{video_id}",
    response_model=VideoCountingResponse,
    summary="Run vehicle counting on an ingested video",
    description=(
        "Executes the full pipeline: VideoSource -> Detector -> Tracker -> LineCrossingCounter. "
        "Evaluates tracked vehicle trajectories against a virtual counting line, producing deduplicated "
        "counts by class and direction without leaking server storage paths."
    ),
)
def count_video(
    video_id: str,
    request_params: Optional[CountingRequest] = None,
    db: Session = Depends(get_db),
    detector: YOLOVehicleDetector = Depends(get_detector),
    tracker: ByteTrackVehicleTracker = Depends(get_tracker),
    counter: LineCrossingCounter = Depends(get_counter),
) -> VideoCountingResponse:
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
    req = request_params or CountingRequest()
    confidence = req.confidence_threshold or detector.confidence_threshold
    max_frames = req.max_frames or 50
    target_fps = req.target_fps or settings.processing_fps
    iou_thresh = req.iou_threshold or tracker.iou_threshold

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

    # 4. Open VideoSource and run full pipeline
    logger.info(
        "Starting vehicle counting on video %s (max_frames=%s, fps=%s, conf=%.2f, iou=%.2f, line=%s)",
        video.id, max_frames, target_fps, confidence, iou_thresh, active_line.label,
    )

    with VideoSource(storage_path) as source:
        counting_output = active_counter.count_video(
            video_source=source,
            detector=active_detector,
            tracker=active_tracker,
            max_frames=max_frames,
            target_fps=target_fps,
            video_id=video.id,
            original_filename=video.original_filename,
        )

    # 5. Build structured response
    frames_schema: list[FrameCountingResultSchema] = []
    for f in counting_output.frames:
        events = [
            CrossingEventSchema(
                track_id=e.track_id,
                class_name=e.class_name,
                frame_index=e.frame_index,
                timestamp_seconds=e.timestamp_seconds,
                direction=e.direction,
                crossing_point=e.crossing_point,
                line_label=e.line_label,
            )
            for e in f.new_crossings
        ]
        frames_schema.append(
            FrameCountingResultSchema(
                frame_index=f.frame_index,
                timestamp_seconds=f.timestamp_seconds,
                active_tracks_count=f.active_tracks_count,
                new_crossings=events,
            )
        )

    all_events_schema = [
        CrossingEventSchema(
            track_id=e.track_id,
            class_name=e.class_name,
            frame_index=e.frame_index,
            timestamp_seconds=e.timestamp_seconds,
            direction=e.direction,
            crossing_point=e.crossing_point,
            line_label=e.line_label,
        )
        for e in counting_output.crossing_events
    ]

    line_schema = CountingLineSchema(
        p1=Point2DSchema(x=active_line.p1.x, y=active_line.p1.y),
        p2=Point2DSchema(x=active_line.p2.x, y=active_line.p2.y),
        label=active_line.label,
        direction_a_to_b=active_line.direction_a_to_b,
        direction_b_to_a=active_line.direction_b_to_a,
        min_movement_px=active_line.min_movement_px,
    )

    logger.info(
        "Completed counting on video %s: %d total vehicles counted (%s) in %.1fms",
        video.id,
        counting_output.total_counted_vehicles,
        counting_output.counts_by_class,
        counting_output.processing_time_ms,
    )

    return VideoCountingResponse(
        video_id=video.id,
        original_filename=video.original_filename,
        pipeline_stage="counting-run",
        detector_model=active_detector.model_name,
        tracker_name=active_tracker.tracker_name,
        counting_line=line_schema,
        total_frames_processed=counting_output.total_frames_processed,
        total_detections_count=counting_output.total_detections_count,
        total_unique_tracks=counting_output.total_unique_tracks,
        total_counted_vehicles=counting_output.total_counted_vehicles,
        counts_by_class=counting_output.counts_by_class,
        counts_by_direction=counting_output.counts_by_direction,
        counted_track_ids=counting_output.counted_track_ids,
        crossing_events=all_events_schema,
        frames=frames_schema,
        processing_time_ms=counting_output.processing_time_ms,
        preview_frame_base64=counting_output.annotated_preview_base64,
    )
