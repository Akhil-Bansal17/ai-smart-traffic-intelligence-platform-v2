"""
Import point for Alembic autogenerate.
Imports all models so `alembic revision --autogenerate` can discover them via Base.metadata.
"""
from app.db.session import Base  # noqa: F401
from app.models.analysis import (  # noqa: F401
    AnalysisSession,
    CrossingEventRecord,
    LaneResultRecord,
    TrafficMetricsRecord,
)
from app.models.corridor_simulation import EmergencyCorridorSimulationRun  # noqa: F401
from app.models.prediction import (  # noqa: F401
    PredictionItem,
    PredictionRun,
)
from app.models.simulation import SignalSimulationRun  # noqa: F401
from app.models.video import Video  # noqa: F401

__all__ = [
    "Base",
    "Video",
    "AnalysisSession",
    "TrafficMetricsRecord",
    "LaneResultRecord",
    "CrossingEventRecord",
    "PredictionRun",
    "PredictionItem",
    "SignalSimulationRun",
    "EmergencyCorridorSimulationRun",
]

