"""
Unit tests for application configuration validation and production readiness hardening.
Covers:
- Default settings loading
- Environment name validation (development, staging, production, test)
- Log level validation
- FPS, file size, and probability bounds
- Production secret key security enforcement
"""
import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def test_settings_load_with_defaults():
    s = Settings()
    assert s.environment in ("development", "staging", "production", "test")
    assert s.database_url.startswith(("postgresql://", "sqlite:///"))
    assert isinstance(s.cors_origins, list)
    assert len(s.cors_origins) >= 1
    assert s.yolo_model_path
    assert 0.0 < s.default_confidence_threshold <= 1.0
    assert 1 <= s.processing_fps <= 60


def test_invalid_environment_rejected():
    with pytest.raises(ValidationError) as exc_info:
        Settings(environment="invalid_env_name")
    assert "Invalid environment" in str(exc_info.value)


def test_invalid_log_level_rejected():
    with pytest.raises(ValidationError) as exc_info:
        Settings(log_level="SUPER_VERBOSE")
    assert "Invalid log_level" in str(exc_info.value)


def test_invalid_fps_bounds_rejected():
    with pytest.raises(ValidationError) as exc_info:
        Settings(processing_fps=0)
    assert "processing_fps" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        Settings(processing_fps=120)
    assert "processing_fps" in str(exc_info.value)


def test_invalid_upload_size_rejected():
    with pytest.raises(ValidationError) as exc_info:
        Settings(max_upload_size_mb=-5)
    assert "max_upload_size_mb" in str(exc_info.value)


def test_invalid_confidence_threshold_rejected():
    with pytest.raises(ValidationError) as exc_info:
        Settings(default_confidence_threshold=1.5)
    assert "Threshold must be strictly within" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        Settings(default_confidence_threshold=-0.1)
    assert "Threshold must be strictly within" in str(exc_info.value)


def test_production_secret_key_security_enforcement():
    # 1. Reject placeholder secret in production
    with pytest.raises(ValidationError) as exc_info:
        Settings(environment="production", secret_key="changeme-in-env")
    assert "Production environment requires a secure" in str(exc_info.value)

    # 2. Reject short secret in production (< 16 chars)
    with pytest.raises(ValidationError) as exc_info:
        Settings(environment="production", secret_key="short_secret")
    assert "at least 16 characters" in str(exc_info.value)

    # 3. Accept strong secret in production
    strong_secret = "a-very-long-and-random-production-secret-key-2026"
    prod_settings = Settings(environment="production", secret_key=strong_secret)
    assert prod_settings.environment == "production"
    assert prod_settings.secret_key == strong_secret

    # 4. Accept dev secret in development
    dev_settings = Settings(environment="development", secret_key="dev-secret-key-traffic-platform-2026")
    assert dev_settings.environment == "development"
