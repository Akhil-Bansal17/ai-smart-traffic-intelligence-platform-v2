# Unified Traffic Operations Center & Real-Time Incident Response (Phase 23)

## Overview

The Unified Traffic Operations Center (`/operations`) provides a single, high-reliability command console over the platform's distributed analytical subsystems. It acts purely as an **orchestration and presentation layer**, bridging:
- **Phase 21: Live Monitoring & Camera Sources** (telemetry, live frame processing, preview JPEGs).
- **Phase 15: Operational Anomaly & Incident Detection** (congestion, flow drop, lane imbalance, density spike).
- **Phase 22: Historical Traffic Intelligence** (retrospective summaries, peaks, compositional trends).
- **Phase 18: Decision Intelligence Insights** (explainable evidence packages and advisory recommendations).
- **Phase 19: Business-Grade Reporting** (PDF/CSV exports and audit trails).
- **Phase 12 & 13: Decision Support Simulations** (signal optimization and emergency corridor simulation boundaries).

```
             Unified Traffic Operations Center (Phase 23)
                                │
      ┌─────────────────────────┼─────────────────────────┐
      ▼                         ▼                         ▼
Live Monitoring (21)    Incident System (15)    Historical Analytics (22)
      │                         │                         │
      └──────────────┬──────────┴──────────────┬──────────┘
                     ▼                         ▼
           Decision Insights (18)         Reporting (19)
                     │
                     ▼
           Existing Simulations (12/13)
```

---

## Architectural Principles & Strict Invariants

1. **Zero Secondary Analytics / CV Engines**:
   `OperationsCenterService` does not execute YOLO detection, ByteTrack tracking, flow calculations, or anomaly evaluations. It coordinates authoritative calls to existing managers and services.

2. **Zero Fabricated or Interpolated Data**:
   Empty databases and inactive feeds return exact zero counts and `UNAVAILABLE` state indicators. No synthetic smoothing, imaginary curves, or hard-coded mock vehicles are ever emitted.

3. **Strict Epistemic Provenance Isolation**:
   Every response contains a `HistoricalProvenanceSummary` distinguishing:
   - `REAL DATA`: Generated exclusively from verified camera sources or real-world video files.
   - `TEST FIXTURE`: Emitted from deterministic synthetic sources (e.g. `test_fixture://`). Prominently badged with warning ribbons.
   - `MIXED`: Telemetry spanning both verified real sources and synthetic fixtures.
   - `UNAVAILABLE`: Zero recorded telemetry.

4. **Preservation of Phase 11 ML Forecasting Limits**:
   The minimum real-world sample threshold ($N \ge 20$) is strictly preserved. In the Operations Center, predictive forecasting is marked `UNAVAILABLE` with explicit explanations regarding data requirements ($N=10 < 20$).

5. **Simulation Safety & Non-Actuation Disclaimers**:
   Signal Optimization (Phase 12) and Emergency Corridor (Phase 13) simulations are linked as decision support only. All UI surfaces and API payloads include explicit `NON-ACTUATING` disclaimers.

6. **Credential Protection & Redaction**:
   Connection strings containing credentials (e.g. `rtsp://admin:secret@host/stream`) are sanitized by `redact_uri_credentials` into `rtsp://admin:***@host/stream` before leaving the backend boundary.

---

## Operational Configuration & Resource Bounding

Settings defined in `app.config.settings.Settings`:

| Setting | Default | Range | Description |
|---|---|---|---|
| `operations_default_poll_interval_seconds` | 5 | 1–60 | Coordinated client polling cadence for real-time console updates. |
| `operations_max_timeline_events` | 50 | 5–500 | Upper limit for chronological events returned in a single query. |
| `operations_max_active_incidents` | 50 | 5–500 | Upper limit for concurrent active incidents aggregated in overview. |

---

## REST API Specification (`/api/v1/operations`)

All endpoints are mounted under `/api/v1/operations`:

### 1. `GET /api/v1/operations/overview`
- **Description**: Assembles composite operational overview in a single coordinated query set.
- **Latency Budget**: Sub-50ms.
- **Payload**:
  - `system_health`: `"healthy"`, `"degraded"`, or `"offline"`.
  - `database_connected`: Connectivity probe status.
  - `database_latency_ms`: Round-trip query latency.
  - `active_cameras_count` / `total_cameras_count`.
  - `active_incidents_count` / `critical_incidents_count`.
  - `cameras`: List of camera fleet items with health badges, telemetry metrics, and preview flags.
  - `active_incidents`: Unresolved traffic anomalies (`open`, `acknowledged`).
  - `traffic_snapshot`: Instantaneous network volume, vpm/vph rates, directional ratio, and class distribution.
  - `insights`: Active advisory insights from Phase 18.
  - `timeline`: Recent authoritative events (incidents, jobs, insights, reports).
  - `provenance_summary`: Data trust tag (`REAL DATA`, `TEST FIXTURE`, `MIXED`).
  - `simulation_support`: Read-only links and disclaimers for Phase 12/13.
  - `prediction_support`: Phase 11 forecast availability status ($N < 20$ explanation).

### 2. `GET /api/v1/operations/cameras`
- **Description**: Returns all registered cameras with live telemetry, processing FPS, and health status (`ONLINE`, `CONNECTING`, `DEGRADED`, `OFFLINE`, `UNKNOWN`).

### 3. `GET /api/v1/operations/incidents`
- **Query Params**: `status`, `severity`, `camera_source_id`, `anomaly_type`, `limit`, `offset`.
- **Description**: Paginated incident listing with parent session and source provenance.

### 4. `GET /api/v1/operations/incidents/{incident_id}`
- **Description**: Detailed inspection of a single operational incident with metric triggers and baseline comparison.

### 5. `PATCH /api/v1/operations/incidents/{incident_id}/status`
- **Payload**: `{"status": "acknowledged" | "resolved", "note": "..."}`
- **Description**: Reuses Phase 15 state mutation rules, attaching operator audit notes and timestamps.

### 6. `GET /api/v1/operations/timeline`
- **Query Params**: `limit` (default 50), `event_type`.
- **Description**: Deterministic chronological event timeline assembled from authoritative records without requiring heavy event-sourcing database models.

### 7. `GET /api/v1/operations/context/{source_id}`
- **Query Params**: `time_window` (default `"7d"`).
- **Description**: Retrieves retrospective historical context from Phase 22 (`HistoricalAnalyticsService`) for drawer display.

---

## Frontend Architecture (`/operations`)

- **Component**: `frontend/src/pages/OperationsCenterPage.tsx`
- **Design Tokens**: Dark glassmorphic styling (`#0c1322`, `#0e1726`), cyan/indigo accents, Lucide-react iconography.
- **Responsive Layout**:
  - Command Bar: Title, Phase badge, provenance chip, last-updated timestamp, and auto-refresh toggle.
  - Drill-down Ribbon: Fast navigation to Live Console, Historical Analytics, Video Analysis, Reports, Simulations, and Predictions.
  - KPI Metrics Grid: Active Cameras, Active/Critical Incidents, Observed Traffic Volume, Active Insights.
  - Fleet & Snapshot Column: Camera grid with live thumbnails and processing FPS; network-level vehicle composition breakdown.
  - Incident & Insight Column: Active incidents with status/severity pills, trigger metrics, operator action modal, and advisory recommendations.
  - Authoritative Timeline: Chronological audit events with filtering by event type.
  - Context Drawer: Historical peak periods, volume, and anomaly history on demand.
