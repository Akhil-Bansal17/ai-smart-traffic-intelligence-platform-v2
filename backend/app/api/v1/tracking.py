"""
Tracking API endpoints: /api/v1/tracking.

Handles:
- POST /api/v1/tracking/videos/{video_id} — Run YOLO detection and ByteTrack object tracking on an ingested video
- GET  /api/v1/tracking/info — Inspect active tracking algorithm properties and lifecycle transitions
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.detection import get_detector
from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.video import Video
from app.schemas.detection import BoundingBoxSchema
from app.schemas.tracking import (
    FrameTrackingResultSchema,
    TrackedItem,
    TrackerInfoResponse,
    TrackingRequest,
    VideoTrackingResponse,
)
from app.services.cv.detector import YOLOVehicleDetector
from app.services.cv.tracker import ByteTrackVehicleTracker
from app.services.cv.video_source import VideoSource

router = APIRouter()
logger = get_logger(__name__)

# Module-level singleton tracker instance
_tracker_instance: Optional[ByteTrackVehicleTracker] = None


def get_tracker() -> ByteTrackVehicleTracker:
    """Returns a singleton ByteTrackVehicleTracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ByteTrackVehicleTracker()
    return _tracker_instance


@router.get(
    "/info",
    response_model=TrackerInfoResponse,
    summary="Get active object tracker information",
    description="Returns configuration parameters and lifecycle state machine description for the active multi-object tracker.",
)
def get_tracker_info(
    tracker: ByteTrackVehicleTracker = Depends(get_tracker),
) -> TrackerInfoResponse:
    return TrackerInfoResponse(
        tracker_name=tracker.tracker_name,
        iou_threshold=tracker.iou_threshold,
        max_lost_frames=tracker.max_lost_frames,
        track_lifecycle={
            "new": "Initial state upon first detection appearance",
            "active": "Confirmed and actively matched in the current frame",
            "lost": "Temporarily missed in current frame (retained for up to max_lost_frames)",
            "terminated": "Unmatched for > max_lost_frames; track identity retired to prevent stale ID resurrection",
        },
    )


@router.post(
    "/videos/{video_id}",
    response_model=VideoTrackingResponse,
    summary="Run object tracking on an ingested video",
    description=(
        "Executes YOLO vehicle detection and Kalman-filter/IoU multi-object tracking across frames decoded from an uploaded video. "
        "Associates detections across consecutive frames, assigning persistent track IDs to vehicles over time. "
        "Strictly excludes server filesystem paths."
    ),
)
def track_video(
    video_id: str,
    request_params: Optional[TrackingRequest] = None,
    db: Session = Depends(get_db),
    detector: YOLOVehicleDetector = Depends(get_detector),
    tracker: ByteTrackVehicleTracker = Depends(get_tracker),
) -> VideoTrackingResponse:
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
    req = request_params or TrackingRequest()
    confidence = req.confidence_threshold or detector.confidence_threshold
    max_frames = req.max_frames or 50
    target_fps = req.target_fps or settings.processing_fps
    iou_thresh = req.iou_threshold or tracker.iou_threshold
    max_lost = req.max_lost_frames or tracker.max_lost_frames

    # Instantiate specialized detector/tracker if custom parameters requested
    active_detector = detector
    if confidence != detector.confidence_threshold:
        active_detector = YOLOVehicleDetector(confidence_threshold=confidence)

    active_tracker = tracker
    if iou_thresh != tracker.iou_threshold or max_lost != tracker.max_lost_frames:
        active_tracker = ByteTrackVehicleTracker(
            iou_threshold=iou_thresh,
            max_lost_frames=max_lost,
        )
    else:
        active_tracker.reset()

    # 4. Open VideoSource and run tracking pipeline
    logger.info(
        "Starting tracking on video %s (max_frames=%s, fps=%s, conf=%.2f, iou=%.2f, max_lost=%d)",
        video.id, max_frames, target_fps, confidence, iou_thresh, max_lost,
    )
    with VideoSource(storage_path) as source:
        tracking_output = active_tracker.track_video(
            video_source=source,
            detector=active_detector,
            max_frames=max_frames,
            target_fps=target_fps,
        )

    # 5. Build structured response
    frames_schema: list[FrameTrackingResultSchema] = []
    for f in tracking_output.frames:
        items = [
            TrackedItem(
                track_id=obj.track_id,
                class_id=obj.class_id,
                class_name=obj.class_name,
                confidence=obj.confidence,
                bbox=BoundingBoxSchema(
                    x1=obj.bbox.x1,
                    y1=obj.bbox.y1,
                    x2=obj.bbox.x2,
                    y2=obj.bbox.y2,
                    width=obj.bbox.width,
                    height=obj.bbox.height,
                ),
                frame_index=obj.frame_index,
                timestamp_seconds=obj.timestamp_seconds,
                state=obj.state.value if hasattr(obj.state, "value") else str(obj.state),
                age_frames=obj.age_frames,
                hits=obj.hits,
            )
            for obj in f.tracked_objects
        ]
        frames_schema.append(
            FrameTrackingResultSchema(
                frame_index=f.frame_index,
                timestamp_seconds=f.timestamp_seconds,
                tracked_objects=items,
                active_tracks_count=f.active_tracks_count,
            )
        )

    logger.info(
        "Completed tracking on video %s: %d unique tracks (%d total detections) across %d frames in %.1fms",
        video.id,
        tracking_output.total_unique_tracks,
        tracking_output.total_detections_count,
        tracking_output.total_frames_processed,
        tracking_output.processing_time_ms,
    )

    return VideoTrackingResponse(
        video_id=video.id,
        original_filename=video.original_filename,
        pipeline_stage="tracking-run",
        detector_model=active_detector.model_name,
        tracker_name=active_tracker.tracker_name,
        confidence_threshold=confidence,
        target_fps=target_fps,
        total_frames_processed=tracking_output.total_frames_processed,
        total_detections_count=tracking_output.total_detections_count,
        total_unique_tracks=tracking_output.total_unique_tracks,
        tracks_by_class=tracking_output.tracks_by_class,
        frames=frames_schema,
        processing_time_ms=tracking_output.processing_time_ms,
        preview_frame_base64=tracking_output.annotated_preview_base64,
    )
