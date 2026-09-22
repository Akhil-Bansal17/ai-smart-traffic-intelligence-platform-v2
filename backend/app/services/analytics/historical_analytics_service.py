"""
Historical Traffic Intelligence & Trend Analysis Service.
Phase 22: Historical Traffic Intelligence & Trend Analysis.

Strict adherence to:
- Evidence-based descriptive analysis: answers "What actually happened?", NEVER "What will happen?"
- Zero CV re-execution: strictly queries authoritative persisted records.
- Honest observed vs. extrapolated vs. unavailable semantics.
- Deterministic peak analysis with explicit, documented tie-breaking rules.
- Strict provenance tracking with real vs synthetic vs test-fixture isolation.
- Zero fake data, zero padded empty states.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
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
from app.models.camera_source import CameraSource
from app.models.insight import TrafficInsight
from app.models.video import Video
from app.schemas.historical_analytics import (
    AnomalyHistoryItem,
    AnomalyHistoryResponse,
    DirectionalFlowMetric,
    DirectionalTrendResponse,
    HistoricalBucketItem,
    HistoricalFilterParams,
    HistoricalProvenanceSummary,
    HistoricalSummaryResponse,
    HistoricalTimeSeriesResponse,
    LaneIntelligenceItem,
    LaneIntelligenceResponse,
    PeakPeriodItem,
    PeakPeriodsResponse,
    PeriodComparisonResponse,
    PeriodDeltaMetric,
    SourceComparisonResponse,
    SourceMetricItem,
    VehicleClassMetricItem,
    VehicleCompositionTrendResponse,
)

logger = get_logger(__name__)

SUPPORTED_VEHICLE_CLASSES = ["car", "truck", "bus", "motorcycle", "bicycle"]
TIE_BREAKING_RULE_DESC = (
    "In the event of identical peak values, the earlier bucket start time takes precedence; "
    "if still tied, the bucket with greater cumulative observation duration wins; "
    "if still tied, sorted by chronological bucket start ascending."
)


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


class HistoricalAnalyticsService:
    """
    High-performance, query-safe service for aggregating, bucketing, and analyzing
    historical traffic observations from uploaded videos and live camera sources.
    """

    # -------------------------------------------------------------------------
    # Helper: Resolve and Validate Time Window
    # -------------------------------------------------------------------------
    @staticmethod
    def resolve_time_window(
        params: HistoricalFilterParams,
    ) -> Tuple[datetime, datetime]:
        """
        Resolves start and end datetimes from parameters or presets and validates bounds.
        Boundary semantics: strictly [start_time, end_time] inclusive.
        """
        now = utcnow()

        if params.start_time and params.end_time:
            start_time = params.start_time
            end_time = params.end_time
        elif params.time_preset and params.time_preset != "custom":
            preset = params.time_preset.lower()
            if preset == "24h":
                start_time = now - timedelta(hours=24)
            elif preset == "7d":
                start_time = now - timedelta(days=7)
            elif preset == "30d":
                start_time = now - timedelta(days=30)
            elif preset == "90d":
                start_time = now - timedelta(days=90)
            else:
                start_time = now - timedelta(days=7)
            end_time = now
        else:
            start_time = params.start_time or (now - timedelta(days=7))
            end_time = params.end_time or now

        # Ensure timezone-aware UTC
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        if start_time > end_time:
            raise AppException(
                message=f"start_time ({start_time.isoformat()}) cannot be after end_time ({end_time.isoformat()}).",
                code="INVALID_DATE_RANGE",
                status_code=400,
            )

        duration_days = (end_time - start_time).total_seconds() / 86400.0
        if duration_days > settings.max_historical_range_days:
            raise AppException(
                message=(
                    f"Requested date range ({duration_days:.1f} days) exceeds maximum allowed "
                    f"({settings.max_historical_range_days} days)."
                ),
                code="DATE_RANGE_EXCEEDS_LIMIT",
                status_code=400,
            )

        return start_time, end_time

    # -------------------------------------------------------------------------
    # Helper: Resolve Bucket Interval Seconds
    # -------------------------------------------------------------------------
    @staticmethod
    def get_bucket_interval_seconds(bucket_interval: Optional[str]) -> Tuple[str, int]:
        """Resolves bucket interval code and exact duration in seconds."""
        interval = (bucket_interval or "hourly").lower()
        if interval == "15m":
            return "15m", 900
        elif interval == "30m":
            return "30m", 1800
        elif interval == "hourly":
            return "hourly", 3600
        elif interval == "daily":
            return "daily", 86400
        elif interval == "weekly":
            return "weekly", 604800
        return "hourly", 3600

    # -------------------------------------------------------------------------
    # Helper: Query Sessions with Filters and Provenance Isolation
    # -------------------------------------------------------------------------
    @classmethod
    def query_sessions(
        cls,
        db: Session,
        start_time: datetime,
        end_time: datetime,
        params: HistoricalFilterParams,
    ) -> List[AnalysisSession]:
        """
        Retrieves matching analysis sessions with eager relationship joins.
        Enforces strict provenance isolation: synthetic and test fixture data
        are excluded by default unless include_synthetic is True.
        """
        stmt = (
            select(AnalysisSession)
            .options(
                joinedload(AnalysisSession.video),
                joinedload(AnalysisSession.camera_source),
                selectinload(AnalysisSession.traffic_metrics),
                selectinload(AnalysisSession.lane_results),
            )
            .where(
                and_(
                    AnalysisSession.started_at >= start_time,
                    AnalysisSession.started_at <= end_time,
                    AnalysisSession.status == "completed",
                )
            )
            .order_by(AnalysisSession.started_at.asc())
            .limit(settings.max_historical_records)
        )

        # Filter by camera source ID
        if params.camera_source_id:
            stmt = stmt.where(AnalysisSession.camera_source_id == params.camera_source_id)

        # Filter by session mode
        if params.session_mode:
            stmt = stmt.where(AnalysisSession.session_mode == params.session_mode)

        sessions = list(db.scalars(stmt).all())

        # Enforce provenance isolation in Python if necessary
        if not params.include_synthetic:
            filtered = []
            for s in sessions:
                # Exclude explicit test fixture camera sources
                if s.camera_source and s.camera_source.source_type == "test_fixture":
                    continue
                # Exclude unverified synthetic videos
                if s.video and s.video.source_type in ["synthetic_test", "synthetic_fixture"]:
                    continue
                filtered.append(s)
            return filtered

        return sessions

    # -------------------------------------------------------------------------
    # Helper: Synthesize Provenance Summary
    # -------------------------------------------------------------------------
    @classmethod
    def synthesize_provenance(
        cls,
        sessions: List[AnalysisSession],
        duration_seconds: float,
        is_extrapolated: bool,
    ) -> HistoricalProvenanceSummary:
        """Determines strict epistemic truth and provenance classification."""
        if not sessions:
            return HistoricalProvenanceSummary(
                source_types=[],
                provenance_category="unavailable",
                provenance_label="UNAVAILABLE",
                provenance_badge_variant="neutral",
                is_synthetic=False,
                is_mixed=False,
                is_extrapolated=False,
                observation_duration_seconds=0.0,
                session_count=0,
                camera_source_count=0,
                description="No completed observation sessions found within specified parameters",
            )

        source_types = set()
        real_count = 0
        synthetic_count = 0
        fixture_count = 0
        camera_sources = set()

        for s in sessions:
            if s.camera_source_id:
                camera_sources.add(s.camera_source_id)
            if s.camera_source:
                stype = s.camera_source.source_type
                source_types.add(stype)
                if stype == "test_fixture":
                    fixture_count += 1
                elif stype in ["local_camera", "rtsp", "http_stream"]:
                    real_count += 1
                else:
                    synthetic_count += 1
            elif s.video:
                vtype = s.video.source_type
                source_types.add(vtype)
                if vtype == "real_world" and s.video.provenance_verified:
                    real_count += 1
                elif vtype == "synthetic_fixture":
                    fixture_count += 1
                else:
                    synthetic_count += 1
            else:
                source_types.add("unknown")
                synthetic_count += 1

        total = len(sessions)
        is_mixed = (real_count > 0 and (synthetic_count > 0 or fixture_count > 0)) or (synthetic_count > 0 and fixture_count > 0)

        if is_mixed:
            label = "MIXED"
            badge = "warning"
            cat = "mixed_provenance"
            desc = (
                f"Mixed dataset across {real_count} real-world, {synthetic_count} synthetic, "
                f"and {fixture_count} test fixture session(s). Interpret with caution."
            )
            mix_warn = (
                "Dataset contains mixed provenance. Synthetic and real observations are aggregated together. "
                "Set include_synthetic=False for strict real-world isolation."
            )
            is_synth = synthetic_count > 0 or fixture_count > 0
        elif real_count == total:
            label = "REAL DATA"
            badge = "success"
            cat = "real_database_metrics"
            desc = f"Verified genuine observations across {total} session(s)"
            mix_warn = None
            is_synth = False
        elif fixture_count == total:
            label = "TEST FIXTURE"
            badge = "purple"
            cat = "synthetic_fixture"
            desc = f"Deterministic test fixture data across {total} session(s)"
            mix_warn = None
            is_synth = True
        else:
            label = "SYNTHETIC"
            badge = "warning"
            cat = "synthetic_pipeline_metrics"
            desc = f"Synthetic/test pipeline observations across {total} session(s)"
            mix_warn = None
            is_synth = True

        return HistoricalProvenanceSummary(
            source_types=sorted(list(source_types)),
            provenance_category=cat,
            provenance_label=label,
            provenance_badge_variant=badge,
            is_synthetic=is_synth,
            is_mixed=is_mixed,
            is_extrapolated=is_extrapolated,
            observation_duration_seconds=duration_seconds,
            session_count=total,
            camera_source_count=len(camera_sources),
            description=desc,
            mix_warning=mix_warn,
        )

    # -------------------------------------------------------------------------
    # 1. Historical Summary Endpoint Logic
    # -------------------------------------------------------------------------
    @classmethod
    def get_summary(
        cls,
        db: Session,
        params: HistoricalFilterParams,
    ) -> HistoricalSummaryResponse:
        """Computes comprehensive high-level historical traffic summary."""
        start_time, end_time = cls.resolve_time_window(params)
        sessions = cls.query_sessions(db, start_time, end_time, params)

        if not sessions:
            prov = cls.synthesize_provenance([], 0.0, False)
            return HistoricalSummaryResponse(
                time_range_start=start_time,
                time_range_end=end_time,
                observation_duration_seconds=0.0,
                total_observed_volume=0,
                flow_rate_per_minute=0.0,
                flow_rate_per_hour=0.0,
                is_extrapolated=False,
                inbound_volume=0,
                outbound_volume=0,
                inbound_percentage=0.0,
                outbound_percentage=0.0,
                session_count=0,
                source_count=0,
                anomaly_count=0,
                insight_count=0,
                peak_flow_rate_vph=0.0,
                peak_flow_period=None,
                data_status="insufficient",
                data_message="No completed analysis sessions recorded within the selected period.",
                provenance=prov,
            )

        total_volume = 0
        total_duration = 0.0
        inbound_volume = 0
        outbound_volume = 0
        sources = set()
        session_ids = [s.id for s in sessions]

        for s in sessions:
            src_key = s.camera_source_id or s.video_id or s.id
            sources.add(src_key)
            if s.traffic_metrics:
                m = s.traffic_metrics
                total_volume += m.total_volume
                total_duration += m.observation_duration_seconds
                # Extract inbound/outbound from directional distribution
                if m.direction_distribution and isinstance(m.direction_distribution, list):
                    for d in m.direction_distribution:
                        d_name = str(d.get("direction", "")).lower()
                        d_count = int(d.get("count", 0))
                        if d_name in ["inbound", "in", "northbound", "eastbound"]:
                            inbound_volume += d_count
                        elif d_name in ["outbound", "out", "southbound", "westbound"]:
                            outbound_volume += d_count
            else:
                total_volume += s.total_vehicles_counted
                total_duration += (s.completed_at - s.started_at).total_seconds() if s.completed_at else 0.0

        # Flow rates calculation
        flow_rate_per_minute = (total_volume / (total_duration / 60.0)) if total_duration > 0 else 0.0
        flow_rate_per_hour = (total_volume / (total_duration / 3600.0)) if total_duration > 0 else 0.0
        is_extrapolated = total_duration < 3600.0 and total_volume > 0

        # Fallback for inbound/outbound if directional distribution was empty
        if inbound_volume == 0 and outbound_volume == 0 and total_volume > 0:
            inbound_volume = total_volume

        inbound_pct = round((inbound_volume / total_volume * 100.0), 1) if total_volume > 0 else 0.0
        outbound_pct = round((outbound_volume / total_volume * 100.0), 1) if total_volume > 0 else 0.0

        # Query anomalies and insights in range
        anomaly_count = db.scalar(
            select(func.count(AnomalyEvent.id)).where(AnomalyEvent.session_id.in_(session_ids))
        ) or 0
        insight_count = db.scalar(
            select(func.count(TrafficInsight.id)).where(TrafficInsight.session_id.in_(session_ids))
        ) or 0

        # Peak flow calculation across sessions
        peak_vph = 0.0
        peak_period_str = None
        for s in sessions:
            if s.traffic_metrics and s.traffic_metrics.flow_rate_per_hour > peak_vph:
                peak_vph = s.traffic_metrics.flow_rate_per_hour
                peak_period_str = s.started_at.strftime("%Y-%m-%d %H:%M UTC")

        prov = cls.synthesize_provenance(sessions, total_duration, is_extrapolated)

        return HistoricalSummaryResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            observation_duration_seconds=round(total_duration, 2),
            total_observed_volume=total_volume,
            flow_rate_per_minute=round(flow_rate_per_minute, 2),
            flow_rate_per_hour=round(flow_rate_per_hour, 2),
            is_extrapolated=is_extrapolated,
            inbound_volume=inbound_volume,
            outbound_volume=outbound_volume,
            inbound_percentage=inbound_pct,
            outbound_percentage=outbound_pct,
            session_count=len(sessions),
            source_count=len(sources),
            anomaly_count=anomaly_count,
            insight_count=insight_count,
            peak_flow_rate_vph=round(peak_vph, 2),
            peak_flow_period=peak_period_str,
            data_status="observed",
            data_message="Authoritative observations synthesized from database",
            provenance=prov,
        )

    # -------------------------------------------------------------------------
    # 2. Historical Time-Series Bucketing
    # -------------------------------------------------------------------------
    @classmethod
    def get_timeseries(
        cls,
        db: Session,
        params: HistoricalFilterParams,
    ) -> HistoricalTimeSeriesResponse:
        """Computes discrete, non-interpolated time-series bucket aggregation."""
        start_time, end_time = cls.resolve_time_window(params)
        interval_code, interval_sec = cls.get_bucket_interval_seconds(params.bucket_interval)
        sessions = cls.query_sessions(db, start_time, end_time, params)

        # Generate non-overlapping contiguous temporal buckets
        total_seconds = (end_time - start_time).total_seconds()
        num_buckets = int(total_seconds // interval_sec)
        if total_seconds % interval_sec > 0:
            num_buckets += 1
        num_buckets = min(num_buckets, settings.max_historical_buckets)

        bucket_items: List[HistoricalBucketItem] = []
        cumulative_duration = 0.0

        for b_idx in range(num_buckets):
            b_start = start_time + timedelta(seconds=b_idx * interval_sec)
            b_end = min(b_start + timedelta(seconds=interval_sec), end_time)

            # Find all sessions whose started_at falls into [b_start, b_end)
            # or for the last bucket [b_start, b_end]
            matching_sessions = []
            for s in sessions:
                s_st = ensure_utc(s.started_at)
                if (b_start <= s_st < b_end) or (b_idx == num_buckets - 1 and b_start <= s_st <= b_end):
                    matching_sessions.append(s)

            b_volume = 0
            b_duration = 0.0
            b_classes: Dict[str, int] = {c: 0 for c in SUPPORTED_VEHICLE_CLASSES}
            b_inbound = 0
            b_outbound = 0
            b_sources = set()

            for s in matching_sessions:
                b_src = s.camera_source_id or s.video_id or s.id
                b_sources.add(b_src)
                if s.traffic_metrics:
                    m = s.traffic_metrics
                    b_volume += m.total_volume
                    b_duration += m.observation_duration_seconds
                    # Classes
                    if m.class_distribution and isinstance(m.class_distribution, list):
                        for c_item in m.class_distribution:
                            c_name = str(c_item.get("class_name", "")).lower()
                            if c_name in b_classes:
                                b_classes[c_name] += int(c_item.get("count", 0))
                    # Directions
                    if m.direction_distribution and isinstance(m.direction_distribution, list):
                        for d in m.direction_distribution:
                            d_name = str(d.get("direction", "")).lower()
                            d_count = int(d.get("count", 0))
                            if d_name in ["inbound", "in", "northbound", "eastbound"]:
                                b_inbound += d_count
                            elif d_name in ["outbound", "out", "southbound", "westbound"]:
                                b_outbound += d_count
                else:
                    b_volume += s.total_vehicles_counted
                    b_duration += (s.completed_at - s.started_at).total_seconds() if s.completed_at else 0.0

            if b_inbound == 0 and b_outbound == 0 and b_volume > 0:
                b_inbound = b_volume

            flow_min = (b_volume / (b_duration / 60.0)) if b_duration > 0 else 0.0
            flow_hr = (b_volume / (b_duration / 3600.0)) if b_duration > 0 else 0.0
            is_extrap = any(s.traffic_metrics and s.traffic_metrics.is_extrapolated for s in matching_sessions)

            cumulative_duration += b_duration
            data_status = "observed" if b_volume > 0 else ("sparse" if matching_sessions else "empty")
            prov_type = "real_observation" if matching_sessions else "no_data"

            bucket_items.append(
                HistoricalBucketItem(
                    bucket_index=b_idx,
                    start_time=b_start,
                    end_time=b_end,
                    observation_duration_seconds=round(b_duration, 2),
                    observed_volume=b_volume,
                    flow_rate_per_minute=round(flow_min, 2),
                    flow_rate_per_hour=round(flow_hr, 2),
                    is_extrapolated=is_extrap,
                    vehicle_composition=b_classes,
                    inbound_count=b_inbound,
                    outbound_count=b_outbound,
                    session_count=len(matching_sessions),
                    source_count=len(b_sources),
                    provenance_type=prov_type,
                    data_status=data_status,
                )
            )

        prov = cls.synthesize_provenance(sessions, cumulative_duration, False)
        status = "observed" if any(b.observed_volume > 0 for b in bucket_items) else "insufficient"

        return HistoricalTimeSeriesResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            bucket_interval=interval_code,
            bucket_interval_seconds=interval_sec,
            total_buckets=len(bucket_items),
            buckets=bucket_items,
            data_status=status,
            provenance=prov,
        )

    # -------------------------------------------------------------------------
    # 3. Vehicle Composition Trends
    # -------------------------------------------------------------------------
    @classmethod
    def get_vehicle_composition(
        cls,
        db: Session,
        params: HistoricalFilterParams,
    ) -> VehicleCompositionTrendResponse:
        """Analyzes vehicle classification composition and temporal trend."""
        start_time, end_time = cls.resolve_time_window(params)
        sessions = cls.query_sessions(db, start_time, end_time, params)

        class_totals = {c: 0 for c in SUPPORTED_VEHICLE_CLASSES}
        total_vehicles = 0
        total_duration = 0.0

        # Split sessions into first half and second half for slope / trend evaluation
        midpoint = start_time + (end_time - start_time) / 2
        first_half_counts = {c: 0 for c in SUPPORTED_VEHICLE_CLASSES}
        second_half_counts = {c: 0 for c in SUPPORTED_VEHICLE_CLASSES}

        for s in sessions:
            is_first_half = ensure_utc(s.started_at) < midpoint
            if s.traffic_metrics:
                m = s.traffic_metrics
                total_duration += m.observation_duration_seconds
                if m.class_distribution and isinstance(m.class_distribution, list):
                    for item in m.class_distribution:
                        c_name = str(item.get("class_name", "")).lower()
                        c_count = int(item.get("count", 0))
                        if c_name in class_totals:
                            class_totals[c_name] += c_count
                            total_vehicles += c_count
                            if is_first_half:
                                first_half_counts[c_name] += c_count
                            else:
                                second_half_counts[c_name] += c_count

        items: List[VehicleClassMetricItem] = []
        for c_name in SUPPORTED_VEHICLE_CLASSES:
            cnt = class_totals[c_name]
            pct = round((cnt / total_vehicles * 100.0), 1) if total_vehicles > 0 else 0.0
            rate = round(cnt / (total_duration / 3600.0), 2) if total_duration > 0 else 0.0

            # Determine trend direction
            h1 = first_half_counts[c_name]
            h2 = second_half_counts[c_name]
            if h1 == 0 and h2 == 0:
                trend = "stable"
            elif h1 == 0 and h2 > 0:
                trend = "increasing"
            elif h1 > 0 and h2 == 0:
                trend = "decreasing"
            else:
                pct_change = ((h2 - h1) / h1) * 100.0
                if pct_change > 15.0:
                    trend = "increasing"
                elif pct_change < -15.0:
                    trend = "decreasing"
                else:
                    trend = "stable"

            items.append(
                VehicleClassMetricItem(
                    class_name=c_name.capitalize(),
                    count=cnt,
                    percentage=pct,
                    trend=trend,
                    rate_per_hour=rate,
                )
            )

        prov = cls.synthesize_provenance(sessions, total_duration, False)
        status = "observed" if total_vehicles > 0 else "insufficient"

        return VehicleCompositionTrendResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_vehicles=total_vehicles,
            classes=items,
            data_status=status,
            provenance=prov,
        )

    # -------------------------------------------------------------------------
    # 4. Directional Trends Endpoint Logic
    # -------------------------------------------------------------------------
    @classmethod
    def get_directions(
        cls,
        db: Session,
        params: HistoricalFilterParams,
    ) -> DirectionalTrendResponse:
        """Computes directional split and trend metrics."""
        start_time, end_time = cls.resolve_time_window(params)
        sessions = cls.query_sessions(db, start_time, end_time, params)

        inbound_count = 0
        outbound_count = 0
        total_duration = 0.0

        for s in sessions:
            if s.traffic_metrics:
                m = s.traffic_metrics
                total_duration += m.observation_duration_seconds
                if m.direction_distribution and isinstance(m.direction_distribution, list):
                    for d in m.direction_distribution:
                        d_name = str(d.get("direction", "")).lower()
                        d_count = int(d.get("count", 0))
                        if d_name in ["inbound", "in", "northbound", "eastbound"]:
                            inbound_count += d_count
                        elif d_name in ["outbound", "out", "southbound", "westbound"]:
                            outbound_count += d_count
            else:
                total_duration += (s.completed_at - s.started_at).total_seconds() if s.completed_at else 0.0

        total_vehicles = inbound_count + outbound_count
        if total_vehicles == 0 and sessions:
            # Fallback to total counted
            counted = sum(s.total_vehicles_counted for s in sessions)
            if counted > 0:
                inbound_count = counted
                total_vehicles = counted

        in_pct = round((inbound_count / total_vehicles * 100.0), 1) if total_vehicles > 0 else 0.0
        out_pct = round((outbound_count / total_vehicles * 100.0), 1) if total_vehicles > 0 else 0.0
        ratio = round(inbound_count / outbound_count, 2) if outbound_count > 0 else (1.0 if inbound_count == 0 else 99.0)

        if in_pct > 60.0:
            trend_dir = "inbound_dominant"
        elif out_pct > 60.0:
            trend_dir = "outbound_dominant"
        else:
            trend_dir = "balanced"

        in_vph = round(inbound_count / (total_duration / 3600.0), 2) if total_duration > 0 else 0.0
        out_vph = round(outbound_count / (total_duration / 3600.0), 2) if total_duration > 0 else 0.0

        directions = [
            DirectionalFlowMetric(
                direction="inbound",
                count=inbound_count,
                percentage=in_pct,
                flow_rate_per_hour=in_vph,
            ),
            DirectionalFlowMetric(
                direction="outbound",
                count=outbound_count,
                percentage=out_pct,
                flow_rate_per_hour=out_vph,
            ),
        ]

        prov = cls.synthesize_provenance(sessions, total_duration, False)
        status = "observed" if total_vehicles > 0 else "insufficient"

        return DirectionalTrendResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_vehicles=total_vehicles,
            inbound_count=inbound_count,
            outbound_count=outbound_count,
            inbound_percentage=in_pct,
            outbound_percentage=out_pct,
            directional_ratio=ratio,
            trend_direction=trend_dir,
            directions=directions,
            data_status=status,
            provenance=prov,
        )

    # -------------------------------------------------------------------------
    # 5. Lane Intelligence Trends
    # -------------------------------------------------------------------------
    @classmethod
    def get_lanes(
        cls,
        db: Session,
        params: HistoricalFilterParams,
    ) -> LaneIntelligenceResponse:
        """Aggregates lane-level volume, occupancy, and image-space density history."""
        start_time, end_time = cls.resolve_time_window(params)
        sessions = cls.query_sessions(db, start_time, end_time, params)

        lane_data: Dict[str, Dict[str, Any]] = {}
        total_duration = 0.0
        total_all_lanes_volume = 0

        for s in sessions:
            if s.traffic_metrics:
                total_duration += s.traffic_metrics.observation_duration_seconds
            for lr in s.lane_results:
                lid = lr.lane_id
                if lid not in lane_data:
                    lane_data[lid] = {
                        "lane_id": lid,
                        "lane_name": lr.lane_name,
                        "direction_hint": lr.direction_hint,
                        "volume": 0,
                        "occupancies": [],
                        "peak_occupancies": [],
                        "densities": [],
                        "density_scores": [],
                        "density_unit": lr.density_unit,
                        "calibration_warning": lr.density_calibration_warning,
                        "session_count": 0,
                    }
                ld = lane_data[lid]
                ld["volume"] += lr.unique_vehicles_count
                ld["occupancies"].append(lr.average_occupancy)
                ld["peak_occupancies"].append(lr.peak_occupancy)
                ld["densities"].append(lr.image_space_density)
                ld["density_scores"].append(lr.normalized_density_score)
                ld["session_count"] += 1
                total_all_lanes_volume += lr.unique_vehicles_count

        lane_items: List[LaneIntelligenceItem] = []
        busiest_lane = None
        max_vol = -1
        highest_dens_lane = None
        max_dens = -1.0

        for lid, ld in lane_data.items():
            vol = ld["volume"]
            avg_occ = sum(ld["occupancies"]) / len(ld["occupancies"]) if ld["occupancies"] else 0.0
            peak_occ = max(ld["peak_occupancies"]) if ld["peak_occupancies"] else 0
            avg_dens = sum(ld["densities"]) / len(ld["densities"]) if ld["densities"] else 0.0
            avg_score = sum(ld["density_scores"]) / len(ld["density_scores"]) if ld["density_scores"] else 0.0
            share = round((vol / total_all_lanes_volume * 100.0), 1) if total_all_lanes_volume > 0 else 0.0

            if vol > max_vol:
                max_vol = vol
                busiest_lane = ld["lane_name"]
            if avg_score > max_dens:
                max_dens = avg_score
                highest_dens_lane = ld["lane_name"]

            lane_items.append(
                LaneIntelligenceItem(
                    lane_id=lid,
                    lane_name=ld["lane_name"],
                    direction_hint=ld["direction_hint"],
                    total_volume=vol,
                    average_occupancy=round(avg_occ, 2),
                    peak_occupancy=peak_occ,
                    average_density=round(avg_dens, 6),
                    normalized_density_score=round(avg_score, 3),
                    density_unit=ld["density_unit"],
                    density_calibration_warning=ld["calibration_warning"],
                    volume_share_pct=share,
                    session_count=ld["session_count"],
                )
            )

        # Sort lanes by volume descending
        lane_items.sort(key=lambda l: l.total_volume, reverse=True)
        prov = cls.synthesize_provenance(sessions, total_duration, False)
        status = "observed" if lane_items else "insufficient"

        return LaneIntelligenceResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_lanes=len(lane_items),
            lanes=lane_items,
            busiest_lane_name=busiest_lane,
            highest_density_lane_name=highest_dens_lane,
            data_status=status,
            provenance=prov,
        )

    # -------------------------------------------------------------------------
    # 6. Peak Periods Analysis with Deterministic Tie-Breaking
    # -------------------------------------------------------------------------
    @classmethod
    def get_peaks(
        cls,
        db: Session,
        params: HistoricalFilterParams,
    ) -> PeakPeriodsResponse:
        """
        Determines deterministic observed peak periods:
        1. Highest observed flow rate
        2. Highest observed volume
        3. Highest observed lane density
        Tie-breaking rule: Earlier start time wins; then longer duration wins.
        """
        start_time, end_time = cls.resolve_time_window(params)
        sessions = cls.query_sessions(db, start_time, end_time, params)

        if not sessions:
            prov = cls.synthesize_provenance([], 0.0, False)
            empty_item = PeakPeriodItem(
                peak_type="unavailable",
                title="No observed peak",
                value=0.0,
                unit="none",
                details="No sessions found in time range",
            )
            return PeakPeriodsResponse(
                time_range_start=start_time,
                time_range_end=end_time,
                peak_flow=empty_item,
                peak_volume=empty_item,
                peak_density=empty_item,
                tie_breaking_rule=TIE_BREAKING_RULE_DESC,
                data_status="insufficient",
                provenance=prov,
            )

        # 1. Peak Flow Rate (with tie-breaking: earlier start, then longer duration)
        best_flow_s = None
        best_flow_val = -1.0
        tie_applied_flow = False

        for s in sessions:
            if s.traffic_metrics:
                vph = s.traffic_metrics.flow_rate_per_hour
                dur = s.traffic_metrics.observation_duration_seconds
                if vph > best_flow_val:
                    best_flow_val = vph
                    best_flow_s = s
                    tie_applied_flow = False
                elif vph == best_flow_val and best_flow_s is not None:
                    # Tie-breaker: earlier started_at wins
                    if s.started_at < best_flow_s.started_at:
                        best_flow_s = s
                        tie_applied_flow = True
                    elif s.started_at == best_flow_s.started_at:
                        # Tie-breaker 2: longer duration wins
                        if dur > (best_flow_s.traffic_metrics.observation_duration_seconds if best_flow_s.traffic_metrics else 0):
                            best_flow_s = s
                            tie_applied_flow = True

        if best_flow_s and best_flow_s.traffic_metrics:
            m = best_flow_s.traffic_metrics
            s_name = best_flow_s.camera_source.name if best_flow_s.camera_source else (
                best_flow_s.video.original_filename if best_flow_s.video else "Session"
            )
            peak_flow = PeakPeriodItem(
                peak_type="flow_rate",
                title="Observed Peak Flow Rate",
                start_time=best_flow_s.started_at,
                end_time=best_flow_s.completed_at or (best_flow_s.started_at + timedelta(seconds=m.observation_duration_seconds)),
                value=round(m.flow_rate_per_hour, 1),
                unit="veh/hr",
                is_extrapolated=m.is_extrapolated,
                observation_duration_seconds=round(m.observation_duration_seconds, 1),
                session_id=best_flow_s.id,
                source_name=s_name,
                tie_breaking_applied=tie_applied_flow,
                details=f"Flow observed at {s_name} ({m.total_volume} veh over {m.observation_duration_seconds:.0f}s)",
            )
        else:
            peak_flow = PeakPeriodItem(
                peak_type="flow_rate",
                title="Peak Flow Rate",
                value=0.0,
                unit="veh/hr",
                details="No flow metrics recorded",
            )

        # 2. Peak Volume Period (with tie-breaking: earlier start, then longer duration)
        best_vol_s = None
        best_vol_val = -1
        tie_applied_vol = False

        for s in sessions:
            vol = s.traffic_metrics.total_volume if s.traffic_metrics else s.total_vehicles_counted
            dur = s.traffic_metrics.observation_duration_seconds if s.traffic_metrics else 0.0
            if vol > best_vol_val:
                best_vol_val = vol
                best_vol_s = s
                tie_applied_vol = False
            elif vol == best_vol_val and best_vol_s is not None:
                if s.started_at < best_vol_s.started_at:
                    best_vol_s = s
                    tie_applied_vol = True
                elif s.started_at == best_vol_s.started_at:
                    prev_dur = best_vol_s.traffic_metrics.observation_duration_seconds if best_vol_s.traffic_metrics else 0.0
                    if dur > prev_dur:
                        best_vol_s = s
                        tie_applied_vol = True

        if best_vol_s:
            s_name = best_vol_s.camera_source.name if best_vol_s.camera_source else (
                best_vol_s.video.original_filename if best_vol_s.video else "Session"
            )
            m_dur = best_vol_s.traffic_metrics.observation_duration_seconds if best_vol_s.traffic_metrics else 0.0
            peak_volume = PeakPeriodItem(
                peak_type="volume",
                title="Observed Peak Volume Period",
                start_time=best_vol_s.started_at,
                end_time=best_vol_s.completed_at or (best_vol_s.started_at + timedelta(seconds=m_dur)),
                value=float(best_vol_val),
                unit="vehicles",
                is_extrapolated=False,
                observation_duration_seconds=round(m_dur, 1),
                session_id=best_vol_s.id,
                source_name=s_name,
                tie_breaking_applied=tie_applied_vol,
                details=f"Highest count ({best_vol_val} vehicles) recorded at {s_name}",
            )
        else:
            peak_volume = PeakPeriodItem(
                peak_type="volume",
                title="Peak Volume Period",
                value=0.0,
                unit="vehicles",
                details="No volume recorded",
            )

        # 3. Peak Lane Density Period
        best_dens_lr = None
        best_dens_s = None
        best_dens_val = -1.0
        tie_applied_dens = False

        for s in sessions:
            for lr in s.lane_results:
                score = lr.normalized_density_score
                if score > best_dens_val:
                    best_dens_val = score
                    best_dens_lr = lr
                    best_dens_s = s
                    tie_applied_dens = False
                elif score == best_dens_val and best_dens_s is not None:
                    if s.started_at < best_dens_s.started_at:
                        best_dens_lr = lr
                        best_dens_s = s
                        tie_applied_dens = True

        if best_dens_lr and best_dens_s:
            s_name = best_dens_s.camera_source.name if best_dens_s.camera_source else (
                best_dens_s.video.original_filename if best_dens_s.video else "Session"
            )
            peak_density = PeakPeriodItem(
                peak_type="lane_density",
                title="Observed Peak Lane Density",
                start_time=best_dens_s.started_at,
                end_time=best_dens_s.completed_at,
                value=round(best_dens_val, 3),
                unit="score (0-1)",
                is_extrapolated=False,
                observation_duration_seconds=round(best_dens_s.traffic_metrics.observation_duration_seconds if best_dens_s.traffic_metrics else 0.0, 1),
                session_id=best_dens_s.id,
                source_name=s_name,
                lane_name=best_dens_lr.lane_name,
                tie_breaking_applied=tie_applied_dens,
                details=f"Peak lane density score {best_dens_val:.2f} observed in {best_dens_lr.lane_name} at {s_name}",
            )
        else:
            peak_density = PeakPeriodItem(
                peak_type="lane_density",
                title="Peak Lane Density",
                value=0.0,
                unit="score (0-1)",
                details="No lane density records found",
            )

        total_dur = sum((s.traffic_metrics.observation_duration_seconds if s.traffic_metrics else 0.0) for s in sessions)
        prov = cls.synthesize_provenance(sessions, total_dur, False)

        return PeakPeriodsResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            peak_flow=peak_flow,
            peak_volume=peak_volume,
            peak_density=peak_density,
            tie_breaking_rule=TIE_BREAKING_RULE_DESC,
            data_status="observed",
            provenance=prov,
        )

    # -------------------------------------------------------------------------
    # 7. Anomaly & Incident History Endpoint Logic
    # -------------------------------------------------------------------------
    @classmethod
    def get_anomalies(
        cls,
        db: Session,
        params: HistoricalFilterParams,
    ) -> AnomalyHistoryResponse:
        """Aggregates operational anomaly events and incident history."""
        start_time, end_time = cls.resolve_time_window(params)
        sessions = cls.query_sessions(db, start_time, end_time, params)

        if not sessions:
            prov = cls.synthesize_provenance([], 0.0, False)
            return AnomalyHistoryResponse(
                time_range_start=start_time,
                time_range_end=end_time,
                total_anomalies=0,
                active_anomalies=0,
                resolved_anomalies=0,
                by_type={},
                by_severity={},
                incidents=[],
                data_status="insufficient",
                provenance=prov,
            )

        session_map = {s.id: s for s in sessions}
        session_ids = list(session_map.keys())

        # Query anomalies in range linked to matching sessions
        anomalies = list(
            db.scalars(
                select(AnomalyEvent)
                .where(AnomalyEvent.session_id.in_(session_ids))
                .order_by(AnomalyEvent.created_at.desc())
                .limit(settings.max_historical_records)
            ).all()
        )

        by_type: Dict[str, int] = {}
        by_sev: Dict[str, int] = {}
        active_count = 0
        resolved_count = 0
        incidents: List[AnomalyHistoryItem] = []

        for a in anomalies:
            atype = a.anomaly_type
            asev = a.severity
            by_type[atype] = by_type.get(atype, 0) + 1
            by_sev[asev] = by_sev.get(asev, 0) + 1

            if a.status in ["open", "investigating"]:
                active_count += 1
            else:
                resolved_count += 1

            sess = session_map.get(a.session_id)
            sname = None
            if sess:
                sname = sess.camera_source.name if sess.camera_source else (
                    sess.video.original_filename if sess.video else "Video Session"
                )

            incidents.append(
                AnomalyHistoryItem(
                    id=a.id,
                    anomaly_type=a.anomaly_type,
                    severity=a.severity,
                    status=a.status,
                    title=a.title,
                    description=a.description,
                    metric_name=a.metric_name,
                    trigger_value=round(a.trigger_value, 2),
                    threshold_value=round(a.threshold_value, 2),
                    deviation_pct=round(a.deviation_pct, 1) if a.deviation_pct else None,
                    lane_id=a.lane_id,
                    session_id=a.session_id,
                    source_name=sname,
                    duration_seconds=round(a.duration_seconds, 1),
                    is_synthetic=a.is_synthetic,
                    created_at=a.created_at,
                )
            )

        total_dur = sum((s.traffic_metrics.observation_duration_seconds if s.traffic_metrics else 0.0) for s in sessions)
        prov = cls.synthesize_provenance(sessions, total_dur, False)

        return AnomalyHistoryResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_anomalies=len(anomalies),
            active_anomalies=active_count,
            resolved_anomalies=resolved_count,
            by_type=by_type,
            by_severity=by_sev,
            incidents=incidents,
            data_status="observed" if anomalies else "sparse",
            provenance=prov,
        )

    # -------------------------------------------------------------------------
    # 8. Source Comparison Endpoint Logic
    # -------------------------------------------------------------------------
    @classmethod
    def get_sources(
        cls,
        db: Session,
        params: HistoricalFilterParams,
    ) -> SourceComparisonResponse:
        """Per-source and per-camera aggregated comparison."""
        start_time, end_time = cls.resolve_time_window(params)
        sessions = cls.query_sessions(db, start_time, end_time, params)

        if not sessions:
            prov = cls.synthesize_provenance([], 0.0, False)
            return SourceComparisonResponse(
                time_range_start=start_time,
                time_range_end=end_time,
                total_sources=0,
                sources=[],
                busiest_source_name=None,
                data_status="insufficient",
                provenance=prov,
            )

        # Group sessions by source
        source_data: Dict[str, Dict[str, Any]] = {}
        for s in sessions:
            if s.camera_source_id and s.camera_source:
                src_key = s.camera_source_id
                src_name = s.camera_source.name
                src_type = s.camera_source.source_type
                loc = s.camera_source.location_name
                is_synth = src_type in ["test_fixture", "synthetic_test"]
            elif s.video:
                src_key = s.video.id
                src_name = s.video.original_filename
                src_type = s.video.source_type
                loc = "Uploaded File"
                is_synth = s.video.source_type != "real_world" or not s.video.provenance_verified
            else:
                src_key = s.id
                src_name = f"Session {s.id[:8]}"
                src_type = "file"
                loc = "Unknown"
                is_synth = False

            if src_key not in source_data:
                source_data[src_key] = {
                    "source_id": src_key,
                    "source_name": src_name,
                    "source_type": src_type,
                    "location_name": loc,
                    "session_count": 0,
                    "volume": 0,
                    "duration": 0.0,
                    "anomaly_count": 0,
                    "is_synthetic": is_synth,
                    "sessions": [],
                }

            sd = source_data[src_key]
            sd["session_count"] += 1
            sd["sessions"].append(s.id)
            if s.traffic_metrics:
                sd["volume"] += s.traffic_metrics.total_volume
                sd["duration"] += s.traffic_metrics.observation_duration_seconds
            else:
                sd["volume"] += s.total_vehicles_counted

        # Fetch anomaly counts per session
        all_s_ids = [s.id for s in sessions]
        anom_counts = dict(
            db.execute(
                select(AnomalyEvent.session_id, func.count(AnomalyEvent.id))
                .where(AnomalyEvent.session_id.in_(all_s_ids))
                .group_by(AnomalyEvent.session_id)
            ).all()
        )

        sources_list: List[SourceMetricItem] = []
        busiest_name = None
        max_vol = -1

        for src_key, sd in source_data.items():
            anom_sum = sum(anom_counts.get(sid, 0) for sid in sd["sessions"])
            vol = sd["volume"]
            dur = sd["duration"]
            flow_vph = (vol / (dur / 3600.0)) if dur > 0 else 0.0
            is_extrap = dur < 3600.0 and vol > 0
            label = "TEST FIXTURE" if sd["source_type"] == "test_fixture" else (
                "SYNTHETIC" if sd["is_synthetic"] else "REAL DATA"
            )

            if vol > max_vol:
                max_vol = vol
                busiest_name = sd["source_name"]

            sources_list.append(
                SourceMetricItem(
                    source_id=src_key,
                    source_name=sd["source_name"],
                    source_type=sd["source_type"],
                    location_name=sd["location_name"],
                    session_count=sd["session_count"],
                    total_volume=vol,
                    total_duration_seconds=round(dur, 1),
                    average_flow_rate_vph=round(flow_vph, 1),
                    is_extrapolated=is_extrap,
                    anomaly_count=anom_sum,
                    provenance_label=label,
                    is_synthetic=sd["is_synthetic"],
                )
            )

        sources_list.sort(key=lambda x: x.total_volume, reverse=True)
        total_dur = sum(sd["duration"] for sd in source_data.values())
        prov = cls.synthesize_provenance(sessions, total_dur, False)

        return SourceComparisonResponse(
            time_range_start=start_time,
            time_range_end=end_time,
            total_sources=len(sources_list),
            sources=sources_list,
            busiest_source_name=busiest_name,
            data_status="observed",
            provenance=prov,
        )

    # -------------------------------------------------------------------------
    # 9. Period-over-Period Comparison
    # -------------------------------------------------------------------------
    @classmethod
    def get_comparison(
        cls,
        db: Session,
        params: HistoricalFilterParams,
    ) -> PeriodComparisonResponse:
        """Period-over-period delta computation between current and preceding time windows."""
        curr_start, curr_end = cls.resolve_time_window(params)
        delta = curr_end - curr_start
        prev_start = curr_start - delta
        prev_end = curr_start

        # Query current period
        curr_sessions = cls.query_sessions(db, curr_start, curr_end, params)
        # Query previous period
        prev_params = params.model_copy()
        prev_params.start_time = prev_start
        prev_params.end_time = prev_end
        prev_params.time_preset = "custom"
        prev_sessions = cls.query_sessions(db, prev_start, prev_end, prev_params)

        def _compute_stats(sess_list: List[AnalysisSession]) -> Tuple[int, float, float, int]:
            vol = sum((s.traffic_metrics.total_volume if s.traffic_metrics else s.total_vehicles_counted) for s in sess_list)
            dur = sum((s.traffic_metrics.observation_duration_seconds if s.traffic_metrics else 0.0) for s in sess_list)
            flow = (vol / (dur / 3600.0)) if dur > 0 else 0.0
            return vol, dur, flow, len(sess_list)

        curr_vol, curr_dur, curr_flow, curr_sc = _compute_stats(curr_sessions)
        prev_vol, prev_dur, prev_flow, prev_sc = _compute_stats(prev_sessions)

        # Anomaly counts
        curr_ids = [s.id for s in curr_sessions]
        prev_ids = [s.id for s in prev_sessions]
        curr_anom = db.scalar(select(func.count(AnomalyEvent.id)).where(AnomalyEvent.session_id.in_(curr_ids))) if curr_ids else 0
        prev_anom = db.scalar(select(func.count(AnomalyEvent.id)).where(AnomalyEvent.session_id.in_(prev_ids))) if prev_ids else 0
        curr_anom = curr_anom or 0
        prev_anom = prev_anom or 0

        def _build_delta(metric_name: str, c_val: float, p_val: float) -> PeriodDeltaMetric:
            abs_change = round(c_val - p_val, 2)
            pct_change = round((abs_change / p_val * 100.0), 1) if p_val > 0 else None
            if abs_change > 0:
                trend = "up"
            elif abs_change < 0:
                trend = "down"
            else:
                trend = "neutral"
            return PeriodDeltaMetric(
                metric_name=metric_name,
                current_value=round(c_val, 2),
                previous_value=round(p_val, 2),
                absolute_change=abs_change,
                percentage_change=pct_change,
                trend_direction=trend,
            )

        vol_comp = _build_delta("Observed Volume", curr_vol, prev_vol)
        flow_comp = _build_delta("Flow Rate (veh/hr)", curr_flow, prev_flow)
        dur_comp = _build_delta("Observation Duration (s)", curr_dur, prev_dur)
        anom_comp = _build_delta("Incident Count", float(curr_anom), float(prev_anom))
        sess_comp = _build_delta("Analysis Sessions", float(curr_sc), float(prev_sc))

        prov = cls.synthesize_provenance(curr_sessions, curr_dur, False)
        status = "observed" if curr_sessions or prev_sessions else "insufficient"

        return PeriodComparisonResponse(
            current_start=curr_start,
            current_end=curr_end,
            previous_start=prev_start,
            previous_end=prev_end,
            volume_comparison=vol_comp,
            flow_rate_comparison=flow_comp,
            duration_comparison=dur_comp,
            anomaly_comparison=anom_comp,
            session_comparison=sess_comp,
            data_status=status,
            provenance=prov,
        )
