"""
Pydantic schemas for Historical Traffic Intelligence & Trend Analysis.
Phase 22: Historical Traffic Intelligence & Trend Analysis.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HistoricalFilterParams(BaseModel):
    """Filter parameters for querying historical traffic intelligence."""
    start_time: Optional[datetime] = Field(None, description="Start datetime (UTC, inclusive)")
    end_time: Optional[datetime] = Field(None, description="End datetime (UTC, inclusive)")
    time_preset: Optional[str] = Field("7d", description="Quick preset: 24h, 7d, 30d, 90d, custom")
    camera_source_id: Optional[str] = Field(None, description="Filter to specific camera source ID")
    session_mode: Optional[str] = Field(None, description="Filter by session mode: file_analysis, live_monitoring")
    include_synthetic: bool = Field(False, description="Whether to include synthetic test data or test fixtures")
    bucket_interval: Optional[str] = Field("hourly", description="Aggregation bucket interval: 15m, 30m, hourly, daily, weekly")


class HistoricalProvenanceSummary(BaseModel):
    """Authoritative provenance and data authenticity summary."""
    source_types: List[str] = Field(default_factory=list)
    provenance_category: str = "unavailable"
    provenance_label: str = "UNAVAILABLE"  # REAL DATA, SYNTHETIC, TEST FIXTURE, MIXED, UNAVAILABLE
    provenance_badge_variant: str = "neutral"  # success, warning, danger, purple, neutral
    is_synthetic: bool = False
    is_mixed: bool = False
    is_extrapolated: bool = False
    observation_duration_seconds: float = 0.0
    session_count: int = 0
    camera_source_count: int = 0
    description: str = "No recorded sessions in scope"
    mix_warning: Optional[str] = None


class VehicleClassMetricItem(BaseModel):
    """Vehicle class volume, share, and temporal trend."""
    class_name: str
    count: int
    percentage: float
    trend: str = "stable"  # increasing, decreasing, stable, insufficient
    rate_per_hour: float = 0.0


class DirectionalFlowMetric(BaseModel):
    """Directional traffic count, proportion, and flow rate."""
    direction: str  # inbound, outbound, unknown
    count: int
    percentage: float
    flow_rate_per_hour: float = 0.0


class HistoricalBucketItem(BaseModel):
    """Discrete, non-interpolated time-series bucket."""
    bucket_index: int
    start_time: datetime
    end_time: datetime
    observation_duration_seconds: float = 0.0
    observed_volume: int = 0
    flow_rate_per_minute: float = 0.0
    flow_rate_per_hour: float = 0.0
    is_extrapolated: bool = False
    vehicle_composition: Dict[str, int] = Field(default_factory=dict)
    inbound_count: int = 0
    outbound_count: int = 0
    session_count: int = 0
    source_count: int = 0
    provenance_type: str = "unavailable"
    data_status: str = "observed"  # observed, sparse, empty


class PeakPeriodItem(BaseModel):
    """Deterministically observed peak traffic period."""
    peak_type: str  # flow_rate, volume, lane_density
    title: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    value: float = 0.0
    unit: str  # veh/hr, vehicles, score, vehicles/px²
    is_extrapolated: bool = False
    observation_duration_seconds: float = 0.0
    session_id: Optional[str] = None
    source_name: Optional[str] = None
    lane_name: Optional[str] = None
    tie_breaking_applied: bool = False
    details: Optional[str] = None


class LaneIntelligenceItem(BaseModel):
    """Lane-level traffic utilization, density, and occupancy history."""
    lane_id: str
    lane_name: str
    direction_hint: Optional[str] = None
    total_volume: int = 0
    average_occupancy: float = 0.0
    peak_occupancy: int = 0
    average_density: float = 0.0
    normalized_density_score: float = 0.0
    density_unit: str = "vehicles/px²"
    density_calibration_warning: Optional[str] = None
    volume_share_pct: float = 0.0
    session_count: int = 0


class AnomalyHistoryItem(BaseModel):
    """Historical record of an anomaly or congestion incident."""
    id: str
    anomaly_type: str
    severity: str
    status: str
    title: str
    description: str
    metric_name: str
    trigger_value: float
    threshold_value: float
    deviation_pct: Optional[float] = None
    lane_id: Optional[str] = None
    session_id: str
    source_name: Optional[str] = None
    duration_seconds: float = 0.0
    is_synthetic: bool = False
    created_at: datetime


class SourceMetricItem(BaseModel):
    """Aggregate traffic metrics per camera or video source."""
    source_id: str
    source_name: str
    source_type: str
    location_name: Optional[str] = None
    session_count: int = 0
    total_volume: int = 0
    total_duration_seconds: float = 0.0
    average_flow_rate_vph: float = 0.0
    is_extrapolated: bool = False
    anomaly_count: int = 0
    provenance_label: str = "REAL DATA"
    is_synthetic: bool = False


class PeriodDeltaMetric(BaseModel):
    """Metric comparison between current and previous time window."""
    metric_name: str
    current_value: float
    previous_value: float
    absolute_change: float
    percentage_change: Optional[float] = None
    trend_direction: str = "neutral"  # up, down, neutral, insufficient


# --- Response Envelopes ---

class HistoricalSummaryResponse(BaseModel):
    """Comprehensive high-level summary over the selected historical period."""
    time_range_start: datetime
    time_range_end: datetime
    observation_duration_seconds: float = 0.0
    total_observed_volume: int = 0
    flow_rate_per_minute: float = 0.0
    flow_rate_per_hour: float = 0.0
    is_extrapolated: bool = False
    inbound_volume: int = 0
    outbound_volume: int = 0
    inbound_percentage: float = 0.0
    outbound_percentage: float = 0.0
    session_count: int = 0
    source_count: int = 0
    anomaly_count: int = 0
    insight_count: int = 0
    peak_flow_rate_vph: float = 0.0
    peak_flow_period: Optional[str] = None
    data_status: str = "observed"  # observed, insufficient, empty
    data_message: str = "Authoritative observations synthesized from database"
    provenance: HistoricalProvenanceSummary


class HistoricalTimeSeriesResponse(BaseModel):
    """Time-series bucketed flow rate and volume distribution."""
    time_range_start: datetime
    time_range_end: datetime
    bucket_interval: str
    bucket_interval_seconds: int
    total_buckets: int
    buckets: List[HistoricalBucketItem]
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class VehicleCompositionTrendResponse(BaseModel):
    """Vehicle classification breakdown and temporal trend analysis."""
    time_range_start: datetime
    time_range_end: datetime
    total_vehicles: int = 0
    classes: List[VehicleClassMetricItem]
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class DirectionalTrendResponse(BaseModel):
    """Inbound vs. outbound directional traffic metrics and trends."""
    time_range_start: datetime
    time_range_end: datetime
    total_vehicles: int = 0
    inbound_count: int = 0
    outbound_count: int = 0
    inbound_percentage: float = 0.0
    outbound_percentage: float = 0.0
    directional_ratio: float = 1.0
    trend_direction: str = "balanced"  # inbound_dominant, outbound_dominant, balanced
    directions: List[DirectionalFlowMetric]
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class LaneIntelligenceResponse(BaseModel):
    """Lane-level traffic utilization, peak occupancy, and density history."""
    time_range_start: datetime
    time_range_end: datetime
    total_lanes: int = 0
    lanes: List[LaneIntelligenceItem]
    busiest_lane_name: Optional[str] = None
    highest_density_lane_name: Optional[str] = None
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class PeakPeriodsResponse(BaseModel):
    """Deterministic peak period analysis based solely on observed history."""
    time_range_start: datetime
    time_range_end: datetime
    peak_flow: PeakPeriodItem
    peak_volume: PeakPeriodItem
    peak_density: PeakPeriodItem
    tie_breaking_rule: str
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class AnomalyHistoryResponse(BaseModel):
    """Historical traffic anomalies and incident lifecycle analysis."""
    time_range_start: datetime
    time_range_end: datetime
    total_anomalies: int = 0
    active_anomalies: int = 0
    resolved_anomalies: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_severity: Dict[str, int] = Field(default_factory=dict)
    incidents: List[AnomalyHistoryItem]
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class SourceComparisonResponse(BaseModel):
    """Comparative analysis across distinct camera and video sources."""
    time_range_start: datetime
    time_range_end: datetime
    total_sources: int = 0
    sources: List[SourceMetricItem]
    busiest_source_name: Optional[str] = None
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary


class PeriodComparisonResponse(BaseModel):
    """Period-over-period comparison between current window and preceding window."""
    current_start: datetime
    current_end: datetime
    previous_start: datetime
    previous_end: datetime
    volume_comparison: PeriodDeltaMetric
    flow_rate_comparison: PeriodDeltaMetric
    duration_comparison: PeriodDeltaMetric
    anomaly_comparison: PeriodDeltaMetric
    session_comparison: PeriodDeltaMetric
    data_status: str = "observed"
    provenance: HistoricalProvenanceSummary
