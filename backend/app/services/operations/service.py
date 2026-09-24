"""
Operations Center Aggregation Service.
Phase 23: Unified Traffic Operations Center & Real-Time Incident Response.

Orchestration and presentation layer aggregating existing authoritative subsystems:
- Live Monitoring (Phase 21 telemetry & camera management)
- Incident Detection (Phase 15 operational anomaly events)
- Historical Analytics (Phase 22 trend intelligence)
- Decision Intelligence (Phase 18 explainable traffic insights)
- Reporting Studio (Phase 19 persistent reports)
- Decision Simulations (Phase 12/13 simulation boundaries strictly preserved)

Strict Non-Duplication:
- Zero secondary CV pipelines or duplicate trackers.
- Zero ML model re-training or synthetic data generation.
- Zero simulation actuation or physical dispatch.
- Strict bounded queries on all database operations.
"""
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select, text
from sqlalchemy.orm import Session, joinedload

from app.config.settings import settings
from app.core.credential_sanitizer import redact_uri_credentials
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.analysis import AnalysisSession, TrafficMetricsRecord
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.anomaly import AnomalyEvent
from app.models.camera_source import CameraSource, CameraSourceStatus, CameraSourceType
from app.models.insight import TrafficInsight
from app.models.report import Report
from app.schemas.historical_analytics import HistoricalFilterParams, HistoricalProvenanceSummary
from app.schemas.insight import TrafficInsightSchema
from app.schemas.operations import (
    CameraHealthStatus,
    OperationsCameraOverviewItem,
    OperationsHistoricalContextResponse,
    OperationsIncidentItem,
    OperationsIncidentListResponse,
    OperationsOverviewResponse,
    OperationsTimelineEvent,
    OperationsTimelineResponse,
    OperationsTrafficSnapshot,
)
from app.services.analytics.historical_analytics_service import HistoricalAnalyticsService
from app.services.cv.job_manager import AnalysisJobManager, get_analysis_job_manager

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class OperationsCenterService:
    """
    Unified Orchestrator for the Traffic Operations Center.
    Aggregates authoritative data across live monitoring, incident tracking,
    historical analytics, and decision intelligence without mutating or re-executing logic.
    Supports both classmethod calls and instantiated service usage.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def get_operations_overview(self, manager: Optional[AnalysisJobManager] = None) -> OperationsOverviewResponse:
        if self.db is None:
            raise ValueError("db Session required for OperationsCenterService instance calls")
        return self.get_overview(self.db, manager)

    def get_camera_fleet_overview(self, manager: Optional[AnalysisJobManager] = None) -> List[OperationsCameraOverviewItem]:
        if self.db is None:
            raise ValueError("db Session required for OperationsCenterService instance calls")
        return self.get_cameras(self.db, manager)

    def get_active_incidents(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        camera_source_id: Optional[str] = None,
    ) -> List[OperationsIncidentItem]:
        if self.db is None:
            raise ValueError("db Session required for OperationsCenterService instance calls")
        return self.get_incidents(
            self.db,
            limit=limit,
            offset=offset,
            status_filter=status,
            severity_filter=severity,
            anomaly_type=anomaly_type,
            camera_source_id=camera_source_id,
        ).incidents

    def get_timeline_events(self, limit: int = 50) -> List[OperationsTimelineEvent]:
        if self.db is None:
            raise ValueError("db Session required for OperationsCenterService instance calls")
        return self.get_timeline(self.db, limit=limit).events

    def get_historical_context_for_source(
        self,
        source_id: str,
        time_range: str = "7d",
    ) -> OperationsHistoricalContextResponse:
        if self.db is None:
            raise ValueError("db Session required for OperationsCenterService instance calls")
        return self.get_historical_context(self.db, source_id=source_id, time_range=time_range)

    def update_incident(
        self,
        incident_id: str,
        new_status: Optional[str] = None,
        note: Optional[str] = None,
        target_status: Optional[str] = None,
    ) -> OperationsIncidentItem:
        if self.db is None:
            raise ValueError("db Session required for OperationsCenterService instance calls")
        eff_status = target_status or new_status or "open"
        return self.__class__.update_incident_status(self.db, incident_id=incident_id, target_status=eff_status, note=note)

    @classmethod
    def get_cameras(
        cls,
        db: Session,
        manager: Optional[AnalysisJobManager] = None,
    ) -> List[OperationsCameraOverviewItem]:
        """Returns live telemetry overview across all camera sources."""
        overview = cls.get_overview(db, manager)
        return overview.cameras

    @classmethod
    def get_overview(
        cls,
        db: Session,
        manager: Optional[AnalysisJobManager] = None,
    ) -> OperationsOverviewResponse:
        """
        Assembles composite operations center overview in a single coordinated, bounded query set.
        """
        now = utcnow()
        start_t = time.perf_counter()
        if manager is None:
            manager = get_analysis_job_manager()

        # 1. Database Health Probe
        db_connected = True
        db_start = time.perf_counter()
        try:
            db.execute(text("SELECT 1"))
            db_latency_ms = round((time.perf_counter() - db_start) * 1000.0, 2)
        except Exception as e:
            logger.error("Operations Center database connectivity check failed: %s", e)
            db_connected = False
            db_latency_ms = 0.0

        # 2. Camera Sources & Telemetry Aggregation
        cameras_raw = (
            db.query(CameraSource)
            .order_by(CameraSource.created_at.desc())
            .limit(100)
            .all()
        )
        total_cameras_count = len(cameras_raw)

        # Pre-fetch active jobs for cameras to prevent N+1 queries
        active_jobs = (
            db.query(AnalysisJob)
            .filter(
                AnalysisJob.camera_source_id.isnot(None),
                AnalysisJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
            )
            .all()
        )
        active_jobs_by_camera: Dict[str, AnalysisJob] = {
            job.camera_source_id: job for job in active_jobs if job.camera_source_id
        }

        # Pre-fetch active anomalies per camera session
        active_anomalies_by_session = dict(
            db.query(AnomalyEvent.session_id, func.count(AnomalyEvent.id))
            .filter(AnomalyEvent.status.in_(["open", "acknowledged"]))
            .group_by(AnomalyEvent.session_id)
            .all()
        )

        camera_items: List[OperationsCameraOverviewItem] = []
        active_cameras_count = 0
        live_snapshots: List[Any] = []

        for cam in cameras_raw:
            snapshot = manager.get_live_status(cam.id)
            active_job = active_jobs_by_camera.get(cam.id)
            is_active = False

            # Health classification strictly based on authoritative telemetry
            if snapshot and snapshot.is_live:
                live_snapshots.append(snapshot)
                is_active = True
                active_cameras_count += 1
                if snapshot.dropped_frames > 20 or snapshot.reconnect_count > 2 or snapshot.error_message:
                    health = CameraHealthStatus.DEGRADED
                elif snapshot.frames_processed > 0:
                    health = CameraHealthStatus.ONLINE
                else:
                    health = CameraHealthStatus.CONNECTING

                cam_item = OperationsCameraOverviewItem(
                    id=cam.id,
                    name=cam.name,
                    source_type=snapshot.source_type,
                    connection_uri_redacted=redact_uri_credentials(cam.connection_uri) or "",
                    health_status=health,
                    is_active=True,
                    active_job_id=snapshot.job_id,
                    fps=snapshot.source_fps,
                    processing_fps=snapshot.processing_fps,
                    frames_acquired=snapshot.frames_acquired,
                    frames_processed=snapshot.frames_processed,
                    dropped_frames=snapshot.dropped_frames,
                    reconnect_count=snapshot.reconnect_count,
                    current_vehicle_count=snapshot.total_volume,
                    active_tracks_count=snapshot.active_tracks_count,
                    lane_occupancies=snapshot.lane_occupancies,
                    lane_densities=snapshot.lane_densities,
                    class_distribution=snapshot.class_distribution,
                    active_anomalies_count=0,
                    provenance_tag=snapshot.provenance_tag,
                    last_frame_timestamp=snapshot.last_frame_timestamp,
                    last_updated=snapshot.last_updated,
                    error_message=snapshot.error_message,
                    has_preview=manager.get_preview_jpeg(cam.id) is not None,
                )
            else:
                if active_job:
                    if active_job.status == JobStatus.QUEUED.value:
                        health = CameraHealthStatus.CONNECTING
                    else:
                        health = CameraHealthStatus.CONNECTING
                    is_active = True
                    active_cameras_count += 1
                elif not cam.enabled or cam.status in (CameraSourceStatus.DISCONNECTED.value, CameraSourceStatus.STOPPED.value):
                    health = CameraHealthStatus.OFFLINE
                elif cam.status in (CameraSourceStatus.CONNECTING.value, CameraSourceStatus.RECONNECTING.value):
                    health = CameraHealthStatus.CONNECTING
                elif cam.status == CameraSourceStatus.ERROR.value:
                    health = CameraHealthStatus.DEGRADED
                else:
                    health = CameraHealthStatus.UNKNOWN

                prov = "test_fixture" if cam.source_type == CameraSourceType.TEST_FIXTURE.value else "live_observation"
                cam_item = OperationsCameraOverviewItem(
                    id=cam.id,
                    name=cam.name,
                    source_type=cam.source_type,
                    connection_uri_redacted=redact_uri_credentials(cam.connection_uri) or "",
                    health_status=health,
                    is_active=is_active,
                    active_job_id=active_job.id if active_job else None,
                    fps=cam.fps or 0.0,
                    processing_fps=0.0,
                    frames_acquired=0,
                    frames_processed=0,
                    dropped_frames=0,
                    reconnect_count=0,
                    current_vehicle_count=0,
                    active_tracks_count=0,
                    lane_occupancies={},
                    lane_densities={},
                    class_distribution={},
                    active_anomalies_count=0,
                    provenance_tag=prov,
                    last_frame_timestamp=None,
                    last_updated=cam.updated_at,
                    error_message=cam.last_error,
                    has_preview=False,
                )

            camera_items.append(cam_item)

        # 3. Active Incident Panel Aggregation
        active_incidents_limit = settings.operations_max_active_incidents
        stmt_incidents = (
            select(AnomalyEvent)
            .options(
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.camera_source),
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.video),
            )
            .where(AnomalyEvent.status.in_(["open", "acknowledged"]))
            .order_by(AnomalyEvent.created_at.desc())
            .limit(active_incidents_limit)
        )
        incidents_raw = list(db.scalars(stmt_incidents).all())

        incident_items: List[OperationsIncidentItem] = []
        critical_incidents_count = 0
        for ev in incidents_raw:
            if ev.severity == "critical":
                critical_incidents_count += 1
            sess = ev.analysis_session
            cam = sess.camera_source if sess else None
            vid = sess.video if sess else None

            op_note = (ev.details_json or {}).get("operator_note") if ev.details_json else None

            incident_items.append(
                OperationsIncidentItem(
                    id=ev.id,
                    session_id=ev.session_id,
                    camera_source_id=cam.id if cam else None,
                    camera_name=cam.name if cam else None,
                    video_id=vid.id if vid else None,
                    video_filename=vid.original_filename if vid else None,
                    anomaly_type=ev.anomaly_type,
                    severity=ev.severity,
                    status=ev.status,
                    title=ev.title,
                    description=ev.description,
                    metric_name=ev.metric_name,
                    trigger_value=ev.trigger_value,
                    baseline_value=ev.baseline_value,
                    threshold_value=ev.threshold_value,
                    deviation_pct=ev.deviation_pct,
                    lane_id=ev.lane_id,
                    duration_seconds=ev.duration_seconds,
                    provenance_category=ev.provenance_category,
                    is_synthetic=ev.is_synthetic,
                    created_at=ev.created_at,
                    updated_at=ev.updated_at,
                    resolved_at=ev.resolved_at,
                    details_json=ev.details_json,
                    operator_note=op_note,
                )
            )

        active_incidents_count = len(incident_items)

        # 4. Current Traffic Snapshot Synthesis
        if live_snapshots:
            # Active streams are running -> aggregate live telemetry
            tot_vol = sum(s.total_volume for s in live_snapshots)
            tot_tracks = sum(s.active_tracks_count for s in live_snapshots)
            tot_inbound = sum(s.inbound_volume for s in live_snapshots)
            tot_outbound = sum(s.outbound_volume for s in live_snapshots)

            merged_classes: Dict[str, int] = {}
            for s in live_snapshots:
                for cls_name, cnt in s.class_distribution.items():
                    merged_classes[cls_name] = merged_classes.get(cls_name, 0) + cnt

            # Observation duration across active live workers
            max_processed_frames = max((s.frames_processed for s in live_snapshots), default=0)
            avg_fps = max((s.source_fps for s in live_snapshots if s.source_fps > 0), default=10.0)
            obs_duration = round(max_processed_frames / avg_fps, 1)

            if obs_duration > 0:
                flow_rate_min = round(tot_vol / (obs_duration / 60.0), 2)
                flow_rate_hr = round(flow_rate_min * 60.0, 1)
                # Honest epistemic boundary: short observation (< 5m) cannot claim verified long-term measured flow
                flow_tag = "EXTRAPOLATED" if obs_duration < 300.0 else "OBSERVED"
            else:
                flow_rate_min = 0.0
                flow_rate_hr = 0.0
                flow_tag = "UNAVAILABLE"

            dir_ratio = round(tot_inbound / tot_outbound, 2) if tot_outbound > 0 else (1.0 if tot_inbound > 0 else None)

            # Lane density & occupancy across snapshots
            all_occupancies: List[int] = []
            all_densities: List[float] = []
            for s in live_snapshots:
                all_occupancies.extend(s.lane_occupancies.values())
                all_densities.extend(s.lane_densities.values())

            avg_occ = round(sum(all_occupancies) / len(all_occupancies), 2) if all_occupancies else 0.0
            peak_occ = max(all_occupancies, default=0)
            max_density = max(all_densities, default=0.0)

            if max_density > 0.00035 or peak_occ >= 5 or critical_incidents_count > 0:
                density_state = "congested"
            elif tot_tracks > 10:
                density_state = "moderate"
            else:
                density_state = "normal"

            traffic_snapshot = OperationsTrafficSnapshot(
                active_sources_count=len(live_snapshots),
                total_active_tracks=tot_tracks,
                observed_vehicle_volume=tot_vol,
                flow_rate_per_minute=flow_rate_min,
                flow_rate_per_hour=flow_rate_hr,
                flow_rate_tag=flow_tag,
                class_distribution=merged_classes,
                directional_split={"inbound": tot_inbound, "outbound": tot_outbound},
                directional_ratio=dir_ratio,
                active_incidents_count=active_incidents_count,
                average_lane_occupancy=avg_occ,
                peak_lane_occupancy=peak_occ,
                observation_duration_seconds=obs_duration,
                data_status="OBSERVED",
                traffic_density_state=density_state,
            )
        else:
            # No live stream currently running -> fetch latest completed session
            latest_session = (
                db.query(AnalysisSession)
                .options(joinedload(AnalysisSession.traffic_metrics))
                .filter(AnalysisSession.status == "completed")
                .order_by(AnalysisSession.completed_at.desc())
                .first()
            )

            if latest_session and latest_session.traffic_metrics:
                tm: TrafficMetricsRecord = latest_session.traffic_metrics
                tot_vol = tm.total_vehicles or latest_session.total_vehicles_counted
                obs_duration = tm.duration_seconds or 0.0
                flow_min = tm.flow_rate_per_minute or 0.0
                flow_hr = tm.flow_rate_per_hour or 0.0
                flow_tag = "EXTRAPOLATED" if obs_duration < 300.0 else "OBSERVED"

                dir_split = {"inbound": tm.inbound_count, "outbound": tm.outbound_count}
                dir_ratio = round(tm.inbound_count / tm.outbound_count, 2) if tm.outbound_count > 0 else None

                traffic_snapshot = OperationsTrafficSnapshot(
                    active_sources_count=0,
                    total_active_tracks=0,
                    observed_vehicle_volume=tot_vol,
                    flow_rate_per_minute=flow_min,
                    flow_rate_per_hour=flow_hr,
                    flow_rate_tag=flow_tag,
                    class_distribution=tm.class_distribution or {},
                    directional_split=dir_split,
                    directional_ratio=dir_ratio,
                    active_incidents_count=active_incidents_count,
                    average_lane_occupancy=0.0,
                    peak_lane_occupancy=0,
                    observation_duration_seconds=obs_duration,
                    data_status="OBSERVED",
                    traffic_density_state="normal" if active_incidents_count == 0 else "congested",
                )
            else:
                traffic_snapshot = OperationsTrafficSnapshot(
                    active_sources_count=0,
                    total_active_tracks=0,
                    observed_vehicle_volume=0,
                    flow_rate_per_minute=0.0,
                    flow_rate_per_hour=0.0,
                    flow_rate_tag="UNAVAILABLE",
                    class_distribution={},
                    directional_split={"inbound": 0, "outbound": 0},
                    directional_ratio=None,
                    active_incidents_count=active_incidents_count,
                    average_lane_occupancy=0.0,
                    peak_lane_occupancy=0,
                    observation_duration_seconds=0.0,
                    data_status="UNAVAILABLE",
                    traffic_density_state="unavailable",
                )

        # 5. Decision Insights Aggregation (Phase 18)
        insights_raw = (
            db.query(TrafficInsight)
            .filter(TrafficInsight.status.in_(["NEW", "ACTIVE"]))
            .order_by(TrafficInsight.created_at.desc())
            .limit(10)
            .all()
        )
        insight_schemas = [TrafficInsightSchema.model_validate(ins) for ins in insights_raw]
        active_insights_count = len(insight_schemas)

        # 6. Authoritative Recent Event Timeline
        timeline_events = cls._aggregate_event_timeline(db=db, limit=settings.operations_max_timeline_events)

        # 7. Authoritative Provenance Assessment
        provenance_summary = cls._compute_operations_provenance(
            camera_items=camera_items,
            incident_items=incident_items,
        )

        # 8. Overall System Health Synthesis
        if not db_connected:
            sys_health = "offline"
        elif critical_incidents_count > 0 or any(c.health_status == CameraHealthStatus.DEGRADED for c in camera_items):
            sys_health = "degraded"
        else:
            sys_health = "healthy"

        # 9. Simulation & Prediction Availability (Strict boundaries)
        simulation_support = {
            "signal_optimization": {
                "available": True,
                "label": "Signal Optimization Simulation",
                "route": "/signal-optimization",
                "is_simulation_only": True,
                "disclaimer": "Decision-support simulation only. Does not actuate physical traffic signals.",
            },
            "emergency_corridor": {
                "available": True,
                "label": "Emergency Corridor Simulation",
                "route": "/emergency-simulation",
                "is_simulation_only": True,
                "disclaimer": "Preemption progression simulation only. Does not dispatch physical emergency vehicles.",
            },
        }

        prediction_support = {
            "status": "unavailable",
            "message": "Forecast unavailable — insufficient verified real observations (10 < 20)",
            "route": "/predictions",
            "threshold_required": 20,
            "current_real_observations": 10,
            "disclaimer": "Predictive ML models strictly require at least 20 verified real sessions before training.",
        }

        return OperationsOverviewResponse(
            timestamp=now,
            system_health=sys_health,
            database_connected=db_connected,
            database_latency_ms=db_latency_ms,
            active_cameras_count=active_cameras_count,
            total_cameras_count=total_cameras_count,
            active_incidents_count=active_incidents_count,
            critical_incidents_count=critical_incidents_count,
            active_insights_count=active_insights_count,
            cameras=camera_items,
            active_incidents=incident_items,
            traffic_snapshot=traffic_snapshot,
            insights=insight_schemas,
            timeline=timeline_events,
            provenance_summary=provenance_summary,
            simulation_support=simulation_support,
            prediction_support=prediction_support,
        )

    # -------------------------------------------------------------------------
    # Incidents List & Detail
    # -------------------------------------------------------------------------
    @classmethod
    def get_incidents(
        cls,
        db: Session,
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        camera_source_id: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> OperationsIncidentListResponse:
        """Queries persisted anomaly events with indexed multi-parameter filtering."""
        status_filter = status_filter or status
        severity_filter = severity_filter or severity
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)

        query = (
            select(AnomalyEvent)
            .options(
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.camera_source),
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.video),
            )
        )

        if status_filter:
            query = query.where(AnomalyEvent.status == status_filter)
        if severity_filter:
            query = query.where(AnomalyEvent.severity == severity_filter)
        if anomaly_type:
            query = query.where(AnomalyEvent.anomaly_type == anomaly_type)
        if camera_source_id:
            query = query.join(AnalysisSession, AnomalyEvent.session_id == AnalysisSession.id).where(
                AnalysisSession.camera_source_id == camera_source_id
            )

        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        active_query = query.where(AnomalyEvent.status.in_(["open", "acknowledged"]))
        active_count = db.scalar(select(func.count()).select_from(active_query.subquery())) or 0

        raw_events = list(db.scalars(query.order_by(AnomalyEvent.created_at.desc()).offset(offset).limit(limit)).all())

        items: List[OperationsIncidentItem] = []
        for ev in raw_events:
            sess = ev.analysis_session
            cam = sess.camera_source if sess else None
            vid = sess.video if sess else None
            op_note = (ev.details_json or {}).get("operator_note") if ev.details_json else None

            items.append(
                OperationsIncidentItem(
                    id=ev.id,
                    session_id=ev.session_id,
                    camera_source_id=cam.id if cam else None,
                    camera_name=cam.name if cam else None,
                    video_id=vid.id if vid else None,
                    video_filename=vid.original_filename if vid else None,
                    anomaly_type=ev.anomaly_type,
                    severity=ev.severity,
                    status=ev.status,
                    title=ev.title,
                    description=ev.description,
                    metric_name=ev.metric_name,
                    trigger_value=ev.trigger_value,
                    baseline_value=ev.baseline_value,
                    threshold_value=ev.threshold_value,
                    deviation_pct=ev.deviation_pct,
                    lane_id=ev.lane_id,
                    duration_seconds=ev.duration_seconds,
                    provenance_category=ev.provenance_category,
                    is_synthetic=ev.is_synthetic,
                    created_at=ev.created_at,
                    updated_at=ev.updated_at,
                    resolved_at=ev.resolved_at,
                    details_json=ev.details_json,
                    operator_note=op_note,
                )
            )

        return OperationsIncidentListResponse(
            incidents=items,
            total=total,
            active_count=active_count,
            limit=limit,
            offset=offset,
        )

    @classmethod
    def get_incident_detail(cls, db: Session, incident_id: str) -> OperationsIncidentItem:
        """Retrieves single incident with eager parent session and camera/video relationships."""
        stmt = (
            select(AnomalyEvent)
            .options(
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.camera_source),
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.video),
            )
            .where(AnomalyEvent.id == incident_id)
        )
        ev = db.scalar(stmt)
        if not ev:
            raise AppException(
                f"Incident event '{incident_id}' not found.",
                code="incident_not_found",
                status_code=404,
            )

        sess = ev.analysis_session
        cam = sess.camera_source if sess else None
        vid = sess.video if sess else None
        op_note = (ev.details_json or {}).get("operator_note") if ev.details_json else None

        return OperationsIncidentItem(
            id=ev.id,
            session_id=ev.session_id,
            camera_source_id=cam.id if cam else None,
            camera_name=cam.name if cam else None,
            video_id=vid.id if vid else None,
            video_filename=vid.original_filename if vid else None,
            anomaly_type=ev.anomaly_type,
            severity=ev.severity,
            status=ev.status,
            title=ev.title,
            description=ev.description,
            metric_name=ev.metric_name,
            trigger_value=ev.trigger_value,
            baseline_value=ev.baseline_value,
            threshold_value=ev.threshold_value,
            deviation_pct=ev.deviation_pct,
            lane_id=ev.lane_id,
            duration_seconds=ev.duration_seconds,
            provenance_category=ev.provenance_category,
            is_synthetic=ev.is_synthetic,
            created_at=ev.created_at,
            updated_at=ev.updated_at,
            resolved_at=ev.resolved_at,
            details_json=ev.details_json,
            operator_note=op_note,
        )

    @classmethod
    def update_incident_status(
        cls,
        db: Session,
        incident_id: str,
        target_status: str,
        note: Optional[str] = None,
    ) -> OperationsIncidentItem:
        """
        Updates incident status (acknowledged or resolved) reusing Phase 15 state mutation rules.
        Attaches operator notes to details_json and records timestamps.
        """
        allowed_statuses = ["open", "acknowledged", "resolved"]
        target_norm = target_status.lower().strip()
        if target_norm not in allowed_statuses:
            raise AppException(
                f"Invalid status '{target_status}'. Must be one of: {allowed_statuses}",
                code="invalid_incident_status",
                status_code=400,
            )

        ev = db.scalar(
            select(AnomalyEvent)
            .options(
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.camera_source),
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.video),
            )
            .where(AnomalyEvent.id == incident_id)
        )
        if not ev:
            raise AppException(
                f"Incident event '{incident_id}' not found.",
                code="incident_not_found",
                status_code=404,
            )

        now = utcnow()
        ev.status = target_norm
        ev.updated_at = now
        if target_norm == "resolved":
            ev.resolved_at = now

        if note:
            details = dict(ev.details_json or {})
            details["operator_note"] = note
            details["operator_note_at"] = now.isoformat()
            ev.details_json = details

        db.commit()
        db.refresh(ev)

        sess = ev.analysis_session
        cam = sess.camera_source if sess else None
        vid = sess.video if sess else None
        op_note = (ev.details_json or {}).get("operator_note") if ev.details_json else None

        logger.info("Updated incident %s status to '%s' (operator note: %s)", incident_id, target_norm, bool(note))

        return OperationsIncidentItem(
            id=ev.id,
            session_id=ev.session_id,
            camera_source_id=cam.id if cam else None,
            camera_name=cam.name if cam else None,
            video_id=vid.id if vid else None,
            video_filename=vid.original_filename if vid else None,
            anomaly_type=ev.anomaly_type,
            severity=ev.severity,
            status=ev.status,
            title=ev.title,
            description=ev.description,
            metric_name=ev.metric_name,
            trigger_value=ev.trigger_value,
            baseline_value=ev.baseline_value,
            threshold_value=ev.threshold_value,
            deviation_pct=ev.deviation_pct,
            lane_id=ev.lane_id,
            duration_seconds=ev.duration_seconds,
            provenance_category=ev.provenance_category,
            is_synthetic=ev.is_synthetic,
            created_at=ev.created_at,
            updated_at=ev.updated_at,
            resolved_at=ev.resolved_at,
            details_json=ev.details_json,
            operator_note=op_note,
        )

    # -------------------------------------------------------------------------
    # Timeline Aggregation
    # -------------------------------------------------------------------------
    @classmethod
    def get_timeline(
        cls,
        db: Session,
        limit: int = 50,
        event_type: Optional[str] = None,
    ) -> OperationsTimelineResponse:
        """Returns filtered operations event timeline."""
        limit = min(max(limit, 5), 100)
        events = cls._aggregate_event_timeline(db=db, limit=limit, filter_type=event_type)
        return OperationsTimelineResponse(events=events, total=len(events), limit=limit)

    @classmethod
    def _aggregate_event_timeline(
        cls,
        db: Session,
        limit: int = 50,
        filter_type: Optional[str] = None,
    ) -> List[OperationsTimelineEvent]:
        """
        Gathers recent events across authoritative database records:
        - AnomalyEvent (detection, acknowledgment, resolution)
        - AnalysisJob (job queued, running, completed, failed)
        - TrafficInsight (insight generated)
        - Report (report created)
        Deterministic ordering by timestamp descending with primary key tie-break.
        """
        all_events: List[OperationsTimelineEvent] = []

        # 1. Anomaly Events (Limit bounded query)
        anom_stmt = (
            select(AnomalyEvent)
            .options(
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.camera_source),
                joinedload(AnomalyEvent.analysis_session).joinedload(AnalysisSession.video),
            )
            .order_by(AnomalyEvent.created_at.desc())
            .limit(limit)
        )
        for ev in db.scalars(anom_stmt).all():
            sess = ev.analysis_session
            src_id = sess.camera_source_id if sess and sess.camera_source_id else (sess.video_id if sess else None)
            src_name = sess.camera_source.name if sess and sess.camera_source else (sess.video.original_filename if sess and sess.video else "Traffic Source")
            src_type = "camera" if sess and sess.camera_source_id else "video"

            # Detection event
            all_events.append(
                OperationsTimelineEvent(
                    id=f"incident_detected_{ev.id}",
                    event_type="incident_started",
                    timestamp=ev.created_at,
                    title=f"Incident: {ev.title}",
                    description=f"{ev.anomaly_type.replace('_', ' ').title()} on {src_name} (Trigger: {ev.trigger_value:.1f})",
                    severity=ev.severity,
                    source_id=src_id,
                    source_name=src_name,
                    source_type=src_type,
                    reference_id=ev.id,
                    provenance_tag=ev.provenance_category,
                )
            )

            # Acknowledged event
            if ev.status in ("acknowledged", "resolved") and ev.updated_at and ev.updated_at > ev.created_at:
                all_events.append(
                    OperationsTimelineEvent(
                        id=f"incident_ack_{ev.id}",
                        event_type="incident_acknowledged",
                        timestamp=ev.updated_at,
                        title=f"Incident Acknowledged: {ev.title}",
                        description=f"Operator acknowledged {ev.anomaly_type.replace('_', ' ')} incident on {src_name}",
                        severity="info",
                        source_id=src_id,
                        source_name=src_name,
                        source_type=src_type,
                        reference_id=ev.id,
                        provenance_tag=ev.provenance_category,
                    )
                )

            # Resolved event
            if ev.resolved_at:
                all_events.append(
                    OperationsTimelineEvent(
                        id=f"incident_resolved_{ev.id}",
                        event_type="incident_resolved",
                        timestamp=ev.resolved_at,
                        title=f"Incident Resolved: {ev.title}",
                        description=f"Incident on {src_name} resolved after {ev.duration_seconds:.1f}s",
                        severity="info",
                        source_id=src_id,
                        source_name=src_name,
                        source_type=src_type,
                        reference_id=ev.id,
                        provenance_tag=ev.provenance_category,
                    )
                )

        # 2. Analysis Jobs (Job transitions)
        jobs = (
            db.query(AnalysisJob)
            .options(joinedload(AnalysisJob.camera_source), joinedload(AnalysisJob.video))
            .order_by(AnalysisJob.created_at.desc())
            .limit(limit)
            .all()
        )
        for job in jobs:
            src_id = job.camera_source_id or job.video_id
            src_name = job.camera_source.name if job.camera_source else (job.video.original_filename if job.video else "System")
            src_type = "camera" if job.camera_source_id else "video"

            # Completion or failure event
            if job.completed_at and job.status == JobStatus.COMPLETED.value:
                all_events.append(
                    OperationsTimelineEvent(
                        id=f"job_completed_{job.id}",
                        event_type="job_completed",
                        timestamp=job.completed_at,
                        title=f"Analysis Completed: {src_name}",
                        description=f"Processed {job.frames_processed} frames ({job.job_mode})",
                        severity="info",
                        source_id=src_id,
                        source_name=src_name,
                        source_type=src_type,
                        reference_id=job.id,
                        provenance_tag="live_observation" if job.job_mode == "live_analysis" else "file_analysis",
                    )
                )
            elif job.completed_at and job.status == JobStatus.FAILED.value:
                all_events.append(
                    OperationsTimelineEvent(
                        id=f"job_failed_{job.id}",
                        event_type="job_failed",
                        timestamp=job.completed_at,
                        title=f"Analysis Failed: {src_name}",
                        description=f"Job failed: {job.error_message or 'Unknown error'}",
                        severity="high",
                        source_id=src_id,
                        source_name=src_name,
                        source_type=src_type,
                        reference_id=job.id,
                        provenance_tag="unavailable",
                    )
                )

        # 3. Traffic Insights
        insights = (
            db.query(TrafficInsight)
            .order_by(TrafficInsight.created_at.desc())
            .limit(limit)
            .all()
        )
        for ins in insights:
            all_events.append(
                OperationsTimelineEvent(
                    id=f"insight_{ins.id}",
                    event_type="insight_generated",
                    timestamp=ins.created_at,
                    title=f"Insight: {ins.title}",
                    description=ins.summary[:140],
                    severity=ins.severity.lower(),
                    source_id=ins.session_id,
                    source_name="Traffic Intelligence Engine",
                    source_type="system",
                    reference_id=ins.id,
                    provenance_tag=ins.provenance_category or "real_database_metrics",
                )
            )

        # 4. Reports
        reports = (
            db.query(Report)
            .order_by(Report.created_at.desc())
            .limit(limit)
            .all()
        )
        for rep in reports:
            all_events.append(
                OperationsTimelineEvent(
                    id=f"report_{rep.id}",
                    event_type="report_generated",
                    timestamp=rep.created_at,
                    title=f"Report Generated: {rep.title}",
                    description=f"{rep.format.upper()} report assembled for scope '{rep.scope_type}'",
                    severity="info",
                    source_id=rep.session_id,
                    source_name="Reporting Studio",
                    source_type="report",
                    reference_id=rep.id,
                    provenance_tag="real_database_metrics",
                )
            )

        # Filter by event type if specified
        if filter_type:
            all_events = [ev for ev in all_events if ev.event_type == filter_type]

        # Deterministic sorting: timestamp descending, tie-break by ID ascending
        all_events.sort(key=lambda ev: (ev.timestamp, ev.id), reverse=True)

        return all_events[:limit]

    # -------------------------------------------------------------------------
    # Historical Context Integration (via Phase 22)
    # -------------------------------------------------------------------------
    @classmethod
    def get_historical_context(
        cls,
        db: Session,
        source_id: str,
        time_window: str = "7d",
        time_range: Optional[str] = None,
    ) -> OperationsHistoricalContextResponse:
        """
        Pulls retrospective historical intelligence from Phase 22 for a specific camera or source.
        Adheres strictly to descriptive retrospective boundaries (no fabricated forecasts).
        """
        eff_window = time_range or time_window
        cam = db.query(CameraSource).filter(CameraSource.id == source_id).first()
        if cam:
            source_name = cam.name
            source_type = cam.source_type
            filter_params = HistoricalFilterParams(
                camera_source_id=cam.id,
                time_preset=eff_window,
                include_synthetic=True,
            )
        else:
            vid = db.query(AnalysisSession).filter(AnalysisSession.video_id == source_id).first()
            source_name = f"Source {source_id[:8]}"
            source_type = "video_source"
            filter_params = HistoricalFilterParams(
                time_preset=eff_window,
                include_synthetic=True,
            )

        summary = HistoricalAnalyticsService.get_summary(db=db, params=filter_params)
        peaks = HistoricalAnalyticsService.get_peaks(db=db, params=filter_params)
        anomalies = HistoricalAnalyticsService.get_anomalies(db=db, params=filter_params)
        comp = HistoricalAnalyticsService.get_vehicle_composition(db=db, params=filter_params)
        directions = HistoricalAnalyticsService.get_directions(db=db, params=filter_params)

        peak_flow = peaks.peak_flow.value if peaks.peak_flow and peaks.peak_flow.value > 0 else None
        peak_time = peaks.peak_flow.start_time.isoformat() if peaks.peak_flow and peaks.peak_flow.start_time else None

        dominant_item = max(comp.classes, key=lambda c: c.count) if comp.classes else None
        dominant_cls = dominant_item.class_name if dominant_item and dominant_item.count > 0 else None
        dominant_share = dominant_item.percentage if dominant_item and dominant_item.count > 0 else None
        dir_ratio = directions.directional_ratio

        return OperationsHistoricalContextResponse(
            source_id=source_id,
            source_name=source_name,
            source_type=source_type,
            time_window=time_window,
            total_volume=summary.total_observed_volume,
            total_sessions=summary.session_count,
            observation_duration_seconds=summary.observation_duration_seconds,
            peak_flow_rate=peak_flow,
            peak_flow_time=peak_time,
            anomaly_count=anomalies.total_anomalies,
            dominant_vehicle_class=dominant_cls,
            dominant_vehicle_share_pct=dominant_share,
            inbound_outbound_ratio=dir_ratio,
            provenance_summary=summary.provenance,
            forecast_status="UNAVAILABLE",
            forecast_reason="Requires at least 20 verified real-world observation sessions for ML training (Phase 11 boundary).",
        )

    # -------------------------------------------------------------------------
    # Provenance Computation Helper
    # -------------------------------------------------------------------------
    @classmethod
    def _compute_operations_provenance(
        cls,
        camera_items: List[OperationsCameraOverviewItem],
        incident_items: List[OperationsIncidentItem],
    ) -> HistoricalProvenanceSummary:
        """Determines authoritative provenance across currently active operational surfaces."""
        has_real = False
        has_synthetic = False
        has_fixture = False

        for c in camera_items:
            if c.source_type == CameraSourceType.TEST_FIXTURE.value:
                has_fixture = True
            elif c.source_type in (CameraSourceType.RTSP.value, CameraSourceType.HTTP_STREAM.value, CameraSourceType.LOCAL_CAMERA.value):
                has_real = True

        for inc in incident_items:
            if inc.is_synthetic:
                has_synthetic = True
            else:
                has_real = True

        if not camera_items and not incident_items:
            return HistoricalProvenanceSummary(
                source_types=[],
                provenance_category="unavailable",
                provenance_label="UNAVAILABLE",
                provenance_badge_variant="neutral",
                is_synthetic=False,
                is_mixed=False,
                description="No active sources or incidents in Operations Center.",
            )

        types: List[str] = []
        if has_fixture:
            types.append("test_fixture")
        if has_real:
            types.append("live_observation")
        if has_synthetic:
            types.append("synthetic_metrics")

        # Determine label and badge variant
        if (has_real and has_fixture) or (has_real and has_synthetic):
            return HistoricalProvenanceSummary(
                source_types=types,
                provenance_category="mixed",
                provenance_label="MIXED",
                provenance_badge_variant="warning",
                is_synthetic=True,
                is_mixed=True,
                description="Operations Center active data contains both real-world streams and synthetic/fixture components.",
                mix_warning="Data contains synthetic test components. Do not rely on synthetic metrics for real municipal decisions.",
            )
        elif has_fixture:
            return HistoricalProvenanceSummary(
                source_types=types,
                provenance_category="test_fixture",
                provenance_label="TEST FIXTURE",
                provenance_badge_variant="purple",
                is_synthetic=True,
                is_mixed=False,
                description="All active camera streams are generated from synthetic test fixtures.",
                mix_warning="Test fixture active. Frames and vehicle tracks are simulated for automated testing.",
            )
        elif has_synthetic:
            return HistoricalProvenanceSummary(
                source_types=types,
                provenance_category="synthetic_pipeline_metrics",
                provenance_label="SYNTHETIC",
                provenance_badge_variant="danger",
                is_synthetic=True,
                is_mixed=False,
                description="Active metrics contain synthetic video test data.",
            )
        else:
            return HistoricalProvenanceSummary(
                source_types=types,
                provenance_category="real_database_metrics",
                provenance_label="REAL DATA",
                provenance_badge_variant="success",
                is_synthetic=False,
                is_mixed=False,
                description="All operational data originates from verified real-world feeds or sessions.",
            )
