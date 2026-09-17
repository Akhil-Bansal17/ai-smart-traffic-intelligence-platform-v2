"""
SQLAlchemy ORM model for Traffic Analysis & Intelligence Reports.
Phase 19: Business-Grade Traffic Reporting & Export.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    """Helper returning timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class ReportType(str, Enum):
    """Supported report types (extensible enum)."""
    TRAFFIC_ANALYSIS = "traffic_analysis"


class ReportScopeType(str, Enum):
    """Scope selector for report generation."""
    SESSION = "session"
    TIME_RANGE = "time_range"


class ReportStatus(str, Enum):
    """Report generation lifecycle status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportFormat(str, Enum):
    """Supported export formats."""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"


class Report(Base):
    """
    Persistent record of a generated or requested traffic intelligence report.
    Stores report metadata, scope, generation status, artifact references, and provenance summary.
    Does NOT duplicate raw metrics records — report content is assembled from authoritative persisted models.
    """
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    report_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=ReportType.TRAFFIC_ANALYSIS.value,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ReportScopeType.SESSION.value,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("analysis_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    time_range_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    time_range_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Traffic Analysis Report",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ReportStatus.PENDING.value,
        index=True,
    )
    format: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ReportFormat.PDF.value,
        index=True,
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    report_data_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    provenance_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    artifact_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processing_time_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Relationships
    analysis_session = relationship("AnalysisSession", backref="reports")

    def __repr__(self) -> str:
        return (
            f"<Report(id={self.id}, type={self.report_type}, "
            f"scope={self.scope_type}, status={self.status}, format={self.format})>"
        )
