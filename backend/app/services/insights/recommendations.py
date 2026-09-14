"""
Deterministic Advisory Recommendation Engine.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.

Maps detected traffic conditions deterministically to actionable, advisory operational guidance.
Never claims physical signal actuation or unverified real-world gains.
Explicitly labels simulation-backed improvements as 'simulation indicates'.
"""
from typing import Any, Dict, List, Optional, Tuple

from app.models.insight import RecommendationType


def generate_congestion_recommendation(
    lane_name: str,
    peak_occupancy: int,
    density_score: float,
    signal_sim_runs: Optional[List[Any]] = None,
) -> Tuple[str, str, str]:
    """
    Generates advisory guidance for congestion conditions.
    Returns (recommendation_text, rationale, recommendation_type).
    """
    sim_note = ""
    if signal_sim_runs:
        best_run = signal_sim_runs[0]
        delay_red = getattr(best_run, "delay_reduction_pct", 0.0)
        algo = getattr(best_run, "algorithm_used", "Webster Optimizer")
        if delay_red > 0.0:
            sim_note = (
                f" Offline signal simulation using {algo} indicates a potential {delay_red:.1f}% delay reduction "
                "via adjusted green splits. (Advisory only: physical signal actuation not connected)."
            )

    rec_text = (
        f"Consider reviewing signal green time allocation for the approach serving '{lane_name}'."
        f"{sim_note}"
    )
    rationale = (
        f"Peak occupancy reached {peak_occupancy} vehicles with normalized density of {density_score:.2f}, "
        "indicating demand exceeding single-cycle clearance capacity."
    )
    return rec_text, rationale, RecommendationType.SIGNAL_RETIMING.value


def generate_flow_drop_recommendation(
    drop_pct: float,
    start_time_s: float,
    end_time_s: float,
) -> Tuple[str, str, str]:
    """Generates advisory guidance for flow degradation/collapse."""
    rec_text = (
        "Monitor downstream corridor for temporary obstructions, lane blockages, or upstream signal cycle transition. "
        "Verify throughput recovery in subsequent observation interval."
    )
    rationale = (
        f"Flow rate collapsed by {drop_pct:.1f}% during [{start_time_s:.0f}s, {end_time_s:.0f}s], "
        "which typically signals a downstream bottleneck or abrupt disruption."
    )
    return rec_text, rationale, RecommendationType.MONITORING_ONLY.value


def generate_lane_imbalance_recommendation(
    dominant_lane: str,
    starved_lane: str,
    skew_ratio: float,
) -> Tuple[str, str, str]:
    """Generates advisory guidance for lane utilization imbalance."""
    rec_text = (
        f"Evaluate advance lane assignment signage, turning lane markings, or dynamic message displays "
        f"to encourage utilization of underutilized lane '{starved_lane}'."
    )
    rationale = (
        f"Lane '{dominant_lane}' handled {skew_ratio:.1f}x the volume of '{starved_lane}', "
        "concentrating queue delay while adjacent approach capacity remained idle."
    )
    return rec_text, rationale, RecommendationType.LANE_MANAGEMENT.value


def generate_density_spike_recommendation(
    lane_name: str,
    density_val: float,
    threshold: float,
) -> Tuple[str, str, str]:
    """Generates advisory guidance for image-space density spike."""
    rec_text = (
        f"Inspect camera view for stationary queues, merge bottlenecks, or slow-moving platoons in '{lane_name}'. "
        "Consider upstream metering if queue propagates."
    )
    rationale = (
        f"Image-space spatial density peaked at {density_val:.6f} veh/px² "
        f"({(density_val/threshold):.1f}x reference threshold), indicating tight vehicle headway."
    )
    return rec_text, rationale, RecommendationType.CAPACITY_WARNING.value


def generate_traffic_surge_recommendation(
    flow_rate: float,
    heavy_pct: float,
    heavy_count: int,
) -> Tuple[str, str, str]:
    """Generates advisory guidance for traffic volume surge or heavy vehicle composition."""
    if heavy_pct >= 30.0:
        rec_text = (
            f"Account for increased Passenger Car Units (PCU) due to {heavy_pct:.1f}% heavy commercial vehicles ({heavy_count} trucks/buses). "
            "Consider extending amber/all-red clearance intervals on critical phases."
        )
        rationale = (
            f"Heavy vehicles require longer acceleration and deceleration distances, "
            f"reducing effective saturation flow rate."
        )
        return rec_text, rationale, RecommendationType.SIGNAL_RETIMING.value
    else:
        rec_text = (
            f"High volume surge ({flow_rate:.1f} veh/min). Monitor approach queues to prevent spillback into upstream junctions."
        )
        rationale = (
            f"Elevated flow rate increases queue accumulation rates during red phases."
        )
        return rec_text, rationale, RecommendationType.MONITORING_ONLY.value


def generate_underutilized_lane_recommendation(
    lane_name: str,
    lane_volume: int,
    total_volume: int,
) -> Tuple[str, str, str]:
    """Generates advisory guidance for underutilized lane."""
    rec_text = (
        f"Investigate driver routing behavior or physical lane restrictions on '{lane_name}'. "
        "Consider reallocating lane designation if turning movement demand is skewed."
    )
    rationale = (
        f"Lane '{lane_name}' processed only {lane_volume} of {total_volume} total vehicles, "
        "indicating structural or behavioral under-utilization."
    )
    return rec_text, rationale, RecommendationType.LANE_MANAGEMENT.value


def generate_corridor_coordination_recommendation(
    corridor_sim_runs: List[Any],
) -> Tuple[str, str, str]:
    """Generates advisory guidance for emergency corridor coordination."""
    best_corridor = corridor_sim_runs[0]
    time_saved = getattr(best_corridor, "time_saved_seconds", 0.0)
    travel_red = getattr(best_corridor, "travel_time_reduction_pct", 0.0)
    c_name = getattr(best_corridor, "corridor_name", "Arterial Corridor")
    v_type = getattr(best_corridor, "vehicle_type", "Emergency Vehicle")

    rec_text = (
        f"Simulation indicates coordinated green progression on '{c_name}' could reduce {v_type} travel time by "
        f"{travel_red:.1f}% ({time_saved:.1f}s saved). Notice: this is a simulation estimate, not physical preemption."
    )
    rationale = (
        f"Pre-clearing queue lead-times ahead of approaching {v_type} eliminates intersection standing delay."
    )
    return rec_text, rationale, RecommendationType.CORRIDOR_COORDINATION.value


def generate_signal_optimization_recommendation(
    signal_sim_runs: List[Any],
) -> Tuple[str, str, str]:
    """Generates advisory guidance for signal timing plan optimization."""
    best_sim = signal_sim_runs[0]
    delay_red = getattr(best_sim, "delay_reduction_pct", 0.0)
    queue_red = getattr(best_sim, "queue_reduction_pct", 0.0)
    intersection = getattr(best_sim, "intersection_name", "Intersection")
    algo = getattr(best_sim, "algorithm_used", "Webster Optimizer")

    rec_text = (
        f"Simulation indicates {algo} timing plan on '{intersection}' could reduce delay by {delay_red:.1f}% "
        f"and queue length by {queue_red:.1f}%. (Advisory only: physical signal actuation not connected)."
    )
    rationale = (
        "Optimized green split distribution balances degree of saturation across all critical approaches."
    )
    return rec_text, rationale, RecommendationType.SIGNAL_RETIMING.value

