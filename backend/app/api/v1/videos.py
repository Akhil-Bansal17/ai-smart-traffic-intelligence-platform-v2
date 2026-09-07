"""
Video ingestion and metadata endpoints: /api/v1/videos.

Handles:
- POST /api/v1/videos/upload — Upload, validate, extract metadata, and persist
- GET /api/v1/videos/{video_id} — Retrieve video record and metadata
- GET /api/v1/videos — List all uploaded videos
"""
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from typing import Optional
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.video import Video
from app.schemas.video import VideoListResponse, VideoResponse, VideoUploadResponse
from app.services.cv.video_source import VideoSource
from app.services.cv.video_validator import save_and_validate_upload

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a traffic video",
    description=(
        "Uploads a traffic video file (.mp4, .avi, .mov), validates file format and readability, "
        "extracts video metadata (resolution, fps, duration, frame count), and records the video in the database."
    ),
)
async def upload_video(
    file: UploadFile = File(...),
    source_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> VideoUploadResponse:
    # Step 1: Save upload with streaming size & magic-byte validation
    original_name, dest_path, _ = await save_and_validate_upload(file)

    try:
        # Step 2: Content-level validation & metadata extraction
        with VideoSource(dest_path) as source:
            metadata = source.read_metadata()

        # Step 3: Determine provenance classification
        lower_name = original_name.lower()
        if source_type:
            resolved_source = source_type
        elif any(k in lower_name for k in ("test_", "synthetic", "fixture", "clip_", "camera_stream", "live_test")):
            resolved_source = "synthetic_test"
        else:
            resolved_source = "real_world"

        # Step 4: Persist record in database
        video = Video(
            original_filename=original_name,
            storage_path=str(dest_path),
            duration_seconds=metadata.duration_seconds,
            fps=metadata.fps,
            resolution=metadata.resolution,
            frame_count=metadata.frame_count,
            source_type=resolved_source,
            status="uploaded",
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        logger.info("Successfully ingested video '%s' (ID: %s, %s, %s FPS, source: %s)", original_name, video.id, metadata.resolution, metadata.fps, resolved_source)
        return VideoUploadResponse.model_validate(video)

    except Exception:
        # Clean up storage file on metadata/DB failure
        if dest_path.exists():
            try:
                dest_path.unlink()
                logger.debug("Cleaned up file after ingestion error: %s", dest_path.name)
            except OSError as err:
                logger.warning("Failed to clean up file %s: %s", dest_path.name, err)
        raise


@router.get(
    "/{video_id}",
    response_model=VideoResponse,
    summary="Get video metadata by ID",
)
def get_video(
    video_id: str,
    db: Session = Depends(get_db),
) -> VideoResponse:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise AppException(
            f"Video with ID '{video_id}' not found.",
            code="video_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return VideoResponse.model_validate(video)


@router.get(
    "",
    response_model=VideoListResponse,
    summary="List all uploaded videos",
)
def list_videos(
    db: Session = Depends(get_db),
) -> VideoListResponse:
    videos = db.query(Video).order_by(Video.uploaded_at.desc()).all()
    return VideoListResponse(
        total=len(videos),
        videos=[VideoResponse.model_validate(v) for v in videos],
    )


@router.post(
    "/{video_id}/detect",
    summary="Run YOLO vehicle detection on video by ID",
    description="Shortcut for /api/v1/detection/videos/{video_id}",
)
def detect_video_shortcut(
    video_id: str,
    db: Session = Depends(get_db),
):
    from app.api.v1.detection import detect_video as run_detect
    from app.api.v1.detection import get_detector
    return run_detect(video_id=video_id, db=db, detector=get_detector())


@router.post(
    "/{video_id}/track",
    summary="Run object tracking on video by ID",
    description="Shortcut for /api/v1/tracking/videos/{video_id}",
)
def track_video_shortcut(
    video_id: str,
    db: Session = Depends(get_db),
):
    from app.api.v1.detection import get_detector
    from app.api.v1.tracking import get_tracker
    from app.api.v1.tracking import track_video as run_track
    return run_track(video_id=video_id, db=db, detector=get_detector(), tracker=get_tracker())


@router.post(
    "/{video_id}/count",
    summary="Run vehicle counting on video by ID",
    description="Shortcut for /api/v1/counting/videos/{video_id}",
)
def count_video_shortcut(
    video_id: str,
    db: Session = Depends(get_db),
):
    from app.api.v1.counting import count_video as run_count
    from app.api.v1.counting import get_counter
    from app.api.v1.detection import get_detector
    from app.api.v1.tracking import get_tracker
    return run_count(
        video_id=video_id,
        db=db,
        detector=get_detector(),
        tracker=get_tracker(),
        counter=get_counter(),
    )


@router.post(
    "/{video_id}/analytics",
    summary="Run traffic flow analytics on video by ID",
    description="Shortcut for /api/v1/analytics/videos/{video_id}",
)
def analyze_video_shortcut(
    video_id: str,
    db: Session = Depends(get_db),
):
    from app.api.v1.analytics import analyze_video_traffic as run_analytics
    from app.api.v1.analytics import get_analytics_engine
    from app.api.v1.counting import get_counter
    from app.api.v1.detection import get_detector
    from app.api.v1.tracking import get_tracker
    return run_analytics(
        video_id=video_id,
        db=db,
        detector=get_detector(),
        tracker=get_tracker(),
        counter=get_counter(),
        engine=get_analytics_engine(),
    )


@router.post(
    "/{video_id}/lane-analysis",
    summary="Run lane analysis on video by ID",
    description="Shortcut for /api/v1/lane-analysis/videos/{video_id}",
)
def lane_analysis_video_shortcut(
    video_id: str,
    request_params: dict,
    db: Session = Depends(get_db),
):
    from app.api.v1.detection import get_detector
    from app.api.v1.lane_analysis import analyze_video_lanes as run_lane_analysis
    from app.api.v1.lane_analysis import get_lane_analyzer
    from app.api.v1.tracking import get_tracker
    from app.schemas.lane_analysis import LaneAnalysisRequest
    req_obj = LaneAnalysisRequest.model_validate(request_params)
    return run_lane_analysis(
        video_id=video_id,
        request_params=req_obj,
        db=db,
        detector=get_detector(),
        tracker=get_tracker(),
        analyzer=get_lane_analyzer(),
    )

