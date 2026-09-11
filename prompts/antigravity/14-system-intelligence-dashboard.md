# Phase 14 — System-Wide Traffic Intelligence & Decision-Support Dashboard

## Role

You are Antigravity, the implementation agent for the AI Smart Traffic Intelligence Platform. You implement, test, debug, verify, and report. You do not invent architecture decisions that contradict the existing verified system. If something in this prompt conflicts with what you find in the repository, the repository is the source of truth — stop and report the conflict rather than guessing.

Workflow for this phase, in order: READ → INSPECT → PLAN → IMPLEMENT → TEST → DEBUG → VERIFY → REGRESSION TEST → DOCUMENT → GIT REVIEW → REPORT. Do not skip steps. Do not start implementing before you have inspected the actual current repository state.

## Required Reading

Before writing any code:

1. Read `PROJECT_STATUS.md` (or equivalent status file) for the current verified state of Phases 1–13.
2. Read the backend service/router modules for: video ingestion (Phase 4), detection (5), tracking (6), counting (7), analytics (8), lane/density (9), database models (10), prediction (11), signal optimization (12), emergency corridor (13).
3. Read the existing frontend page components, shared layout, design tokens/theme, and API client to understand conventions already in use.
4. Read the database schema/models and any existing Alembic migrations to understand what is actually persisted today (not what was planned).
5. Read any existing provenance/data-honesty utilities (e.g. `source_type`, `provenance_verified`, `synthetic`/`simulation` flags) already implemented in Phase 10/11.

Do not proceed to PLAN until you can state, from the actual repo, which of the below already exist and which need to be built.

## Current Project State (verified baseline — confirm against repo, do not assume)

- Phases 1–10, 12, 13: VERIFIED.
- Phase 11 (Traffic Prediction): CLOSED / PARTIALLY VERIFIED. Only 10 verified real-world observation buckets exist; 20 are required before real-world forecasting is considered ready.- Do not hardcode the current 10/20 values into dashboard logic. Read the actual real-observation count and configured readiness threshold from the existing backend/data layer so the dashboard remains dynamically correct as the dataset changes. This limitation must remain visible in Phase 14, not hidden or worked around.
- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pydantic.
- Frontend: React, TypeScript, Vite, Tailwind, with existing pages for Dashboard, Video Analysis, Traffic Analytics, Predictions, Signal Optimization, Emergency Simulation, History, Settings, System Information.
- Data provenance categories already established: `real_database_metrics`, `synthetic_pipeline_metrics`, `simulation_configured`, `synthetic_fixture`. These must never be silently mixed.

## Objective

Build a system-wide Decision Dashboard that **integrates and summarizes** existing Phase 4–13 outputs into one coherent view. This phase is an aggregation and presentation layer over already-verified subsystems — it is not a new analytics, ML, or simulation engine.

## Existing Components to Reuse (do not rebuild)

- YOLO detector, ByteTrack-style tracker, counting logic (Phases 5–7)
- Traffic analytics computation (Phase 8)
- Lane/density polygon analysis (Phase 9)
- Persistence models: `AnalysisSession`, `TrafficMetricsRecord`, `LaneResultRecord`, `CrossingEventRecord` (Phase 10)
- Prediction pipeline and its current real-data limitation (Phase 11)
- Signal optimization engine and Webster-based calculations (Phase 12)
- Emergency corridor simulation engine (Phase 13)
- Existing React design system, layout shell, navigation, API client, and Tailwind theme

If any of these do not exist in the form described, use what actually exists in the repository and report the discrepancy — do not build a parallel version.

## Architecture

```
Existing Phase 4-13 REST APIs / DB tables
            ↓
  (optional) thin aggregation endpoint(s) — read-only, no new business logic
            ↓
   Dashboard data contract (typed schema, includes provenance per section)
            ↓
   React Dashboard page (composed of section widgets)
```

Aggregation, if implemented, must call into existing services/queries — it must not reimplement counting, analytics, prediction, optimization, or simulation logic.

## Functional Requirements

The dashboard must present the following sections, each independently loadable and independently capable of showing an empty/unavailable state:

1. **System Health & Status** — backend/API reachability, database connectivity, last successful video-processing run, current subsystem status per phase (available / degraded / unavailable). No fabricated uptime or fake "all systems operational" states — derive from real health checks.
2. **Traffic Overview** — most recent analysis session(s): volume, flow/min, flow/hour (respecting the existing extrapolation rule — hourly figures from <1hr observation windows must be marked extrapolated, never presented as measured).
3. **Vehicle Composition** — per-class distribution from real persisted counting data.
4. **Traffic Flow Metrics** — time-series view sourced from persisted `TrafficMetricsRecord` data, not recomputed.
5. **Lane / Density Intelligence** — per-lane occupancy and image-space density from Phase 9/10 data, explicitly labeled as image-space density, not physical vehicles/km².
6. **Prediction Availability** — show real-world forecasting as unavailable/insufficient given the 10/20 observation-bucket limitation. If synthetic/test predictions exist, label them clearly as synthetic and separate from any real-world claim. Do not hide this limitation and do not soften the wording to imply readiness.
7. **Signal Optimization Results** — most recent simulation results from Phase 12, explicitly labeled "Simulation / Decision Support — not connected to physical signals."
8. **Emergency Corridor Results** — most recent simulation results from Phase 13, explicitly labeled "Simulation / Decision Support — not a real dispatch or control system."
9. **Historical View** — list/browse of past `AnalysisSession` records with links into existing History page, not reimplemented.
10. **Data Provenance Panel** — for the currently displayed session/data, show which provenance category applies (`real_database_metrics` / `synthetic_pipeline_metrics` / `simulation_configured` / `synthetic_fixture` / unavailable) using existing provenance fields.

Every section must independently support these states, rendered distinctly (not just a spinner or blank box):
- **REAL DATA** — genuine persisted real-world-derived data
- **SIMULATION** — Phase 12/13 simulation output
- **PREDICTION** — Phase 11 output, further qualified as real-eligible or synthetic/insufficient
- **SYNTHETIC** — synthetic pipeline or fixture data
- **UNAVAILABLE** — no data, insufficient data, or subsystem unreachable

## Data / Provenance Requirements

- Every dashboard section must carry an explicit, visible provenance/state label sourced from real backend fields — never inferred, guessed, or defaulted to "real."
- Do not silently fall back to synthetic/simulated data and present it as real when real data is absent — the UNAVAILABLE state must be used instead.
- Do not fabricate values to fill empty charts. Empty/insufficient states must say so honestly (e.g. "Insufficient real-world observations: 10 of 20 required").
- Stale data (e.g. last session older than a defined threshold) must be flagged, not presented as current.
- Partial data (e.g. lane analysis present but prediction absent) must render the available parts and clearly mark the missing parts — not fail the whole dashboard.

## API Requirements

- Reuse existing GET endpoints wherever they already return what the dashboard needs.
- If a new aggregation endpoint is genuinely necessary (e.g. to avoid N+1 waterfalls from the frontend), it must:
  - be read-only
  - call existing service-layer functions/queries, not duplicate logic
  - return a typed Pydantic response schema including a provenance/state field per section
  - be documented with request/response examples
- Justify in the completion report why any new endpoint was necessary rather than composing existing ones client-side.

## Frontend Requirements

- Keep the dashboard modular. Implement reusable section/widget components and small data-fetching/formatting utilities rather than placing the entire dashboard in one monolithic component.
- A failure in one section must not prevent unrelated sections from rendering.
- Add a Dashboard page/route (or extend the existing Dashboard page) composed of section widgets matching Functional Requirements above.
- Reuse existing design tokens, layout shell, navigation, typography, and component patterns — do not introduce a new UI framework or a divergent visual style.
- Each section widget must handle loading, empty, partial, stale, and error states explicitly, with visible labeling of provenance/state.
- Provide a way to drill from a dashboard section into its full existing page (e.g. clicking Signal Optimization summary goes to the existing Signal Optimization page).

## Database Requirements

- No new persisted tables should be required for this phase if existing tables already carry the needed data.
- If a genuinely new table/column is required (e.g. a health-check log), it must go through a proper Alembic migration, be minimal, and be justified in the completion report.
- Do not modify or backfill historical migrations.

## Security

- No new authentication/authorization model unless one already exists in the repo — reuse existing conventions.
- Sanitize/validate any new endpoint inputs (query params, filters, date ranges).
- Do not expose internal error details, stack traces, or raw DB errors in API responses.
- Confirm no secrets, credentials, or `.env` values are introduced or logged.

## Performance

- Opening or refreshing the Dashboard must never automatically trigger video upload, YOLO inference, tracking, counting, lane analysis, prediction training, signal optimization, or emergency-corridor simulation. The Dashboard is a read/aggregation/presentation layer only.
- Dashboard initial load should not trigger heavy recomputation — read persisted/aggregated data, don't recompute analytics/tracking/detection on load.
- Avoid N+1 query patterns in any new aggregation endpoint; use joins/batched queries.
- Report actual load-time/query-time measurements — do not estimate or guess.

## Testing

- Unit tests for any new aggregation service/endpoint logic, including: all-real-data case, all-unavailable case, partial/mixed-provenance case, stale-data case, Phase-11-insufficient-data case.
- Frontend component tests for each section widget's loading/empty/partial/error states.
- Integration test hitting the dashboard endpoint(s) against a seeded test database covering both a "healthy full data" scenario and a "sparse/partial data" scenario.

## Verification Script

Provide/extend a verification script that:
- Starts backend against the test/dev database
- Hits the dashboard endpoint(s)
- Asserts each section's provenance/state field is present and correctly derived (not defaulted)
- Asserts the Phase 11 insufficient-data message is present when real observations < 20
- Prints pass/fail per check, not just "success"

## Regression

Run and report results for existing test suites covering Phases 1–13 (backend and frontend). Confirm no existing endpoint, page, or migration was broken. Any pre-existing failing tests unrelated to this phase must be reported as pre-existing, not silently ignored or fixed as a side effect.

## Documentation

- Update `PROJECT_STATUS.md`: mark Phase 14 status honestly (VERIFIED / PARTIALLY VERIFIED / BLOCKED), list what was built, what was reused, and any new endpoint(s).
- Add/update README section describing the dashboard and its provenance-labeling behavior.
- Document any new API endpoint (path, method, request/response schema, example).

## Git

- Focused commit(s) scoped to Phase 14 only.
- No `.env`, secrets, database files, generated runtime artifacts, or media uploads committed.
- Clean working tree at the end.
- Commit message references Phase 14 explicitly.

## Definition of Done

- All ten dashboard sections render using real existing data sources, with correct and honest provenance/state labeling.
- Phase 11's real-world prediction limitation (10/20 observations) is visibly and honestly represented, not hidden or worked around.
- Signal optimization and emergency corridor sections are explicitly labeled simulation/decision-support.
- No detector/tracker/counter/lane analyzer/predictor/optimizer/simulator was rebuilt.
- All new code has passing tests; full regression suite for Phases 1–13 passes (or failures are pre-existing and reported as such).
- Verification script passes with printed evidence, not a bare "success" claim.
- Documentation and `PROJECT_STATUS.md` updated.
- Git history is clean and focused.

## Completion Report

Report must include, with actual evidence (command output, screenshots, or logs — not claims):
- What was reused vs. newly built, and why
- Verification script output
- Regression test results (pass/fail counts, any pre-existing failures noted)
- Performance measurements (load time, query counts/time)
- Any provenance/data-honesty edge cases encountered and how they were handled
- Any deviation from this prompt and why
- Explicit statement of Phase 14 status: VERIFIED / PARTIALLY VERIFIED / BLOCKED, with justification

## Strict Scope Exclusions

- Do NOT build a new detector, tracker, counter, lane analyzer, prediction model, signal optimizer, or emergency simulator.
- Do NOT reopen or attempt to "fix" Phase 11's real-data shortfall (no fabricating, duplicating, or relabeling observations).
- Do NOT implement any physical control: no traffic light hardware control, IoT controller communication, V2X commands, ambulance/emergency dispatch, or police/fire dispatch integration.
- Do NOT introduce a new frontend framework, competing design system, or new auth model.
- Do NOT begin Phase 15 or any work beyond this dashboard's scope.
- Do NOT silently default any section to "real" when provenance is unknown or absent — default to UNAVAILABLE.

## Final Rules

Never fabricate KPIs, charts, traffic values, predictions, historical data, or test results. Never present simulation or synthetic output as real-world measured traffic. Never weaken existing data-provenance rules. If something cannot be verified, report PARTIALLY VERIFIED, BLOCKED, or FAILED — not "everything works." The repository is the source of truth; when this prompt and the actual repo state disagree, stop and report the conflict rather than guessing.
