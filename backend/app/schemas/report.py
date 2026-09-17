"""
Pydantic v2 schemas for Business-Grade Traffic Reporting & Export.
Phase 19: Business-Grade Traffic Reporting & Export.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.report import ReportFormat, ReportScopeType, ReportStatus, ReportType


class CreateReportRequest(BaseModel):
    """Payload to request report generation."""
    model_config = ConfigDict(from_attributes=True)

    report_type: str = Field(
        default=ReportType.TRAFFIC_ANALYSIS.value,
        description="Type of report to generate.",
    )
    scope_type: str = Field(
        default=ReportScopeType.SESSION.value,
        description="Scope selector ('session' or 'time_range').",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Target analysis session ID when scope_type='session'.",
    )
    time_range_start: Optional[datetime] = Field(
        default=None,
        description="Start timestamp when scope_type='time_range'.",
    )
    time_range_end: Optional[datetime] = Field(
        default=None,
        description="End timestamp when scope_type='time_range'.",
    )
    format: str = Field(
        default=ReportFormat.PDF.value,
        description="Export format ('pdf', 'csv', 'json').",
    )
    title: Optional[str] = Field(
        default=None,
        description="Optional custom title for the report.",
    )


class ReportSummarySchema(BaseModel):
    """Summary schema for report listing."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_type: str
    scope_type: str
    session_id: Optional[str] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    title: str
    status: str
    format: str
    file_size_bytes: Optional[int] = None
    provenance_summary: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None


class ReportDetailResponse(BaseModel):
    """Detailed response schema including complete normalized report data."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_type: str
    scope_type: str
    session_id: Optional[str] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    title: str
    status: str
    format: str
    file_size_bytes: Optional[int] = None
    report_data_json: Optional[Dict[str, Any]] = None
    provenance_summary: Optional[Dict[str, Any]] = None
    artifact_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None

    @computed_field
    @property
    def report_data(self) -> Optional[Dict[str, Any]]:
        """Normalized report domain data."""
        return self.report_data_json


class ReportListResponse(BaseModel):
    """Paginated list response of reports."""
    model_config = ConfigDict(from_attributes=True)

    items: List[ReportSummarySchema]
    total: int
    skip: int
    limit: int


class ReportInfoResponse(BaseModel):
    """Metadata and capabilities info schema for reporting subsystem."""
    model_config = ConfigDict(from_attributes=True)

    name: str = "Traffic Intelligence Reporting Subsystem"
    version: str = "1.0.0"
    supported_report_types: List[str]
    supported_formats: List[str]
    truth_label_taxonomy: Dict[str, str]
    max_time_range_days: int
