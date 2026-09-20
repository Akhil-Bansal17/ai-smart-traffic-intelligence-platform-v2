"""
SQLAlchemy ORM model for camera sources.
Phase 21: Live Traffic Monitoring & Camera Source Management.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.credential_sanitizer import redact_uri_credentials
from app.db.session import Base


def utcnow() -> datetime:
    """Helper returning timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class CameraSourceType(str, Enum):
    LOCAL_CAMERA = "local_camera"
    RTSP = "rtsp"
    HTTP_STREAM = "http_stream"
    TEST_FIXTURE = "test_fixture"
    FILE = "file"


class CameraSourceStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    STOPPED = "stopped"


class CameraSource(Base):
    """
    Persistent record of a video camera feed or stream source.
    Supports local cameras, RTSP network streams, HTTP streams, and deterministic test fixtures.
    """
    __tablename__ = "camera_sources"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CameraSourceType.TEST_FIXTURE.value,
        index=True,
    )
    connection_uri: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CameraSourceStatus.DISCONNECTED.value,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    location_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    fps: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_frame_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        String(1024),
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
        index=True,
    )

    # Relationships
    analysis_jobs = relationship("AnalysisJob", back_populates="camera_source", cascade="all, delete-orphan")
    analysis_sessions = relationship("AnalysisSession", back_populates="camera_source")

    @property
    def redacted_uri(self) -> str:
        """Returns connection URI with any password masked."""
        return redact_uri_credentials(self.connection_uri) or ""

    def __repr__(self) -> str:
        return (
            f"<CameraSource(id={self.id}, name={self.name}, "
            f"type={self.source_type}, status={self.status})>"
        )
