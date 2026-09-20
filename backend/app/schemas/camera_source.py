"""
Pydantic schemas for camera sources and live monitoring.
Phase 21: Live Traffic Monitoring & Camera Source Management.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.credential_sanitizer import redact_uri_credentials, validate_camera_uri
from app.schemas.counting import CountingLineSchema
from app.schemas.lane_analysis import LaneRegionSchema


class CameraSourceCreateRequest(BaseModel):
    """Payload for registering a new camera source."""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=128, description="Human-readable camera source identifier")
    description: Optional[str] = Field(default=None, max_length=512)
    source_type: str = Field(
        default="test_fixture",
        description="Source type: 'local_camera', 'rtsp', 'http_stream', 'test_fixture', 'file'",
    )
    connection_uri: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Connection URI, device index, or stream URL",
    )
    enabled: bool = Field(default=True, description="Whether camera source is enabled for monitoring")
    location_name: Optional[str] = Field(default=None, max_length=255)

    @field_validator("source_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("local_camera", "rtsp", "http_stream", "test_fixture", "file"):
            raise ValueError(f"Invalid source_type '{v}'.")
        return clean

    @field_validator("connection_uri")
    @classmethod
    def validate_uri(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("connection_uri cannot be empty.")
        return clean


class CameraSourceUpdateRequest(BaseModel):
    """Payload for updating an existing camera source."""
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)
    source_type: Optional[str] = Field(default=None)
    connection_uri: Optional[str] = Field(default=None, min_length=1, max_length=512)
    enabled: Optional[bool] = Field(default=None)
    location_name: Optional[str] = Field(default=None, max_length=255)


class CameraSourceResponse(BaseModel):
    """Clean representation of a camera source with credentials redacted."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    connection_uri: str
    status: str
    enabled: bool
    location_name: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    last_connected_at: Optional[datetime] = None
    last_frame_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("connection_uri", mode="before")
    @classmethod
    def redact_uri(cls, v: Any) -> str:
        if isinstance(v, str):
            return redact_uri_credentials(v) or ""
        return ""


class CameraSourceListResponse(BaseModel):
    """Paginated list of camera sources."""
    model_config = ConfigDict(from_attributes=True)

    total: int
    items: List[CameraSourceResponse]


class CameraSourceTestResponse(BaseModel):
    """Diagnostic response from probing a camera stream connection."""
    success: bool
    message: str
    source_type: str
    connection_uri: str
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    error: Optional[str] = None


class LiveMonitoringStartRequest(BaseModel):
    """Configuration options when launching a live monitoring session."""
    model_config = ConfigDict(extra="ignore")

    confidence_threshold: Optional[float] = Field(default=None, ge=0.01, le=1.0)
    processing_fps: Optional[int] = Field(default=None, ge=1, le=30)
    iou_threshold: Optional[float] = Field(default=None, ge=0.05, le=0.95)
    counting_line: Optional[CountingLineSchema] = None
    lanes: Optional[List[LaneRegionSchema]] = None
    persistence_threshold: Optional[int] = Field(default=2, ge=1, le=10)


class LiveMonitoringStatusResponse(BaseModel):
    """Live traffic metrics and operational state returned during real-time monitoring."""
    camera_source_id: str
    camera_name: str
    status: str
    active_job_id: Optional[str] = None
    is_live: bool
    source_type: str
    source_fps: float = 0.0
    processing_fps: float = 0.0
    frames_acquired: int = 0
    frames_processed: int = 0
    dropped_frames: int = 0
    reconnect_count: int = 0
    total_volume: int = 0
    inbound_volume: int = 0
    outbound_volume: int = 0
    active_tracks_count: int = 0
    class_distribution: Dict[str, int] = Field(default_factory=dict)
    direction_distribution: Dict[str, int] = Field(default_factory=dict)
    lane_occupancies: Dict[str, int] = Field(default_factory=dict)
    lane_densities: Dict[str, float] = Field(default_factory=dict)
    provenance_tag: str
    last_frame_timestamp: Optional[float] = None
    last_updated: Optional[datetime] = None
    error_message: Optional[str] = None
