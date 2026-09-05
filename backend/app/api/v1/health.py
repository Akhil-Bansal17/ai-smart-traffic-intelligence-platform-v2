"""
Versioned health endpoint: GET /api/v1/health

Distinct from the bare GET /health at the app root (see app/main.py),
which exists for infra-level liveness checks (load balancers, Docker
healthchecks) that shouldn't need to know about API versioning.
This one is part of the actual API surface documented in ARCHITECTURE.md.
"""
from fastapi import APIRouter

from app.config.settings import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.environment)
