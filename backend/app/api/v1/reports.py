"""
REST API Endpoints for Traffic Intelligence Reporting & Export.
Phase 19: Business-Grade Traffic Reporting & Export.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.report import ReportFormat, ReportScopeType, ReportType
from app.schemas.report import (
    CreateReportRequest,
    ReportDetailResponse,
    ReportInfoResponse,
    ReportListResponse,
    ReportSummarySchema,
)
from app.services.reports.models import TruthLabel
from app.services.reports.service import ReportService

router = APIRouter()


@router.get("/info", response_model=ReportInfoResponse)
def get_reporting_info() -> ReportInfoResponse:
    """
    Returns reporting subsystem capabilities, supported report types,
    export formats, and epistemic truth labeling taxonomy.
    """
    return ReportInfoResponse(
        name="Traffic Intelligence Reporting Subsystem",
        version="1.0.0",
        supported_report_types=[ReportType.TRAFFIC_ANALYSIS.value],
        supported_formats=[ReportFormat.PDF.value, ReportFormat.CSV.value, ReportFormat.JSON.value],
        truth_label_taxonomy={
            TruthLabel.OBSERVED.value: "Direct empirical measurement from computer vision pipeline",
            TruthLabel.INFERRED.value: "Deterministic analytical conclusion or deduction from empirical data",
            TruthLabel.PREDICTED.value: "Forecasting subsystem multi-step output with residual intervals",
            TruthLabel.SIMULATED.value: "Signal optimization or emergency corridor simulation result",
            TruthLabel.RECOMMENDED.value: "Actionable decision-support guidance for human operators",
            TruthLabel.UNAVAILABLE.value: "Underlying telemetry or sample count is unavailable/insufficient",
        },
        max_time_range_days=settings.max_report_time_range_days,
    )


@router.post("", response_model=ReportDetailResponse, status_code=status.HTTP_201_CREATED)
def create_and_generate_report(
    payload: CreateReportRequest,
    db: Session = Depends(get_db),
) -> ReportDetailResponse:
    """
    Creates and deterministically generates a business-grade traffic report (PDF/CSV).
    Never recomputes core analytics — all data is assembled from authoritative persisted records.
    """
    report = ReportService.create_and_generate_report(
        db=db,
        report_type=payload.report_type,
        scope_type=payload.scope_type,
        session_id=payload.session_id,
        time_range_start=payload.time_range_start,
        time_range_end=payload.time_range_end,
        export_format=payload.format,
        title=payload.title,
    )
    return ReportDetailResponse.model_validate(report)


@router.get("", response_model=ReportListResponse)
def list_reports(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Page size limit"),
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    status: Optional[str] = Query(None, description="Filter by generation status"),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """
    Returns a paginated list of generated traffic intelligence reports.
    """
    items, total = ReportService.list_reports(
        db=db,
        skip=skip,
        limit=limit,
        report_type=report_type,
        status=status,
    )
    return ReportListResponse(
        items=[ReportSummarySchema.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{report_id}", response_model=ReportDetailResponse)
def get_report_detail(
    report_id: str,
    db: Session = Depends(get_db),
) -> ReportDetailResponse:
    """
    Retrieves complete metadata and normalized assembled report data by ID.
    """
    report = ReportService.get_report(db, report_id)
    return ReportDetailResponse.model_validate(report)


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
):
    """
    Securely downloads the generated report artifact (PDF/CSV) with path traversal protection.
    Never exposes raw filesystem paths to the client.
    """
    safe_path, mime_type, filename = ReportService.get_report_file(db, report_id)
    return FileResponse(
        path=str(safe_path),
        media_type=mime_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{report_id}", status_code=status.HTTP_200_OK)
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
):
    """
    Deletes the report database record and safely removes the generated file artifact.
    """
    ReportService.delete_report(db, report_id)
    return {"message": f"Report '{report_id}' and associated file artifact deleted successfully."}
