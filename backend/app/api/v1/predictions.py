"""
Traffic Prediction and Forecasting API endpoints: /api/v1/predictions.
Phase 11: Traffic Prediction / Forecasting.

Provides:
- GET  /api/v1/predictions/info — Forecasting service metadata and feature definitions
- GET  /api/v1/predictions/readiness — Check if database contains enough real observations
- POST /api/v1/predictions/train — Train ML model on database data, evaluate, and persist forecast
- GET  /api/v1/predictions/runs — List historical prediction runs (paginated)
- GET  /api/v1/predictions/runs/{run_id} — Retrieve detailed prediction run with evaluations and items
- POST /api/v1/predictions/fixtures/generate — Generate synthetic development fixtures
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.prediction import PredictionItem, PredictionRun
from app.schemas.prediction import (
    DatasetReadinessResponse,
    GenerateFixturesRequest,
    PredictionInfoResponse,
    PredictionItemSchema,
    PredictionRunDetailResponse,
    PredictionRunListResponse,
    PredictionRunSummarySchema,
    TrainModelRequest,
)
from app.services.ml.dataset_extractor import DatasetExtractor
from app.services.ml.traffic_predictor import TrafficPredictor, get_traffic_predictor

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/info",
    response_model=PredictionInfoResponse,
    summary="Get traffic prediction engine information",
)
def get_prediction_info() -> PredictionInfoResponse:
    """Returns forecasting metadata, feature set definitions, and supported models."""
    return PredictionInfoResponse()


@router.get(
    "/readiness",
    response_model=DatasetReadinessResponse,
    summary="Check dataset readiness for model training",
)
def check_dataset_readiness(
    db: Session = Depends(get_db),
    predictor: TrafficPredictor = Depends(get_traffic_predictor),
) -> DatasetReadinessResponse:
    """
    Inspects real database traffic records and determines if sufficient observations exist for training.
    """
    readiness = predictor.extractor.check_readiness(db)
    return DatasetReadinessResponse(
        is_ready=readiness.is_ready,
        sample_count=readiness.sample_count,
        threshold=readiness.threshold,
        data_source=readiness.data_source,
        message=readiness.message,
        session_count=readiness.session_count,
        status_code=readiness.status_code,
        real_sample_count=readiness.real_sample_count,
        synthetic_sample_count=readiness.synthetic_sample_count,
        earliest_timestamp=readiness.earliest_timestamp,
        latest_timestamp=readiness.latest_timestamp,
    )


@router.post(
    "/train",
    response_model=PredictionRunDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Train ML model and generate persisted traffic predictions",
)
def train_and_forecast(
    payload: TrainModelRequest,
    db: Session = Depends(get_db),
    predictor: TrafficPredictor = Depends(get_traffic_predictor),
) -> PredictionRunDetailResponse:
    """
    Trains the requested model on chronological database observations (or synthetic fixtures if allowed),
    evaluates held-out test split against naive baseline, generates forecast points, and persists results.
    """
    forecast_result = predictor.execute_and_persist(
        db=db,
        model_name=payload.model_name,
        horizon_minutes=payload.horizon_minutes,
        use_fixtures_if_insufficient=payload.use_fixtures_if_insufficient,
    )

    # Query back persisted record with relationship
    run_record = db.scalars(
        select(PredictionRun).where(PredictionRun.id == forecast_result.run_id)
    ).first()

    if not run_record:
        raise AppException("Failed to load persisted prediction run.", status_code=500)

    prediction_items = [
        PredictionItemSchema(
            step_index=item.step_index,
            timestamp=item.timestamp,
            predicted_value=item.predicted_value,
            lower_bound=item.lower_bound,
            upper_bound=item.upper_bound,
        )
        for item in run_record.predictions
    ]

    return PredictionRunDetailResponse(
        id=run_record.id,
        model_name=run_record.model_name,
        model_type=run_record.model_type,
        target_variable=run_record.target_variable,
        horizon_minutes=run_record.horizon_minutes,
        data_source=run_record.data_source,
        training_sample_count=run_record.training_sample_count,
        test_sample_count=run_record.test_sample_count,
        training_time_ms=run_record.training_time_ms,
        mae=run_record.mae,
        rmse=run_record.rmse,
        r2_score=run_record.r2_score,
        baseline_mae=run_record.baseline_mae,
        baseline_rmse=run_record.baseline_rmse,
        feature_names=run_record.feature_names,
        feature_importances=run_record.feature_importances,
        predictions=prediction_items,
        created_at=run_record.created_at,
    )


@router.get(
    "/runs",
    response_model=PredictionRunListResponse,
    summary="List historical prediction runs",
)
def list_prediction_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PredictionRunListResponse:
    """Lists past trained prediction runs ordered chronologically (newest first)."""
    total = db.scalar(select(func.count()).select_from(PredictionRun)) or 0
    runs = db.scalars(
        select(PredictionRun)
        .order_by(PredictionRun.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    summaries = [
        PredictionRunSummarySchema(
            id=r.id,
            model_name=r.model_name,
            model_type=r.model_type,
            target_variable=r.target_variable,
            horizon_minutes=r.horizon_minutes,
            data_source=r.data_source,
            training_sample_count=r.training_sample_count,
            mae=r.mae,
            rmse=r.rmse,
            r2_score=r.r2_score,
            baseline_mae=r.baseline_mae,
            created_at=r.created_at,
        )
        for r in runs
    ]

    return PredictionRunListResponse(
        total=total,
        limit=limit,
        offset=offset,
        runs=summaries,
    )


@router.get(
    "/runs/{run_id}",
    response_model=PredictionRunDetailResponse,
    summary="Get details of a specific prediction run",
)
def get_prediction_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
) -> PredictionRunDetailResponse:
    """Retrieves full evaluation scores, feature importances, and predicted points for a run."""
    run = db.scalars(select(PredictionRun).where(PredictionRun.id == run_id)).first()
    if not run:
        raise AppException(f"Prediction run '{run_id}' not found.", status_code=404)

    prediction_items = [
        PredictionItemSchema(
            step_index=item.step_index,
            timestamp=item.timestamp,
            predicted_value=item.predicted_value,
            lower_bound=item.lower_bound,
            upper_bound=item.upper_bound,
        )
        for item in run.predictions
    ]

    return PredictionRunDetailResponse(
        id=run.id,
        model_name=run.model_name,
        model_type=run.model_type,
        target_variable=run.target_variable,
        horizon_minutes=run.horizon_minutes,
        data_source=run.data_source,
        training_sample_count=run.training_sample_count,
        test_sample_count=run.test_sample_count,
        training_time_ms=run.training_time_ms,
        mae=run.mae,
        rmse=run.rmse,
        r2_score=run.r2_score,
        baseline_mae=run.baseline_mae,
        baseline_rmse=run.baseline_rmse,
        feature_names=run.feature_names,
        feature_importances=run.feature_importances,
        predictions=prediction_items,
        created_at=run.created_at,
    )


@router.post(
    "/fixtures/generate",
    response_model=DatasetReadinessResponse,
    summary="Generate labeled synthetic fixtures for development testing",
)
def generate_synthetic_fixtures(
    payload: GenerateFixturesRequest,
) -> DatasetReadinessResponse:
    """
    Generates in-memory synthetic fixture data points and returns development readiness status.
    All downstream training will be explicitly flagged as DATA_SOURCE: synthetic_fixture.
    """
    fixtures = DatasetExtractor.generate_synthetic_fixtures(
        num_samples=payload.num_samples,
        interval_minutes=payload.interval_minutes,
    )
    earliest = fixtures[0].timestamp.isoformat() if fixtures else None
    latest = fixtures[-1].timestamp.isoformat() if fixtures else None

    return DatasetReadinessResponse(
        is_ready=True,
        sample_count=len(fixtures),
        threshold=20,
        data_source="synthetic_fixture",
        message=(
            f"Generated {len(fixtures)} clearly-labeled synthetic fixture observations. "
            "Suitable for development testing only — not real-world traffic data."
        ),
        real_sample_count=0,
        synthetic_sample_count=len(fixtures),
        earliest_timestamp=earliest,
        latest_timestamp=latest,
    )
