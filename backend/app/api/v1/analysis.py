"""
Analysis session persistence and historical query endpoints: /api/v1/analysis.
Phase 10: Database Integration.

Handles:
- POST /api/v1/analysis/videos/{video_id}/run — Execute analysis pipeline and persist session to database
- GET  /api/v1/analysis/sessions — List all historical analysis sessions (paginated)
- GET  /api/v1/analysis/sessions/{session_id} — Retrieve detailed session with metrics, lane density, and crossing events
- GET  /api/v1/analysis/videos/{video_id}/sessions — List analysis sessions for a specific video
- DELETE /api/v1/analysis/sessions/{session_id} — Delete an analysis session
- GET  /api/v1/analysis/info — Persistence service metadata and database schema info
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.analysis import AnalysisSession
from app.models.analysis_job import AnalysisJob
from app.models.video import Video
from app.schemas.analysis import (
    AnalysisInfoResponse,
    AnalysisRunRequest,
    AnalysisSessionDetailResponse,
    AnalysisSessionListResponse,
    AnalysisSessionSummarySchema,
)
from app.schemas.analysis_job import (
    AnalysisJobCancelResponse,
    AnalysisJobCreateRequest,
    AnalysisJobListResponse,
    AnalysisJobResponse,
)
from app.services.cv.analysis_persistence_service import AnalysisPersistenceService
from app.services.cv.job_manager import AnalysisJobManager, get_analysis_job_manager

router = APIRouter()
logger = get_logger(__name__)

# Module singleton service instance
_persistence_service: Optional[AnalysisPersistenceService] = None


def get_persistence_service() -> AnalysisPersistenceService:
    global _persistence_service
    if _persistence_service is None:
        _persistence_service = AnalysisPersistenceService()
    return _persistence_service


@router.get(
    "/info",
    response_model=AnalysisInfoResponse,
    summary="Get analysis persistence service information",
)
def get_analysis_info() -> AnalysisInfoResponse:
    """Returns database persistence metadata, supported analysis types, and schema rules."""
    return AnalysisInfoResponse()


# =========================================================================
# Phase 17: Analysis Job Orchestration Endpoints
# =========================================================================


@router.post(
    "/jobs",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and queue an asynchronous video analysis job",
    description="Submits a video for long-running computer vision processing in the background without blocking the HTTP request.",
)
def create_analysis_job(
    request: AnalysisJobCreateRequest,
    db: Session = Depends(get_db),
    manager: AnalysisJobManager = Depends(get_analysis_job_manager),
) -> AnalysisJobResponse:
    job = manager.submit_job(db=db, request=request)
    return AnalysisJobResponse.model_validate(job)


@router.get(
    "/jobs",
    response_model=AnalysisJobListResponse,
    summary="List analysis jobs (paginated)",
    description="Returns a paginated list of asynchronous analysis background jobs ordered by creation time descending.",
)
def list_analysis_jobs(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum jobs to return"),
    offset: int = Query(default=0, ge=0, description="Number of jobs to skip"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by job status"),
    video_id: Optional[str] = Query(default=None, description="Filter by video ID"),
    db: Session = Depends(get_db),
) -> AnalysisJobListResponse:
    query = db.query(AnalysisJob)
    if status_filter:
        query = query.filter(AnalysisJob.status == status_filter)
    if video_id:
        query = query.filter(AnalysisJob.video_id == video_id)

    total = query.count()
    jobs = query.order_by(AnalysisJob.created_at.desc()).offset(offset).limit(limit).all()

    return AnalysisJobListResponse(
        total=total,
        limit=limit,
        offset=offset,
        jobs=[AnalysisJobResponse.model_validate(j) for j in jobs],
    )


@router.get(
    "/jobs/{job_id}",
    response_model=AnalysisJobResponse,
    summary="Get analysis job status and progress",
    description="Retrieves the real-time execution status, progress percentage, frame counters, and completion details for an analysis job.",
)
def get_analysis_job(
    job_id: str,
    db: Session = Depends(get_db),
) -> AnalysisJobResponse:
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise AppException(
            f"Analysis job with ID '{job_id}' not found.",
            code="job_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return AnalysisJobResponse.model_validate(job)


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=AnalysisJobCancelResponse,
    summary="Cancel a queued or running analysis job",
    description="Requests cooperative cancellation of an active analysis job. Rejects cancellation of terminal jobs.",
)
def cancel_analysis_job(
    job_id: str,
    db: Session = Depends(get_db),
    manager: AnalysisJobManager = Depends(get_analysis_job_manager),
) -> AnalysisJobCancelResponse:
    job = manager.cancel_job(db=db, job_id=job_id)
    return AnalysisJobCancelResponse(
        status="cancelled" if job.status == "cancelled" else "cancellation_requested",
        message=f"Analysis job '{job_id}' cancellation processed.",
        job=AnalysisJobResponse.model_validate(job),
    )


@router.post(
    "/videos/{video_id}/run",
    response_model=AnalysisSessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute CV pipeline on video and persist results",
    description="Runs detection, tracking, counting, traffic flow analytics, and lane density analysis, persisting structured records to the database.",
)
def run_and_persist_analysis(
    video_id: str,
    request_params: AnalysisRunRequest = AnalysisRunRequest(),
    db: Session = Depends(get_db),
    service: AnalysisPersistenceService = Depends(get_persistence_service),
) -> AnalysisSessionDetailResponse:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise AppException(
            f"Video with ID '{video_id}' not found.",
            code="video_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    session = service.execute_and_persist(
        video=video,
        db=db,
        request=request_params,
    )
    return service.session_to_detail_response(session)


@router.get(
    "/sessions",
    response_model=AnalysisSessionListResponse,
    summary="List historical analysis sessions",
    description="Returns a paginated list of analysis execution runs ordered by start time descending.",
)
def list_analysis_sessions(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum sessions to return"),
    offset: int = Query(default=0, ge=0, description="Number of sessions to skip"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by session status"),
    analysis_type: Optional[str] = Query(default=None, description="Filter by analysis type"),
    db: Session = Depends(get_db),
    service: AnalysisPersistenceService = Depends(get_persistence_service),
) -> AnalysisSessionListResponse:
    query = db.query(AnalysisSession)
    if status_filter:
        query = query.filter(AnalysisSession.status == status_filter)
    if analysis_type:
        query = query.filter(AnalysisSession.analysis_type == analysis_type)

    total = query.count()
    sessions = query.order_by(AnalysisSession.started_at.desc()).offset(offset).limit(limit).all()

    return AnalysisSessionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        sessions=[service.session_to_summary_schema(s) for s in sessions],
    )


@router.get(
    "/sessions/{session_id}",
    response_model=AnalysisSessionDetailResponse,
    summary="Get detailed analysis session record",
    description="Retrieves an analysis session with all child traffic metrics, lane density results, and crossing event logs.",
)
def get_analysis_session(
    session_id: str,
    db: Session = Depends(get_db),
    service: AnalysisPersistenceService = Depends(get_persistence_service),
) -> AnalysisSessionDetailResponse:
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise AppException(
            f"Analysis session with ID '{session_id}' not found.",
            code="session_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return service.session_to_detail_response(session)


@router.get(
    "/videos/{video_id}/sessions",
    response_model=AnalysisSessionListResponse,
    summary="List analysis sessions for a specific video",
)
def list_sessions_for_video(
    video_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    service: AnalysisPersistenceService = Depends(get_persistence_service),
) -> AnalysisSessionListResponse:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise AppException(
            f"Video with ID '{video_id}' not found.",
            code="video_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    query = db.query(AnalysisSession).filter(AnalysisSession.video_id == video_id)
    total = query.count()
    sessions = query.order_by(AnalysisSession.started_at.desc()).offset(offset).limit(limit).all()

    return AnalysisSessionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        sessions=[service.session_to_summary_schema(s) for s in sessions],
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an analysis session",
    description="Permanently deletes an analysis session and cascade deletes all child traffic metrics, lane results, and crossing events.",
)
def delete_analysis_session(
    session_id: str,
    db: Session = Depends(get_db),
) -> dict:
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise AppException(
            f"Analysis session with ID '{session_id}' not found.",
            code="session_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    db.delete(session)
    db.commit()
    logger.info("Deleted analysis session %s", session_id)
    return {
        "status": "ok",
        "message": f"Analysis session '{session_id}' and all associated metrics successfully deleted.",
        "deleted_id": session_id,
    }
