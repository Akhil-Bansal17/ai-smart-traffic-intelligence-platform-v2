"""
Aggregates all v1 routers into one. As real endpoints are added in
later phases (videos, analysis, analytics, simulation), each gets its
own module here and is included below - main.py only ever imports
this one router, not individual endpoint modules.
"""
from fastapi import APIRouter

from app.api.v1 import (
    analysis,
    analytics,
    counting,
    dashboard,
    detection,
    emergency_corridor,
    health,
    lane_analysis,
    predictions,
    signal_optimization,
    tracking,
    videos,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(detection.router, prefix="/detection", tags=["detection"])
api_router.include_router(tracking.router, prefix="/tracking", tags=["tracking"])
api_router.include_router(counting.router, prefix="/counting", tags=["counting"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(lane_analysis.router, prefix="/lane-analysis", tags=["lane-analysis"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(signal_optimization.router, prefix="/signal-optimization", tags=["signal-optimization"])
api_router.include_router(emergency_corridor.router, prefix="/emergency-corridor", tags=["emergency-corridor"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])


