"""
Pydantic schemas for YOLO vehicle detection API responses and requests.

Rules:
- Server-side filesystem paths are strictly excluded.
- Detection responses clearly state pipeline_stage as 'detections-run'.
- No track_id is present (tracking belongs to Phase 6).
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BoundingBoxSchema(BaseModel):
    """Bounding box coordinates and dimensions in pixels."""
    model_config = ConfigDict(from_attributes=True)

    x1: float = Field(..., description="Top-left X coordinate")
    y1: float = Field(..., description="Top-left Y coordinate")
    x2: float = Field(..., description="Bottom-right X coordinate")
    y2: float = Field(..., description="Bottom-right Y coordinate")
    width: float = Field(..., description="Box width in pixels")
    height: float = Field(..., description="Box height in pixels")


class DetectionItem(BaseModel):
    """Single vehicle detection item."""
    model_config = ConfigDict(from_attributes=True)

    class_id: int = Field(..., description="COCO numeric class identifier")
    class_name: str = Field(..., description="Detected vehicle class label (e.g. car, bus, truck)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score between 0.0 and 1.0")
    bbox: BoundingBoxSchema = Field(..., description="Bounding box location")
    frame_index: Optional[int] = Field(None, description="Index of the frame where detected")
    timestamp_seconds: Optional[float] = Field(None, description="Timestamp in seconds from video start")


class FrameDetectionResult(BaseModel):
    """Detection results for a single sampled frame."""
    model_config = ConfigDict(from_attributes=True)

    frame_index: int = Field(..., description="Sequential frame index")
    timestamp_seconds: float = Field(..., description="Timestamp in seconds")
    detections: List[DetectionItem] = Field(default_factory=list, description="List of detected vehicles")
    vehicle_count: int = Field(..., description="Total vehicle detections in this frame")


class VideoDetectionResponse(BaseModel):
    """Structured response payload for video detection inference."""
    model_config = ConfigDict(from_attributes=True)

    video_id: str = Field(..., description="Unique video identifier")
    original_filename: str = Field(..., description="Original name of the ingested video")
    pipeline_stage: str = Field("detections-run", description="Current pipeline lifecycle stage")
    model_name: str = Field(..., description="Active YOLO model identifier")
    confidence_threshold: float = Field(..., description="Confidence threshold used for filtering")
    target_fps: int = Field(..., description="Frame sampling rate used for inference")
    total_frames_processed: int = Field(..., description="Total sampled frames evaluated")
    total_detections_count: int = Field(..., description="Total vehicle instances detected across all frames")
    detections_by_class: Dict[str, int] = Field(..., description="Count breakdown by vehicle class")
    frames: List[FrameDetectionResult] = Field(default_factory=list, description="Per-frame detection breakdown")
    processing_time_ms: float = Field(..., description="Total inference runtime in milliseconds")
    preview_frame_base64: Optional[str] = Field(
        None,
        description="Base64 encoded JPEG thumbnail with visual bounding boxes drawn",
    )


class DetectionRequest(BaseModel):
    """Optional parameters for triggering video inference."""
    confidence_threshold: Optional[float] = Field(
        None,
        ge=0.05,
        le=1.0,
        description="Override confidence threshold (default from app settings)",
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
        description="Override sampling FPS (default from app settings: 5 FPS)",
    )
    target_classes: Optional[List[str]] = Field(
        None,
        description="Optional subset of vehicle classes to detect (default: car, motorcycle, bus, truck, bicycle)",
    )


class ModelInfoResponse(BaseModel):
    """Information regarding the active detector and supported labels."""
    model_name: str = Field(..., description="Model identifier or filename")
    device: str = Field(..., description="Inference device (cpu / cuda)")
    confidence_threshold: float = Field(..., description="Default confidence threshold")
    target_classes: List[str] = Field(..., description="Configured active vehicle target classes")
    supported_classes: Dict[int, str] = Field(..., description="Full class mapping supported by underlying model")
