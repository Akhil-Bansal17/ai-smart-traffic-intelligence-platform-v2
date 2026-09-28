"""
Network Intelligence & Multi-Source Traffic Operations REST API.
Phase 24: Advanced Traffic Operations Analytics & Network Intelligence.

Mounted at: /api/v1/network-intelligence
Provides:
- GET /overview: Network-wide traffic metrics, coverage, and health
- GET /compare: Source-by-source comparison with window mismatch detection
- GET /hotspots: Evidence-based traffic hotspot ranking
- GET /vehicle-composition: Network & per-source vehicle distribution
- GET /directional-analysis: Directional flow balance
- GET /lane-analysis: Cross-source lane utilization and density
- GET /temporal-analysis: Synchronized cross-source timeline patterns
- GET /historical-comparison: Period-over-period delta comparisons (Phase 22 reuse)
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.historical_analytics import PeriodComparisonResponse
from app.schemas.network_intelligence import (
    NetworkDirectionalResponse,
    NetworkFilterParams,
    NetworkHotspotResponse,
    NetworkLaneResponse,
    NetworkOverviewResponse,
    NetworkSourceComparisonResponse,
    NetworkTemporalAnalysisResponse,
    NetworkVehicleCompositionResponse,
)
from app.services.network_intelligence.service import NetworkIntelligenceService

router = APIRouter()


@router.get(
    "/overview",
    response_model=NetworkOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Network Traffic Overview",
    description="Aggregates observed traffic volume, flow rates, vehicle composition, active incidents, and data provenance across selected camera sources.",
)
def get_network_overview(
    time_preset: str = Query("7d", description="Preset: 24h, 7d, 30d, 90d, custom"),
    start_time: Optional[datetime] = Query(None, description="Start datetime (UTC, inclusive)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (UTC, inclusive)"),
    source_ids: Optional[List[str]] = Query(None, description="Optional camera/source ID filter"),
    include_synthetic: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db),
) -> NetworkOverviewResponse:
    params = NetworkFilterParams(
        time_preset=time_preset,
        start_time=start_time,
        end_time=end_time,
        source_ids=source_ids,
        include_synthetic=include_synthetic,
    )
    return NetworkIntelligenceService.get_network_overview(db=db, params=params)


@router.get(
    "/compare",
    response_model=NetworkSourceComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Traffic Sources",
    description="Evaluates traffic volume, flow rate, composition, directions, lane utilization, and incidents between sources with window mismatch detection.",
)
def compare_traffic_sources(
    time_preset: str = Query("7d", description="Preset: 24h, 7d, 30d, 90d, custom"),
    start_time: Optional[datetime] = Query(None, description="Start datetime (UTC, inclusive)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (UTC, inclusive)"),
    source_ids: Optional[List[str]] = Query(None, description="Filter specific sources"),
    include_synthetic: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db),
) -> NetworkSourceComparisonResponse:
    params = NetworkFilterParams(
        time_preset=time_preset,
        start_time=start_time,
        end_time=end_time,
        source_ids=source_ids,
        include_synthetic=include_synthetic,
    )
    return NetworkIntelligenceService.compare_sources(db=db, params=params)


@router.get(
    "/hotspots",
    response_model=NetworkHotspotResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Traffic Hotspots",
    description="Identifies operational traffic hotspots strictly from recorded incidents, recurring anomalies, high volume, and density evidence.",
)
def get_traffic_hotspots(
    time_preset: str = Query("7d", description="Preset: 24h, 7d, 30d, 90d, custom"),
    start_time: Optional[datetime] = Query(None, description="Start datetime (UTC, inclusive)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (UTC, inclusive)"),
    limit: int = Query(10, ge=1, le=50, description="Max hotspots to return"),
    include_synthetic: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db),
) -> NetworkHotspotResponse:
    params = NetworkFilterParams(
        time_preset=time_preset,
        start_time=start_time,
        end_time=end_time,
        include_synthetic=include_synthetic,
    )
    return NetworkIntelligenceService.get_hotspots(db=db, params=params, limit=limit)


@router.get(
    "/vehicle-composition",
    response_model=NetworkVehicleCompositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Network Vehicle Composition",
    description="Returns network-wide and per-source vehicle class breakdown across supported YOLO classes.",
)
def get_network_vehicle_composition(
    time_preset: str = Query("7d", description="Preset: 24h, 7d, 30d, 90d, custom"),
    start_time: Optional[datetime] = Query(None, description="Start datetime (UTC, inclusive)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (UTC, inclusive)"),
    source_ids: Optional[List[str]] = Query(None, description="Filter specific sources"),
    include_synthetic: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db),
) -> NetworkVehicleCompositionResponse:
    params = NetworkFilterParams(
        time_preset=time_preset,
        start_time=start_time,
        end_time=end_time,
        source_ids=source_ids,
        include_synthetic=include_synthetic,
    )
    return NetworkIntelligenceService.get_vehicle_composition(db=db, params=params)


@router.get(
    "/directional-analysis",
    response_model=NetworkDirectionalResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Directional Flow Intelligence",
    description="Computes inbound vs outbound traffic balance network-wide and per individual source.",
)
def get_directional_analysis(
    time_preset: str = Query("7d", description="Preset: 24h, 7d, 30d, 90d, custom"),
    start_time: Optional[datetime] = Query(None, description="Start datetime (UTC, inclusive)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (UTC, inclusive)"),
    source_ids: Optional[List[str]] = Query(None, description="Filter specific sources"),
    include_synthetic: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db),
) -> NetworkDirectionalResponse:
    params = NetworkFilterParams(
        time_preset=time_preset,
        start_time=start_time,
        end_time=end_time,
        source_ids=source_ids,
        include_synthetic=include_synthetic,
    )
    return NetworkIntelligenceService.get_directional_analysis(db=db, params=params)


@router.get(
    "/lane-analysis",
    response_model=NetworkLaneResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Cross-Source Lane Intelligence",
    description="Aggregates lane occupancy and image-space density; returns UNAVAILABLE for unconfigured cameras.",
)
def get_lane_analysis(
    time_preset: str = Query("7d", description="Preset: 24h, 7d, 30d, 90d, custom"),
    start_time: Optional[datetime] = Query(None, description="Start datetime (UTC, inclusive)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (UTC, inclusive)"),
    source_ids: Optional[List[str]] = Query(None, description="Filter specific sources"),
    include_synthetic: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db),
) -> NetworkLaneResponse:
    params = NetworkFilterParams(
        time_preset=time_preset,
        start_time=start_time,
        end_time=end_time,
        source_ids=source_ids,
        include_synthetic=include_synthetic,
    )
    return NetworkIntelligenceService.get_lane_analysis(db=db, params=params)


@router.get(
    "/temporal-analysis",
    response_model=NetworkTemporalAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Temporal Cross-Source Analysis",
    description="Evaluates cross-source synchronized timeline patterns across discrete hourly/daily buckets.",
)
def get_temporal_analysis(
    time_preset: str = Query("7d", description="Preset: 24h, 7d, 30d, 90d, custom"),
    start_time: Optional[datetime] = Query(None, description="Start datetime (UTC, inclusive)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (UTC, inclusive)"),
    source_ids: Optional[List[str]] = Query(None, description="Filter specific sources"),
    bucket_interval: str = Query("hourly", description="Bucket interval: hourly, daily"),
    include_synthetic: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db),
) -> NetworkTemporalAnalysisResponse:
    params = NetworkFilterParams(
        time_preset=time_preset,
        start_time=start_time,
        end_time=end_time,
        source_ids=source_ids,
        bucket_interval=bucket_interval,
        include_synthetic=include_synthetic,
    )
    return NetworkIntelligenceService.get_temporal_cross_source_analysis(db=db, params=params)


@router.get(
    "/historical-comparison",
    response_model=PeriodComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Network Historical Comparison",
    description="Reuses Phase 22 HistoricalAnalyticsService to compute authoritative period-over-period delta comparisons.",
)
def get_historical_comparison(
    time_preset: str = Query("7d", description="Preset: 24h, 7d, 30d, 90d, custom"),
    start_time: Optional[datetime] = Query(None, description="Start datetime (UTC, inclusive)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (UTC, inclusive)"),
    include_synthetic: bool = Query(False, description="Include test fixtures"),
    db: Session = Depends(get_db),
) -> PeriodComparisonResponse:
    params = NetworkFilterParams(
        time_preset=time_preset,
        start_time=start_time,
        end_time=end_time,
        include_synthetic=include_synthetic,
    )
    return NetworkIntelligenceService.get_historical_comparison(db=db, params=params)
