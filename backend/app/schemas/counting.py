"""
Pydantic schemas for vehicle counting API responses and requests.

Rules:
- Server-side filesystem paths are strictly excluded.
- Response models clearly state pipeline_stage as 'counting-run'.
- Deduplicated counts by class and direction are included.
"""
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class Point2DSchema(BaseModel):
    """2D Point coordinate in relative [0.0, 1.0] or pixel space."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class CountingLineSchema(BaseModel):
    """Configuration for a virtual counting tripwire."""
    p1: Point2DSchema = Field(..., description="Start point of the virtual counting line")
    p2: Point2DSchema = Field(..., description="End point of the virtual counting line")
    label: str = Field("main_tripwire", description="Identifier label for the counting line")
    direction_a_to_b: str = Field("inbound", description="Direction name for A -> B crossing")
    direction_b_to_a: str = Field("outbound", description="Direction name for B -> A crossing")
    min_movement_px: float = Field(2.0, ge=0.0, le=50.0, description="Minimum centroid movement to avoid noise")


class CrossingEventSchema(BaseModel):
    """A vehicle line crossing event."""
    model_config = ConfigDict(from_attributes=True)

    track_id: int = Field(..., description="Persistent track ID of the counted vehicle")
    class_name: str = Field(..., description="Detected vehicle class label (e.g. car, bus, truck)")
    frame_index: int = Field(..., description="Frame index where crossing occurred")
    timestamp_seconds: float = Field(..., description="Timestamp in seconds from video start")
    direction: str = Field(..., description="Crossing direction (inbound / outbound)")
    crossing_point: Tuple[float, float] = Field(..., description="Pixel coordinate (x, y) at crossing")
    line_label: str = Field("main_line", description="Label of the counting line crossed")


class FrameCountingResultSchema(BaseModel):
    """Counting results for a single sampled frame."""
    model_config = ConfigDict(from_attributes=True)

    frame_index: int = Field(..., description="Sequential frame index")
    timestamp_seconds: float = Field(..., description="Timestamp in seconds")
    active_tracks_count: int = Field(..., description="Number of active tracks in this frame")
    new_crossings: List[CrossingEventSchema] = Field(
        default_factory=list,
        description="Vehicles that crossed the counting line in this frame",
    )


class VideoCountingResponse(BaseModel):
    """Structured response payload for video vehicle counting inference."""
    model_config = ConfigDict(from_attributes=True)

    video_id: str = Field(..., description="Unique video identifier")
    original_filename: str = Field(..., description="Original name of the ingested video")
    pipeline_stage: str = Field("counting-run", description="Current pipeline lifecycle stage")
    detector_model: str = Field(..., description="Active YOLO detector model")
    tracker_name: str = Field(..., description="Active tracking algorithm name")
    counting_line: CountingLineSchema = Field(..., description="Counting line geometry used")
    total_frames_processed: int = Field(..., description="Total sampled frames evaluated")
    total_detections_count: int = Field(..., description="Total raw vehicle detections")
    total_unique_tracks: int = Field(..., description="Total persistent tracks initialized")
    total_counted_vehicles: int = Field(..., description="Total genuine deduplicated vehicles counted")
    counts_by_class: Dict[str, int] = Field(..., description="Deduplicated vehicle counts by vehicle class")
    counts_by_direction: Dict[str, int] = Field(..., description="Deduplicated vehicle counts by crossing direction")
    counted_track_ids: List[int] = Field(default_factory=list, description="List of track IDs counted")
    crossing_events: List[CrossingEventSchema] = Field(default_factory=list, description="Chronological crossing log")
    frames: List[FrameCountingResultSchema] = Field(default_factory=list, description="Per-frame counting results")
    processing_time_ms: float = Field(..., description="Total pipeline runtime in milliseconds")
    preview_frame_base64: Optional[str] = Field(
        None,
        description="Base64 encoded JPEG preview with counting line and crossing indicators",
    )


class CountingRequest(BaseModel):
    """Parameters for triggering video vehicle counting inference."""
    confidence_threshold: Optional[float] = Field(
        None,
        ge=0.05,
        le=1.0,
        description="Override detection confidence threshold",
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
    counting_line: Optional[CountingLineSchema] = Field(
        None,
        description="Optional custom virtual counting line configuration",
    )


class CountingInfoResponse(BaseModel):
    """Information regarding the active counting engine and mathematical crossing semantics."""
    counter_name: str = Field(..., description="Counting algorithm name")
    default_line: CountingLineSchema = Field(..., description="Default virtual tripwire configuration")
    crossing_semantics: str = Field(..., description="Mathematical description of line crossing algorithm")
    direction_rules: Dict[str, str] = Field(..., description="Direction assignment definitions")
