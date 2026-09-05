# 07 — Vehicle Counting

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior backend/CV engineer converting persistent tracked trajectories into genuine, deduplicated vehicle counts. Counting operates on tracking output only — never on raw detections or frame counts.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`
3. `ARCHITECTURE.md` — §3 (CV Pipeline, especially `vehicle_counter.py`'s described role: "counts a track only when its trajectory crosses a configured line/zone — not per-frame"), §8 (database schema)
4. `README.md`
5. `SECURITY.md`
6. `prompts/antigravity/01` through `06` — for the accumulated architecture decisions and known discrepancies already on record
7. The actual current Phase 4 video-ingestion implementation, Phase 5 detector implementation, and Phase 6 tracker implementation
8. The actual current `DetectionResult` and `TrackingResult`/`TrackedObject` schemas — **inspect their real field names and shapes; do not assume they match this prompt's description**
9. The actual current `VideoSource` implementation
10. Current API routers, configuration/settings, frontend Video Analysis page, all existing tests
11. `backend/requirements.txt` and `.env.example`

**Do not blindly trust prior completion reports.** If the actual repository differs from what's described in Current State below, build against what's actually there and report the discrepancy. If a genuine gap makes Phase 7 impossible to build correctly, stop and report `BLOCKED`.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY → DOCUMENT → UPDATE PROJECT_STATUS.md → REPORT
```

## Context — Verify Before Building On It

Phases 1–2 were independently verified directly in a prior session. **Phases 3–6 were completed by prior Antigravity runs and are recorded in `PROJECT_STATUS.md` as *reported*, not independently re-verified in the environment this prompt was authored in.** Phase 6's reported scope: a `Tracker` consuming Phase 5's `DetectionResult`s, producing persistent track IDs via a ByteTrack/Kalman/IoU-based approach, with 43/43 backend tests passing and a documented track lifecycle. **Before writing any Phase 7 code, confirm this is actually true** by inspecting the repository and re-running the existing test suite yourself.

## Current State You're Building Against (per architecture docs + prior reports — confirm against actual code)

- `ARCHITECTURE.md` §3 already describes the intended role of a counting module: "counts a track only when its trajectory crosses a configured line/zone — not per-frame — so one vehicle is counted once." Phase 7 implements exactly this.
- A `Tracker` and `TrackingResult`/`TrackedObject` representation reportedly exist from Phase 6, including some form of persistent track ID. Whether it already carries centroid/position **history** (needed for crossing detection) is unconfirmed — check this first (see Track Trajectory Requirement below).
- No counting engine, no counting endpoint, and no counting persistence exist yet as of the state this prompt was written against — confirm this is still true.
- No counting-specific configuration exists yet in `.env.example`.

## Objective

```
Video → VideoSource → Detector → DetectionResult → Tracker → TrackedObject/trajectory
  → Counting Engine → Vehicle Counting Result
```

Convert tracked trajectories into genuine vehicle counts via configurable virtual-line crossing detection — never by counting raw detections, and never by counting every frame a track appears in.

## Counting Scope

Implement a clean, extensible counting abstraction (`CountingEngine`/`VehicleCounter`) supporting a configurable counting line for this first implementation (prefer line-crossing over zone-based for now — clearer, more verifiable semantics; a zone-based mode may be added later if architecturally easy, but isn't required). A vehicle is counted when its tracked trajectory genuinely crosses the configured line according to a well-defined direction rule. Explicitly avoid: counting the same track ID more than once, counting per-frame, counting from raw detection presence alone, fabricating counts, or using frame index as vehicle identity.

## Track-Based Counting Requirements

At minimum support: a unique total vehicle count, per-class counts, track-ID-based deduplication (each track counted at most once regardless of how many frames it crossed near the line), a configurable counting line, crossing-direction detection, and duplicate-count prevention. Example result shape (illustrative only — do not hard-code these numbers):

```json
{"total_count": 12, "by_class": {"car": 7, "bus": 2, "truck": 2, "motorcycle": 1}}
```

## Counting Engine Architecture

```
Tracker → TrackingResult → VehicleCounter → CountingResult
```

The counting engine consumes tracking results only — it must never depend on YOLO/the detector directly. Keep it independently testable (constructible and testable with synthetic trajectory data, no video/model required for unit tests). Do not put counting logic inside `detector.py`, `tracker.py`, the API router, or a frontend component — it's its own service module in `backend/app/services/cv/`, consistent with `detector.py`/`tracker.py`/`video_source.py`.

## Crossing Logic

Define crossing mathematically and implement it precisely: represent the counting line as two configurable points; determine which side of the line a vehicle's centroid occupies (e.g., via a cross-product/sign test, which works for arbitrary line orientation — don't restrict to horizontal/vertical lines only); compare the previous and current centroid side per track; a genuine side transition (not just proximity to the line) triggers a count; determine direction from the transition; count each track ID exactly once for its lifetime. Handle explicitly: a track starting near/on the line (don't double-trigger, don't miscount based on initial ambiguous side), a track disappearing before crossing (never counted), a track crossing and then moving back (still counted exactly once for the original crossing — don't double-count the return), multiple tracks crossing in nearby frames (each counted independently and correctly), temporarily lost tracks (per Phase 6's lifecycle — don't lose the crossing-state when a track is merely "temporarily missing," but do handle it correctly if the track terminates instead), and terminated tracks (no further counting activity for them). Choose a robust, justified approach — don't over-engineer beyond what these cases require.

## Track Trajectory Requirement

Inspect the actual current `TrackedObject`/`TrackingResult` representation from Phase 6 first. If it already carries centroid or position history sufficient for crossing detection, reuse it as-is. If it's insufficient (e.g., only the current-frame bounding box, no history), make the smallest clean addition needed (e.g., an appended centroid-history list) — do not redesign the tracker itself or add unrelated tracking features while you're in there.

## Configuration

Do not hard-code counting parameters. Using the existing settings conventions (`app/config/settings.py`, `.env.example`), add configuration only where justified — likely candidates: counting line coordinates (or a sensible default with documentation that it's configurable), a minimum-movement threshold to reduce noise-driven false crossings, and reuse of the existing `PROCESSING_FPS`/frame-limit conventions rather than inventing new equivalents. Never expose or accept arbitrary filesystem paths as part of this configuration.

## API

Extend the existing versioned API (`backend/app/api/v1/`) — a reasonable shape is `POST /api/v1/counting/videos/{video_id}` or whatever is most consistent with the actual current router conventions for videos/detection/tracking (inspect and match them; don't invent a divergent style). The endpoint should: validate the video exists (server-side, using the stored video, never a client-supplied path), run `VideoSource` → `Detector` → `Tracker` → `CountingEngine` (reusing the existing detector/tracker — do not reimplement or duplicate their logic), and return a structured counting result. No server filesystem paths in the response. Existing resource bounds (frame/duration limits) apply here too.

## Frontend

Extend the existing Video Analysis page only enough to demonstrate real counting — reuse its existing components/API-client conventions from Phases 3–6. Reasonable scope: a counting mode/trigger, a way to see or configure the counting line (even a simple visual overlay is enough — full interactive line editing isn't required unless it's easy given what's already there), total count and per-class counts displayed, crossing direction shown, and a visual indication when a vehicle actually crosses. All numbers shown must come from real backend results — no hard-coded demo statistics. Do not redesign the broader application or add unrelated UI.

## Database

Do not introduce a new counting table by default. Prefer computing counting results on demand from stored video + the existing pipeline for this phase — that keeps Phase 7 consistent with Phase 5/6's deferred-persistence pattern. If you find a genuine architectural reason persistence is needed now, implement it minimally, explain why in the report, and keep the schema small — don't build toward speculative future analytics tables in this phase.

## Security / Resource Safety

Preserve every earlier-phase control: video IDs validated server-side, storage paths remain server-controlled (never client-supplied), processing bounded (frame/duration limits enforced, not bypassed for counting), malformed input fails safely with the existing structured error shape, no path traversal, no unbounded CPU/memory usage, no internal path leakage in responses or logs.

## Testing

**Counting engine (unit-level, no video/model needed):** one object crosses the line → count 1; an object that never crosses → count 0; the same track ID crossing near the line across multiple frames → counted exactly once; multiple distinct vehicles → distinct, correct counts; per-class counts are correct; direction is correctly detected; reverse-direction crossing is correctly handled; an arbitrarily-oriented line is handled correctly (not just axis-aligned); a track starting near/on the line doesn't misfire; a temporarily-missing track resumes correctly; a terminated track doesn't get miscounted; duplicate-track-ID protection holds under adversarial-ish synthetic input.

**API:** invalid video ID is rejected cleanly; a valid counting request returns the documented schema; processing stays bounded; storage paths stay isolated; errors use the existing structured shape.

**Regression:** run the entire existing backend suite and paste actual results — Phase 1–6 functionality must remain intact.

## Real Verification Is Mandatory (unit tests alone are not sufficient)

Create a real, standalone verification script: `scripts/verify_phase7_counting.py`. It must exercise the actual `VideoSource` + Phase 5 detector + Phase 6 tracker + Phase 7 counting engine together (not mocks) against a real or deliberately constructed multi-frame fixture where a vehicle genuinely crosses the configured line. Capture and print real evidence in a form like:

```
Frame X: Track #1 centroid before line
Frame Y: Track #1 centroid after line
=> Track #1 counted exactly once
```

Also report: total count, per-class counts, direction, number of unique tracks, processing time, and throughput, and explicitly confirm no duplicate counting occurred. **Do not claim verification if no genuine line crossing actually occurred in the run.** If a real available video doesn't happen to produce a crossing, construct a deterministic multi-frame fixture that does — but still route it through the real pipeline components (detector/tracker/counter), not a hand-rolled shortcut that bypasses them.

## Performance

Measure and report: frames processed, detections, tracked objects, vehicles counted, total processing time, average time per frame, and throughput. Do not invent any of these numbers.

## Documentation

Update `PROJECT_STATUS.md`, `ARCHITECTURE.md` (confirm the counting module's real implementation against §3's description), and `README.md` if the feature set changed enough to matter. Document: counting architecture, counting semantics (the exact crossing rule), line configuration, direction logic, the API contract, the verification evidence from `scripts/verify_phase7_counting.py`, limitations, and measured performance — clearly distinguishing real measurements from illustrative examples.

## Git

Inspect `git status` before making changes. After genuine implementation and verification: review the changed files, avoid unrelated changes, and make one focused commit. Suggested: `feat: implement track-based vehicle counting`. Only commit if everything above is actually verified — not on the strength of code existing.

## Completion Report

Require:

1. Implementation summary
2. Files created
3. Files modified
4. Counting architecture
5. Crossing semantics (the exact rule used)
6. API endpoints
7. Frontend changes
8. Configuration changes
9. Database changes, if any, and why
10. Security/resource controls
11. Unit test results (pasted, not summarized)
12. Full regression test results (Phase 1–6, pasted)
13. Real counting verification output (from `scripts/verify_phase7_counting.py`, pasted)
14. Example genuine track-ID crossing evidence (real, in the Frame→centroid-side form above)
15. Total/per-class counts (from the real verification run)
16. Direction evidence
17. Performance measurements
18. Documentation updates made
19. Git commit hash
20. Limitations
21. Explicit Phase 7 status: `VERIFIED` / `PARTIALLY VERIFIED` / `BLOCKED` / `FAILED`
22. Exact recommended next phase

`VERIFIED` requires a genuine observed line crossing, correct exactly-once counting for that track, passing unit tests, and passing full regression — not code that merely looks correct.

## Scope Boundary — Do NOT Implement

Traffic congestion scoring, traffic flow analytics, lane detection or lane-level analytics, speed estimation, traffic prediction/ML forecasting, signal-timing optimization, emergency corridor simulation, reinforcement learning, or any dashboard beyond the minimum counting UI described above. Those belong to later phases.

## Final Scope

Phase 7 is exactly: **TRACKED VEHICLES → VEHICLE COUNTING.** Nothing beyond that.
