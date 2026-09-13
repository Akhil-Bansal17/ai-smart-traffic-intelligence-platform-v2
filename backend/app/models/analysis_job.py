"""
SQLAlchemy ORM model for video analysis jobs.
Phase 17: Analysis Job Orchestration & Real-Time Processing Foundation.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    """Helper returning timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    """Lifecycle states of an analysis job state machine."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisJob(Base):
    """
    Persistent record of an asynchronous video analysis background job.
    Tracks state transitions, honest frame-level progress, cancellation, and provenance.
    """
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("analysis_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobStatus.QUEUED.value,
        index=True,
    )
    analysis_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="full_pipeline",
        index=True,
    )
    progress: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )
    frames_processed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_frames: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    processing_fps: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )
    config_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    cancellation_requested: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    provenance_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="real_analysis_job",
        index=True,
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
        index=True,
    )

    # Relationships
    video = relationship("Video", backref="analysis_jobs")
    analysis_session = relationship("AnalysisSession", backref="analysis_jobs")

    def __repr__(self) -> str:
        return (
            f"<AnalysisJob(id={self.id}, video_id={self.video_id}, "
            f"status={self.status}, progress={self.progress})>"
        )
