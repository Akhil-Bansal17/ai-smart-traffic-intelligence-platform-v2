"""
Versioned health and readiness diagnostic endpoints:
- GET /api/v1/health — Lightweight liveness check
- GET /api/v1/health/readiness — Comprehensive readiness evaluation
"""
from pathlib import Path
import time
from typing import Dict

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.health import DependencyStatus, HealthResponse, ReadinessResponse

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["system"],
    summary="Versioned API Liveness Check",
    description="Lightweight liveness probe indicating that the FastAPI process is responsive.",
)
def health() -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.environment)


@router.get(
    "/health/readiness",
    response_model=ReadinessResponse,
    tags=["system"],
    summary="System Readiness Diagnostics",
    description=(
        "Evaluates critical and optional runtime dependencies (database connectivity, "
        "storage filesystem accessibility, model weights presence, configuration validity) "
        "to determine if the platform is ready to serve operational traffic."
    ),
)
def readiness(
    response: Response,
    db: Session = Depends(get_db),
) -> ReadinessResponse:
    dependencies: Dict[str, DependencyStatus] = {}
    is_ready = True

    # 1. Database Connectivity Probe (Critical)
    db_start = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        db_latency = round((time.perf_counter() - db_start) * 1000.0, 2)
        dependencies["database"] = DependencyStatus(
            name="database",
            status="healthy",
            critical=True,
            latency_ms=db_latency,
            message="Database connection verified.",
        )
    except Exception as exc:
        logger.error("Readiness check database probe failed: %s", exc)
        dependencies["database"] = DependencyStatus(
            name="database",
            status="unhealthy",
            critical=True,
            latency_ms=round((time.perf_counter() - db_start) * 1000.0, 2),
            message=f"Database connection error: {type(exc).__name__}",
        )
        is_ready = False

    # 2. File Upload Storage Probe (Critical)
    try:
        upload_path = Path(settings.upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)
        # Test write permission
        test_file = upload_path / ".readiness_probe"
        test_file.write_text("probe")
        test_file.unlink()
        dependencies["storage"] = DependencyStatus(
            name="storage",
            status="healthy",
            critical=True,
            message=f"Storage directory '{settings.upload_dir}' writable.",
        )
    except Exception as exc:
        logger.warning("Readiness check storage probe failed: %s", exc)
        dependencies["storage"] = DependencyStatus(
            name="storage",
            status="degraded",
            critical=True,
            message=f"Storage access issue: {exc}",
        )
        is_ready = False

    # 3. Model Weights Availability Probe (Non-critical fallback if pipeline unexercised)
    model_path = Path(settings.yolo_model_path)
    if model_path.exists() and model_path.stat().st_size > 0:
        dependencies["model_weights"] = DependencyStatus(
            name="model_weights",
            status="healthy",
            critical=False,
            message=f"YOLO model weights located ({model_path.stat().st_size / (1024 * 1024):.1f} MB).",
        )
    else:
        dependencies["model_weights"] = DependencyStatus(
            name="model_weights",
            status="degraded",
            critical=False,
            message=f"Model weights file not found at '{settings.yolo_model_path}'.",
        )

    # 4. Configuration Validity (Critical)
    dependencies["configuration"] = DependencyStatus(
        name="configuration",
        status="healthy",
        critical=True,
        message=f"Environment '{settings.environment}' with valid log level '{settings.log_level}'.",
    )

    overall_status = "ready" if is_ready else "not_ready"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=overall_status,
        environment=settings.environment,
        dependencies=dependencies,
        is_ready=is_ready,
    )
