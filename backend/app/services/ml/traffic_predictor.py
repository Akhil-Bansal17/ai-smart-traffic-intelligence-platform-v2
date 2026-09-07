"""
Traffic Prediction and Forecasting Service.
Phase 11: Traffic Prediction / Forecasting.

Trains, evaluates, and persists classical explainable ML regression models on chronological traffic data.
Features strict temporal train/test validation, baseline comparisons, and empirical uncertainty bands.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.prediction import PredictionItem, PredictionRun
from app.services.ml.dataset_extractor import DatasetExtractor, TrafficDataPoint
from app.services.ml.feature_engineer import FeatureMatrixResult, TrafficFeatureEngineer

logger = get_logger(__name__)


@dataclass
class ForecastPoint:
    """A single forecast point with timestamp and prediction interval."""
    step_index: int
    timestamp: str
    predicted_value: float
    lower_bound: float
    upper_bound: float


@dataclass
class ModelEvaluationResult:
    """Comprehensive evaluation metrics comparing trained model against baseline."""
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
    r2_score: Optional[float]
    baseline_mae: float
    baseline_rmse: float
    baseline_improvement_pct: float
    feature_names: List[str]
    feature_importances: Dict[str, float]
    residual_std: float


@dataclass
class ForecastResult:
    """Complete prediction output containing evaluation metrics and future forecast points."""
    run_id: str
    model_name: str
    data_source: str
    generated_at: str
    evaluation: ModelEvaluationResult
    forecast: List[ForecastPoint]


class NaivePersistenceBaseline:
    """Simple baseline model that predicts the latest observed volume (y_t+h = y_t)."""
    def fit(self, X: np.ndarray, y: np.ndarray) -> "NaivePersistenceBaseline":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        # lag_1_volume is assumed at index 0 of X
        return X[:, 0].copy()


class TrafficPredictor:
    """
    Orchestrates training, chronological validation, multi-step forecasting, and DB persistence.
    """

    SUPPORTED_MODELS = {
        "RandomForestRegressor": lambda: RandomForestRegressor(
            n_estimators=50, max_depth=6, min_samples_split=3, random_state=42
        ),
        "HistGradientBoostingRegressor": lambda: HistGradientBoostingRegressor(
            max_iter=50, max_depth=4, random_state=42
        ),
        "RidgeRegression": lambda: Ridge(alpha=1.0, random_state=42),
    }

    def __init__(
        self,
        extractor: Optional[DatasetExtractor] = None,
        feature_engineer: Optional[TrafficFeatureEngineer] = None,
    ):
        self.extractor = extractor or DatasetExtractor()
        self.feature_engineer = feature_engineer or TrafficFeatureEngineer()

    def train_and_evaluate(
        self,
        data_points: List[TrafficDataPoint],
        model_name: str = "RandomForestRegressor",
        horizon_steps: int = 1,
        interval_minutes: int = 5,
        test_ratio: float = 0.25,
    ) -> Tuple[Any, ModelEvaluationResult, FeatureMatrixResult]:
        """
        Builds feature matrix, splits chronologically, trains model, and evaluates against baseline.
        """
        if model_name not in self.SUPPORTED_MODELS and model_name != "NaivePersistenceBaseline":
            raise AppException(
                f"Unsupported model '{model_name}'. Supported: {list(self.SUPPORTED_MODELS.keys())}",
                status_code=422,
            )

        # 1. Feature Engineering
        feat_result = self.feature_engineer.build_features(
            data_points=data_points,
            horizon_steps=horizon_steps,
        )
        X, y = feat_result.X, feat_result.y
        n_samples = len(X)

        if n_samples < 8:
            raise AppException(
                f"Feature matrix has too few valid samples ({n_samples}) for training and testing.",
                status_code=422,
            )

        # 2. Strict Chronological Train/Test Split (No random shuffling)
        split_idx = int(n_samples * (1.0 - test_ratio))
        split_idx = max(4, min(n_samples - 2, split_idx))

        X_train, y_train = X[:split_idx], y[:split_idx]
        X_test, y_test = X[split_idx:], y[split_idx:]

        # 3. Fit Baseline Model
        baseline = NaivePersistenceBaseline()
        baseline.fit(X_train, y_train)
        y_pred_baseline = baseline.predict(X_test)
        baseline_mae = float(mean_absolute_error(y_test, y_pred_baseline))
        baseline_rmse = float(math.sqrt(mean_squared_error(y_test, y_pred_baseline)))

        # 4. Fit Target Model
        t0 = time.perf_counter()
        if model_name == "NaivePersistenceBaseline":
            model = baseline
            model_type = "baseline"
        else:
            model = self.SUPPORTED_MODELS[model_name]()
            model.fit(X_train, y_train)
            model_type = "ensemble_tree" if "Forest" in model_name or "Boosting" in model_name else "linear_regularized"

        training_time_ms = (time.perf_counter() - t0) * 1000

        # 5. Evaluate on Held-Out Chronological Test Set
        y_pred_test = model.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred_test))
        rmse = float(math.sqrt(mean_squared_error(y_test, y_pred_test)))

        # R2 score (meaningful only if variance > 0 and len >= 3)
        if len(y_test) >= 3 and np.var(y_test) > 1e-6:
            r2 = float(r2_score(y_test, y_pred_test))
        else:
            r2 = None

        # Residual std for empirical prediction interval
        residuals = y_test - y_pred_test
        residual_std = float(np.std(residuals)) if len(residuals) > 1 else 1.0

        # Baseline Improvement %
        improvement_pct = (
            ((baseline_mae - mae) / baseline_mae * 100.0)
            if baseline_mae > 1e-6
            else 0.0
        )

        # 6. Extract Feature Importances
        importances: Dict[str, float] = {}
        if hasattr(model, "feature_importances_"):
            raw_imp = model.feature_importances_
            for name, val in zip(feat_result.feature_names, raw_imp):
                importances[name] = round(float(val), 4)
        elif hasattr(model, "coef_"):
            raw_coef = np.abs(model.coef_)
            total_coef = np.sum(raw_coef) + 1e-6
            for name, val in zip(feat_result.feature_names, raw_coef):
                importances[name] = round(float(val / total_coef), 4)
        else:
            # Baseline uses strictly lag_1
            for name in feat_result.feature_names:
                importances[name] = 1.0 if name == "lag_1_volume" else 0.0

        # Determine precise data source provenance
        sources = set(getattr(dp, "data_source", "real_observations") for dp in data_points)
        if "synthetic_fixture" in sources:
            data_source = "synthetic_fixture"
        elif "synthetic_pipeline" in sources or any(dp.is_synthetic for dp in data_points):
            data_source = "synthetic_pipeline"
        else:
            data_source = "real_observations"

        eval_result = ModelEvaluationResult(
            model_name=model_name,
            model_type=model_type,
            data_source=data_source,
            target_variable="vehicle_volume",
            horizon_minutes=horizon_steps * interval_minutes,
            training_samples=len(X_train),
            test_samples=len(X_test),
            training_time_ms=round(training_time_ms, 2),
            mae=round(mae, 3),
            rmse=round(rmse, 3),
            r2_score=round(r2, 3) if r2 is not None else None,
            baseline_mae=round(baseline_mae, 3),
            baseline_rmse=round(baseline_rmse, 3),
            baseline_improvement_pct=round(improvement_pct, 2),
            feature_names=feat_result.feature_names,
            feature_importances=importances,
            residual_std=round(residual_std, 3),
        )

        return model, eval_result, feat_result

    def generate_forecast(
        self,
        model: Any,
        eval_result: ModelEvaluationResult,
        recent_points: List[TrafficDataPoint],
        num_steps: int = 3,
        interval_minutes: int = 5,
    ) -> List[ForecastPoint]:
        """
        Generates forward multi-step forecast points with empirical uncertainty bounds.
        """
        sorted_points = sorted(recent_points, key=lambda x: x.timestamp)
        latest_ts = sorted_points[-1].timestamp
        forecast_points: List[ForecastPoint] = []

        # Rolling autoregressive forecast
        current_points = list(sorted_points)

        for step in range(1, num_steps + 1):
            future_ts = latest_ts + timedelta(minutes=step * interval_minutes)
            vector, _ = self.feature_engineer.extract_inference_vector(
                recent_points=current_points,
                target_timestamp=future_ts,
            )

            pred_val = float(model.predict(vector)[0])
            pred_val = max(0.0, round(pred_val, 1))

            # Empirical prediction interval: 1.96 * residual_std (expanding slightly with horizon step)
            margin = max(1.0, 1.96 * eval_result.residual_std * math.sqrt(step))
            lower = max(0.0, round(pred_val - margin, 1))
            upper = round(pred_val + margin, 1)

            forecast_points.append(
                ForecastPoint(
                    step_index=step,
                    timestamp=future_ts.isoformat(),
                    predicted_value=pred_val,
                    lower_bound=lower,
                    upper_bound=upper,
                )
            )

            # Append synthetic predicted point for next step autoregression
            current_points.append(
                TrafficDataPoint(
                    timestamp=future_ts,
                    vehicle_volume=pred_val,
                    flow_rate_per_minute=pred_val / interval_minutes,
                    inbound_count=int(pred_val * 0.5),
                    outbound_count=int(pred_val * 0.5),
                    observation_duration_seconds=float(interval_minutes * 60),
                    session_id="forecast_step",
                    is_synthetic=True,
                    data_source=eval_result.data_source,
                )
            )

        return forecast_points

    def execute_and_persist(
        self,
        db: Session,
        model_name: str = "RandomForestRegressor",
        horizon_minutes: int = 15,
        use_fixtures_if_insufficient: bool = False,
    ) -> ForecastResult:
        """
        High-level orchestrator: loads data from DB (or fixtures if explicitly allowed),
        trains model, evaluates against baseline, generates predictions, and saves to database.
        Strictly enforces that synthetic data is never labeled as real_observations.
        """
        all_db_points = self.extractor.extract_from_db(db)
        real_points = [p for p in all_db_points if not p.is_synthetic]
        synthetic_pipeline_points = [p for p in all_db_points if p.is_synthetic]

        if len(real_points) >= self.extractor.min_samples:
            data_points = real_points
        elif not use_fixtures_if_insufficient:
            raise AppException(
                f"Insufficient real data: Insufficient genuine real-world observations in database ({len(real_points)} < {self.extractor.min_samples}). "
                "Cannot train model without genuine real-world traffic data. Set use_fixtures_if_insufficient=True to test using synthetic data.",
                status_code=400,
            )
        elif len(synthetic_pipeline_points) >= self.extractor.min_samples:
            # Test pipeline observations exist from CV execution on synthetic videos
            data_points = synthetic_pipeline_points
        else:
            # Generate transparent development fixtures
            data_points = self.extractor.generate_synthetic_fixtures(num_samples=120)

        interval_minutes = 5
        horizon_steps = max(1, horizon_minutes // interval_minutes)

        # Train & Evaluate
        model, eval_result, _ = self.train_and_evaluate(
            data_points=data_points,
            model_name=model_name,
            horizon_steps=horizon_steps,
            interval_minutes=interval_minutes,
        )

        # Generate Forecast Points
        forecast_points = self.generate_forecast(
            model=model,
            eval_result=eval_result,
            recent_points=data_points[-10:],
            num_steps=horizon_steps,
            interval_minutes=interval_minutes,
        )

        # Persist to Database
        run_record = PredictionRun(
            model_name=eval_result.model_name,
            model_type=eval_result.model_type,
            target_variable=eval_result.target_variable,
            horizon_minutes=eval_result.horizon_minutes,
            data_source=eval_result.data_source,
            training_sample_count=eval_result.training_samples,
            test_sample_count=eval_result.test_samples,
            training_time_ms=eval_result.training_time_ms,
            mae=eval_result.mae,
            rmse=eval_result.rmse,
            r2_score=eval_result.r2_score,
            baseline_mae=eval_result.baseline_mae,
            baseline_rmse=eval_result.baseline_rmse,
            feature_names=eval_result.feature_names,
            feature_importances=eval_result.feature_importances,
            model_params={"random_state": 42},
        )
        db.add(run_record)
        db.flush()

        for fp in forecast_points:
            item_record = PredictionItem(
                prediction_run_id=run_record.id,
                step_index=fp.step_index,
                timestamp=datetime.fromisoformat(fp.timestamp),
                predicted_value=fp.predicted_value,
                lower_bound=fp.lower_bound,
                upper_bound=fp.upper_bound,
            )
            db.add(item_record)

        db.commit()
        db.refresh(run_record)

        logger.info(
            "Persisted PredictionRun %s: %s (data_source=%s, MAE=%.3f, Baseline MAE=%.3f)",
            run_record.id,
            run_record.model_name,
            run_record.data_source,
            run_record.mae,
            run_record.baseline_mae,
        )

        return ForecastResult(
            run_id=run_record.id,
            model_name=run_record.model_name,
            data_source=run_record.data_source,
            generated_at=run_record.created_at.isoformat(),
            evaluation=eval_result,
            forecast=forecast_points,
        )


_global_traffic_predictor: Optional[TrafficPredictor] = None


def get_traffic_predictor() -> TrafficPredictor:
    """Returns singleton TrafficPredictor instance."""
    global _global_traffic_predictor
    if _global_traffic_predictor is None:
        _global_traffic_predictor = TrafficPredictor()
    return _global_traffic_predictor
