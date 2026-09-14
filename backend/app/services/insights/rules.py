"""
Deterministic Rule Evaluators for Traffic Decision Intelligence.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.

Evaluates persisted analytical records and maps conditions to structured insight candidates.
Strictly deterministic: identical input data produces identical insight candidates.
"""
from dataclasses import dataclass, field
import hashlib
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.models.analysis import AnalysisSession, LaneResultRecord, TrafficMetricsRecord
from app.models.anomaly import AnomalyEvent
from app.models.corridor_simulation import EmergencyCorridorSimulationRun
from app.models.insight import (
    InsightCategory,
    InsightSeverity,
    InsightStatus,
    RecommendationType,
)
from app.models.simulation import SignalSimulationRun
from app.services.insights.evidence import build_evidence_package, build_limitations_list
from app.services.insights.recommendations import (
    generate_congestion_recommendation,
    generate_corridor_coordination_recommendation,
    generate_density_spike_recommendation,
    generate_flow_drop_recommendation,
    generate_lane_imbalance_recommendation,
    generate_signal_optimization_recommendation,
    generate_traffic_surge_recommendation,
    generate_underutilized_lane_recommendation,
)
from app.services.insights.root_cause import make_inferred, make_observed
from app.services.insights.severity import (
    evaluate_congestion_severity,
    evaluate_density_spike_severity,
    evaluate_flow_drop_severity,
    evaluate_lane_imbalance_severity,
    evaluate_traffic_surge_severity,
)


@dataclass
class InsightCandidate:
    """Intermediate candidate representation before persistence."""
    session_id: str
    job_id: Optional[str]
    insight_type: str
    category: str
    severity: str
    status: str
    title: str
    summary: str
    start_timestamp_seconds: float
    end_timestamp_seconds: Optional[float]
    duration_seconds: float
    affected_lane_id: Optional[str]
    affected_lane_name: Optional[str]
    root_cause_observed: List[Dict[str, Any]]
    root_cause_inferred: List[Dict[str, Any]]
    recommendation: Optional[str]
    recommendation_rationale: Optional[str]
    recommendation_type: str
    evidence_package: Dict[str, Any]
    limitations: List[str]
    provenance_category: str
    is_synthetic: bool
    dedup_signature: str


def compute_dedup_signature(
    session_id: str,
    insight_type: str,
    affected_lane_id: Optional[str] = None,
    time_bin: float = 0.0,
) -> str:
    """
    Computes a deterministic deduplication signature.
    Prevents duplicate insertions for identical observation contexts.
    """
    lane_key = affected_lane_id or "none"
    bin_key = f"{round(time_bin, 1)}"
    raw = f"{session_id}:{insight_type}:{lane_key}:{bin_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


# ==============================================================================
# Rule 1: CONGESTION
# ==============================================================================
def evaluate_congestion(
    session: AnalysisSession,
    metrics: Optional[TrafficMetricsRecord],
    lanes: List[LaneResultRecord],
    anomalies: List[AnomalyEvent],
    signal_sims: List[SignalSimulationRun],
    corridor_sims: List[EmergencyCorridorSimulationRun],
    prov_cat: str,
    is_synth: bool,
    job_id: Optional[str] = None,
) -> List[InsightCandidate]:
    candidates: List[InsightCandidate] = []
    obs_dur = metrics.observation_duration_seconds if metrics else 0.0
    thresh_occ = settings.insight_congestion_occupancy_threshold
    thresh_dens = settings.insight_congestion_density_score_threshold

    # Correlate Phase 15 congestion anomalies
    congestion_anomalies = [a for a in anomalies if a.anomaly_type == "congestion_buildup"]

    for lane in lanes:
        condition_met = (
            lane.peak_occupancy >= thresh_occ
            or lane.normalized_density_score >= thresh_dens
            or any(a.lane_id == lane.lane_id for a in congestion_anomalies)
        )

        if condition_met:
            severity = evaluate_congestion_severity(
                peak_occupancy=lane.peak_occupancy,
                threshold=thresh_occ,
                density_score=lane.normalized_density_score,
            )

            rec_text, rec_rat, rec_type = generate_congestion_recommendation(
                lane_name=lane.lane_name,
                peak_occupancy=lane.peak_occupancy,
                density_score=lane.normalized_density_score,
                signal_sim_runs=signal_sims,
            )

            observed = [
                make_observed(
                    f"Lane '{lane.lane_name}' recorded peak occupancy of {lane.peak_occupancy} vehicles.",
                    metric="peak_occupancy",
                    value=lane.peak_occupancy,
                    unit="vehicles",
                ),
                make_observed(
                    f"Normalized density score reached {lane.normalized_density_score:.2f} (threshold: {thresh_dens:.2f}).",
                    metric="normalized_density_score",
                    value=lane.normalized_density_score,
                ),
                make_observed(
                    f"Total {lane.unique_vehicles_count} unique vehicles processed through lane polygon.",
                    metric="unique_vehicles_count",
                    value=lane.unique_vehicles_count,
                    unit="vehicles",
                ),
            ]

            inferred = [
                make_inferred(
                    f"Vehicle arrival rate on '{lane.lane_name}' exceeded single-phase clearance capacity.",
                    rationale=f"Peak queue depth ({lane.peak_occupancy} veh) indicates persistent residual queue across signal intervals.",
                    confidence="high" if severity in ["HIGH", "CRITICAL"] else "medium",
                ),
                make_inferred(
                    "Downstream bottleneck or insufficient green split is propagating queue accumulation.",
                    rationale=f"Average occupancy ({lane.average_occupancy:.2f}) remained elevated relative to reference cell area.",
                    confidence="medium",
                ),
            ]

            correl_ids = [a.id for a in congestion_anomalies if a.lane_id == lane.lane_id]
            evidence = build_evidence_package(
                session=session,
                metrics=metrics,
                lanes=[lane],
                signal_simulations=signal_sims,
                corridor_simulations=corridor_sims,
                correlated_anomaly_ids=correl_ids,
            )
            limits = build_limitations_list(metrics, lanes, has_simulations=bool(signal_sims))

            dedup = compute_dedup_signature(
                session_id=session.id,
                insight_type="congestion_buildup",
                affected_lane_id=lane.lane_id,
                time_bin=0.0,
            )

            candidates.append(
                InsightCandidate(
                    session_id=session.id,
                    job_id=job_id,
                    insight_type="congestion_buildup",
                    category=InsightCategory.CONGESTION.value,
                    severity=severity,
                    status=InsightStatus.ACTIVE.value,
                    title=f"Sustained Congestion on {lane.lane_name}",
                    summary=(
                        f"Lane '{lane.lane_name}' experienced sustained high occupancy "
                        f"peaking at {lane.peak_occupancy} vehicles (normalized density: {lane.normalized_density_score:.2f}) "
                        f"over an observation window of {obs_dur:.1f}s."
                    ),
                    start_timestamp_seconds=0.0,
                    end_timestamp_seconds=obs_dur,
                    duration_seconds=obs_dur,
                    affected_lane_id=lane.lane_id,
                    affected_lane_name=lane.lane_name,
                    root_cause_observed=observed,
                    root_cause_inferred=inferred,
                    recommendation=rec_text,
                    recommendation_rationale=rec_rat,
                    recommendation_type=rec_type,
                    evidence_package=evidence,
                    limitations=limits,
                    provenance_category=prov_cat,
                    is_synthetic=is_synth,
                    dedup_signature=dedup,
                )
            )

    return candidates


# ==============================================================================
# Rule 2: FLOW_DEGRADATION
# ==============================================================================
def evaluate_flow_degradation(
    session: AnalysisSession,
    metrics: Optional[TrafficMetricsRecord],
    lanes: List[LaneResultRecord],
    anomalies: List[AnomalyEvent],
    signal_sims: List[SignalSimulationRun],
    corridor_sims: List[EmergencyCorridorSimulationRun],
    prov_cat: str,
    is_synth: bool,
    job_id: Optional[str] = None,
) -> List[InsightCandidate]:
    candidates: List[InsightCandidate] = []
    if not metrics or not metrics.time_series_buckets or len(metrics.time_series_buckets) < 2:
        return candidates

    buckets = metrics.time_series_buckets
    counts = [float(b.get("count", b.get("vehicle_count", 0))) for b in buckets]
    thresh_drop = settings.insight_flow_drop_pct_threshold

    flow_anomalies = [a for a in anomalies if a.anomaly_type == "abnormal_flow_drop"]

    for i in range(1, len(buckets)):
        prev_c = counts[i - 1]
        curr_c = counts[i]

        if prev_c >= 2.0:
            drop_pct = ((prev_c - curr_c) / prev_c) * 100.0
            if drop_pct >= thresh_drop or any(a.trigger_value == curr_c for a in flow_anomalies):
                severity = evaluate_flow_drop_severity(drop_pct)
                start_t = float(buckets[i].get("start_time_seconds", 0.0))
                end_t = float(buckets[i].get("end_time_seconds", start_t + 10.0))
                dur = max(end_t - start_t, 5.0)

                rec_text, rec_rat, rec_type = generate_flow_drop_recommendation(
                    drop_pct=drop_pct,
                    start_time_s=start_t,
                    end_time_s=end_t,
                )

                observed = [
                    make_observed(
                        f"Flow volume dropped from {int(prev_c)} to {int(curr_c)} vehicles ({drop_pct:.1f}% reduction).",
                        metric="flow_drop_pct",
                        value=round(drop_pct, 1),
                        unit="%",
                    ),
                    make_observed(
                        f"Occurred during interval [{start_t:.1f}s, {end_t:.1f}s] (bucket index {i}).",
                        metric="interval_start_seconds",
                        value=start_t,
                        unit="s",
                    ),
                ]

                inferred = [
                    make_inferred(
                        "Upstream blockage, red-phase hold, or incident abruptly halted traffic progression.",
                        rationale=f"A {drop_pct:.1f}% volume collapse within a short window indicates an acute disruption rather than natural demand decay.",
                        confidence="high" if drop_pct >= 75.0 else "medium",
                    ),
                ]

                correl_ids = [a.id for a in flow_anomalies if abs(a.start_timestamp_seconds - start_t) < 5.0]
                evidence = build_evidence_package(
                    session=session,
                    metrics=metrics,
                    lanes=lanes,
                    signal_simulations=signal_sims,
                    corridor_simulations=corridor_sims,
                    correlated_anomaly_ids=correl_ids,
                )
                limits = build_limitations_list(metrics, lanes, has_simulations=bool(signal_sims))

                dedup = compute_dedup_signature(
                    session_id=session.id,
                    insight_type="flow_degradation",
                    time_bin=start_t,
                )

                candidates.append(
                    InsightCandidate(
                        session_id=session.id,
                        job_id=job_id,
                        insight_type="flow_degradation",
                        category=InsightCategory.FLOW_DEGRADATION.value,
                        severity=severity,
                        status=InsightStatus.ACTIVE.value,
                        title=f"Sudden Flow Collapse ({drop_pct:.0f}% reduction)",
                        summary=(
                            f"Vehicle throughput collapsed by {drop_pct:.1f}% "
                            f"(from {int(prev_c)} to {int(curr_c)} vehicles) between {start_t:.1f}s and {end_t:.1f}s."
                        ),
                        start_timestamp_seconds=start_t,
                        end_timestamp_seconds=end_t,
                        duration_seconds=dur,
                        affected_lane_id=None,
                        affected_lane_name=None,
                        root_cause_observed=observed,
                        root_cause_inferred=inferred,
                        recommendation=rec_text,
                        recommendation_rationale=rec_rat,
                        recommendation_type=rec_type,
                        evidence_package=evidence,
                        limitations=limits,
                        provenance_category=prov_cat,
                        is_synthetic=is_synth,
                        dedup_signature=dedup,
                    )
                )

    return candidates


# ==============================================================================
# Rule 3: LANE_IMBALANCE
# ==============================================================================
def evaluate_lane_imbalance(
    session: AnalysisSession,
    metrics: Optional[TrafficMetricsRecord],
    lanes: List[LaneResultRecord],
    anomalies: List[AnomalyEvent],
    signal_sims: List[SignalSimulationRun],
    corridor_sims: List[EmergencyCorridorSimulationRun],
    prov_cat: str,
    is_synth: bool,
    job_id: Optional[str] = None,
) -> List[InsightCandidate]:
    candidates: List[InsightCandidate] = []
    if len(lanes) < 2:
        return candidates

    lane_counts = [(l.lane_id, l.lane_name, l.unique_vehicles_count) for l in lanes]
    lane_counts.sort(key=lambda x: x[2], reverse=True)
    max_lane = lane_counts[0]
    min_lane = lane_counts[-1]

    total_vol = sum(c[2] for c in lane_counts)
    thresh_ratio = settings.insight_lane_imbalance_ratio_threshold

    imbalance_anomalies = [a for a in anomalies if a.anomaly_type == "lane_imbalance"]

    if total_vol >= 5:
        skew_ratio = max_lane[2] / max(min_lane[2], 1)
        if skew_ratio >= thresh_ratio or imbalance_anomalies:
            severity = evaluate_lane_imbalance_severity(skew_ratio)
            obs_dur = metrics.observation_duration_seconds if metrics else 0.0

            rec_text, rec_rat, rec_type = generate_lane_imbalance_recommendation(
                dominant_lane=max_lane[1],
                starved_lane=min_lane[1],
                skew_ratio=skew_ratio,
            )

            observed = [
                make_observed(
                    f"Dominant lane '{max_lane[1]}' processed {max_lane[2]} vehicles.",
                    metric="dominant_lane_count",
                    value=max_lane[2],
                    unit="vehicles",
                ),
                make_observed(
                    f"Adjacent lane '{min_lane[1]}' processed {min_lane[2]} vehicles.",
                    metric="starved_lane_count",
                    value=min_lane[2],
                    unit="vehicles",
                ),
                make_observed(
                    f"Lane utilization skew ratio reached {skew_ratio:.1f}x (threshold: {thresh_ratio:.1f}x).",
                    metric="lane_skew_ratio",
                    value=round(skew_ratio, 2),
                ),
            ]

            inferred = [
                make_inferred(
                    f"Drivers exhibit systematic preference for '{max_lane[1]}' due to downstream turning movements or merge geometry.",
                    rationale=f"Skew ratio of {skew_ratio:.1f}x across parallel approach lanes indicates non-uniform path utility.",
                    confidence="high" if skew_ratio >= 6.0 else "medium",
                ),
                make_inferred(
                    f"Approach capacity is constrained because '{min_lane[1]}' is significantly under-utilized.",
                    rationale=f"Only {round((min_lane[2]/total_vol)*100, 1)}% of total approach volume utilized '{min_lane[1]}'.",
                    confidence="medium",
                ),
            ]

            correl_ids = [a.id for a in imbalance_anomalies]
            evidence = build_evidence_package(
                session=session,
                metrics=metrics,
                lanes=lanes,
                signal_simulations=signal_sims,
                corridor_simulations=corridor_sims,
                correlated_anomaly_ids=correl_ids,
            )
            limits = build_limitations_list(metrics, lanes, has_simulations=bool(signal_sims))

            dedup = compute_dedup_signature(
                session_id=session.id,
                insight_type="lane_imbalance",
                affected_lane_id=max_lane[0],
                time_bin=0.0,
            )

            candidates.append(
                InsightCandidate(
                    session_id=session.id,
                    job_id=job_id,
                    insight_type="lane_imbalance",
                    category=InsightCategory.LANE_IMBALANCE.value,
                    severity=severity,
                    status=InsightStatus.ACTIVE.value,
                    title=f"Lane Utilization Skew ({max_lane[1]} vs {min_lane[1]})",
                    summary=(
                        f"Significant lane flow imbalance detected: '{max_lane[1]}' processed {max_lane[2]} vehicles "
                        f"while '{min_lane[1]}' carried only {min_lane[2]} vehicles (skew ratio: {skew_ratio:.1f}x)."
                    ),
                    start_timestamp_seconds=0.0,
                    end_timestamp_seconds=obs_dur,
                    duration_seconds=obs_dur,
                    affected_lane_id=max_lane[0],
                    affected_lane_name=max_lane[1],
                    root_cause_observed=observed,
                    root_cause_inferred=inferred,
                    recommendation=rec_text,
                    recommendation_rationale=rec_rat,
                    recommendation_type=rec_type,
                    evidence_package=evidence,
                    limitations=limits,
                    provenance_category=prov_cat,
                    is_synthetic=is_synth,
                    dedup_signature=dedup,
                )
            )

    return candidates


# ==============================================================================
# Rule 4: DENSITY_SPIKE
# ==============================================================================
def evaluate_density_spike(
    session: AnalysisSession,
    metrics: Optional[TrafficMetricsRecord],
    lanes: List[LaneResultRecord],
    anomalies: List[AnomalyEvent],
    signal_sims: List[SignalSimulationRun],
    corridor_sims: List[EmergencyCorridorSimulationRun],
    prov_cat: str,
    is_synth: bool,
    job_id: Optional[str] = None,
) -> List[InsightCandidate]:
    candidates: List[InsightCandidate] = []
    thresh_dens = settings.insight_density_spike_threshold
    obs_dur = metrics.observation_duration_seconds if metrics else 0.0

    density_anomalies = [a for a in anomalies if a.anomaly_type == "density_spike"]

    for lane in lanes:
        condition_met = (
            lane.image_space_density >= thresh_dens
            or any(a.lane_id == lane.lane_id for a in density_anomalies)
        )

        if condition_met:
            severity = evaluate_density_spike_severity(
                density_value=lane.image_space_density,
                threshold=thresh_dens,
            )

            rec_text, rec_rat, rec_type = generate_density_spike_recommendation(
                lane_name=lane.lane_name,
                density_val=lane.image_space_density,
                threshold=thresh_dens,
            )

            mult = lane.image_space_density / max(thresh_dens, 1e-9)

            observed = [
                make_observed(
                    f"Image-space spatial density reached {lane.image_space_density:.6f} veh/px².",
                    metric="image_space_density",
                    value=lane.image_space_density,
                    unit="veh/px²",
                ),
                make_observed(
                    f"Exceeded reference density threshold ({thresh_dens:.6f} veh/px²) by {mult:.1f}x.",
                    metric="density_multiplier",
                    value=round(mult, 2),
                ),
                make_observed(
                    f"Polygon area in camera plane is {lane.polygon_area_px2:.0f} px².",
                    metric="polygon_area_px2",
                    value=lane.polygon_area_px2,
                    unit="px²",
                ),
            ]

            inferred = [
                make_inferred(
                    f"High vehicle spatial packing density inside '{lane.lane_name}' polygon.",
                    rationale="Multiple vehicle bounding boxes were simultaneously localized within a compact image-plane polygon.",
                    confidence="medium",
                ),
            ]

            correl_ids = [a.id for a in density_anomalies if a.lane_id == lane.lane_id]
            evidence = build_evidence_package(
                session=session,
                metrics=metrics,
                lanes=[lane],
                signal_simulations=signal_sims,
                corridor_simulations=corridor_sims,
                correlated_anomaly_ids=correl_ids,
            )
            limits = build_limitations_list(metrics, lanes, has_simulations=bool(signal_sims))

            dedup = compute_dedup_signature(
                session_id=session.id,
                insight_type="density_spike",
                affected_lane_id=lane.lane_id,
                time_bin=0.0,
            )

            candidates.append(
                InsightCandidate(
                    session_id=session.id,
                    job_id=job_id,
                    insight_type="density_spike",
                    category=InsightCategory.DENSITY_SPIKE.value,
                    severity=severity,
                    status=InsightStatus.ACTIVE.value,
                    title=f"Image-Space Density Spike on {lane.lane_name}",
                    summary=(
                        f"Spatial vehicle concentration peaked at {lane.image_space_density:.6f} veh/px² "
                        f"({mult:.1f}x baseline) on lane '{lane.lane_name}'. "
                        "Notice: 2D image-plane density, uncalibrated to physical ground area."
                    ),
                    start_timestamp_seconds=0.0,
                    end_timestamp_seconds=obs_dur,
                    duration_seconds=obs_dur,
                    affected_lane_id=lane.lane_id,
                    affected_lane_name=lane.lane_name,
                    root_cause_observed=observed,
                    root_cause_inferred=inferred,
                    recommendation=rec_text,
                    recommendation_rationale=rec_rat,
                    recommendation_type=rec_type,
                    evidence_package=evidence,
                    limitations=limits,
                    provenance_category=prov_cat,
                    is_synthetic=is_synth,
                    dedup_signature=dedup,
                )
            )

    return candidates


# ==============================================================================
# Rule 5: TRAFFIC_SURGE
# ==============================================================================
def evaluate_traffic_surge(
    session: AnalysisSession,
    metrics: Optional[TrafficMetricsRecord],
    lanes: List[LaneResultRecord],
    anomalies: List[AnomalyEvent],
    signal_sims: List[SignalSimulationRun],
    corridor_sims: List[EmergencyCorridorSimulationRun],
    prov_cat: str,
    is_synth: bool,
    job_id: Optional[str] = None,
) -> List[InsightCandidate]:
    candidates: List[InsightCandidate] = []
    if not metrics:
        return candidates

    flow_rate = metrics.flow_rate_per_minute
    total_vol = metrics.total_volume
    obs_dur = metrics.observation_duration_seconds

    # Extract heavy vehicle percentage (trucks + buses)
    heavy_count = 0
    if metrics.class_distribution:
        for c in metrics.class_distribution:
            if c.get("class_name") in ["truck", "bus"]:
                heavy_count += c.get("count", 0)

    heavy_pct = (heavy_count / max(total_vol, 1)) * 100.0 if total_vol > 0 else 0.0

    thresh_flow = settings.insight_surge_flow_rate_threshold
    thresh_heavy = settings.insight_heavy_vehicle_pct_threshold

    condition_met = (flow_rate >= thresh_flow) or (total_vol >= 5 and heavy_pct >= thresh_heavy)

    if condition_met:
        severity = evaluate_traffic_surge_severity(flow_rate, heavy_pct)

        rec_text, rec_rat, rec_type = generate_traffic_surge_recommendation(
            flow_rate=flow_rate,
            heavy_pct=heavy_pct,
            heavy_count=heavy_count,
        )

        observed = [
            make_observed(
                f"Observed flow rate of {flow_rate:.1f} vehicles/minute (extrapolated: {metrics.is_extrapolated}).",
                metric="flow_rate_per_minute",
                value=round(flow_rate, 1),
                unit="veh/min",
            ),
            make_observed(
                f"Heavy vehicles (buses/trucks) accounted for {heavy_pct:.1f}% ({heavy_count}/{total_vol}) of volume.",
                metric="heavy_vehicle_percentage",
                value=round(heavy_pct, 1),
                unit="%",
            ),
        ]

        inferred = [
            make_inferred(
                "Elevated PCU load requires extended clearance times and adjusted green splits.",
                rationale="Commercial vehicle presence increases queue discharge headways and reduces intersection capacity.",
                confidence="high" if heavy_pct >= 30.0 else "medium",
            ),
        ]

        evidence = build_evidence_package(
            session=session,
            metrics=metrics,
            lanes=lanes,
            signal_simulations=signal_sims,
            corridor_simulations=corridor_sims,
        )
        limits = build_limitations_list(metrics, lanes, has_simulations=bool(signal_sims))

        dedup = compute_dedup_signature(
            session_id=session.id,
            insight_type="traffic_surge",
            time_bin=0.0,
        )

        candidates.append(
            InsightCandidate(
                session_id=session.id,
                job_id=job_id,
                insight_type="traffic_surge",
                category=InsightCategory.TRAFFIC_SURGE.value,
                severity=severity,
                status=InsightStatus.ACTIVE.value,
                title="Traffic Volume / Fleet Composition Surge",
                summary=(
                    f"Traffic flow surged to {flow_rate:.1f} veh/min with "
                    f"{heavy_pct:.1f}% heavy commercial vehicles ({heavy_count} trucks/buses)."
                ),
                start_timestamp_seconds=0.0,
                end_timestamp_seconds=obs_dur,
                duration_seconds=obs_dur,
                affected_lane_id=None,
                affected_lane_name=None,
                root_cause_observed=observed,
                root_cause_inferred=inferred,
                recommendation=rec_text,
                recommendation_rationale=rec_rat,
                recommendation_type=rec_type,
                evidence_package=evidence,
                limitations=limits,
                provenance_category=prov_cat,
                is_synthetic=is_synth,
                dedup_signature=dedup,
            )
        )

    return candidates


# ==============================================================================
# Rule 6: UNDERUTILIZED_LANE
# ==============================================================================
def evaluate_underutilized_lane(
    session: AnalysisSession,
    metrics: Optional[TrafficMetricsRecord],
    lanes: List[LaneResultRecord],
    anomalies: List[AnomalyEvent],
    signal_sims: List[SignalSimulationRun],
    corridor_sims: List[EmergencyCorridorSimulationRun],
    prov_cat: str,
    is_synth: bool,
    job_id: Optional[str] = None,
) -> List[InsightCandidate]:
    candidates: List[InsightCandidate] = []
    if len(lanes) < 2:
        return candidates

    total_vol = sum(l.unique_vehicles_count for l in lanes)
    if total_vol < 10:
        return candidates

    obs_dur = metrics.observation_duration_seconds if metrics else 0.0

    for lane in lanes:
        # Underutilized if <= 1 vehicle while total session volume >= 10 and max lane >= 5
        if lane.unique_vehicles_count <= 1:
            rec_text, rec_rat, rec_type = generate_underutilized_lane_recommendation(
                lane_name=lane.lane_name,
                lane_volume=lane.unique_vehicles_count,
                total_volume=total_vol,
            )

            observed = [
                make_observed(
                    f"Lane '{lane.lane_name}' processed {lane.unique_vehicles_count} vehicles out of {total_vol} total.",
                    metric="unique_vehicles_count",
                    value=lane.unique_vehicles_count,
                    unit="vehicles",
                ),
                make_observed(
                    f"Average occupancy was {lane.average_occupancy:.2f} vehicles.",
                    metric="average_occupancy",
                    value=lane.average_occupancy,
                ),
            ]

            inferred = [
                make_inferred(
                    f"Lane '{lane.lane_name}' is structurally or behaviorally under-utilized by approaching traffic.",
                    rationale=f"Carried only {round((lane.unique_vehicles_count/total_vol)*100, 1)}% of total corridor volume.",
                    confidence="medium",
                ),
            ]

            evidence = build_evidence_package(
                session=session,
                metrics=metrics,
                lanes=[lane],
                signal_simulations=signal_sims,
                corridor_simulations=corridor_sims,
            )
            limits = build_limitations_list(metrics, lanes, has_simulations=bool(signal_sims))

            dedup = compute_dedup_signature(
                session_id=session.id,
                insight_type="underutilized_lane",
                affected_lane_id=lane.lane_id,
                time_bin=0.0,
            )

            candidates.append(
                InsightCandidate(
                    session_id=session.id,
                    job_id=job_id,
                    insight_type="underutilized_lane",
                    category=InsightCategory.UNDERUTILIZED_LANE.value,
                    severity=InsightSeverity.INFO.value,
                    status=InsightStatus.ACTIVE.value,
                    title=f"Underutilized Capacity on {lane.lane_name}",
                    summary=(
                        f"Lane '{lane.lane_name}' carried only {lane.unique_vehicles_count} of {total_vol} total vehicles "
                        f"during the observation window ({obs_dur:.1f}s)."
                    ),
                    start_timestamp_seconds=0.0,
                    end_timestamp_seconds=obs_dur,
                    duration_seconds=obs_dur,
                    affected_lane_id=lane.lane_id,
                    affected_lane_name=lane.lane_name,
                    root_cause_observed=observed,
                    root_cause_inferred=inferred,
                    recommendation=rec_text,
                    recommendation_rationale=rec_rat,
                    recommendation_type=rec_type,
                    evidence_package=evidence,
                    limitations=limits,
                    provenance_category=prov_cat,
                    is_synthetic=is_synth,
                    dedup_signature=dedup,
                )
            )

    return candidates


# ==============================================================================
# Rule 7: OPERATIONAL_RECOMMENDATION (Holistic Synthesis)
# ==============================================================================
def evaluate_operational_recommendation(
    session: AnalysisSession,
    metrics: Optional[TrafficMetricsRecord],
    lanes: List[LaneResultRecord],
    anomalies: List[AnomalyEvent],
    signal_sims: List[SignalSimulationRun],
    corridor_sims: List[EmergencyCorridorSimulationRun],
    candidates_so_far: List[InsightCandidate],
    prov_cat: str,
    is_synth: bool,
    job_id: Optional[str] = None,
) -> List[InsightCandidate]:
    candidates: List[InsightCandidate] = []
    obs_dur = metrics.observation_duration_seconds if metrics else 0.0

    # 1. Signal Simulation Optimization Guidance
    if signal_sims:
        best_sim = signal_sims[0]
        delay_red = getattr(best_sim, "delay_reduction_pct", 0.0)
        queue_red = getattr(best_sim, "queue_reduction_pct", 0.0)
        intersection = getattr(best_sim, "intersection_name", "Intersection")
        algo = getattr(best_sim, "algorithm_used", "Webster Optimizer")

        if delay_red > 0.0 or queue_red > 0.0:
            rec_text, rec_rat, rec_type = generate_signal_optimization_recommendation(signal_sims)
            observed = [
                make_observed(
                    f"Signal optimization simulation run '{best_sim.id}' tested for '{intersection}'.",
                    metric="signal_simulation_run_id",
                    value=best_sim.id,
                ),
                make_observed(
                    f"Baseline cycle length {best_sim.baseline_cycle_length:.1f}s vs optimized {best_sim.optimized_cycle_length:.1f}s.",
                    metric="baseline_cycle_length",
                    value=best_sim.baseline_cycle_length,
                    unit="s",
                ),
            ]
            inferred = [
                make_inferred(
                    f"Simulation indicates {algo} plan can achieve {delay_red:.1f}% delay reduction and {queue_red:.1f}% queue reduction.",
                    rationale="Green split rebalancing satisfies critical movement saturation ratios under observed demand.",
                    confidence="high",
                ),
            ]
            evidence = build_evidence_package(
                session=session,
                metrics=metrics,
                lanes=lanes,
                signal_simulations=signal_sims,
                corridor_simulations=corridor_sims,
            )
            limits = build_limitations_list(metrics, lanes, has_simulations=True)
            dedup = compute_dedup_signature(
                session_id=session.id,
                insight_type="operational_signal_advisory",
                time_bin=0.0,
            )
            candidates.append(
                InsightCandidate(
                    session_id=session.id,
                    job_id=job_id,
                    insight_type="operational_signal_advisory",
                    category=InsightCategory.OPERATIONAL_RECOMMENDATION.value,
                    severity=InsightSeverity.INFO.value,
                    status=InsightStatus.ACTIVE.value,
                    title=f"Signal Timing Optimization Advisory ({intersection})",
                    summary=(
                        f"Simulation indicates {delay_red:.1f}% delay reduction and {queue_red:.1f}% queue reduction "
                        f"using {algo} for '{intersection}'. Notice: offline simulation estimate, not live actuation."
                    ),
                    start_timestamp_seconds=0.0,
                    end_timestamp_seconds=obs_dur,
                    duration_seconds=obs_dur,
                    affected_lane_id=None,
                    affected_lane_name=None,
                    root_cause_observed=observed,
                    root_cause_inferred=inferred,
                    recommendation=rec_text,
                    recommendation_rationale=rec_rat,
                    recommendation_type=rec_type,
                    evidence_package=evidence,
                    limitations=limits,
                    provenance_category=prov_cat,
                    is_synthetic=is_synth,
                    dedup_signature=dedup,
                )
            )

    # 2. Corridor Simulation Coordination Guidance
    if corridor_sims:
        best_corridor = corridor_sims[0]
        if getattr(best_corridor, "time_saved_seconds", 0.0) > 0:
            rec_text, rec_rat, rec_type = generate_corridor_coordination_recommendation(corridor_sims)
            time_saved = getattr(best_corridor, "time_saved_seconds", 0.0)
            travel_red = getattr(best_corridor, "travel_time_reduction_pct", 0.0)
            c_name = getattr(best_corridor, "corridor_name", "Arterial Corridor")
            v_type = getattr(best_corridor, "vehicle_type", "Emergency Vehicle")

            observed = [
                make_observed(
                    f"Emergency corridor simulation model tested for '{c_name}' with '{v_type}'.",
                    metric="corridor_simulation_run_id",
                    value=best_corridor.id,
                ),
                make_observed(
                    f"Baseline travel time was {best_corridor.baseline_travel_time_seconds:.1f}s vs priority {best_corridor.priority_travel_time_seconds:.1f}s.",
                    metric="baseline_travel_time_seconds",
                    value=best_corridor.baseline_travel_time_seconds,
                    unit="s",
                ),
            ]

            inferred = [
                make_inferred(
                    f"Simulation indicates coordinated signal progression can save {time_saved:.1f}s ({travel_red:.1f}% reduction).",
                    rationale="Dynamic queue pre-clearance green window eliminates approach standing delay for priority vehicle.",
                    confidence="high",
                ),
            ]

            evidence = build_evidence_package(
                session=session,
                metrics=metrics,
                lanes=lanes,
                signal_simulations=signal_sims,
                corridor_simulations=corridor_sims,
            )
            limits = build_limitations_list(metrics, lanes, has_simulations=True)

            dedup = compute_dedup_signature(
                session_id=session.id,
                insight_type="operational_corridor_advisory",
                time_bin=0.0,
            )

            candidates.append(
                InsightCandidate(
                    session_id=session.id,
                    job_id=job_id,
                    insight_type="operational_corridor_advisory",
                    category=InsightCategory.OPERATIONAL_RECOMMENDATION.value,
                    severity=InsightSeverity.INFO.value,
                    status=InsightStatus.ACTIVE.value,
                    title=f"Coordinated Progression Advisory ({c_name})",
                    summary=(
                        f"Simulation indicates {travel_red:.1f}% travel time reduction ({time_saved:.1f}s saved) "
                        f"for {v_type} along '{c_name}'. Notice: simulation estimate, not field preemption."
                    ),
                    start_timestamp_seconds=0.0,
                    end_timestamp_seconds=obs_dur,
                    duration_seconds=obs_dur,
                    affected_lane_id=None,
                    affected_lane_name=None,
                    root_cause_observed=observed,
                    root_cause_inferred=inferred,
                    recommendation=rec_text,
                    recommendation_rationale=rec_rat,
                    recommendation_type=rec_type,
                    evidence_package=evidence,
                    limitations=limits,
                    provenance_category=prov_cat,
                    is_synthetic=is_synth,
                    dedup_signature=dedup,
                )
            )

    return candidates

