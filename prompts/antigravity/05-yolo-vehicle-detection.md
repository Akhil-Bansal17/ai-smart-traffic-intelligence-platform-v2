# 05 — YOLO Vehicle Detection

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior computer-vision engineer adding the first real inference capability to this platform: frame → YOLO model → vehicle detections → structured results. This is detection only — no tracking, counting, or analytics happens in this phase.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`
3. `ARCHITECTURE.md` — read §3 (CV Pipeline), §6 (Decision-Support Simulations — for context on what NOT to build yet), §7 (API surface), and §8 (`detections` table) in full.
4. `README.md`
5. `SECURITY.md`
6. `backend/app/services/cv/video_source.py` and whatever else exists under `backend/app/services/cv/` from Phase 4 — **inspect the actual current contents; don't assume the shape described in the Phase 4 completion report until you've confirmed it yourself.**
7. Existing models (`backend/app/models/`), schemas (`backend/app/schemas/`), API router structure (`backend/app/api/v1/`), database/session architecture (`backend/app/db/`), and configuration (`backend/app/config/settings.py`).
8. The frontend Video Analysis page as it actually exists after Phase 4.
9. All existing tests (`backend/tests/`, and any frontend tests).
10. `backend/requirements.txt` and `.env.example`.

If anything in this prompt conflicts with what you find in the repository, **the repository wins** — report the discrepancy explicitly rather than building around an assumption.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY → DOCUMENT → UPDATE PROJECT_STATUS.md → REPORT
```

## Context — Verify Before Building On It

Phases 1–2 (architecture, backend foundation) were independently verified directly in a prior session — see `PROJECT_STATUS.md` for that evidence. **Phases 3 and 4 were completed by prior Antigravity runs and are recorded in `PROJECT_STATUS.md` as *reported*, not independently re-verified in the environment this prompt was authored in.** Phase 4's reported scope: secure video upload with extension/MIME/content validation and size limits, secure UUID-based storage, a `videos` model with an applied Alembic migration, video metadata extraction, a `VideoSource` frame-extraction foundation, `POST/GET /api/v1/videos` endpoints, a frontend upload workflow, and passing test/regression evidence (19 backend tests, 20 frontend/integration tests). **Before writing any Phase 5 code, confirm this is actually true by inspecting the repository and re-running the existing test suite yourself.** If what you find differs from this description — different endpoint shapes, a different `VideoSource` interface, missing pieces — build Phase 5 against what's actually there and report the discrepancy; do not silently patch Phase 4 to match this description, and do not block Phase 5 on a Phase 4 gap unless it's genuinely impossible to proceed without fixing it (in which case, stop and report `BLOCKED` with specifics).

## Current State You're Building Against (per architecture docs — confirm against actual code)

- `ARCHITECTURE.md` §3 names `Detector` as its own interface, separate from `Tracker`, `VehicleCounter`, etc. — each pipeline stage is independently swappable. Phase 5 implements `Detector` only.
- `.env.example` **already defines** `YOLO_MODEL_PATH=./data_science/models/yolo_traffic.pt`, `DEFAULT_CONFIDENCE_THRESHOLD=0.4`, and `PROCESSING_FPS=5` — these exist specifically for this phase. Use them via `app/config/settings.py`; don't reinvent equivalents.
- `ARCHITECTURE.md` §8 documents a `detections` table with columns including `track_id` and `analysis_session_id` (both implying a tracking/analysis-session context that doesn't exist yet at Phase 5). **This is a known architectural tension you need to resolve, not ignore** — see the Database section below.
- No detector code, no inference endpoint, and no detection persistence exist yet as of the state this prompt was written against — confirm this is still true.

## Objective

Given a validated, previously-uploaded video (from Phase 4), run YOLO inference on its frames and return structured vehicle detections: class, confidence, bounding box, frame identifier, and timestamp where available. Build this behind a `Detector` interface so the underlying model implementation can be swapped later without touching anything that consumes it.

## Model

Inspect the repo for any existing YOLO dependency or model reference before choosing. If none exists, select a lightweight pretrained YOLO model suitable for CPU-friendly development use (your judgment on the exact variant — state and justify your choice in the report). Do not commit large model binaries into Git unless you have a specific, documented reason (e.g., note in `data_science/models/` why a binary is or isn't checked in, and make sure `.gitignore` already covers it — it currently ignores `*.pt`/`*.onnx`, confirm that's still appropriate). Model path, confidence threshold, device, image size, and sample FPS must all be configuration-driven, not hard-coded. **Never state an accuracy metric you haven't actually measured** — a pretrained model's general-purpose performance claims from its source are not this project's measured accuracy.

## Detection Scope

Detect the traffic-relevant classes the selected pretrained model actually supports — at minimum car, motorcycle, bus, truck if the model provides them. The class-ID-to-name mapping must come from the model's real class labels, not be invented or guessed, and must live in one centralized, configurable place — not scattered magic numbers across the codebase. Define and document your policy for non-vehicle detections the model produces (e.g., person, traffic light) — filter them, or include them with a category flag; either is fine, but be explicit and consistent.

## Architecture

```
VideoSource (Phase 4) → Frame → Detector interface → YOLO implementation → Detection results
```

Implement a `Detector` abstraction (interface/protocol) with a concrete YOLO-backed implementation, living in `backend/app/services/cv/` alongside `video_source.py` — consistent with the existing module, not a parallel structure. No YOLO calls directly inside API route handlers or (if frontend changes are made) React components — the service layer owns inference. Each detection result should carry class, confidence, bounding box, frame identifier/index, and timestamp where available — **do not include a track ID or any tracking-related field; that's Phase 6.**

## Explicit Exclusions — Do NOT Implement

ByteTrack, BoT-SORT, or any object tracking; persistent track IDs; vehicle counting; lane detection or assignment; traffic density; congestion scoring; traffic analytics; prediction; signal optimization; emergency corridor simulation. If you're tempted to add a "quick counting demo" to show detection is useful, don't — a raw detection list is sufficient proof for this phase.

## Inference Design

Run inference against frames produced by the Phase 4 `VideoSource` foundation — do not load an entire video into memory to do this. Support frame-by-frame or controlled small-batch inference, whichever fits the existing `VideoSource` interface better (state your reasoning). Configurable settings: model path, confidence threshold, device (`cpu` now; leave room for a future `cuda`/GPU config value without implementing GPU support), image size, and sample FPS (reuse `PROCESSING_FPS` rather than inventing a second sampling knob unless you have a concrete reason two are needed).

## API

Inspect the existing `backend/app/api/v1/` structure before designing the endpoint — extend it, don't parallel it. If an inference endpoint is appropriate (it likely is, given the objective), keep it under `/api/v1/...`, following the same schema/error-handling conventions as `videos` and `health`. Response payloads must expose structured detection results without leaking server filesystem paths. The response must clearly distinguish three states an uploaded video can be in: uploaded-only, frames-decoded, and detections-run — never imply a video has been analyzed when it hasn't.

## Database

`ARCHITECTURE.md`'s documented `detections` table assumes context (`track_id`, `analysis_session_id`) that doesn't exist until later phases (tracking = Phase 6, analysis sessions = a fuller pipeline concept). Resolve this deliberately, not by ignoring it:
- **Option A (recommended default, but your judgment):** don't persist detections yet — return them as structured inference output directly from the API for this phase, and defer the `detections` table's real implementation to whichever phase actually needs `track_id` populated (Phase 6 or later). If you choose this, explain why in your report and note it as a deliberate deferral, not an oversight.
- **Option B:** persist detections now with `track_id` nullable and either a nullable `analysis_session_id` or a minimal ad-hoc session record created per detection run. If you choose this, justify why persistence is needed now rather than in Phase 6, and keep the schema change minimal and consistent with existing Alembic conventions.

Either choice is acceptable — do not invent additional speculative columns for future tracking/analytics regardless of which option you pick.

## Frontend

Extend the existing (Phase 4) Video Analysis page only enough to demonstrate real detection — don't build the eventual full CV dashboard. Reasonable scope: select an already-uploaded video, trigger detection, show a processing/loading state, display a sampled frame with bounding boxes drawn over it, show detected class + confidence per box, and clearly label the output as "YOLO detections" (not "traffic analysis"). Do not build a vehicle-count dashboard, lane visualization, or congestion display — those are later phases. Never show fabricated detection results; if inference hasn't actually run for a video, the UI must not imply that it has.

## Security

Inference is resource-intensive — treat it accordingly: only run inference against videos that exist and were legitimately uploaded through Phase 4 (validate the video ID server-side, don't accept arbitrary filesystem paths from the client), bound processing (e.g., a reasonable cap on frames/duration processed per request, configurable), safe error handling with no internal paths in responses, no secrets, safe logging. Do not weaken any Phase 4 upload security control while integrating with it.

## Testing

At minimum, real (not described, actually run) tests for:
1. The detector initializes correctly with the configured model.
2. A known test frame produces detections.
3. The detection result schema is correct (all expected fields present, correctly typed).
4. Confidence values are valid (within [0, 1], or whatever range the model actually produces).
5. Bounding boxes are valid (coordinates within frame bounds, non-degenerate).
6. Vehicle class mapping is correct against the model's real labels.
7. Unsupported/non-vehicle classes are handled per your stated policy.
8. An empty/no-detection frame is handled correctly (empty result, not an error).
9. An invalid/nonexistent video ID is rejected cleanly by the inference endpoint.
10. The inference endpoint returns the documented response schema.
11. No filesystem path leaks through any API response.
12. The full existing Phase 1–4 backend test suite still passes (regression check — paste actual output).
13. Frontend typecheck/build still pass, if frontend changes were made.
14. All of the above use small, deterministic test fixtures — do not require large real traffic datasets for unit tests.

## Real Verification (required — this phase is not abstract)

You must actually run YOLO inference on at least one real, known test frame or short video fixture and capture genuine evidence: model loaded successfully, inference completed, number of detections returned, actual detected class names, actual confidence values, actual bounding-box dimensions. Do not fabricate or estimate any of this. **If the model cannot be downloaded or inference cannot actually run in your environment, the phase must be reported `BLOCKED` or `NOT IMPLEMENTED` — never `VERIFIED`,** regardless of how complete the surrounding code is.

## Performance

Measure and report actual inference runtime (e.g., time per frame or per short clip) on whatever hardware you're running on — don't claim "real-time" or any other performance characterization unless you measured it. CPU execution must work, since that's the default development environment. A GPU/`cuda` device option may exist in configuration for future use, but must not be described as currently available or tested unless it actually was.

## Documentation

Update `PROJECT_STATUS.md` (phase status, implementation summary, latest test/inference evidence), relevant README content, `ARCHITECTURE.md` (confirm the `Detector` module and, if applicable, the `detections` table's actual implementation against what's documented, noting any deviation and why), and `.env.example` if new configuration was introduced. Document explicitly: the selected YOLO model and its source/version, supported classes, confidence threshold, inference configuration options, CPU/GPU behavior (and which is actually tested), the detection response schema, and known limitations. Never state a model accuracy figure without a measured evaluation behind it.

## Git

One commit once everything above is verified. Suggested: `feat: add yolo vehicle detection`. If a more accurate conventional-commit message fits what was actually built, use it and report the choice. Do not bundle unrelated changes; if a genuine Phase 1–4 defect is found and fixed, commit it separately with its own justified message.

## Completion Report

Follow the format in `00-master-project-context.md`, and include explicitly:

1. Overall classification: `VERIFIED` / `PARTIALLY VERIFIED` / `NOT IMPLEMENTED` / `BLOCKED`
2. Implementation summary
3. Detector architecture (interface + concrete implementation)
4. YOLO model selected
5. Model source/version
6. Files created/modified
7. Dependencies added
8. Configuration changes
9. API endpoints added
10. Database changes, if any (and which option from the Database section you chose, and why)
11. Frontend changes
12. Security controls implemented
13. Exact commands executed
14. Actual test output (pasted, not summarized)
15. Real YOLO inference evidence (model load, detection count, classes, confidences, bbox dimensions — from an actual run)
16. Example detection output (real, from the run above)
17. Runtime/performance observations (measured, with the hardware/environment noted)
18. Phase 1–4 regression results (paste actual re-run output — this is your independent re-verification of the reported Phase 3/4 state)
19. Known issues
20. Limitations
21. Anything intentionally deferred to a later phase, and why
22. Exact recommended next phase

`VERIFIED` means real YOLO inference actually ran successfully and the required tests and regression checks actually passed — not that the code exists and looks plausible. If blocked by an environment limitation (e.g., can't download the model), report `BLOCKED` with exactly what's needed to unblock it.

## Final Scope

Phase 5 is exactly: **FRAME → YOLO MODEL → VEHICLE DETECTIONS → STRUCTURED RESULTS.** Nothing beyond detection.
