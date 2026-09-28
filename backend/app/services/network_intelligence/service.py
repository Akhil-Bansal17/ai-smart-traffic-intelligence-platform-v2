"""
Network Intelligence & Multi-Source Traffic Operations Analytics Service.
Phase 24: Advanced Traffic Operations Analytics & Network Intelligence.

Core Orchestration and Analytics Layer:
- Multi-source network aggregation across cameras and video feeds.
- Evidence-based hotspot detection without fabricating GPS coordinates.
- Source-by-source comparative analysis with window mismatch detection.
- Supported vehicle composition strictly adhering to YOLO classes.
- Directional balance and traffic distribution.
- Lane intelligence reusing Phase 9 / Phase 22 authoritative data.
- Cross-source temporal pattern analysis with synchronized windows.
- Reusing Phase 22 HistoricalAnalyticsService for historical period comparisons.
- Strict epistemic safety: OBSERVED, DERIVED, EXTRAPOLATED, UNAVAILABLE.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.analysis import (
    AnalysisSession,
    CrossingEventRecord,
    LaneResultRecord,
    TrafficMetricsRecord,
)
from app.models.anomaly import AnomalyEvent
from app.models.camera_source import CameraSource, CameraSourceStatus, CameraSourceType
from app.models.insight import TrafficInsight
from app.models.video import Video
from app.schemas.historical_analytics import (
    HistoricalFilterParams,
    HistoricalProvenanceSummary,
    LaneIntelligenceItem,
    PeriodComparisonResponse,
)
from app.schemas.network_intelligence import (
    NetworkDirectionalResponse,
    NetworkDirectionalSourceItem,
    NetworkDirectionalSummary,
    NetworkFilterParams,
    NetworkHotspotItem,
    NetworkHotspotResponse,
    NetworkLaneResponse,
    NetworkLaneSummary,
    NetworkOverviewResponse,
    NetworkSourceComparisonItem,
    NetworkSourceComparisonResponse,
    NetworkTemporalAnalysisResponse,
    NetworkTemporalBucket,
    NetworkTemporalBucketSourceItem,
    NetworkVehicleClassItem,
    NetworkVehicleCompositionResponse,
)
from app.services.analytics.historical_analytics_service import (
    SUPPORTED_VEHICLE_CLASSES,
    HistoricalAnalyticsService,
)

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is timezone-aware in UTC for safe comparison."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class NetworkIntelligenceService:
    """
    High-performance, query-safe service orchestrating network-wide
    traffic analytics from authoritative persisted records.
    """

    @classmethod
    def _to_historical_params(cls, params: NetworkFilterParams) -> HistoricalFilterParams:
        """Converts NetworkFilterParams to HistoricalFilterParams for service reuse."""
        return HistoricalFilterParams(
            start_time=params.start_time,
            end_time=params.end_time,
            time_preset=params.time_preset,
            camera_source_id=params.source_ids[0] if (params.source_ids and len(params.source_ids) == 1) else None,
            include_synthetic=params.include_synthetic,
            bucket_interval=params.bucket_interval or "hourly",
        )

    @classmethod
    def resolve_and_validate_window(
        cls, params: NetworkFilterParams
    ) -> Tuple[datetime, datetime]:
        """
        Resolves start/end datetimes from presets or custom bounds.
        Enforces maximum query range ceiling to prevent unbounded DB scans.
        """
        hist_params = cls._to_historical_params(params)
        start_time, end_time = HistoricalAnalyticsService.resolve_time_window(hist_params)

        # Enforce range limit
        diff_days = (end_time - start_time).total_seconds() / 86400.0
        max_days = settings.network_intelligence_max_range_days
        if diff_days > max_days:
            raise AppException(
                f"Query time window exceeds maximum limit of {max_days} days (requested: {round(diff_days, 1)} days). "
                "Please shorten your date filter.",
                status_code=422,
            )

        return start_time, end_time

    @classmethod
    def _query_sessions(
        cls,
        db: Session,
        start_time: datetime,
        end_time: datetime,
        source_ids: Optional[List[str]] = None,
        include_synthetic: bool = False,
    ) -> List[AnalysisSession]:
        """
        Executes bounded, indexed query for completed analysis sessions in the time window.
        """
        query = (
            select(AnalysisSession)
            .options(
                joinedload(AnalysisSession.traffic_metrics),
                joinedload(AnalysisSession.camera_source),
                selectinload(AnalysisSession.lane_results),
            )
            .where(
                AnalysisSession.started_at >= start_time,
                AnalysisSession.started_at <= end_time,
                AnalysisSession.status == "completed",
            )
        )

        if source_ids:
            query = query.where(AnalysisSession.camera_source_id.in_(source_ids))

        # Query bounded by 5000 sessions
        sessions = db.scalars(query.order_by(AnalysisSession.started_at.asc()).limit(5000)).all()

        if not include_synthetic:
            # Exclude sessions linked to test fixtures or mock videos
            filtered = []
            for s in sessions:
                if s.camera_source and s.camera_source.source_type == CameraSourceType.TEST_FIXTURE.value:
                    continue
                filtered.append(s)
            sessions = filtered

        return sessions

    @classmethod
    def _query_camera_sources(
        cls,
        db: Session,
        source_ids: Optional[List[str]] = None,
        include_synthetic: bool = False,
    ) -> List[CameraSource]:
        """
        Queries registered camera sources safely up to configured max limit.
        """
        query = select(CameraSource).order_by(CameraSource.name.asc())
        if source_ids:
            query = query.where(CameraSource.id.in_(source_ids))
        if not include_synthetic:
            query = query.where(CameraSource.source_type != CameraSourceType.TEST_FIXTURE.value)

        return db.scalars(query.limit(settings.network_intelligence_max_sources)).all()

    # =========================================================================
    # 1. Network Overview
    # =========================================================================
    @classmethod
    def get_network_overview(
        cls,
        db: Session,
        params: NetworkFilterParams,
    ) -> NetworkOverviewResponse:
        """
        Assembles comprehensive network-wide overview across multiple traffic sources.
        """
        start_time, end_time = cls.resolve_and_validate_window(params)
        sources = cls._query_camera_sources(db, params.source_ids, params.include_synthetic)
        sessions = cls._query_sessions(db, start_time, end_time, params.source_ids, params.include_synthetic)

        total_volume = 0
        total_duration = 0.0
        inbound_count = 0
        outbound_count = 0
        vehicle_class_counts: Dict[str, int] = {c: 0 for c in SUPPORTED_VEHICLE_CLASSES}
        active_source_ids: Set[str] = set()
        is_extrapolated = False

        # Lane tracking
        lanes_seen: Dict[str, LaneResultRecord] = {}

        for sess in sessions:
            if sess.camera_source_id:
                active_source_ids.add(sess.camera_source_id)

            metrics = sess.traffic_metrics
            if metrics:
                total_volume += metrics.total_volume
                total_duration += metrics.observation_duration_seconds
                if metrics.is_extrapolated:
                    is_extrapolated = True

                # Class breakdown
                if metrics.class_distribution and isinstance(metrics.class_distribution, list):
                    for item in metrics.class_distribution:
                        c_name = item.get("class_name")
                        c_count = item.get("count", 0)
                        if c_name in vehicle_class_counts:
                            vehicle_class_counts[c_name] += c_count

                # Direction breakdown
                if metrics.direction_distribution and isinstance(metrics.direction_distribution, list):
                    for d in metrics.direction_distribution:
                        dir_name = str(d.get("direction", "")).lower()
                        d_count = d.get("count", 0)
                        if "in" in dir_name:
                            inbound_count += d_count
                        elif "out" in dir_name:
                            outbound_count += d_count

            # Lane results
            for lane in sess.lane_results:
                if lane.lane_id not in lanes_seen or lane.unique_vehicles_count > lanes_seen[lane.lane_id].unique_vehicles_count:
                    lanes_seen[lane.lane_id] = lane

        # Calculate flow rates
        minutes = total_duration / 60.0
        hours = total_duration / 3600.0
        flow_rate_per_minute = round(total_volume / minutes, 2) if minutes > 0 else 0.0
        flow_rate_per_hour = round(total_volume / hours, 2) if hours > 0 else 0.0

        # Incidents query
        session_ids = [s.id for s in sessions]
        active_incident_count = 0
        recurring_locations_count = 0
        top_hotspot_source_name: Optional[str] = None

        if session_ids or sources:
            incident_query = select(AnomalyEvent).where(
                AnomalyEvent.status.in_(["open", "acknowledged"])
            )
            if session_ids:
                incident_query = incident_query.where(AnomalyEvent.session_id.in_(session_ids))
            active_incidents = db.scalars(incident_query).all()
            active_incident_count = len(active_incidents)

            # Check recurring locations (source with >= 2 incidents in window)
            source_inc_counts: Dict[str, int] = {}
            for inc in active_incidents:
                # Find camera source from session
                sess_match = next((s for s in sessions if s.id == inc.session_id), None)
                if sess_match and sess_match.camera_source_id:
                    sid = sess_match.camera_source_id
                    source_inc_counts[sid] = source_inc_counts.get(sid, 0) + 1

            recurring_locations_count = sum(1 for c in source_inc_counts.values() if c >= 2)

        # Vehicle class items
        vehicle_class_items: List[NetworkVehicleClassItem] = []
        for c in SUPPORTED_VEHICLE_CLASSES:
            cnt = vehicle_class_counts[c]
            pct = round((cnt / total_volume * 100.0), 1) if total_volume > 0 else 0.0
            r_hr = round(cnt / hours, 1) if hours > 0 else 0.0
            vehicle_class_items.append(
                NetworkVehicleClassItem(
                    class_name=c,
                    count=cnt,
                    percentage=pct,
                    rate_per_hour=r_hr,
                    epistemic_status="OBSERVED",
                )
            )

        # Directional summary
        dir_ratio = round(inbound_count / max(1, outbound_count), 2) if (inbound_count + outbound_count) > 0 else 1.0
        if dir_ratio >= 1.25 and (inbound_count + outbound_count) > 0:
            balance_status = "inbound_dominant"
        elif dir_ratio <= 0.80 and (inbound_count + outbound_count) > 0:
            balance_status = "outbound_dominant"
        else:
            balance_status = "balanced"

        total_dir = inbound_count + outbound_count
        directional_summary = NetworkDirectionalSummary(
            inbound_count=inbound_count,
            outbound_count=outbound_count,
            inbound_percentage=round((inbound_count / total_dir * 100.0), 1) if total_dir > 0 else 0.0,
            outbound_percentage=round((outbound_count / total_dir * 100.0), 1) if total_dir > 0 else 0.0,
            directional_ratio=dir_ratio,
            balance_status=balance_status,
            epistemic_status="OBSERVED" if total_dir > 0 else "UNAVAILABLE",
        )

        # Lane summary
        sources_with_lanes = set()
        for sess in sessions:
            if sess.lane_results and sess.camera_source_id:
                sources_with_lanes.add(sess.camera_source_id)

        if lanes_seen:
            busiest_lane = max(lanes_seen.values(), key=lambda l: l.unique_vehicles_count)
            highest_density_lane = max(lanes_seen.values(), key=lambda l: l.image_space_density)
            avg_density = round(sum(l.image_space_density for l in lanes_seen.values()) / len(lanes_seen), 6)
            lane_summary = NetworkLaneSummary(
                total_lanes=len(lanes_seen),
                sources_with_lanes=len(sources_with_lanes),
                busiest_lane_name=busiest_lane.lane_name,
                highest_density_lane_name=highest_density_lane.lane_name,
                average_density=avg_density,
                density_unit="vehicles/px²",
                lane_data_status="OBSERVED",
                epistemic_status="OBSERVED",
            )
        else:
            lane_summary = NetworkLaneSummary(
                total_lanes=0,
                sources_with_lanes=0,
                busiest_lane_name=None,
                highest_density_lane_name=None,
                average_density=0.0,
                density_unit="vehicles/px²",
                lane_data_status="UNAVAILABLE",
                epistemic_status="UNAVAILABLE",
            )

        # Hotspots quick check for top hotspot name
        hotspots_res = cls.get_hotspots(db, params, limit=1)
        if hotspots_res.hotspots:
            top_hotspot_source_name = hotspots_res.hotspots[0].source_name

        # Provenance synthesis
        provenance = HistoricalAnalyticsService.synthesize_provenance(
            sessions=sessions,
            duration_seconds=total_duration,
            is_extrapolated=is_extrapolated,
        )

        # Determine overall epistemic status and data status
        if not sessions:
            epistemic_status = "UNAVAILABLE"
            data_status = "empty"
            data_msg = "No observed traffic records found for the selected network time window."
        elif is_extrapolated:
            epistemic_status = "EXTRAPOLATED"
            data_status = "observed"
            data_msg = "Network metrics synthesized from short-duration observation sessions with extrapolation."
        else:
            epistemic_status = "OBSERVED"
            data_status = "observed"
            data_msg = "Authoritative network intelligence aggregated from persisted observations."

        return NetworkOverviewResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_sources=len(sources),
            selected_sources_count=len(sources),
            active_sources_count=len(active_source_ids),
            total_volume=total_volume,
            flow_rate_per_minute=flow_rate_per_minute,
            flow_rate_per_hour=flow_rate_per_hour,
            observation_duration_seconds=round(total_duration, 1),
            session_count=len(sessions),
            active_incident_count=active_incident_count,
            recurring_incident_locations_count=recurring_locations_count,
            vehicle_classes=vehicle_class_items,
            directional_summary=directional_summary,
            lane_summary=lane_summary,
            top_hotspot_source_name=top_hotspot_source_name,
            epistemic_status=epistemic_status,
            data_status=data_status,
            data_message=data_msg,
            provenance=provenance,
        )

    # =========================================================================
    # 2. Source Comparison
    # =========================================================================
    @classmethod
    def compare_sources(
        cls,
        db: Session,
        params: NetworkFilterParams,
    ) -> NetworkSourceComparisonResponse:
        """
        Compares traffic volume, flow rate, composition, direction, lanes,
        and incident frequency across distinct traffic sources.
        Detects and clearly states observation window mismatches between sources.
        """
        start_time, end_time = cls.resolve_and_validate_window(params)
        sources = cls._query_camera_sources(db, params.source_ids, params.include_synthetic)
        sessions = cls._query_sessions(db, start_time, end_time, params.source_ids, params.include_synthetic)

        # Group sessions by source_id
        sessions_by_source: Dict[str, List[AnalysisSession]] = {s.id: [] for s in sources}
        for sess in sessions:
            if sess.camera_source_id and sess.camera_source_id in sessions_by_source:
                sessions_by_source[sess.camera_source_id].append(sess)

        # Fetch incidents and anomalies grouped by session
        session_ids = [s.id for s in sessions]
        incidents_by_session: Dict[str, List[AnomalyEvent]] = {}
        if session_ids:
            anoms = db.scalars(
                select(AnomalyEvent).where(AnomalyEvent.session_id.in_(session_ids))
            ).all()
            for a in anoms:
                incidents_by_session.setdefault(a.session_id, []).append(a)

        comparison_items: List[NetworkSourceComparisonItem] = []
        network_window_duration = (end_time - start_time).total_seconds()
        window_mismatch_detected = False

        for source in sources:
            src_sessions = sessions_by_source.get(source.id, [])
            src_vol = 0
            src_duration = 0.0
            src_classes: Dict[str, int] = {c: 0 for c in SUPPORTED_VEHICLE_CLASSES}
            src_inbound = 0
            src_outbound = 0
            src_is_extrapolated = False
            src_has_synthetic = source.source_type == CameraSourceType.TEST_FIXTURE.value
            src_has_real = source.source_type != CameraSourceType.TEST_FIXTURE.value

            lane_records: List[LaneResultRecord] = []
            src_incidents: List[AnomalyEvent] = []

            first_seen: Optional[datetime] = None
            last_seen: Optional[datetime] = None

            for sess in src_sessions:
                dt_started = ensure_utc(sess.started_at)
                if dt_started:
                    if first_seen is None or dt_started < first_seen:
                        first_seen = dt_started
                    if last_seen is None or dt_started > last_seen:
                        last_seen = dt_started

                # Incident tracking
                if sess.id in incidents_by_session:
                    src_incidents.extend(incidents_by_session[sess.id])

                # Lane tracking
                lane_records.extend(sess.lane_results)

                # Metrics
                metrics = sess.traffic_metrics
                if metrics:
                    src_vol += metrics.total_volume
                    src_duration += metrics.observation_duration_seconds
                    if metrics.is_extrapolated:
                        src_is_extrapolated = True

                    if metrics.class_distribution and isinstance(metrics.class_distribution, list):
                        for item in metrics.class_distribution:
                            cn = item.get("class_name")
                            cc = item.get("count", 0)
                            if cn in src_classes:
                                src_classes[cn] += cc

                    if metrics.direction_distribution and isinstance(metrics.direction_distribution, list):
                        for item in metrics.direction_distribution:
                            dn = str(item.get("direction", "")).lower()
                            dc = item.get("count", 0)
                            if "in" in dn:
                                src_inbound += dc
                            elif "out" in dn:
                                src_outbound += dc

            src_hours = src_duration / 3600.0
            src_flow_vph = round(src_vol / src_hours, 1) if src_hours > 0 else 0.0

            # Dominant class
            dom_class = max(src_classes.items(), key=lambda x: x[1])[0] if src_vol > 0 else None

            # Directional balance
            dir_ratio = round(src_inbound / max(1, src_outbound), 2) if (src_inbound + src_outbound) > 0 else 1.0
            if dir_ratio >= 1.25 and (src_inbound + src_outbound) > 0:
                dir_balance = "inbound_dominant"
            elif dir_ratio <= 0.80 and (src_inbound + src_outbound) > 0:
                dir_balance = "outbound_dominant"
            else:
                dir_balance = "balanced"

            # Lane metrics
            has_lane_data = len(lane_records) > 0
            lane_count = len(set(lr.lane_id for lr in lane_records))
            avg_lane_density = (
                round(sum(lr.image_space_density for lr in lane_records) / len(lane_records), 6)
                if lane_records else None
            )
            busiest_lane = (
                max(lane_records, key=lambda lr: lr.unique_vehicles_count).lane_name
                if lane_records else None
            )

            # Incidents & recurring
            inc_count = sum(1 for inc in src_incidents if inc.status in ["open", "acknowledged"])
            anom_count = len(src_incidents)
            # Recurring: same type >= 2
            type_counts: Dict[str, int] = {}
            for inc in src_incidents:
                type_counts[inc.anomaly_type] = type_counts.get(inc.anomaly_type, 0) + 1
            recurring_inc_count = sum(1 for c in type_counts.values() if c >= 2)

            # Provenance label
            if src_has_synthetic and not src_has_real:
                src_prov = "TEST FIXTURE"
            elif src_has_synthetic and src_has_real:
                src_prov = "MIXED"
            elif src_sessions:
                src_prov = "REAL DATA"
            else:
                src_prov = "REAL DATA" if source.source_type != CameraSourceType.TEST_FIXTURE.value else "TEST FIXTURE"

            # Epistemic status
            if not src_sessions:
                src_epistemic = "UNAVAILABLE"
            elif src_is_extrapolated:
                src_epistemic = "EXTRAPOLATED"
            else:
                src_epistemic = "OBSERVED"

            # Window mismatch detection
            window_mismatch = False
            window_mismatch_details = None
            if src_sessions and len(sources) > 1 and first_seen and last_seen:
                src_span = (last_seen - first_seen).total_seconds()
                # If source duration is very small compared to network window or starts much later
                if network_window_duration > 86400 and src_span < 0.15 * network_window_duration:
                    window_mismatch = True
                    window_mismatch_detected = True
                    window_mismatch_details = (
                        f"Observation window ({first_seen.strftime('%Y-%m-%d')} to {last_seen.strftime('%Y-%m-%d')}) "
                        f"spans only {round(src_span / 3600.0, 1)}h compared to full {params.time_preset} network window."
                    )

            comparison_items.append(
                NetworkSourceComparisonItem(
                    source_id=source.id,
                    source_name=source.name,
                    source_type=source.source_type,
                    location_name=source.location_name,
                    status=source.status,
                    observed_volume=src_vol,
                    flow_rate_per_hour=src_flow_vph,
                    observation_duration_seconds=round(src_duration, 1),
                    session_count=len(src_sessions),
                    vehicle_composition=src_classes,
                    dominant_vehicle_class=dom_class,
                    inbound_count=src_inbound,
                    outbound_count=src_outbound,
                    directional_balance=dir_balance,
                    has_lane_data=has_lane_data,
                    lane_count=lane_count,
                    average_lane_density=avg_lane_density,
                    busiest_lane_name=busiest_lane,
                    incident_count=inc_count,
                    anomaly_count=anom_count,
                    recurring_incident_count=recurring_inc_count,
                    provenance_label=src_prov,
                    epistemic_status=src_epistemic,
                    observation_window_start=first_seen,
                    observation_window_end=last_seen,
                    window_mismatch=window_mismatch,
                    window_mismatch_details=window_mismatch_details,
                )
            )

        # Sort sources by volume descending
        comparison_items.sort(key=lambda s: s.observed_volume, reverse=True)

        busiest_source_name = comparison_items[0].source_name if (comparison_items and comparison_items[0].observed_volume > 0) else None
        highest_incident_source = max(comparison_items, key=lambda s: s.incident_count) if comparison_items else None
        highest_incident_name = highest_incident_source.source_name if (highest_incident_source and highest_incident_source.incident_count > 0) else None

        # Provenance
        total_duration = sum(s.observation_duration_seconds for s in comparison_items)
        is_comp_extrap = any(s.epistemic_status == "EXTRAPOLATED" for s in comparison_items)
        provenance = HistoricalAnalyticsService.synthesize_provenance(
            sessions=sessions,
            duration_seconds=total_duration,
            is_extrapolated=is_comp_extrap,
        )

        comparison_notes = None
        if len(sources) < 2:
            comparison_notes = "Single source available; multi-source comparative variance requires at least 2 registered sources."
        elif window_mismatch_detected:
            comparison_notes = "Observation window discrepancies detected between sources. Direct comparison should account for unequal observation spans."

        return NetworkSourceComparisonResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_sources_compared=len(comparison_items),
            busiest_source_name=busiest_source_name,
            highest_incident_source_name=highest_incident_name,
            sources=comparison_items,
            window_mismatch_detected=window_mismatch_detected,
            comparison_notes=comparison_notes,
            epistemic_status="DERIVED",
            data_status="observed" if sessions else "empty",
            provenance=provenance,
        )

    # =========================================================================
    # 3. Traffic Hotspot Analysis
    # =========================================================================
    @classmethod
    def get_hotspots(
        cls,
        db: Session,
        params: NetworkFilterParams,
        limit: int = 10,
    ) -> NetworkHotspotResponse:
        """
        Derives operational traffic hotspots from real evidence:
        recurring incidents, repeated anomalies, high observed volume, and lane density.
        Strictly prevents claiming physical geographic coordinates when only camera IDs exist.
        """
        eff_limit = min(max(1, limit), settings.network_intelligence_max_hotspots)
        start_time, end_time = cls.resolve_and_validate_window(params)
        sources = cls._query_camera_sources(db, params.source_ids, params.include_synthetic)
        sessions = cls._query_sessions(db, start_time, end_time, params.source_ids, params.include_synthetic)

        # Provenance
        total_duration = sum(s.traffic_metrics.observation_duration_seconds for s in sessions if s.traffic_metrics)
        is_hotspot_extrap = any(s.traffic_metrics and s.traffic_metrics.is_extrapolated for s in sessions)
        provenance = HistoricalAnalyticsService.synthesize_provenance(
            sessions=sessions,
            duration_seconds=total_duration,
            is_extrapolated=is_hotspot_extrap,
        )

        if not sources or not sessions:
            return NetworkHotspotResponse(
                time_range_start=start_time,
                time_range_end=end_time,
                total_hotspots_identified=0,
                hotspots=[],
                data_status="empty",
                provenance=provenance,
            )

        # Aggregate evidence per source
        sessions_by_source: Dict[str, List[AnalysisSession]] = {s.id: [] for s in sources}
        for sess in sessions:
            if sess.camera_source_id and sess.camera_source_id in sessions_by_source:
                sessions_by_source[sess.camera_source_id].append(sess)

        # Query anomalies in scope
        session_ids = [s.id for s in sessions]
        anoms = db.scalars(
            select(AnomalyEvent).where(AnomalyEvent.session_id.in_(session_ids))
        ).all() if session_ids else []

        anoms_by_session: Dict[str, List[AnomalyEvent]] = {}
        for a in anoms:
            anoms_by_session.setdefault(a.session_id, []).append(a)

        # Calculate max metrics across network for normalization
        max_vol = 1
        max_density = 0.001

        source_stats: Dict[str, Dict[str, Any]] = {}
        for source in sources:
            src_sessions = sessions_by_source.get(source.id, [])
            src_vol = 0
            src_duration = 0.0
            src_anoms: List[AnomalyEvent] = []
            lane_densities: List[float] = []

            for sess in src_sessions:
                if sess.id in anoms_by_session:
                    src_anoms.extend(anoms_by_session[sess.id])
                if sess.traffic_metrics:
                    src_vol += sess.traffic_metrics.total_volume
                    src_duration += sess.traffic_metrics.observation_duration_seconds
                for lr in sess.lane_results:
                    lane_densities.append(lr.image_space_density)

            avg_density = sum(lane_densities) / len(lane_densities) if lane_densities else None

            if src_vol > max_vol:
                max_vol = src_vol
            if avg_density and avg_density > max_density:
                max_density = avg_density

            inc_count = sum(1 for a in src_anoms if a.status in ["open", "acknowledged"])
            # Recurring incidents
            type_counts: Dict[str, int] = {}
            for a in src_anoms:
                type_counts[a.anomaly_type] = type_counts.get(a.anomaly_type, 0) + 1
            recurring_count = sum(1 for c in type_counts.values() if c >= 2)

            src_hours = src_duration / 3600.0
            flow_vph = round(src_vol / src_hours, 1) if src_hours > 0 else 0.0

            source_stats[source.id] = {
                "source": source,
                "vol": src_vol,
                "flow_vph": flow_vph,
                "inc_count": inc_count,
                "recurring_count": recurring_count,
                "anom_count": len(src_anoms),
                "avg_density": avg_density,
                "sessions_count": len(src_sessions),
            }

        hotspot_candidates: List[NetworkHotspotItem] = []

        for sid, stats in source_stats.items():
            src: CameraSource = stats["source"]
            vol = stats["vol"]
            inc_count = stats["inc_count"]
            rec_count = stats["recurring_count"]
            anom_count = stats["anom_count"]
            avg_density = stats["avg_density"]

            # If no activity and no incidents at all, skip from hotspot ranking
            if vol == 0 and anom_count == 0 and inc_count == 0:
                continue

            # Normalized sub-scores (0 - 100)
            inc_score = min(100.0, inc_count * 30.0 + rec_count * 20.0)
            anom_score = min(100.0, anom_count * 25.0)
            vol_score = min(100.0, (vol / max_vol) * 100.0)
            dens_score = min(100.0, (avg_density / max_density) * 100.0) if avg_density else 0.0

            # Composite intensity score
            composite = round(
                0.35 * inc_score + 0.25 * anom_score + 0.25 * vol_score + 0.15 * dens_score,
                1,
            )

            # Severity label
            if composite >= 70.0 or inc_count >= 3:
                severity = "critical"
            elif composite >= 45.0 or inc_count >= 1:
                severity = "high"
            elif composite >= 20.0:
                severity = "medium"
            else:
                severity = "low"

            # Primary contributing factor
            factors = []
            if rec_count > 0:
                factors.append(f"Recurring operational incidents ({rec_count} repeated incident types)")
            if inc_count > 0:
                factors.append(f"{inc_count} active traffic incident(s)")
            if anom_count > 0:
                factors.append(f"{anom_count} detected traffic anomalies")
            if vol_score >= 60.0:
                factors.append(f"High observed traffic volume ({vol} vehicles)")
            if dens_score >= 50.0:
                factors.append(f"Elevated image-space lane density ({round(avg_density, 5)})")

            if not factors:
                factors.append("Observed baseline operational traffic activity")

            primary_factor = factors[0]

            # Hotspot wording rule: "use 'Source hotspot' wording when physical location data is unavailable"
            hotspot_type = "intersection_hotspot" if src.location_name and "intersection" in src.location_name.lower() else "source_hotspot"

            prov_label = "TEST FIXTURE" if src.source_type == CameraSourceType.TEST_FIXTURE.value else "REAL DATA"

            hotspot_candidates.append(
                NetworkHotspotItem(
                    rank=0,  # Assigned after sorting
                    source_id=src.id,
                    source_name=src.name,
                    location_name=src.location_name,
                    hotspot_type=hotspot_type,
                    hotspot_score=composite,
                    severity=severity,
                    incident_count=inc_count,
                    recurring_incident_count=rec_count,
                    anomaly_count=anom_count,
                    observed_volume=vol,
                    flow_rate_per_hour=stats["flow_vph"],
                    average_lane_density=round(avg_density, 6) if avg_density else None,
                    primary_contributing_factor=primary_factor,
                    contributing_factors=factors,
                    epistemic_status="DERIVED",
                    provenance_label=prov_label,
                )
            )

        # Sort: composite score DESC, incident count DESC, volume DESC
        hotspot_candidates.sort(
            key=lambda h: (h.hotspot_score, h.incident_count, h.observed_volume),
            reverse=True,
        )

        # Apply ranks and limit
        ranked_hotspots: List[NetworkHotspotItem] = []
        for i, item in enumerate(hotspot_candidates[:eff_limit], start=1):
            item.rank = i
            ranked_hotspots.append(item)

        return NetworkHotspotResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_hotspots_identified=len(ranked_hotspots),
            hotspots=ranked_hotspots,
            data_status="observed" if ranked_hotspots else "empty",
            provenance=provenance,
        )

    # =========================================================================
    # 4. Vehicle Composition
    # =========================================================================
    @classmethod
    def get_vehicle_composition(
        cls,
        db: Session,
        params: NetworkFilterParams,
    ) -> NetworkVehicleCompositionResponse:
        """
        Analyzes vehicle class distribution network-wide and per-source
        strictly using the 5 supported YOLO vehicle classes.
        """
        start_time, end_time = cls.resolve_and_validate_window(params)
        sources = cls._query_camera_sources(db, params.source_ids, params.include_synthetic)
        sessions = cls._query_sessions(db, start_time, end_time, params.source_ids, params.include_synthetic)

        total_vehicles = 0
        total_duration = 0.0
        network_class_counts: Dict[str, int] = {c: 0 for c in SUPPORTED_VEHICLE_CLASSES}
        source_composition: Dict[str, Dict[str, int]] = {s.id: {c: 0 for c in SUPPORTED_VEHICLE_CLASSES} for s in sources}

        for sess in sessions:
            metrics = sess.traffic_metrics
            if metrics:
                total_duration += metrics.observation_duration_seconds
                if metrics.class_distribution and isinstance(metrics.class_distribution, list):
                    for item in metrics.class_distribution:
                        cn = item.get("class_name")
                        cc = item.get("count", 0)
                        if cn in network_class_counts:
                            network_class_counts[cn] += cc
                            total_vehicles += cc
                            if sess.camera_source_id and sess.camera_source_id in source_composition:
                                source_composition[sess.camera_source_id][cn] += cc

        hours = total_duration / 3600.0
        classes_list: List[NetworkVehicleClassItem] = []
        for c in SUPPORTED_VEHICLE_CLASSES:
            cnt = network_class_counts[c]
            pct = round(cnt / total_vehicles * 100.0, 1) if total_vehicles > 0 else 0.0
            rate_hr = round(cnt / hours, 1) if hours > 0 else 0.0
            classes_list.append(
                NetworkVehicleClassItem(
                    class_name=c,
                    count=cnt,
                    percentage=pct,
                    rate_per_hour=rate_hr,
                    epistemic_status="OBSERVED",
                )
            )

        # Dominant classes
        net_dom = max(network_class_counts.items(), key=lambda x: x[1])[0] if total_vehicles > 0 else None
        source_dom: Dict[str, str] = {}
        for sid, comp in source_composition.items():
            s_total = sum(comp.values())
            source_dom[sid] = max(comp.items(), key=lambda x: x[1])[0] if s_total > 0 else "car"

        # Heavy vehicles: truck + bus
        heavy_count = network_class_counts.get("truck", 0) + network_class_counts.get("bus", 0)
        heavy_pct = round(heavy_count / total_vehicles * 100.0, 1) if total_vehicles > 0 else 0.0

        is_veh_extrap = any(s.traffic_metrics and s.traffic_metrics.is_extrapolated for s in sessions)
        provenance = HistoricalAnalyticsService.synthesize_provenance(
            sessions=sessions,
            duration_seconds=total_duration,
            is_extrapolated=is_veh_extrap,
        )

        return NetworkVehicleCompositionResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_vehicles=total_vehicles,
            heavy_vehicle_percentage=heavy_pct,
            network_dominant_class=net_dom,
            classes=classes_list,
            source_composition=source_composition,
            source_dominant_classes=source_dom,
            epistemic_status="OBSERVED" if total_vehicles > 0 else "UNAVAILABLE",
            data_status="observed" if total_vehicles > 0 else "empty",
            provenance=provenance,
        )

    # =========================================================================
    # 5. Directional Intelligence
    # =========================================================================
    @classmethod
    def get_directional_analysis(
        cls,
        db: Session,
        params: NetworkFilterParams,
    ) -> NetworkDirectionalResponse:
        """
        Analyzes directional balance (inbound vs outbound) across sources and network-wide.
        """
        start_time, end_time = cls.resolve_and_validate_window(params)
        sources = cls._query_camera_sources(db, params.source_ids, params.include_synthetic)
        sessions = cls._query_sessions(db, start_time, end_time, params.source_ids, params.include_synthetic)

        net_inbound = 0
        net_outbound = 0
        total_duration = 0.0

        source_dir_map: Dict[str, Dict[str, int]] = {s.id: {"inbound": 0, "outbound": 0} for s in sources}

        for sess in sessions:
            metrics = sess.traffic_metrics
            if metrics:
                total_duration += metrics.observation_duration_seconds
                if metrics.direction_distribution and isinstance(metrics.direction_distribution, list):
                    for d in metrics.direction_distribution:
                        dn = str(d.get("direction", "")).lower()
                        dc = d.get("count", 0)
                        if "in" in dn:
                            net_inbound += dc
                            if sess.camera_source_id and sess.camera_source_id in source_dir_map:
                                source_dir_map[sess.camera_source_id]["inbound"] += dc
                        elif "out" in dn:
                            net_outbound += dc
                            if sess.camera_source_id and sess.camera_source_id in source_dir_map:
                                source_dir_map[sess.camera_source_id]["outbound"] += dc

        net_total = net_inbound + net_outbound
        net_ratio = round(net_inbound / max(1, net_outbound), 2) if net_total > 0 else 1.0
        if net_ratio >= 1.25 and net_total > 0:
            net_balance = "inbound_dominant"
        elif net_ratio <= 0.80 and net_total > 0:
            net_balance = "outbound_dominant"
        else:
            net_balance = "balanced"

        net_summary = NetworkDirectionalSummary(
            inbound_count=net_inbound,
            outbound_count=net_outbound,
            inbound_percentage=round(net_inbound / net_total * 100.0, 1) if net_total > 0 else 0.0,
            outbound_percentage=round(net_outbound / net_total * 100.0, 1) if net_total > 0 else 0.0,
            directional_ratio=net_ratio,
            balance_status=net_balance,
            epistemic_status="OBSERVED" if net_total > 0 else "UNAVAILABLE",
        )

        source_items: List[NetworkDirectionalSourceItem] = []
        inbound_dom_count = 0
        outbound_dom_count = 0
        balanced_count = 0

        for src in sources:
            d_counts = source_dir_map.get(src.id, {"inbound": 0, "outbound": 0})
            s_in = d_counts["inbound"]
            s_out = d_counts["outbound"]
            s_total = s_in + s_out
            s_ratio = round(s_in / max(1, s_out), 2) if s_total > 0 else 1.0

            if s_ratio >= 1.25 and s_total > 0:
                s_bal = "inbound_dominant"
                inbound_dom_count += 1
            elif s_ratio <= 0.80 and s_total > 0:
                s_bal = "outbound_dominant"
                outbound_dom_count += 1
            else:
                s_bal = "balanced"
                balanced_count += 1

            source_items.append(
                NetworkDirectionalSourceItem(
                    source_id=src.id,
                    source_name=src.name,
                    location_name=src.location_name,
                    inbound_count=s_in,
                    outbound_count=s_out,
                    inbound_percentage=round(s_in / s_total * 100.0, 1) if s_total > 0 else 0.0,
                    outbound_percentage=round(s_out / s_total * 100.0, 1) if s_total > 0 else 0.0,
                    directional_ratio=s_ratio,
                    balance_status=s_bal,
                )
            )

        is_dir_extrap = any(s.traffic_metrics and s.traffic_metrics.is_extrapolated for s in sessions)
        provenance = HistoricalAnalyticsService.synthesize_provenance(
            sessions=sessions,
            duration_seconds=total_duration,
            is_extrapolated=is_dir_extrap,
        )

        return NetworkDirectionalResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            network_summary=net_summary,
            sources=source_items,
            inbound_dominant_count=inbound_dom_count,
            outbound_dominant_count=outbound_dom_count,
            balanced_count=balanced_count,
            epistemic_status="DERIVED",
            data_status="observed" if net_total > 0 else "empty",
            provenance=provenance,
        )

    # =========================================================================
    # 6. Lane Analysis
    # =========================================================================
    @classmethod
    def get_lane_analysis(
        cls,
        db: Session,
        params: NetworkFilterParams,
    ) -> NetworkLaneResponse:
        """
        Reuses Phase 22 Lane Intelligence to aggregate lane occupancy and image-space density.
        Returns UNAVAILABLE for sources without valid lane configurations.
        """
        start_time, end_time = cls.resolve_and_validate_window(params)
        sources = cls._query_camera_sources(db, params.source_ids, params.include_synthetic)
        sessions = cls._query_sessions(db, start_time, end_time, params.source_ids, params.include_synthetic)

        # Call Phase 22 authoritative lane intelligence
        hist_params = cls._to_historical_params(params)
        lane_res = HistoricalAnalyticsService.get_lanes(db, hist_params)

        sources_with_lanes: Set[str] = set()
        for sess in sessions:
            if sess.lane_results and sess.camera_source_id:
                sources_with_lanes.add(sess.camera_source_id)

        sources_without_count = len(sources) - len(sources_with_lanes)

        lane_data_status = "OBSERVED" if lane_res.lanes else "UNAVAILABLE"

        return NetworkLaneResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_lanes=len(lane_res.lanes),
            sources_with_lanes_count=len(sources_with_lanes),
            sources_without_lanes_count=max(0, sources_without_count),
            lanes=lane_res.lanes,
            busiest_lane_name=lane_res.busiest_lane_name,
            highest_density_lane_name=lane_res.highest_density_lane_name,
            density_calibration_disclaimer=lane_res.provenance.mix_warning
            or "Uncalibrated image-space density heuristic: relative comparison only, not physical density (pce/km).",
            epistemic_status=lane_data_status,
            data_status="observed" if lane_res.lanes else "empty",
            provenance=lane_res.provenance,
        )

    # =========================================================================
    # 7. Temporal Cross-Source Analysis
    # =========================================================================
    @classmethod
    def get_temporal_cross_source_analysis(
        cls,
        db: Session,
        params: NetworkFilterParams,
    ) -> NetworkTemporalAnalysisResponse:
        """
        Cross-source synchronized timeline analysis across discrete time buckets.
        Honest epistemic note: Never asserts vehicle travel times or route causality.
        """
        start_time, end_time = cls.resolve_and_validate_window(params)
        sources = cls._query_camera_sources(db, params.source_ids, params.include_synthetic)
        sessions = cls._query_sessions(db, start_time, end_time, params.source_ids, params.include_synthetic)

        bucket_int_name, bucket_seconds = HistoricalAnalyticsService.get_bucket_interval_seconds(
            params.bucket_interval or "hourly"
        )

        # Build chronological buckets
        buckets: List[NetworkTemporalBucket] = []
        cur_t = start_time
        bucket_idx = 0
        total_range_seconds = (end_time - start_time).total_seconds()
        max_buckets = min(settings.max_historical_buckets, 500)

        source_map = {s.id: s.name for s in sources}

        while cur_t < end_time and bucket_idx < max_buckets:
            next_t = min(cur_t + timedelta(seconds=bucket_seconds), end_time)
            bucket_idx += 1

            # Match sessions in this bucket
            sess_in_bucket = [
                s for s in sessions
                if s.started_at and cur_t <= ensure_utc(s.started_at) < next_t
            ]

            b_vol = 0
            src_vol_map: Dict[str, int] = {}
            src_duration_map: Dict[str, float] = {}

            for s in sess_in_bucket:
                sid = s.camera_source_id or "unknown"
                vol = s.traffic_metrics.total_volume if s.traffic_metrics else 0
                dur = s.traffic_metrics.observation_duration_seconds if s.traffic_metrics else 0.0
                b_vol += vol
                src_vol_map[sid] = src_vol_map.get(sid, 0) + vol
                src_duration_map[sid] = src_duration_map.get(sid, 0.0) + dur

            src_items: List[NetworkTemporalBucketSourceItem] = []
            for sid, v in src_vol_map.items():
                d = src_duration_map.get(sid, 0.0)
                hrs = d / 3600.0
                rate_hr = round(v / hrs, 1) if hrs > 0 else float(v)
                src_items.append(
                    NetworkTemporalBucketSourceItem(
                        source_id=sid,
                        source_name=source_map.get(sid, sid),
                        volume=v,
                        flow_rate_per_hour=rate_hr,
                    )
                )

            buckets.append(
                NetworkTemporalBucket(
                    bucket_index=bucket_idx,
                    start_time=cur_t,
                    end_time=next_t,
                    total_volume=b_vol,
                    sources=src_items,
                    active_sources_count=len(src_items),
                    is_network_peak=False,  # Evaluated below
                )
            )

            cur_t = next_t

        # Evaluate network peak buckets
        peak_buckets_count = 0
        if buckets:
            avg_bucket_vol = sum(b.total_volume for b in buckets) / len(buckets)
            for b in buckets:
                # Network peak: elevated volume and >= 2 active sources (if multi-source)
                if b.total_volume >= max(10, avg_bucket_vol * 1.3) and b.active_sources_count >= min(2, len(sources)):
                    b.is_network_peak = True
                    peak_buckets_count += 1

        total_duration = sum(
            (s.traffic_metrics.observation_duration_seconds or 0.0)
            for s in sessions
            if s.traffic_metrics
        )
        is_temp_extrap = any(s.traffic_metrics and s.traffic_metrics.is_extrapolated for s in sessions)
        provenance = HistoricalAnalyticsService.synthesize_provenance(
            sessions=sessions,
            duration_seconds=total_duration,
            is_extrapolated=is_temp_extrap,
        )

        return NetworkTemporalAnalysisResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            bucket_interval=bucket_int_name,
            total_buckets=len(buckets),
            buckets=buckets,
            synchronized_peak_buckets_count=peak_buckets_count,
            epistemic_note=(
                "Temporal cross-source patterns represent synchronized observation windows. "
                "No vehicle travel times, propagation speeds, or route causality are asserted without multi-camera tracking evidence."
            ),
            epistemic_status="DERIVED",
            data_status="observed" if sessions else "empty",
            provenance=provenance,
        )

    # =========================================================================
    # 8. Historical Comparison (Phase 22 Reuse)
    # =========================================================================
    @classmethod
    def get_historical_comparison(
        cls,
        db: Session,
        params: NetworkFilterParams,
    ) -> PeriodComparisonResponse:
        """
        Reuses Phase 22 HistoricalAnalyticsService to compute authoritative
        period-over-period delta comparisons across the traffic network.
        """
        hist_params = cls._to_historical_params(params)
        return HistoricalAnalyticsService.get_comparison(db, hist_params)
