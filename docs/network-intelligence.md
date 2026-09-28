# Advanced Traffic Operations Analytics & Network Intelligence (Phase 24)

## Overview

The Advanced Traffic Operations Analytics & Network Intelligence platform (`/network-intelligence`) provides bounded, evidence-based cross-source intelligence across distributed camera and sensor feeds. It acts strictly as an **analytics and orchestration layer** over authoritative persisted data models (`CameraSource`, `AnalysisSession`, `TrafficMetricsRecord`, `AnomalyEvent`, `LaneResultRecord`) and reuses existing analytical subsystems (`HistoricalAnalyticsService` from Phase 22, `AnomalyDetector` from Phase 15, `OperationsCenterService` from Phase 23).

```
                     Network Intelligence Layer (Phase 24)
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
Network Overview              Source Comparison             Hotspot Analysis
(Volume, Rates, Lanes)        (Variance, Mismatch)          (Score 0-100, Evidence)
        │                             │                             │
        ├─────────────────────────────┼─────────────────────────────┤
        ▼                             ▼                             ▼
Vehicle Composition           Directional Analysis          Lane Intelligence
(5 YOLO Classes, Heavy %)     (In/Out Ratio, Balance)       (Image-Space Heuristic)
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
                        Temporal Cross-Source Timeline
                        & Historical Comparison (Phase 22)
```

---

## Architectural Principles & Strict Invariants

1. **Zero Secondary Analytics / CV Engines**:
   `NetworkIntelligenceService` does **not** execute YOLO detection, ByteTrack tracking, line-crossing detection, lane assignment, or recalculate raw traffic metrics. It strictly consumes metrics previously computed by authoritative processing workers and stored in `traffic_metrics`, `analysis_sessions`, `lane_results`, and `anomaly_events`.

2. **Zero Fabricated Geographic or Physical Data**:
   The platform does not invent latitude/longitude coordinates, map pins, or fake geographic bounding boxes when the database only identifies a camera source name and location string. Hotspots are explicitly labeled **Source Hotspots** or **Intersection Hotspots** with plain-text location attribution.

3. **Zero Fabricated Route Causality or Propagation**:
   Temporal cross-source timeline analysis aggregates synchronized chronological observation buckets across sources. It strictly includes epistemic disclaimers:
   > *"Temporal cross-source patterns represent synchronized observation windows. No vehicle travel times, propagation speeds, or route causality are asserted without multi-camera tracking evidence."*

4. **Strict Epistemic Truth & Provenance Isolation**:
   Every response carries an epistemic status label (`OBSERVED`, `DERIVED`, `EXTRAPOLATED`, `UNAVAILABLE`) and a comprehensive `HistoricalProvenanceSummary`:
   - `REAL DATA`: Derived exclusively from verified genuine sources (`local_camera`, `rtsp`, `http_stream`, or verified real-world video files).
   - `TEST FIXTURE`: Emitted from test fixtures or synthetic simulators (`test_fixture://`).
   - `MIXED`: Telemetry spanning both verified real sources and synthetic fixtures, with mandatory warning ribbons advising operators to filter synthetic data.
   - `UNAVAILABLE`: Zero recorded telemetry matching the query window.

5. **Observation Window Mismatch Detection**:
   When comparing sources with significantly divergent observation durations (ratio $\ge 2.0$), the system automatically sets `window_mismatch_detected = True` and appends explanatory warnings to prevent invalid or misleading comparisons.

6. **Preservation of Phase 11 Forecasting Limits**:
   The minimum real-world sample threshold ($N \ge 20$) is strictly preserved. Network intelligence does not generate "predicted network traffic" to simulate artificial capability.

7. **Simulation Safety & Non-Actuation Disclaimers**:
   Simulation features (Phase 12 Signal Optimization, Phase 13 Emergency Corridor) remain isolated as decision-support models only. No automated actuation or physical signal override is performed.

---

## Core Analytics Capabilities

### 1. Network Overview (`GET /api/v1/network-intelligence/overview`)
- Total traffic volume, active sources vs registered sources, observation duration, and session count.
- Network flow rates (vehicles per minute and vehicles per hour).
- Active and recurring incident counts aggregated from Phase 15 `AnomalyEvent` records.
- 5-class vehicle breakdown and heavy-vehicle proportion.
- Directional balance summary (inbound/outbound counts, ratio, status).
- Lane intelligence summary (total lanes, busiest lane, average density, image-space calibration warning).

### 2. Source Comparison (`GET /api/v1/network-intelligence/compare`)
- Per-source comparative rankings across volume, flow rate, duration, incident count, and lane density.
- Ranking of busiest source and highest-incident source.
- Automated duration variance checking with `window_mismatch_detected` flags.

### 3. Traffic Hotspots (`GET /api/v1/network-intelligence/hotspots`)
- Composite intensity score ($0.0 - 100.0$) computed deterministically from:
  - Incident frequency ($40\%$ weight)
  - Congestion anomaly frequency ($25\%$ weight)
  - Observed traffic volume and flow rate ($20\%$ weight)
  - Peak lane occupancy/density ($15\%$ weight)
- Plain-text contributing factor explanations (e.g. *"2 active incidents recorded in observation window"*).
- Severity categorization (`critical`, `high`, `medium`, `low`).

### 4. Vehicle Composition (`GET /api/v1/network-intelligence/vehicle-composition`)
- Strict compliance with repository reality: exactly 5 YOLO vehicle classes (`car`, `motorcycle`, `bus`, `truck`, `bicycle`).
- Network-level and source-level class distributions and rates per hour.
- Heavy-vehicle percentage (sum of `truck` + `bus` divided by total vehicles).
- Identification of network dominant class and source dominant classes.

### 5. Directional Intelligence (`GET /api/v1/network-intelligence/directional-analysis`)
- Inbound vs. outbound directional traffic volume and proportion.
- Directional balance ratio ($\text{inbound} / \max(1, \text{outbound})$).
- Balance classification: `inbound_dominant` ($\text{ratio} \ge 1.25$), `outbound_dominant` ($\text{ratio} \le 0.80$), or `balanced`.
- Per-source directional breakdown table.

### 6. Lane Intelligence (`GET /api/v1/network-intelligence/lane-analysis`)
- Aggregated lane analytics reusing Phase 9 and Phase 22 lane records.
- Identification of busiest lane and highest image-space density lane.
- Explicit uncalibrated pixel-space density disclaimer:
  > *"Uncalibrated image-space density heuristic: relative comparison only, not physical density (pce/km)."*
- Graceful return of `UNAVAILABLE` epistemic status when sources lack configured lanes.

### 7. Temporal Cross-Source Analysis (`GET /api/v1/network-intelligence/temporal-analysis`)
- Synchronized time buckets (`hourly` or `daily`) aligning telemetry across multiple camera feeds.
- Identification of network peak buckets ($\ge 1.3\times$ average bucket volume and multi-source concurrency).
- Per-source flow rate breakdown within each synchronized bucket.

### 8. Historical Comparison (`GET /api/v1/network-intelligence/historical-comparison`)
- Direct reuse of Phase 22 `HistoricalAnalyticsService.get_comparison` to evaluate period-over-period delta metrics.
- Volume, flow rate, duration, incident, and session count delta percentages.

---

## Configuration & Safety Ceilings

Configured in `app.config.settings.Settings`:

| Setting | Default | Range | Description |
| :--- | :--- | :--- | :--- |
| `network_intelligence_max_sources` | `50` | $1 - 500$ | Maximum camera sources queried in a single network operation |
| `network_intelligence_max_range_days` | `90` | $1 - 365$ | Maximum query date range ceiling to protect DB performance |
| `network_intelligence_default_time_window` | `"7d"` | `24h, 7d, 30d, 90d` | Default query time window preset |
| `network_intelligence_max_hotspots` | `20` | $5 - 100$ | Maximum hotspot results returned in ranked queries |

---

## REST API Reference

All endpoints are mounted under prefix `/api/v1/network-intelligence`:

| Method | Endpoint | Response Schema | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/overview` | `NetworkOverviewResponse` | Aggregated network KPIs, flow rates, class breakdown, and lane summary |
| `GET` | `/compare` | `NetworkSourceComparisonResponse` | Cross-source comparative rankings and window mismatch detection |
| `GET` | `/hotspots` | `NetworkHotspotResponse` | Evidence-based ranked traffic hotspots ($0-100$ intensity score) |
| `GET` | `/vehicle-composition`| `NetworkVehicleCompositionResponse` | 5-class vehicle breakdown, dominance, and heavy vehicle share |
| `GET` | `/directional-analysis` | `NetworkDirectionalResponse` | Inbound/outbound flow distribution, ratios, and balance classification |
| `GET` | `/lane-analysis` | `NetworkLaneResponse` | Cross-source lane utilization and calibrated heuristic disclosures |
| `GET` | `/temporal-analysis` | `NetworkTemporalAnalysisResponse` | Synchronized chronological buckets across sources |
| `GET` | `/historical-comparison` | `PeriodComparisonResponse` | Period-over-period delta metrics reusing Phase 22 service |

---

## Frontend Implementation

Mounted at `/network-intelligence`:
- **Header & Filter Bar**: Preset selectors (`24h`, `7d`, `30d`, `90d`, `custom`), camera filter, synthetic data toggle, refresh button.
- **Provenance Banner**: Visual status banner indicating `REAL DATA`, `TEST FIXTURE`, `MIXED`, or `UNAVAILABLE` with contextual warnings.
- **Top KPI Cards**: Total Volume, Active Sources, Network Flow Rate, Dominant Vehicle Class, Directional Balance, and Active Incidents.
- **Tabbed Analytical Views**:
  1. *Source Comparison*: Ranking table with volume bars, flow rates, incident counts, and window mismatch badges.
  2. *Traffic Hotspots*: Severity-badged source hotspots with composite intensity progress bars and contributing factor tags.
  3. *Vehicle Composition*: Exact 5 YOLO class distribution cards with visual progress bars and heavy vehicle highlight card.
  4. *Directional Intelligence*: Inbound vs. Outbound flow cards, ratio indicators, and per-source directional breakdown table.
  5. *Lane Intelligence*: Lane utilization table with density heuristics, calibration disclaimer alert, and busiest lane callout.
  6. *Temporal Analysis*: Synchronized bucket cards with multi-source volume breakdown and network peak badges.
  7. *Historical Trends*: Period-over-period delta comparison cards with volume, flow rate, and incident trajectory arrows.
- **Cross-Platform Drill-Down Links**: Direct navigation to Operations Center (`/operations`), Historical Analytics (`/historical-analytics`), Traffic Analytics (`/traffic-analytics`), and Live Monitoring (`/live-monitoring`).

---

## Verification & Regression Status

- **Dedicated Test Suite**: `backend/tests/test_network_intelligence.py` — **11/11 PASSED** (100%).
- **Automated Verification Script**: `scripts/verify_phase24_network_intelligence.py` — **18/18 CHECKS PASSED** (100%).
- **Full Phase Regressions**:
  - Phase 23 (Operations Center): **18/18 PASSED**
  - Phase 22 (Historical Analytics): **18/18 PASSED**
  - Phase 19 (Reporting & Exports): **18/18 PASSED**
  - Phase 18 (Decision Intelligence): **18/18 PASSED**
  - Phase 17 (Job Orchestration): **17/17 PASSED**
  - Phase 16 (Security & Production Readiness): **16/16 PASSED**
  - Phase 15 (Anomaly Detection): **10/10 PASSED**
- **Frontend Typecheck & Production Build**: `tsc && vite build` — **BUILT IN 7.89s (0 ERRORS)**.
