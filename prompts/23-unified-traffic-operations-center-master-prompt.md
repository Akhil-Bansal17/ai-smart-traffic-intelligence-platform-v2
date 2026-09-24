# PHASE 23 — Unified Traffic Operations Center & Real-Time Incident Response

> Repository: `https://github.com/Akhil-Bansal17/ai-smart-traffic-intelligence-platform-v2.git`, branch `main`. Before making any implementation decision, inspect the entire actual repository. Never assume a file, endpoint, class, component, database table, service, or architecture exists merely because this prompt mentions it. **If the repository differs from this prompt, repository reality wins.**

## Role

You are the implementation, testing, verification, and Git agent building a unified operational interface over the existing, already-verified platform. This phase is an orchestration/presentation layer — it must not become a second analytics engine, and it must not duplicate any existing subsystem's logic.

## Critical Workflow Rule (before writing any code)

Inspect, in order: the entire repository; current branch and Git status; the latest commit; `PROJECT_STATUS.md`; `ARCHITECTURE.md`; relevant phase documentation; backend architecture; frontend architecture; database models and migrations; existing APIs; the existing anomaly/incident system; the existing insight/decision system; live monitoring; historical analytics; reporting; existing dashboard components; tests and verification scripts; configuration and security controls; Docker/deployment configuration. **Do not begin coding until this assessment is complete.** Do not blindly rebuild existing functionality — reuse existing services, models, APIs, components, schemas, and infrastructure wherever appropriate; if something genuinely needs to change, determine why first, and avoid duplicate implementations.

## Context — Verified Baseline (per the planning team; confirm all of it yourself)

Phase 10: persistent `AnalysisSession`/`TrafficMetricsRecord`/`LaneResultRecord`/`CrossingEventRecord`. **Phase 11:** forecasting architecture exists but real observations remain below the training threshold — **do not reopen it, do not fabricate real-world forecasts, preserve its existing provenance/availability rules exactly.** Phase 12/13: signal-optimization and emergency-corridor simulations — simulation/decision-support only, no physical control or dispatch. Phase 14: read-only system dashboard. **Phase 15:** anomaly/incident detection (congestion buildup, flow drop, lane imbalance, density spike) with a full lifecycle (start/continuation/recovery/end/repeat, idempotent reruns, provenance inheritance, operator status open/acknowledged/resolved) — **do not build a second anomaly engine; Phase 23 consumes this system.** Phase 16: production reliability/security hardening — preserve existing controls. Phase 17: `AnalysisJob` orchestration (queued/running/completed/failed/cancelled, progress, cancellation, stale-job handling, bounded concurrency) — don't duplicate it. **Phase 18:** the deterministic insight engine with evidence packages, observed/inferred distinction, severity, advisory recommendations, provenance, simulation labeling — **do not build a second insight engine; consume this one.** Phase 19: PDF/CSV reporting with deterministic assembly and SHA-256 hashing — reuse it. Phase 20: production packaging — don't reopen its documented Docker CVE work without an actual new compatibility issue. **Phase 21:** live monitoring and camera sources (RTSP/HTTP/MJPEG/USB/V4L2/deterministic test fixture, bounded frame queue, live analysis worker, telemetry, annotated preview, credential sanitization) — this is Phase 23's primary real-time foundation. **Phase 22:** historical traffic intelligence (summaries, time-series buckets, vehicle composition, directional/lane analysis, peak-period analysis, anomaly/insight history, source comparison, period-over-period comparison, observed-vs-extrapolated distinction, bounded queries — max 90-day range, 1000 buckets, 10000 records). Historical data stays deterministic: no interpolation of missing periods, no fake curves, no invented observations.

## Workflow
READ → INSPECT → PLAN → IMPLEMENT → TEST → DEBUG → VERIFY
→ REGRESSION → SECURITY REVIEW → DOCUMENT → GIT REVIEW → REPORT

Root-cause-first on any failure: reproduce, capture the exact error, identify the actual root cause, trace the affected dependency, apply the minimal correct fix, add a regression test, re-run the failing test, re-run relevant phase regressions, verify actual behavior, document any real limitation. Never weaken an assertion to pass, never skip a failing test, never fabricate verification output, never reopen a closed phase without a concrete dependency forcing it.

## Objective

Unify **live monitoring + active incidents + traffic insights + historical context + camera health + an event timeline + reporting/drill-down** into one operational view answering: what's happening right now, which sources/cameras are active and healthy, which incidents are currently active, what changed recently, what evidence supports an incident, what historical context applies, what insights are available, which source/session produced an observation, and what existing decision-support tools exist. The Operations Center orchestrates existing systems through clean service/API boundaries — it never becomes its own analytics engine:
             Unified Traffic Operations Center (Phase 23)
                                │
      ┌─────────────────────────┼─────────────────────────┐
      ▼                         ▼                         ▼
      Live Monitoring (21) Incident System (15) Historical Analytics (22)
│ │ │
└──────────────┬──────────┴──────────────┬─────────┘
▼ ▼
Decision Insights (18) Reporting (19)
│
▼
Existing Simulations (12/13)

## Functional Scope

**Operations Center page** — a dedicated route (e.g. `/operations`, or whatever matches existing conventions), complementing rather than replacing the Dashboard, designed for frequent monitoring, desktop- and mobile-responsive, prioritizing information hierarchy over decoration.

**Live camera overview** — for each active source: name, source type, connection status, active/inactive, last-frame time, FPS, processed-frame count, analysis status, current traffic metrics/vehicle count, current congestion/anomaly state — all from Phase 21 telemetry, reusing it rather than duplicating connection logic, and **never exposing RTSP/HTTP credentials.**

**Camera health** — states limited to what actual telemetry can support (e.g. ONLINE/OFFLINE/CONNECTING/DEGRADED/UNKNOWN) — use `UNKNOWN` rather than inventing a metric the backend can't reliably determine.

**Active incident panel** — type, severity, camera/source, start time, current duration, latest observed value, baseline/comparison if already available, lifecycle state, operator status, provenance, evidence summary — all backend-authoritative; **never calculate or recreate incident logic in the frontend.**

**Incident detail** — summary, source, camera, session, timestamps, lifecycle, operator status, traffic metrics, lane information, the anomaly rule, evidence, provenance, historical context, related insights, available reports, with drill-down links where possible — exposing existing evidence, never inventing new evidence.

**Incident acknowledgement/operator status** — reuse Phase 15's mutation APIs if they exist; only expose acknowledge/resolve controls if existing backend permissions and lifecycle rules genuinely support them. Never invent authorization, bypass backend validation, or allow an arbitrary status transition from the frontend — document the limitation instead of building unsafe behavior if the backend doesn't support a desired action.

**Recent event timeline** — aggregated from authoritative existing data only (incident started/continued/recovered/resolved, camera connected/disconnected, analysis started/completed/failed, insight generated, report generated). Never fabricate an event timestamp, and never imply historical events exist for a type with no actual persistence. A lightweight, deterministic aggregation layer over existing records is fine; avoid introducing full event-sourcing unless inspection proves it's actually necessary.

**Current traffic snapshot** — active vehicles, flow, composition, directional balance, lane occupancy/density, congestion state, active anomalies, observation duration — via existing Phase 21/15/18 capabilities, with every value explicitly tagged OBSERVED / EXTRAPOLATED / UNAVAILABLE. Never let a short observation look like a long-term measured statistic.

**Historical context** — for a selected camera/source/incident, pull recent trend, comparable prior periods, historical peaks, historical anomaly frequency, historical composition/direction from Phase 22. Stays strictly historical — no "expected"/"will increase"/"predicted" language unless it genuinely comes from Phase 11's prediction system and is explicitly marked as such; given Phase 11's current data limitation, forecasting should normally show as unavailable unless the backend itself says otherwise.

**Insight panel** — reuse Phase 18's insights, severity, evidence, explanation, and recommendations exactly as they exist; recommendations stay advisory, never become automatic commands; no LLM dependency unless Phase 18's own architecture already requires one.

**Provenance** — every operational surface distinguishes REAL DATA / MIXED / SYNTHETIC-TEST-FIXTURE / UNKNOWN / UNAVAILABLE using the existing provenance system (no parallel implementation). Synthetic/test-fixture data never silently appears as real; when intentionally shown for dev/testing, it carries an obvious label/warning.

**Source filtering** — by whatever dimensions the backend can cleanly support (camera, source type, session type, provenance, active/inactive, incident status, severity) — implement only what's cleanly supportable; avoid expensive unbounded filtering.

**Quick drill-downs** — navigation to Live Monitoring, Historical Analytics, Incident Detail, Traffic Analytics, Reports, Signal Optimization Simulation, Emergency Corridor Simulation, and the Prediction page — links, never duplicated page logic.

## Backend

Inspect existing backend patterns first. If a dedicated aggregation service makes sense (e.g. `OperationsCenterService`, named per actual repository convention), create one that aggregates existing authoritative data — system status, camera status, current traffic snapshot, active incidents, recent events, current insights, historical-context availability, report availability, provenance summary — designed to fit the existing architecture, not copied verbatim from this prompt's example.

## API

Determine the design after inspecting existing APIs — a plausible shape is `GET /api/v1/operations/overview` plus supporting endpoints (`/cameras`, `/incidents`, `/events`, `/insights`, `/context/{source_id}`) — these are examples, not a mandate; prefer one safely-aggregated endpoint over unnecessary fragmentation. No N+1 patterns, bounded queries throughout, reuse existing schemas where possible.

## Performance

The Operations Center will be polled frequently: no unbounded queries, no full historical-table scans per refresh, no CV execution or ML training or simulation execution or report generation or video reprocessing triggered by page load, no blocking long-running work inside request handlers, appropriate indexes, bounded result counts, pagination where needed, efficient aggregation. If polling, use an interval consistent with Phase 21's precedent and prefer one coordinated refresh over many independent polling loops. Handle timeout, abort, offline backend, partial data, and empty/loading/error states.

## Real-Time Behavior

Do not introduce WebSockets unless inspection shows they're justified and compatible with the existing architecture — HTTP polling is acceptable, and reuse SSE/WebSockets only if they already exist. Never claim "real-time" for data refreshed every few seconds — show "Last updated: [timestamp]" instead.

## Frontend

Use the existing React/TypeScript architecture, design system, cards/tables/badges/alerts/charts, loading/error states, API client, routing, theme, and responsive layout — no second UI framework, no new state-management system if existing patterns suffice. Desktop may use multiple panels; mobile must stack logically with critical information visible without excessive horizontal scrolling. A reasonable layout: top bar (status, last-updated, active sources/incidents counts) → camera/system status → active incidents → current traffic → traffic insights → event timeline → historical context → quick actions — adapt this conceptual structure to the actual existing design system rather than copying it literally.

## Mobile

Prioritize, in order: active incidents, camera status, current traffic, important insights, event timeline, historical context, secondary navigation. Use cards or responsive tables rather than shrinking dense desktop tables.

## Security

Preserve all existing controls — review authentication/authorization boundaries if present, input/query-parameter validation, source identifiers, camera credentials, error messages, sensitive configuration, logs, path handling, SQL-injection resistance, resource limits. Never expose RTSP credentials, passwords, API keys, database credentials, or secrets; ensure error responses don't leak internals. If auth/RBAC doesn't currently exist, do not invent a fake security layer — document the limitation honestly.

## Database

Reuse existing tables for cameras, incidents, anomalies, insights, sessions, traffic metrics, and reports — no duplicate representations. Migrate only if genuinely necessary; add narrowly targeted indexes only after inspecting actual query patterns (no speculative indexing). Every migration upgrades and downgrades successfully, following existing conventions.

## Data Provenance (critical)

Never blur REAL / MIXED / SYNTHETIC / TEST-FIXTURE data — use existing provenance metadata exclusively. If a live test fixture is running, make that obvious in the UI. The system must function correctly using test fixtures when no real camera is available, but must never claim a fixture represents a real traffic camera.

## Simulation Boundary

Phase 12/13 remain simulations. The Operations Center may link to or summarize them ("Signal Optimization Simulation Available") but must never imply physical signal control, real emergency dispatch, real actuation, or guaranteed real-world travel-time savings — simulation outputs stay clearly labeled.

## Forecasting Boundary

Phase 11 stays untouched — no threshold change, no fabricated training data, no training on fixture data as if real, no fake forecast values, no silent substitution. If forecasting is unavailable, show the actual backend availability response (e.g. "Forecast unavailable — insufficient verified real observations").

## No Fake Data (absolute)

No hard-coded fake vehicle counts, incidents, camera statuses, traffic flow, historical trends, prediction values, performance metrics, or timestamps. Test fixtures only where the existing architecture already supports them, always clearly labeled.

## Error Handling

Gracefully handle: backend offline, database unavailable, no cameras, no active incidents, no historical data, insufficient data, camera disconnected, stale telemetry, partial API failures, malformed responses, timeout, cancellation. One unavailable optional section must never fail the entire page — use partial-data rendering.

## Observability

Structured logging for operations-overview request failures, aggregation failures, and important state transitions not already logged — never logging passwords, camera credentials, secrets, or tokens. Use existing logging conventions.

## Testing

**Backend:** operations overview; active-camera aggregation; camera health; active-incident aggregation; incident filtering; event timeline; insight aggregation; provenance; synthetic-data labeling; historical-context integration; empty data; partial data; backend error handling; bounded queries; security/sanitization; operator-status integration; deterministic response behavior.

**Frontend:** route, loading, empty, error, incident display, camera display, provenance warning, responsive behavior where test infrastructure supports it. Don't inflate test counts artificially.

## Verification Script

`scripts/verify_phase23_operations_center.py`, checking: operations-service import; configuration; API registration; aggregation correctness; active-camera behavior; active-incident behavior; provenance handling; historical integration; simulation labeling; the forecasting boundary; the no-fake-data invariant; security/sanitization; bounded-query behavior; frontend route/component existence; frontend build; relevant regression tests. Use existing verification-script conventions. Never make it pass by mocking away the functionality it's supposed to verify.

## Regression Testing

Run, at minimum, the verification suites for Phases 15, 16, 17, 18, 19, 21, and 22, plus the full backend test suite, frontend typecheck, and frontend production build. Do not declare success if an important test is skipped without documenting exactly why.

## Docker / Deployment

Don't reopen Phase 20's Docker CVE cleanup unless Phase 23 introduces an actual compatibility issue. Confirm the new functionality imports correctly in-container, the API starts, the frontend builds, migrations apply, and existing health/readiness endpoints stay healthy. Avoid unnecessary new dependencies.

## Documentation

Update `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md`, and relevant phase docs. If this master prompt is stored in-repo, add it at `prompts/23-unified-traffic-operations-center-master-prompt.md`; create/update the Antigravity prompt file at `prompts/antigravity/23-unified-traffic-operations-center.md` per repository convention. Document what Phase 23 adds, its architecture, API, UI, data flow, provenance behavior, limitations, testing, verification, and known environment limitations — never claim untested functionality.

## Git Workflow

Repository `Akhil-Bansal17/ai-smart-traffic-intelligence-platform-v2`, branch `main`. Inspect the current remote and confirm it's correct; inspect the current branch; implement; test; run regressions; update documentation; inspect `git diff` and `git status`; create one meaningful commit (suggested: `feat(phase-23): add unified traffic operations center`, or the repository's actual convention if different); push to `origin/main`. Never push unrelated user changes, never overwrite unrelated work, never force-push, never create a new repository, never change the remote URL unless it's demonstrably wrong.

## Git Safety Check

Before committing, review `git status`, `git diff --stat`, and `git diff --name-only`, and commit only the intended Phase 23 changes — never `.env`, secrets, credentials, temporary files, `node_modules`, virtual environments, model caches, or other unintended large files. If automatic Git hooks/scripts already exist for this, inspect and reuse them rather than building a competing system.

## Resource Limits

Bound every Operations Center query — no unlimited incidents, events, historical rows, cameras, or insights retrievable by a user-controlled request. Review pagination and query limits explicitly.

## Architectural Quality Rule

Prefer: existing service → existing data → an operations aggregator → a typed API → the operations UI. Avoid: the frontend making many direct database-like requests, duplicating calculations, or duplicating business logic. The frontend is never the source of truth.

## Do Not Build a "God Service"

`OperationsCenterService` orchestrates — it must not become a replacement for anomaly detection, historical analytics, traffic analytics, insight generation, reporting, or live monitoring. If logic belongs to another service, call that service. If an existing service is missing one small read-only method this phase needs, extend it cleanly rather than duplicating its logic elsewhere.

## Strict Exclusions

Do not implement: new ML or forecasting models; autonomous traffic control; physical signal control or emergency dispatch; automatic emergency-vehicle routing; new CV algorithms, detector, tracker, or lane detector; a new anomaly engine, historical-analytics engine, or reporting engine; blockchain; a microservices or Kubernetes migration; a distributed tracing platform; an authentication rewrite; a large infrastructure rewrite; fake real-world data; or fabricated dashboard metrics. This phase is integration/operations only.

## Definition of Done

Complete only when: the repository was inspected first and existing architecture reused; the Operations Center, live camera info, camera health, active incidents, incident detail, existing operator-status semantics, an authoritative-data-derived event timeline, the current traffic snapshot, Phase 18 insights, and historical context are all integrated; provenance, synthetic/test-fixture labeling, and simulation labeling are all clearly displayed; the forecasting boundary is preserved; no fake operational data exists; no anomaly/historical-analytics/reporting engine was duplicated; security was reviewed and resource limits enforced; backend tests, frontend typecheck, and frontend production build all pass; the Phase 23 verification script passes; Phase 15/16/17/18/19/21/22 regressions all pass; Docker compatibility was checked; documentation is updated; the correct repository and branch were confirmed; a commit was created and `origin/main` synchronized; the working tree is clean.

## Final Completion Report

Require: Phase status; commit hash; repository/branch; files added/modified; backend architecture changes; API endpoints; database changes; frontend changes; Operations Center capabilities delivered; provenance behavior; security changes; tests executed and their results; verification-script result; regression results; frontend typecheck and build results; Docker result; Git push result; known limitations; environment-limited checks; explicit confirmation that no fake data was introduced; explicit confirmation that Phase 11's forecasting boundaries remain intact; explicit confirmation that Phase 12/13 remain simulations only; confirmation the working tree is clean. Never claim "production-ready" unless the actual verification supports that wording — use exact test counts and results throughout, never a summary claim.

## Final Instruction

Repository reality always wins. Inspect before modifying, reuse before creating, integrate before duplicating, measure before claiming, test before declaring success. Never fabricate data, never hide a failure, never weaken a test to get a green result, never reopen a closed phase without a concrete dependency forcing it. The finished system should feel like one coherent traffic operations platform, not a collection of disconnected features — while preserving the project's strict boundaries between real, observed, extrapolated, predictive, simulation, and test/fixture data at every layer.
