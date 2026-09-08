"""
SQLAlchemy ORM model for uploaded video records.
Matches ARCHITECTURE.md §8 schema definition.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    uploaded_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    fps: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    resolution: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="0x0",
    )
    frame_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="uploaded",
        index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unknown",
        index=True,
    )
    source_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    license_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    provenance_note: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    provenance_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    captured_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, name={self.original_filename}, source={self.source_type}, verified={self.provenance_verified}, status={self.status})>"
