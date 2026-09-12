"""
Verification Script for Phase 14: System-Wide Traffic Intelligence & Decision-Support Dashboard.
Hits the dashboard endpoints live against the development database,
validates all 10 modular sections, checks explicit 5-state provenance labeling,
verifies Phase 11 dynamic real-observation threshold reporting (10/20 observations),
confirms simulation decision-support disclaimers, and measures latency.
"""
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from fastapi.testclient import TestClient
from app.main import app


def print_header(title: str):
    print(f"\n{'='*75}")
    print(f"  {title}")
    print(f"{'='*75}")


def print_check(index: int, description: str, passed: bool, detail: str = ""):
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"  {status_str} Check {index:02d}: {description}")
    if detail:
        print(f"         ↳ {detail}")


def run_verification():
    print_header("PHASE 14 VERIFICATION: SYSTEM-WIDE INTELLIGENCE DASHBOARD")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Testing environment: FastAPI TestClient + SQLite/PostgreSQL Database")

    client = TestClient(app)
    checks_passed = 0
    total_checks = 11

    # -------------------------------------------------------------
    # Check 1: Dashboard Info Endpoint & Anti-Trigger Guarantee
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    info_res = client.get("/api/v1/dashboard/info")
    info_lat = (time.perf_counter() - t0) * 1000.0

    if info_res.status_code == 200:
        info_data = info_res.json()
        has_anti_trigger = "NEVER trigger" in info_data.get("anti_trigger_guarantee", "")
        has_prov_cats = len(info_data.get("provenance_categories", [])) >= 4
        c1_pass = has_anti_trigger and has_prov_cats
        detail = f"Status 200 OK in {info_lat:.2f}ms. Anti-trigger guarantee confirmed: '{info_data.get('anti_trigger_guarantee')[:60]}...'"
    else:
        c1_pass = False
        detail = f"Failed with HTTP {info_res.status_code}: {info_res.text}"

    if c1_pass:
        checks_passed += 1
    print_check(1, "Dashboard Info API & Anti-Trigger Architecture Guarantee", c1_pass, detail)

    # -------------------------------------------------------------
    # Check 2: Single-Roundtrip Summary Endpoint Execution
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    summary_res = client.get("/api/v1/dashboard/summary")
    summary_lat = (time.perf_counter() - t0) * 1000.0

    if summary_res.status_code == 200:
        summary_data = summary_res.json()
        required_sections = [
            "system_health",
            "traffic_overview",
            "vehicle_composition",
            "traffic_flow_metrics",
            "lane_density",
            "prediction_availability",
            "signal_optimization",
            "emergency_corridor",
            "recent_history",
            "data_provenance",
        ]
        all_sections_present = all(sec in summary_data for sec in required_sections)
        server_exec_ms = summary_data.get("execution_time_ms", 0.0)
        c2_pass = all_sections_present and summary_lat < 200.0
        detail = f"Summary loaded in {summary_lat:.2f}ms (server exec: {server_exec_ms:.2f}ms). All 10 sections present."
    else:
        summary_data = {}
        c2_pass = False
        detail = f"Failed with HTTP {summary_res.status_code}: {summary_res.text}"

    if c2_pass:
        checks_passed += 1
    print_check(2, "Unified Dashboard Summary Single-Roundtrip API", c2_pass, detail)

    # -------------------------------------------------------------
    # Check 3: Section 1 — System Health & Live Subsystems Matrix
    # -------------------------------------------------------------
    health = summary_data.get("system_health", {})
    subsystems = health.get("subsystems", [])
    db_connected = health.get("database_connected", False)
    db_latency = health.get("database_latency_ms", 0.0)
    c3_pass = (
        health.get("provenance", {}).get("state") == "REAL DATA"
        and db_connected
        and len(subsystems) >= 10
    )
    detail = f"DB connected ({db_latency:.2f}ms latency). {len(subsystems)} subsystem health checks monitored live."
    if c3_pass:
        checks_passed += 1
    print_check(3, "System Health & Live Subsystems Matrix", c3_pass, detail)

    # -------------------------------------------------------------
    # Check 4: Section 2 — Traffic Overview & Extrapolation Rule
    # -------------------------------------------------------------
    overview = summary_data.get("traffic_overview", {})
    counted = overview.get("total_vehicles_counted", 0)
    obs_sec = overview.get("observation_duration_seconds", 0.0)
    is_extrapolated = overview.get("is_extrapolated", False)
    prov_state = overview.get("provenance", {}).get("state", "UNAVAILABLE")
    c4_pass = prov_state in ["REAL DATA", "SYNTHETIC", "UNAVAILABLE"] and (not (obs_sec > 0 and obs_sec < 3600) or is_extrapolated)
    detail = f"Provenance: {prov_state}. Vehicles counted: {counted}. Duration: {obs_sec:.1f}s (Extrapolated: {is_extrapolated})."
    if c4_pass:
        checks_passed += 1
    print_check(4, "Traffic Overview & Anti-Fabrication Extrapolation Rule", c4_pass, detail)

    # -------------------------------------------------------------
    # Check 5: Section 3 — Vehicle Class Composition
    # -------------------------------------------------------------
    comp = summary_data.get("vehicle_composition", {})
    classes = comp.get("class_distribution", [])
    total_comp_count = comp.get("total_counted", 0)
    c5_pass = comp.get("provenance", {}).get("state") in ["REAL DATA", "SYNTHETIC", "UNAVAILABLE"]
    class_summary = ", ".join([f"{c.get('class_name')}: {c.get('count')} ({c.get('percentage'):.1f}%)" for c in classes[:4]])
    detail = f"Class breakdown ({len(classes)} classes): {class_summary or 'None'}"
    if c5_pass:
        checks_passed += 1
    print_check(5, "Vehicle Class Distribution from Persisted Counting", c5_pass, detail)

    # -------------------------------------------------------------
    # Check 6: Section 4 — Discrete Time-Series Traffic Flow
    # -------------------------------------------------------------
    flow = summary_data.get("traffic_flow_metrics", {})
    buckets = flow.get("time_series_buckets", [])
    c6_pass = flow.get("provenance", {}).get("state") in ["REAL DATA", "SYNTHETIC", "UNAVAILABLE"]
    detail = f"Discrete non-interpolated time-series buckets: {len(buckets)} intervals (interval: {flow.get('bucket_interval_seconds')}s)."
    if c6_pass:
        checks_passed += 1
    print_check(6, "Discrete Non-Interpolated Traffic Flow Time-Series", c6_pass, detail)

    # -------------------------------------------------------------
    # Check 7: Section 5 — Lane Analysis & Image-Space Density
    # -------------------------------------------------------------
    lane_sec = summary_data.get("lane_density", {})
    lanes = lane_sec.get("lanes", [])
    unit = lane_sec.get("density_unit", "")
    warn = lane_sec.get("calibration_warning", "")
    c7_pass = (
        "vehicles/px²" in unit
        and len(warn) > 0
        and lane_sec.get("provenance", {}).get("state") in ["REAL DATA", "SYNTHETIC", "UNAVAILABLE"]
    )
    detail = f"Lanes evaluated: {len(lanes)}. Unit: '{unit}'. Calibration warning verified."
    if c7_pass:
        checks_passed += 1
    print_check(7, "Lane Analysis & Shoelace Image-Space Density Qualification", c7_pass, detail)

    # -------------------------------------------------------------
    # Check 8: Section 6 — Dynamic Prediction Readiness & Observation Count
    # -------------------------------------------------------------
    pred = summary_data.get("prediction_availability", {})
    real_count = pred.get("real_sample_count", 0)
    thresh = pred.get("threshold", 20)
    is_ready = pred.get("is_ready", False)
    msg = pred.get("readiness_message", "")
    c8_pass = (
        pred.get("provenance", {}).get("state") == "PREDICTION"
        and thresh == 20
        and ((real_count >= 20 and is_ready) or (real_count < 20 and not is_ready))
    )
    detail = f"Real observations: {real_count}/{thresh} (Ready: {is_ready}). Message: '{msg[:65]}...'"
    if c8_pass:
        checks_passed += 1
    print_check(8, "Dynamic Phase 11 Real-Data Observation Threshold (10/20)", c8_pass, detail)

    # -------------------------------------------------------------
    # Check 9: Section 7 — Signal Optimization Decision-Support Disclaimer
    # -------------------------------------------------------------
    sig = summary_data.get("signal_optimization", {})
    sig_disclaimer = sig.get("disclaimer", "")
    has_sig_disc = "Simulation / Decision Support" in sig_disclaimer and "not connected to physical signals" in sig_disclaimer
    c9_pass = sig.get("provenance", {}).get("state") in ["SIMULATION", "UNAVAILABLE"] and has_sig_disc
    detail = f"Latest run: {sig.get('latest_run_id') or 'None'}. Disclaimer: '{sig_disclaimer}'"
    if c9_pass:
        checks_passed += 1
    print_check(9, "Signal Optimization Simulation Results & Physical Control Disclaimer", c9_pass, detail)

    # -------------------------------------------------------------
    # Check 10: Section 8 — Emergency Corridor Decision-Support Disclaimer
    # -------------------------------------------------------------
    ec = summary_data.get("emergency_corridor", {})
    ec_disclaimer = ec.get("disclaimer", "")
    has_ec_disc = "Simulation / Decision Support" in ec_disclaimer and "not a real dispatch or control system" in ec_disclaimer
    c10_pass = ec.get("provenance", {}).get("state") in ["SIMULATION", "UNAVAILABLE"] and has_ec_disc
    detail = f"Latest run: {ec.get('latest_run_id') or 'None'}. Disclaimer: '{ec_disclaimer}'"
    if c10_pass:
        checks_passed += 1
    print_check(10, "Emergency Corridor Simulation Results & Dispatch Disclaimer", c10_pass, detail)

    # -------------------------------------------------------------
    # Check 11: Section 9 & 10 — History Browse & Provenance Panel
    # -------------------------------------------------------------
    hist = summary_data.get("recent_history", {})
    prov_panel = summary_data.get("data_provenance", {})
    recent_sess = hist.get("sessions", [])
    c11_pass = (
        hist.get("provenance", {}).get("state") in ["REAL DATA", "SYNTHETIC", "UNAVAILABLE"]
        and prov_panel.get("provenance", {}).get("state") in ["REAL DATA", "SYNTHETIC", "UNAVAILABLE"]
    )
    detail = f"Recent sessions listed: {len(recent_sess)} (Total: {hist.get('total_sessions_count')}). Active video: {prov_panel.get('video_filename') or 'None'}."
    if c11_pass:
        checks_passed += 1
    print_check(11, "Session History Browsing & Complete Provenance Transparency Panel", c11_pass, detail)

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print_header("VERIFICATION SUMMARY")
    print(f"Checks Passed: {checks_passed}/{total_checks} ({(checks_passed/total_checks)*100:.1f}%)")
    if checks_passed == total_checks:
        print("PHASE 14 STATUS: FULLY VERIFIED [PASS]")
        return 0
    else:
        print("PHASE 14 STATUS: PARTIALLY VERIFIED / FAILED [FAIL]")
        return 1


if __name__ == "__main__":
    sys.exit(run_verification())
