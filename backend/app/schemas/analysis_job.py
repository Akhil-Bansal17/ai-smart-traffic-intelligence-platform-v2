"""
Pydantic v2 validation and serialization schemas for video analysis jobs.
Phase 17: Analysis Job Orchestration & Real-Time Processing Foundation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.counting import CountingLineSchema
from app.schemas.lane_analysis import LaneRegionSchema


class AnalysisJobCreateRequest(BaseModel):
    """Request payload to initiate a background asynchronous video analysis job."""
    model_config = ConfigDict(extra="ignore")

    video_id: str = Field(
        ...,
        description="ID of the uploaded video to analyze",
        min_length=1,
    )
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


class AnalysisJobResponse(BaseModel):
    """Detailed status and progress representation of an Analysis Job."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    session_id: Optional[str] = None
    status: str
    analysis_type: str
    progress: Optional[float] = None
    frames_processed: int = 0
    total_frames: Optional[int] = None
    processing_fps: Optional[float] = None
    cancellation_requested: bool = False
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    provenance_category: str = "real_analysis_job"
    is_synthetic: bool = False
    config_snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime


class AnalysisJobListResponse(BaseModel):
    """Paginated list of analysis jobs."""
    model_config = ConfigDict(from_attributes=True)

    total: int
    limit: int
    offset: int
    jobs: List[AnalysisJobResponse]


class AnalysisJobCancelResponse(BaseModel):
    """Response returned upon cancelling an analysis job."""
    model_config = ConfigDict(from_attributes=True)

    status: str
    message: str
    job: AnalysisJobResponse
