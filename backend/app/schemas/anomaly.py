"""
Pydantic v2 schemas for Traffic Anomaly & Congestion Incident Detection.
Phase 15: Traffic Anomaly & Congestion Incident Detection.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnomalyEventSchema(BaseModel):
    """Schema representing a single persisted traffic anomaly / incident event."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    anomaly_type: str = Field(
        ...,
        description="Type of anomaly: 'congestion_buildup', 'abnormal_flow_drop', 'lane_imbalance', or 'density_spike'",
    )
    severity: str = Field(
        ...,
        description="Severity level: 'low', 'medium', 'high', or 'critical'",
    )
    status: str = Field(
        default="open",
        description="Lifecycle status: 'open', 'acknowledged', or 'resolved'",
    )
    title: str
    description: str
    start_timestamp_seconds: float
    end_timestamp_seconds: Optional[float] = None
    duration_seconds: float
    metric_name: str
    trigger_value: float
    baseline_value: Optional[float] = None
    threshold_value: float
    deviation_pct: Optional[float] = None
    lane_id: Optional[str] = None
    provenance_category: str = Field(
        default="real_database_metrics",
        description="Inherited provenance: 'real_database_metrics', 'synthetic_pipeline_metrics', 'synthetic_fixture', or 'unavailable'",
    )
    is_synthetic: bool = False
    details_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None


class AnomalyEventListResponse(BaseModel):
    """Paginated response containing filtered anomaly events."""
    model_config = ConfigDict(from_attributes=True)

    events: List[AnomalyEventSchema]
    total: int
    limit: int
    offset: int
    active_count: int
    provenance_breakdown: Dict[str, int] = Field(default_factory=dict)


class AnomalyEventDetailResponse(BaseModel):
    """Detailed response for a single anomaly event with session and video lineage."""
    model_config = ConfigDict(from_attributes=True)

    event: AnomalyEventSchema
    video_id: Optional[str] = None
    video_filename: Optional[str] = None
    video_source_type: Optional[str] = None
    provenance_verified: bool = False
    source_reference: Optional[str] = None
    license_reference: Optional[str] = None


class AnomalyRuleConfigSchema(BaseModel):
    """Metadata describing a specific anomaly detection rule and its active threshold."""
    model_config = ConfigDict(from_attributes=True)

    rule_name: str
    anomaly_type: str
    description: str
    threshold_value: float
    threshold_unit: str
    condition_description: str
    severity_criteria: Dict[str, str]
    caveats: Optional[str] = None


class AnomalyInfoResponse(BaseModel):
    """Metadata describing Phase 15 detection capabilities, rule configurations, and safety disclaimers."""
    model_config = ConfigDict(from_attributes=True)

    version: str = "1.0.0"
    phase: str = "Phase 15 — Traffic Anomaly & Congestion Incident Detection"
    description: str = (
        "Statistical and rule-based anomaly detection engine evaluating persisted traffic "
        "flow, lane occupancy, density spikes, and directional distributions."
    )
    terminology_disclaimer: str = (
        "Anomaly = statistical deviation; Incident = persisted threshold event. "
        "Does NOT imply vehicle collision, accident, or emergency dispatch event."
    )
    anti_fabrication_policy: str = (
        "Anomalies are detected strictly from genuine metric threshold crossings. "
        "Zero synthetic fabrication: if no anomaly condition exists, zero events are created."
    )
    rules: List[AnomalyRuleConfigSchema]


class UpdateAnomalyStatusRequest(BaseModel):
    """Request payload to acknowledge or resolve an anomaly event."""
    model_config = ConfigDict(extra="ignore")

    status: str = Field(
        ...,
        description="Target status: 'acknowledged', 'resolved', or 'open'",
    )
    note: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Optional operator note regarding status update",
    )


class DetectAnomaliesResponse(BaseModel):
    """Response returned when on-demand anomaly detection is executed for a session."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    anomalies_detected: int
    new_events_count: int
    updated_events_count: int
    events: List[AnomalyEventSchema]
    execution_time_ms: float
