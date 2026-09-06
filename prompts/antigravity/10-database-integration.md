# 10 — Database Integration

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior backend engineer turning the existing PostgreSQL/SQLAlchemy foundation into a real persistence layer for the platform's already-verified CV pipeline. This is database integration, not a new CV capability.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `README.md`, `ARCHITECTURE.md` (§8, the documented schema — see Current State below), `PROJECT_STATUS.md`
3. `prompts/antigravity/01` through `09.1` — accumulated architecture decisions, known discrepancies, and the Phase 9.1 baseline-verification results if present
4. The actual current implementation under `backend/app/` — especially `models/`, `schemas/`, `api/`, `services/`, `config/`, `db/` — and `backend/alembic/` (or `backend/migrations/`, whichever the repo actually uses)
5. `backend/tests/` and any existing test fixtures/utilities
6. `frontend/src/` — especially the History page and any existing analysis-result views
7. `backend/requirements.txt` (or `pyproject.toml`), `frontend/package.json`, `.env.example`, `.gitignore`, pytest configuration

**Do not assume a component does or doesn't exist based on previous completion reports — the actual repository is authoritative.** In particular: confirm exactly which of `videos`, an analysis-run concept, `lanes`, `traffic_metrics`, and `detections` already exist as real SQLAlchemy models vs. are only described in `ARCHITECTURE.md` §8 as intended design. If the repository differs from Current State below, build against what's actually there and report the discrepancy. If a genuine gap makes Phase 10 impossible to build correctly, stop and report `BLOCKED`.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY → DOCUMENT → UPDATE PROJECT_STATUS.md → REPORT
```

## Context — Verify Before Building On It

Phases 1–2 were independently verified directly in a prior session. **Phases 3–9 were completed by prior Antigravity runs; Phase 9.1 (baseline verification & hardening) was intended to close the "reported, not independently verified" gap for all of them before Phase 10 begins.** Confirm the actual outcome of Phase 9.1 in `PROJECT_STATUS.md` before starting — if it was `PARTIALLY VERIFIED` or wasn't run at all, treat any phase it didn't fully confirm with the same "verify before building on it" caution as earlier prompts in this series required.

## Current State You're Building Against (per architecture docs — confirm against actual code)

- `ARCHITECTURE.md` §8 already documents this schema, designed back in Phase 1: **`videos`** (id, uploaded_by, original_filename, storage_path, duration_seconds, fps, resolution, uploaded_at, status), **`analysis_sessions`** (id, video_id, started_at, completed_at, status, total_vehicles, peak_traffic, avg_density, max_congestion, config_snapshot jsonb), **`lanes`** (id, intersection_id nullable, video_id, name, direction, polygon jsonb, counting_line jsonb), **`traffic_metrics`** (id, analysis_session_id, lane_id nullable, timestamp, vehicle_count, density_score, congestion_score, flow_rate, avg_speed_estimate, queue_length), **`detections`** (id, analysis_session_id, track_id, frame_number, timestamp, class, confidence, bbox jsonb, lane_id nullable, direction — explicitly *not* retained indefinitely per §8's own retention note).
- Per Phases 5–9's own prompts, **none of these have actually been implemented yet** — Phases 5, 6, 7, 8, and 9 all deliberately deferred persistence and returned structured API output directly instead. Phase 10 is where this catches up for real. Confirm this is still true before assuming a clean slate.
- A `videos` table may already exist from Phase 4 (video ingestion needed to persist upload metadata) — confirm its actual current columns against §8's design before extending it; don't create a duplicate.

## Objective

Turn the existing SQLAlchemy/Alembic/PostgreSQL foundation into a reliable persistence layer: results from the already-verified CV pipeline (detection → tracking → counting → analytics → lane analysis) get stored so they survive process restarts and can be retrieved later by the dashboard — without rewriting or duplicating any of that pipeline's logic.

## Explicit Exclusions — Do NOT Implement

New YOLO capabilities, new tracker algorithms, autonomous lane detection, speed estimation, prediction models, signal optimization, emergency corridor simulation, advanced ML, authentication, cloud deployment, or distributed processing. Those belong to later phases. Phase 10 is persistence only.

## Database Design Principles

Use the project's existing SQLAlchemy setup, PostgreSQL instance, Alembic migration system, naming conventions, UUID strategy, timestamp conventions, and configuration system — do not introduce a second ORM, do not introduce SQLite as a replacement or parallel store, do not create a second database layer. **First determine what already exists** (per Current State above) and extend it only where necessary — don't duplicate a model that's already there in a different but adequate shape.

## Required Persistence Scope

**A. Videos.** The existing (or Phase 4-created) `videos` record remains the source record. Persist: id, original filename, a safe storage reference (never a raw filesystem path exposed via API), duration, fps, width, height, frame count, status, upload timestamp, processing timestamp if appropriate, and bounded error/status info on failure. If fields already exist from Phase 4, don't duplicate them — extend only what's missing.

**B. Analysis Runs.** Introduce a persistent analysis/processing-run concept if one doesn't already exist (`analysis_sessions` per §8 is the intended home for this). It must record: which video, what analysis type(s) were performed (detection/tracking/counting/analytics/lane-analysis — use the repository's actual terminology for these, not invented names), start/completion time, current status, the configuration used (e.g., lane polygons, confidence threshold — a `config_snapshot` for reproducibility, per §8), and success/failure with bounded error detail on failure. Don't over-abstract this if a simpler single-table design genuinely fits better than a multi-type-run model — state your reasoning either way.

**C. Traffic Analytics Results.** Persist observation duration, total vehicle volume, flow rate (per minute/hour), **an explicit extrapolation flag** (Phase 8's data-honesty rule — if a rate was extrapolated from a short window, that fact must be persisted, not lost), class distribution, directional distribution, and time-series buckets if Phase 8 implemented them. Never persist a fabricated measurement, and never silently convert an image-space value into a physical unit.

**D. Lane Analysis Results.** Persist per-lane: the analysis-run reference, lane ID and name, a reference to the polygon/configuration used, polygon area, unique observed vehicle count, occupancy (active/peak/mean, whichever Phase 9 actually computed), class distribution, and the image-space density value. The schema must make it structurally obvious which fields are physical measurements (none, in this project, absent calibration), which are image-space measurements, and which are project-defined indicators — carry forward Phase 9's density-labeling discipline into the database, not just the API response.

**E. Counting Results / Crossing Events.** Decide deliberately whether to persist individual line-crossing events or only aggregate counts — evaluate based on what Phase 7 actually produces and what the dashboard genuinely needs. If persisting events, store: run reference, track ID, class, direction, frame index, timestamp, the counting-line reference, and a creation timestamp. **Enforce impossibility of duplicate counting at the persistence layer** (e.g., a uniqueness constraint on track ID per run per crossing), not just in application logic. Never create synthetic events to pad the table.

## Relationships and Data Integrity

```
Video → Analysis Run → Analytics / Lane / Counting Results
```

Use foreign keys, appropriate indexes (especially on `(analysis_session_id, timestamp)`-style time-series access patterns, matching §8's own indexing note), uniqueness constraints where justified (e.g., the counting-event dedup above), `NOT NULL` where appropriate, sensible cascade behavior (deleting a video's analysis run shouldn't orphan its results — decide and document the cascade policy), and correct transaction boundaries. Don't over-normalize — the schema should be reviewable by a junior developer, not a maze of indirection for theoretical future extensibility.

## Migrations

Alembic only, no manual schema edits. Inspect current migration history and the actual current schema first. Create the next migration(s) needed for this phase's models. Verify: the migration applies cleanly to a fresh database, applies cleanly to the existing development database, upgrades correctly, downgrades correctly where that's safe to test, and re-upgrades correctly afterward. Do not modify or delete existing migration history.

## Database Configuration

Confirm `DATABASE_URL` is used correctly and consistently, no credentials are hard-coded anywhere, `.env.example` has safe placeholders for anything new, connection configuration stays centralized in the existing `app/config/settings.py` + `app/db/session.py` pattern, and sessions/transactions are opened and closed correctly (no leaked sessions, no long-lived transactions across the CV processing itself — see Performance below). Never expose `DATABASE_URL`, credentials, or connection strings via API responses or logs.

## API Integration

Extend the existing versioned API (`/api/v1/...`) with the same schema, error-format, dependency-injection, and 404 conventions already established — no parallel API style. Evaluate and implement what's genuinely useful: list analysis runs for a video, retrieve a specific run, retrieve persisted analytics/lane/counting results, retrieve recent history. Never expose a raw SQLAlchemy model instance directly, never leak filesystem paths or internal DB details, and don't add an endpoint with no real frontend or programmatic purpose.

## Connecting Existing Processing to the Database (the critical part of this phase)

```
Video → Analysis Run → existing CV pipeline (unchanged) → Results → DB persistence → API → Frontend
```

**Do not rewrite the detector, tracker, counter, analytics engine, or lane analyzer** unless you discover a concrete compatibility defect while wiring persistence in (in which case, fix only that defect, document it, and don't use it as license to refactor further). Persist the output of the existing verified logic — the database is a new consumer of that output, not a second analytics engine recomputing anything.

## Frontend Integration

Don't redesign the frontend. Connect the existing History page (built as a placeholder in Phase 3) to real persisted data if that's genuinely achievable within this phase's scope: analysis history list, the ability to select and reload a previous analysis's results after a page refresh. If there's no persisted history yet (e.g., freshly migrated database), show an honest empty state — never seed or fabricate historical records to make the page look populated.

## No Fake Data (non-negotiable)

Never generate fake traffic statistics, seed fake analysis history, invent vehicle counts/timestamps/lane occupancy, or fabricate historical results. Test fixtures may generate synthetic data **inside automated tests only** — it must never appear as if it were real production data, and the UI/API must never blur that line. Do not ship seeded demo records unless explicitly required elsewhere and clearly labeled as demo data.

## Transaction and Failure Handling

If CV processing succeeds but persistence fails, don't silently report success — return a real error, preserve useful server-side diagnostic detail, and don't leave a partially-persisted invalid record behind (use a transaction boundary that makes this atomic, or clean up on failure). If processing itself fails, persist a genuine failed-run state if the architecture supports it — never a fake success or fake result row. Batch persistence sensibly (see Performance) rather than committing every individual detection/event as it's produced.

## Performance

Do not degrade the existing CV pipeline's performance by bolting on per-frame or per-detection database writes. Process in memory as today, then persist bounded results in batched transactions. Add indexes for the access patterns the new API endpoints actually use. Measure (or at minimum explicitly verify and report) that persistence overhead is small relative to CV processing time — don't just assert it's fine.

## Security

Focused review of: SQL-injection exposure (should be none, given ORM/parameterized queries — confirm no raw string-built SQL was introduced), path leakage, secret leakage, database-credential leakage, unsafe dynamic SQL, unbounded result queries (apply pagination/limits to any history/list endpoint), excessive payload sizes, and sensitive exception detail leaking to clients. Never expose `DATABASE_URL`, passwords, secret keys, raw filesystem paths, or internal stack traces.

## Testing

**Database foundation:** session creation, model creation, transaction commit, rollback behavior.

**Migrations:** upgrade, schema creation on a fresh database, migration consistency (re-running upgrade is a no-op / idempotent as expected).

**Models:** valid record creation, required-field enforcement, foreign-key enforcement, uniqueness-constraint enforcement, relationship traversal.

**Persistence:** video persistence, analysis-run persistence, analytics persistence, lane-result persistence, counting-event persistence if implemented.

**API:** create/retrieve/list behavior, a nonexistent resource returns a clean structured 404, response schemas validate, pagination/limits work, no internal path or secret leakage.

**Integration:** at least one genuine end-to-end test — video → existing CV/analysis pipeline → database persistence → API retrieval — using a synthetic/fixture video (acceptable for automated tests) but exercising the real pipeline and real persistence, not mocks standing in for either.

## Regression Requirement (mandatory)

Phase 10 is not complete unless Phase 1–9 behavior remains intact. Run and paste actual output for: the full backend regression suite, Phase 4 ingestion tests, Phase 5 detector tests, Phase 6 tracker tests, Phase 7 counter tests, Phase 8 analytics tests, Phase 9 lane-analysis tests, all existing verification scripts where practical, frontend typecheck, frontend production build, and frontend integration tests. No previously verified capability may regress.

## Real Verification

Create a real verification script — `scripts/verify_phase10_database.py` or whatever name matches repository convention. It must prove, with actual observed values (never fabricated):

1. PostgreSQL connection works.
2. Current migrations apply.
3. A real uploaded/fixture video is processed through the existing pipeline.
4. An analysis run is persisted.
5. Real analytics results are persisted.
6. Lane results are persisted, if included in this phase's scope.
7. Counting results/events are persisted, if included.
8. The database actually contains the expected records (query them back, don't just trust the write call succeeded).
9. API retrieval returns the persisted results correctly.
10. Data survives reopening/recreating the database session (proving it's genuinely persisted, not just cached in-process).
11. No fake production data was used anywhere in the run.
12. No internal filesystem path or secret is leaked in any output.
13. Persistence overhead is measured or at least reasonably reported.

Evidence format (illustrative — use real values):

```
Database: PostgreSQL connected, migration revision: <actual>
Video: video_id=<actual UUID>, duration=<actual>, frames=<actual>
Analysis Run: run_id=<actual UUID>, type=<actual>, status=completed
Traffic Analytics: total_volume=<actual>, observation_duration=<actual>, extrapolated=<actual>
Lane Results: lane_id=<actual>, unique_vehicles=<actual>, density=<actual>
Database Verification: persisted_rows=<actual>, api_retrieval=PASS, session_reload=PASS
```

If real end-to-end persistence cannot actually be demonstrated in your environment, report `BLOCKED` or `NOT IMPLEMENTED` — never `VERIFIED`.

## Documentation

Update `PROJECT_STATUS.md` and `ARCHITECTURE.md` §8 (confirm the actually-implemented schema against what was documented back in Phase 1, and correct any drift — this is the phase where §8 stops being aspirational). Update `README.md` if warranted. Document: the final schema and relationships, the analysis-run concept and its lifecycle, migration history, the API endpoints added, the verification evidence, performance observations, and known limitations.

## Git

Inspect `git status` and migration history before changing anything. After genuine implementation and verification: review changed files, avoid unrelated changes, run the complete test suite, inspect the diff, and make one focused commit (or a small number of logically separate ones — e.g., migration + models as one, API endpoints as another, if that's cleaner). Suggested: `feat: implement database integration and persistence`.

## Completion Report

Require:

1. Overall classification: `VERIFIED` / `PARTIALLY VERIFIED` / `NOT IMPLEMENTED` / `BLOCKED`
2. Implementation summary
3. Final schema (tables, columns, relationships) as actually implemented
4. Files created/modified
5. Migrations created, and their upgrade/downgrade verification results
6. API endpoints added
7. Analysis-run design and lifecycle
8. What was persisted for analytics/lane/counting results, and what (if anything) was deliberately not persisted, and why
9. Frontend changes (History page or otherwise)
10. Security controls verified
11. Performance observations (persistence overhead)
12. Unit/integration test results (pasted, not summarized)
13. Full Phase 1–9 regression results (pasted)
14. Real end-to-end verification output (from the verification script, pasted, with real values)
15. Known issues
16. Limitations
17. Anything intentionally deferred, and why
18. Exact recommended next phase

`VERIFIED` requires genuine, queryable persistence demonstrated end-to-end, passing tests, and passing full regression — not a migration file that merely exists.

## Scope Boundary

Do not implement anything from the Explicit Exclusions list above, and do not begin Phase 11 or any later phase under this prompt.

## Final Scope

Phase 10 is exactly: **connect the existing, already-verified CV pipeline's output to real, queryable PostgreSQL persistence, exposed through the existing API conventions.** Nothing about the CV/ML pipeline itself changes.
