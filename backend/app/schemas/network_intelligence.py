"""
Pydantic schemas for Network Intelligence & Multi-Source Traffic Analytics.
Phase 24: Advanced Traffic Operations Analytics & Network Intelligence.

Defines strict type contracts, epistemic status labels, and multi-source aggregation responses:
- Epistemic status: OBSERVED, DERIVED, EXTRAPOLATED, UNAVAILABLE
- Provenance status: REAL DATA, TEST FIXTURE, MIXED, UNAVAILABLE
- Supported vehicle classes strictly matching repository reality: car, truck, bus, motorcycle, bicycle
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.historical_analytics import (
    HistoricalProvenanceSummary,
    LaneIntelligenceItem,
    PeriodComparisonResponse,
)

SUPPORTED_VEHICLE_CLASSES: List[str] = ["car", "motorcycle", "bus", "truck", "bicycle"]



class NetworkFilterParams(BaseModel):
    """Filter parameters for querying multi-source network intelligence."""
    start_time: Optional[datetime] = Field(None, description="Start datetime (UTC, inclusive)")
    end_time: Optional[datetime] = Field(None, description="End datetime (UTC, inclusive)")
    time_preset: Optional[str] = Field("7d", description="Quick preset: 24h, 7d, 30d, 90d, custom")
    source_ids: Optional[List[str]] = Field(None, description="Filter to specific camera/source IDs")
    include_synthetic: bool = Field(False, description="Whether to include synthetic test data or test fixtures")
    bucket_interval: Optional[str] = Field("hourly", description="Temporal aggregation bucket interval: hourly, daily")


class NetworkVehicleClassItem(BaseModel):
    """Vehicle class distribution item with strict repository classes."""
    class_name: str
    count: int = 0
    percentage: float = 0.0
    rate_per_hour: float = 0.0
    epistemic_status: str = "OBSERVED"


class NetworkDirectionalSummary(BaseModel):
    """Directional balance across the analyzed traffic network."""
    inbound_count: int = 0
    outbound_count: int = 0
    inbound_percentage: float = 0.0
    outbound_percentage: float = 0.0
    directional_ratio: float = 1.0
    balance_status: str = "balanced"  # balanced, inbound_dominant, outbound_dominant
    epistemic_status: str = "OBSERVED"


class NetworkLaneSummary(BaseModel):
    """Lane intelligence summary across monitored traffic sources."""
    total_lanes: int = 0
    sources_with_lanes: int = 0
    busiest_lane_name: Optional[str] = None
    highest_density_lane_name: Optional[str] = None
    average_density: float = 0.0
    density_unit: str = "vehicles/px²"
    density_warning: str = "Uncalibrated image-space density heuristic: relative comparison only, not physical density (pce/km)."
    lane_data_status: str = "OBSERVED"  # OBSERVED, UNAVAILABLE
    epistemic_status: str = "OBSERVED"  # OBSERVED, UNAVAILABLE


class NetworkOverviewResponse(BaseModel):
    """Network-wide traffic overview aggregating multiple camera sources."""
    time_range_start: datetime
    time_range_end: datetime
    total_sources: int = 0
    selected_sources_count: int = 0
    active_sources_count: int = 0
    total_volume: int = 0
    flow_rate_per_minute: float = 0.0
    flow_rate_per_hour: float = 0.0
    observation_duration_seconds: float = 0.0
    session_count: int = 0
    active_incident_count: int = 0
    recurring_incident_locations_count: int = 0
    vehicle_classes: List[NetworkVehicleClassItem] = Field(default_factory=list)
    directional_summary: NetworkDirectionalSummary
    lane_summary: NetworkLaneSummary
    top_hotspot_source_name: Optional[str] = None
    epistemic_status: str = "OBSERVED"  # OBSERVED, DERIVED, EXTRAPOLATED, UNAVAILABLE
    data_status: str = "observed"  # observed, sparse, empty
    data_message: str = "Authoritative network intelligence aggregated from persisted observations"
    provenance: HistoricalProvenanceSummary


class NetworkSourceComparisonItem(BaseModel):
    """Comparative traffic metric item for a single camera or video source."""
    source_id: str
    source_name: str
    source_type: str
    location_name: Optional[str] = None
    status: str = "unknown"
    observed_volume: int = 0
    flow_rate_per_hour: float = 0.0
    observation_duration_seconds: float = 0.0
    session_count: int = 0
    vehicle_composition: Dict[str, int] = Field(default_factory=dict)
    dominant_vehicle_class: Optional[str] = None
    inbound_count: int = 0
    outbound_count: int = 0
    directional_balance: str = "balanced"  # balanced, inbound_dominant, outbound_dominant
    has_lane_data: bool = False
    lane_count: int = 0
    average_lane_density: Optional[float] = None
    busiest_lane_name: Optional[str] = None
    incident_count: int = 0
    anomaly_count: int = 0
    recurring_incident_count: int = 0
    provenance_label: str = "REAL DATA"  # REAL DATA, TEST FIXTURE, MIXED
    epistemic_status: str = "OBSERVED"  # OBSERVED, DERIVED, EXTRAPOLATED
    observation_window_start: Optional[datetime] = None
    observation_window_end: Optional[datetime] = None
    window_mismatch: bool = False
    window_mismatch_details: Optional[str] = None


class NetworkSourceComparisonResponse(BaseModel):
    """Comparative response evaluating metrics across multiple sources."""
    time_range_start: datetime
    time_range_end: datetime
    total_sources_compared: int = 0
    busiest_source_name: Optional[str] = None
    highest_incident_source_name: Optional[str] = None
    sources: List[NetworkSourceComparisonItem] = Field(default_factory=list)
    window_mismatch_detected: bool = False
    comparison_notes: Optional[str] = None
    epistemic_status: str = "DERIVED"
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class NetworkHotspotItem(BaseModel):
    """Evidence-based traffic hotspot identified from persisted records."""
    rank: int
    source_id: str
    source_name: str
    location_name: Optional[str] = None
    hotspot_type: str = "source_hotspot"  # source_hotspot or intersection_hotspot
    hotspot_score: float = 0.0  # 0.0 - 100.0 composite intensity score
    severity: str = "low"  # low, medium, high, critical
    incident_count: int = 0
    recurring_incident_count: int = 0
    anomaly_count: int = 0
    observed_volume: int = 0
    flow_rate_per_hour: float = 0.0
    average_lane_density: Optional[float] = None
    primary_contributing_factor: str
    contributing_factors: List[str] = Field(default_factory=list)
    epistemic_status: str = "DERIVED"
    provenance_label: str = "REAL DATA"


class NetworkHotspotResponse(BaseModel):
    """Ranked hotspot response based solely on recorded traffic evidence."""
    time_range_start: datetime
    time_range_end: datetime
    total_hotspots_identified: int = 0
    hotspots: List[NetworkHotspotItem] = Field(default_factory=list)
    epistemic_note: str = (
        "Hotspots represent source-level concentrations derived from observed incident frequency, "
        "congestion anomaly events, and flow density. Physical geographic coordinates are not assumed when not provided."
    )
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class NetworkVehicleCompositionResponse(BaseModel):
    """Network-wide vehicle classification and cross-source dominance."""
    time_range_start: datetime
    time_range_end: datetime
    total_vehicles: int = 0
    heavy_vehicle_percentage: float = 0.0
    network_dominant_class: Optional[str] = None
    classes: List[NetworkVehicleClassItem] = Field(default_factory=list)
    source_composition: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    source_dominant_classes: Dict[str, str] = Field(default_factory=dict)
    epistemic_status: str = "OBSERVED"
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class NetworkDirectionalSourceItem(BaseModel):
    """Per-source directional flow details."""
    source_id: str
    source_name: str
    location_name: Optional[str] = None
    inbound_count: int = 0
    outbound_count: int = 0
    inbound_percentage: float = 0.0
    outbound_percentage: float = 0.0
    directional_ratio: float = 1.0
    balance_status: str = "balanced"


class NetworkDirectionalResponse(BaseModel):
    """Network and per-source directional intelligence."""
    time_range_start: datetime
    time_range_end: datetime
    network_summary: NetworkDirectionalSummary
    sources: List[NetworkDirectionalSourceItem] = Field(default_factory=list)
    inbound_dominant_count: int = 0
    outbound_dominant_count: int = 0
    balanced_count: int = 0
    epistemic_status: str = "DERIVED"
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class NetworkLaneResponse(BaseModel):
    """Cross-source lane utilization, peak occupancy, and density."""
    time_range_start: datetime
    time_range_end: datetime
    total_lanes: int = 0
    sources_with_lanes_count: int = 0
    sources_without_lanes_count: int = 0
    lanes: List[LaneIntelligenceItem] = Field(default_factory=list)
    busiest_lane_name: Optional[str] = None
    highest_density_lane_name: Optional[str] = None
    density_calibration_disclaimer: str = (
        "Uncalibrated image-space density heuristic: relative comparison only, not physical density (pce/km)."
    )
    epistemic_status: str = "OBSERVED"
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class NetworkTemporalBucketSourceItem(BaseModel):
    """Source traffic metrics in a discrete temporal bucket."""
    source_id: str
    source_name: str
    volume: int = 0
    flow_rate_per_hour: float = 0.0


class NetworkTemporalBucket(BaseModel):
    """Synchronized timeline bucket for cross-source temporal analysis."""
    bucket_index: int
    start_time: datetime
    end_time: datetime
    total_volume: int = 0
    sources: List[NetworkTemporalBucketSourceItem] = Field(default_factory=list)
    active_sources_count: int = 0
    is_network_peak: bool = False


class NetworkTemporalAnalysisResponse(BaseModel):
    """Cross-source temporal pattern analysis across synchronized observation windows."""
    time_range_start: datetime
    time_range_end: datetime
    bucket_interval: str
    total_buckets: int = 0
    buckets: List[NetworkTemporalBucket] = Field(default_factory=list)
    synchronized_peak_buckets_count: int = 0
    epistemic_note: str = (
        "Temporal cross-source patterns represent synchronized observation windows. "
        "No vehicle travel times, propagation speeds, or route causality are asserted without multi-camera tracking evidence."
    )
    epistemic_status: str = "DERIVED"
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary
