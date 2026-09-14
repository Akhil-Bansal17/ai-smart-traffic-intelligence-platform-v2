"""
Pydantic schemas for Traffic Decision Intelligence & Explainable Insights.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.insight import (
    InsightCategory,
    InsightSeverity,
    InsightStatus,
    RecommendationType,
)


class ObservedFactorSchema(BaseModel):
    """Directly measured empirical evidence from sensor/video tracking data."""
    label: str = Field("Observed", description="Factor classification tag")
    statement: str = Field(..., description="Fact-based measurement sentence")
    metric: str = Field(..., description="Name of the measured metric")
    value: Any = Field(..., description="Exact numerical or categorical value")
    unit: Optional[str] = Field(None, description="Physical or pixel measurement unit")


class InferredFactorSchema(BaseModel):
    """Deductive reasoning explaining why the system believes the condition exists."""
    label: str = Field("Inferred", description="Factor classification tag")
    statement: str = Field(..., description="Deductive inference sentence")
    rationale: str = Field(..., description="Logical deduction explaining the underlying condition")
    confidence: str = Field("medium", description="Confidence tier: 'high', 'medium', 'low'")


class EvidencePackageSchema(BaseModel):
    """Structured evidence package consolidating all supporting records and limitations."""
    metrics_summary: Optional[Dict[str, Any]] = Field(
        None, description="Snapshot of core flow and volume metrics"
    )
    lane_metrics: Optional[List[Dict[str, Any]]] = Field(
        None, description="Snapshot of per-lane occupancy and density metrics"
    )
    anomaly_event_ids: List[str] = Field(
        default_factory=list, description="IDs of correlated Phase 15 anomaly events"
    )
    simulation_references: List[Dict[str, Any]] = Field(
        default_factory=list, description="References to signal or emergency corridor simulation runs"
    )
    prediction_evidence: Dict[str, Any] = Field(
        default_factory=lambda: {
            "is_available": False,
            "reason": "Insufficient verified real-world observations (N < 20 per Phase 11 trust boundary)",
        },
        description="ML forecast evidence availability status",
    )
    unavailable_evidence: List[str] = Field(
        default_factory=list, description="List of evidence types that were unavailable or unmeasured"
    )


class TrafficInsightSchema(BaseModel):
    """Complete serialized model for a persisted TrafficInsight."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: Optional[str] = None
    job_id: Optional[str] = None
    insight_type: str
    category: str
    severity: str
    status: str
    title: str
    summary: str
    start_timestamp_seconds: float = 0.0
    end_timestamp_seconds: Optional[float] = None
    duration_seconds: float = 0.0
    affected_lane_id: Optional[str] = None
    affected_lane_name: Optional[str] = None
    root_cause_observed: Optional[List[Dict[str, Any]]] = None
    root_cause_inferred: Optional[List[Dict[str, Any]]] = None
    recommendation: Optional[str] = None
    recommendation_rationale: Optional[str] = None
    recommendation_type: Optional[str] = RecommendationType.NONE.value
    evidence_package: Optional[Dict[str, Any]] = None
    limitations: Optional[List[str]] = None
    provenance_category: str = "real_database_metrics"
    is_synthetic: bool = False
    dedup_signature: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None


class TrafficInsightDetailResponse(BaseModel):
    """Response envelope for a single detailed insight record."""
    insight: TrafficInsightSchema


class TrafficInsightListResponse(BaseModel):
    """Paginated response containing matching traffic insights and provenance breakdown."""
    total: int
    active_count: int
    limit: int
    offset: int
    items: List[TrafficInsightSchema]
    provenance_breakdown: Dict[str, int] = Field(default_factory=dict)


class InsightGenerateRequest(BaseModel):
    """Request payload to generate deterministic insights from persisted session data."""
    session_id: str = Field(..., description="Target AnalysisSession ID")
    job_id: Optional[str] = Field(None, description="Optional associated AnalysisJob ID")
    force_recompute: bool = Field(False, description="Whether to recompute and update existing active insights")


class InsightGenerateResponse(BaseModel):
    """Response payload returned upon on-demand insight generation."""
    session_id: str
    insights_generated: int
    insights: List[TrafficInsightSchema]
    processing_time_ms: float


class UpdateInsightStatusRequest(BaseModel):
    """Payload to update the lifecycle status of an insight."""
    status: str = Field(..., description="Target status: 'NEW', 'ACTIVE', 'RECOVERED', 'DISMISSED'")
    note: Optional[str] = Field(None, description="Optional operator note")


class InsightCategoryInfo(BaseModel):
    """Metadata describing a supported insight category."""
    category: str
    description: str
    supported_signals: List[str]
    sample_title: str


class InsightSeverityInfo(BaseModel):
    """Metadata describing a severity rating and its criteria."""
    severity: str
    criteria: str
    color_hint: str


class InsightInfoResponse(BaseModel):
    """Catalog response describing decision intelligence configuration and policies."""
    categories: List[InsightCategoryInfo]
    severity_levels: List[InsightSeverityInfo]
    architectural_boundaries: Dict[str, str]
    anti_fabrication_policies: List[str]
