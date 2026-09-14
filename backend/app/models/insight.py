"""
SQLAlchemy ORM model for Traffic Decision Intelligence Insights.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    """Helper returning timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class InsightCategory(str, Enum):
    """Supported traffic decision intelligence insight categories."""
    CONGESTION = "CONGESTION"
    FLOW_DEGRADATION = "FLOW_DEGRADATION"
    LANE_IMBALANCE = "LANE_IMBALANCE"
    DENSITY_SPIKE = "DENSITY_SPIKE"
    TRAFFIC_SURGE = "TRAFFIC_SURGE"
    UNDERUTILIZED_LANE = "UNDERUTILIZED_LANE"
    OPERATIONAL_RECOMMENDATION = "OPERATIONAL_RECOMMENDATION"


class InsightSeverity(str, Enum):
    """Evidence-grounded severity classification."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InsightStatus(str, Enum):
    """Operational lifecycle state of a traffic insight."""
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    RECOVERED = "RECOVERED"
    DISMISSED = "DISMISSED"


class RecommendationType(str, Enum):
    """Taxonomy of advisory recommendations."""
    SIGNAL_RETIMING = "signal_retiming"
    LANE_MANAGEMENT = "lane_management"
    CORRIDOR_COORDINATION = "corridor_coordination"
    CAPACITY_WARNING = "capacity_warning"
    MONITORING_ONLY = "monitoring_only"
    NONE = "none"


class TrafficInsight(Base):
    """
    Persisted record of an explainable traffic intelligence insight.
    Contains deterministic evidence aggregation, observed vs. inferred root causes,
    advisory recommendations, honest limitations, and strict provenance tracking.
    """
    __tablename__ = "traffic_insights"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("analysis_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    insight_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=InsightCategory.CONGESTION.value,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=InsightSeverity.INFO.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=InsightStatus.NEW.value,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    start_timestamp_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    end_timestamp_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    affected_lane_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    affected_lane_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    root_cause_observed: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    root_cause_inferred: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    recommendation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    recommendation_rationale: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    recommendation_type: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        default=RecommendationType.NONE.value,
    )
    evidence_package: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    limitations: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )
    provenance_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="real_database_metrics",
        index=True,
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    dedup_signature: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    analysis_session = relationship("AnalysisSession", back_populates="insights")
    analysis_job = relationship("AnalysisJob", backref="insights")

    def __repr__(self) -> str:
        return (
            f"<TrafficInsight(id={self.id}, category={self.category}, "
            f"severity={self.severity}, status={self.status}, session={self.session_id})>"
        )
