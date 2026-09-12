"""
Centralized application settings.

Everything configurable lives here and is loaded from environment
variables (via a local .env file in development, real env vars in
production). No secret or environment-specific value should ever be
hard-coded elsewhere in the codebase — import `settings` instead.

See ../../.env.example for the full list of variables this expects.
"""
from functools import lru_cache
from typing import List, Literal, Set

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VALID_ENVIRONMENTS: Set[str] = {"development", "staging", "production", "test"}
VALID_LOG_LEVELS: Set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
INSECURE_DEFAULT_SECRETS: Set[str] = {
    "changeme-in-env",
    "dev-secret-key-traffic-platform-2026",
    "replace-with-a-long-random-value",
    "changeme",
    "secret",
    "admin",
    "default",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    environment: str = "development"
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = "postgresql://traffic_user:changeme@localhost:5432/traffic_platform"

    # --- Auth ---
    secret_key: str = "changeme-in-env"
    access_token_expire_minutes: int = 60

    # --- CORS ---
    allowed_origins: str = "http://localhost:5173"

    # --- File uploads (used starting Phase 4) ---
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 500
    allowed_video_extensions: str = ".mp4,.avi,.mov"

    # --- CV / ML (used starting Phase 5+) ---
    yolo_model_path: str = "./data_science/models/yolov8n.pt"
    default_confidence_threshold: float = 0.4
    processing_fps: int = 5
    yolo_device: str = "cpu"
    yolo_imgsz: int = 640

    # --- Object Tracking (used starting Phase 6+) ---
    tracker_iou_threshold: float = 0.3
    tracker_max_lost_frames: int = 15
    tracker_min_hits: int = 1

    # --- Vehicle Counting (used starting Phase 7+) ---
    counting_line_p1_x: float = 0.0
    counting_line_p1_y: float = 0.5
    counting_line_p2_x: float = 1.0
    counting_line_p2_y: float = 0.5
    counting_min_movement_px: float = 2.0

    # --- Anomaly / Incident Detection (Phase 15) ---
    anomaly_congestion_occupancy_threshold: int = 5
    anomaly_congestion_min_duration_seconds: float = 20.0
    anomaly_congestion_density_score_threshold: float = 0.70
    anomaly_flow_drop_pct_threshold: float = 50.0
    anomaly_lane_imbalance_ratio_threshold: float = 3.0
    anomaly_lane_imbalance_min_volume: int = 5
    anomaly_density_spike_threshold: float = 0.00035
    anomaly_min_buckets_for_baseline: int = 2

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        val = v.strip().lower()
        if val not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment '{v}'. Must be one of: {sorted(list(VALID_ENVIRONMENTS))}"
            )
        return val

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        val = v.strip().upper()
        if val not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log_level '{v}'. Must be one of: {sorted(list(VALID_LOG_LEVELS))}"
            )
        return val

    @field_validator("processing_fps")
    @classmethod
    def validate_processing_fps(cls, v: int) -> int:
        if v < 1 or v > 60:
            raise ValueError(f"processing_fps must be between 1 and 60, got {v}")
        return v

    @field_validator("max_upload_size_mb")
    @classmethod
    def validate_max_upload_size_mb(cls, v: int) -> int:
        if v < 1 or v > 2000:
            raise ValueError(f"max_upload_size_mb must be between 1 and 2000 MB, got {v}")
        return v

    @field_validator("default_confidence_threshold", "tracker_iou_threshold")
    @classmethod
    def validate_probabilities(cls, v: float) -> float:
        if v <= 0.0 or v > 1.0:
            raise ValueError(f"Threshold must be strictly within (0.0, 1.0], got {v}")
        return v

    @field_validator("tracker_max_lost_frames", "tracker_min_hits")
    @classmethod
    def validate_positive_integers(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"Tracking frame count/hits must be >= 1, got {v}")
        return v

    @field_validator("anomaly_congestion_occupancy_threshold", "anomaly_lane_imbalance_min_volume", "anomaly_min_buckets_for_baseline")
    @classmethod
    def validate_anomaly_counts(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"Anomaly threshold count must be >= 1, got {v}")
        return v

    @field_validator("anomaly_congestion_min_duration_seconds")
    @classmethod
    def validate_anomaly_duration(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"Anomaly congestion duration must be >= 0.0s, got {v}")
        return v

    @field_validator("anomaly_flow_drop_pct_threshold")
    @classmethod
    def validate_flow_drop(cls, v: float) -> float:
        if v <= 0.0 or v > 100.0:
            raise ValueError(f"anomaly_flow_drop_pct_threshold must be between 0.0 and 100.0, got {v}")
        return v

    @field_validator("anomaly_density_spike_threshold")
    @classmethod
    def validate_density_spike(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError(f"anomaly_density_spike_threshold must be positive, got {v}")
        return v

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Rejects insecure default secret key when deployed in production."""
        if self.environment == "production":
            clean_secret = self.secret_key.strip()
            if clean_secret in INSECURE_DEFAULT_SECRETS or len(clean_secret) < 16:
                raise ValueError(
                    "Production environment requires a secure, non-default SECRET_KEY with at least 16 characters."
                )
        return self

    @property
    def cors_origins(self) -> list[str]:
        """allowed_origins as a parsed list for the CORS middleware."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — env is read once per process, not per request."""
    return Settings()


settings = get_settings()
