"""
SQLAlchemy ORM models for video analysis sessions, traffic metrics, lane results, and crossing events.
Matches ARCHITECTURE.md §8 schema definition for Phase 10 Database Integration.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    """Helper returning timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class AnalysisSession(Base):
    """
    Persistent record of an analysis execution run on a video.
    Tracks pipeline parameters, status, duration, and child metrics.
    """
    __tablename__ = "analysis_sessions"

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
    analysis_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="full_pipeline",
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
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
    total_frames_processed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_vehicles_detected: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_vehicles_counted: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    config_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )

    # Relationships
    video = relationship("Video", backref="analysis_sessions")
    traffic_metrics = relationship(
        "TrafficMetricsRecord",
        back_populates="analysis_session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    lane_results = relationship(
        "LaneResultRecord",
        back_populates="analysis_session",
        cascade="all, delete-orphan",
    )
    crossing_events = relationship(
        "CrossingEventRecord",
        back_populates="analysis_session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AnalysisSession(id={self.id}, video_id={self.video_id}, type={self.analysis_type}, status={self.status})>"


class TrafficMetricsRecord(Base):
    """
    Persisted aggregate traffic flow metrics and time-series bucketing for an analysis session.
    """
    __tablename__ = "traffic_metrics"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    analysis_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    total_volume: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    flow_rate_per_minute: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    flow_rate_per_hour: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    is_extrapolated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    class_distribution: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    direction_distribution: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    time_series_buckets: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    # Relationships
    analysis_session = relationship("AnalysisSession", back_populates="traffic_metrics")

    def __repr__(self) -> str:
        return f"<TrafficMetricsRecord(id={self.id}, session_id={self.analysis_session_id}, volume={self.total_volume})>"


class LaneResultRecord(Base):
    """
    Persisted per-lane metrics, occupancy, and image-space density for an analysis session.
    """
    __tablename__ = "lane_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    analysis_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lane_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    lane_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    direction_hint: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    polygon_json: Mapped[Optional[List[List[float]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    polygon_area_px2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    unique_vehicles_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    peak_occupancy: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    average_occupancy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    image_space_density: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    normalized_density_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    vehicle_class_counts: Mapped[Optional[Dict[str, int]]] = mapped_column(
        JSON,
        nullable=True,
    )
    density_unit: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="vehicles/px²",
    )
    density_calibration_warning: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    # Relationships
    analysis_session = relationship("AnalysisSession", back_populates="lane_results")

    def __repr__(self) -> str:
        return f"<LaneResultRecord(id={self.id}, lane_id={self.lane_id}, vehicles={self.unique_vehicles_count}, density={self.image_space_density})>"


class CrossingEventRecord(Base):
    """
    Persisted individual vehicle line-crossing events with strict deduplication per (session, track_id, line).
    """
    __tablename__ = "crossing_events"
    __table_args__ = (
        UniqueConstraint(
            "analysis_session_id",
            "track_id",
            "line_label",
            name="uq_crossing_event_session_track_line",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    analysis_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    class_name: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    frame_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    timestamp_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    centroid_x: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    centroid_y: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    line_label: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="main_line",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    # Relationships
    analysis_session = relationship("AnalysisSession", back_populates="crossing_events")

    def __repr__(self) -> str:
        return f"<CrossingEventRecord(session_id={self.analysis_session_id}, track_id={self.track_id}, class={self.class_name}, dir={self.direction})>"
