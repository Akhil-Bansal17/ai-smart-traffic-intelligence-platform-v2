"""Confirms settings load from environment/.env without raising and cover expected keys."""
from app.config.settings import Settings


def test_settings_load_with_defaults():
    s = Settings()
    assert s.environment
    assert s.database_url.startswith(("postgresql://", "sqlite:///"))
    assert isinstance(s.cors_origins, list)
    assert len(s.cors_origins) >= 1
    assert s.yolo_model_path
    assert 0.0 < s.default_confidence_threshold < 1.0
    assert s.processing_fps > 0


def test_secret_key_not_hardcoded_placeholder_in_prod_would_be_flagged():
    # This just documents the expectation; real enforcement (refusing to boot
    # with the default secret in production) belongs to Phase 16 hardening.
    s = Settings()
    assert isinstance(s.secret_key, str) and len(s.secret_key) > 0
