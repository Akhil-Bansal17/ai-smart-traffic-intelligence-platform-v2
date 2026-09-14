"""
Decision Intelligence Engine: Deterministic Insight Generation & Lifecycle Orchestrator.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.

Orchestrates deterministic rule evaluation, evidence packaging, severity assessment,
deduplication, and persistence over persisted analytical outputs.
Consumes database records only — zero heavy CV / ByteTrack / YOLO execution.
"""
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.analysis import AnalysisSession, LaneResultRecord, TrafficMetricsRecord
from app.models.anomaly import AnomalyEvent
from app.models.corridor_simulation import EmergencyCorridorSimulationRun
from app.models.insight import (
    InsightCategory,
    InsightSeverity,
    InsightStatus,
    TrafficInsight,
)
from app.models.simulation import SignalSimulationRun
from app.models.video import Video
from app.schemas.insight import (
    InsightCategoryInfo,
    InsightInfoResponse,
    InsightSeverityInfo,
)
from app.services.insights.rules import (
    InsightCandidate,
    evaluate_congestion,
    evaluate_density_spike,
    evaluate_flow_degradation,
    evaluate_lane_imbalance,
    evaluate_operational_recommendation,
    evaluate_traffic_surge,
    evaluate_underutilized_lane,
)

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Helper returning timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class DecisionIntelligenceEngine:
    """
    Deterministic Decision Intelligence Engine.
    Interprets persisted analytical outputs into explainable traffic insights.
    """

    def __init__(self):
        pass

    def get_info_catalog(self) -> InsightInfoResponse:
        """Returns catalog describing supported insight categories, severities, and policies."""
        categories = [
            InsightCategoryInfo(
                category=InsightCategory.CONGESTION.value,
                description="Flags sustained high vehicle occupancy, queuing, or high normalized density on approach lanes.",
                supported_signals=["peak_occupancy", "normalized_density_score", "anomaly_congestion_buildup"],
                sample_title="Sustained Congestion on Lane 1",
            ),
            InsightCategoryInfo(
                category=InsightCategory.FLOW_DEGRADATION.value,
                description="Identifies acute drops in vehicle flow rate across discrete time-series observation intervals.",
                supported_signals=["time_series_buckets", "flow_drop_pct", "anomaly_abnormal_flow_drop"],
                sample_title="Sudden Flow Collapse (65% reduction)",
            ),
            InsightCategoryInfo(
                category=InsightCategory.LANE_IMBALANCE.value,
                description="Detects severe volume or occupancy skew across adjacent parallel approach lanes.",
                supported_signals=["lane_skew_ratio", "multi_lane_polygon_occupancy", "anomaly_lane_imbalance"],
                sample_title="Lane Utilization Skew (Lane 1 vs Lane 2)",
            ),
            InsightCategoryInfo(
                category=InsightCategory.DENSITY_SPIKE.value,
                description="Flags sudden high spatial vehicle concentration in the 2D camera image plane.",
                supported_signals=["image_space_density", "polygon_area_px2", "anomaly_density_spike"],
                sample_title="Image-Space Density Spike on Lane 2",
            ),
            InsightCategoryInfo(
                category=InsightCategory.TRAFFIC_SURGE.value,
                description="Identifies volume surges or elevated proportions of heavy commercial vehicles (buses/trucks).",
                supported_signals=["flow_rate_per_minute", "class_distribution", "heavy_vehicle_percentage"],
                sample_title="Traffic Volume / Fleet Composition Surge",
            ),
            InsightCategoryInfo(
                category=InsightCategory.UNDERUTILIZED_LANE.value,
                description="Highlights approach lanes operating significantly below throughput capacity despite corridor demand.",
                supported_signals=["unique_vehicles_count", "average_occupancy", "lane_volume_ratio"],
                sample_title="Underutilized Capacity on Lane 3",
            ),
            InsightCategoryInfo(
                category=InsightCategory.OPERATIONAL_RECOMMENDATION.value,
                description="Synthesizes actionable advisory guidance incorporating signal timing and corridor simulation models.",
                supported_signals=["signal_simulation_runs", "emergency_corridor_simulations"],
                sample_title="Coordinated Progression Advisory (Downtown Arterial)",
            ),
        ]

        severities = [
            InsightSeverityInfo(
                severity=InsightSeverity.CRITICAL.value,
                criteria="Extreme threshold breach (> 150% above threshold, > 90% flow collapse, or > 10x skew).",
                color_hint="rose-500",
            ),
            InsightSeverityInfo(
                severity=InsightSeverity.HIGH.value,
                criteria="Major operational impact (+75% to +150% occupancy, 75–90% flow drop, or 6x–10x skew).",
                color_hint="amber-500",
            ),
            InsightSeverityInfo(
                severity=InsightSeverity.MEDIUM.value,
                criteria="Moderate condition (+25% to +75% occupancy, 60–75% flow drop, or 4x–6x skew).",
                color_hint="yellow-500",
            ),
            InsightSeverityInfo(
                severity=InsightSeverity.LOW.value,
                criteria="Threshold boundary trigger (5–6 veh occupancy, 50–60% flow drop, or 3x–4x skew).",
                color_hint="cyan-500",
            ),
            InsightSeverityInfo(
                severity=InsightSeverity.INFO.value,
                criteria="Informational observation, underutilized lane capacity, or simulation advisory.",
                color_hint="blue-400",
            ),
        ]

        boundaries = {
            "ml_model_scope": "Deterministic interpretation rules only; zero unverified ML forecasting or LLM fabrication.",
            "cv_pipeline_scope": "Consumes persisted database records; never triggers video decoding, YOLO, or ByteTrack.",
            "signal_control_scope": "Advisory decision-support only; platform does not directly actuate physical traffic controllers.",
            "simulation_labeling": "All simulation benefits are explicitly phrased as 'simulation indicates', never as field observations.",
            "prediction_boundary": "Prediction evidence is marked unavailable (N < 20 sample threshold) per Phase 11 trust boundary.",
        }

        anti_fab = [
            "Observed and Inferred statements are strictly partitioned with separate schemas and UI indicators.",
            "Unavailable telemetry (speed radar, field controllers, forecasts) is represented honestly as unavailable.",
            "Short observation clips (< 3600s) are transparently labeled as extrapolated.",
            "Image-space density (veh/px²) is explicitly declared as uncalibrated camera perspective.",
            "Deterministic generation ensures identical inputs produce identical insight outputs.",
        ]

        return InsightInfoResponse(
            categories=categories,
            severity_levels=severities,
            architectural_boundaries=boundaries,
            anti_fabrication_policies=anti_fab,
        )

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

    def generate_for_session(
        self,
        db: Session,
        session_id: str,
        job_id: Optional[str] = None,
        force_recompute: bool = False,
    ) -> List[TrafficInsight]:
        """
        Executes deterministic insight generation for an AnalysisSession and persists records.
        Implements strict deduplication, Observed vs Inferred separation, and honest evidence packaging.
        """
        start_time = time.perf_counter()

        # 1. Eagerly load AnalysisSession and all child records in a single query
        session_stmt = (
            select(AnalysisSession)
            .options(
                joinedload(AnalysisSession.video),
                selectinload(AnalysisSession.traffic_metrics),
                selectinload(AnalysisSession.lane_results),
                selectinload(AnalysisSession.anomaly_events),
            )
            .where(AnalysisSession.id == session_id)
        )
        session = db.scalar(session_stmt)
        if not session:
            logger.warning("Session not found for insight generation: %s", session_id)
            raise AppException(f"Analysis session '{session_id}' not found.", code="session_not_found", status_code=404)

        metrics: Optional[TrafficMetricsRecord] = session.traffic_metrics
        lanes: List[LaneResultRecord] = session.lane_results or []
        anomalies: List[AnomalyEvent] = session.anomaly_events or []

        # 2. Query correlated simulation runs (if any)
        signal_sims = list(
            db.scalars(
                select(SignalSimulationRun).where(SignalSimulationRun.session_id == session_id)
            ).all()
        )
        corridor_sims = list(
            db.scalars(
                select(EmergencyCorridorSimulationRun)
            ).all()
        )

        prov_cat, is_synth = self._resolve_provenance(session)

        # 3. Deterministic Candidate Evaluation across all 7 Categories
        candidates: List[InsightCandidate] = []

        # Category 1: Congestion
        candidates.extend(
            evaluate_congestion(
                session, metrics, lanes, anomalies, signal_sims, corridor_sims, prov_cat, is_synth, job_id
            )
        )

        # Category 2: Flow Degradation
        candidates.extend(
            evaluate_flow_degradation(
                session, metrics, lanes, anomalies, signal_sims, corridor_sims, prov_cat, is_synth, job_id
            )
        )

        # Category 3: Lane Imbalance
        candidates.extend(
            evaluate_lane_imbalance(
                session, metrics, lanes, anomalies, signal_sims, corridor_sims, prov_cat, is_synth, job_id
            )
        )

        # Category 4: Density Spike
        candidates.extend(
            evaluate_density_spike(
                session, metrics, lanes, anomalies, signal_sims, corridor_sims, prov_cat, is_synth, job_id
            )
        )

        # Category 5: Traffic Surge
        candidates.extend(
            evaluate_traffic_surge(
                session, metrics, lanes, anomalies, signal_sims, corridor_sims, prov_cat, is_synth, job_id
            )
        )

        # Category 6: Underutilized Lane
        candidates.extend(
            evaluate_underutilized_lane(
                session, metrics, lanes, anomalies, signal_sims, corridor_sims, prov_cat, is_synth, job_id
            )
        )

        # Category 7: Operational Recommendation (Holistic)
        candidates.extend(
            evaluate_operational_recommendation(
                session, metrics, lanes, anomalies, signal_sims, corridor_sims, candidates, prov_cat, is_synth, job_id
            )
        )

        # 4. Load Existing Insights for this Session
        existing_insights = list(
            db.scalars(
                select(TrafficInsight).where(TrafficInsight.session_id == session_id)
            ).all()
        )
        existing_map: Dict[str, TrafficInsight] = {
            ins.dedup_signature: ins for ins in existing_insights
        }

        now = utcnow()
        persisted_insights: List[TrafficInsight] = []
        candidate_signatures = set()

        # 5. Deduplication & Continuation Logic
        for cand in candidates:
            candidate_signatures.add(cand.dedup_signature)
            if cand.dedup_signature in existing_map:
                existing_ins = existing_map[cand.dedup_signature]
                # If existing is DISMISSED and force_recompute is False, leave as dismissed
                if existing_ins.status == InsightStatus.DISMISSED.value and not force_recompute:
                    persisted_insights.append(existing_ins)
                    continue

                # Update existing insight with latest observations & metrics
                existing_ins.severity = cand.severity
                existing_ins.title = cand.title
                existing_ins.summary = cand.summary
                existing_ins.duration_seconds = cand.duration_seconds
                existing_ins.end_timestamp_seconds = cand.end_timestamp_seconds
                existing_ins.root_cause_observed = cand.root_cause_observed
                existing_ins.root_cause_inferred = cand.root_cause_inferred
                existing_ins.recommendation = cand.recommendation
                existing_ins.recommendation_rationale = cand.recommendation_rationale
                existing_ins.recommendation_type = cand.recommendation_type
                existing_ins.evidence_package = cand.evidence_package
                existing_ins.limitations = cand.limitations
                existing_ins.status = InsightStatus.ACTIVE.value
                existing_ins.updated_at = now
                persisted_insights.append(existing_ins)
            else:
                # Create new insight
                new_ins = TrafficInsight(
                    session_id=cand.session_id,
                    job_id=cand.job_id,
                    insight_type=cand.insight_type,
                    category=cand.category,
                    severity=cand.severity,
                    status=InsightStatus.ACTIVE.value,
                    title=cand.title,
                    summary=cand.summary,
                    start_timestamp_seconds=cand.start_timestamp_seconds,
                    end_timestamp_seconds=cand.end_timestamp_seconds,
                    duration_seconds=cand.duration_seconds,
                    affected_lane_id=cand.affected_lane_id,
                    affected_lane_name=cand.affected_lane_name,
                    root_cause_observed=cand.root_cause_observed,
                    root_cause_inferred=cand.root_cause_inferred,
                    recommendation=cand.recommendation,
                    recommendation_rationale=cand.recommendation_rationale,
                    recommendation_type=cand.recommendation_type,
                    evidence_package=cand.evidence_package,
                    limitations=cand.limitations,
                    provenance_category=cand.provenance_category,
                    is_synthetic=cand.is_synthetic,
                    dedup_signature=cand.dedup_signature,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_ins)
                persisted_insights.append(new_ins)

        # 6. Recovery Check: Mark previously active insights as RECOVERED if no longer triggered
        for sig, existing_ins in existing_map.items():
            if sig not in candidate_signatures and existing_ins.status == InsightStatus.ACTIVE.value:
                existing_ins.status = InsightStatus.RECOVERED.value
                existing_ins.resolved_at = now
                existing_ins.updated_at = now

        db.commit()
        for ins in persisted_insights:
            db.refresh(ins)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(
            f"Decision intelligence generation complete for session {session_id}: "
            f"{len(persisted_insights)} insights generated/updated in {elapsed_ms:.2f}ms"
        )
        return persisted_insights
