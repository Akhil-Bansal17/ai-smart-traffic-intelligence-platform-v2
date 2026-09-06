"""
SQLAlchemy ORM models for traffic prediction runs and forecast items.
Phase 11: Traffic Prediction / Forecasting.
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
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PredictionRun(Base):
    """
    Persisted metadata and evaluation scores for a trained traffic forecasting run.
    """
    __tablename__ = "prediction_runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    model_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="RandomForestRegressor",
    )
    model_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="ensemble_tree",
    )
    target_variable: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="vehicle_volume",
    )
    horizon_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=15,
    )
    data_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="real_database",
    )
    training_sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    test_sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    training_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    mae: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    rmse: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    r2_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    baseline_mae: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    baseline_rmse: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    feature_names: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )
    feature_importances: Mapped[Optional[Dict[str, float]]] = mapped_column(
        JSON,
        nullable=True,
    )
    model_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(
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
    predictions = relationship(
        "PredictionItem",
        back_populates="prediction_run",
        cascade="all, delete-orphan",
        order_by="PredictionItem.step_index",
    )

    def __repr__(self) -> str:
        return f"<PredictionRun(id={self.id}, model={self.model_name}, target={self.target_variable}, data_source={self.data_source}, mae={self.mae:.3f})>"


class PredictionItem(Base):
    """
    A single time-step forecast point generated within a prediction run.
    """
    __tablename__ = "prediction_items"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    prediction_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("prediction_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    predicted_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    lower_bound: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    upper_bound: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    # Relationships
    prediction_run = relationship("PredictionRun", back_populates="predictions")

    def __repr__(self) -> str:
        return f"<PredictionItem(run_id={self.prediction_run_id}, step={self.step_index}, val={self.predicted_value:.2f})>"
