"""
SQLAlchemy ORM models for Traffic Signal Optimization Simulation runs.
Phase 12: Traffic Signal Optimization Simulation.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SignalSimulationRun(Base):
    """
    Persisted historical record of a traffic signal optimization simulation run.
    Contains full intersection geometry, input demands, baseline and optimized timing plans,
    evaluation proxies, and comparison metrics.
    """
    __tablename__ = "signal_simulations"

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
    intersection_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    intersection_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="four_way",
    )
    data_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    algorithm_used: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    baseline_cycle_length: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    optimized_cycle_length: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    baseline_delay_proxy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    optimized_delay_proxy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    delay_reduction_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    baseline_queue_proxy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    optimized_queue_proxy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    queue_reduction_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    baseline_throughput_proxy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    optimized_throughput_proxy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    throughput_increase_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    objective_improvement_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    execution_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    intersection_config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    demand_input: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )
    baseline_plan: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    optimized_plan: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    baseline_metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    optimized_metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    phase_comparisons: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )
    approach_comparisons: Mapped[List[Dict[str, Any]]] = mapped_column(
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
    analysis_session = relationship("AnalysisSession", backref="signal_simulations")

    def __repr__(self) -> str:
        return (
            f"<SignalSimulationRun(id={self.id}, intersection='{self.intersection_name}', "
            f"algo='{self.algorithm_used}', delay_red={self.delay_reduction_pct:.1f}%)>"
        )
