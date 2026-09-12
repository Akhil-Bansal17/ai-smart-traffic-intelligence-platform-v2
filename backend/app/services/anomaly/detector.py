"""
Traffic Anomaly & Congestion Incident Detection Service.
Phase 15: Traffic Anomaly & Congestion Incident Detection.

Analyzes persisted traffic metrics (flow, density, lane occupancy, class distribution)
to detect, categorize, and track operational traffic anomalies:
1. Congestion Buildup (sustained queue/occupancy above threshold)
2. Abnormal Flow Drop (sudden drop relative to baseline/recent interval)
3. Lane Imbalance (significant multi-lane occupancy/volume skew)
4. Density Spike (image-space density threshold breach)

Strictly rule- and statistics-based: zero black-box ML, zero fabrication.
Full provenance inheritance: anomalies inherit source video provenance and never upgrade trust level.
"""
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config.settings import settings
from app.core.logging import get_logger
from app.models.analysis import AnalysisSession, LaneResultRecord, TrafficMetricsRecord
from app.models.anomaly import AnomalyEvent
from app.models.video import Video
from app.schemas.anomaly import AnomalyRuleConfigSchema

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Helper returning timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class AnomalyDetectionService:
    """
    Service responsible for evaluating persisted traffic metrics against explainable
    statistical & rule-based anomaly detection criteria.
    """

    def __init__(
        self,
        congestion_occupancy_threshold: Optional[int] = None,
        congestion_min_duration_seconds: Optional[float] = None,
        congestion_density_score_threshold: Optional[float] = None,
        flow_drop_pct_threshold: Optional[float] = None,
        lane_imbalance_ratio_threshold: Optional[float] = None,
        lane_imbalance_min_volume: Optional[int] = None,
        density_spike_threshold: Optional[float] = None,
        min_buckets_for_baseline: Optional[int] = None,
    ):
        self.congestion_occupancy_threshold = (
            congestion_occupancy_threshold
            if congestion_occupancy_threshold is not None
            else settings.anomaly_congestion_occupancy_threshold
        )
        self.congestion_min_duration_seconds = (
            congestion_min_duration_seconds
            if congestion_min_duration_seconds is not None
            else settings.anomaly_congestion_min_duration_seconds
        )
        self.congestion_density_score_threshold = (
            congestion_density_score_threshold
            if congestion_density_score_threshold is not None
            else settings.anomaly_congestion_density_score_threshold
        )
        self.flow_drop_pct_threshold = (
            flow_drop_pct_threshold
            if flow_drop_pct_threshold is not None
            else settings.anomaly_flow_drop_pct_threshold
        )
        self.lane_imbalance_ratio_threshold = (
            lane_imbalance_ratio_threshold
            if lane_imbalance_ratio_threshold is not None
            else settings.anomaly_lane_imbalance_ratio_threshold
        )
        self.lane_imbalance_min_volume = (
            lane_imbalance_min_volume
            if lane_imbalance_min_volume is not None
            else settings.anomaly_lane_imbalance_min_volume
        )
        self.density_spike_threshold = (
            density_spike_threshold
            if density_spike_threshold is not None
            else settings.anomaly_density_spike_threshold
        )
        self.min_buckets_for_baseline = (
            min_buckets_for_baseline
            if min_buckets_for_baseline is not None
            else settings.anomaly_min_buckets_for_baseline
        )

    def get_rule_catalog(self) -> List[AnomalyRuleConfigSchema]:
        """Returns the complete rule catalog with current configuration thresholds."""
        return [
            AnomalyRuleConfigSchema(
                rule_name="Congestion Buildup Detection",
                anomaly_type="congestion_buildup",
                description="Flags sustained high vehicle occupancy or queue length within designated lanes or time windows.",
                threshold_value=float(self.congestion_occupancy_threshold),
                threshold_unit="vehicles (peak occupancy)",
                condition_description=(
                    f"Peak lane occupancy >= {self.congestion_occupancy_threshold} vehicles "
                    f"or normalized density score >= {self.congestion_density_score_threshold:.2f}."
                ),
                severity_criteria={
                    "low": "Peak occupancy = threshold (5–6 veh)",
                    "medium": "Peak occupancy 7–8 veh (+25% to +75%)",
                    "high": "Peak occupancy 9–12 veh (+75% to +150%)",
                    "critical": "Peak occupancy >= 13 veh (> +150%)",
                },
                caveats="Derived from discrete Kalman-tracked centroids in polygon regions.",
            ),
            AnomalyRuleConfigSchema(
                rule_name="Abnormal Flow Drop Detection",
                anomaly_type="abnormal_flow_drop",
                description="Identifies sudden collapse in vehicle flow rate relative to preceding intervals or session baseline.",
                threshold_value=float(self.flow_drop_pct_threshold),
                threshold_unit="percentage drop (%)",
                condition_description=f"Flow rate drops by >= {self.flow_drop_pct_threshold}% relative to baseline interval.",
                severity_criteria={
                    "low": "50% to 60% flow reduction",
                    "medium": "60% to 75% flow reduction",
                    "high": "75% to 90% flow reduction",
                    "critical": "> 90% flow collapse to near zero",
                },
                caveats=f"Requires at least {self.min_buckets_for_baseline} discrete time-series buckets to establish baseline.",
            ),
            AnomalyRuleConfigSchema(
                rule_name="Lane Utilization Imbalance",
                anomaly_type="lane_imbalance",
                description="Flags significant skew in vehicle distribution across multiple parallel approach lanes.",
                threshold_value=float(self.lane_imbalance_ratio_threshold),
                threshold_unit="occupancy ratio (max/min)",
                condition_description=(
                    f"Ratio of max lane volume to min lane volume >= {self.lane_imbalance_ratio_threshold}x "
                    f"when total volume >= {self.lane_imbalance_min_volume}."
                ),
                severity_criteria={
                    "low": "Ratio 3.0x to 4.0x",
                    "medium": "Ratio 4.0x to 6.0x",
                    "high": "Ratio 6.0x to 10.0x",
                    "critical": "Ratio > 10.0x severe bottleneck",
                },
                caveats="Applicable only to multi-lane configurations (>= 2 configured polygon lanes).",
            ),
            AnomalyRuleConfigSchema(
                rule_name="Image-Space Density Spike",
                anomaly_type="density_spike",
                description="Flags sudden high spatial density concentration in camera image plane.",
                threshold_value=float(self.density_spike_threshold),
                threshold_unit="vehicles/px²",
                condition_description=f"Image-space density >= {self.density_spike_threshold:.6f} vehicles/px².",
                severity_criteria={
                    "low": "1.0x to 1.3x threshold",
                    "medium": "1.3x to 1.8x threshold",
                    "high": "1.8x to 2.5x threshold",
                    "critical": "> 2.5x threshold extreme density",
                },
                caveats="Image-space density (vehicles/px²) is uncalibrated camera perspective, not physical veh/km².",
            ),
        ]

    def _resolve_provenance(self, session: AnalysisSession) -> Tuple[str, bool]:
        """
        Derives inherited provenance from the session's video source.
        Real data qualification strictly requires source_type='real_world' AND provenance_verified=True AND source_reference.
        Never upgrades trust level.
        """
        video: Optional[Video] = session.video
        if (
            video
            and video.source_type == "real_world"
            and video.provenance_verified is True
            and video.source_reference is not None
            and len(str(video.source_reference).strip()) > 0
        ):
            return "real_database_metrics", False
        elif video and video.source_type in ["synthetic_test", "synthetic_pipeline"]:
            return "synthetic_pipeline_metrics", True
        else:
            return "synthetic_fixture", True

    def detect_for_session(
        self,
        session: AnalysisSession,
    ) -> List[Dict[str, Any]]:
        """
        Runs all 4 rule checks against session metrics and returns raw detected candidates.
        Does not perform DB commits.
        """
        candidates: List[Dict[str, Any]] = []
        metrics: Optional[TrafficMetricsRecord] = session.traffic_metrics
        lanes: List[LaneResultRecord] = session.lane_results or []
        obs_duration = metrics.observation_duration_seconds if metrics else 0.0

        provenance_cat, is_synthetic = self._resolve_provenance(session)

        # -------------------------------------------------------------
        # Rule 1: Congestion Buildup
        # -------------------------------------------------------------
        for lane in lanes:
            if (
                lane.peak_occupancy >= self.congestion_occupancy_threshold
                or lane.normalized_density_score >= self.congestion_density_score_threshold
            ):
                # Calculate severity
                peak = lane.peak_occupancy
                thresh = self.congestion_occupancy_threshold
                dev_pct = round(((peak - thresh) / max(thresh, 1)) * 100.0, 1)

                if peak >= thresh + 8 or lane.normalized_density_score >= 0.98:
                    severity = "critical"
                elif peak >= thresh + 4 or lane.normalized_density_score >= 0.90:
                    severity = "high"
                elif peak >= thresh + 2 or lane.normalized_density_score >= 0.80:
                    severity = "medium"
                else:
                    severity = "low"

                candidates.append({
                    "session_id": session.id,
                    "anomaly_type": "congestion_buildup",
                    "severity": severity,
                    "status": "open",
                    "title": f"Congestion Buildup on {lane.lane_name}",
                    "description": (
                        f"Lane '{lane.lane_name}' reached a peak occupancy of {peak} vehicles "
                        f"(threshold: {thresh}) with normalized density score of {lane.normalized_density_score:.2f}."
                    ),
                    "start_timestamp_seconds": 0.0,
                    "end_timestamp_seconds": obs_duration,
                    "duration_seconds": obs_duration,
                    "metric_name": "peak_occupancy",
                    "trigger_value": float(peak),
                    "baseline_value": float(lane.average_occupancy),
                    "threshold_value": float(thresh),
                    "deviation_pct": max(dev_pct, 0.0),
                    "lane_id": lane.lane_id,
                    "provenance_category": provenance_cat,
                    "is_synthetic": is_synthetic,
                    "details_json": {
                        "condition_state": "active",
                        "lane_name": lane.lane_name,
                        "peak_occupancy": peak,
                        "average_occupancy": lane.average_occupancy,
                        "normalized_density_score": lane.normalized_density_score,
                        "polygon_area_px2": lane.polygon_area_px2,
                    },
                })

        # -------------------------------------------------------------
        # Rule 2: Abnormal Flow Drop
        # -------------------------------------------------------------
        if metrics and metrics.time_series_buckets and len(metrics.time_series_buckets) >= self.min_buckets_for_baseline:
            buckets = metrics.time_series_buckets
            # Calculate non-zero baseline flow
            counts = [float(b.get("count", b.get("vehicle_count", 0))) for b in buckets]
            for i in range(1, len(buckets)):
                prev_count = counts[i - 1]
                curr_count = counts[i]

                if prev_count >= 2.0:
                    drop_pct = ((prev_count - curr_count) / prev_count) * 100.0
                    if drop_pct >= self.flow_drop_pct_threshold:
                        if drop_pct >= 90.0:
                            severity = "critical"
                        elif drop_pct >= 75.0:
                            severity = "high"
                        elif drop_pct >= 60.0:
                            severity = "medium"
                        else:
                            severity = "low"

                        start_t = float(buckets[i].get("start_time_seconds", 0.0))
                        end_t = float(buckets[i].get("end_time_seconds", start_t + 10.0))
                        dur = max(end_t - start_t, 10.0)

                        candidates.append({
                            "session_id": session.id,
                            "anomaly_type": "abnormal_flow_drop",
                            "severity": severity,
                            "status": "open",
                            "title": f"Sudden Traffic Flow Drop at {start_t:.0f}s",
                            "description": (
                                f"Traffic flow collapsed by {drop_pct:.1f}% (from {prev_count:.0f} to {curr_count:.0f} vehicles) "
                                f"during time bucket interval [{start_t:.1f}s, {end_t:.1f}s]."
                            ),
                            "start_timestamp_seconds": start_t,
                            "end_timestamp_seconds": end_t,
                            "duration_seconds": dur,
                            "metric_name": "vehicle_flow_count",
                            "trigger_value": curr_count,
                            "baseline_value": prev_count,
                            "threshold_value": float(self.flow_drop_pct_threshold),
                            "deviation_pct": round(drop_pct, 1),
                            "lane_id": None,
                            "provenance_category": provenance_cat,
                            "is_synthetic": is_synthetic,
                            "details_json": {
                                "condition_state": "active",
                                "bucket_index": i,
                                "previous_bucket_count": prev_count,
                                "current_bucket_count": curr_count,
                                "drop_percentage": round(drop_pct, 1),
                            },
                        })

        # -------------------------------------------------------------
        # Rule 3: Lane Imbalance (multi-lane configurations)
        # -------------------------------------------------------------
        if len(lanes) >= 2:
            lane_counts = [(l.lane_id, l.lane_name, l.unique_vehicles_count) for l in lanes]
            lane_counts.sort(key=lambda x: x[2], reverse=True)
            max_lane = lane_counts[0]
            min_lane = lane_counts[-1]

            total_vehicles = sum(c[2] for c in lane_counts)
            if total_vehicles >= self.lane_imbalance_min_volume:
                ratio = max_lane[2] / max(min_lane[2], 1)
                if ratio >= self.lane_imbalance_ratio_threshold:
                    if ratio >= 10.0:
                        severity = "critical"
                    elif ratio >= 6.0:
                        severity = "high"
                    elif ratio >= 4.0:
                        severity = "medium"
                    else:
                        severity = "low"

                    dev_pct = round(((ratio - self.lane_imbalance_ratio_threshold) / self.lane_imbalance_ratio_threshold) * 100.0, 1)

                    candidates.append({
                        "session_id": session.id,
                        "anomaly_type": "lane_imbalance",
                        "severity": severity,
                        "status": "open",
                        "title": f"Lane Flow Imbalance ({max_lane[1]} vs {min_lane[1]})",
                        "description": (
                            f"Significant lane occupancy skew detected: '{max_lane[1]}' processed {max_lane[2]} vehicles "
                            f"while '{min_lane[1]}' processed only {min_lane[2]} vehicles (skew ratio: {ratio:.1f}x, threshold: {self.lane_imbalance_ratio_threshold:.1f}x)."
                        ),
                        "start_timestamp_seconds": 0.0,
                        "end_timestamp_seconds": obs_duration,
                        "duration_seconds": obs_duration,
                        "metric_name": "lane_skew_ratio",
                        "trigger_value": round(ratio, 2),
                        "baseline_value": 1.0,
                        "threshold_value": float(self.lane_imbalance_ratio_threshold),
                        "deviation_pct": dev_pct,
                        "lane_id": max_lane[0],
                        "provenance_category": provenance_cat,
                        "is_synthetic": is_synthetic,
                        "details_json": {
                            "condition_state": "active",
                            "dominant_lane_id": max_lane[0],
                            "dominant_lane_name": max_lane[1],
                            "dominant_lane_count": max_lane[2],
                            "starved_lane_id": min_lane[0],
                            "starved_lane_name": min_lane[1],
                            "starved_lane_count": min_lane[2],
                            "skew_ratio": round(ratio, 2),
                        },
                    })

        # -------------------------------------------------------------
        # Rule 4: Image-Space Density Spike
        # -------------------------------------------------------------
        for lane in lanes:
            if lane.image_space_density >= self.density_spike_threshold:
                density = lane.image_space_density
                thresh = self.density_spike_threshold
                multiplier = density / thresh
                dev_pct = round(((density - thresh) / thresh) * 100.0, 1)

                if multiplier >= 2.5:
                    severity = "critical"
                elif multiplier >= 1.8:
                    severity = "high"
                elif multiplier >= 1.3:
                    severity = "medium"
                else:
                    severity = "low"

                candidates.append({
                    "session_id": session.id,
                    "anomaly_type": "density_spike",
                    "severity": severity,
                    "status": "open",
                    "title": f"Image-Space Density Spike on {lane.lane_name}",
                    "description": (
                        f"Image-space density peaked at {density:.6f} vehicles/px² (threshold: {thresh:.6f} vehicles/px²). "
                        "Notice: uncalibrated camera perspective, not physical vehicles/km²."
                    ),
                    "start_timestamp_seconds": 0.0,
                    "end_timestamp_seconds": obs_duration,
                    "duration_seconds": obs_duration,
                    "metric_name": "image_space_density",
                    "trigger_value": float(density),
                    "baseline_value": float(thresh),
                    "threshold_value": float(thresh),
                    "deviation_pct": dev_pct,
                    "lane_id": lane.lane_id,
                    "provenance_category": provenance_cat,
                    "is_synthetic": is_synthetic,
                    "details_json": {
                        "condition_state": "active",
                        "lane_name": lane.lane_name,
                        "image_space_density": density,
                        "density_multiplier": round(multiplier, 2),
                        "density_unit": "vehicles/px²",
                        "calibration_warning": lane.density_calibration_warning,
                    },
                })

        return candidates

    def detect_and_persist_for_session(
        self,
        db: Session,
        session_id: str,
    ) -> List[AnomalyEvent]:
        """
        Executes idempotent anomaly detection for a specific session and persists events.
        Implements Start / Continuation / Recovery lifecycle semantics.
        """
        session_stmt = (
            select(AnalysisSession)
            .options(
                joinedload(AnalysisSession.video),
                selectinload(AnalysisSession.traffic_metrics),
                selectinload(AnalysisSession.lane_results),
            )
            .where(AnalysisSession.id == session_id)
        )
        session = db.scalar(session_stmt)
        if not session:
            logger.warning("Session not found for anomaly detection", session_id=session_id)
            return []

        # Find existing events for this session
        existing_events = list(
            db.scalars(
                select(AnomalyEvent).where(AnomalyEvent.session_id == session_id)
            ).all()
        )
        existing_map = {
            (e.anomaly_type, e.lane_id, round(e.start_timestamp_seconds, 1)): e
            for e in existing_events
        }

        candidates = self.detect_for_session(session)
        persisted_events: List[AnomalyEvent] = []
        candidate_keys = set()
        now = utcnow()

        for cand in candidates:
            key = (
                cand["anomaly_type"],
                cand["lane_id"],
                round(cand["start_timestamp_seconds"], 1),
            )
            candidate_keys.add(key)
            if key in existing_map:
                # Continuation: update existing event
                event = existing_map[key]
                event.trigger_value = cand["trigger_value"]
                event.deviation_pct = cand["deviation_pct"]
                event.duration_seconds = cand["duration_seconds"]
                event.end_timestamp_seconds = cand["end_timestamp_seconds"]
                event.severity = cand["severity"]
                event.description = cand["description"]
                existing_details = dict(event.details_json or {})
                existing_details.update(cand["details_json"])
                existing_details["condition_state"] = "ongoing"
                event.details_json = existing_details
                event.updated_at = now
                persisted_events.append(event)
            else:
                # Start: create new open event
                event = AnomalyEvent(
                    session_id=cand["session_id"],
                    anomaly_type=cand["anomaly_type"],
                    severity=cand["severity"],
                    status=cand["status"],
                    title=cand["title"],
                    description=cand["description"],
                    start_timestamp_seconds=cand["start_timestamp_seconds"],
                    end_timestamp_seconds=cand["end_timestamp_seconds"],
                    duration_seconds=cand["duration_seconds"],
                    metric_name=cand["metric_name"],
                    trigger_value=cand["trigger_value"],
                    baseline_value=cand["baseline_value"],
                    threshold_value=cand["threshold_value"],
                    deviation_pct=cand["deviation_pct"],
                    lane_id=cand["lane_id"],
                    provenance_category=cand["provenance_category"],
                    is_synthetic=cand["is_synthetic"],
                    details_json=cand["details_json"],
                    created_at=now,
                    updated_at=now,
                )
                db.add(event)
                persisted_events.append(event)

        # Recovery check: mark previously active conditions as recovered if no longer triggered
        for key, existing_event in existing_map.items():
            if key not in candidate_keys:
                details = dict(existing_event.details_json or {})
                if details.get("condition_state") != "recovered":
                    details["condition_state"] = "recovered"
                    details["recovered_at"] = now.isoformat()
                    existing_event.details_json = details
                    existing_event.updated_at = now

        db.commit()
        for e in persisted_events:
            db.refresh(e)

        logger.info(
            f"Completed anomaly detection for session {session_id}: {len(persisted_events)} anomalies detected"
        )
        return persisted_events
