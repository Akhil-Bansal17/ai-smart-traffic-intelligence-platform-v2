# 04 — Video Ingestion

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior backend engineer building a secure video-ingestion pipeline: upload → validate → securely store → read metadata → extract frames → clean handoff to future CV phases. This phase is infrastructure, not computer vision — no detection, tracking, or analytics happens here.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`
3. `ARCHITECTURE.md` — read §3 (CV Pipeline), §7 (API surface), and §8 (Database Schema, `videos` table) in full.
4. `README.md`
5. `SECURITY.md`
6. The existing backend service/model structure: `backend/app/services/cv/` (currently empty except `__init__.py` — this is where the video-reading/frame-extraction foundation belongs), `backend/app/models/`, `backend/app/db/`, `backend/app/schemas/`, `backend/app/api/v1/`.
7. The completed Phase 3 frontend structure — **reported** complete (see Current State below), so inspect it directly rather than assuming its exact shape.
8. All existing tests and configuration: `backend/tests/`, `backend/requirements.txt`, `.env.example`, `backend/app/config/settings.py`.

If anything below conflicts with what you find in these documents or the repository itself, **the repository wins** — report the discrepancy rather than silently resolving it or building around it.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY → DOCUMENT → UPDATE PROJECT_STATUS.md → REPORT
```

Execute every step for real. A completion report is only as good as what was actually run and observed — see Completion Report below for the required format.

## Context

Phase 1 (scaffolding) and Phase 2 (backend foundation) are complete and were independently verified in a prior session — see `PROJECT_STATUS.md` for the exact evidence (test output, live endpoint checks, a real PostgreSQL connection). **Phase 3 (frontend foundation) has been reported complete by a prior Antigravity run** with this claimed evidence: React 18 + TypeScript + Vite + Tailwind implemented, React Router with planned routes, a typed API client, a genuine backend health indicator, frontend typecheck passing, production build passing, 6 backend tests passing, 15 frontend/backend integration tests passing, backend left untouched, committed as `feat: initialize frontend foundation`. **This report has not been independently re-verified in the environment this prompt was written in — you must verify it yourself** by inspecting the actual repository and, ideally, re-running the Phase 3 checks before building on top of them. If what you find doesn't match this claim, stop and report the discrepancy before proceeding into Phase 4.

## Current State You're Building Against (verify all of this yourself)

- Backend has a versioned API (`/api/v1/...`) with centralized exception handling returning `{"error": {"code": "...", "message": "..."}}` (`backend/app/core/exceptions.py`), structured logging (`backend/app/core/logging.py`), Pydantic settings loaded from `.env` (`backend/app/config/settings.py`), and a SQLAlchemy engine/session + Alembic migration foundation already wired up and previously verified against a live PostgreSQL instance (`backend/app/db/`, `backend/migrations/`).
- `.env.example` **already defines** `UPLOAD_DIR=./uploads`, `MAX_UPLOAD_SIZE_MB=500`, `ALLOWED_VIDEO_EXTENSIONS=.mp4,.avi,.mov`, and `PROCESSING_FPS=5` — these exist specifically for this phase. Use them; don't reinvent equivalents with different names.
- `ARCHITECTURE.md` §8 **already documents a `videos` table** (id, uploaded_by, original_filename, storage_path, duration_seconds, fps, resolution, uploaded_at, status). This means persistence was already architecturally decided in Phase 1 — you do not need to re-litigate whether a video record is justified, only implement it consistently with the existing SQLAlchemy/Alembic setup. If you find a genuine reason the documented schema is wrong, say so explicitly rather than silently changing it.
- `ARCHITECTURE.md` §3 already names a `VideoSource` module as part of the intended CV pipeline. Frame extraction in this phase should become (or lay the foundation for) that module — don't invent a differently-named, parallel abstraction.
- **Known discrepancy to resolve:** `ARCHITECTURE.md` §7's example endpoint list shows `POST /api/videos/upload` (unversioned), but the actual implemented convention from Phase 2 is versioned (`/api/v1/health`, etc.). Use the versioned convention (`/api/v1/videos/upload`) for consistency with what's actually running, and update §7's example list to match while you're in there.
- No frontend upload UI, no video model, no upload endpoint, and no frame-extraction code exist yet as of the state this prompt was written against — confirm this is still true before starting.

## Objective

Establish a secure, production-quality video-ingestion pipeline: accept a traffic video upload, validate it thoroughly (extension, MIME, size, content-level readability), store it safely, extract and persist its metadata, provide a frame-extraction foundation for future CV phases to consume, and expose this through the existing versioned API with consistent error handling. Nothing beyond ingestion — no detection, tracking, counting, or analytics.

## Scope — In Scope

- Video upload endpoint (`POST /api/v1/videos/upload`) with request/response schemas.
- Supported-format, MIME, and extension validation (client-supplied MIME/extension is never trusted alone — validate actual file content).
- File-size limits enforced server-side, driven by `MAX_UPLOAD_SIZE_MB`.
- Secure filename handling: sanitize the original filename, never use it directly as a storage path component; generate a collision-safe storage name (UUID-based or equivalent).
- Path-traversal protection on any filesystem operation involving user-supplied input.
- A dedicated, isolated upload directory (`UPLOAD_DIR`), with a clear policy on temporary-vs-persistent storage and cleanup of failed/partial uploads.
- Video metadata extraction: duration, width, height, fps, frame count where reliably available, codec/container info where practical.
- Content-level validation that the file is actually a readable video, not just correctly named/typed (protects against extension/MIME spoofing and corrupted uploads).
- A frame-extraction foundation (feeding `backend/app/services/cv/`) with configurable sampling driven by `PROCESSING_FPS` — extracting/sampling frames, not analyzing them.
- Persistent `videos` record per `ARCHITECTURE.md` §8, via a new Alembic migration.
- Structured, centralized error responses consistent with `app/core/exceptions.py` — no raw stack traces, no internal filesystem paths in API responses.
- Logging that never leaks full server-side paths or unnecessary detail to logs a client could see, while still being useful for debugging server-side.
- A full test suite (see Testing below).
- Only the frontend surface genuinely needed to drive this workflow (see Backend/Frontend Boundary below).

## Explicit Exclusions — Do NOT Implement

YOLO detection, vehicle detection, ByteTrack/BoT-SORT or any object tracking, vehicle counting, lane detection/assignment, traffic density or congestion scoring, traffic analytics, prediction/ML, signal optimization, or emergency corridor simulation. Frame extraction here means "produce frames for a future consumer," not "analyze frames." If you're tempted to add a detection call to prove frames work, don't — a frame-count/shape assertion in a test is sufficient proof.

## Backend/Frontend Boundary

Inspect the actual (reported-complete) Phase 3 frontend before deciding what to add — reuse its existing layout, API-client pattern, and component conventions (Button/Card/LoadingState/ErrorState/EmptyState) rather than introducing a parallel style.

Add only what Phase 4 genuinely needs on the Video Analysis page (which currently should be a placeholder per Phase 3): a working upload flow — file picker (drag/drop optional), visible supported-format and max-size info, upload progress/state, validation-error display, and a result view showing the extracted metadata once upload succeeds. **Do not build the full Video Analysis dashboard** (no detection overlay, no bounding boxes, no analytics panel — those belong to later phases). If a video has only been uploaded and validated, the UI must make that state visually distinct from "analyzed" — don't imply analysis has happened.

## Security Requirements

Treat every uploaded file as untrusted input. Explicitly address: filename sanitization, path-traversal prevention, extension-spoofing and MIME-spoofing resistance (validate actual content, not just headers/extension), enforced size limits, safe/isolated storage paths, collision-safe (UUID or equivalent) storage naming, preventing any possibility of uploaded content being executed, cleanup of failed/partial/temporary uploads, no secrets anywhere in source, no sensitive filesystem paths in API responses or error messages shown to the client, controlled/generic client-facing error messages with detail reserved for server logs, safe logging (no path/secret leakage), configurable upload limits (not hard-coded), and basic resource-exhaustion awareness (e.g., don't buffer an entire large file in memory if a streamed/chunked alternative is reasonably available in the framework). Do not weaken any existing security control (CORS, exception handling, logging conventions) to make uploads more convenient.

## Database

`ARCHITECTURE.md` §8 already justifies a `videos` table — implement it now:
- Add the SQLAlchemy model consistent with the existing `Base` (`backend/app/db/base.py`) and the documented columns (id, uploaded_by [nullable is fine — no auth system exists yet, don't build one for this phase], original_filename, storage_path, duration_seconds, fps, resolution, uploaded_at, status).
- Generate a real Alembic migration (`alembic revision --autogenerate` or manually, your judgment) and verify it actually applies against a live PostgreSQL instance — don't just create the migration file, run it.
- Keep the model minimal and consistent with the documented schema; don't add speculative columns for future phases (e.g., no analysis-related fields — those belong with `analysis_sessions` in a later phase).

## API Design

Use the existing versioned router pattern (`app/api/v1/router.py`, following the `health.py` module as a template) — add a `videos` module, not a parallel API structure. Define clear Pydantic request/response schemas in `app/schemas/`. Response payloads should include useful metadata (duration, resolution, fps, status, an opaque video ID) while never exposing the real server-side storage path or filesystem layout. Errors must go through the existing centralized exception handling — add a new `AppException` subtype if a domain-specific error code is warranted (e.g., `unsupported_format`, `file_too_large`), rather than inventing a separate error-response shape.

## Configuration

Use the existing `.env.example` variables (`UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, `ALLOWED_VIDEO_EXTENSIONS`, `PROCESSING_FPS`) via `app/config/settings.py` — do not hard-code any of these values or any filesystem path. If a genuinely new variable is required (e.g., a temp-directory path, a max-duration limit), add it to both `.env.example` (placeholder value) and `Settings`, and explain why it was needed. Never commit a real `.env` or any secret value.

## Performance

Do not load an entire large video file into memory to validate or process it. Prefer a streaming/chunked upload approach if reasonably supported by FastAPI/Starlette, or clearly justify why a simpler approach is acceptable given the configured size limit. Frame extraction should avoid full-video decoding when only metadata or a sampled subset of frames is needed — use the sampling rate from `PROCESSING_FPS` rather than decoding every frame. Keep resource usage bounded and configurable, not hard-coded.

## Testing

At minimum, real (not described, actually run) tests for:
1. Valid, supported video upload succeeds end-to-end.
2. Unsupported extension is rejected with a clean error.
3. Spoofed/invalid MIME type is rejected (extension says one thing, content is another).
4. Oversized file is rejected.
5. Malicious/path-traversal filename (e.g., `../../etc/passwd`, embedded null bytes, etc.) is safely handled and never escapes the upload directory.
6. Empty or malformed upload is rejected cleanly.
7. Corrupted/unreadable video (correct extension, garbage content) is detected and rejected, not silently accepted.
8. Metadata extraction returns correct values for a small known-good test fixture.
9. Frame extraction produces the expected number/shape of sampled frames for a known fixture.
10. Successful API response has the correct shape and status code.
11. Validation errors use the existing structured error shape.
12. Cleanup behavior: a failed/rejected upload doesn't leave orphaned files in the upload directory.
13. Frontend upload/error/loading/empty states, if frontend changes were made — cover at least: idle, uploading, success-with-metadata, and validation-error.
14. The full existing backend test suite still passes (no regressions).
15. Frontend build/typecheck (if frontend changes were made) still passes.

Use small, deterministic test video fixtures (a few seconds, tiny resolution) — do not require large real traffic footage or datasets to test ingestion.

## Acceptance Criteria (Phase 4 is not done until every line here is true and verified)

- [ ] `POST /api/v1/videos/upload` exists, documented, and returns the correct schema on success.
- [ ] All 15 test categories above exist and pass, with real output captured.
- [ ] A malicious filename cannot write outside `UPLOAD_DIR` — proven by an actual test, not just code review.
- [ ] A file with a spoofed extension/MIME is rejected based on actual content validation, not just the claimed type.
- [ ] Oversized files are rejected server-side regardless of what the client claims.
- [ ] A `videos` row is created for a successful upload, via a real, applied Alembic migration — verified against a live database, not just present as a migration file.
- [ ] No raw filesystem path, stack trace, or internal detail appears in any API response.
- [ ] No secret or environment-specific path is hard-coded anywhere in the diff.
- [ ] Failed/rejected uploads leave no orphaned files behind.
- [ ] The existing 6 backend Phase 2 tests still pass unmodified (regression check).
- [ ] If frontend changes were made: build and typecheck still pass, and the upload flow visibly distinguishes "uploaded" from "analyzed."
- [ ] Nothing from the Explicit Exclusions list was implemented, even partially.
- [ ] `PROJECT_STATUS.md` reflects the true, verified end state.

## Documentation

Update `PROJECT_STATUS.md` (phase status, what's implemented, latest test evidence), `README.md` if the feature set changed enough to matter, and `ARCHITECTURE.md` §7 (fix the unversioned endpoint example noted above; add the real request/response schema if useful) and §8 (confirm the `videos` table as actually implemented, noting any deviation from the original design and why). If the project has any auto-generated API documentation (FastAPI's `/docs`), confirm the new endpoint appears correctly there — no extra doc system needs to be introduced for this. Document explicitly: supported formats, size limits, the upload endpoint's contract, storage behavior, metadata behavior, frame-extraction behavior, all relevant configuration variables, and known limitations.

## Git

One commit once everything above is verified working. Suggested: `feat: implement secure video ingestion`. If the actual implementation is better described differently, choose a more accurate conventional-commit message and report what you used and why. Do not bundle unrelated changes. If you find and fix a genuine Phase 1–3 defect while inspecting, commit it separately with its own justified message.

## Completion Report

Follow the format in `00-master-project-context.md`, and include explicitly:

1. Overall classification: `VERIFIED` / `PARTIALLY VERIFIED` / `NOT IMPLEMENTED` / `BLOCKED`
2. Implementation summary
3. Files created/modified
4. Dependencies added (and why each was necessary)
5. API endpoints added
6. Database changes (model + migration, confirmed applied)
7. Configuration changes (new/changed env vars)
8. Security controls implemented (map each back to the Security Requirements list)
9. Exact commands executed
10. Actual test results (pasted output, not a summary)
11. Upload verification (real request/response evidence)
12. Metadata-extraction verification (actual values from a real test fixture)
13. Frame-extraction verification (actual evidence, e.g., frame count/shape from a real run)
14. Invalid-input verification (evidence for each of the malicious/invalid cases in Testing)
15. Frontend verification, if applicable
16. Regression results for Phases 1–3 (paste actual re-run output — this is your independent re-verification of the reported Phase 3 state, not just this phase's own tests)
17. Known issues
18. Limitations
19. Anything intentionally deferred to a later phase, and why
20. Exact recommended next phase

Never mark anything `VERIFIED` because the code exists and looks right — only because you ran it and observed the claimed behavior. If something is `BLOCKED`, state exactly what's blocking it and what you need to proceed.

## Scope Reminder

This phase is exactly: **UPLOAD → VALIDATE → SECURELY STORE → READ METADATA → EXTRACT FRAMES → PROVIDE CLEAN HANDOFF TO FUTURE CV PHASES.** Nothing more.
