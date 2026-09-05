"""
Detection API endpoints: /api/v1/detection.

Handles:
- POST /api/v1/detection/videos/{video_id} — Run YOLO vehicle detection on an uploaded video
- GET  /api/v1/detection/info — Inspect active YOLO detector properties and class labels
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.video import Video
from app.schemas.detection import (
    BoundingBoxSchema,
    DetectionItem,
    DetectionRequest,
    FrameDetectionResult,
    ModelInfoResponse,
    VideoDetectionResponse,
)
from app.services.cv.detector import YOLOVehicleDetector
from app.services.cv.video_source import VideoSource

router = APIRouter()
logger = get_logger(__name__)

# Module-level singleton detector instance for efficiency
_detector_instance: Optional[YOLOVehicleDetector] = None


def get_detector() -> YOLOVehicleDetector:
    """Returns a singleton YOLOVehicleDetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = YOLOVehicleDetector()
    return _detector_instance


@router.get(
    "/info",
    response_model=ModelInfoResponse,
    summary="Get active YOLO detector information",
    description="Returns metadata about the active detection model, device, default confidence threshold, and supported class labels.",
)
def get_model_info(
    detector: YOLOVehicleDetector = Depends(get_detector),
) -> ModelInfoResponse:
    return ModelInfoResponse(
        model_name=detector.model_name,
        device=detector.device,
        confidence_threshold=detector.confidence_threshold,
        target_classes=sorted(list(detector.target_classes)),
        supported_classes=detector.all_model_classes,
    )


@router.post(
    "/videos/{video_id}",
    response_model=VideoDetectionResponse,
    summary="Run YOLO vehicle detection on an ingested video",
    description=(
        "Executes YOLO inference against frames decoded from an uploaded video at a controlled sample rate. "
        "Returns structured vehicle detections (class, confidence, bounding box, frame index, timestamp). "
        "Strictly excludes server filesystem paths."
    ),
)
def detect_video(
    video_id: str,
    request_params: Optional[DetectionRequest] = None,
    db: Session = Depends(get_db),
    detector: YOLOVehicleDetector = Depends(get_detector),
) -> VideoDetectionResponse:
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
    req = request_params or DetectionRequest()
    confidence = req.confidence_threshold or detector.confidence_threshold
    max_frames = req.max_frames or 50
    target_fps = req.target_fps or settings.processing_fps
    target_classes = set(req.target_classes) if req.target_classes else detector.target_classes

    # Create temporary detector instance if custom confidence/classes requested
    active_detector = detector
    if confidence != detector.confidence_threshold or target_classes != detector.target_classes:
        active_detector = YOLOVehicleDetector(
            confidence_threshold=confidence,
            target_classes=target_classes,
        )

    # 4. Open VideoSource and run inference
    logger.info("Starting detection inference on video %s (max_frames=%s, fps=%s, conf=%.2f)", video.id, max_frames, target_fps, confidence)
    with VideoSource(storage_path) as source:
        detection_output = active_detector.detect_video(
            video_source=source,
            max_frames=max_frames,
            target_fps=target_fps,
        )

    # 5. Build structured response
    frames_schema: list[FrameDetectionResult] = []
    for f in detection_output.frames:
        items = [
            DetectionItem(
                class_id=d.class_id,
                class_name=d.class_name,
                confidence=d.confidence,
                bbox=BoundingBoxSchema(
                    x1=d.bbox.x1,
                    y1=d.bbox.y1,
                    x2=d.bbox.x2,
                    y2=d.bbox.y2,
                    width=d.bbox.width,
                    height=d.bbox.height,
                ),
                frame_index=d.frame_index,
                timestamp_seconds=d.timestamp_seconds,
            )
            for d in f.detections
        ]
        frames_schema.append(
            FrameDetectionResult(
                frame_index=f.frame_index,
                timestamp_seconds=f.timestamp_seconds,
                detections=items,
                vehicle_count=f.vehicle_count,
            )
        )

    logger.info(
        "Completed detection on video %s: %d detections across %d frames in %.1fms",
        video.id,
        detection_output.total_detections_count,
        detection_output.total_frames_processed,
        detection_output.processing_time_ms,
    )

    return VideoDetectionResponse(
        video_id=video.id,
        original_filename=video.original_filename,
        pipeline_stage="detections-run",
        model_name=active_detector.model_name,
        confidence_threshold=confidence,
        target_fps=target_fps,
        total_frames_processed=detection_output.total_frames_processed,
        total_detections_count=detection_output.total_detections_count,
        detections_by_class=detection_output.detections_by_class,
        frames=frames_schema,
        processing_time_ms=detection_output.processing_time_ms,
        preview_frame_base64=detection_output.annotated_preview_base64,
    )
