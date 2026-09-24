"""
Pydantic v2 schemas for Unified Traffic Operations Center & Real-Time Incident Response.
Phase 23: Unified Traffic Operations Center.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.historical_analytics import HistoricalProvenanceSummary
from app.schemas.insight import TrafficInsightSchema


class CameraHealthStatus(str, Enum):
    """Authoritative camera health states grounded strictly in live telemetry."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    CONNECTING = "CONNECTING"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class OperationsCameraOverviewItem(BaseModel):
    """Live camera telemetry, processing status, and current metrics."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    source_type: str
    connection_uri_redacted: str
    health_status: CameraHealthStatus
    is_active: bool
    active_job_id: Optional[str] = None
    fps: float = 0.0
    processing_fps: float = 0.0
    frames_acquired: int = 0
    frames_processed: int = 0
    dropped_frames: int = 0
    reconnect_count: int = 0
    current_vehicle_count: int = 0
    active_tracks_count: int = 0
    lane_occupancies: Dict[str, int] = Field(default_factory=dict)
    lane_densities: Dict[str, float] = Field(default_factory=dict)
    class_distribution: Dict[str, int] = Field(default_factory=dict)
    active_anomalies_count: int = 0
    provenance_tag: str = "test_fixture"
    last_frame_timestamp: Optional[float] = None
    last_updated: Optional[datetime] = None
    error_message: Optional[str] = None
    has_preview: bool = False


class OperationsIncidentItem(BaseModel):
    """Authoritative traffic incident item with parent session and video/camera provenance."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    camera_source_id: Optional[str] = None
    camera_name: Optional[str] = None
    video_id: Optional[str] = None
    video_filename: Optional[str] = None
    anomaly_type: str
    severity: str  # low, medium, high, critical
    status: str    # open, acknowledged, resolved
    title: str
    description: str
    metric_name: str
    trigger_value: float
    baseline_value: Optional[float] = None
    threshold_value: float
    deviation_pct: Optional[float] = None
    lane_id: Optional[str] = None
    duration_seconds: float
    provenance_category: str
    is_synthetic: bool = False
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    details_json: Optional[Dict[str, Any]] = None
    operator_note: Optional[str] = None


class OperationsTrafficSnapshot(BaseModel):
    """Current live traffic aggregation with strict epistemic tagging."""
    model_config = ConfigDict(from_attributes=True)

    active_sources_count: int = 0
    total_active_tracks: int = 0
    observed_vehicle_volume: int = 0
    flow_rate_per_minute: float = 0.0
    flow_rate_per_hour: float = 0.0
    flow_rate_tag: str = "UNAVAILABLE"  # OBSERVED, EXTRAPOLATED, UNAVAILABLE
    class_distribution: Dict[str, int] = Field(default_factory=dict)
    directional_split: Dict[str, int] = Field(default_factory=dict)
    directional_ratio: Optional[float] = None
    active_incidents_count: int = 0
    average_lane_occupancy: float = 0.0
    peak_lane_occupancy: int = 0
    observation_duration_seconds: float = 0.0
    data_status: str = "OBSERVED"  # OBSERVED, EXTRAPOLATED, UNAVAILABLE
    traffic_density_state: str = "normal"  # normal, moderate, congested, critical, unavailable


class OperationsTimelineEvent(BaseModel):
    """Chronological event timeline item derived from authoritative persisted records."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str  # incident_started, incident_acknowledged, incident_resolved, job_started, job_completed, job_failed, insight_generated, report_generated
    timestamp: datetime
    title: str
    description: str
    severity: str = "info"  # info, low, medium, high, critical
    source_id: Optional[str] = None
    source_name: Optional[str] = None
    source_type: Optional[str] = None  # camera, video, system, report
    reference_id: Optional[str] = None
    provenance_tag: str = "real_database_metrics"


class OperationsHistoricalContextResponse(BaseModel):
    """Retrospective historical context for a specific camera or source via Phase 22."""
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    source_name: str
    source_type: str
    time_window: str = "7d"
    total_volume: int = 0
    total_sessions: int = 0
    observation_duration_seconds: float = 0.0
    peak_flow_rate: Optional[float] = None
    peak_flow_time: Optional[str] = None
    anomaly_count: int = 0
    dominant_vehicle_class: Optional[str] = None
    dominant_vehicle_share_pct: Optional[float] = None
    inbound_outbound_ratio: Optional[float] = None
    provenance_summary: HistoricalProvenanceSummary
    forecast_status: str = "UNAVAILABLE"
    forecast_reason: str = "Requires at least 20 verified real-world observation sessions for ML training."


class OperationsOverviewResponse(BaseModel):
    """Unified composite operations center overview payload for single-poll orchestration."""
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    system_health: str  # healthy, degraded, offline
    database_connected: bool
    database_latency_ms: float
    active_cameras_count: int
    total_cameras_count: int
    active_incidents_count: int
    critical_incidents_count: int
    active_insights_count: int
    cameras: List[OperationsCameraOverviewItem]
    active_incidents: List[OperationsIncidentItem]
    traffic_snapshot: OperationsTrafficSnapshot
    insights: List[TrafficInsightSchema]
    timeline: List[OperationsTimelineEvent]
    provenance_summary: HistoricalProvenanceSummary
    simulation_support: Dict[str, Any]
    prediction_support: Dict[str, Any]


class OperationsIncidentListResponse(BaseModel):
    """Paginated list of traffic incident events with filtering."""
    model_config = ConfigDict(from_attributes=True)

    incidents: List[OperationsIncidentItem]
    total: int
    active_count: int
    limit: int
    offset: int


class OperationsTimelineResponse(BaseModel):
    """Filtered chronological operations event timeline."""
    model_config = ConfigDict(from_attributes=True)

    events: List[OperationsTimelineEvent]
    total: int
    limit: int


class UpdateIncidentStatusRequest(BaseModel):
    """Request payload for operator incident acknowledgment or resolution."""
    status: str = Field(..., description="Target status: 'acknowledged' or 'resolved' or 'open'")
    note: Optional[str] = Field(None, description="Operator note explaining reason or action taken")
