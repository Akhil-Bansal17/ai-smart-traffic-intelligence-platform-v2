"""
Pydantic v2 schemas for traffic prediction and forecasting.
Phase 11: Traffic Prediction / Forecasting.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PredictionInfoResponse(BaseModel):
    """Metadata about the ML forecasting engine and configuration policies."""
    service_name: str = "TrafficPredictionEngine"
    version: str = "0.1.0"
    supported_models: List[str] = Field(
        default_factory=lambda: [
            "RandomForestRegressor",
            "HistGradientBoostingRegressor",
            "RidgeRegression",
            "NaivePersistenceBaseline",
        ]
    )
    default_model: str = "RandomForestRegressor"
    feature_set: List[str] = Field(
        default_factory=lambda: [
            "lag_1_volume",
            "lag_2_volume",
            "lag_3_volume",
            "rolling_mean_3_volume",
            "rolling_std_3_volume",
            "flow_rate_per_minute",
            "inbound_ratio",
            "hour_sin",
            "hour_cos",
            "day_of_week",
            "is_peak_hour",
        ]
    )
    target_variable: str = "vehicle_volume"
    supported_horizons_minutes: List[int] = Field(default_factory=lambda: [5, 10, 15, 30])
    min_training_samples: int = 20
    data_reality_policy: str = "Strict separation of real database observations and synthetic fixtures. Zero fabricated confidence."


class DatasetReadinessResponse(BaseModel):
    """Readiness status of the persisted traffic dataset for ML training."""
    is_ready: bool
    sample_count: int
    threshold: int
    data_source: str
    message: str
    session_count: int = 0
    status_code: str = "insufficient_observations"
    earliest_timestamp: Optional[str] = None
    latest_timestamp: Optional[str] = None


class TrainModelRequest(BaseModel):
    """Parameters to trigger a model training and forecasting run."""
    model_name: str = Field(
        default="RandomForestRegressor",
        description="ML algorithm to train: 'RandomForestRegressor', 'HistGradientBoostingRegressor', 'RidgeRegression', or 'NaivePersistenceBaseline'",
    )
    horizon_minutes: int = Field(
        default=15,
        ge=5,
        le=60,
        description="Forecast horizon in minutes into the future",
    )
    use_fixtures_if_insufficient: bool = Field(
        default=False,
        description="If true and real database records are below threshold, train on clearly-labeled development fixtures",
    )


class PredictionItemSchema(BaseModel):
    """A single forecast point with timestamp and prediction interval."""
    model_config = ConfigDict(from_attributes=True)

    step_index: int
    timestamp: datetime
    predicted_value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class ModelEvaluationSchema(BaseModel):
    """Evaluation metrics comparing the model against the naive persistence baseline."""
    model_name: str
    model_type: str
    data_source: str
    target_variable: str
    horizon_minutes: int
    training_samples: int
    test_samples: int
    training_time_ms: float
    mae: float
    rmse: float
    r2_score: Optional[float] = None
    baseline_mae: float
    baseline_rmse: float
    baseline_improvement_pct: float
    feature_names: List[str]
    feature_importances: Dict[str, float]


class PredictionRunDetailResponse(BaseModel):
    """Complete detail of a trained prediction run, evaluation scores, and forecast points."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_name: str
    model_type: str
    target_variable: str
    horizon_minutes: int
    data_source: str
    training_sample_count: int
    test_sample_count: int
    training_time_ms: float
    mae: float
    rmse: float
    r2_score: Optional[float] = None
    baseline_mae: float
    baseline_rmse: float
    feature_names: Optional[List[str]] = None
    feature_importances: Optional[Dict[str, float]] = None
    predictions: List[PredictionItemSchema] = Field(default_factory=list)
    created_at: datetime


class PredictionRunSummarySchema(BaseModel):
    """Summary overview of a historical prediction run."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_name: str
    model_type: str
    target_variable: str
    horizon_minutes: int
    data_source: str
    training_sample_count: int
    mae: float
    rmse: float
    r2_score: Optional[float] = None
    baseline_mae: float
    created_at: datetime


class PredictionRunListResponse(BaseModel):
    """Paginated list of historical prediction runs."""
    model_config = ConfigDict(from_attributes=True)

    total: int
    limit: int
    offset: int
    runs: List[PredictionRunSummarySchema]


class GenerateFixturesRequest(BaseModel):
    """Request to create synthetic fixture records for development testing."""
    num_samples: int = Field(default=120, ge=20, le=500)
    interval_minutes: int = Field(default=5, ge=1, le=60)
