"""
Pydantic schemas for object tracking API responses and requests.

Rules:
- Server-side filesystem paths are strictly excluded.
- Response models clearly state pipeline_stage as 'tracking-run'.
- Each tracked object contains a persistent track_id and lifecycle state.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.detection import BoundingBoxSchema


class TrackedItem(BaseModel):
    """Single tracked object instance with persistent track_id."""
    model_config = ConfigDict(from_attributes=True)

    track_id: int = Field(..., description="Persistent track ID assigned by the tracker")
    class_id: int = Field(..., description="COCO numeric class identifier")
    class_name: str = Field(..., description="Detected vehicle class label (e.g. car, bus, truck)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    bbox: BoundingBoxSchema = Field(..., description="Tracked bounding box location")
    frame_index: Optional[int] = Field(None, description="Index of the frame where observed")
    timestamp_seconds: Optional[float] = Field(None, description="Timestamp in seconds from video start")
    state: str = Field("active", description="Track lifecycle state (new, active, lost, terminated)")
    age_frames: int = Field(1, description="Total frames this track has been alive")
    hits: int = Field(1, description="Number of frames with successful detection matches")


class FrameTrackingResultSchema(BaseModel):
    """Tracking results for a single sampled frame."""
    model_config = ConfigDict(from_attributes=True)

    frame_index: int = Field(..., description="Sequential frame index")
    timestamp_seconds: float = Field(..., description="Timestamp in seconds")
    tracked_objects: List[TrackedItem] = Field(default_factory=list, description="Active tracked vehicles")
    active_tracks_count: int = Field(..., description="Number of active tracks in this frame")


class VideoTrackingResponse(BaseModel):
    """Structured response payload for video object tracking inference."""
    model_config = ConfigDict(from_attributes=True)

    video_id: str = Field(..., description="Unique video identifier")
    original_filename: str = Field(..., description="Original name of the ingested video")
    pipeline_stage: str = Field("tracking-run", description="Current pipeline lifecycle stage")
    detector_model: str = Field(..., description="Active YOLO detector model")
    tracker_name: str = Field(..., description="Active tracking algorithm name")
    confidence_threshold: float = Field(..., description="Detection confidence threshold")
    target_fps: int = Field(..., description="Frame sampling rate used for tracking")
    total_frames_processed: int = Field(..., description="Total sampled frames evaluated")
    total_detections_count: int = Field(..., description="Total detections fed into tracker")
    total_unique_tracks: int = Field(..., description="Total distinct persistent track IDs created")
    tracks_by_class: Dict[str, int] = Field(..., description="Vehicle count breakdown by class across all frames")
    frames: List[FrameTrackingResultSchema] = Field(default_factory=list, description="Per-frame tracking results")
    processing_time_ms: float = Field(..., description="Total detection and tracking runtime in milliseconds")
    preview_frame_base64: Optional[str] = Field(
        None,
        description="Base64 encoded JPEG preview with bounding boxes and visible track IDs",
    )


class TrackingRequest(BaseModel):
    """Parameters for triggering video tracking inference."""
    confidence_threshold: Optional[float] = Field(
        None,
        ge=0.05,
        le=1.0,
        description="Override detection confidence threshold (default from app settings)",
    )
    max_frames: Optional[int] = Field(
        50,
        ge=1,
        le=300,
        description="Maximum sampled frames to process (bounded to 300)",
    )
    target_fps: Optional[int] = Field(
        None,
        ge=1,
        le=30,
        description="Override frame sampling rate (default from app settings: 5 FPS)",
    )
    iou_threshold: Optional[float] = Field(
        None,
        ge=0.1,
        le=0.9,
        description="Override IoU spatial association threshold",
    )
    max_lost_frames: Optional[int] = Field(
        None,
        ge=1,
        le=60,
        description="Override maximum frames a lost track is retained before termination",
    )


class TrackerInfoResponse(BaseModel):
    """Information regarding the active tracker configuration and lifecycle state machine."""
    tracker_name: str = Field(..., description="Tracker implementation name")
    iou_threshold: float = Field(..., description="Active IoU association threshold")
    max_lost_frames: int = Field(..., description="Max tolerance for missed frames")
    track_lifecycle: Dict[str, str] = Field(..., description="Track state machine transitions and descriptions")
