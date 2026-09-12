"""
Dashboard Aggregator Service for Phase 14 Traffic Intelligence Command.
Strictly read-only: performs batched database queries with eager relationship joins,
evaluates dynamic subsystem readiness, and tags every section with explicit provenance.
Zero N+1 queries. Zero heavy CV/ML computation on load.
"""
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.logging import get_logger
from app.models.analysis import AnalysisSession, LaneResultRecord, TrafficMetricsRecord
from app.models.corridor_simulation import EmergencyCorridorSimulationRun
from app.models.prediction import PredictionRun
from app.models.simulation import SignalSimulationRun
from app.models.video import Video
from app.schemas.dashboard import (
    ClassDistributionItem,
    DashboardSummaryResponse,
    DataProvenanceSection,
    EmergencyCorridorSection,
    HistorySessionSummaryItem,
    LaneDensitySection,
    LaneResultSummaryItem,
    PredictionStatusSection,
    RecentHistorySection,
    SectionProvenanceDetail,
    SignalOptimizationSection,
    SubsystemStatusItem,
    SystemHealthSection,
    TimeSeriesBucketItem,
    TrafficFlowSection,
    TrafficOverviewSection,
    VehicleCompositionSection,
)
from app.services.ml.dataset_extractor import DatasetExtractor

logger = get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DashboardAggregatorService:
    """
    Read-only aggregation service for the Decision-Support Dashboard.
    Collects and synthesizes verified outputs from Phases 4–13.
    """

    def __init__(self, dataset_extractor: Optional[DatasetExtractor] = None):
        self.dataset_extractor = dataset_extractor or DatasetExtractor()

    def get_summary(
        self,
        db: Session,
        session_id: Optional[str] = None,
    ) -> DashboardSummaryResponse:
        """
        Gathers composite dashboard summary data in a single batched operation.
        Opening or refreshing never triggers pipeline executions.
        """
        start_time = time.perf_counter()
        now = utcnow()

        # 1. Measure DB Connectivity and Latency
        db_start = time.perf_counter()
        db_connected = True
        try:
            db.execute(text("SELECT 1"))
            db_latency_ms = round((time.perf_counter() - db_start) * 1000.0, 3)
        except Exception as e:
            logger.error("Database connectivity check failed", error=str(e))
            db_connected = False
            db_latency_ms = 0.0

        # 2. Batched Global Aggregations (Counts)
        total_sessions = db.scalar(select(func.count(AnalysisSession.id))) or 0
        total_videos = db.scalar(select(func.count(Video.id))) or 0
        total_counted = (
            db.scalar(select(func.coalesce(func.sum(AnalysisSession.total_vehicles_counted), 0))) or 0
        )
        total_detected = (
            db.scalar(select(func.coalesce(func.sum(AnalysisSession.total_vehicles_detected), 0))) or 0
        )

        # 3. Active Session Resolution (Eagerly loaded to prevent N+1)
        session_stmt = (
            select(AnalysisSession)
            .options(
                joinedload(AnalysisSession.video),
                selectinload(AnalysisSession.traffic_metrics),
                selectinload(AnalysisSession.lane_results),
            )
        )

        active_session: Optional[AnalysisSession] = None
        if session_id:
            active_session = db.scalar(session_stmt.where(AnalysisSession.id == session_id))
        
        if not active_session:
            # Pick latest completed session with traffic metrics
            active_session = db.scalar(
                session_stmt.where(AnalysisSession.status == "completed")
                .order_by(AnalysisSession.completed_at.desc(), AnalysisSession.started_at.desc())
                .limit(1)
            )

        if not active_session:
            # Fallback to any latest session
            active_session = db.scalar(
                session_stmt.order_by(AnalysisSession.started_at.desc()).limit(1)
            )

        # 4. Derive Active Session Provenance
        active_video = active_session.video if active_session else None
        if active_video and active_video.source_type == "real_world" and active_video.provenance_verified:
            session_prov_state = "REAL DATA"
            session_prov_cat = "real_database_metrics"
            session_prov_badge = "success"
            session_prov_desc = f"Verified genuine real-world traffic recording ({active_video.original_filename})"
        elif active_video:
            session_prov_state = "SYNTHETIC"
            session_prov_cat = "synthetic_pipeline_metrics"
            session_prov_badge = "warning"
            session_prov_desc = f"Synthetic/test pipeline processing run ({active_video.original_filename})"
        else:
            session_prov_state = "UNAVAILABLE"
            session_prov_cat = "unavailable"
            session_prov_badge = "neutral"
            session_prov_desc = "No recorded video analysis sessions available in database"

        # 5. Dynamic Dataset & Prediction Readiness Check (Phase 11)
        readiness = self.dataset_extractor.check_readiness(db)

        # Latest Prediction Run
        latest_prediction_run = db.scalar(
            select(PredictionRun).order_by(PredictionRun.created_at.desc()).limit(1)
        )

        # 6. Latest Signal Optimization Simulation Run (Phase 12)
        latest_signal_run = db.scalar(
            select(SignalSimulationRun).order_by(SignalSimulationRun.created_at.desc()).limit(1)
        )

        # 7. Latest Emergency Corridor Simulation Run (Phase 13)
        latest_corridor_run = db.scalar(
            select(EmergencyCorridorSimulationRun)
            .order_by(EmergencyCorridorSimulationRun.created_at.desc())
            .limit(1)
        )

        # 8. Recent 5 Historical Sessions
        recent_sessions_raw = db.scalars(
            select(AnalysisSession)
            .options(joinedload(AnalysisSession.video))
            .order_by(AnalysisSession.started_at.desc())
            .limit(5)
        ).all()

        # Build Section 1: System Health
        health_prov = SectionProvenanceDetail(
            state="REAL DATA",
            category="real_database_metrics",
            badge_variant="success",
            description="Live API and database connectivity telemetry",
        )

        subsystems = [
            SubsystemStatusItem(
                phase=4,
                name="Video Ingestion",
                status="available",
                provenance_type="real_pipeline",
                note="Container format validation, magic byte check, frame sampler",
            ),
            SubsystemStatusItem(
                phase=5,
                name="YOLO Vehicle Detection",
                status="available",
                provenance_type="yolov8n",
                note="Ultralytics YOLOv8n CPU detector (car, bus, truck, motorcycle, bicycle)",
            ),
            SubsystemStatusItem(
                phase=6,
                name="Object Tracking",
                status="available",
                provenance_type="bytetrack",
                note="ByteTrack Kalman 8-state bounding box association",
            ),
            SubsystemStatusItem(
                phase=7,
                name="Vehicle Counting",
                status="available",
                provenance_type="line_crossing",
                note="2D virtual tripwire cross-product transition testing",
            ),
            SubsystemStatusItem(
                phase=8,
                name="Traffic Analytics",
                status="available",
                provenance_type="flow_metrics",
                note="Volume, flow rate per min/hr, and non-interpolated time-series",
            ),
            SubsystemStatusItem(
                phase=9,
                name="Lane & Density Analysis",
                status="available",
                provenance_type="polygon_density",
                note="Ray-casting point-in-polygon and Shoelace image-space density",
            ),
            SubsystemStatusItem(
                phase=10,
                name="Database Persistence",
                status="available" if db_connected else "unavailable",
                provenance_type="sqlite_postgresql",
                note=f"SQLAlchemy ORM + Alembic migrations ({db_latency_ms:.2f}ms query latency)",
            ),
            SubsystemStatusItem(
                phase=11,
                name="Traffic Prediction",
                status="available" if readiness.is_ready else "insufficient",
                provenance_type=readiness.data_source,
                note=readiness.message,
            ),
            SubsystemStatusItem(
                phase=12,
                name="Signal Optimization",
                status="available",
                provenance_type="simulation_only",
                note="Webster delay minimization & green split simulation engine",
            ),
            SubsystemStatusItem(
                phase=13,
                name="Emergency Corridor",
                status="available",
                provenance_type="simulation_only",
                note="Multi-intersection arterial priority progression simulator",
            ),
            SubsystemStatusItem(
                phase=15,
                name="Anomaly & Incident Detection",
                status="available",
                provenance_type="rule_based_events",
                note="Explainable statistical threshold detector (congestion, flow drop, imbalance, density spike)",
            ),
        ]

        system_health = SystemHealthSection(
            provenance=health_prov,
            backend_online=True,
            database_connected=db_connected,
            database_latency_ms=db_latency_ms,
            last_successful_session_at=active_session.completed_at if active_session else None,
            last_session_id=active_session.id if active_session else None,
            subsystems=subsystems,
        )

        # Build Section 2: Traffic Overview
        metrics = active_session.traffic_metrics if active_session else None
        obs_duration = metrics.observation_duration_seconds if metrics else 0.0
        is_extrapolated = metrics.is_extrapolated if metrics else (obs_duration > 0 and obs_duration < 3600.0)

        traffic_overview = TrafficOverviewSection(
            provenance=SectionProvenanceDetail(
                state=session_prov_state,
                category=session_prov_cat,
                badge_variant=session_prov_badge,
                description=session_prov_desc,
            ),
            active_session_id=active_session.id if active_session else None,
            video_filename=active_video.original_filename if active_video else None,
            total_sessions_count=total_sessions,
            total_videos_count=total_videos,
            total_vehicles_counted=total_counted,
            total_vehicles_detected=total_detected,
            observation_duration_seconds=obs_duration,
            flow_rate_per_minute=metrics.flow_rate_per_minute if metrics else 0.0,
            flow_rate_per_hour=metrics.flow_rate_per_hour if metrics else 0.0,
            is_extrapolated=is_extrapolated,
            extrapolation_note=(
                f"Observation duration ({obs_duration:.1f}s < 3600s); hourly flow is extrapolated, not measured"
                if is_extrapolated
                else None
            ),
            started_at=active_session.started_at if active_session else None,
        )

        # Build Section 3: Vehicle Composition
        class_dist_items: List[ClassDistributionItem] = []
        if metrics and metrics.class_distribution:
            for item in metrics.class_distribution:
                class_dist_items.append(
                    ClassDistributionItem(
                        class_name=item.get("class_name", "unknown"),
                        count=int(item.get("count", 0)),
                        percentage=float(item.get("percentage", 0.0)),
                    )
                )

        vehicle_composition = VehicleCompositionSection(
            provenance=SectionProvenanceDetail(
                state=session_prov_state if class_dist_items else "UNAVAILABLE",
                category=session_prov_cat if class_dist_items else "unavailable",
                badge_variant=session_prov_badge if class_dist_items else "neutral",
                description="Per-class vehicle breakdown from persisted counting data"
                if class_dist_items
                else "No vehicle class counts available",
            ),
            total_counted=metrics.total_volume if metrics else 0,
            class_distribution=class_dist_items,
        )

        # Build Section 4: Traffic Flow Time-Series
        time_series_items: List[TimeSeriesBucketItem] = []
        if metrics and metrics.time_series_buckets:
            for b in metrics.time_series_buckets:
                time_series_items.append(
                    TimeSeriesBucketItem(
                        bucket_index=int(b.get("bucket_index", 0)),
                        start_time_seconds=float(b.get("start_time_seconds", 0.0)),
                        end_time_seconds=float(b.get("end_time_seconds", 0.0)),
                        count=int(b.get("count", 0)),
                        flow_rate_per_minute=float(b.get("flow_rate_per_minute", 0.0)),
                    )
                )

        traffic_flow_metrics = TrafficFlowSection(
            provenance=SectionProvenanceDetail(
                state=session_prov_state if time_series_items else "UNAVAILABLE",
                category=session_prov_cat if time_series_items else "unavailable",
                badge_variant=session_prov_badge if time_series_items else "neutral",
                description="Discrete non-interpolated time-series bucketing"
                if time_series_items
                else "No time-series flow data available",
            ),
            bucket_interval_seconds=10.0,
            is_extrapolated=is_extrapolated,
            time_series_buckets=time_series_items,
        )

        # Build Section 5: Lane Density
        lane_items: List[LaneResultSummaryItem] = []
        if active_session and active_session.lane_results:
            for lr in active_session.lane_results:
                lane_items.append(
                    LaneResultSummaryItem(
                        lane_id=lr.lane_id,
                        lane_name=lr.lane_name,
                        direction_hint=lr.direction_hint,
                        unique_vehicles_count=lr.unique_vehicles_count,
                        peak_occupancy=lr.peak_occupancy,
                        average_occupancy=lr.average_occupancy,
                        image_space_density=lr.image_space_density,
                        normalized_density_score=lr.normalized_density_score,
                        polygon_area_px2=lr.polygon_area_px2,
                        vehicle_class_counts=lr.vehicle_class_counts,
                    )
                )

        lane_density = LaneDensitySection(
            provenance=SectionProvenanceDetail(
                state=session_prov_state if lane_items else "UNAVAILABLE",
                category=session_prov_cat if lane_items else "unavailable",
                badge_variant=session_prov_badge if lane_items else "neutral",
                description="Shoelace polygon ray-casting occupancy and image-space density"
                if lane_items
                else "No lane polygons evaluated for this session",
            ),
            total_lanes_analyzed=len(lane_items),
            density_unit="vehicles/px²",
            calibration_warning="Image-space density (vehicles/px²) — uncalibrated camera view, not physical veh/km².",
            lanes=lane_items,
        )

        # Build Section 6: Prediction Status
        pred_prov_state = "PREDICTION"
        if readiness.is_ready:
            pred_prov_cat = "real_observations"
            pred_prov_badge = "success"
            pred_prov_desc = f"Dataset ready: {readiness.sample_count} real observations (threshold: {readiness.threshold})"
        elif readiness.synthetic_sample_count > 0 and readiness.real_sample_count == 0:
            pred_prov_cat = "synthetic_fixture"
            pred_prov_badge = "warning"
            pred_prov_desc = f"Insufficient real data: {readiness.sample_count} of {readiness.threshold} required (pipeline test only)"
        else:
            pred_prov_cat = "real_observations_insufficient"
            pred_prov_badge = "warning"
            pred_prov_desc = f"Insufficient real data: {readiness.real_sample_count} of {readiness.threshold} required observations"

        prediction_availability = PredictionStatusSection(
            provenance=SectionProvenanceDetail(
                state=pred_prov_state,
                category=pred_prov_cat,
                badge_variant=pred_prov_badge,
                description=pred_prov_desc,
            ),
            is_ready=readiness.is_ready,
            status_code=readiness.status_code,
            real_sample_count=readiness.real_sample_count,
            synthetic_sample_count=readiness.synthetic_sample_count,
            threshold=readiness.threshold,
            readiness_message=readiness.message,
            latest_run_id=latest_prediction_run.id if latest_prediction_run else None,
            latest_model_name=latest_prediction_run.model_name if latest_prediction_run else None,
            latest_rmse=latest_prediction_run.rmse if latest_prediction_run else None,
            latest_mae=latest_prediction_run.mae if latest_prediction_run else None,
            latest_r2=latest_prediction_run.r2_score if latest_prediction_run else None,
            latest_horizon_minutes=latest_prediction_run.horizon_minutes if latest_prediction_run else None,
            latest_created_at=latest_prediction_run.created_at if latest_prediction_run else None,
        )

        # Build Section 7: Signal Optimization Results
        if latest_signal_run:
            sig_prov = SectionProvenanceDetail(
                state="SIMULATION",
                category="simulation_configured",
                badge_variant="primary",
                description=f"Phase 12 decision-support simulation ({latest_signal_run.intersection_name})",
            )
            signal_optimization = SignalOptimizationSection(
                provenance=sig_prov,
                disclaimer="Simulation / Decision Support — not connected to physical signals.",
                latest_run_id=latest_signal_run.id,
                intersection_name=latest_signal_run.intersection_name,
                intersection_type=latest_signal_run.intersection_type,
                algorithm_used=latest_signal_run.algorithm_used,
                baseline_cycle_length=latest_signal_run.baseline_cycle_length,
                optimized_cycle_length=latest_signal_run.optimized_cycle_length,
                baseline_delay_proxy=latest_signal_run.baseline_delay_proxy,
                optimized_delay_proxy=latest_signal_run.optimized_delay_proxy,
                delay_reduction_pct=latest_signal_run.delay_reduction_pct,
                queue_reduction_pct=latest_signal_run.queue_reduction_pct,
                throughput_increase_pct=latest_signal_run.throughput_increase_pct,
                created_at=latest_signal_run.created_at,
            )
        else:
            signal_optimization = SignalOptimizationSection(
                provenance=SectionProvenanceDetail(
                    state="UNAVAILABLE",
                    category="unavailable",
                    badge_variant="neutral",
                    description="No signal optimization simulation runs recorded",
                ),
                disclaimer="Simulation / Decision Support — not connected to physical signals.",
            )

        # Build Section 8: Emergency Corridor Results
        if latest_corridor_run:
            ec_prov = SectionProvenanceDetail(
                state="SIMULATION",
                category="simulation_configured",
                badge_variant="primary",
                description=f"Phase 13 arterial priority progression simulation ({latest_corridor_run.corridor_name})",
            )
            emergency_corridor = EmergencyCorridorSection(
                provenance=ec_prov,
                disclaimer="Simulation / Decision Support — not a real dispatch or control system.",
                latest_run_id=latest_corridor_run.id,
                corridor_name=latest_corridor_run.corridor_name,
                corridor_nodes_count=latest_corridor_run.corridor_nodes_count,
                vehicle_type=latest_corridor_run.vehicle_type,
                priority_strategy=latest_corridor_run.priority_strategy,
                baseline_travel_time_seconds=latest_corridor_run.baseline_travel_time_seconds,
                priority_travel_time_seconds=latest_corridor_run.priority_travel_time_seconds,
                travel_time_savings_seconds=latest_corridor_run.travel_time_savings_seconds,
                travel_time_savings_pct=latest_corridor_run.travel_time_savings_pct,
                emergency_delay_reduction_pct=latest_corridor_run.emergency_delay_reduction_pct,
                cross_street_delay_impact_pct=latest_corridor_run.priority_cross_street_delay_avg,
                created_at=latest_corridor_run.created_at,
            )
        else:
            emergency_corridor = EmergencyCorridorSection(
                provenance=SectionProvenanceDetail(
                    state="UNAVAILABLE",
                    category="unavailable",
                    badge_variant="neutral",
                    description="No emergency corridor simulation runs recorded",
                ),
                disclaimer="Simulation / Decision Support — not a real dispatch or control system.",
            )

        # Build Section 9: Recent History
        history_items: List[HistorySessionSummaryItem] = []
        for s in recent_sessions_raw:
            v = s.video
            history_items.append(
                HistorySessionSummaryItem(
                    id=s.id,
                    video_id=s.video_id,
                    original_filename=v.original_filename if v else "unknown",
                    source_type=v.source_type if v else "unknown",
                    provenance_verified=v.provenance_verified if v else False,
                    total_vehicles_counted=s.total_vehicles_counted,
                    started_at=s.started_at,
                    status=s.status,
                    processing_time_ms=s.processing_time_ms,
                )
            )

        recent_history = RecentHistorySection(
            provenance=SectionProvenanceDetail(
                state="REAL DATA" if history_items else "UNAVAILABLE",
                category="real_database_metrics" if history_items else "unavailable",
                badge_variant="success" if history_items else "neutral",
                description="Recent persisted video analysis sessions from database",
            ),
            total_sessions_count=total_sessions,
            sessions=history_items,
        )

        # Build Section 10: Data Provenance Transparency Panel
        data_provenance = DataProvenanceSection(
            provenance=SectionProvenanceDetail(
                state=session_prov_state,
                category=session_prov_cat,
                badge_variant=session_prov_badge,
                description=session_prov_desc,
            ),
            active_session_id=active_session.id if active_session else None,
            video_id=active_video.id if active_video else None,
            video_filename=active_video.original_filename if active_video else None,
            source_type=active_video.source_type if active_video else "unknown",
            provenance_verified=active_video.provenance_verified if active_video else False,
            source_reference=active_video.source_reference if active_video else None,
            license_reference=active_video.license_reference if active_video else None,
            provenance_note=active_video.provenance_note if active_video else None,
            captured_at=active_video.captured_at if active_video else None,
            uploaded_at=active_video.uploaded_at if active_video else None,
        )

        total_exec_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

        return DashboardSummaryResponse(
            timestamp=now,
            execution_time_ms=total_exec_ms,
            system_health=system_health,
            traffic_overview=traffic_overview,
            vehicle_composition=vehicle_composition,
            traffic_flow_metrics=traffic_flow_metrics,
            lane_density=lane_density,
            prediction_availability=prediction_availability,
            signal_optimization=signal_optimization,
            emergency_corridor=emergency_corridor,
            recent_history=recent_history,
            data_provenance=data_provenance,
        )
