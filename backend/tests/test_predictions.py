"""
Comprehensive Unit and Integration Tests for Phase 11: Traffic Prediction / Forecasting.
"""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
from typing import Generator

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis import AnalysisSession, TrafficMetricsRecord
from app.models.prediction import PredictionItem, PredictionRun
from app.models.video import Video
from app.services.ml.dataset_extractor import DatasetExtractor, MIN_TRAINING_SAMPLES
from app.services.ml.feature_engineer import TrafficFeatureEngineer
from app.services.ml.traffic_predictor import TrafficPredictor, get_traffic_predictor

# Isolated SQLite test database
TEST_DB_PATH = Path(tempfile.gettempdir()) / "test_phase11_prediction.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create test tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except OSError:
            pass


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_dataset_extractor_synthetic_fixtures():
    """Verifies synthetic fixture generation produces valid, clearly-labeled chronological points."""
    fixtures = DatasetExtractor.generate_synthetic_fixtures(num_samples=50, interval_minutes=5)
    assert len(fixtures) == 50
    assert all(f.is_synthetic is True for f in fixtures)
    assert all(f.vehicle_volume >= 0 for f in fixtures)
    # Ensure chronological order
    for i in range(len(fixtures) - 1):
        assert fixtures[i].timestamp < fixtures[i + 1].timestamp


def test_dataset_readiness_insufficient_vs_sufficient(db_session):
    """Verifies readiness assessment correctly distinguishes insufficient vs sufficient real data."""
    extractor = DatasetExtractor(min_samples=20)
    
    # Empty DB -> Insufficient
    readiness = extractor.check_readiness(db_session)
    assert readiness.is_ready is False
    assert readiness.sample_count == 0
    assert readiness.threshold == 20
    assert "insufficient" in readiness.data_source

    # Add 25 real completed sessions with metrics
    base_time = datetime(2026, 9, 1, 8, 0, 0, tzinfo=timezone.utc)
    vid = Video(
        id="test_vid_pred",
        original_filename="test.mp4",
        storage_path="/tmp/test.mp4",
        status="ready",
    )
    db_session.add(vid)
    db_session.flush()

    for i in range(25):
        sess = AnalysisSession(
            id=f"sess_{i:03d}",
            video_id=vid.id,
            status="completed",
            started_at=base_time + timedelta(minutes=i * 5),
            total_frames_processed=100,
            total_vehicles_detected=10,
            total_vehicles_counted=5,
        )
        db_session.add(sess)
        db_session.flush()
        metrics = TrafficMetricsRecord(
            analysis_session_id=sess.id,
            observation_duration_seconds=300.0,
            total_volume=10 + (i % 5),
            flow_rate_per_minute=2.0,
            flow_rate_per_hour=120.0,
            is_extrapolated=True,
        )
        db_session.add(metrics)
    db_session.commit()

    # Now sufficient
    readiness_after = extractor.check_readiness(db_session)
    assert readiness_after.is_ready is True
    assert readiness_after.sample_count == 25
    assert readiness_after.data_source == "real_observations"
    assert readiness_after.session_count == 25
    assert readiness_after.status_code == "ready"


def test_feature_engineering_no_future_leakage():
    """
    Verifies that feature engineering strictly derives features from past observations
    and that modifying future observations does not change past feature rows.
    """
    import copy
    engineer = TrafficFeatureEngineer(lag_steps=3, rolling_window=3)
    fixtures_a = DatasetExtractor.generate_synthetic_fixtures(num_samples=40, random_seed=42)
    fixtures_b = copy.deepcopy(fixtures_a)

    res_a = engineer.build_features(fixtures_a, horizon_steps=1)
    k = 10
    target_ts = res_a.timestamps[k]

    # Mutate all future observations strictly after target_ts
    for pt in fixtures_b:
        if pt.timestamp > target_ts:
            pt.vehicle_volume = 9999.0
            pt.flow_rate_per_minute = 8888.0

    res_b = engineer.build_features(fixtures_b, horizon_steps=1)

    # Feature row at index k must be strictly identical before and after future mutation
    diff = float(np.max(np.abs(res_a.X[k] - res_b.X[k])))
    assert diff < 1e-9
    assert "lag_1_volume" in res_a.feature_names
    assert "rolling_mean_3_volume" in res_a.feature_names
    assert "is_peak_hour" in res_a.feature_names


def test_model_training_and_evaluation_vs_baseline():
    """Verifies that RandomForestRegressor trains, evaluates held-out test data, and computes metrics."""
    predictor = TrafficPredictor()
    fixtures = DatasetExtractor.generate_synthetic_fixtures(num_samples=60, random_seed=42)

    model, eval_result, feat_result = predictor.train_and_evaluate(
        data_points=fixtures,
        model_name="RandomForestRegressor",
        horizon_steps=1,
    )

    assert eval_result.model_name == "RandomForestRegressor"
    assert eval_result.training_samples > 0
    assert eval_result.test_samples > 0
    assert eval_result.mae >= 0.0
    assert eval_result.rmse >= 0.0
    assert eval_result.baseline_mae >= 0.0
    assert len(eval_result.feature_importances) == len(feat_result.feature_names)
    assert eval_result.data_source == "synthetic_fixture"


def test_alternative_models_training():
    """Verifies HistGradientBoostingRegressor and RidgeRegression train cleanly."""
    predictor = TrafficPredictor()
    fixtures = DatasetExtractor.generate_synthetic_fixtures(num_samples=60, random_seed=42)

    # Test Ridge
    _, eval_ridge, _ = predictor.train_and_evaluate(
        data_points=fixtures,
        model_name="RidgeRegression",
        horizon_steps=2,
    )
    assert eval_ridge.model_name == "RidgeRegression"
    assert eval_ridge.mae >= 0.0

    # Test HistGradientBoosting
    _, eval_hgb, _ = predictor.train_and_evaluate(
        data_points=fixtures,
        model_name="HistGradientBoostingRegressor",
        horizon_steps=1,
    )
    assert eval_hgb.model_name == "HistGradientBoostingRegressor"
    assert eval_hgb.mae >= 0.0


def test_forecast_generation_uncertainty_intervals():
    """Verifies multi-step forecast generation produces expanding empirical uncertainty intervals."""
    predictor = TrafficPredictor()
    fixtures = DatasetExtractor.generate_synthetic_fixtures(num_samples=60, random_seed=42)

    model, eval_result, _ = predictor.train_and_evaluate(
        data_points=fixtures,
        model_name="RandomForestRegressor",
        horizon_steps=3,
    )

    forecast = predictor.generate_forecast(
        model=model,
        eval_result=eval_result,
        recent_points=fixtures[-10:],
        num_steps=3,
        interval_minutes=5,
    )

    assert len(forecast) == 3
    for i, pt in enumerate(forecast, start=1):
        assert pt.step_index == i
        assert pt.lower_bound <= pt.predicted_value <= pt.upper_bound


def test_prediction_api_info_and_readiness(client):
    """Tests GET /api/v1/predictions/info and GET /api/v1/predictions/readiness."""
    resp_info = client.get("/api/v1/predictions/info")
    assert resp_info.status_code == 200
    info_data = resp_info.json()
    assert info_data["service_name"] == "TrafficPredictionEngine"
    assert "RandomForestRegressor" in info_data["supported_models"]
    assert "lag_1_volume" in info_data["feature_set"]

    resp_ready = client.get("/api/v1/predictions/readiness")
    assert resp_ready.status_code == 200
    ready_data = resp_ready.json()
    assert "is_ready" in ready_data
    assert "sample_count" in ready_data


def test_prediction_api_train_and_runs_lifecycle(client):
    """Tests POST /api/v1/predictions/train, listing runs, and retrieving run detail."""
    # 1. Train on synthetic fixtures
    train_payload = {
        "model_name": "RandomForestRegressor",
        "horizon_minutes": 15,
        "use_fixtures_if_insufficient": True,
    }
    resp_train = client.post("/api/v1/predictions/train", json=train_payload)
    assert resp_train.status_code == 201
    run_data = resp_train.json()
    run_id = run_data["id"]
    assert run_data["model_name"] == "RandomForestRegressor"
    assert run_data["data_source"] == "synthetic_fixture"
    assert len(run_data["predictions"]) == 3
    assert run_data["mae"] >= 0.0

    # 2. List prediction runs
    resp_list = client.get("/api/v1/predictions/runs")
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["total"] >= 1
    assert any(r["id"] == run_id for r in list_data["runs"])

    # 3. Retrieve run detail
    resp_detail = client.get(f"/api/v1/predictions/runs/{run_id}")
    assert resp_detail.status_code == 200
    detail_data = resp_detail.json()
    assert detail_data["id"] == run_id
    assert len(detail_data["predictions"]) == 3


def test_prediction_api_insufficient_data_rejection(client):
    """Tests that POST /api/v1/predictions/train without fixture flag returns 400 when data is insufficient."""
    train_payload = {
        "model_name": "RandomForestRegressor",
        "horizon_minutes": 15,
        "use_fixtures_if_insufficient": False,
    }
    resp = client.post("/api/v1/predictions/train", json=train_payload)
    assert resp.status_code == 400
    err_json = resp.json()
    err_msg = err_json.get("error", {}).get("message", "") or err_json.get("detail", "")
    assert "Insufficient real data" in err_msg


def test_real_data_training_and_forecasting_persistence(db_session, client):
    """Tests full lifecycle of training on genuine real-world records, provenance tagging, and persistence."""
    base_time = datetime(2026, 9, 1, 8, 0, 0, tzinfo=timezone.utc)
    vid = Video(
        id="test_vid_real_pred",
        original_filename="real_traffic_highway_cam.mp4",
        storage_path="/storage/real_traffic_highway_cam.mp4",
        source_type="real_world",
        status="ready",
    )
    db_session.add(vid)
    db_session.flush()

    for i in range(25):
        sess = AnalysisSession(
            id=f"real_sess_{i:03d}",
            video_id=vid.id,
            status="completed",
            started_at=base_time + timedelta(minutes=i * 5),
            total_frames_processed=100,
            total_vehicles_detected=10,
            total_vehicles_counted=5,
        )
        db_session.add(sess)
        db_session.flush()
        metrics = TrafficMetricsRecord(
            analysis_session_id=sess.id,
            observation_duration_seconds=300.0,
            total_volume=8 + (i % 6),
            flow_rate_per_minute=2.0,
            flow_rate_per_hour=120.0,
            is_extrapolated=True,
        )
        db_session.add(metrics)
    db_session.commit()

    # Train on real data via API
    resp = client.post(
        "/api/v1/predictions/train",
        json={"model_name": "RandomForestRegressor", "horizon_minutes": 15, "use_fixtures_if_insufficient": False},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["data_source"] == "real_observations"
    assert data["training_sample_count"] > 0
    assert data["test_sample_count"] > 0
    assert len(data["predictions"]) == 3

    # Query DB to confirm persistence
    run = db_session.scalars(select(PredictionRun).where(PredictionRun.id == data["id"])).first()
    assert run is not None
    assert run.data_source == "real_observations"
    assert len(run.predictions) == 3


def test_synthetic_pipeline_provenance_and_rejection(db_session, client):
    """Tests that synthetic pipeline data is never misclassified as real_observations and rejected for real forecasting."""
    base_time = datetime(2026, 9, 1, 8, 0, 0, tzinfo=timezone.utc)
    vid = Video(
        id="test_vid_syn_pipeline",
        original_filename="synthetic_test_bus_clip.mp4",
        storage_path="/scratch/synthetic_test_bus_clip.mp4",
        source_type="synthetic_test",
        status="ready",
    )
    db_session.add(vid)
    db_session.flush()

    for i in range(25):
        sess = AnalysisSession(
            id=f"syn_sess_{i:03d}",
            video_id=vid.id,
            status="completed",
            started_at=base_time + timedelta(minutes=i * 5),
            total_frames_processed=50,
            total_vehicles_detected=2,
            total_vehicles_counted=1,
        )
        db_session.add(sess)
        db_session.flush()
        metrics = TrafficMetricsRecord(
            analysis_session_id=sess.id,
            observation_duration_seconds=300.0,
            total_volume=5,
            flow_rate_per_minute=1.0,
            flow_rate_per_hour=60.0,
            is_extrapolated=True,
        )
        db_session.add(metrics)
    db_session.commit()

    # 1. Check readiness API reports not ready for real forecasting
    r_ready = client.get("/api/v1/predictions/readiness")
    assert r_ready.status_code == 200
    ready_data = r_ready.json()
    assert ready_data["is_ready"] is False
    assert ready_data["real_sample_count"] == 0
    assert ready_data["synthetic_sample_count"] == 25
    assert ready_data["status_code"] == "synthetic_pipeline_only"

    # 2. POST /train without fallback must be rejected with 400
    r_fail = client.post(
        "/api/v1/predictions/train",
        json={"model_name": "RandomForestRegressor", "use_fixtures_if_insufficient": False},
    )
    assert r_fail.status_code == 400
    assert "Insufficient genuine real-world observations" in r_fail.json()["error"]["message"]

    # 3. POST /train with fallback allowed must train and persist as synthetic_pipeline
    r_train = client.post(
        "/api/v1/predictions/train",
        json={"model_name": "RandomForestRegressor", "use_fixtures_if_insufficient": True},
    )
    assert r_train.status_code == 201
    train_data = r_train.json()
    assert train_data["data_source"] == "synthetic_pipeline"

    # 4. Confirm persistence in database
    run = db_session.scalars(select(PredictionRun).where(PredictionRun.id == train_data["id"])).first()
    assert run is not None
    assert run.data_source == "synthetic_pipeline"
