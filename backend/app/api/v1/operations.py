"""
Unified Traffic Operations Center REST API.
Phase 23: Unified Traffic Operations Center & Real-Time Incident Response.

Mounted at: /api/v1/operations
Provides coordinated polling overview, camera health, active incidents,
incident operator lifecycle management, authoritative timeline, and historical context.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.operations import (
    OperationsCameraOverviewItem,
    OperationsHistoricalContextResponse,
    OperationsIncidentItem,
    OperationsIncidentListResponse,
    OperationsOverviewResponse,
    OperationsTimelineResponse,
    UpdateIncidentStatusRequest,
)
from app.services.cv.job_manager import AnalysisJobManager, get_analysis_job_manager
from app.services.operations.service import OperationsCenterService

router = APIRouter()


@router.get(
    "/overview",
    response_model=OperationsOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Unified Operations Center Overview",
    description="Assembles real-time camera health, active incidents, traffic snapshot, decision insights, timeline, and provenance in one coordinated call.",
)
def get_operations_overview(
    db: Session = Depends(get_db),
    manager: AnalysisJobManager = Depends(get_analysis_job_manager),
) -> OperationsOverviewResponse:
    """Returns composite operational overview for the unified operations console."""
    return OperationsCenterService.get_overview(db=db, manager=manager)


@router.get(
    "/cameras",
    response_model=List[OperationsCameraOverviewItem],
    status_code=status.HTTP_200_OK,
    summary="Get Live Cameras Operational Overview",
    description="Returns all registered cameras with live telemetry, health state, and processing statistics.",
)
def get_operations_cameras(
    db: Session = Depends(get_db),
    manager: AnalysisJobManager = Depends(get_analysis_job_manager),
) -> List[OperationsCameraOverviewItem]:
    """Returns live telemetry overview across all camera sources."""
    overview = OperationsCenterService.get_overview(db=db, manager=manager)
    return overview.cameras


@router.get(
    "/incidents",
    response_model=OperationsIncidentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Operational Incidents",
    description="Returns paginated, filterable traffic incidents with camera and session provenance.",
)
def list_operations_incidents(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: 'open', 'acknowledged', 'resolved'"),
    severity: Optional[str] = Query(None, description="Filter by severity: 'low', 'medium', 'high', 'critical'"),
    camera_source_id: Optional[str] = Query(None, description="Filter by camera source ID"),
    anomaly_type: Optional[str] = Query(None, description="Filter by anomaly type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> OperationsIncidentListResponse:
    """Queries operational traffic incidents with indexed multi-parameter filtering."""
    return OperationsCenterService.get_incidents(
        db=db,
        status_filter=status_filter,
        severity_filter=severity,
        camera_source_id=camera_source_id,
        anomaly_type=anomaly_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/incidents/{incident_id}",
    response_model=OperationsIncidentItem,
    status_code=status.HTTP_200_OK,
    summary="Get Incident Detail",
    description="Returns detailed incident record with parent session, camera/video metadata, and operator notes.",
)
def get_operations_incident_detail(
    incident_id: str,
    db: Session = Depends(get_db),
) -> OperationsIncidentItem:
    """Retrieves full incident detail by ID."""
    return OperationsCenterService.get_incident_detail(db=db, incident_id=incident_id)


@router.patch(
    "/incidents/{incident_id}/status",
    response_model=OperationsIncidentItem,
    status_code=status.HTTP_200_OK,
    summary="Update Incident Operator Status",
    description="Acknowledge or resolve an incident with optional operator note, reusing Phase 15 state mutation.",
)
def update_operations_incident_status(
    incident_id: str,
    payload: UpdateIncidentStatusRequest,
    db: Session = Depends(get_db),
) -> OperationsIncidentItem:
    """Updates incident status to 'acknowledged' or 'resolved' with operator audit note."""
    return OperationsCenterService.update_incident_status(
        db=db,
        incident_id=incident_id,
        target_status=payload.status,
        note=payload.note,
    )


@router.get(
    "/timeline",
    response_model=OperationsTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Recent Operations Event Timeline",
    description="Returns chronological events aggregated strictly from authoritative database records.",
)
def get_operations_timeline(
    limit: int = Query(50, ge=5, le=100, description="Maximum events to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db),
) -> OperationsTimelineResponse:
    """Returns chronological event timeline derived from authoritative DB records."""
    return OperationsCenterService.get_timeline(db=db, limit=limit, event_type=event_type)


@router.get(
    "/context/{source_id}",
    response_model=OperationsHistoricalContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Historical Context for Source",
    description="Pulls retrospective historical intelligence from Phase 22 for a specific camera or source.",
)
def get_operations_historical_context(
    source_id: str,
    time_window: str = Query("7d", description="Time window preset: 24h, 7d, 30d, 90d"),
    db: Session = Depends(get_db),
) -> OperationsHistoricalContextResponse:
    """Returns retrospective historical analytics context for a specific camera or video source."""
    return OperationsCenterService.get_historical_context(
        db=db,
        source_id=source_id,
        time_window=time_window,
    )
