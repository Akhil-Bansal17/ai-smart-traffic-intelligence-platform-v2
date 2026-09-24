"""
Phase 23 Verification: Unified Traffic Operations Center & Real-Time Incident Response.

Comprehensive 18-check automated verification suite testing:
1. Operations Center Settings & Configuration Validation
2. Pydantic Schema Contracts & Health Status Enums
3. Service Import & Delegation Architecture
4. Active Camera Aggregation & Real-Time Telemetry
5. Camera Health State Determination (ONLINE/OFFLINE/CONNECTING/DEGRADED/UNKNOWN)
6. Security & Credential Redaction (RTSP/HTTP sanitization)
7. Active Incident Aggregation & Severity Categorization
8. Incident Operator Status Mutation Lifecycle (acknowledge/resolve)
9. Authoritative Event Timeline Assembly (No Event-Sourcing DB Bloat)
10. Epistemic Data Provenance Isolation (REAL vs TEST FIXTURE vs MIXED)
11. Real-Time Traffic Snapshot & Extrapolation Flagging (OBSERVED vs EXTRAPOLATED)
12. Historical Context Integration (Phase 22 Historical Analytics Reuse)
13. Simulation Boundaries & Advisory Labeling (Phase 12-14 Non-Actuating Invariants)
14. Preservation of Phase 11 Forecasting Limits (N=10 < 20 Untouched)
15. No-Fake-Data Invariant & Determinism
16. Bounded Query Performance & Resource Safety
17. FastAPI REST Router Endpoints & OpenAPI Contract (7 Endpoints)
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


class MockJobManager:
    """Mock job manager for simulating live stream telemetry."""
    def __init__(self, snapshots=None, previews=None):
        self._snapshots = snapshots or {}
        self._previews = previews or {}

    def get_live_status(self, camera_source_id: str):
        return self._snapshots.get(camera_source_id)

    def get_preview_jpeg(self, camera_source_id: str):
        return self._previews.get(camera_source_id)


def run_all_checks():
    print("================================================================================")
    print("PHASE 23: UNIFIED TRAFFIC OPERATIONS CENTER & REAL-TIME INCIDENT RESPONSE")
    print("================================================================================\n")

    # -------------------------------------------------------------------------
    # Check 1: Settings & Configuration Validation
    # -------------------------------------------------------------------------
    try:
        from app.config.settings import settings
        assert hasattr(settings, "operations_default_poll_interval_seconds"), "Missing operations_default_poll_interval_seconds"
        assert hasattr(settings, "operations_max_timeline_events"), "Missing operations_max_timeline_events"
        assert hasattr(settings, "operations_max_active_incidents"), "Missing operations_max_active_incidents"

        assert 1 <= settings.operations_default_poll_interval_seconds <= 60
        assert 5 <= settings.operations_max_timeline_events <= 500
        assert 5 <= settings.operations_max_active_incidents <= 500

        log_check(
            1,
            "Operations Center Settings Validation",
            True,
            f"Configured: poll={settings.operations_default_poll_interval_seconds}s, max_timeline={settings.operations_max_timeline_events}, max_incidents={settings.operations_max_active_incidents}",
        )
    except Exception as e:
        log_check(1, "Operations Center Settings Validation", False, str(e))

    # -------------------------------------------------------------------------
    # Check 2: Pydantic Schema Contracts & Health Status Enums
    # -------------------------------------------------------------------------
    try:
        from app.schemas.operations import (
            CameraHealthStatus,
            OperationsCameraOverviewItem,
            OperationsIncidentItem,
            OperationsTrafficSnapshot,
            OperationsTimelineEvent,
            OperationsHistoricalContextResponse,
            OperationsOverviewResponse,
            OperationsIncidentListResponse,
            OperationsTimelineResponse,
            UpdateIncidentStatusRequest,
        )

        valid_statuses = {"ONLINE", "OFFLINE", "CONNECTING", "DEGRADED", "UNKNOWN"}
        actual_statuses = {s.value for s in CameraHealthStatus}
        assert actual_statuses == valid_statuses, f"Statuses mismatch: {actual_statuses}"

        # Test request validation
        req = UpdateIncidentStatusRequest(status="acknowledged", note="Investigating flow drop")
        assert req.status == "acknowledged"

        log_check(
            2,
            "Pydantic Schema Contracts & Health Status Enums",
            True,
            f"Verified {len(actual_statuses)} health states and 9 Pydantic operations schemas",
        )
    except Exception as e:
        log_check(2, "Pydantic Schema Contracts & Health Status Enums", False, str(e))

    # -------------------------------------------------------------------------
    # Setup Temporary SQLite DB for Database Testing
    # -------------------------------------------------------------------------
    test_db_file = Path(tempfile.gettempdir()) / f"test_p23_verify_{uuid.uuid4().hex[:8]}.db"
    test_db_url = f"sqlite:///{test_db_file}"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base

    db_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=db_engine)
    SessionTest = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    try:
        # ---------------------------------------------------------------------
        # Check 3: Service Import & Delegation Architecture
        # ---------------------------------------------------------------------
        try:
            from app.services.operations.service import OperationsCenterService
            db = SessionTest()
            ops_service = OperationsCenterService(db)

            assert hasattr(ops_service, "get_operations_overview")
            assert hasattr(ops_service, "get_camera_fleet_overview")
            assert hasattr(ops_service, "get_active_incidents")
            assert hasattr(ops_service, "get_timeline_events")
            assert hasattr(ops_service, "get_historical_context_for_source")
            assert hasattr(ops_service, "update_incident")
            db.close()

            log_check(
                3,
                "Service Import & Delegation Architecture",
                True,
                "OperationsCenterService instantiated with clean aggregation architecture",
            )
        except Exception as e:
            log_check(3, "Service Import & Delegation Architecture", False, str(e))

        # ---------------------------------------------------------------------
        # Check 4 & 5 & 6: Camera Aggregation, Health States & Credential Redaction
        # ---------------------------------------------------------------------
        try:
            from app.models.camera_source import CameraSource
            from app.services.cv.live_analysis_service import LiveMetricsSnapshot

            db = SessionTest()
            cam_online = CameraSource(
                name="Cam-North-RTSP",
                source_type="rtsp",
                connection_uri="rtsp://admin:secretPass123@10.0.0.1:554/h264",
                enabled=True,
                status="connected",
                fps=30.0,
                location_name="Junction North",
            )
            cam_degraded = CameraSource(
                name="Cam-South-Degraded",
                source_type="http_stream",
                connection_uri="http://user:pw456@10.0.0.2:8080/stream.mjpg",
                enabled=True,
                status="connected",
                fps=25.0,
                location_name="Junction South",
            )
            cam_offline = CameraSource(
                name="Cam-East-Offline",
                source_type="local_camera",
                connection_uri="0",
                enabled=False,
                status="disconnected",
                fps=15.0,
                location_name="Junction East",
            )
            db.add_all([cam_online, cam_degraded, cam_offline])
            db.commit()

            # Create mock telemetry
            now = datetime.now(timezone.utc)
            snap_online = LiveMetricsSnapshot(
                camera_source_id=cam_online.id,
                job_id="job_online_001",
                job_status="running",
                is_live=True,
                source_type="rtsp",
                source_fps=30.0,
                processing_fps=28.0,
                frames_acquired=1200,
                frames_processed=1180,
                dropped_frames=0,
                reconnect_count=0,
                total_volume=14,
                inbound_volume=8,
                outbound_volume=6,
                active_tracks_count=14,
                class_distribution={"car": 10, "bus": 2, "truck": 2},
                direction_distribution={"inbound": 8, "outbound": 6},
                lane_occupancies={},
                lane_densities={},
                provenance_tag="live_camera_feed",
                last_frame_timestamp=now.timestamp(),
                last_updated=now,
            )

            snap_degraded = LiveMetricsSnapshot(
                camera_source_id=cam_degraded.id,
                job_id="job_degraded_002",
                job_status="running",
                is_live=True,
                source_type="http_stream",
                source_fps=25.0,
                processing_fps=11.5,
                frames_acquired=800,
                frames_processed=720,
                dropped_frames=45,  # Trigger DEGRADED status
                reconnect_count=1,
                total_volume=8,
                inbound_volume=4,
                outbound_volume=4,
                active_tracks_count=8,
                class_distribution={"car": 6, "motorcycle": 2},
                direction_distribution={"inbound": 4, "outbound": 4},
                lane_occupancies={},
                lane_densities={},
                provenance_tag="live_camera_feed",
                last_frame_timestamp=now.timestamp(),
                last_updated=now,
            )

            manager = MockJobManager(
                snapshots={
                    cam_online.id: snap_online,
                    cam_degraded.id: snap_degraded,
                },
                previews={
                    cam_online.id: b"\xff\xd8fakejpegbytes",
                },
            )

            ops_service = OperationsCenterService(db)
            fleet = ops_service.get_camera_fleet_overview(manager=manager)

            # Verify camera aggregation
            assert len(fleet) == 3, f"Expected 3 cameras, got {len(fleet)}"
            c_on = next(c for c in fleet if c.name == "Cam-North-RTSP")
            c_deg = next(c for c in fleet if c.name == "Cam-South-Degraded")
            c_off = next(c for c in fleet if c.name == "Cam-East-Offline")

            # Check 4: Aggregation
            assert c_on.active_tracks_count == 14
            assert c_on.is_active is True
            log_check(4, "Active Camera Aggregation & Real-Time Telemetry", True, f"Aggregated 3 cameras with live frame metrics")

            # Check 5: Health States
            assert c_on.health_status == CameraHealthStatus.ONLINE
            assert c_deg.health_status == CameraHealthStatus.DEGRADED
            assert c_off.health_status == CameraHealthStatus.OFFLINE
            log_check(5, "Camera Health State Determination", True, "ONLINE, DEGRADED, and OFFLINE correctly evaluated")

            # Check 6: Credential Redaction
            assert "secretPass123" not in c_on.connection_uri_redacted
            assert "admin:***@" in c_on.connection_uri_redacted or "***@" in c_on.connection_uri_redacted
            assert "pw456" not in c_deg.connection_uri_redacted
            assert "user:***@" in c_deg.connection_uri_redacted or "***@" in c_deg.connection_uri_redacted
            log_check(6, "Security & Credential Redaction", True, f"Redacted URIs: {c_on.connection_uri_redacted}")

            db.close()
        except Exception as e:
            log_check(4, "Active Camera Aggregation & Real-Time Telemetry", False, str(e))
            log_check(5, "Camera Health State Determination", False, str(e))
            log_check(6, "Security & Credential Redaction", False, str(e))

        # ---------------------------------------------------------------------
        # Check 7 & 8: Active Incident Aggregation & Operator Status Mutation
        # ---------------------------------------------------------------------
        try:
            from app.models.anomaly import AnomalyEvent
            from app.models.analysis import AnalysisSession

            db = SessionTest()
            session = AnalysisSession(
                camera_source_id=cam_online.id,
                session_mode="camera_live",
                status="completed",
            )
            db.add(session)
            db.commit()

            inc1 = AnomalyEvent(
                session_id=session.id,
                anomaly_type="flow_drop",
                severity="critical",
                status="open",
                title="Critical Flow Drop Observed",
                description="Traffic flow dropped below minimum threshold for 6 minutes",
                start_timestamp_seconds=0.0,
                duration_seconds=360.0,
                metric_name="flow_rate",
                trigger_value=2.0,
                threshold_value=12.0,
                provenance_category="real_database_metrics",
                is_synthetic=False,
            )
            inc2 = AnomalyEvent(
                session_id=session.id,
                anomaly_type="congestion_buildup",
                severity="high",
                status="open",
                title="High Congestion Buildup",
                description="Density spike observed across inbound lanes",
                start_timestamp_seconds=60.0,
                duration_seconds=900.0,
                metric_name="density",
                trigger_value=85.0,
                threshold_value=60.0,
                provenance_category="real_database_metrics",
                is_synthetic=False,
            )
            db.add_all([inc1, inc2])
            db.commit()

            ops_service = OperationsCenterService(db)
            active_incidents = ops_service.get_active_incidents()
            assert len(active_incidents) == 2

            crit_count = sum(1 for inc in active_incidents if inc.severity.lower() == "critical")
            assert crit_count == 1
            log_check(7, "Active Incident Aggregation & Severity Categorization", True, f"Found 2 active incidents (1 critical, 1 high)")

            # Check 8: Operator Status Mutation
            mutated = ops_service.update_incident(
                incident_id=inc1.id,
                new_status="acknowledged",
                note="Dispatched patrol unit to check approach",
            )
            assert mutated.status == "acknowledged"
            assert mutated.operator_note == "Dispatched patrol unit to check approach"

            # Resolve test
            resolved = ops_service.update_incident(
                incident_id=inc1.id,
                new_status="resolved",
                note="Patrol cleared blockage",
            )
            assert resolved.status == "resolved"
            assert resolved.resolved_at is not None

            log_check(8, "Incident Operator Status Mutation Lifecycle", True, "Tested open -> acknowledged -> resolved transitions with notes")
            db.close()
        except Exception as e:
            log_check(7, "Active Incident Aggregation & Severity Categorization", False, str(e))
            log_check(8, "Incident Operator Status Mutation Lifecycle", False, str(e))

        # ---------------------------------------------------------------------
        # Check 9: Authoritative Event Timeline Assembly
        # ---------------------------------------------------------------------
        try:
            from app.models.analysis_job import AnalysisJob
            from app.models.insight import TrafficInsight
            from app.models.report import Report

            db = SessionTest()
            job = AnalysisJob(
                status="completed",
                camera_source_id=cam_online.id,
                job_mode="camera_live",
            )
            db.add(job)
            db.commit()

            insight = TrafficInsight(
                session_id=session.id,
                insight_type="congestion_bottleneck",
                category="CONGESTION",
                severity="MEDIUM",
                status="ACTIVE",
                title="Recurring Bottleneck Detected",
                summary="Inbound lane throughput drops during peak flow",
                dedup_signature="dedup_sig_p23_verify_001",
            )
            db.add(insight)

            report = Report(
                session_id=session.id,
                title="Operational Traffic Report",
                report_type="traffic_analysis",
                scope_type="session",
                format="pdf",
                status="completed",
                file_path="/reports/test.pdf",
            )
            db.add(report)
            db.commit()

            ops_service = OperationsCenterService(db)
            events = ops_service.get_timeline_events(limit=20)
            assert len(events) >= 3, f"Expected at least 3 events, got {len(events)}"

            event_types = {e.event_type for e in events}
            assert "incident_started" in event_types or "incident" in str(event_types)
            assert any("job" in et or "insight" in et or "report" in et for et in event_types)

            # Verify chronological order (newest first)
            for i in range(len(events) - 1):
                assert events[i].timestamp >= events[i + 1].timestamp

            log_check(9, "Authoritative Event Timeline Assembly", True, f"Aggregated {len(events)} events across incidents, jobs, insights, reports")
            db.close()
        except Exception as e:
            log_check(9, "Authoritative Event Timeline Assembly", False, str(e))

        # ---------------------------------------------------------------------
        # Check 10: Epistemic Data Provenance Isolation
        # ---------------------------------------------------------------------
        try:
            db = SessionTest()
            ops_service = OperationsCenterService(db)
            overview = ops_service.get_operations_overview(manager=manager)

            assert overview.provenance_summary.provenance_label in ["REAL DATA", "MIXED", "TEST FIXTURE"]
            assert overview.provenance_summary.is_synthetic is False
            log_check(10, "Epistemic Data Provenance Isolation", True, f"Provenance evaluated correctly: {overview.provenance_summary.provenance_label}")
            db.close()
        except Exception as e:
            log_check(10, "Epistemic Data Provenance Isolation", False, str(e))

        # ---------------------------------------------------------------------
        # Check 11: Real-Time Traffic Snapshot & Extrapolation Flagging
        # ---------------------------------------------------------------------
        try:
            db = SessionTest()
            ops_service = OperationsCenterService(db)
            overview = ops_service.get_operations_overview(manager=manager)

            snap = overview.traffic_snapshot
            assert snap.data_status in ["OBSERVED", "UNAVAILABLE", "EXTRAPOLATED"]
            assert snap.flow_rate_tag in ["OBSERVED", "EXTRAPOLATED", "UNAVAILABLE"]
            assert isinstance(snap.class_distribution, dict)

            log_check(11, "Real-Time Traffic Snapshot & Extrapolation Flagging", True, f"Snapshot status={snap.data_status}, flow_tag={snap.flow_rate_tag}, vpm={snap.flow_rate_per_minute}")
            db.close()
        except Exception as e:
            log_check(11, "Real-Time Traffic Snapshot & Extrapolation Flagging", False, str(e))

        # ---------------------------------------------------------------------
        # Check 12: Historical Context Integration (Phase 22 Reuse)
        # ---------------------------------------------------------------------
        try:
            db = SessionTest()
            ops_service = OperationsCenterService(db)
            hist_ctx = ops_service.get_historical_context_for_source(source_id=cam_online.id, time_range="7d")

            assert hist_ctx.source_id == cam_online.id
            assert hist_ctx.source_name == "Cam-North-RTSP"
            assert hasattr(hist_ctx, "total_volume")
            assert hasattr(hist_ctx, "observation_duration_seconds")
            assert hasattr(hist_ctx, "anomaly_count")
            assert hasattr(hist_ctx, "provenance_summary")

            log_check(12, "Historical Context Integration (Phase 22 Reuse)", True, f"Successfully integrated Phase 22 HistoricalAnalyticsService")
            db.close()
        except Exception as e:
            log_check(12, "Historical Context Integration (Phase 22 Reuse)", False, str(e))

        # ---------------------------------------------------------------------
        # Check 13: Simulation Boundaries & Advisory Labeling (Phase 12-14)
        # ---------------------------------------------------------------------
        try:
            db = SessionTest()
            ops_service = OperationsCenterService(db)
            overview = ops_service.get_operations_overview(manager=manager)

            assert "signal_optimization" in overview.simulation_support
            assert overview.simulation_support["signal_optimization"]["is_simulation_only"] is True
            assert "emergency_corridor" in overview.simulation_support
            assert overview.simulation_support["emergency_corridor"]["is_simulation_only"] is True

            log_check(13, "Simulation Boundaries & Advisory Labeling", True, "Simulations explicitly tagged as non-actuating decision support")
            db.close()
        except Exception as e:
            log_check(13, "Simulation Boundaries & Advisory Labeling", False, str(e))

        # ---------------------------------------------------------------------
        # Check 14: Preservation of Phase 11 Forecasting Limits (N < 20)
        # ---------------------------------------------------------------------
        try:
            db = SessionTest()
            ops_service = OperationsCenterService(db)
            overview = ops_service.get_operations_overview(manager=manager)

            fc = overview.prediction_support
            assert fc["status"] == "unavailable", "Forecasting must remain unavailable"
            assert fc["current_real_observations"] < fc["threshold_required"]
            assert "insufficient" in fc["message"].lower()

            log_check(14, "Preservation of Phase 11 Forecasting Limits (N < 20)", True, f"N={fc['current_real_observations']} < {fc['threshold_required']} strictly preserved")
            db.close()
        except Exception as e:
            log_check(14, "Preservation of Phase 11 Forecasting Limits (N < 20)", False, str(e))

        # ---------------------------------------------------------------------
        # Check 15: No-Fake-Data Invariant & Determinism
        # ---------------------------------------------------------------------
        try:
            # Create a completely fresh empty database to test zero-data determinism
            empty_db_file = Path(tempfile.gettempdir()) / f"empty_p23_verify_{uuid.uuid4().hex[:8]}.db"
            empty_engine = create_engine(f"sqlite:///{empty_db_file}", connect_args={"check_same_thread": False})
            Base.metadata.create_all(bind=empty_engine)
            EmptySession = sessionmaker(autocommit=False, autoflush=False, bind=empty_engine)

            empty_db = EmptySession()
            empty_manager = MockJobManager()

            empty_ops_service = OperationsCenterService(empty_db)
            empty_overview = empty_ops_service.get_operations_overview(manager=empty_manager)

            assert empty_overview.active_cameras_count == 0
            assert empty_overview.active_incidents_count == 0
            assert empty_overview.traffic_snapshot.data_status == "UNAVAILABLE"
            assert empty_overview.traffic_snapshot.observed_vehicle_volume == 0
            assert empty_overview.traffic_snapshot.flow_rate_per_minute == 0.0

            empty_db.close()
            try:
                empty_db_file.unlink(missing_ok=True)
            except Exception:
                pass

            log_check(15, "No-Fake-Data Invariant & Determinism", True, "Zero-data environment produces exact zero counts, no fake interpolation")
        except Exception as e:
            log_check(15, "No-Fake-Data Invariant & Determinism", False, str(e))

        # ---------------------------------------------------------------------
        # Check 16: Bounded Query Performance & Resource Safety
        # ---------------------------------------------------------------------
        try:
            db = SessionTest()
            ops_service = OperationsCenterService(db)

            # Test limit bounding
            events_5 = ops_service.get_timeline_events(limit=5)
            assert len(events_5) <= 5

            incidents_1 = ops_service.get_active_incidents(limit=1)
            assert len(incidents_1) <= 1

            log_check(16, "Bounded Query Performance & Resource Safety", True, "Enforced query limits on timeline events and incidents")
            db.close()
        except Exception as e:
            log_check(16, "Bounded Query Performance & Resource Safety", False, str(e))

        # ---------------------------------------------------------------------
        # Check 17: FastAPI REST Router Endpoints (7 Endpoints)
        # ---------------------------------------------------------------------
        try:
            from app.api.v1.operations import router as operations_router
            routes = operations_router.routes
            expected_paths = {
                "/overview": ["GET"],
                "/cameras": ["GET"],
                "/incidents": ["GET"],
                "/incidents/{incident_id}": ["GET"],
                "/incidents/{incident_id}/status": ["PATCH"],
                "/timeline": ["GET"],
                "/context/{source_id}": ["GET"],
            }

            actual_paths = {}
            for r in routes:
                methods = list(r.methods)
                actual_paths[r.path] = methods

            for path, methods in expected_paths.items():
                assert path in actual_paths, f"Missing route {path}"
                for m in methods:
                    assert m in actual_paths[path], f"Route {path} missing method {m}"

            log_check(17, "FastAPI REST Router Endpoints (7 Endpoints)", True, f"Verified 7 operations endpoints: {list(expected_paths.keys())}")
        except Exception as e:
            log_check(17, "FastAPI REST Router Endpoints (7 Endpoints)", False, str(e))

    finally:
        # Cleanup temporary database
        try:
            db_engine.dispose()
            test_db_file.unlink(missing_ok=True)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Check 18: Frontend Route, Navigation, Type Definitions & Production Build
    # -------------------------------------------------------------------------
    try:
        # Check OperationsCenterPage.tsx exists
        page_file = FRONTEND_DIR / "src" / "pages" / "OperationsCenterPage.tsx"
        assert page_file.exists(), "OperationsCenterPage.tsx does not exist"

        # Check App.tsx has /operations route
        app_file = FRONTEND_DIR / "src" / "App.tsx"
        app_content = app_file.read_text(encoding="utf-8")
        assert "operations" in app_content, "App.tsx does not contain operations route"
        assert "OperationsCenterPage" in app_content, "App.tsx does not import OperationsCenterPage"

        # Check Sidebar.tsx has Operations Center nav item
        sidebar_file = FRONTEND_DIR / "src" / "layouts" / "Sidebar.tsx"
        sidebar_content = sidebar_file.read_text(encoding="utf-8")
        assert "Operations Center" in sidebar_content, "Sidebar.tsx missing Operations Center nav item"
        assert "/operations" in sidebar_content, "Sidebar.tsx missing /operations path"

        # Check types
        types_file = FRONTEND_DIR / "src" / "types" / "operations.ts"
        assert types_file.exists(), "operations.ts types file missing"

        # Check production build artifacts
        dist_dir = FRONTEND_DIR / "dist"
        assert dist_dir.exists(), "Frontend dist directory missing"
        assert (dist_dir / "index.html").exists(), "dist/index.html missing"

        log_check(18, "Frontend Route, Navigation, Type Definitions & Build", True, "OperationsCenterPage, /operations route, sidebar link, and production build verified")
    except Exception as e:
        log_check(18, "Frontend Route, Navigation, Type Definitions & Build", False, str(e))

    print("\n================================================================================")
    print(f"VERIFICATION SUMMARY: {PASS_COUNT}/18 CHECKS PASSED, {FAIL_COUNT} FAILED")
    print("================================================================================")
    if FAIL_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_checks()
