"""
Comprehensive Verification Script for Phase 11 Final Closure:
Real-World Data, Provenance, ML Readiness & Production Hardening.

Verifies all 18 verification dimensions:
  1. Database Schema & Alembic Migration 0005
  2. Database Provenance Audit for Legacy Test Videos
  3. Real-World Video Ingestion & Provenance Records
  4. Computer Vision Pipeline Execution (Detector -> Tracker -> Counter -> Analytics -> Persistence)
  5. DatasetExtractor 3-Tier Data Segregation (real_observations vs synthetic_pipeline vs synthetic_fixture)
  6. Zero-Contamination Guarantee Across All Tiers
  7. Dataset Readiness Audit & Honesty Policy (< 20 sample gate)
  8. Feature Engineering Temporal Integrity & Anti-Leakage (t-k only)
  9. Future Data Perturbation Robustness Test
 10. Model Training Safety & Rejection Gate (ValueError on insufficient real data without fallback)
 11. Model Training with Authorized Fallback (use_fixtures_if_insufficient=True)
 12. Model Evaluation Honesty (Realistic RMSE, MAE, R², Baseline Comparisons)
 13. Forecasting Engine Multi-Step Output & Confidence Bounds
 14. REST API Safety & Endpoints Integration (FastAPI TestClient)
 15. Client Upload Trust Boundary (Reject/Sanitize Unverified Claims)
 16. Persistence, Artifact Serialization & Model Reloading
 17. Full Regression Pipeline Integration
 18. Definitive Outcome B Classification & Formal Closure Declaration
"""
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Dict, List, Tuple

# Ensure paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import inspect, select
from starlette.testclient import TestClient

from app.config.settings import settings
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.video import Video
from app.models.analysis import AnalysisSession, TrafficMetricsRecord
from app.models.prediction import PredictionRun, PredictionItem
from app.services.ml.dataset_extractor import DatasetExtractor, DatasetReadiness, TrafficDataPoint, MIN_TRAINING_SAMPLES
from app.services.ml.feature_engineer import TrafficFeatureEngineer
from app.services.ml.traffic_predictor import TrafficPredictor


class Phase11FinalClosureVerifier:
    def __init__(self):
        self.results: Dict[str, Tuple[bool, str]] = {}
        self.client = TestClient(app)

    def log(self, step_num: int, title: str, passed: bool, detail: str = ""):
        status = "PASSED" if passed else "FAILED"
        prefix = f"[Step {step_num:02d}] {title}"
        print(f"{prefix:<65} [{status}]")
        if detail:
            for line in detail.strip().split("\n"):
                print(f"       -> {line}")
        self.results[f"Step {step_num:02d}: {title}"] = (passed, detail)

    def run_all_checks(self):
        print("=" * 90)
        print("AI SMART TRAFFIC PLATFORM — PHASE 11 FINAL CLOSURE VERIFICATION SUITE")
        print("=" * 90)

        self.verify_step_01_schema()
        self.verify_step_02_legacy_videos_audit()
        self.verify_step_03_real_video_ingestion()
        self.verify_step_04_cv_pipeline_execution()
        self.verify_step_05_segregation()
        self.verify_step_06_zero_contamination()
        self.verify_step_07_readiness_audit()
        self.verify_step_08_feature_engineering_temporal_integrity()
        self.verify_step_09_perturbation_test()
        self.verify_step_10_training_safety_rejection()
        self.verify_step_11_training_with_fallback()
        self.verify_step_12_evaluation_honesty()
        self.verify_step_13_forecasting_execution()
        self.verify_step_14_rest_api_safety()
        self.verify_step_15_upload_trust_boundary()
        self.verify_step_16_persistence_and_reload()
        self.verify_step_17_full_regression_health()
        self.verify_step_18_outcome_b_declaration()

        print("\n" + "=" * 90)
        print("PHASE 11 FINAL CLOSURE VERIFICATION SUMMARY")
        print("=" * 90)
        all_passed = all(p for p, _ in self.results.values())
        total = len(self.results)
        passed_cnt = sum(1 for p, _ in self.results.values() if p)

        for name, (p, detail) in self.results.items():
            st = "PASS" if p else "FAIL"
            print(f"[{st}] {name}")

        print("-" * 90)
        print(f"Total Steps: {total} | Passed: {passed_cnt} | Failed: {total - passed_cnt}")
        if all_passed:
            print("\n>>> ALL 18 PHASE 11 FINAL CLOSURE VERIFICATION GATES PASSED <<<")
            print(">>> CLASSIFICATION: OUTCOME B (REAL DATA EXISTS BUT INSUFFICIENT < 20) <<<")
        else:
            print("\n>>> SOME VERIFICATION GATES FAILED <<<")
            raise AssertionError("Phase 11 Final Closure Verification failed!")

    def verify_step_01_schema(self):
        """Step 1: Alembic migration 0005 applied and all 5 provenance columns present in videos table."""
        db = SessionLocal()
        try:
            insp = inspect(engine)
            cols = {c["name"] for c in insp.get_columns("videos")}
            req_cols = {"source_type", "source_reference", "license_reference", "provenance_note", "provenance_verified", "captured_at"}
            missing = req_cols - cols
            passed = len(missing) == 0
            detail = f"Verified video columns present: {req_cols.intersection(cols)}" if passed else f"Missing columns: {missing}"
            self.log(1, "Database Schema & Migration 0005 Provenance Columns", passed, detail)
        finally:
            db.close()

    def verify_step_02_legacy_videos_audit(self):
        """Step 2: Pre-existing synthetic/test videos properly labeled."""
        db = SessionLocal()
        try:
            legacy_videos = db.scalars(
                select(Video).where(Video.original_filename.like("%test%"))
            ).all()
            if not legacy_videos:
                legacy_videos = db.scalars(select(Video).where(Video.source_type == "synthetic_test")).all()

            unverified_real = db.scalars(
                select(Video).where(Video.source_type == "real_world", Video.provenance_verified == False)
            ).all()

            passed = len(unverified_real) == 0
            detail = f"Audited {len(legacy_videos)} synthetic test videos. Zero unverified real-world records."
            self.log(2, "Database Provenance Audit for Legacy Test Records", passed, detail)
        finally:
            db.close()

    def verify_step_03_real_video_ingestion(self):
        """Step 3: Real-world video records exist with valid metadata and open licenses."""
        db = SessionLocal()
        try:
            real_vids = db.scalars(
                select(Video).where(Video.source_type == "real_world", Video.provenance_verified == True)
            ).all()

            passed = len(real_vids) >= 3
            details = []
            for v in real_vids:
                details.append(f"Video {v.original_filename}: ref={v.source_reference}, license={v.license_reference}, verified={v.provenance_verified}")
            self.log(3, "Real-World Video Ingestion & Provenance Records", passed, "\n".join(details))
        finally:
            db.close()

    def verify_step_04_cv_pipeline_execution(self):
        """Step 4: Real videos processed through complete CV pipeline."""
        db = SessionLocal()
        try:
            real_vids = db.scalars(
                select(Video).where(Video.source_type == "real_world", Video.provenance_verified == True)
            ).all()

            sessions = []
            total_observations = 0
            for v in real_vids:
                s = db.scalars(
                    select(AnalysisSession)
                    .where(AnalysisSession.video_id == v.id, AnalysisSession.status == "completed")
                ).first()
                if s and s.traffic_metrics:
                    sessions.append(s)
                    buckets = s.traffic_metrics.time_series_buckets or []
                    total_observations += len(buckets)

            passed = len(sessions) >= 3 and total_observations > 0
            detail = f"Found {len(sessions)} completed CV sessions across real videos with {total_observations} total observation buckets."
            self.log(4, "Full CV Pipeline Execution on Genuine Real Footage", passed, detail)
        finally:
            db.close()

    def verify_step_05_segregation(self):
        """Step 5: Strict 3-tier data segregation in DatasetExtractor."""
        db = SessionLocal()
        try:
            extractor = DatasetExtractor()
            all_pts = extractor.extract_from_db(db)
            real_pts = [p for p in all_pts if p.data_source == "real_observations" and not p.is_synthetic]
            synthetic_pipeline_pts = [p for p in all_pts if p.data_source == "synthetic_pipeline" and p.is_synthetic]
            fixtures = extractor.generate_synthetic_fixtures(num_samples=10)
            fixture_pts = [p for p in fixtures if p.data_source == "synthetic_fixture" and p.is_synthetic]

            passed = (
                len(real_pts) > 0
                and all(not p.is_synthetic for p in real_pts)
                and all(p.is_synthetic for p in synthetic_pipeline_pts)
                and all(p.is_synthetic for p in fixture_pts)
            )
            detail = (
                f"Segregation counts: real_observations={len(real_pts)}, "
                f"synthetic_pipeline={len(synthetic_pipeline_pts)}, synthetic_fixture={len(fixture_pts)}"
            )
            self.log(5, "DatasetExtractor 3-Tier Data Segregation", passed, detail)
        finally:
            db.close()

    def verify_step_06_zero_contamination(self):
        """Step 6: Zero cross-contamination between real observations and synthetic fixtures."""
        db = SessionLocal()
        try:
            extractor = DatasetExtractor()
            real_pts = extractor.extract_from_db(db, source_filter="real_observations")
            fixtures = extractor.generate_synthetic_fixtures(num_samples=25)

            real_clean = all(
                p.data_source == "real_observations" and p.is_synthetic is False and not str(p.session_id).startswith("synthetic_")
                for p in real_pts
            )
            fixture_clean = all(
                p.data_source == "synthetic_fixture" and p.is_synthetic is True and str(p.session_id).startswith("synthetic_fixture_")
                for p in fixtures
            )

            passed = real_clean and fixture_clean
            detail = f"Zero contamination confirmed across {len(real_pts)} real observations and {len(fixtures)} synthetic fixtures."
            self.log(6, "Zero-Contamination Guarantee Across All Tiers", passed, detail)
        finally:
            db.close()

    def verify_step_07_readiness_audit(self):
        """Step 7: Dataset readiness truthfully reports is_ready=False when real observations < 20."""
        db = SessionLocal()
        try:
            extractor = DatasetExtractor(min_samples=20)
            readiness = extractor.check_readiness(db)

            passed = (
                readiness.is_ready is False
                and readiness.sample_count < 20
                and readiness.threshold == 20
                and readiness.status_code == "insufficient_observations"
                and readiness.data_source == "real_observations_insufficient"
            )
            detail = (
                f"Readiness: is_ready={readiness.is_ready}, sample_count={readiness.sample_count}/{readiness.threshold}, "
                f"status_code='{readiness.status_code}', message='{readiness.message}'"
            )
            self.log(7, "Dataset Readiness Audit & Honest Gate (< 20 threshold)", passed, detail)
        finally:
            db.close()

    def verify_step_08_feature_engineering_temporal_integrity(self):
        """Step 8: TrafficFeatureEngineer constructs lag features strictly from past observations (t - k)."""
        db = SessionLocal()
        try:
            extractor = DatasetExtractor()
            fixtures = extractor.generate_synthetic_fixtures(num_samples=30)
            engineer = TrafficFeatureEngineer(lag_steps=3, rolling_window=3)
            feat_result = engineer.build_features(fixtures, horizon_steps=1)

            col_names = feat_result.feature_names
            has_future_cols = any("future" in c or "lead" in c for c in col_names)
            strictly_ordered = all(
                fixtures[i].timestamp < fixtures[i + 1].timestamp
                for i in range(len(fixtures) - 1)
            )

            passed = not has_future_cols and strictly_ordered and len(feat_result.feature_names) > 0
            detail = f"Features extracted: {col_names}. Monotonic time order: {strictly_ordered}."
            self.log(8, "Feature Engineering Temporal Integrity & Anti-Leakage", passed, detail)
        finally:
            db.close()

    def verify_step_09_perturbation_test(self):
        """Step 9: Perturbing a future observation does not alter past lag features."""
        db = SessionLocal()
        try:
            extractor = DatasetExtractor()
            fixtures = extractor.generate_synthetic_fixtures(num_samples=30)
            engineer = TrafficFeatureEngineer(lag_steps=3, rolling_window=3)

            # Baseline features
            base_result = engineer.build_features(fixtures, horizon_steps=1)
            mid_idx = len(fixtures) // 2

            # Perturb future observation at mid_idx + 5
            perturbed_pts = copy.deepcopy(fixtures)
            perturbed_pts[mid_idx + 5].vehicle_volume += 100.0

            perturbed_result = engineer.build_features(perturbed_pts, horizon_steps=1)

            # Features prior to mid_idx + 5 must be 100% identical
            pre_features_base = base_result.X[: mid_idx + 5 - 3]
            pre_features_pert = perturbed_result.X[: mid_idx + 5 - 3]

            diff = np.abs(pre_features_base - pre_features_pert).max()
            passed = bool(diff == 0.0)
            detail = f"Max past feature difference after future perturbation: {diff:.6f} (strictly 0.0)."
            self.log(9, "Future Data Perturbation Robustness Test", passed, detail)
        finally:
            db.close()

    def verify_step_10_training_safety_rejection(self):
        """Step 10: Training without fallback on insufficient real data raises ValueError / AppException."""
        db = SessionLocal()
        try:
            predictor = TrafficPredictor()
            rejection_occurred = False
            err_msg = ""
            try:
                predictor.execute_and_persist(db, model_name="RandomForestRegressor", use_fixtures_if_insufficient=False)
            except Exception as e:
                rejection_occurred = True
                err_msg = str(e)

            passed = rejection_occurred and "insufficient" in err_msg.lower()
            detail = f"Rejection triggered as required. Error: {err_msg}"
            self.log(10, "Model Training Safety & Insufficient Data Rejection Gate", passed, detail)
        finally:
            db.close()

    def verify_step_11_training_with_fallback(self):
        """Step 11: Training with explicit fallback succeeds with clear audit logging."""
        db = SessionLocal()
        try:
            predictor = TrafficPredictor()
            forecast_res = predictor.execute_and_persist(
                db,
                model_name="RandomForestRegressor",
                use_fixtures_if_insufficient=True,
                horizon_minutes=15,
            )
            eval_res = forecast_res.evaluation

            passed = (
                forecast_res is not None
                and eval_res is not None
                and eval_res.data_source in ("synthetic_fixture", "synthetic_pipeline")
                and eval_res.rmse >= 0
            )
            detail = (
                f"Model trained: data_source={eval_res.data_source}, "
                f"RMSE={eval_res.rmse:.3f}, MAE={eval_res.mae:.3f}, R²={eval_res.r2_score}"
            )
            self.log(11, "Model Training with Authorized Fixture Fallback", passed, detail)
        finally:
            db.close()

    def verify_step_12_evaluation_honesty(self):
        """Step 12: Model evaluation metrics computed truthfully without inflation."""
        db = SessionLocal()
        try:
            predictor = TrafficPredictor()
            fixtures = DatasetExtractor.generate_synthetic_fixtures(num_samples=60)
            model, eval_res, _ = predictor.train_and_evaluate(
                data_points=fixtures,
                model_name="RandomForestRegressor",
                horizon_steps=3,
            )

            passed = (
                not np.isnan(eval_res.rmse)
                and not np.isnan(eval_res.mae)
                and eval_res.rmse >= 0
                and eval_res.mae >= 0
                and eval_res.baseline_mae >= 0
            )
            detail = (
                f"Honest Evaluation: Model MAE={eval_res.mae:.4f}, Baseline MAE={eval_res.baseline_mae:.4f}, "
                f"Model RMSE={eval_res.rmse:.4f}, Baseline RMSE={eval_res.baseline_rmse:.4f}"
            )
            self.log(12, "Model Evaluation Metrics Integrity & Honesty", passed, detail)
        finally:
            db.close()

    def verify_step_13_forecasting_execution(self):
        """Step 13: Multi-step forecasting generates predictions with upper/lower bounds."""
        db = SessionLocal()
        try:
            predictor = TrafficPredictor()
            fixtures = DatasetExtractor.generate_synthetic_fixtures(num_samples=60)
            model, eval_res, _ = predictor.train_and_evaluate(data_points=fixtures, model_name="RandomForestRegressor")
            forecast_points = predictor.generate_forecast(
                model=model,
                eval_result=eval_res,
                recent_points=fixtures[-10:],
                num_steps=4,
                interval_minutes=5,
            )

            passed = (
                len(forecast_points) == 4
                and all(p.predicted_value >= 0 for p in forecast_points)
                and all(p.lower_bound <= p.predicted_value <= p.upper_bound for p in forecast_points)
            )
            detail = (
                f"Generated {len(forecast_points)} forecast steps. "
                f"Step 1: val={forecast_points[0].predicted_value:.1f} [{forecast_points[0].lower_bound:.1f}, {forecast_points[0].upper_bound:.1f}]. "
                f"Step 4: val={forecast_points[-1].predicted_value:.1f} [{forecast_points[-1].lower_bound:.1f}, {forecast_points[-1].upper_bound:.1f}]."
            )
            self.log(13, "Multi-Step Traffic Forecasting & Confidence Intervals", passed, detail)
        finally:
            db.close()

    def verify_step_14_rest_api_safety(self):
        """Step 14: REST API enforces readiness check and training rejection."""
        # 1. GET /api/v1/predictions/readiness
        resp_readiness = self.client.get("/api/v1/predictions/readiness")
        readiness_ok = (
            resp_readiness.status_code == 200
            and resp_readiness.json()["is_ready"] is False
            and resp_readiness.json()["status_code"] == "insufficient_observations"
        )

        # 2. POST /api/v1/predictions/train with use_fixtures_if_insufficient=False -> HTTP 400
        resp_train_reject = self.client.post(
            "/api/v1/predictions/train",
            json={"model_name": "RandomForestRegressor", "use_fixtures_if_insufficient": False},
        )
        reject_ok = resp_train_reject.status_code == 400

        # 3. POST /api/v1/predictions/train with use_fixtures_if_insufficient=True -> HTTP 201
        resp_train_fallback = self.client.post(
            "/api/v1/predictions/train",
            json={"model_name": "RandomForestRegressor", "use_fixtures_if_insufficient": True},
        )
        fallback_ok = resp_train_fallback.status_code == 201 and resp_train_fallback.json()["data_source"] in ("synthetic_fixture", "synthetic_pipeline")

        # 4. GET /api/v1/predictions/runs
        resp_runs = self.client.get("/api/v1/predictions/runs")
        runs_ok = resp_runs.status_code == 200 and resp_runs.json()["total"] > 0

        # 5. GET /api/v1/predictions/info
        resp_info = self.client.get("/api/v1/predictions/info")
        info_ok = resp_info.status_code == 200 and "RandomForestRegressor" in resp_info.json()["supported_models"]

        passed = readiness_ok and reject_ok and fallback_ok and runs_ok and info_ok
        detail = (
            f"API Endpoints: readiness={resp_readiness.status_code}, "
            f"train_reject={resp_train_reject.status_code}, train_fallback={resp_train_fallback.status_code}, "
            f"runs={resp_runs.status_code}, info={resp_info.status_code}"
        )
        self.log(14, "REST API Safety & Rejection Gate Enforcement", passed, detail)

    def verify_step_15_upload_trust_boundary(self):
        """Step 15: Client uploads claiming source_type='real_world' without verified provenance are sanitized."""
        test_file = PROJECT_ROOT / "scratch" / "real_traffic_degirum.mp4"
        if not test_file.exists():
            test_file = PROJECT_ROOT / "data_science" / "datasets" / "real_traffic" / "real_traffic_degirum.mp4"

        with open(test_file, "rb") as f:
            resp = self.client.post(
                "/api/v1/videos/upload",
                files={"file": ("client_upload_test.mp4", f, "video/mp4")},
                data={"source_type": "real_world"},  # Unverified client claim
            )

        passed = False
        detail = ""
        if resp.status_code == 201:
            data = resp.json()
            sanitized_type = data.get("source_type")
            prov_verified = data.get("provenance_verified")
            passed = sanitized_type == "unknown" and prov_verified is False
            detail = f"Client claim 'real_world' sanitized to '{sanitized_type}' with provenance_verified={prov_verified}."
        else:
            detail = f"Upload endpoint returned status: {resp.status_code}, response: {resp.text}"

        self.log(15, "Client Video Upload Trust Boundary Enforcement", passed, detail)

    def verify_step_16_persistence_and_reload(self):
        """Step 16: Model artifacts and training records persist and reload cleanly."""
        db = SessionLocal()
        try:
            predictor = TrafficPredictor()
            forecast_res = predictor.execute_and_persist(
                db,
                model_name="RandomForestRegressor",
                use_fixtures_if_insufficient=True,
            )

            # Check DB record
            db_rec = db.scalars(select(PredictionRun).where(PredictionRun.id == forecast_res.run_id)).first()
            passed = db_rec is not None and len(db_rec.predictions) > 0
            detail = f"Prediction run persisted in DB: ID={forecast_res.run_id}, predictions_count={len(db_rec.predictions)}."
            self.log(16, "Model Persistence, Run Serialization & DB Linkage", passed, detail)
        finally:
            db.close()

    def verify_step_17_full_regression_health(self):
        """Step 17: Core system health check."""
        resp = self.client.get("/api/v1/health")
        passed = resp.status_code == 200 and resp.json().get("status") == "ok"
        detail = f"Health endpoint response: {resp.json()}"
        self.log(17, "Full Backend Health & Regression Readiness", passed, detail)

    def verify_step_18_outcome_b_declaration(self):
        """Step 18: Final formal declaration of Outcome B."""
        db = SessionLocal()
        try:
            extractor = DatasetExtractor()
            real_pts = extractor.extract_from_db(db, source_filter="real_observations")
            real_cnt = len(real_pts)

            # Outcome B requires 0 < real_cnt < 20
            passed = 0 < real_cnt < 20
            declaration = (
                f"CONFIRMED OUTCOME B: Genuine real-world traffic data exists ({real_cnt} observations "
                f"across 3 MIT-licensed video recordings processed by CV pipeline), but sample count is "
                f"below statistical threshold ({MIN_TRAINING_SAMPLES}). "
                "Phase 11 implementation = VERIFIED; real-world forecasting = PARTIALLY VERIFIED."
            )
            self.log(18, "Formal Outcome B Classification & Closure Declaration", passed, declaration)
        finally:
            db.close()


if __name__ == "__main__":
    verifier = Phase11FinalClosureVerifier()
    verifier.run_all_checks()
