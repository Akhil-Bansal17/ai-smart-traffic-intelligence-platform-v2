# PHASE 24 — Advanced Traffic Operations Analytics & Network Intelligence (Master Prompt)

> Repository: `https://github.com/Akhil-Bansal17/ai-smart-traffic-intelligence-platform-v2.git`, branch `main`. **The current local repository is the source of truth.** Before making any implementation or modification decision, inspect the actual repository. **If repository reality contradicts this prompt, repository reality wins.**

## Mandatory Permanent Git Rule

**Do not push anything to GitHub.** Do not execute `git push`, do not push to `origin/main`, do not create GitHub push automation. All commits are strictly local. The final report must explicitly confirm: **"GITHUB PUSH: NOT PERFORMED."**

---

## Role & Mission

You are the implementation, testing, and verification agent evolving the platform into a bounded, evidence-based **network intelligence** layer (`/network-intelligence`). This phase acts strictly as an **analytics and orchestration layer** over authoritative persisted data models (`CameraSource`, `AnalysisSession`, `TrafficMetricsRecord`, `AnomalyEvent`, `LaneResultRecord`).

### Core Architectural Principle
Phase 24 does **not** duplicate YOLO detection, ByteTrack tracking, line-crossing counting, lane assignment, traffic-metric calculation, anomaly detection, forecasting, historical analytics, decision intelligence, reporting, or live monitoring. **If an existing service already calculates a metric, consume that metric — do not recalculate it independently.**

---

## Implemented Architecture

### 1. Backend Service Layer (`app.services.network_intelligence`)
The `NetworkIntelligenceService` encapsulates 8 core analytical functions:
- `get_network_overview`: Aggregates total traffic volume, flow rates (veh/min and veh/hr), active sources, 5-class vehicle breakdown, directional summary, and lane summary.
- `compare_sources`: Multi-source ranking across volume, duration, incident count, and lane density with duration variance checking (`window_mismatch_detected` flagged when duration ratio $\ge 2.0$).
- `get_hotspots`: Evidence-based composite intensity score ($0.0 - 100.0$) combining incidents ($40\%$), congestion anomalies ($25\%$), traffic volume/rate ($20\%$), and lane density ($15\%$). Labels locations as source/intersection hotspots without fabricated GPS coordinates.
- `get_vehicle_composition`: Exact 5 YOLO classes (`car`, `motorcycle`, `bus`, `truck`, `bicycle`), dominant class determination, and heavy vehicle percentage (`truck` + `bus`).
- `get_directional_analysis`: Inbound vs outbound counts, flow ratio, balance status (`inbound_dominant`, `outbound_dominant`, `balanced`), and per-source breakdown.
- `get_lane_analysis`: Cross-source lane utilization with explicit uncalibrated image-space density heuristic disclosures and graceful `UNAVAILABLE` handling when sources lack lane configurations.
- `get_temporal_cross_source_analysis`: Synchronized chronological buckets (`hourly`, `daily`), peak bucket detection, and honest epistemic notes (never asserts vehicle travel times or route causality).
- `get_historical_comparison`: Reuses Phase 22 `HistoricalAnalyticsService.get_comparison` for period-over-period delta computation.

### 2. Configuration & Bounds (`app.config.settings`)
- `network_intelligence_max_sources`: 50 (bounded 1-500)
- `network_intelligence_max_range_days`: 90 (bounded 1-365)
- `network_intelligence_default_time_window`: "7d"
- `network_intelligence_max_hotspots`: 20 (bounded 5-100)

### 3. REST API Router (`app.api.v1.network_intelligence`)
Mounted at `/api/v1/network-intelligence`:
- `GET /overview`
- `GET /compare`
- `GET /hotspots`
- `GET /vehicle-composition`
- `GET /directional-analysis`
- `GET /lane-analysis`
- `GET /temporal-analysis`
- `GET /historical-comparison`

### 4. Frontend Layer (`frontend/src/pages/NetworkIntelligencePage.tsx`)
- Route: `/network-intelligence`
- Reusable UI cards, tables, progress indicators, severity badges, and tabs.
- Provenance status banner (`REAL DATA`, `TEST FIXTURE`, `MIXED`, `UNAVAILABLE`).
- Cross-platform drill-down links to Operations Center, Historical Analytics, Traffic Analytics, and Live Monitoring.

---

## Epistemic Truth & Invariants

1. **No Fake Data**: Empty database produces exact 0 counts, empty lists, and `UNAVAILABLE` status labels.
2. **Preservation of Phase 11 Forecasting Limits**: $N \ge 20$ genuine real-world sample requirement remains strictly enforced.
3. **Simulation Boundaries**: All simulations remain decision-support / non-actuating only.
4. **No Route Causality**: Cross-source temporal analysis never asserts travel times or route propagation without multi-camera tracking evidence.
5. **No Fabricated GPS**: Hotspots are attributed to source and intersection names, not invented coordinates.

---

## Verification Suite

- Dedicated Test Suite: `pytest backend/tests/test_network_intelligence.py` (11/11 passed)
- Comprehensive Verification Script: `python scripts/verify_phase24_network_intelligence.py` (18/18 passed)
- Regressions: Phase 15, 16, 17, 18, 19, 21, 22, 23 (all passed)
- Frontend Typecheck & Build: `npm run build` in `frontend` (clean 0 errors)
