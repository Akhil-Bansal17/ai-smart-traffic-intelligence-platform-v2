"""
Dataset Extraction and Readiness Assessment Service for Traffic Prediction.
Phase 11: Traffic Prediction / Forecasting.
Phase 11.1: Real-Data Validation & Hardening.

Extracts time-ordered tabular observations from persisted traffic database records.
Enforces strict transparency: Real vs. Synthetic distinction and minimum dataset size threshold.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.analysis import AnalysisSession, TrafficMetricsRecord

logger = get_logger(__name__)

# Minimum threshold of observations required for meaningful supervised learning
MIN_TRAINING_SAMPLES = 20


@dataclass
class DatasetReadiness:
    """Readiness status of the traffic dataset for ML training."""
    is_ready: bool
    sample_count: int
    threshold: int
    data_source: str
    message: str
    session_count: int = 0
    status_code: str = "insufficient_observations"
    earliest_timestamp: Optional[str] = None
    latest_timestamp: Optional[str] = None


@dataclass
class TrafficDataPoint:
    """A single chronological observation extracted from database or synthetic fixtures."""
    timestamp: datetime
    vehicle_volume: float
    flow_rate_per_minute: float
    inbound_count: int
    outbound_count: int
    observation_duration_seconds: float
    session_id: str
    is_synthetic: bool = False


class DatasetExtractor:
    """
    Queries persisted traffic metrics from the database, extracts discrete time-series
    observations, and checks dataset adequacy against strict statistical thresholds.
    """

    def __init__(self, min_samples: int = MIN_TRAINING_SAMPLES):
        self.min_samples = min_samples

    def check_readiness(self, db: Session) -> DatasetReadiness:
        """
        Inspects real persisted database records to determine if sufficient observations exist.
        """
        data_points = self.extract_from_db(db)
        count = len(data_points)
        is_ready = count >= self.min_samples

        distinct_sessions = len(set(dp.session_id for dp in data_points))

        earliest = data_points[0].timestamp.isoformat() if data_points else None
        latest = data_points[-1].timestamp.isoformat() if data_points else None

        if count == 0:
            message = (
                f"Dataset contains 0 real observations (minimum required: {self.min_samples}). "
                "Prediction unavailable: no historical observations."
            )
            source = "real_observations_insufficient"
            status_code = "no_observations"
        elif not is_ready:
            message = (
                f"Dataset contains only {count} real observations across {distinct_sessions} session(s) "
                f"(minimum required: {self.min_samples}). Prediction unavailable: insufficient historical observations."
            )
            source = "real_observations_insufficient"
            status_code = "insufficient_observations"
        else:
            message = (
                f"Dataset contains {count} real observations across {distinct_sessions} session(s) "
                f"(threshold: {self.min_samples}). Sufficient for chronological model training."
            )
            source = "real_observations"
            status_code = "ready"

        return DatasetReadiness(
            is_ready=is_ready,
            sample_count=count,
            threshold=self.min_samples,
            data_source=source,
            message=message,
            session_count=distinct_sessions,
            status_code=status_code,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

    def extract_from_db(self, db: Session) -> List[TrafficDataPoint]:
        """
        Extracts all chronological time-series points from persisted traffic metrics.
        Preserves strict temporal ordering without future leakage.
        """
        # Query completed sessions ordered by started_at
        sessions = db.scalars(
            select(AnalysisSession)
            .where(AnalysisSession.status == "completed")
            .order_by(AnalysisSession.started_at.asc())
        ).all()

        data_points: List[TrafficDataPoint] = []

        for s in sessions:
            if not s.traffic_metrics:
                continue

            metrics = s.traffic_metrics
            buckets = metrics.time_series_buckets or []

            if buckets:
                # Extract fine-grained bucket observations
                for b in buckets:
                    # b is dict with bucket_index, start_time_seconds, vehicle_count, inbound_count, outbound_count
                    start_s = float(b.get("start_time_seconds", 0.0))
                    end_s = float(b.get("end_time_seconds", start_s + 5.0))
                    duration = max(0.5, end_s - start_s)
                    count = float(b.get("vehicle_count", 0))
                    flow_rate = count / (duration / 60.0)
                    inbound = int(b.get("inbound_count", 0))
                    outbound = int(b.get("outbound_count", 0))

                    # Timestamp relative to session started_at
                    ts = s.started_at + timedelta(seconds=start_s)

                    data_points.append(
                        TrafficDataPoint(
                            timestamp=ts,
                            vehicle_volume=count,
                            flow_rate_per_minute=flow_rate,
                            inbound_count=inbound,
                            outbound_count=outbound,
                            observation_duration_seconds=duration,
                            session_id=s.id,
                            is_synthetic=False,
                        )
                    )
            else:
                # Fallback to session aggregate point
                data_points.append(
                    TrafficDataPoint(
                        timestamp=s.started_at,
                        vehicle_volume=float(metrics.total_volume),
                        flow_rate_per_minute=float(metrics.flow_rate_per_minute),
                        inbound_count=sum(
                            d.get("count", 0)
                            for d in (metrics.direction_distribution or [])
                            if d.get("direction") == "inbound"
                        ),
                        outbound_count=sum(
                            d.get("count", 0)
                            for d in (metrics.direction_distribution or [])
                            if d.get("direction") == "outbound"
                        ),
                        observation_duration_seconds=float(metrics.observation_duration_seconds),
                        session_id=s.id,
                        is_synthetic=False,
                    )
                )

        # Sort strictly chronologically by timestamp
        data_points.sort(key=lambda x: x.timestamp)
        return data_points

    @staticmethod
    def generate_synthetic_fixtures(
        num_samples: int = 120,
        start_time: Optional[datetime] = None,
        interval_minutes: int = 5,
        random_seed: int = 42,
    ) -> List[TrafficDataPoint]:
        """
        Generates clearly-labeled synthetic fixture data for testing and local development.
        Follows realistic diurnal traffic patterns (morning & evening peaks + Poisson noise).
        Strictly labeled with is_synthetic=True.
        """
        rng = np.random.RandomState(random_seed)
        if start_time is None:
            # Start 2 days ago at 06:00 UTC
            now = datetime.now(timezone.utc)
            start_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(
                minutes=num_samples * interval_minutes
            )

        fixtures: List[TrafficDataPoint] = []

        for i in range(num_samples):
            ts = start_time + timedelta(minutes=i * interval_minutes)
            hour = ts.hour + ts.minute / 60.0

            # Diurnal baseline: morning peak (8:00) and evening peak (17:30)
            morning_peak = 18.0 * math.exp(-0.5 * ((hour - 8.0) / 1.5) ** 2)
            evening_peak = 22.0 * math.exp(-0.5 * ((hour - 17.5) / 2.0) ** 2)
            base_volume = 5.0 + morning_peak + evening_peak

            # Add random fluctuations
            noise = rng.normal(0, 2.0)
            volume = max(1.0, round(base_volume + noise, 1))

            inbound_ratio = 0.65 if (7.0 <= hour <= 10.0) else (0.35 if (16.0 <= hour <= 19.0) else 0.50)
            inbound_count = int(round(volume * inbound_ratio))
            outbound_count = int(max(0, volume - inbound_count))
            flow_rate = round(volume / (interval_minutes), 2)

            fixtures.append(
                TrafficDataPoint(
                    timestamp=ts,
                    vehicle_volume=volume,
                    flow_rate_per_minute=flow_rate,
                    inbound_count=inbound_count,
                    outbound_count=outbound_count,
                    observation_duration_seconds=float(interval_minutes * 60),
                    session_id=f"synthetic_fixture_sample_{i:04d}",
                    is_synthetic=True,
                )
            )

        fixtures.sort(key=lambda x: x.timestamp)
        return fixtures
