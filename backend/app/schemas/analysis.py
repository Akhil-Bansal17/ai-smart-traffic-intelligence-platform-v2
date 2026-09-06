"""
Pydantic v2 validation and serialization schemas for video analysis persistence.
Phase 10: Database Integration.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.counting import CountingLineSchema
from app.schemas.lane_analysis import LaneRegionSchema


class AnalysisRunRequest(BaseModel):

    """Request payload to initiate a persisted video analysis run."""
    model_config = ConfigDict(extra="ignore")

    analysis_type: str = Field(
        default="full_pipeline",
        description="Type of analysis run: 'full_pipeline', 'analytics', 'lane_analysis', or 'counting'",
    )
    confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.01,
        le=1.0,
        description="YOLO detection confidence threshold (defaults to settings/model default)",
    )
    processing_fps: Optional[int] = Field(
        default=None,
        ge=1,
        le=30,
        description="Frame extraction sampling rate (defaults to settings.processing_fps)",
    )
    max_frames: Optional[int] = Field(
        default=None,
        ge=1,
        le=300,
        description="Maximum frames to process in this run",
    )
    iou_threshold: Optional[float] = Field(
        default=None,
        ge=0.05,
        le=0.95,
        description="ByteTrack Kalman IoU association threshold",
    )
    counting_line: Optional[CountingLineSchema] = Field(
        default=None,
        description="Virtual tripwire geometry configuration for line-crossing counting",
    )
    lanes: Optional[List[LaneRegionSchema]] = Field(
        default=None,
        description="Polygonal lane regions for lane assignment and density estimation",
    )
    persistence_threshold: Optional[int] = Field(
        default=2,
        ge=1,
        le=10,
        description="Temporal persistence threshold (consecutive frames required for lane assignment)",
    )


class CrossingEventSchema(BaseModel):
    """Schema for an individual persisted vehicle line-crossing event."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    track_id: int
    class_name: str
    direction: str
    frame_index: int
    timestamp_seconds: float
    centroid_x: float
    centroid_y: float
    line_label: str
    created_at: datetime


class TrafficMetricsRecordSchema(BaseModel):
    """Schema for persisted traffic flow metrics and time-series distributions."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    observation_duration_seconds: float
    total_volume: int
    flow_rate_per_minute: float
    flow_rate_per_hour: float
    is_extrapolated: bool
    class_distribution: Optional[List[Dict[str, Any]]] = None
    direction_distribution: Optional[List[Dict[str, Any]]] = None
    time_series_buckets: Optional[List[Dict[str, Any]]] = None
    created_at: datetime


class LaneResultRecordSchema(BaseModel):
    """Schema for persisted per-lane occupancy, vehicles, and image-space density."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    lane_id: str
    lane_name: str
    direction_hint: Optional[str] = None
    polygon_json: Optional[List[List[float]]] = None
    polygon_area_px2: float
    unique_vehicles_count: int
    peak_occupancy: int
    average_occupancy: float
    image_space_density: float
    normalized_density_score: float
    vehicle_class_counts: Optional[Dict[str, int]] = None
    density_unit: str = "vehicles/px²"
    density_calibration_warning: Optional[str] = None
    created_at: datetime


class AnalysisSessionSummarySchema(BaseModel):
    """Summary schema for an analysis execution run."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    video_filename: Optional[str] = None
    analysis_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[float] = None
    total_frames_processed: int
    total_vehicles_detected: int
    total_vehicles_counted: int
    error_message: Optional[str] = None


class AnalysisSessionDetailResponse(BaseModel):
    """Comprehensive detail response for an analysis session including child results."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    video_filename: Optional[str] = None
    analysis_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[float] = None
    total_frames_processed: int
    total_vehicles_detected: int
    total_vehicles_counted: int
    config_snapshot: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    traffic_metrics: Optional[TrafficMetricsRecordSchema] = None
    lane_results: List[LaneResultRecordSchema] = Field(default_factory=list)
    crossing_events: List[CrossingEventSchema] = Field(default_factory=list)


class AnalysisSessionListResponse(BaseModel):
    """Paginated list of analysis execution sessions."""
    model_config = ConfigDict(from_attributes=True)

    total: int
    limit: int
    offset: int
    sessions: List[AnalysisSessionSummarySchema]


class AnalysisInfoResponse(BaseModel):
    """Database persistence and schema metadata."""
    service_name: str = "AnalysisPersistenceEngine"
    version: str = "0.1.0"
    persisted_entities: List[str] = Field(
        default_factory=lambda: [
            "analysis_sessions",
            "traffic_metrics",
            "lane_results",
            "crossing_events",
        ]
    )
    supported_analysis_types: List[str] = Field(
        default_factory=lambda: [
            "full_pipeline",
            "analytics",
            "lane_analysis",
            "counting",
            "tracking",
            "detection",
        ]
    )
    deduplication_policy: str = "Enforced unique constraint (analysis_session_id, track_id, line_label) in database."
    extrapolation_policy: str = "is_extrapolated boolean flag persisted directly in traffic_metrics table."
    density_policy: str = "Image-space density (veh/px²) persisted with explicit calibration warning."
