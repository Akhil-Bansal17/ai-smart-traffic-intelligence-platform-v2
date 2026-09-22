# Historical Traffic Intelligence & Trend Analysis Architecture (Phase 22)

## Overview

The Historical Traffic Intelligence & Trend Analysis layer provides an authoritative, query-optimized analytical interface over persisted video analysis and live camera monitoring sessions. It answers the fundamental operational question: **"What actually happened?"** across intersections, corridors, and monitored areas.

In strict alignment with the platform's epistemic integrity principles:
- **Zero Extrapolation**: Rates are calculated strictly over actual recorded observation durations. Short sessions (< 1 hour) are flagged with `is_extrapolated: true` when converted to hourly rates (`veh/hr`).
- **Zero Predictive Forecasting**: This layer does not forecast future traffic. Phase 11 ML forecasting constraints ($N < 20$ sample barrier) remain strictly untouched.
- **Zero Physical Actuation**: Simulation-only boundaries established in Phase 12 & 13 and read-only invariants in Phase 14 are strictly preserved.
- **Zero Synthetic Disguise**: Real-world data and test fixtures are segregated with explicit provenance labeling (`REAL DATA`, `SYNTHETIC / TEST FIXTURE`, `MIXED`, `NO DATA`). Synthetic data is excluded by default (`include_synthetic=false`).

---

## Architectural Configuration & Safety Bounds

To prevent Denial of Service (DoS) and memory exhaustion on heavy analytical aggregation queries, queries are bounded by configuration settings in `app.config.settings.Settings`:

| Setting | Default | Description |
|---|---|---|
| `max_historical_range_days` | 90 | Maximum temporal query window allowed in a single request. Queries exceeding this are rejected with HTTP 400. |
| `max_historical_buckets` | 1000 | Maximum discrete time-series buckets generated in a single query. |
| `max_historical_records` | 10000 | Maximum raw database records queried during aggregation. |

---

## Database Schema Optimization & Indexes

Alembic migration `0013_add_historical_analytics_indexes` introduced composite and single-column b-tree indexes to ensure sub-100ms aggregation performance over large datasets:

1. `ix_traffic_metrics_created_at` on `traffic_metrics(created_at)`: Accelerates temporal filtering for metric records.
2. `ix_analysis_sessions_started_status` on `analysis_sessions(started_at, status)`: Optimizes bounded historical session scanning by start time and completion status.
3. `ix_analysis_sessions_camera_source_started` on `analysis_sessions(camera_source_id, started_at)`: Optimizes per-camera historical queries and time ordering.
4. `ix_lane_results_session_lane` on `lane_results(analysis_session_id, lane_id)`: Accelerates lane intelligence joins.

---

## Strict Epistemic Data Provenance Isolation

Every historical response includes a `HistoricalProvenanceSummary` object:
- `provenance_label`: `"REAL DATA"`, `"SYNTHETIC / TEST FIXTURE"`, `"MIXED"`, or `"NO DATA"`
- `is_synthetic`: `true` if any synthetic source is included
- `is_mixed`: `true` if both real-world and synthetic data are present in the filtered time window
- `camera_source_count`: Distinct camera sources analyzed
- `session_count`: Total sessions analyzed
- `observation_duration_seconds`: Total cumulative observation seconds

By default, all queries omit synthetic test fixtures and non-verified video files unless the client explicitly passes `include_synthetic=true`.

---

## Analytics Subsystems & Algorithms

### 1. Discrete Time-Series Bucketing (Non-Interpolating)
Generates discrete buckets (hourly, daily, weekly) within the requested window. Empty buckets report zero volume without artificial smoothing, linear interpolation, or synthetic flatlining.

### 2. Vehicle Class Composition
Aggregates vehicle counts strictly across the supported YOLO detection classes (`car`, `truck`, `bus`, `motorcycle`, `bicycle`). Computes proportional shares and hourly vehicle rates.

### 3. Directional Flow & Movement Balance
Synthesizes directional counts (inbound vs. outbound), calculating the directional ratio and proportion to reveal lane imbalance and directional surge.

### 4. Lane Intelligence & Density Calibration Disclaimers
Aggregates lane occupancy and image-space density proxy values across sessions. Includes mandatory calibration disclaimers:
> *"Uncalibrated image-space density heuristic based on bounding-box pixel area proxy. Requires camera calibration matrix for true physical surface density."*

### 5. Deterministic Observed Peak Periods
Identifies historical peak periods for flow rate (`veh/hr`), total volume (`vehicles`), and lane density (`score 0-1`). Applies a deterministic, unambiguous tie-breaking hierarchy:
1. Higher metric value wins.
2. Earlier session `started_at` timestamp wins.
3. Longer observation duration wins.
4. Chronological session ID ascending.

### 6. Phase 15 Operational Anomaly & Incident History
Aggregates congestion events, speed drops, queue spillbacks, and abnormal volume incidents recorded by Phase 15 detection routines.

### 7. Multi-Source Traffic Comparison
Compares traffic flow and volumes across camera sources and video files within the selected time window.

### 8. Period-over-Period Delta Comparison
Computes absolute and percentage change between the active time window ($T_0$ to $T_1$) and the preceding equivalent temporal period ($T_0 - \Delta T$ to $T_0$).

---

## REST API Specification

Mounted under `/api/v1/historical-analytics/`:

| Method | Endpoint | Query Parameters | Description |
|---|---|---|---|
| `GET` | `/summary` | `time_preset`, `start_time`, `end_time`, `camera_source_id`, `session_mode`, `include_synthetic` | Unified high-level KPI summary |
| `GET` | `/timeseries` | same + `bucket_interval` (`hourly`, `daily`, `weekly`) | Discrete time-series buckets |
| `GET` | `/vehicle-composition` | standard filter params | YOLO vehicle class breakdown |
| `GET` | `/directions` | standard filter params | Inbound vs outbound flow metrics |
| `GET` | `/lanes` | standard filter params | Lane utilization and density metrics |
| `GET` | `/peaks` | standard filter params | Deterministic peak flow, volume & density |
| `GET` | `/anomalies` | standard filter params | Historical incident and anomaly events |
| `GET` | `/sources` | standard filter params | Multi-source and multi-camera comparison |
| `GET` | `/compare` | standard filter params | Period-over-period delta comparison |

---

## Frontend Implementation

- **Route**: `/historical-analytics` registered in `App.tsx` and linked via `Sidebar.tsx`.
- **Component**: `HistoricalAnalyticsPage.tsx`:
  - Temporal Presets: `Last 24 Hours`, `Last 7 Days`, `Last 30 Days`, `Last 90 Days`, and `Custom Range`.
  - Source Filtering: All sources or specific camera / video source.
  - Mode Filtering: All modes, Live Monitoring, or Video File Analysis.
  - Synthetic Data Toggle: Checkbox to explicitly permit synthetic test fixtures with warning banners.
  - Provenance Banner: Visual alert badge displaying data origin (`REAL DATA` in emerald, `MIXED` in amber, `SYNTHETIC` in purple).
  - KPI Stat Cards: Total Volume, Flow Rate, Inbound/Outbound Balance, Anomaly Incidents, and Peak Rate.
  - 8 Analytical Tabs: Overview, Time Series, Vehicle Classes, Directional Balance, Lane Intelligence, Peak Periods, Anomaly History, and Multi-Source Comparison.
