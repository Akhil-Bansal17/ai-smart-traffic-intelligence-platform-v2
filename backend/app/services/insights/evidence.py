"""
Evidence Package & Limitations Aggregator.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.

Consolidates supporting empirical evidence, anomaly correlations, simulation references,
and honest declarations of unavailable or unmeasured telemetry.
"""
from typing import Any, Dict, List, Optional

from app.models.analysis import AnalysisSession, LaneResultRecord, TrafficMetricsRecord
from app.models.anomaly import AnomalyEvent
from app.models.corridor_simulation import EmergencyCorridorSimulationRun
from app.models.simulation import SignalSimulationRun


def build_evidence_package(
    session: AnalysisSession,
    metrics: Optional[TrafficMetricsRecord] = None,
    lanes: Optional[List[LaneResultRecord]] = None,
    anomalies: Optional[List[AnomalyEvent]] = None,
    signal_simulations: Optional[List[SignalSimulationRun]] = None,
    corridor_simulations: Optional[List[EmergencyCorridorSimulationRun]] = None,
    correlated_anomaly_ids: Optional[List[str]] = None,
    custom_unavailable: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Builds a structured evidence package consolidating all supporting records.
    Explicitly labels unavailable metrics and simulation models.
    """
    # 1. Metrics Summary
    metrics_summary: Optional[Dict[str, Any]] = None
    if metrics:
        metrics_summary = {
            "total_volume": metrics.total_volume,
            "flow_rate_per_minute": round(metrics.flow_rate_per_minute, 2),
            "flow_rate_per_hour": round(metrics.flow_rate_per_hour, 1),
            "is_extrapolated": metrics.is_extrapolated,
            "observation_duration_seconds": round(metrics.observation_duration_seconds, 2),
            "total_vehicles_counted": session.total_vehicles_counted,
            "total_vehicles_detected": session.total_vehicles_detected,
        }

    # 2. Per-Lane Metrics Snapshot
    lane_snapshots: List[Dict[str, Any]] = []
    if lanes:
        for l in lanes:
            lane_snapshots.append({
                "lane_id": l.lane_id,
                "lane_name": l.lane_name,
                "unique_vehicles_count": l.unique_vehicles_count,
                "peak_occupancy": l.peak_occupancy,
                "average_occupancy": round(l.average_occupancy, 2),
                "normalized_density_score": round(l.normalized_density_score, 2),
                "image_space_density": round(l.image_space_density, 6),
                "density_unit": l.density_unit,
            })

    # 3. Anomaly Event References
    anomaly_ids = correlated_anomaly_ids or []
    if not anomaly_ids and anomalies:
        anomaly_ids = [a.id for a in anomalies]

    # 4. Simulation References (Explicitly labeled as simulation estimates)
    sim_refs: List[Dict[str, Any]] = []
    if signal_simulations:
        for s in signal_simulations:
            b_metrics = s.baseline_metrics if isinstance(s.baseline_metrics, dict) else {}
            o_metrics = s.optimized_metrics if isinstance(s.optimized_metrics, dict) else {}
            b_los = b_metrics.get("los") or getattr(s, "baseline_los", "N/A")
            o_los = o_metrics.get("los") or getattr(s, "optimized_los", "N/A")
            sim_refs.append({
                "simulation_id": s.id,
                "simulation_type": "signal_optimization",
                "intersection_name": s.intersection_name,
                "algorithm_used": s.algorithm_used,
                "delay_reduction_pct": round(getattr(s, "delay_reduction_pct", 0.0), 1),
                "queue_reduction_pct": round(getattr(s, "queue_reduction_pct", 0.0), 1),
                "baseline_los": str(b_los),
                "optimized_los": str(o_los),
                "is_simulation": True,
                "provenance": s.data_source,
                "disclaimer": "Simulated timing plan estimate; does not actuate field hardware.",
            })

    if corridor_simulations:
        for c in corridor_simulations:
            sim_refs.append({
                "simulation_id": c.id,
                "simulation_type": "emergency_corridor",
                "corridor_name": c.corridor_name,
                "vehicle_type": c.vehicle_type,
                "time_saved_seconds": round(c.time_saved_seconds, 1),
                "travel_time_reduction_pct": round(c.travel_time_reduction_pct, 1),
                "is_simulation": True,
                "provenance": c.data_source,
                "disclaimer": "Simulated arterial priority progression; does not actuate field hardware.",
            })

    # 5. Prediction Evidence: Strict Phase 11 Trust Boundary
    # Dataset contains < 20 verified real-world samples, so forecast evidence is unavailable
    prediction_evidence = {
        "is_available": False,
        "sample_count_available": 10,
        "sample_threshold_required": 20,
        "status_code": "insufficient_real_world_observations",
        "reason": "Forecast evidence unavailable: genuine real-world observations (10) are below the statistical threshold (20) per Phase 11 trust boundary.",
    }

    # 6. Explicit Unavailable Telemetry
    unavailable = [
        "physical_speed_radar_telemetry",
        "real_world_signal_controller_feedback",
        "connected_vehicle_v2x_broadcasts",
    ]
    if custom_unavailable:
        for u in custom_unavailable:
            if u not in unavailable:
                unavailable.append(u)

    return {
        "metrics_summary": metrics_summary,
        "lane_metrics": lane_snapshots,
        "anomaly_event_ids": anomaly_ids,
        "simulation_references": sim_refs,
        "prediction_evidence": prediction_evidence,
        "unavailable_evidence": unavailable,
    }


def build_limitations_list(
    metrics: Optional[TrafficMetricsRecord] = None,
    lanes: Optional[List[LaneResultRecord]] = None,
    has_simulations: bool = False,
) -> List[str]:
    """Constructs an explicit list of technical limitations and caveats for the insight."""
    limitations: List[str] = [
        "Image-space spatial density is measured in 2D camera pixel coordinates (veh/px²) and is uncalibrated to physical ground area (veh/km²).",
        "Advisory recommendations are decision-support outputs and do not physically actuate traffic signal controllers.",
        "Traffic prediction evidence is currently unavailable due to insufficient real-world historical observation samples (N < 20).",
    ]

    if metrics and metrics.is_extrapolated:
        limitations.append(
            f"Observation duration ({metrics.observation_duration_seconds:.1f}s) is less than 1 hour; "
            "hourly flow rate is extrapolated assuming stationary arrival rates."
        )

    if has_simulations:
        limitations.append(
            "Signal and corridor delay reductions are model-based simulation projections, not observed field performance."
        )

    return limitations
