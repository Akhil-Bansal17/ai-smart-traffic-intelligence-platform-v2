"""
Feature Engineering Service for Traffic Time-Series Forecasting.
Phase 11: Traffic Prediction / Forecasting.

Constructs non-leaking chronological tabular features from time-ordered observations.
Guarantees zero future data leakage, explicit NaN dropping, and mathematical consistency.
"""
from dataclasses import dataclass
from datetime import datetime
import math
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from app.services.ml.dataset_extractor import TrafficDataPoint


@dataclass
class FeatureMatrixResult:
    """Result of feature engineering containing X, y, metadata, and timestamps."""
    X: np.ndarray
    y: np.ndarray
    feature_names: List[str]
    timestamps: List[datetime]
    dropped_initial_rows: int
    target_horizon_steps: int
    target_variable: str = "vehicle_volume"


class TrafficFeatureEngineer:
    """
    Transforms raw sequential traffic data points into clean feature matrices.
    Strictly forbids looking ahead: every feature row at index t only sees data <= t.
    """

    def __init__(self, lag_steps: int = 3, rolling_window: int = 3):
        self.lag_steps = max(1, int(lag_steps))
        self.rolling_window = max(2, int(rolling_window))

    def build_features(
        self,
        data_points: List[TrafficDataPoint],
        horizon_steps: int = 1,
    ) -> FeatureMatrixResult:
        """
        Builds feature matrix X and target array y for a specified prediction horizon.
        
        y[t] = volume[t + horizon_steps]
        X[t] = [lag_1, lag_2, lag_3, rolling_mean, rolling_std, flow_rate, inbound_ratio, hour_sin, hour_cos, is_peak]
        """
        if len(data_points) < (self.lag_steps + self.rolling_window + horizon_steps):
            raise ValueError(
                f"Insufficient data points ({len(data_points)}) to construct "
                f"lags={self.lag_steps}, rolling={self.rolling_window}, horizon={horizon_steps}."
            )

        # Convert to DataFrame
        records = []
        for dp in data_points:
            records.append({
                "timestamp": dp.timestamp,
                "volume": float(dp.vehicle_volume),
                "flow_rate": float(dp.flow_rate_per_minute),
                "inbound": float(dp.inbound_count),
                "outbound": float(dp.outbound_count),
            })
        df = pd.DataFrame(records)

        # 1. Target column: future volume shifted backwards by horizon_steps
        df["target"] = df["volume"].shift(-horizon_steps)

        # 2. Lag features (strictly past values)
        feature_names: List[str] = []
        for lag in range(1, self.lag_steps + 1):
            col_name = f"lag_{lag}_volume"
            df[col_name] = df["volume"].shift(lag - 1)  # lag 1 is current volume at time t
            feature_names.append(col_name)

        # 3. Rolling window statistics
        rolling_mean_col = f"rolling_mean_{self.rolling_window}_volume"
        rolling_std_col = f"rolling_std_{self.rolling_window}_volume"
        df[rolling_mean_col] = df["volume"].rolling(window=self.rolling_window, min_periods=self.rolling_window).mean()
        df[rolling_std_col] = df["volume"].rolling(window=self.rolling_window, min_periods=self.rolling_window).std().fillna(0.0)
        feature_names.extend([rolling_mean_col, rolling_std_col])

        # 4. Instantaneous flow rate & directional ratio
        df["flow_rate_per_minute"] = df["flow_rate"]
        df["inbound_ratio"] = df["inbound"] / (df["inbound"] + df["outbound"] + 1e-6)
        feature_names.extend(["flow_rate_per_minute", "inbound_ratio"])

        # 5. Temporal periodic & peak indicators
        hours = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60.0
        df["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
        df["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)
        df["day_of_week"] = df["timestamp"].dt.dayofweek.astype(float)
        df["is_peak_hour"] = ((hours >= 7.0) & (hours <= 9.5) | (hours >= 16.5) & (hours <= 19.0)).astype(float)
        feature_names.extend(["hour_sin", "hour_cos", "day_of_week", "is_peak_hour"])

        # Drop initial rows with NaNs from lags/rolling and trailing rows with NaNs from future target
        valid_df = df.dropna(subset=feature_names + ["target"]).copy()
        dropped_initial_rows = len(df) - len(valid_df)

        X = valid_df[feature_names].to_numpy(dtype=np.float64)
        y = valid_df["target"].to_numpy(dtype=np.float64)
        timestamps = valid_df["timestamp"].tolist()

        return FeatureMatrixResult(
            X=X,
            y=y,
            feature_names=feature_names,
            timestamps=timestamps,
            dropped_initial_rows=dropped_initial_rows,
            target_horizon_steps=horizon_steps,
            target_variable="vehicle_volume",
        )

    def extract_inference_vector(
        self,
        recent_points: List[TrafficDataPoint],
        target_timestamp: Optional[datetime] = None,
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Builds a single feature vector (1, n_features) from recent historical points to generate a forecast.
        """
        if len(recent_points) < max(self.lag_steps, self.rolling_window):
            raise ValueError(
                f"Need at least {max(self.lag_steps, self.rolling_window)} recent points for inference, got {len(recent_points)}."
            )

        # Sort chronologically
        sorted_points = sorted(recent_points, key=lambda x: x.timestamp)
        volumes = [float(p.vehicle_volume) for p in sorted_points]
        latest_point = sorted_points[-1]
        ts = target_timestamp or (latest_point.timestamp)

        # Lag features
        feature_dict = {}
        for lag in range(1, self.lag_steps + 1):
            idx = -lag
            feature_dict[f"lag_{lag}_volume"] = volumes[idx] if abs(idx) <= len(volumes) else volumes[0]

        # Rolling stats on last rolling_window points
        window_vols = volumes[-self.rolling_window:]
        feature_dict[f"rolling_mean_{self.rolling_window}_volume"] = float(np.mean(window_vols))
        feature_dict[f"rolling_std_{self.rolling_window}_volume"] = float(np.std(window_vols))

        # Flow rate & direction
        feature_dict["flow_rate_per_minute"] = float(latest_point.flow_rate_per_minute)
        tot_dir = float(latest_point.inbound_count + latest_point.outbound_count)
        feature_dict["inbound_ratio"] = float(latest_point.inbound_count / (tot_dir + 1e-6))

        # Temporal periodic
        hour = ts.hour + ts.minute / 60.0
        feature_dict["hour_sin"] = float(np.sin(2.0 * np.pi * hour / 24.0))
        feature_dict["hour_cos"] = float(np.cos(2.0 * np.pi * hour / 24.0))
        feature_dict["day_of_week"] = float(ts.weekday())
        feature_dict["is_peak_hour"] = 1.0 if ((7.0 <= hour <= 9.5) or (16.5 <= hour <= 19.0)) else 0.0

        feature_names = list(feature_dict.keys())
        vector = np.array([feature_dict[k] for k in feature_names], dtype=np.float64).reshape(1, -1)
        return vector, feature_names
