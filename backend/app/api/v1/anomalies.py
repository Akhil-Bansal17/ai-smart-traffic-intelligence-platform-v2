"""
REST API endpoints for Traffic Anomaly & Congestion Incident Detection.
Phase 15: Traffic Anomaly & Congestion Incident Detection.

Provides query, inspection, manual on-demand detection, and status update endpoints
for persisted operational traffic anomalies.
"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.analysis import AnalysisSession
from app.models.anomaly import AnomalyEvent
from app.schemas.anomaly import (
    AnomalyEventDetailResponse,
    AnomalyEventListResponse,
    AnomalyEventSchema,
    AnomalyInfoResponse,
    DetectAnomaliesResponse,
    UpdateAnomalyStatusRequest,
)
from app.services.anomaly.detector import AnomalyDetectionService, utcnow

logger = get_logger(__name__)

router = APIRouter()
anomaly_service = AnomalyDetectionService()


@router.get(
    "/info",
    response_model=AnomalyInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Anomaly Detection Configuration & Metadata",
    description="Returns metadata describing rule thresholds, severity scaling criteria, terminology, and anti-fabrication policies.",
)
def get_anomaly_info() -> AnomalyInfoResponse:
    """Returns rule configurations, threshold parameters, and architectural policies."""
    rules = anomaly_service.get_rule_catalog()
    return AnomalyInfoResponse(rules=rules)


@router.get(
    "/events",
    response_model=AnomalyEventListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Anomaly Events",
    description="Returns paginated, filterable list of persisted traffic anomaly and congestion incident events.",
)
def list_anomaly_events(
    session_id: Optional[str] = Query(None, description="Filter by AnalysisSession ID"),
    anomaly_type: Optional[str] = Query(None, description="Filter by anomaly type"),
    severity: Optional[str] = Query(None, description="Filter by severity: 'low', 'medium', 'high', 'critical'"),
    event_status: Optional[str] = Query(None, alias="status", description="Filter by status: 'open', 'acknowledged', 'resolved'"),
    provenance_category: Optional[str] = Query(None, description="Filter by provenance category"),
    is_synthetic: Optional[bool] = Query(None, description="Filter by synthetic flag"),
    limit: int = Query(50, ge=1, le=200, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> AnomalyEventListResponse:
    """Queries persisted anomaly events with indexed multi-parameter filtering."""
    query = select(AnomalyEvent)

    if session_id:
        query = query.where(AnomalyEvent.session_id == session_id)
    if anomaly_type:
        query = query.where(AnomalyEvent.anomaly_type == anomaly_type)
    if severity:
        query = query.where(AnomalyEvent.severity == severity)
    if event_status:
        query = query.where(AnomalyEvent.status == event_status)
    if provenance_category:
        query = query.where(AnomalyEvent.provenance_category == provenance_category)
    if is_synthetic is not None:
        query = query.where(AnomalyEvent.is_synthetic == is_synthetic)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    # Count active (open / acknowledged) events in total matching filter
    active_query = query.where(AnomalyEvent.status.in_(["open", "acknowledged"]))
    active_count = db.scalar(select(func.count()).select_from(active_query.subquery())) or 0

    # Order by newest detection first
    events_raw = list(
        db.scalars(
            query.order_by(AnomalyEvent.created_at.desc()).offset(offset).limit(limit)
        ).all()
    )

    # Compute provenance breakdown
    prov_counts: dict[str, int] = {}
    for ev in events_raw:
        prov_counts[ev.provenance_category] = prov_counts.get(ev.provenance_category, 0) + 1

    event_schemas = [AnomalyEventSchema.model_validate(ev) for ev in events_raw]

    return AnomalyEventListResponse(
        events=event_schemas,
        total=total,
        limit=limit,
        offset=offset,
        active_count=active_count,
        provenance_breakdown=prov_counts,
    )


@router.get(
    "/events/{event_id}",
    response_model=AnomalyEventDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Anomaly Event Details",
    description="Returns detailed event information including parent session and video provenance lineage.",
)
def get_anomaly_event_detail(
    event_id: str,
    db: Session = Depends(get_db),
) -> AnomalyEventDetailResponse:
    """Retrieves single anomaly event with full parent video and session lineage."""
    stmt = (
        select(AnomalyEvent)
        .options(
            joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.video)
        )
        .where(AnomalyEvent.id == event_id)
    )
    event = db.scalar(stmt)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly event with ID '{event_id}' not found.",
        )

    session = event.analysis_session
    video = session.video if session else None

    return AnomalyEventDetailResponse(
        event=AnomalyEventSchema.model_validate(event),
        video_id=video.id if video else None,
        video_filename=video.original_filename if video else None,
        video_source_type=video.source_type if video else None,
        provenance_verified=video.provenance_verified if video else False,
        source_reference=video.source_reference if video else None,
        license_reference=video.license_reference if video else None,
    )


@router.post(
    "/detect/{session_id}",
    response_model=DetectAnomaliesResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger On-Demand Anomaly Detection for Session",
    description="Explicitly executes idempotent statistical anomaly detection over an already-persisted AnalysisSession.",
)
def trigger_anomaly_detection(
    session_id: str,
    db: Session = Depends(get_db),
) -> DetectAnomaliesResponse:
    """Runs idempotent anomaly detection on-demand for a given session."""
    t0 = time.perf_counter()

    session = db.scalar(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AnalysisSession with ID '{session_id}' not found.",
        )

    existing_count = db.scalar(
        select(func.count(AnomalyEvent.id)).where(AnomalyEvent.session_id == session_id)
    ) or 0

    events = anomaly_service.detect_and_persist_for_session(db=db, session_id=session_id)

    total_detected = len(events)
    new_count = max(total_detected - existing_count, 0)
    updated_count = total_detected - new_count
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    return DetectAnomaliesResponse(
        session_id=session_id,
        anomalies_detected=total_detected,
        new_events_count=new_count,
        updated_events_count=updated_count,
        events=[AnomalyEventSchema.model_validate(e) for e in events],
        execution_time_ms=elapsed_ms,
    )


@router.patch(
    "/events/{event_id}/status",
    response_model=AnomalyEventSchema,
    status_code=status.HTTP_200_OK,
    summary="Update Anomaly Event Status",
    description="Acknowledge or resolve an open traffic anomaly event.",
)
def update_anomaly_status(
    event_id: str,
    req: UpdateAnomalyStatusRequest,
    db: Session = Depends(get_db),
) -> AnomalyEventSchema:
    """Updates event status to 'acknowledged' or 'resolved'."""
    allowed_statuses = ["open", "acknowledged", "resolved"]
    if req.status.lower() not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{req.status}'. Must be one of: {allowed_statuses}",
        )

    event = db.scalar(select(AnomalyEvent).where(AnomalyEvent.id == event_id))
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly event with ID '{event_id}' not found.",
        )

    event.status = req.status.lower()
    now = utcnow()
    event.updated_at = now
    if event.status == "resolved":
        event.resolved_at = now

    if req.note:
        details = dict(event.details_json or {})
        details["operator_note"] = req.note
        event.details_json = details

    db.commit()
    db.refresh(event)
    return AnomalyEventSchema.model_validate(event)


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Anomaly Event",
    description="Removes a single anomaly event from the database.",
)
def delete_anomaly_event(
    event_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Deletes an anomaly event by ID."""
    event = db.scalar(select(AnomalyEvent).where(AnomalyEvent.id == event_id))
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly event with ID '{event_id}' not found.",
        )

    db.delete(event)
    db.commit()
    return {"status": "deleted", "id": event_id}
