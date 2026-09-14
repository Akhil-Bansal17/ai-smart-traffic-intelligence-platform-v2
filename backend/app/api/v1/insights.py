"""
REST API Endpoints for Traffic Decision Intelligence & Explainable Insights.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.

Provides deterministic insight generation, multi-parameter querying, detail inspection,
status updates, and configuration metadata endpoints.
"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.insight import (
    InsightCategory,
    InsightSeverity,
    InsightStatus,
    TrafficInsight,
)
from app.schemas.insight import (
    InsightGenerateRequest,
    InsightGenerateResponse,
    InsightInfoResponse,
    TrafficInsightDetailResponse,
    TrafficInsightListResponse,
    TrafficInsightSchema,
    UpdateInsightStatusRequest,
)
from app.services.insights.engine import DecisionIntelligenceEngine, utcnow

logger = get_logger(__name__)

router = APIRouter()
insight_engine = DecisionIntelligenceEngine()


@router.get(
    "/info",
    response_model=InsightInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Decision Intelligence Configuration & Policies",
    description="Returns supported insight categories, severity scales, architectural boundaries, and anti-fabrication guidelines.",
)
def get_insight_info() -> InsightInfoResponse:
    """Returns catalog describing supported insight categories, severities, and boundaries."""
    return insight_engine.get_info_catalog()


@router.post(
    "/generate",
    response_model=InsightGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Deterministic Insights for Session",
    description="Consumes persisted database observations to deterministically generate explainable traffic insights.",
)
def generate_insights(
    request: InsightGenerateRequest,
    db: Session = Depends(get_db),
) -> InsightGenerateResponse:
    """Synchronously evaluates persisted records and returns generated insights."""
    start_t = time.perf_counter()
    insights = insight_engine.generate_for_session(
        db=db,
        session_id=request.session_id,
        job_id=request.job_id,
        force_recompute=request.force_recompute,
    )
    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)

    schemas = [TrafficInsightSchema.model_validate(ins) for ins in insights]
    return InsightGenerateResponse(
        session_id=request.session_id,
        insights_generated=len(schemas),
        insights=schemas,
        processing_time_ms=elapsed_ms,
    )


@router.get(
    "",
    response_model=TrafficInsightListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Traffic Insights",
    description="Returns paginated, filterable list of persisted decision intelligence insights.",
)
def list_insights(
    session_id: Optional[str] = Query(None, description="Filter by AnalysisSession ID"),
    job_id: Optional[str] = Query(None, description="Filter by AnalysisJob ID"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. 'CONGESTION', 'FLOW_DEGRADATION')"),
    severity: Optional[str] = Query(None, description="Filter by severity ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')"),
    insight_status: Optional[str] = Query(None, alias="status", description="Filter by status ('NEW', 'ACTIVE', 'RECOVERED', 'DISMISSED')"),
    affected_lane_id: Optional[str] = Query(None, description="Filter by affected lane ID"),
    provenance_category: Optional[str] = Query(None, description="Filter by provenance category"),
    is_synthetic: Optional[bool] = Query(None, description="Filter by synthetic flag"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> TrafficInsightListResponse:
    """Queries persisted insights with indexed multi-parameter filtering and bounded pagination."""
    query = select(TrafficInsight)

    if session_id:
        query = query.where(TrafficInsight.session_id == session_id)
    if job_id:
        query = query.where(TrafficInsight.job_id == job_id)
    if category:
        clean_cat = category.strip().upper()
        query = query.where(TrafficInsight.category == clean_cat)
    if severity:
        clean_sev = severity.strip().upper()
        query = query.where(TrafficInsight.severity == clean_sev)
    if insight_status:
        clean_st = insight_status.strip().upper()
        query = query.where(TrafficInsight.status == clean_st)
    if affected_lane_id:
        query = query.where(TrafficInsight.affected_lane_id == affected_lane_id)
    if provenance_category:
        query = query.where(TrafficInsight.provenance_category == provenance_category)
    if is_synthetic is not None:
        query = query.where(TrafficInsight.is_synthetic == is_synthetic)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    # Count active insights in total matching filter
    active_query = query.where(TrafficInsight.status.in_([InsightStatus.NEW.value, InsightStatus.ACTIVE.value]))
    active_count = db.scalar(select(func.count()).select_from(active_query.subquery())) or 0

    # Retrieve sorted by newest created first
    raw_insights = list(
        db.scalars(
            query.order_by(TrafficInsight.created_at.desc()).offset(offset).limit(limit)
        ).all()
    )

    # Compute provenance breakdown
    prov_counts: dict[str, int] = {}
    for ins in raw_insights:
        prov_counts[ins.provenance_category] = prov_counts.get(ins.provenance_category, 0) + 1

    schemas = [TrafficInsightSchema.model_validate(ins) for ins in raw_insights]
    return TrafficInsightListResponse(
        total=total,
        active_count=active_count,
        limit=limit,
        offset=offset,
        items=schemas,
        provenance_breakdown=prov_counts,
    )


@router.get(
    "/{insight_id}",
    response_model=TrafficInsightDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Traffic Insight Detail",
    description="Retrieves a single detailed insight record with full evidence package and root-cause factors.",
)
def get_insight_detail(
    insight_id: str,
    db: Session = Depends(get_db),
) -> TrafficInsightDetailResponse:
    """Retrieves a single insight by ID."""
    insight = db.scalar(select(TrafficInsight).where(TrafficInsight.id == insight_id))
    if not insight:
        raise AppException(
            f"Traffic insight with ID '{insight_id}' not found.",
            code="insight_not_found",
            status_code=404,
        )
    return TrafficInsightDetailResponse(insight=TrafficInsightSchema.model_validate(insight))


@router.patch(
    "/{insight_id}/status",
    response_model=TrafficInsightDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Traffic Insight Status",
    description="Updates the lifecycle operational status of a traffic insight (NEW, ACTIVE, RECOVERED, DISMISSED).",
)
def update_insight_status(
    insight_id: str,
    request: UpdateInsightStatusRequest,
    db: Session = Depends(get_db),
) -> TrafficInsightDetailResponse:
    """Updates the status of an existing insight."""
    clean_status = request.status.strip().upper()
    valid_statuses = {s.value for s in InsightStatus}
    if clean_status not in valid_statuses:
        raise AppException(
            f"Invalid insight status '{request.status}'. Must be one of: {sorted(list(valid_statuses))}",
            code="invalid_insight_status",
            status_code=400,
        )

    insight = db.scalar(select(TrafficInsight).where(TrafficInsight.id == insight_id))
    if not insight:
        raise AppException(
            f"Traffic insight with ID '{insight_id}' not found.",
            code="insight_not_found",
            status_code=404,
        )

    now = utcnow()
    insight.status = clean_status
    insight.updated_at = now
    if clean_status in [InsightStatus.RECOVERED.value, InsightStatus.DISMISSED.value]:
        insight.resolved_at = now

    db.commit()
    db.refresh(insight)

    logger.info("Updated status for insight %s to '%s'", insight_id, clean_status)
    return TrafficInsightDetailResponse(insight=TrafficInsightSchema.model_validate(insight))
