"""
Evidence-Grounded Severity Evaluator.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.

Assigns discrete severity levels (INFO, LOW, MEDIUM, HIGH, CRITICAL)
based strictly on measured threshold deviations and mathematical conditions.
"""
from app.models.insight import InsightSeverity


def evaluate_congestion_severity(
    peak_occupancy: int,
    threshold: int,
    density_score: float,
) -> str:
    """Computes severity for congestion condition based on occupancy and density."""
    if peak_occupancy >= threshold + 8 or density_score >= 0.98:
        return InsightSeverity.CRITICAL.value
    elif peak_occupancy >= threshold + 4 or density_score >= 0.90:
        return InsightSeverity.HIGH.value
    elif peak_occupancy >= threshold + 2 or density_score >= 0.80:
        return InsightSeverity.MEDIUM.value
    elif peak_occupancy >= threshold or density_score >= 0.70:
        return InsightSeverity.LOW.value
    return InsightSeverity.INFO.value


def evaluate_flow_drop_severity(drop_pct: float) -> str:
    """Computes severity for flow drop percentage."""
    if drop_pct >= 90.0:
        return InsightSeverity.CRITICAL.value
    elif drop_pct >= 75.0:
        return InsightSeverity.HIGH.value
    elif drop_pct >= 60.0:
        return InsightSeverity.MEDIUM.value
    elif drop_pct >= 50.0:
        return InsightSeverity.LOW.value
    return InsightSeverity.INFO.value


def evaluate_lane_imbalance_severity(skew_ratio: float) -> str:
    """Computes severity for multi-lane volume/occupancy skew ratio."""
    if skew_ratio >= 10.0:
        return InsightSeverity.CRITICAL.value
    elif skew_ratio >= 6.0:
        return InsightSeverity.HIGH.value
    elif skew_ratio >= 4.0:
        return InsightSeverity.MEDIUM.value
    elif skew_ratio >= 3.0:
        return InsightSeverity.LOW.value
    return InsightSeverity.INFO.value


def evaluate_density_spike_severity(
    density_value: float,
    threshold: float,
) -> str:
    """Computes severity for image-space density spike."""
    if threshold <= 0.0:
        return InsightSeverity.INFO.value
    multiplier = density_value / threshold
    if multiplier >= 2.5:
        return InsightSeverity.CRITICAL.value
    elif multiplier >= 1.8:
        return InsightSeverity.HIGH.value
    elif multiplier >= 1.3:
        return InsightSeverity.MEDIUM.value
    elif multiplier >= 1.0:
        return InsightSeverity.LOW.value
    return InsightSeverity.INFO.value


def evaluate_traffic_surge_severity(
    flow_rate_per_min: float,
    heavy_vehicle_pct: float,
) -> str:
    """Computes severity for volume surge or heavy vehicle concentration."""
    if heavy_vehicle_pct >= 50.0 or flow_rate_per_min >= 120.0:
        return InsightSeverity.HIGH.value
    elif heavy_vehicle_pct >= 30.0 or flow_rate_per_min >= 60.0:
        return InsightSeverity.MEDIUM.value
    elif heavy_vehicle_pct >= 20.0 or flow_rate_per_min >= 40.0:
        return InsightSeverity.LOW.value
    return InsightSeverity.INFO.value
