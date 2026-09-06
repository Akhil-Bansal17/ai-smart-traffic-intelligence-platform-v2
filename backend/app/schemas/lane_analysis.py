"""
Pydantic schemas for lane analysis and density estimation API requests and responses.

Rules:
- Server-side filesystem paths are strictly excluded.
- Response models clearly state pipeline_stage as 'lane-analysis-run'.
- Clear labeling for image-space density and uncalibrated metrics.
- Enforces strict input validation bounds (min 3 points, max 20 lanes, max 50 points).
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LaneRegionSchema(BaseModel):
    """Configuration for a single user-defined lane polygon region."""
    model_config = ConfigDict(from_attributes=True)

    lane_id: str = Field(..., min_length=1, max_length=50, description="Unique lane identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable lane label")
    polygon: List[List[float]] = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Ordered list of 2D polygon vertices [[x1, y1], [x2, y2], ...]",
    )
    direction_hint: Optional[str] = Field(
        None,
        max_length=50,
        description="Optional metadata hint indicating direction (e.g. inbound, outbound, northbound)",
    )


class LaneAnalysisRequest(BaseModel):
    """Parameters for executing lane assignment and density analysis on an ingested video."""
    confidence_threshold: Optional[float] = Field(
        None,
        ge=0.05,
        le=1.0,
        description="Override vehicle detection confidence threshold",
    )
    iou_threshold: Optional[float] = Field(
        None,
        ge=0.10,
        le=0.95,
        description="Override ByteTrack tracking association IoU threshold",
    )
    max_frames: Optional[int] = Field(
        50,
        ge=1,
        le=300,
        description="Maximum sampled frames to process (bounded to 300)",
    )
    target_fps: Optional[float] = Field(
        None,
        ge=1.0,
        le=60.0,
        description="Downsampled frame rate to balance processing speed",
    )
    lanes: List[LaneRegionSchema] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Configured polygon regions for lane analysis (1 to 20 lanes)",
    )
    persistence_threshold: Optional[int] = Field(
        2,
        ge=1,
        le=10,
        description="Consecutive frames required in lane before confirming assignment (prevents boundary flicker)",
    )


class PerLaneSummarySchema(BaseModel):
    """Aggregated metrics and density results for an individual traffic lane."""
    model_config = ConfigDict(from_attributes=True)

    lane_id: str = Field(..., description="Unique lane identifier")
    lane_name: str = Field(..., description="Human-readable lane label")
    polygon: List[List[float]] = Field(..., description="2D polygon coordinates defining the lane boundaries")
    polygon_area_px2: float = Field(..., description="Computed 2D polygon area in pixel^2 via Shoelace formula")
    total_unique_vehicles: int = Field(..., description="Deduplicated count of unique tracked vehicles assigned to this lane")
    vehicle_class_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of assigned vehicles by vehicle class (car, truck, bus, motorcycle)",
    )
    direction_hint: Optional[str] = Field(None, description="Configured direction hint for reference")
    image_space_density_vehicles_per_px2: float = Field(
        ...,
        description="Uncalibrated image-space density: total_unique_vehicles / polygon_area_px2",
    )
    normalized_density_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized density score (0.0 to 1.0) relative to standard 50x50 px reference cell capacity",
    )
    density_unit: str = Field("vehicles/px²", description="Physical measurement unit")
    density_formula: str = Field(
        "total_unique_vehicles / polygon_area_px2 (image-space uncalibrated)",
        description="Explicit formula used to compute image-space density",
    )
    peak_occupancy: int = Field(..., description="Maximum simultaneous vehicles present in this lane in any single frame")
    average_occupancy: float = Field(..., description="Mean simultaneous vehicles present across processed frames")


class LaneAnalyticsResponse(BaseModel):
    """Structured response payload for video lane analysis and density estimation."""
    model_config = ConfigDict(from_attributes=True)

    video_id: str = Field(..., description="Unique video identifier")
    original_filename: str = Field(..., description="Original name of the ingested video")
    pipeline_stage: str = Field("lane-analysis-run", description="Current pipeline lifecycle stage")
    observation_duration_seconds: float = Field(..., description="Processed video duration in seconds")
    total_frames_processed: int = Field(..., description="Total video frames evaluated")
    total_unique_tracks: int = Field(..., description="Total persistent tracks identified across entire video")
    lanes: List[PerLaneSummarySchema] = Field(
        default_factory=list,
        description="Per-lane traffic volume, class distribution, and image-space density metrics",
    )
    unassigned_vehicles_count: int = Field(
        0,
        description="Tracked vehicles that were never assigned to any configured lane",
    )
    density_calibration_warning: str = Field(
        "Image-space density is not equivalent to vehicles/km² without camera calibration.",
        description="Transparency notice on uncalibrated camera space vs physical world space",
    )
    directional_metrics_omitted_reason: str = Field(
        "Directional per-lane metrics omitted: tripwire crossing events are decoupled from lane polygons in this phase.",
        description="Architectural rationale for absence of directional per-lane metrics",
    )
    processing_time_ms: float = Field(..., description="Total CV pipeline and analysis execution duration in milliseconds")
    generated_at: str = Field(..., description="UTC ISO timestamp when analysis was completed")


class LaneAnalysisInfoResponse(BaseModel):
    """Information regarding lane analysis algorithms, boundary rules, and density definitions."""
    model_config = ConfigDict(from_attributes=True)

    service_name: str = Field("LaneAnalyzer", description="Active CV lane analysis service")
    assignment_method: str = Field(
        "Centroid ray-casting point-in-polygon with N-frame temporal persistence threshold",
        description="Method used to associate tracked vehicles with lane regions",
    )
    density_definition: str = Field(
        "Image-space density = total_unique_vehicles / shoelace_polygon_area_px2 (vehicles/px²)",
        description="Definition of density calculation",
    )
    calibration_policy: str = Field(
        "Image-space density is strictly pixel-space and is not equivalent to physical density (vehicles/km²) without homography or camera calibration matrices.",
        description="Calibration limitation and transparency policy",
    )
    directional_policy: str = Field(
        "Directional metrics per lane are omitted because line-crossing events are decoupled from polygonal lane zones in Phase 9.",
        description="Directional metrics scope boundary explanation",
    )
