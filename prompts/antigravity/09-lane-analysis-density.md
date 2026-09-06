# 09 — Lane Analysis & Density Estimation

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior computer-vision/backend engineer adding lane/region-based analysis on top of the existing tracking pipeline: tracked vehicles → lane assignment → per-lane metrics → density estimation. This is configured-region assignment, not autonomous lane detection.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`
3. `ARCHITECTURE.md` — §3 (CV Pipeline, `lane_analyzer.py`'s described role), §8 (database schema, `lanes` table)
4. `README.md`
5. `SECURITY.md`
6. `prompts/antigravity/01` through `08` — accumulated architecture decisions and known discrepancies already on record
7. The actual current implementations of `VideoSource`, the Phase 5 detector, `DetectionResult`, the Phase 6 tracker, `TrackedObject`/trajectory representation, the Phase 7 vehicle counter and crossing events, and the Phase 8 traffic metrics engine and its schemas — **inspect real field names and shapes; do not assume they match this prompt's description**
8. Current API routers, configuration/settings, the frontend Video Analysis and Traffic Analytics pages, existing frontend types/API clients
9. Database models, migrations, all existing tests
10. `backend/requirements.txt` and `.env.example`

**Do not blindly trust prior completion reports.** If the actual repository differs from Current State below, build against what's actually there and report the discrepancy. If a genuine gap makes Phase 9 impossible to build correctly, stop and report `BLOCKED`.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY → DOCUMENT → UPDATE PROJECT_STATUS.md → REPORT
```

## Context — Verify Before Building On It

Phases 1–2 were independently verified directly in a prior session. **Phases 3–8 were completed by prior Antigravity runs and are recorded in `PROJECT_STATUS.md` as *reported*, not independently re-verified in the environment this prompt was authored in.** Phase 8's reported scope: a traffic-analytics engine consuming Phase 7 counting events, producing flow rate, class distribution, and directional-flow metrics from genuine data, with explicit `ESTIMATED`/`EXTRAPOLATED` labeling where extrapolation occurs, verified via a real `scripts/verify_phase8_analytics.py` run. **Before writing any Phase 9 code, confirm this is actually true** by inspecting the repository and re-running the existing test suite (and, ideally, `scripts/verify_phase8_analytics.py`) yourself.

## Current State You're Building Against (per architecture docs + prior reports — confirm against actual code)

- `ARCHITECTURE.md` §3 already names `lane_analyzer.py` with the role: "maps a tracked point to a configured lane polygon; computes per-lane count, density, queue length, estimated speed." Phase 9 implements the lane-assignment and count/density parts of this — **queue length and estimated speed are not required here** unless trivially available; don't force them in.
- `ARCHITECTURE.md` §8 already documents a `lanes` table (id, intersection_id, video_id, name, direction, polygon, counting_line). Use this as the starting point for lane configuration persistence if persistence is needed — don't invent a parallel schema without checking this first.
- No lane-assignment code, no density calculation, and no lane-analysis endpoint exist yet as of the state this prompt was written against — confirm this is still true.

## Scope Definition (read this before designing anything)

"Lane analysis" here means **assignment of tracked vehicles to configured, manually-defined lane/region polygons** — not autonomous lane-line detection, road segmentation, or CV-based lane discovery. Do not introduce any of that unless the repository already has such functionality and it's genuinely necessary (it doesn't, as of Phase 8). The goal is a reliable, honest lane-assignment and density foundation using explicit configured geometry.

## Objective

```
Video → Detector → Tracker → Tracked Vehicles → Lane/Region Assignment
  → Per-Lane Metrics → Density Estimation → API → Frontend Visualization
```

Given configured lane polygons and Phase 6's tracked vehicles, determine which lane (if any) each tracked vehicle occupies at each relevant frame, and compute measurable per-lane metrics including a clearly-defined density value. Build entirely on top of existing tracking output — never re-derive lane membership from raw detections.

## Core Features

**A. Configurable lane regions.** Each lane has a stable ID, a human-readable name, polygon coordinates, and optional direction metadata. Accept lane configuration via request input or persisted config per the project's existing schema conventions — never hard-code example coordinates into production logic.

**B. Track-to-lane assignment.** For each tracked vehicle, determine lane membership using a well-defined anchor point (centroid is the reasonable default — document exactly which point you use and why). Assigning by bounding-box overlap alone is not acceptable unless you explicitly justify that choice over a centroid-based approach.

**C. Stable lane assignment.** Prevent lane-flicker from small centroid movements near a polygon boundary. Choose a simple, justified stability policy — e.g., a minimum-persistence rule (require N consecutive frames in a new lane before switching) or a boundary tolerance margin. State your choice and reasoning; don't over-engineer beyond what boundary-jitter actually requires.

## Lane Metrics (every metric needs an explicit definition — no metric added just to look impressive)

Per configured lane: active tracked vehicles, unique vehicles observed, count by class, a defined density metric, lane occupancy percentage **only if it can be honestly defined** (see Occupancy vs Density below), directional counts **only if Phase 7's actual crossing-event data can be reliably associated with a specific lane** (see Directional Lane Analysis below), and lane-level traffic volume where appropriate.

## Vehicle Density Definition (be precise — this is the part most likely to be misrepresented)

Define density explicitly, e.g. `vehicle_density = vehicle_count_in_region / region_area`. **If lane polygon coordinates are image pixels (they will be, absent camera calibration), the result is an image-space metric — label it explicitly as such** (e.g., "vehicles per pixel²" or a documented normalized occupancy/density score), never as a real-world "vehicles/km²" or similar. Do not silently convert pixels to meters. If you use a normalized score instead of raw pixel-area density, document the exact normalization formula.

## Occupancy vs. Density

These are different metrics — don't conflate them. If occupancy is implemented, define it explicitly (e.g., proportion of region area covered by vehicle bounding boxes, with an explicit, documented policy for overlapping boxes — union area, not naive summed area, unless you justify otherwise). **If a metric can't be reliably measured from available information, don't implement it just for the dashboard** — honest absence beats fabricated precision.

## Lane Assignment Architecture

```
TrackedObject → Lane Assignment Engine → Lane-aware Tracked Objects
  → Density / Lane Metrics Engine → LaneAnalyticsResult
```

Use module names consistent with existing repository conventions (e.g., `LaneRegion`, `LaneAnalyzer`, `DensityCalculator` — adjust to match what Phases 5–8 actually established). Keep lane logic independent of the YOLO detector, tracker internals, vehicle-counter internals, API routing, and React components — no lane logic embedded directly inside `detector.py`, `tracker.py`, `vehicle_counter.py`, API routes, or frontend pages unless the existing architecture gives a compelling reason otherwise.

## Track ID Semantics

Use Phase 6 track IDs as the sole vehicle identity for lane analysis. Never: count every detection as a separate vehicle, mint new IDs for lane purposes, use frame numbers as identity, randomly assign lane identity, or duplicate a vehicle's presence across multiple lanes simultaneously (a track has one lane assignment at a given timestamp — or none, if outside all configured regions). Document an explicit policy for a track that genuinely moves between lanes over time (e.g., emit a lane-transition event, or simply reflect the current lane at each timestamp — your call, but state it clearly).

## Multi-Lane Support

The implementation must genuinely support 2+ lanes — verify this directly: vehicles in different lanes, distinct per-lane assignments, distinct per-lane counts and density. Do not build around a single hard-coded lane and claim multi-lane support without proving it.

## Density Calculation

Deterministic and reproducible: current vehicle count per region, region area (compute this correctly from the polygon — e.g., the shoelace formula for a simple polygon), and the resulting density metric with units always stated. Show your work in the verification evidence (see below) so the arithmetic is checkable.

## Temporal Density (only if it fits cleanly — not required to force in)

If implemented: timestamp → lane → tracked count → density, using real frame timestamps, no interpolated/fabricated points, no artificially smoothed curves, and a bounded number of stored time buckets (reuse the bucket-bounding principle from Phase 8).

## Vehicle Class Analysis

Per-lane class breakdown (car/bus/truck/motorcycle counts per lane) computed from actual tracked objects — no hardcoded dashboard values.

## Directional Lane Analysis

Only implement inbound/outbound-per-lane counts if Phase 7's crossing-direction data can be safely and reliably associated with a specific lane given the actual current architecture — do not infer direction from unrelated heuristics (e.g., don't guess direction from raw screen position independently of Phase 7's real crossing semantics). If this association can't be made reliably, omit the metric and say so explicitly rather than fabricating it.

## API

Inspect existing API conventions before choosing an exact route — something like `POST /api/v1/lane-analysis/videos/{video_id}` or `POST /api/v1/analytics/lane-analysis/{video_id}`, whichever matches the actual established pattern better. The endpoint should: validate the video and the lane/region configuration, load the server-controlled video, run/reuse `VideoSource` → detector → tracker (never duplicate their logic), assign tracked objects to lanes, calculate lane metrics and density, and return structured results. No server filesystem paths exposed. Existing resource limits apply.

## Request Configuration & Validation

Accept lane polygons via a structured request (adapt the exact shape to existing schema conventions rather than copying an example verbatim). Validate: each polygon has enough points to be a valid region, all coordinates are finite, coordinates fall within reasonable video-frame bounds, lane IDs are unique, lane names are valid/non-empty, the number of lanes is bounded (reject pathological requests), and polygon complexity (point count) is bounded.

## Frontend

Extend the existing frontend (Video Analysis / Traffic Analytics pages) without redesigning the app. Let users configure or select lanes, visualize lane polygons overlaid on the video, run lane analysis, and view per-lane metrics: vehicle counts, class distribution, density, and lane-level traffic volume, plus per-lane tracked-vehicle inspection. All values from real backend results — no fake lane statistics. Handle loading, empty data, invalid-polygon errors, backend errors, videos with zero detected vehicles, and lanes with zero vehicles.

## Visualization Semantics

Any density visualization must communicate what the metric actually means — label it "image-space density" (or whatever you call your normalized score), never imply "vehicles/km²" without real calibration. If a heatmap is implemented, it must be derived from actual tracked positions, not a stylistic approximation — and don't use a color scale that implies a physical-density standard the metric doesn't actually support.

## Security / Resource Safety

Validate video IDs, lane configuration, polygon coordinates, lane count, and polygon point count. Prevent arbitrary filesystem access, path traversal, unbounded polygon complexity, unbounded lane count, unbounded time-series storage, unbounded video processing, and memory exhaustion. Use the existing structured error responses. Never expose internal server storage paths.

## Testing

**Lane geometry:** valid polygon; invalid polygon; insufficient points; duplicate lane IDs; malformed/out-of-range coordinates; bounded lane count enforced.

**Assignment:** a vehicle clearly inside Lane 1; clearly inside Lane 2; outside all lanes; on a boundary (per your stability policy); multiple vehicles in different lanes simultaneously; the same track ID assigned consistently across multiple frames; a genuine lane transition; boundary jitter correctly suppressed; zero vehicles present.

**Density:** zero vehicles; one vehicle; multiple vehicles; different polygon areas produce correctly different densities; arithmetic is verifiably correct; unit labeling is present and correct; zero-area polygons are rejected/handled safely (no division by zero).

**Class metrics:** cars, buses, trucks, motorcycles, and a mixed-class scenario.

**API:** invalid video; invalid lane configuration; a valid lane-analysis request; correct response schema; resource bounds enforced; structured errors; path isolation maintained.

**Regression:** run the complete existing backend suite and paste actual output — Phase 1–8 functionality must remain intact.

## Real End-to-End Verification Is Mandatory

Unit tests alone don't verify this phase. Create `scripts/verify_phase9_lane_analysis.py` exercising the real pipeline — `VideoSource` → detector → tracker → lane assignment → density engine (and counter/analytics too, where it naturally fits) — against a deterministic multi-frame fixture with vehicles genuinely positioned in **at least two distinct lane polygons**. Demonstrate real track IDs, lane assignments, vehicle classes, per-lane counts, density calculations, and correct zero/empty-lane behavior. **Do not claim multi-lane verification if only one lane actually contains vehicles in the fixture.**

## Required Verification Evidence

Show frame-by-frame lane assignment and the resulting per-lane metrics in a checkable form, e.g.:

```
Frame 0: Track #1 car → Lane 1, Track #2 bus → Lane 2
Frame 5: Track #1 car → Lane 1, Track #2 bus → Lane 2
Lane 1: vehicles=1, cars=1, density=<real calculated value>
Lane 2: vehicles=1, buses=1, density=<real calculated value>
```

using real values from the actual run — the numbers above are illustrative only.

## Density Arithmetic Verification

Show the actual arithmetic, e.g. `Lane area = X px², Vehicles = Y, Density = Y / X = Z vehicles/px²` (or your normalized-score equivalent, with its formula shown) — reproducible from the numbers given.

## Real Data Honesty

Distinguish clearly, everywhere (code, API, docs, UI): **real measured data**, **configured geometry** (the lane polygons themselves), **derived metrics** (computed from the above), and **estimated/calibrated values** (none should exist in this phase, since no calibration is implemented — if you ever imply one, that's a bug). Never imply image-space density is a real-world physical density without actual camera calibration; if road dimensions aren't known, don't invent them.

## Performance Measurement

Report: video duration, frames sampled, raw detections, unique tracks, lane assignments made, vehicles per lane, density calculations performed, total processing time, average runtime/frame, throughput. Separate CV processing time from lane-analysis calculation time where practical. Do not invent any number.

## Frontend Validation

Run and report: typecheck, production build, real API integration, lane-visualization rendering, empty-state and error-state behavior. A screenshot with hardcoded metrics is not acceptable evidence.

## Documentation

Update `PROJECT_STATUS.md`, `ARCHITECTURE.md` (confirm `lane_analyzer.py`'s actual implementation against §3, and the `lanes` table against §8), `README.md` if warranted. Document: lane-analysis architecture, polygon configuration, the exact track-to-lane assignment rule and anchor point used, boundary/stability handling, the density formula and its units, occupancy semantics if implemented, the API contract, verification evidence, performance, and known limitations. Explicitly state: **"Image-space density is not equivalent to vehicles/km² without camera calibration"** if that's the implemented model (it should be, per this phase's scope).

## Git

Inspect `git status` before changes. After genuine implementation and verification: review changed files, remove debugging artifacts, run the complete test suite, inspect the diff, avoid unrelated modifications, and make one focused commit. Suggested: `feat: implement lane analysis and density estimation`.

## Completion Report

Require:

1. Implementation summary
2. Architecture
3. Files created
4. Files modified
5. Lane-region representation
6. Polygon validation rules
7. Track-to-lane assignment algorithm (and anchor point used)
8. Boundary handling / stability policy
9. Lane-transition behavior
10. Density formula
11. Density units
12. Occupancy implementation, if any
13. Per-class lane metrics
14. Directional lane metrics, if supported (and why, if omitted)
15. API endpoints
16. Request/response schemas
17. Frontend changes
18. Configuration changes
19. Database changes, if any
20. Security/resource controls
21. Unit test results (pasted, not summarized)
22. Full regression test results (Phase 1–8, pasted)
23. Real end-to-end verification output (from `scripts/verify_phase9_lane_analysis.py`, pasted)
24. Track-ID-to-lane evidence (real, frame-by-frame)
25. Multi-lane evidence (proving 2+ lanes genuinely had vehicles)
26. Density arithmetic verification (reproducible)
27. Performance measurements
28. Frontend typecheck/build results
29. Documentation updates made
30. Git commit hash
31. Known limitations
32. Explicit statement: is density image-space or physically calibrated? (should be image-space)
33. Explicit Phase 9 status: `VERIFIED` / `PARTIALLY VERIFIED` / `BLOCKED` / `FAILED`
34. Exact recommended next phase

`VERIFIED` requires genuine multi-lane assignment with reviewable arithmetic, passing unit tests, and passing full regression — not code that merely looks correct.

## Scope Boundary — Do NOT Implement

Autonomous lane-line detection, road segmentation, camera calibration to real-world coordinates, speed estimation, congestion prediction, traffic prediction, ML forecasting, signal-timing optimization, reinforcement learning, adaptive/autonomous traffic-light control, emergency corridor simulation. Those belong to later phases.

## Architectural Principle

```
Video → VideoSource → Detector → Tracker → Tracked Vehicles
                                    ├→ Counter → Traffic Metrics ─┐
                                    └→ Lane Assignment → Lane Metrics ─┴→ Density Engine → API → Frontend
```

Each layer keeps one clear responsibility — do not merge counting, traffic analytics, and lane analysis into one monolithic service.

## Final Scope

Phase 9 is exactly: **TRACKED VEHICLES + CONFIGURED LANE/REGION POLYGONS → LANE ASSIGNMENT → LANE-LEVEL METRICS → DENSITY ESTIMATION.** Nothing beyond that.
