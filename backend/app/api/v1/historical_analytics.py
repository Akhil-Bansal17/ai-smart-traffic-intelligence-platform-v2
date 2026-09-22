"""
Historical Traffic Intelligence & Trend Analysis API Router.
Phase 22: Historical Traffic Intelligence & Trend Analysis.

Mounted at: /api/v1/historical-analytics
Strictly descriptive, retrospective, provenance-grounded traffic intelligence.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.historical_analytics import (
    AnomalyHistoryResponse,
    DirectionalTrendResponse,
    HistoricalFilterParams,
    HistoricalSummaryResponse,
    HistoricalTimeSeriesResponse,
    LaneIntelligenceResponse,
    PeakPeriodsResponse,
    PeriodComparisonResponse,
    SourceComparisonResponse,
    VehicleCompositionTrendResponse,
)
from app.services.analytics.historical_analytics_service import HistoricalAnalyticsService

router = APIRouter()


def get_filter_params(
    start_time: Optional[datetime] = Query(None, description="Start datetime (ISO 8601 UTC)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (ISO 8601 UTC)"),
    time_preset: Optional[str] = Query("7d", description="Preset: 24h, 7d, 30d, 90d, custom"),
    camera_source_id: Optional[str] = Query(None, description="Filter by camera source ID"),
    session_mode: Optional[str] = Query(None, description="Filter by mode: file_analysis, live_monitoring"),
    include_synthetic: bool = Query(False, description="Include synthetic/test data (default false for real-world isolation)"),
    bucket_interval: Optional[str] = Query("hourly", description="Bucketing interval: 15m, 30m, hourly, daily, weekly"),
) -> HistoricalFilterParams:
    return HistoricalFilterParams(
        start_time=start_time,
        end_time=end_time,
        time_preset=time_preset,
        camera_source_id=camera_source_id,
        session_mode=session_mode,
        include_synthetic=include_synthetic,
        bucket_interval=bucket_interval,
    )


@router.get(
    "/summary",
    response_model=HistoricalSummaryResponse,
    summary="Get aggregated historical traffic summary",
    description="Returns total observed volume, duration, normalized flow rates, inbound/outbound split, and provenance.",
)
def get_historical_summary(
    params: HistoricalFilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
) -> HistoricalSummaryResponse:
    return HistoricalAnalyticsService.get_summary(db=db, params=params)


@router.get(
    "/timeseries",
    response_model=HistoricalTimeSeriesResponse,
    summary="Get historical discrete time-series buckets",
    description="Returns non-interpolated time-series bucket aggregation (hourly/daily) with volume, flow rates, and duration.",
)
def get_historical_timeseries(
    params: HistoricalFilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
) -> HistoricalTimeSeriesResponse:
    return HistoricalAnalyticsService.get_timeseries(db=db, params=params)


@router.get(
    "/vehicle-composition",
    response_model=VehicleCompositionTrendResponse,
    summary="Get vehicle classification composition and trends",
    description="Returns volume, percentage share, and temporal trends strictly across genuine supported vehicle classes.",
)
def get_vehicle_composition_trends(
    params: HistoricalFilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
) -> VehicleCompositionTrendResponse:
    return HistoricalAnalyticsService.get_vehicle_composition(db=db, params=params)


@router.get(
    "/directions",
    response_model=DirectionalTrendResponse,
    summary="Get directional traffic split and flow trends",
    description="Returns inbound vs. outbound traffic counts, percentage splits, and ratio trends over time.",
)
def get_directional_trends(
    params: HistoricalFilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
) -> DirectionalTrendResponse:
    return HistoricalAnalyticsService.get_directions(db=db, params=params)


@router.get(
    "/lanes",
    response_model=LaneIntelligenceResponse,
    summary="Get lane utilization, occupancy, and density history",
    description="Returns historical lane volume share, peak/avg occupancy, and image-space density with calibration warnings.",
)
def get_lane_intelligence(
    params: HistoricalFilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
) -> LaneIntelligenceResponse:
    return HistoricalAnalyticsService.get_lanes(db=db, params=params)


@router.get(
    "/peaks",
    response_model=PeakPeriodsResponse,
    summary="Get deterministic observed peak traffic periods",
    description="Identifies observed peak flow, peak volume, and peak density periods with explicit tie-breaking rules.",
)
def get_observed_peak_periods(
    params: HistoricalFilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
) -> PeakPeriodsResponse:
    return HistoricalAnalyticsService.get_peaks(db=db, params=params)


@router.get(
    "/anomalies",
    response_model=AnomalyHistoryResponse,
    summary="Get historical traffic anomaly and incident statistics",
    description="Returns operational anomaly counts by type, severity, status, and associated observation sources.",
)
def get_anomaly_history(
    params: HistoricalFilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
) -> AnomalyHistoryResponse:
    return HistoricalAnalyticsService.get_anomalies(db=db, params=params)


@router.get(
    "/sources",
    response_model=SourceComparisonResponse,
    summary="Get comparative analytics across camera and video sources",
    description="Compares traffic volume, observation duration, flow rates, and incidents across monitored sources.",
)
def get_source_comparison(
    params: HistoricalFilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
) -> SourceComparisonResponse:
    return HistoricalAnalyticsService.get_sources(db=db, params=params)


@router.get(
    "/compare",
    response_model=PeriodComparisonResponse,
    summary="Get period-over-period comparative metrics",
    description="Compares traffic metrics between current time window and immediately preceding equivalent window.",
)
def get_period_comparison(
    params: HistoricalFilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
) -> PeriodComparisonResponse:
    return HistoricalAnalyticsService.get_comparison(db=db, params=params)
