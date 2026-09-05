"""
Centralized application settings.

Everything configurable lives here and is loaded from environment
variables (via a local .env file in development, real env vars in
production). No secret or environment-specific value should ever be
hard-coded elsewhere in the codebase — import `settings` instead.

See ../../.env.example for the full list of variables this expects.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def cors_origins(self) -> list[str]:
        """allowed_origins as a parsed list for the CORS middleware."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — env is read once per process, not per request."""
    return Settings()


settings = get_settings()
