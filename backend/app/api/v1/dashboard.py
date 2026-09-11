"""
Dashboard REST API endpoints for Phase 14.
Provides unified aggregation and presentation endpoints for the frontend command dashboard.
Strictly read-only: never triggers CV pipelines, model training, or simulations.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardInfoResponse, DashboardSummaryResponse
from app.services.dashboard.aggregator import DashboardAggregatorService

router = APIRouter()

aggregator_service = DashboardAggregatorService()


@router.get(
    "/info",
    response_model=DashboardInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard Metadata and Status",
    description="Returns phase metadata, provenance categories, and read-only anti-trigger architectural guarantee.",
)
def get_dashboard_info() -> DashboardInfoResponse:
    """Returns dashboard metadata and anti-trigger guarantees."""
    return DashboardInfoResponse()


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Unified Dashboard Aggregation Summary",
    description=(
        "Batched, single-roundtrip aggregation endpoint summarizing outputs from Phases 4–13. "
        "Includes system health, traffic overview, vehicle composition, time-series flow, "
        "lane density, prediction readiness, signal optimization results, emergency corridor results, "
        "recent history, and data provenance panel. Strictly read-only."
    ),
)
def get_dashboard_summary(
    session_id: Optional[str] = Query(
        None,
        description="Optional AnalysisSession ID to inspect a specific historical session on the dashboard",
    ),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    """Returns composite dashboard summary data with explicit provenance per section."""
    return aggregator_service.get_summary(db=db, session_id=session_id)
