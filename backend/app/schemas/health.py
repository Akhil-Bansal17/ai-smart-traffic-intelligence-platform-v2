"""Response schema for the health endpoints."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str = "0.1.0"
