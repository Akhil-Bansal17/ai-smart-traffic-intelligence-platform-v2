"""
SQLAlchemy ORM models for Emergency Corridor Simulation & Signal Priority runs.
Phase 13: Emergency Corridor Simulation.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
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
    return datetime.now(timezone.utc)


class EmergencyCorridorSimulationRun(Base):
    """
    Persisted historical record of an Emergency Corridor Simulation run.
    Stores multi-intersection corridor configuration, emergency vehicle scenario,
    baseline vs priority travel metrics, per-intersection timeline events,
    cross-traffic trade-offs, and explainability notes.
    """
    __tablename__ = "emergency_corridor_simulations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("analysis_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    corridor_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    corridor_nodes_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
    )
    total_distance_meters: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    vehicle_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ambulance",
    )
    priority_strategy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="green_extension_early_green",
    )
    recovery_strategy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="smooth_compensation",
    )
    data_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    baseline_travel_time_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    priority_travel_time_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    travel_time_savings_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    travel_time_savings_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    baseline_emergency_delay_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    priority_emergency_delay_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    emergency_delay_reduction_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    baseline_cross_street_delay_avg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    priority_cross_street_delay_avg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    cross_street_delay_impact_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    total_recovery_duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    total_interventions_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    execution_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    corridor_config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    vehicle_scenario: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    node_timelines: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )
    metrics_summary: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    simulation_notes: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        index=True,
    )

    # Relationships
    analysis_session = relationship("AnalysisSession", backref="corridor_simulations")

    def __repr__(self) -> str:
        return (
            f"<EmergencyCorridorSimulationRun(id={self.id}, corridor='{self.corridor_name}', "
            f"vehicle='{self.vehicle_type}', savings={self.travel_time_savings_pct:.1f}%)>"
        )
