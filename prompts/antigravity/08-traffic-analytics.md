# 08 — Traffic Analytics & Flow Metrics

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior backend engineer building a traffic-analytics layer on top of the real tracking/counting pipeline: tracked vehicles + counting events → measurable, mathematically-defined traffic metrics. No fabricated statistics anywhere.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`
3. `ARCHITECTURE.md` — §3 (CV Pipeline, `traffic_metrics_engine.py`'s described role), §8 (database schema)
4. `README.md`
5. `SECURITY.md`
6. `prompts/antigravity/01` through `07` — accumulated architecture decisions and known discrepancies already on record
7. The actual current implementations of `VideoSource`, the Phase 5 detector, `DetectionResult`, the Phase 6 tracker, `TrackedObject`/trajectory representation, the Phase 7 vehicle counter and its crossing-event output/schema — **inspect real field names and shapes; do not assume they match this prompt's description**
8. Current API routers, configuration/settings, the frontend Video Analysis page and any existing analytics-related components
9. Database models, migrations, all current tests
10. `backend/requirements.txt` and `.env.example`

**Do not blindly trust prior completion reports.** If the actual repository differs from Current State below, build against what's actually there and report the discrepancy. If a genuine gap makes Phase 8 impossible to build correctly, stop and report `BLOCKED`.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY → DOCUMENT → UPDATE PROJECT_STATUS.md → REPORT
```

## Context — Verify Before Building On It

Phases 1–2 were independently verified directly in a prior session. **Phases 3–7 were completed by prior Antigravity runs and are recorded in `PROJECT_STATUS.md` as *reported*, not independently re-verified in the environment this prompt was authored in.** Phase 7's reported scope: a `VehicleCounter`/counting engine consuming Phase 6 tracking output, producing deduplicated counts via virtual line-crossing with direction detection, verified via a real `scripts/verify_phase7_counting.py` run. **Before writing any Phase 8 code, confirm this is actually true** by inspecting the repository and re-running the existing test suite (and, ideally, `scripts/verify_phase7_counting.py`) yourself.

## Current State You're Building Against (per architecture docs + prior reports — confirm against actual code)

- `ARCHITECTURE.md` §3 already names a `traffic_metrics_engine.py` role: "aggregates lane-level output into flow rate, occupancy, directional distribution, and the density/congestion score." Phase 8 implements the flow-rate and directional-distribution parts of this from real counting-event data — **lane-level output, density, and congestion scoring do not exist yet (no lane analysis has been built) and are explicitly out of scope here** (see Scope Boundary).
- A counting engine reportedly exists (Phase 7) producing crossing events with track ID, class, and direction. Confirm its actual output shape before designing the analytics engine's input contract around it.
- No analytics engine, no analytics endpoint, and no analytics persistence exist yet as of the state this prompt was written against — confirm this is still true.

## Objective

```
Video → VideoSource → Detector → Tracker → Tracked Vehicles → Counting Engine
  → Analytics Engine → Traffic Metrics → API → React Dashboard
```

Transform real counting events (Phase 7 output) into measurable traffic-flow metrics: volume, class distribution, flow rate, directional flow, and optionally time-series aggregation — all computed from genuine data, never fabricated or hard-coded.

## Core Analytics Scope

- **Traffic volume:** total unique vehicles counted in the observed interval (from Phase 7's deduplicated count — never recount from raw detections).
- **Vehicle-class distribution:** count and percentage per class actually supported by the current detector (car, motorcycle, bus, truck, and bicycle only if the detector actually supports it — confirm, don't assume).
- **Flow rate:** vehicles per minute/hour computed from the actual observation duration — never inferred by scaling a short clip into an implied full-hour volume without explicitly labeling that as an estimate (see Data Honesty).
- **Directional flow:** inbound/outbound counts and percentages, taken directly from Phase 7's crossing-direction output — never re-derived independently from raw screen coordinates.
- **Time-series volume (optional, only if it fits cleanly):** vehicle counts aggregated into configurable time windows (e.g., 5s/10s/1min) based on real crossing-event timestamps. Do not build real-time streaming infrastructure for this — a simple post-hoc aggregation over the processed video is sufficient.

All example numbers in this prompt (42 vehicles, 25 cars, etc.) are illustrative only — never hard-code them.

## Track-Based Semantics

Analytics must derive entirely from genuine tracked vehicles and Phase 7 counting events. Do not: count raw detections as vehicles, count per-frame, generate statistics from bounding boxes without identity, invent trajectories, assign fake IDs, double-count a track ID, or fabricate missing data. The analytics engine does not duplicate detector/tracker/counter logic — it consumes their output.

## Analytics Architecture

```
TrackedObject / Counting Events → Analytics Engine → TrafficMetrics → API/UI
```

Name the module consistent with existing repository conventions (`ARCHITECTURE.md` §3 uses `TrafficMetricsEngine` — prefer that unless the actual codebase has already established a different pattern in Phases 5–7 worth following instead; state your choice). Keep it independent of the YOLO implementation, tracker implementation, API routing, and React components — unit-testable on its own with synthetic counting-event input, no video/model required.

## Metric Definitions (document all of these explicitly, with the real formula used)

- **Observation duration:** actual processed video/time duration — state precisely what this measures (wall-clock processing time is NOT the same as video duration; use video duration for flow-rate math, and be explicit about which one you're using where).
- **Total count:** unique vehicles per Phase 7's deduplication.
- **Flow rate:** `flow_rate = vehicle_count / observation_duration`, converted explicitly to vehicles/minute or vehicles/hour with clear unit handling.
- **Class percentage:** `class_percentage = class_count / total_count × 100`, with `total_count == 0` handled safely (report 0% or null, never divide by zero).
- **Directional flow:** taken directly from Phase 7's crossing-direction data, not re-derived.
- **Time buckets (if implemented):** crossing events assigned to intervals by their real timestamps — document the exact bucket boundaries/semantics (inclusive/exclusive edges).

## Data Model / Schemas

Inspect existing schemas (`videos`, detection, tracking, counting) before designing new ones — match the established naming and typing conventions rather than introducing a divergent style. A reasonable `TrafficMetricsResponse` shape: `video_id`, `observation_duration_seconds`, `total_vehicles`, `flow_rate_per_minute` (and `_per_hour` if justified), `inbound_count`, `outbound_count`, `class_counts`, `class_percentages`, `time_series` (if implemented), `generated_at` — adapt this if the actual repository's conventions suggest something better; don't copy it blindly.

## API

Extend the existing versioned API — a reasonable shape is `POST /api/v1/analytics/videos/{video_id}` or whatever is most consistent with the actual current conventions for videos/detection/tracking/counting (inspect and match; don't diverge). The endpoint should: validate the video exists server-side, run/reuse the existing pipeline (do not duplicate Phase 5–7 logic — call into it), obtain tracking/counting output, calculate analytics, and return structured metrics. No server filesystem paths in the response. Existing resource/processing bounds apply here too.

## Should Analytics Be Persisted?

Inspect the existing database architecture before deciding. Prefer computed-on-demand analytics for this phase (consistent with Phase 5/6/7's deferred-persistence pattern) unless there's a clear architectural reason persistence is needed now. If you do persist, explain why, keep the minimum data needed, and explain how you avoid duplicating data already recoverable from the pipeline. Do not build speculative analytics tables "for later."

## Frontend

Add a traffic-analytics view to the existing frontend, reusing its established components/design system — don't redesign the app. Reasonable components: Total Vehicles, Flow Rate, Inbound/Outbound counts, Class Distribution, Traffic Volume Over Time (if time-series is implemented), Direction Distribution, Observation Duration. Use charts only where they genuinely aid understanding — a plain number is fine for a single value. Every displayed number must come from a real API response — no hardcoded demo values. Handle loading, empty-results (zero vehicles), API-error, and backend-unavailable states explicitly, following the patterns already established in Phase 3's health indicator and Phase 4/7's upload/processing states.

## Time-Series Analytics (if implemented)

Base aggregation strictly on real event timestamps. Choose a reasonable default bucket interval given the actual video's duration (don't hard-code one interval regardless of clip length — a 5-second clip and a 5-minute clip need different defaults, or a clearly stated single default with rationale). Never manufacture a smooth curve — if there are only one or two real events, show that sparse reality rather than interpolating or padding it into something that looks like a trend.

## Data Honesty (non-negotiable)

Explicitly prohibited: fake vehicle counts, fake flow rates, fabricated time-series points, random statistics, hardcoded dashboard values, synthetic values presented as real traffic data, or silently extrapolating a short observation into an implied larger volume. Any extrapolated/estimated metric must be clearly labeled `ESTIMATED`/`EXTRAPOLATED` in both the API response and the UI, alongside the underlying observation duration it was derived from. Prefer reporting the real measured metric over extrapolating at all, where practical.

## Security / Resource Safety

Preserve every earlier-phase control: video IDs validated server-side, server-controlled storage paths, no arbitrary file paths accepted, bounded video/frame processing, safe handling of malformed videos, no unbounded memory accumulation, no unbounded time-series growth (cap bucket count if a pathologically long video is uploaded), structured error responses, no path leakage. Analytics calculation itself should not open a new resource-exhaustion vector (e.g., don't allow a request to trigger unbounded reprocessing).

## Testing

**Analytics engine (unit-level, synthetic counting-event input, no video/model needed):** zero vehicles; one vehicle; multiple vehicles; multiple classes; inbound-only traffic; outbound-only traffic; mixed inbound/outbound; class-percentage correctness; flow-rate calculation correctness; observation-duration handling; time-bucket aggregation (if implemented); duplicate-counting-event protection; missing/invalid timestamps handled safely; boundary timestamps (exactly at a bucket edge); short observation durations; division-by-zero protection (zero total count).

**API:** invalid video ID rejected cleanly; valid analytics request returns the documented schema; structured errors; resource bounds enforced; path isolation maintained.

**Regression:** run the entire existing backend suite and paste actual output — Phase 1–7 functionality must remain intact.

## Real End-to-End Verification Is Mandatory

Unit tests alone do not verify this phase. Create `scripts/verify_phase8_analytics.py` exercising the actual pipeline — `VideoSource` → detector → tracker → vehicle counter → analytics engine — against a deterministic video fixture that produces genuine tracked/counted vehicles. Print real calculated metrics (observation duration, unique vehicles, inbound/outbound, per-class counts, flow rate) — all actual values from the run, never fabricated.

## Analytics Verification Evidence

The completion report must show the arithmetic connecting real source events to calculated metrics, e.g.:

```
Crossing Events: Track #1 → bus → inbound, Track #2 → car → inbound, Track #3 → car → outbound
Analytics: Total = 3, Inbound = 2, Outbound = 1, Bus = 1, Car = 2
```

with flow rate computed from the actual observation duration — reviewable arithmetic, not just a final number.

## Performance Measurement

Report: video duration, frames sampled, detections processed, unique tracks, crossing events, vehicles counted, analytics-calculation time, total pipeline time, average runtime/frame, throughput. Separate ML/CV processing time from analytics-calculation time where practical. Do not invent any number.

## Frontend Verification

Verify and report: frontend typecheck, production build, real analytics-API integration, and the loading/empty/error states actually rendering correctly — a screenshot showing hardcoded numbers is not acceptable evidence.

## Documentation

Update `PROJECT_STATUS.md`, `ARCHITECTURE.md` (confirm the analytics module against §3's `TrafficMetricsEngine` description), `README.md` if warranted. Document: analytics architecture, every metric's exact formula, directional-flow semantics, time-series semantics (if implemented), the API endpoint and an example response, verification evidence, performance measurements, and known limitations — clearly distinguishing **measured data** from **example values** from **estimated/extrapolated values**.

## Git

Inspect `git status` before changes. After genuine implementation and verification: review changed files, remove any debugging artifacts, avoid unrelated changes, run tests, inspect the diff, and make one focused commit. Suggested: `feat: implement traffic analytics and flow metrics`.

## Completion Report

Require:

1. Implementation summary
2. Analytics architecture
3. Files created
4. Files modified
5. Metric definitions (all formulas)
6. Flow-rate formula
7. Directional-flow logic
8. Class-distribution logic
9. Time-series implementation (if any)
10. API endpoints
11. Frontend changes
12. Database changes, if any
13. Configuration changes
14. Security/resource controls
15. Unit test results (pasted, not summarized)
16. Full regression test results (Phase 1–7, pasted)
17. Real end-to-end verification output (from `scripts/verify_phase8_analytics.py`, pasted)
18. Source crossing events used for verification
19. Calculated analytics values
20. Arithmetic verification (showing the math checks out)
21. Performance measurements
22. Frontend typecheck/build results
23. Documentation updates made
24. Git commit hash
25. Known limitations
26. Any estimated/extrapolated metrics, clearly labeled as such
27. Explicit Phase 8 status: `VERIFIED` / `PARTIALLY VERIFIED` / `BLOCKED` / `FAILED`
28. Exact recommended next phase

`VERIFIED` requires real pipeline execution producing genuine metrics with reviewable arithmetic, passing unit tests, and passing full regression — not code that merely looks correct.

## Scope Boundary — Do NOT Implement

Vehicle speed estimation, lane detection, lane-level analytics, congestion prediction, traffic prediction, ML forecasting, signal-timing optimization, reinforcement learning, emergency corridor simulation, adaptive or autonomous traffic-light control. Those belong to later phases.

## Architectural Principle

Keep `VideoSource`, `Detector`, `Tracker`, `Counter`, `Analytics Engine`, API, and Frontend as logically separate layers, each with one clear responsibility — Phase 8 must not collapse into a monolithic analytics script.

## Final Scope

Phase 8 is exactly: **TRACKED VEHICLES + COUNTING EVENTS → TRAFFIC ANALYTICS & FLOW METRICS.** Nothing beyond that.
