"""
Pydantic v2 schemas for the Phase 14 System-Wide Traffic Intelligence Dashboard.
Covers all 10 modular sections, strict 5-state provenance labeling, and metadata.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SectionProvenanceDetail(BaseModel):
    """
    Explicit data provenance and state qualification for a dashboard section.
    Never inferred or defaulted to 'real' without verified backing.
    """
    model_config = ConfigDict(from_attributes=True)

    state: str = Field(
        ...,
        description="High-level state: 'REAL DATA', 'SIMULATION', 'PREDICTION', 'SYNTHETIC', or 'UNAVAILABLE'",
    )
    category: str = Field(
        ...,
        description="Fine-grained category: 'real_database_metrics', 'synthetic_pipeline_metrics', 'simulation_configured', 'synthetic_fixture', 'real_observations', 'real_observations_insufficient', or 'unavailable'",
    )
    badge_variant: str = Field(
        default="neutral",
        description="UI badge variant: 'success' (green), 'info' (cyan), 'warning' (amber), 'primary' (indigo), 'neutral' (slate)",
    )
    description: str = Field(
        default="",
        description="Human-readable explanation of this section's data origin and qualification",
    )


class SubsystemStatusItem(BaseModel):
    """Subsystem operational status derived from genuine component availability."""
    model_config = ConfigDict(from_attributes=True)

    phase: int
    name: str
    status: str = Field(
        ...,
        description="Operational status: 'available', 'degraded', 'insufficient', or 'unavailable'",
    )
    provenance_type: str
    note: str


class SystemHealthSection(BaseModel):
    """Section 1: Live system health, database reachability, and subsystem matrix."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    backend_online: bool = True
    database_connected: bool = True
    database_latency_ms: float = 0.0
    last_successful_session_at: Optional[datetime] = None
    last_session_id: Optional[str] = None
    subsystems: List[SubsystemStatusItem] = Field(default_factory=list)


class TrafficOverviewSection(BaseModel):
    """Section 2: Traffic overview metrics from the most recent analysis session."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    active_session_id: Optional[str] = None
    video_filename: Optional[str] = None
    total_sessions_count: int = 0
    total_videos_count: int = 0
    total_vehicles_counted: int = 0
    total_vehicles_detected: int = 0
    observation_duration_seconds: float = 0.0
    flow_rate_per_minute: float = 0.0
    flow_rate_per_hour: float = 0.0
    is_extrapolated: bool = False
    extrapolation_note: Optional[str] = None
    started_at: Optional[datetime] = None


class ClassDistributionItem(BaseModel):
    """Class breakdown item with counts and relative percentages."""
    model_config = ConfigDict(from_attributes=True)

    class_name: str
    count: int
    percentage: float


class VehicleCompositionSection(BaseModel):
    """Section 3: Vehicle class composition from persisted counting data."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    total_counted: int = 0
    class_distribution: List[ClassDistributionItem] = Field(default_factory=list)


class TimeSeriesBucketItem(BaseModel):
    """Discrete, non-interpolated time-series bucket."""
    model_config = ConfigDict(from_attributes=True)

    bucket_index: int
    start_time_seconds: float
    end_time_seconds: float
    count: int
    flow_rate_per_minute: float


class TrafficFlowSection(BaseModel):
    """Section 4: Discrete time-series traffic flow metrics."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    bucket_interval_seconds: float = 10.0
    is_extrapolated: bool = False
    time_series_buckets: List[TimeSeriesBucketItem] = Field(default_factory=list)


class LaneResultSummaryItem(BaseModel):
    """Per-lane density and occupancy summary."""
    model_config = ConfigDict(from_attributes=True)

    lane_id: str
    lane_name: str
    direction_hint: Optional[str] = None
    unique_vehicles_count: int = 0
    peak_occupancy: int = 0
    average_occupancy: float = 0.0
    image_space_density: float = 0.0
    normalized_density_score: float = 0.0
    polygon_area_px2: float = 0.0
    vehicle_class_counts: Optional[Dict[str, int]] = None


class LaneDensitySection(BaseModel):
    """Section 5: Lane analysis and image-space density estimation."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    total_lanes_analyzed: int = 0
    density_unit: str = "vehicles/px²"
    calibration_warning: str = "Image-space density (vehicles/px²) — not calibrated physical density (veh/km²)."
    lanes: List[LaneResultSummaryItem] = Field(default_factory=list)


class PredictionStatusSection(BaseModel):
    """Section 6: Traffic prediction model readiness and dynamic observation count."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    is_ready: bool = False
    status_code: str = "insufficient_observations"
    real_sample_count: int = 0
    synthetic_sample_count: int = 0
    threshold: int = 20
    readiness_message: str = ""
    latest_run_id: Optional[str] = None
    latest_model_name: Optional[str] = None
    latest_rmse: Optional[float] = None
    latest_mae: Optional[float] = None
    latest_r2: Optional[float] = None
    latest_horizon_minutes: Optional[int] = None
    latest_created_at: Optional[datetime] = None


class SignalOptimizationSection(BaseModel):
    """Section 7: Traffic signal optimization decision-support simulation results."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    disclaimer: str = "Simulation / Decision Support — not connected to physical signals."
    latest_run_id: Optional[str] = None
    intersection_name: Optional[str] = None
    intersection_type: Optional[str] = None
    algorithm_used: Optional[str] = None
    baseline_cycle_length: Optional[float] = None
    optimized_cycle_length: Optional[float] = None
    baseline_delay_proxy: Optional[float] = None
    optimized_delay_proxy: Optional[float] = None
    delay_reduction_pct: Optional[float] = None
    queue_reduction_pct: Optional[float] = None
    throughput_increase_pct: Optional[float] = None
    created_at: Optional[datetime] = None


class EmergencyCorridorSection(BaseModel):
    """Section 8: Emergency corridor simulation results & signal priority trade-offs."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    disclaimer: str = "Simulation / Decision Support — not a real dispatch or control system."
    latest_run_id: Optional[str] = None
    corridor_name: Optional[str] = None
    corridor_nodes_count: Optional[int] = None
    vehicle_type: Optional[str] = None
    priority_strategy: Optional[str] = None
    baseline_travel_time_seconds: Optional[float] = None
    priority_travel_time_seconds: Optional[float] = None
    travel_time_savings_seconds: Optional[float] = None
    travel_time_savings_pct: Optional[float] = None
    emergency_delay_reduction_pct: Optional[float] = None
    cross_street_delay_impact_pct: Optional[float] = None
    created_at: Optional[datetime] = None


class HistorySessionSummaryItem(BaseModel):
    """Compact summary of a historical analysis session."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    original_filename: str
    source_type: str
    provenance_verified: bool
    total_vehicles_counted: int
    started_at: datetime
    status: str
    processing_time_ms: Optional[float] = None


class RecentHistorySection(BaseModel):
    """Section 9: List of recent historical analysis sessions."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    total_sessions_count: int = 0
    sessions: List[HistorySessionSummaryItem] = Field(default_factory=list)


class DataProvenanceSection(BaseModel):
    """Section 10: Complete data provenance transparency panel."""
    model_config = ConfigDict(from_attributes=True)

    provenance: SectionProvenanceDetail
    active_session_id: Optional[str] = None
    video_id: Optional[str] = None
    video_filename: Optional[str] = None
    source_type: str = "unknown"
    provenance_verified: bool = False
    source_reference: Optional[str] = None
    license_reference: Optional[str] = None
    provenance_note: Optional[str] = None
    captured_at: Optional[datetime] = None
    uploaded_at: Optional[datetime] = None


class DashboardSummaryResponse(BaseModel):
    """
    Composite single-roundtrip response for the Decision-Support Dashboard.
    Contains all 10 modular sections with independent provenance qualification.
    """
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    execution_time_ms: float
    system_health: SystemHealthSection
    traffic_overview: TrafficOverviewSection
    vehicle_composition: VehicleCompositionSection
    traffic_flow_metrics: TrafficFlowSection
    lane_density: LaneDensitySection
    prediction_availability: PredictionStatusSection
    signal_optimization: SignalOptimizationSection
    emergency_corridor: EmergencyCorridorSection
    recent_history: RecentHistorySection
    data_provenance: DataProvenanceSection


class DashboardInfoResponse(BaseModel):
    """Metadata response for dashboard API status and architectural guarantees."""
    model_config = ConfigDict(from_attributes=True)

    version: str = "1.0.0"
    phase: str = "Phase 14 — System-Wide Traffic Intelligence & Decision-Support Dashboard"
    description: str = "Unified aggregation and presentation layer over Phases 4–13 outputs"
    provenance_categories: List[str] = [
        "real_database_metrics",
        "synthetic_pipeline_metrics",
        "simulation_configured",
        "synthetic_fixture",
        "real_observations",
        "real_observations_insufficient",
        "unavailable",
    ]
    anti_trigger_guarantee: str = (
        "Strictly read-only: Opening or refreshing the dashboard will NEVER trigger "
        "video processing, YOLO inference, tracking, counting, training, or simulations."
    )
