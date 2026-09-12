"""Response schemas for the health and readiness diagnostic endpoints."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="Liveness status indicator: 'ok'")
    environment: str = Field(description="Application running environment")
    version: str = Field(default="0.1.0", description="API version")


class DependencyStatus(BaseModel):
    name: str
    status: str  # "healthy", "degraded", "unhealthy", "not_found"
    critical: bool = True
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class ReadinessResponse(BaseModel):
    status: str  # "ready", "degraded", "not_ready"
    environment: str
    version: str = "0.1.0"
    dependencies: Dict[str, DependencyStatus]
    is_ready: bool
