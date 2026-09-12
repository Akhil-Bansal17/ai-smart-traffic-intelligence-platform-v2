"""
SQLAlchemy ORM model for Traffic Anomaly & Congestion Incident Events.
Phase 15: Traffic Anomaly & Congestion Incident Detection.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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


class AnomalyEvent(Base):
    """
    Persisted record of an operational traffic anomaly or congestion incident.
    Captures exact triggering metric values, duration, severity, and inherited provenance.
    """
    __tablename__ = "anomaly_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    anomaly_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="open",
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
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
    metric_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    trigger_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    baseline_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    threshold_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    deviation_pct: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    lane_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
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
    details_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
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
    analysis_session = relationship("AnalysisSession", back_populates="anomaly_events")

    def __repr__(self) -> str:
        return (
            f"<AnomalyEvent(id={self.id}, type={self.anomaly_type}, "
            f"severity={self.severity}, status={self.status}, session={self.session_id})>"
        )
