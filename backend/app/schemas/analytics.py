"""
Pydantic schemas for traffic analytics and flow metrics API responses and requests.

Rules:
- Server-side filesystem paths are strictly excluded.
- Response models clearly state pipeline_stage as 'analytics-run'.
- Clear labeling for extrapolated metrics.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.counting import CountingLineSchema


class ClassMetricItem(BaseModel):
    """Vehicle class volume count and percentage breakdown."""
    model_config = ConfigDict(from_attributes=True)

    class_name: str = Field(..., description="Vehicle class label (car, bus, truck, etc.)")
    count: int = Field(..., description="Total unique vehicles of this class")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of total traffic volume")


class DirectionMetricItem(BaseModel):
    """Directional volume count and percentage breakdown."""
    model_config = ConfigDict(from_attributes=True)

    direction: str = Field(..., description="Crossing direction identifier (e.g. inbound, outbound)")
    count: int = Field(..., description="Total vehicles moving in this direction")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of total traffic volume")


class TimeSeriesBucketSchema(BaseModel):
    """Discrete time interval bucket for vehicle volume timeline."""
    model_config = ConfigDict(from_attributes=True)

    bucket_index: int = Field(..., description="Sequential index of the time window")
    start_time_seconds: float = Field(..., description="Start of time window in seconds")
    end_time_seconds: float = Field(..., description="End of time window in seconds")
    vehicle_count: int = Field(..., description="Total vehicle crossing events in this window")
    class_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Per-class volume breakdown within this time window",
    )
    inbound_count: int = Field(0, description="Inbound crossing count in this window")
    outbound_count: int = Field(0, description="Outbound crossing count in this window")


class TrafficMetricsResponse(BaseModel):
    """Structured response payload for video traffic analytics and flow metrics."""
    model_config = ConfigDict(from_attributes=True)

    video_id: str = Field(..., description="Unique video identifier")
    original_filename: str = Field(..., description="Original name of the ingested video")
    pipeline_stage: str = Field("analytics-run", description="Current pipeline lifecycle stage")
    observation_duration_seconds: float = Field(..., description="Actual video observation duration in seconds")
    total_vehicles: int = Field(..., description="Total deduplicated unique vehicles observed")
    flow_rate_per_minute: float = Field(..., description="Measured vehicle flow rate per minute")
    flow_rate_per_hour_extrapolated: float = Field(
        ...,
        description="Extrapolated vehicle flow rate per hour (labeled as estimated)",
    )
    is_extrapolated: bool = Field(True, description="Indicates if hourly flow rate is extrapolated from short clip")
    inbound_count: int = Field(..., description="Total inbound vehicles")
    outbound_count: int = Field(..., description="Total outbound vehicles")
    inbound_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of inbound traffic")
    outbound_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of outbound traffic")
    class_distribution: List[ClassMetricItem] = Field(
        default_factory=list,
        description="Volume and percentage breakdown by vehicle class",
    )
    directional_distribution: List[DirectionMetricItem] = Field(
        default_factory=list,
        description="Volume and percentage breakdown by direction",
    )
    time_series: List[TimeSeriesBucketSchema] = Field(
        default_factory=list,
        description="Time-series volume distribution across time intervals",
    )
    total_frames_processed: int = Field(..., description="Total video frames evaluated")
    total_detections: int = Field(..., description="Total raw detections before deduplication")
    unique_tracks: int = Field(..., description="Total persistent tracks initialized")
    counting_line_label: str = Field("main_tripwire", description="Identifier of the counting line used")
    processing_time_ms: float = Field(..., description="Total analytics pipeline runtime in milliseconds")
    generated_at: str = Field(..., description="UTC timestamp when metrics were calculated")


class AnalyticsRequest(BaseModel):
    """Parameters for triggering video traffic flow analytics."""
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
        description="Override frame sampling rate (default: 5 FPS)",
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
    time_bucket_seconds: Optional[float] = Field(
        5.0,
        ge=0.5,
        le=60.0,
        description="Width of time-series aggregation buckets in seconds",
    )


class AnalyticsInfoResponse(BaseModel):
    """Metadata regarding active traffic analytics formulas and data honesty policy."""
    engine_name: str = Field(..., description="Analytics engine identifier")
    metric_definitions: Dict[str, str] = Field(..., description="Mathematical formulas for all computed metrics")
    extrapolation_policy: str = Field(..., description="Policy regarding extrapolation of hourly flow rates")
