"""
Root-Cause Reasoning Engine: Strict Observed vs Inferred Taxonomy.
Phase 18: Intelligent Traffic Insights & Explainable Decision Intelligence.

Enforces zero epistemic confusion:
- Observed statements represent direct empirical measurements with values, units, and timestamps.
- Inferred statements represent deductive reasoning explaining *why* the condition exists.
"""
from typing import Any, Dict, Optional


def make_observed(
    statement: str,
    metric: str,
    value: Any,
    unit: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates an explicitly labeled Observed factor dictionary.
    Guarantees prefix 'Observed: ' in the statement.
    """
    clean_statement = statement.strip()
    if not clean_statement.startswith("Observed:"):
        clean_statement = f"Observed: {clean_statement}"

    return {
        "label": "Observed",
        "statement": clean_statement,
        "metric": metric,
        "value": value,
        "unit": unit,
    }


def make_inferred(
    statement: str,
    rationale: str,
    confidence: str = "medium",
) -> Dict[str, Any]:
    """
    Creates an explicitly labeled Inferred factor dictionary.
    Guarantees prefix 'Inferred: ' in the statement.
    """
    clean_statement = statement.strip()
    if not clean_statement.startswith("Inferred:"):
        clean_statement = f"Inferred: {clean_statement}"

    valid_confidences = {"high", "medium", "low"}
    conf = confidence.lower() if confidence.lower() in valid_confidences else "medium"

    return {
        "label": "Inferred",
        "statement": clean_statement,
        "rationale": rationale.strip(),
        "confidence": conf,
    }
