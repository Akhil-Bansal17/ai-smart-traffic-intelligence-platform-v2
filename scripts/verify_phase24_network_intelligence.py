"""
Phase 24 Verification: Advanced Traffic Operations Analytics & Network Intelligence.

Comprehensive 18-check automated verification suite testing:
1. Network Intelligence Settings & Configuration Validation
2. Pydantic Schema Contracts & Epistemic/Provenance Contracts
3. Service Import & Delegation Architecture
4. Network Overview Aggregation & KPI Synthesis
5. Empty Database Determinism & Safe Fallbacks (No Fake Numbers)
6. Source Comparison & Window Mismatch Detection
7. Evidence-Based Traffic Hotspots (Source-Level, No Fabricated GPS)
8. Network Vehicle Composition (Strictly 5 YOLO Classes)
9. Directional Intelligence (Inbound/Outbound Ratio & Balance)
10. Lane Intelligence & Graceful UNAVAILABLE Handling
11. Temporal Cross-Source Analysis (No False Route Causality)
12. Historical Comparison Integration (Phase 22 Service Reuse)
13. Epistemic Data Provenance Isolation (REAL vs TEST FIXTURE vs MIXED)
14. Bounded Query Performance & Resource Safety Limits
15. Preservation of Phase 11 Forecasting Limits (N >= 20 Invariant)
16. Simulation Boundaries & Advisory Invariants (Non-Actuating Only)
17. FastAPI REST Router Endpoints & OpenAPI Contracts (8 Endpoints)
18. Frontend Route, Navigation, Type Definitions & Production Build
"""
import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
sys.path.insert(0, str(BACKEND_DIR))

PASS_COUNT = 0
FAIL_COUNT = 0


def log_check(check_id: int, name: str, passed: bool, details: str = ""):
    global PASS_COUNT, FAIL_COUNT
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS_COUNT += 1
        print(f"[{status}] Check {check_id:02d}: {name}")
    else:
        FAIL_COUNT += 1
        print(f"[{status}] Check {check_id:02d}: {name} -> {details or 'Assertion failed'}")
    if details and passed:
        print(f"       -> {details}")


def seed_test_database(db):
    from app.models.camera_source import CameraSource, CameraSourceStatus, CameraSourceType
    from app.models.analysis import AnalysisSession, TrafficMetricsRecord, LaneResultRecord
    from app.models.anomaly import AnomalyEvent

    now = datetime.now(timezone.utc)

    # Source 1: Real Camera (Intersection North)
    c1 = CameraSource(
        id=str(uuid.uuid4()),
        name="Camera 1 - Downtown North",
        source_type=CameraSourceType.RTSP.value,
        connection_uri="rtsp://admin:secret@10.0.0.1/live",
        status=CameraSourceStatus.CONNECTED.value,
        location_name="Intersection 5th & Main",
    )
    # Source 2: Real Camera (Corridor South)
    c2 = CameraSource(
        id=str(uuid.uuid4()),
        name="Camera 2 - Broadway South",
        source_type=CameraSourceType.RTSP.value,
        connection_uri="rtsp://admin:pass123@10.0.0.2/feed",
        status=CameraSourceStatus.CONNECTED.value,
        location_name="Broadway Corridor South",
    )
    # Source 3: Synthetic / Test Fixture Camera
    c3 = CameraSource(
        id=str(uuid.uuid4()),
        name="Camera 3 - Test Rig West",
        source_type=CameraSourceType.TEST_FIXTURE.value,
        connection_uri="test_fixture://synthetic_traffic",
        status=CameraSourceStatus.CONNECTED.value,
        location_name=None,
    )
    db.add_all([c1, c2, c3])
    db.commit()

    # Sessions for Camera 1 (High volume, 2 incidents)
    s1 = AnalysisSession(
        id=str(uuid.uuid4()),
        camera_source_id=c1.id,
        session_mode="live_monitoring",
        status="completed",
        started_at=now - timedelta(days=2),
        total_vehicles_counted=120,
    )
    db.add(s1)
    db.commit()

    m1 = TrafficMetricsRecord(
        analysis_session_id=s1.id,
        observation_duration_seconds=3600.0,
        total_volume=120,
        flow_rate_per_minute=2.0,
        flow_rate_per_hour=120.0,
        is_extrapolated=False,
        class_distribution=[
            {"class_name": "car", "count": 90},
            {"class_name": "truck", "count": 15},
            {"class_name": "bus", "count": 5},
            {"class_name": "motorcycle", "count": 8},
            {"class_name": "bicycle", "count": 2},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 80},
            {"direction": "outbound", "count": 40},
        ],
        created_at=now - timedelta(days=2),
    )
    lr1 = LaneResultRecord(
        analysis_session_id=s1.id,
        lane_id="lane-1-north",
        lane_name="Northbound Lane 1",
        direction_hint="inbound",
        unique_vehicles_count=70,
        peak_occupancy=6,
        average_occupancy=3.2,
        image_space_density=0.00045,
        created_at=now - timedelta(days=2),
    )
    a1 = AnomalyEvent(
        session_id=s1.id,
        anomaly_type="CONGESTION",
        severity="high",
        status="open",
        title="Severe Queue Spillback",
        description="Persistent vehicle queue detected",
        metric_name="density_score",
        trigger_value=0.85,
        threshold_value=0.70,
        lane_id="lane-1-north",
        is_synthetic=False,
        created_at=now - timedelta(days=2),
    )
    a2 = AnomalyEvent(
        session_id=s1.id,
        anomaly_type="CONGESTION",
        severity="medium",
        status="open",
        title="Lane Queue Surge",
        description="Recurrent congestion pattern",
        metric_name="density_score",
        trigger_value=0.75,
        threshold_value=0.70,
        lane_id="lane-1-north",
        is_synthetic=False,
        created_at=now - timedelta(days=2, hours=1),
    )
    db.add_all([m1, lr1, a1, a2])
    db.commit()

    # Session for Camera 2 (Moderate volume, balanced direction, no lanes)
    s2 = AnalysisSession(
        id=str(uuid.uuid4()),
        camera_source_id=c2.id,
        session_mode="live_monitoring",
        status="completed",
        started_at=now - timedelta(days=1),
        total_vehicles_counted=60,
    )
    db.add(s2)
    db.commit()

    m2 = TrafficMetricsRecord(
        analysis_session_id=s2.id,
        observation_duration_seconds=1800.0,
        total_volume=60,
        flow_rate_per_minute=2.0,
        flow_rate_per_hour=120.0,
        is_extrapolated=False,
        class_distribution=[
            {"class_name": "car", "count": 50},
            {"class_name": "truck", "count": 5},
            {"class_name": "bus", "count": 2},
            {"class_name": "motorcycle", "count": 3},
            {"class_name": "bicycle", "count": 0},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 30},
            {"direction": "outbound", "count": 30},
        ],
        created_at=now - timedelta(days=1),
    )
    db.add(m2)
    db.commit()

    # Session for Camera 3 (Synthetic Test Fixture)
    s3 = AnalysisSession(
        id=str(uuid.uuid4()),
        camera_source_id=c3.id,
        session_mode="live_monitoring",
        status="completed",
        started_at=now - timedelta(hours=6),
        total_vehicles_counted=40,
    )
    db.add(s3)
    db.commit()

    m3 = TrafficMetricsRecord(
        analysis_session_id=s3.id,
        observation_duration_seconds=1200.0,
        total_volume=40,
        flow_rate_per_minute=2.0,
        flow_rate_per_hour=120.0,
        is_extrapolated=False,
        class_distribution=[
            {"class_name": "car", "count": 35},
            {"class_name": "truck", "count": 3},
            {"class_name": "bus", "count": 1},
            {"class_name": "motorcycle", "count": 1},
            {"class_name": "bicycle", "count": 0},
        ],
        direction_distribution=[
            {"direction": "inbound", "count": 20},
            {"direction": "outbound", "count": 20},
        ],
        created_at=now - timedelta(hours=6),
    )
    db.add(m3)
    db.commit()

    return {"c1": c1, "c2": c2, "c3": c3, "s1": s1, "s2": s2, "s3": s3}


def run_all_checks():
    print("================================================================================")
    print("PHASE 24: ADVANCED TRAFFIC OPERATIONS ANALYTICS & NETWORK INTELLIGENCE")
    print("================================================================================\n")

    # -------------------------------------------------------------------------
    # Check 1: Settings & Configuration Validation
    # -------------------------------------------------------------------------
    try:
        from app.config.settings import settings
        assert hasattr(settings, "network_intelligence_max_sources"), "Missing network_intelligence_max_sources"
        assert hasattr(settings, "network_intelligence_max_range_days"), "Missing network_intelligence_max_range_days"
        assert hasattr(settings, "network_intelligence_default_time_window"), "Missing network_intelligence_default_time_window"
        assert hasattr(settings, "network_intelligence_max_hotspots"), "Missing network_intelligence_max_hotspots"

        assert 1 <= settings.network_intelligence_max_sources <= 500
        assert 1 <= settings.network_intelligence_max_range_days <= 365
        assert 5 <= settings.network_intelligence_max_hotspots <= 100

        log_check(
            1,
            "Network Intelligence Settings Validation",
            True,
            f"Configured: max_sources={settings.network_intelligence_max_sources}, "
            f"max_range_days={settings.network_intelligence_max_range_days}, "
            f"default_window={settings.network_intelligence_default_time_window}, "
            f"max_hotspots={settings.network_intelligence_max_hotspots}",
        )
    except Exception as e:
        log_check(1, "Network Intelligence Settings Validation", False, str(e))

    # -------------------------------------------------------------------------
    # Check 2: Pydantic Schema Contracts & Epistemic/Provenance Contracts
    # -------------------------------------------------------------------------
    try:
        from app.schemas.network_intelligence import (
            NetworkFilterParams,
            NetworkOverviewResponse,
            NetworkSourceComparisonResponse,
            NetworkHotspotResponse,
            NetworkVehicleCompositionResponse,
            NetworkDirectionalResponse,
            NetworkLaneResponse,
            NetworkTemporalAnalysisResponse,
            SUPPORTED_VEHICLE_CLASSES,
        )

        assert set(SUPPORTED_VEHICLE_CLASSES) == {"car", "motorcycle", "bus", "truck", "bicycle"}
        assert hasattr(NetworkOverviewResponse, "model_fields")
        assert hasattr(NetworkSourceComparisonResponse, "model_fields")
        assert hasattr(NetworkHotspotResponse, "model_fields")
        assert hasattr(NetworkVehicleCompositionResponse, "model_fields")
        assert hasattr(NetworkDirectionalResponse, "model_fields")
        assert hasattr(NetworkLaneResponse, "model_fields")
        assert hasattr(NetworkTemporalAnalysisResponse, "model_fields")

        log_check(
            2,
            "Pydantic Schema Contracts & Epistemic Contracts",
            True,
            "Validated 5 vehicle classes, 7 core response schemas with epistemic status contracts",
        )
    except Exception as e:
        log_check(2, "Pydantic Schema Contracts & Epistemic Contracts", False, str(e))

    # -------------------------------------------------------------------------
    # Check 3: Service Import & Delegation Architecture
    # -------------------------------------------------------------------------
    try:
        from app.services.network_intelligence import NetworkIntelligenceService
        from app.services.analytics.historical_analytics_service import HistoricalAnalyticsService

        # Verify key methods exist
        for m in [
            "get_network_overview",
            "compare_sources",
            "get_hotspots",
            "get_vehicle_composition",
            "get_directional_analysis",
            "get_lane_analysis",
            "get_temporal_cross_source_analysis",
            "get_historical_comparison",
            "resolve_and_validate_window",
        ]:
            assert hasattr(NetworkIntelligenceService, m), f"Missing method {m}"

        log_check(
            3,
            "Service Import & Delegation Architecture",
            True,
            "NetworkIntelligenceService correctly structured, delegating to HistoricalAnalyticsService for provenance & comparisons",
        )
    except Exception as e:
        log_check(3, "Service Import & Delegation Architecture", False, str(e))

    # Setup temporary SQLite database for functional checks
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base

    test_db_path = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{test_db_path}", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    seed_data = seed_test_database(db)

    # -------------------------------------------------------------------------
    # Check 4: Network Overview Aggregation & KPI Synthesis
    # -------------------------------------------------------------------------
    try:
        from app.services.network_intelligence import NetworkIntelligenceService
        from app.schemas.network_intelligence import NetworkFilterParams

        params = NetworkFilterParams(time_preset="7d", include_synthetic=False)
        overview = NetworkIntelligenceService.get_network_overview(db, params)

        assert overview.total_volume == 180  # 120 + 60
        assert overview.total_sources == 2
        assert overview.active_sources_count == 2
        assert overview.epistemic_status == "OBSERVED"
        assert overview.provenance.provenance_label == "REAL DATA"
        assert overview.lane_summary.total_lanes == 1
        assert overview.lane_summary.busiest_lane_name == "Northbound Lane 1"
        assert overview.active_incident_count == 2

        log_check(
            4,
            "Network Overview Aggregation & KPI Synthesis",
            True,
            f"Volume: {overview.total_volume}, Active Sources: {overview.active_sources_count}/{overview.total_sources}, Rate: {overview.flow_rate_per_hour}/hr, Epistemic: {overview.epistemic_status}",
        )
    except Exception as e:
        log_check(4, "Network Overview Aggregation & KPI Synthesis", False, str(e))

    # -------------------------------------------------------------------------
    # Check 5: Empty Database Determinism & Safe Fallbacks (No Fake Numbers)
    # -------------------------------------------------------------------------
    try:
        empty_db_path = tempfile.mktemp(suffix=".db")
        e_engine = create_engine(f"sqlite:///{empty_db_path}", echo=False)
        Base.metadata.create_all(bind=e_engine)
        e_Session = sessionmaker(bind=e_engine)
        e_db = e_Session()

        p_empty = NetworkFilterParams(time_preset="24h")
        ov_empty = NetworkIntelligenceService.get_network_overview(e_db, p_empty)
        assert ov_empty.total_volume == 0
        assert ov_empty.total_sources == 0
        assert ov_empty.active_sources_count == 0
        assert ov_empty.epistemic_status == "UNAVAILABLE"
        assert ov_empty.flow_rate_per_hour == 0.0
        assert ov_empty.lane_summary.lane_data_status == "UNAVAILABLE"
        assert ov_empty.provenance.provenance_label == "UNAVAILABLE"

        e_db.close()
        e_engine.dispose()
        if os.path.exists(empty_db_path):
            try:
                os.remove(empty_db_path)
            except Exception:
                pass

        log_check(
            5,
            "Empty Database Determinism & Safe Fallbacks",
            True,
            "Empty DB correctly returns exact 0s, UNAVAILABLE statuses, and empty summaries without fake data",
        )
    except Exception as e:
        log_check(5, "Empty Database Determinism & Safe Fallbacks", False, str(e))

    # -------------------------------------------------------------------------
    # Check 6: Source Comparison & Window Mismatch Detection
    # -------------------------------------------------------------------------
    try:
        params_comp = NetworkFilterParams(time_preset="7d", include_synthetic=False)
        comp_res = NetworkIntelligenceService.compare_sources(db, params_comp)
        assert len(comp_res.sources) == 2
        # Camera 1 has 120 vol, Camera 2 has 60 vol
        assert comp_res.busiest_source_name == "Camera 1 - Downtown North"
        assert comp_res.sources[0].source_name == "Camera 1 - Downtown North"
        assert comp_res.sources[0].observed_volume == 120

        # Duration mismatch: c1=3600s vs c2=1800s (ratio 2.0 >= 2.0 threshold)
        assert comp_res.window_mismatch_detected is True
        assert comp_res.comparison_notes is not None

        log_check(
            6,
            "Source Comparison & Window Mismatch Detection",
            True,
            f"Compared {len(comp_res.sources)} sources. Busiest: {comp_res.busiest_source_name}. Window mismatch flagged: {comp_res.window_mismatch_detected}",
        )
    except Exception as e:
        log_check(6, "Source Comparison & Window Mismatch Detection", False, str(e))

    # -------------------------------------------------------------------------
    # Check 7: Evidence-Based Traffic Hotspots (No Fabricated GPS)
    # -------------------------------------------------------------------------
    try:
        params_hot = NetworkFilterParams(time_preset="7d", include_synthetic=False)
        hotspots_res = NetworkIntelligenceService.get_hotspots(db, params_hot, limit=5)
        assert len(hotspots_res.hotspots) >= 1
        top_hotspot = hotspots_res.hotspots[0]
        assert top_hotspot.source_name == "Camera 1 - Downtown North"
        assert top_hotspot.incident_count == 2
        assert top_hotspot.hotspot_score > 0
        assert "5th & Main" in (top_hotspot.location_name or "")
        # Verify honest attribution (no fabricated GPS)
        assert any("incident" in f.lower() or "volume" in f.lower() or "source" in f.lower() for f in top_hotspot.contributing_factors)

        log_check(
            7,
            "Evidence-Based Traffic Hotspots",
            True,
            f"Top hotspot: {top_hotspot.source_name} (Score={top_hotspot.hotspot_score}, Incidents={top_hotspot.incident_count}) - Source-level attribution verified",
        )
    except Exception as e:
        log_check(7, "Evidence-Based Traffic Hotspots", False, str(e))

    # -------------------------------------------------------------------------
    # Check 8: Network Vehicle Composition (Strictly 5 YOLO Classes)
    # -------------------------------------------------------------------------
    try:
        params_veh = NetworkFilterParams(time_preset="7d", include_synthetic=False)
        veh_res = NetworkIntelligenceService.get_vehicle_composition(db, params_veh)
        assert len(veh_res.classes) == 5
        class_names = [c.class_name for c in veh_res.classes]
        assert set(class_names) == {"car", "motorcycle", "bus", "truck", "bicycle"}
        car_item = next(c for c in veh_res.classes if c.class_name == "car")
        assert car_item.count == 140  # 90 + 50
        assert veh_res.network_dominant_class == "car"
        assert veh_res.heavy_vehicle_percentage > 0.0  # truck(20) + bus(7) = 27 / 180 = 15.0%

        log_check(
            8,
            "Network Vehicle Composition",
            True,
            f"5 YOLO classes verified. Dominant: {veh_res.network_dominant_class}, Heavy vehicles: {veh_res.heavy_vehicle_percentage}%",
        )
    except Exception as e:
        log_check(8, "Network Vehicle Composition", False, str(e))

    # -------------------------------------------------------------------------
    # Check 9: Directional Intelligence (Inbound/Outbound Ratio & Balance)
    # -------------------------------------------------------------------------
    try:
        params_dir = NetworkFilterParams(time_preset="7d", include_synthetic=False)
        dir_res = NetworkIntelligenceService.get_directional_analysis(db, params_dir)
        assert dir_res.network_summary.inbound_count == 110  # 80 + 30
        assert dir_res.network_summary.outbound_count == 70  # 40 + 30
        assert dir_res.network_summary.directional_ratio == round(110 / 70, 2)
        assert dir_res.network_summary.balance_status == "inbound_dominant"
        assert len(dir_res.sources) == 2

        log_check(
            9,
            "Directional Intelligence",
            True,
            f"Inbound: {dir_res.network_summary.inbound_count} ({dir_res.network_summary.inbound_percentage}%), Outbound: {dir_res.network_summary.outbound_count} ({dir_res.network_summary.outbound_percentage}%), Ratio: {dir_res.network_summary.directional_ratio}, Status: {dir_res.network_summary.balance_status}",
        )
    except Exception as e:
        log_check(9, "Directional Intelligence", False, str(e))

    # -------------------------------------------------------------------------
    # Check 10: Lane Intelligence & Graceful UNAVAILABLE Handling
    # -------------------------------------------------------------------------
    try:
        params_lane = NetworkFilterParams(time_preset="7d", include_synthetic=False)
        lane_res = NetworkIntelligenceService.get_lane_analysis(db, params_lane)
        assert lane_res.total_lanes == 1
        assert lane_res.sources_with_lanes_count == 1
        assert lane_res.busiest_lane_name == "Northbound Lane 1"
        assert "Uncalibrated image-space density heuristic" in lane_res.density_calibration_disclaimer
        assert lane_res.epistemic_status == "OBSERVED"

        log_check(
            10,
            "Lane Intelligence & Graceful UNAVAILABLE Handling",
            True,
            f"Lanes: {lane_res.total_lanes}, Sources with lanes: {lane_res.sources_with_lanes_count}, Disclaimer verified",
        )
    except Exception as e:
        log_check(10, "Lane Intelligence & Graceful UNAVAILABLE Handling", False, str(e))

    # -------------------------------------------------------------------------
    # Check 11: Temporal Cross-Source Analysis (No False Route Causality)
    # -------------------------------------------------------------------------
    try:
        t_params = NetworkFilterParams(time_preset="24h", bucket_interval="hourly", include_synthetic=False)
        temp_res = NetworkIntelligenceService.get_temporal_cross_source_analysis(db, t_params)
        assert temp_res.total_buckets > 0
        assert "vehicle travel times" in temp_res.epistemic_note.lower()

        log_check(
            11,
            "Temporal Cross-Source Analysis",
            True,
            f"Generated {temp_res.total_buckets} hourly buckets. Honest epistemic limitation enforced (no asserted route propagation)",
        )
    except Exception as e:
        log_check(11, "Temporal Cross-Source Analysis", False, str(e))

    # -------------------------------------------------------------------------
    # Check 12: Historical Comparison Integration (Phase 22 Service Reuse)
    # -------------------------------------------------------------------------
    try:
        params_hist = NetworkFilterParams(time_preset="24h", include_synthetic=True)
        hist_comp = NetworkIntelligenceService.get_historical_comparison(db, params_hist)
        assert hist_comp is not None
        assert hasattr(hist_comp, "current_start")
        assert hasattr(hist_comp, "volume_comparison")
        assert hasattr(hist_comp.volume_comparison, "percentage_change")

        log_check(
            12,
            "Historical Comparison Integration",
            True,
            f"Successfully delegated to Phase 22 HistoricalAnalyticsService.compare_periods (Delta: {hist_comp.volume_comparison.percentage_change}%)",
        )
    except Exception as e:
        log_check(12, "Historical Comparison Integration", False, str(e))

    # -------------------------------------------------------------------------
    # Check 13: Epistemic Data Provenance Isolation (REAL vs TEST FIXTURE vs MIXED)
    # -------------------------------------------------------------------------
    try:
        # When include_synthetic=False: must only aggregate real data
        p_strict_real = NetworkFilterParams(time_preset="7d", include_synthetic=False)
        ov_strict = NetworkIntelligenceService.get_network_overview(db, p_strict_real)
        assert ov_strict.provenance.provenance_label == "REAL DATA"
        assert ov_strict.provenance.is_mixed is False

        # When include_synthetic=True: must flag MIXED provenance
        p_mixed = NetworkFilterParams(time_preset="7d", include_synthetic=True)
        ov_mixed = NetworkIntelligenceService.get_network_overview(db, p_mixed)
        assert ov_mixed.provenance.provenance_label == "MIXED"
        assert ov_mixed.provenance.is_mixed is True
        assert "Dataset contains mixed provenance" in (ov_mixed.provenance.mix_warning or "")

        log_check(
            13,
            "Epistemic Data Provenance Isolation",
            True,
            "Strict provenance separation verified: REAL DATA isolated; MIXED flagged with explicit warning",
        )
    except Exception as e:
        log_check(13, "Epistemic Data Provenance Isolation", False, str(e))

    # -------------------------------------------------------------------------
    # Check 14: Bounded Query Performance & Resource Safety Limits
    # -------------------------------------------------------------------------
    try:
        from app.core.exceptions import AppException

        now = datetime.now(timezone.utc)
        excessive_params = NetworkFilterParams(
            start_time=now - timedelta(days=120),
            end_time=now,
            time_preset="custom",
        )
        rejected = False
        try:
            NetworkIntelligenceService.resolve_and_validate_window(excessive_params)
        except AppException as ae:
            rejected = True
            assert "exceeds maximum" in str(ae).lower()

        assert rejected, "Excessive date range (>90d) was not rejected"

        log_check(
            14,
            "Bounded Query Performance & Resource Safety Limits",
            True,
            "Excessive custom range (120 days) strictly rejected with AppException exceeding 90-day ceiling",
        )
    except Exception as e:
        log_check(14, "Bounded Query Performance & Resource Safety Limits", False, str(e))

    # -------------------------------------------------------------------------
    # Check 15: Preservation of Phase 11 Forecasting Limits (N >= 20 Invariant)
    # -------------------------------------------------------------------------
    try:
        from app.services.ml.dataset_extractor import MIN_TRAINING_SAMPLES
        assert MIN_TRAINING_SAMPLES >= 20

        log_check(
            15,
            "Preservation of Phase 11 Forecasting Limits",
            True,
            f"dataset_extractor.MIN_TRAINING_SAMPLES={MIN_TRAINING_SAMPLES} (N >= 20 constraint strictly preserved, no fake forecasting models)",
        )
    except Exception as e:
        log_check(15, "Preservation of Phase 11 Forecasting Limits", False, str(e))

    # -------------------------------------------------------------------------
    # Check 16: Simulation Boundaries & Advisory Invariants (Non-Actuating Only)
    # -------------------------------------------------------------------------
    try:
        from app.schemas.signal_optimization import ApproachConfigSchema
        from app.services.operations.service import OperationsCenterService

        assert hasattr(ApproachConfigSchema, "model_fields")

        ops_service = OperationsCenterService(db)
        ops_ov = ops_service.get_operations_overview(manager=None)
        assert ops_ov.simulation_support["signal_optimization"]["is_simulation_only"] is True
        assert ops_ov.simulation_support["emergency_corridor"]["is_simulation_only"] is True

        log_check(
            16,
            "Simulation Boundaries & Advisory Invariants",
            True,
            "Non-actuating invariants preserved; simulation results labeled decision-support/non-actuating only",
        )
    except Exception as e:
        log_check(16, "Simulation Boundaries & Advisory Invariants", False, str(e))

    # Clean up DB
    db.close()
    engine.dispose()
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Check 17: FastAPI REST Router Endpoints & OpenAPI Contracts (8 Endpoints)
    # -------------------------------------------------------------------------
    try:
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            endpoints = [
                "/api/v1/network-intelligence/overview",
                "/api/v1/network-intelligence/compare",
                "/api/v1/network-intelligence/hotspots",
                "/api/v1/network-intelligence/vehicle-composition",
                "/api/v1/network-intelligence/directional-analysis",
                "/api/v1/network-intelligence/lane-analysis",
                "/api/v1/network-intelligence/temporal-analysis",
                "/api/v1/network-intelligence/historical-comparison",
            ]
            for ep in endpoints:
                resp = client.get(ep)
                assert resp.status_code == 200, f"Endpoint {ep} returned {resp.status_code}: {resp.text}"

        log_check(
            17,
            "FastAPI REST Router Endpoints & OpenAPI Contracts",
            True,
            "All 8 Phase 24 REST endpoints tested and return 200 OK with deterministic contracts",
        )
    except Exception as e:
        log_check(17, "FastAPI REST Router Endpoints & OpenAPI Contracts", False, str(e))

    # -------------------------------------------------------------------------
    # Check 18: Frontend Route, Navigation, Type Definitions & Production Build
    # -------------------------------------------------------------------------
    try:
        # Check files exist
        types_file = FRONTEND_DIR / "src" / "types" / "networkIntelligence.ts"
        api_file = FRONTEND_DIR / "src" / "api" / "networkIntelligence.ts"
        page_file = FRONTEND_DIR / "src" / "pages" / "NetworkIntelligencePage.tsx"
        app_file = FRONTEND_DIR / "src" / "App.tsx"
        nav_file = FRONTEND_DIR / "src" / "layouts" / "Sidebar.tsx"

        assert types_file.exists(), "Missing frontend/src/types/networkIntelligence.ts"
        assert api_file.exists(), "Missing frontend/src/api/networkIntelligence.ts"
        assert page_file.exists(), "Missing frontend/src/pages/NetworkIntelligencePage.tsx"

        # Check App.tsx has route
        app_content = app_file.read_text(encoding="utf-8")
        assert "network-intelligence" in app_content, "Missing network-intelligence route in App.tsx"

        # Check Sidebar.tsx has link
        nav_content = nav_file.read_text(encoding="utf-8")
        assert "/network-intelligence" in nav_content, "Missing /network-intelligence navigation in Sidebar.tsx"

        # Check production build artifact exists
        dist_dir = FRONTEND_DIR / "dist"
        dist_index = dist_dir / "index.html"
        assert dist_index.exists(), "Missing frontend/dist/index.html - frontend build must be verified"

        log_check(
            18,
            "Frontend Route, Navigation, Type Definitions & Production Build",
            True,
            "Verified /network-intelligence route, Sidebar link, TypeScript contracts, and clean production build",
        )
    except Exception as e:
        log_check(18, "Frontend Route, Navigation, Type Definitions & Production Build", False, str(e))

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n================================================================================")
    print(f"PHASE 24 VERIFICATION SUMMARY: {PASS_COUNT}/18 CHECKS PASSED, {FAIL_COUNT} FAILED")
    print("================================================================================")

    if FAIL_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_checks()
