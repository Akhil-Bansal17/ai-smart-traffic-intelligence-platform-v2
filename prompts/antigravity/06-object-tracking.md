# 06 — Object Tracking

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior computer-vision engineer adding object tracking on top of Phase 5's detector: detections in, persistent track IDs out. Tracking is the only new CV capability in this phase.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`
3. `ARCHITECTURE.md` — read §3 (CV Pipeline — note the `tracker.py` row already describes a `Tracker` interface with an `update(detections) -> tracked_objects` signature; treat this as the intended shape unless the actual Phase 5 code did something meaningfully different) and §8 (`detections` table) in full.
4. `README.md`
5. `SECURITY.md`
6. Phase 5's actual detector implementation: `backend/app/services/cv/detector.py` and its `DetectionResult` schema (likely `backend/app/schemas/detection.py`) — **inspect the real interface and field names; don't assume they match this prompt's description until confirmed.**
7. Phase 5's detection API/router implementation.
8. `VideoSource` (`backend/app/services/cv/video_source.py`).
9. Existing database models/session architecture.
10. The existing frontend Video Analysis page (as it stands after Phase 5).
11. All existing tests.
12. `backend/requirements.txt` and `.env.example`.
13. The rest of `backend/app/services/cv/` for overall CV service structure conventions.

**Do not blindly trust the Phase 5 completion report.** If the actual repository differs from what's described in Current State below — different field names, a different return shape, missing pieces — build Phase 6 against what's actually there and report the discrepancy. If a genuine gap makes Phase 6 impossible to build correctly, stop and report `BLOCKED` rather than guessing or silently patching Phase 5.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY → DOCUMENT → UPDATE PROJECT_STATUS.md → REPORT
```

## Context — Verify Before Building On It

Phases 1–2 were independently verified directly in a prior session. **Phases 3, 4, and 5 were completed by prior Antigravity runs and are recorded in `PROJECT_STATUS.md` as *reported*, not independently re-verified in the environment this prompt was authored in.** Phase 5's reported scope: a working `Detector` abstraction backed by YOLOv8n, running real CPU inference (~45.8 ms/frame reported), producing structured `DetectionResult`s (class, confidence, bbox, frame index, timestamp — deliberately no track ID), 31 backend tests passing, frontend typecheck/build passing, Phase 1–4 regression passing, and detection persistence deliberately deferred (no `detections` table populated yet). **Before writing any Phase 6 code, confirm this is actually true** by inspecting the repository and re-running the existing test suite yourself.

## Current State You're Building Against (per architecture docs + Phase 5 report — confirm against actual code)

- A `Detector` interface and YOLOv8n implementation exist in `backend/app/services/cv/detector.py`, producing `DetectionResult` objects with no track ID field (by design — tracking is this phase).
- `ARCHITECTURE.md` §8's `detections` table already includes `track_id` and `analysis_session_id` columns, but Phase 5 reportedly did **not** persist detections at all (chose to return them as structured API output only). This means Phase 6 inherits the same open question: whether to start persisting now.
- No tracker code, no tracking endpoint, and no tracking persistence exist yet as of the state this prompt was written against — confirm this is still true.
- `.env.example` has no tracker-specific configuration yet — you'll likely need to add some (see Configuration below).

## Objective

Given a sequence of per-frame `DetectionResult`s from Phase 5's detector, associate detections across consecutive frames so the same physical vehicle keeps one persistent track ID over time, and return structured tracking results. Build this behind a `Tracker` interface, separate from `Detector`, matching the shape already sketched in `ARCHITECTURE.md` §3.

## Tracking Scope

Implement a `Tracker` interface distinct from `Detector`:
- **Detector** answers "what objects are present in this frame?"
- **Tracker** answers "which detection belongs to which previously observed object?"

The tracker consumes `DetectionResult`s from Phase 5 — it must never call YOLO directly. Do not merge detection and tracking into one monolithic service. A tracking result contains at minimum: `track_id`, class, confidence, bounding box, frame index, and timestamp where available.

## Tracker Implementation

Inspect `backend/requirements.txt` for any existing tracking dependency before adding one. If none exists, select a lightweight tracker appropriate for CPU development — ByteTrack or BoT-SORT are reasonable defaults per `ARCHITECTURE.md`, but you may choose differently with a stated reason (e.g., a simpler IoU-based tracker if a full ByteTrack/BoT-SORT dependency is impractical in this environment — state that tradeoff explicitly if you go that route). **The tracker must genuinely associate detections between frames** (e.g., via IoU/motion matching or the chosen library's real algorithm) — a tracker that just assigns IDs by frame order or detection-list position is not acceptable and does not satisfy this phase. It must handle: multiple simultaneous vehicles, vehicles entering/leaving frame, brief missed detections (occlusion), and different vehicle classes, all receiving correct persistent IDs. Never state a tracking accuracy figure (e.g., MOTA, IDF1) unless you actually computed it against ground truth — if you don't have ground truth for this fixture, don't report an accuracy number at all, just the observed behavior.

## Architecture

```
VideoSource → Detector → DetectionResult → Tracker → TrackingResult
```

Implement the `Tracker` interface and concrete implementation in `backend/app/services/cv/tracker.py`, consistent with `detector.py` and `video_source.py` — not a parallel module structure. No tracker logic inside API route handlers or React components — the service layer owns tracking.

## Explicit Exclusions — Do NOT Implement

Vehicle counting, lane detection or assignment, traffic density, congestion scoring, traffic analytics, prediction, signal optimization, emergency corridor simulation. Tracking is the only new capability. Do not implement a "quick count" to demonstrate tracking works — track-ID continuity across frames is sufficient proof.

## Track ID Requirements

Track IDs must be: generated by the tracker itself (never copied from a YOLO output field, since YOLO doesn't produce persistent IDs); stable/persistent across frames for the same physical object while the tracker maintains the association; never random per frame; never derived solely from bounding-box coordinates (coordinates change frame to frame — that's what makes association nontrivial); clearly distinct from detection class IDs. Document the track lifecycle explicitly in code comments and in `PROJECT_STATUS.md`/`ARCHITECTURE.md`: **new → active → temporarily missing → terminated**, including your chosen thresholds (e.g., how many missed frames before a track is terminated) as configuration, not a hard-coded magic number.

## Database

Phase 5 deliberately deferred persistence. Decide for Phase 6 based on the actual current implementation, not speculation:
- If Phase 5 truly persisted nothing, the simplest consistent choice is to **also not persist tracking results yet** — return them as structured API output, and defer the full `detections`/`track_id`/`analysis_session_id` persistence to whichever phase actually needs durable storage (e.g., Phase 9's Traffic Analytics, which needs historical data). State this explicitly as a deliberate deferral if you choose it.
- If you determine persistence is genuinely needed now (e.g., because a later requirement in this prompt can't be satisfied without it), implement it minimally and consistently with existing Alembic conventions, using the already-documented `detections` table columns — do not invent new speculative tables.

Either way, do not create analytics or session tables "because a future phase might need them" — that's over-building for a phase that isn't this one.

## API

Extend the existing detection/video API structure (`backend/app/api/v1/`) rather than creating a parallel one. The API must clearly distinguish detection results from tracking results in its response shapes/endpoint naming — a caller should never have to guess which one they got. No internal filesystem paths in responses. No accepting arbitrary filesystem paths from clients. Tracking must only operate on legitimate, already-uploaded videos (validate the video ID server-side). Resource limits from earlier phases remain enforced, not bypassed for tracking.

## Frontend

Extend the existing Video Analysis page only enough to demonstrate real tracking — don't build the eventual full CV dashboard. Reasonable scope: select an uploaded video, trigger tracking, show a loading/progress state, display a preview frame (or a few frames) with bounding boxes and their **visible track IDs**, plus class and confidence per box — e.g., "Track ID: 7 · car · 0.91". The same physical vehicle should visibly show the same track ID across consecutive displayed frames when the tracker successfully maintains the association — this is the actual demonstration of the feature, not a cosmetic detail. Do not build a vehicle-counting dashboard, lane visualization, congestion dashboard, or analytics charts.

## Security / Resource Management

Tracking is more computationally expensive than single-frame detection — enforce configurable limits on frames processed, video duration, and per-request execution time/memory. Never accept an arbitrary model or file path from a client. No internal path leakage in responses or logs. No secrets logged. Do not weaken any Phase 4 upload security control.

## Testing

At minimum, real (not described, actually run) tests for:
1. Tracker initializes correctly.
2. A single detection creates a new track.
3. The same object across consecutive frames retains the same track ID.
4. Multiple simultaneous objects receive distinct track IDs.
5. Different object classes are tracked correctly and independently.
6. A genuinely new object receives a new track ID (not reused from another track).
7. A temporarily missing detection (simulated occlusion/miss) is handled per your documented lifecycle policy, not by crashing or silently dropping the track prematurely.
8. A terminated track does not incorrectly reappear as continuing the same identity if a new, different object later appears in a similar location.
9. The tracking-result schema is correct (fields present, correctly typed).
10. An invalid/nonexistent video ID is rejected cleanly by the tracking endpoint.
11. The API response schema correctly distinguishes tracking results from detection results.
12. No filesystem path leaks through any API response.
13. The full existing Phase 1–5 backend test suite still passes (regression check — paste actual output).
14. Frontend typecheck/build still pass, if frontend changes were made.

Use deterministic synthetic or small real fixtures — don't rely solely on a large real traffic dataset for unit-level coverage.

## Real Tracking Verification (required — this phase is not abstract)

Run the tracker against a real short video or a deterministic multi-frame fixture containing multiple detectable vehicles, and capture genuine evidence: frames processed, total detections, number of unique track IDs produced, and — critically — sample evidence of ID continuity across frames, in a form like:

```
Frame 0 → car → Track 1
Frame 1 → car → Track 1
Frame 2 → car → Track 1
```

Also report the classes, actual bounding boxes, and confidence values observed, and the measured tracking runtime. **This must be real observed output from an actual run — not a constructed example.** If real tracking cannot actually run in your environment, report `BLOCKED` or `NOT IMPLEMENTED` — never `VERIFIED`.

## Performance

Measure and report: hardware, Python version, the tracker implementation/library and its version, frames processed, average processing time per frame, and observed FPS if meaningful. Do not claim real-time performance without measurement.

## Documentation

Update `PROJECT_STATUS.md`, `ARCHITECTURE.md` (confirm the `Tracker` module's actual implementation against §3's description, and update §8 if your database decision changes anything there), `README.md` where relevant, and `.env.example` if you introduce tracker configuration (e.g., a max-missed-frames threshold, an IoU/matching threshold). Document explicitly: the tracker selected and its version/source, the tracker's architecture, configuration parameters, the track lifecycle (new/active/temporarily-missing/terminated) and its thresholds, known limitations, CPU/GPU behavior, and measured performance. Never state a tracking accuracy figure without an actual evaluation behind it.

## Git

One clean commit once everything above is genuinely verified. Suggested: `feat: add object tracking`. Do not bundle unrelated changes. If a genuine earlier-phase defect is found and must be fixed, commit it separately with its own justified message.

## Completion Report

Follow the format in `00-master-project-context.md`, and include explicitly:

1. Overall classification: `VERIFIED` / `PARTIALLY VERIFIED` / `NOT IMPLEMENTED` / `BLOCKED`
2. Implementation summary
3. Tracker abstraction/interface
4. Concrete tracker implementation
5. Tracker/library selected
6. Version/source
7. Files created/modified
8. Dependencies added
9. Configuration changes
10. API endpoints added/modified
11. Database changes and rationale (which option from the Database section, and why)
12. Frontend changes
13. Security controls
14. Exact commands executed
15. Actual test output (pasted, not summarized)
16. Real tracking verification evidence (from an actual run)
17. Sample track-ID continuity evidence (real, in the Frame→Class→Track form above)
18. Runtime/performance measurements
19. Phase 1–5 regression results (paste actual re-run output — this is your independent re-verification of the reported Phase 3/4/5 state)
20. Known issues
21. Limitations
22. Anything intentionally deferred, and why
23. Exact recommended next phase

`VERIFIED` means real object tracking actually ran, track IDs were genuinely maintained across multiple frames where appropriate, required tests passed, and Phase 1–5 regression checks passed — not that the code exists and looks plausible.

## Final Scope

Phase 6 is exactly: **DETECTIONS → OBJECT ASSOCIATION → PERSISTENT TRACK IDs → STRUCTURED TRACKING RESULTS.** Nothing beyond tracking. Do not implement Phase 7 (vehicle counting) or any phase beyond this one.
