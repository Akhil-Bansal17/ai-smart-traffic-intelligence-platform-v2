# Phase 17 — Analysis Job Orchestration & Real-Time Processing Foundation

## Role

You are Antigravity, the implementation agent for the AI Smart Traffic Intelligence Platform. Inspect first, implement incrementally, preserve existing behavior, run tests continuously, use the actual repository as source of truth, verify real behavior, fix root causes, avoid fake verification, avoid unrelated refactoring, and do not begin Phase 18 work.

Workflow: READ → INSPECT → UNDERSTAND → PLAN → IMPLEMENT → TEST → DEBUG → ROOT-CAUSE FIX → RE-TEST → VERIFY → FULL REGRESSION → SECURITY REVIEW → PERFORMANCE REVIEW → DOCUMENT → GIT REVIEW → REPORT.

## Root-Cause-First Rule (mandatory)

If a failure is discovered: (1) reproduce it, (2) identify the root cause, (3) trace the affected architecture, (4) fix the root cause, (5) add regression coverage, (6) rerun the affected verification, (7) rerun the full regression suite. Do not patch symptoms merely to make tests pass. If the existing architecture makes a requirement unsafe or impossible, stop and report the blocker instead of fabricating success.

## Required Reading (repository-first — do not design against assumptions)

Inspect before designing anything:

- `backend/app/`, `backend/tests/`, `backend/alembic/`, `frontend/src/`
- Existing video-processing services, analysis persistence services, video models, analysis models, routers, schemas
- Configuration/settings, health/readiness, logging
- Existing verification scripts, `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md`
- Existing frontend API client, Video Analysis page, History page, Dashboard
- Existing phase prompts (Phases 1–16) for established conventions

Trace the current execution path end to end: upload → video record → detection → tracking → counting → lane analysis → metrics → persistence → downstream analytics. Identify exactly where processing currently occurs synchronously within the request lifecycle. Do not proceed to implementation until this is understood from the real code.

## Current Project State

Phases 1–16 are complete. Phase 16 (VERIFIED/CLOSED) established production configuration validation, safe error envelopes, bounded API pagination, readiness/liveness checks, upload/resource limits, security hardening, provenance enforcement, frontend resilience, performance checks, regression verification, and repository hygiene. Phase 15's congestion-duration semantics are verified (15.00s → no event, 19.99s → no event, 20.00s → event, 21.12s → event) — do not reopen Phase 15 unless repository inspection proves an actual regression.

Existing principles that remain in force: no fake AI, no fabricated real-world metrics, no fake production claims, simulations remain explicitly labeled as simulations, real-world provenance must remain trustworthy, synthetic/test data must never silently become real-world data, Phase 11's real-forecasting limitation stays honestly represented (do not fabricate missing forecasting samples), no physical traffic-signal control, lane analysis remains configured-polygon based (not autonomous detection), existing working algorithms are not replaced unnecessarily, architecture stays modular/swappable, existing API contracts are preserved unless a migration is genuinely required, backward compatibility is preserved wherever practical, and existing tests must continue passing.

## Objective

Transform the current request-bound video-analysis pipeline into a controlled, long-running **Analysis Job** architecture. The platform must be able to: create an analysis job, track its lifecycle, process long-running video without holding an HTTP request open, report progress and current state, allow safe cancellation, handle failures cleanly, prevent duplicate uncontrolled processing, preserve existing persistence and provenance, expose job status to the frontend, let the frontend monitor progress, and process deterministically and repeatably.

This is NOT a distributed microservices rewrite, NOT Kubernetes, and NOT Celery/RabbitMQ unless repository inspection proves existing infrastructure already supports it without unnecessary complexity. Prefer a robust application-level background job mechanism appropriate for the current single-node deployment.

## Architectural Principle — Analysis Job State Machine

Introduce a first-class Analysis Job abstraction representing a long-running analysis operation against a video/source. Use the smallest correct lifecycle actually required by the repository — do not add states that won't be implemented:

- Core: `QUEUED → RUNNING → COMPLETED`
- Terminal alternatives: `FAILED`, `CANCELLED`
- Only if genuinely justified: `PAUSED`

The state machine must be explicit and validated; illegal transitions must be rejected with a clear, safe API error. Valid terminal-state rules: `COMPLETED`, `FAILED`, and `CANCELLED` cannot be cancelled or re-transitioned.

## Analysis Job Data Model

Design a persistent `AnalysisJob` model matching existing database conventions, containing only fields that are genuinely useful — determine the final schema from repository inspection, not by copying this list wholesale. Candidate fields: id, video_id, status, progress percentage, frames_processed, total_frames (when available), processing_fps, started_at, completed_at, created_at, updated_at, error_code, error_message, cancellation_requested, worker/processor metadata (only if genuinely useful), provenance information (if needed). The job must remain associated with the existing Video and analysis-persistence records — do not duplicate existing traffic data.

## Job Execution Architecture

Accept a job request quickly, persist the job, return a job identifier, and process outside the request lifecycle. Update progress safely, persist intermediate/terminal state, handle exceptions, support cancellation, avoid orphaned jobs where practical. Prefer a simple, reliable in-process worker/background execution mechanism if sufficient for this deployment — do not introduce a heavyweight distributed queue for appearance, and do not claim an in-process worker is horizontally scalable. Documentation must clearly state the actual deployment model.

## Concurrency Control

Prevent uncontrolled concurrent processing via a configuration-driven limit (e.g. `MAX_CONCURRENT_ANALYSIS_JOBS`). Implementation must: enforce the configured limit, safely queue additional jobs, avoid race conditions, avoid duplicate execution, and behave predictably under simultaneous requests. Do not implement concurrency control with unsafe global state without understanding the actual application lifecycle (e.g. multiple workers/reload behavior).

## API Requirements

**Create job** — `POST /api/v1/analysis/jobs`: accepts `video_id` and only already-supported analysis configuration; returns `job_id`, `status`, created timestamp; must not wait for the full analysis to finish. Validates: video exists and is usable, provenance rules preserved, configuration valid, duplicate-active-job rule respected, concurrency/resource limits respected. Do not invent unsupported configuration parameters.

**Job status** — `GET /api/v1/analysis/jobs/{job_id}`: returns job ID, video ID, current status, progress, frames processed, total frames if known, elapsed time if useful, timestamps, error information when failed, cancellation state. No internal stack traces, secrets, or filesystem internals exposed.

**Job listing** — `GET /api/v1/analysis/jobs`: bounded pagination consistent with Phase 16; filters only where genuinely useful and correctly supportable (e.g. status, video_id); no unbounded database queries.

**Cancellation** — `POST /api/v1/analysis/jobs/{job_id}/cancel`: cooperative cancellation only — no unsafe force-kill of threads/processes. Behavior: `QUEUED → CANCELLED` immediately; `RUNNING →` cancellation requested → processor exits safely → `CANCELLED`; `COMPLETED`/`FAILED`/`CANCELLED` → cannot cancel, return a clear API error for the invalid operation.

## Progress Tracking

Where total frame count is known: `progress = frames_processed / total_frames`. Where unavailable/unreliable: use an honest indeterminate state or null — never fabricate a percentage. Choose an update strategy that avoids excessive database writes (e.g. periodic frame interval, periodic time interval, plus a terminal update) — determine the right cadence from the actual pipeline after inspection.

## Processing Pipeline Integration

The job executor must call the existing services — video ingestion/source → detection → tracking → counting → lane analysis → metrics → persistence — coordinating them, not duplicating them. Do NOT duplicate the YOLO detector, ByteTrack tracker, line-crossing counter, lane assignment engine, traffic metrics engine, or analysis persistence service. The job orchestration layer is a coordination layer only.

## Idempotency

Repeated requests must not create uncontrolled duplicate analysis. If the same video already has a `QUEUED` or `RUNNING` job, the create-job API may reject creation with a deterministic conflict response. Completed historical jobs remain available; do not prevent legitimate re-analysis if the existing architecture supports it. Determine the correct policy from actual repository behavior.

## Failure Handling

A failed job must: transition to `FAILED`, preserve a safe error code and safe user-facing error message, release worker resources, not leave the system permanently busy, and not corrupt existing database state. Log unexpected exceptions with structured context; never expose raw exception traces through API responses. Determine — from the actual persistence architecture — whether partial analysis data can be rolled back or must be explicitly marked as partial; do not invent transactional guarantees that don't exist.

## Database Consistency

Use existing SQLAlchemy/Alembic conventions. Create the necessary migration and verify upgrade, downgrade, and re-upgrade on a clean database. Existing migrations remain untouched unless absolutely necessary and explicitly justified. Never manually modify schemas outside migrations.

## Application Lifecycle & Job Recovery

The background worker must interact correctly with FastAPI startup, shutdown, reload/development mode, and the test environment. Avoid duplicate workers during development reload. Shutdown should stop accepting new work and allow active jobs to exit safely within a reasonable mechanism. Do not claim guaranteed job recovery after process crashes unless actually implemented — document what happens to `RUNNING` jobs after process termination.

At application startup, inspect persisted jobs and determine how stale `RUNNING` jobs are handled — a safe default is `RUNNING → FAILED` with a recovery-related error, or another explicitly justified state. Do NOT automatically mark a stale job `COMPLETED`. Do NOT resume from an arbitrary frame unless resumability is genuinely implemented. Behavior must be deterministic and documented.

## Real-Time Status Updates (Frontend)

Polling is acceptable for this phase. Do NOT introduce WebSockets/SSE unless repository inspection shows a strong existing reason to. Frontend must be able to: start analysis, receive a job ID, navigate to job monitoring, poll status, display progress/running/completion/failure/cancellation. Polling must have a reasonable interval, timeout behavior, cleanup on unmount, and no runaway requests.

## Frontend Job Monitoring

Extend the existing Video Analysis workflow rather than creating a disconnected interface. The user should be able to: select an uploaded video, start analysis, immediately receive job status, see progress and frames-processed where available, see current state, cancel when supported, receive completion/failure state, and navigate to available results. Reuse existing UI components and design language — no new visual system. Handle loading, empty, error, success, cancelled, running, and completed states explicitly.

## History Integration

Integrate jobs into existing History functionality where appropriate — users should see which video was analyzed, when, and current/terminal status. Do not duplicate historical traffic metrics; keep job history separate from analytical result history while linking them appropriately.

## Dashboard Safety

The dashboard must remain strictly read-only. Dashboard requests must never create jobs, start CV processing, run YOLO/tracking, trigger simulations, or retrain prediction models. Verify no side effects were accidentally introduced into dashboard aggregation.

## Resource Protection

Build on Phase 16 protections. Consider: maximum concurrent jobs, processing FPS, video duration, memory usage, database update frequency, cancellation responsiveness, queue size. Configuration must be validated; do not invent arbitrary limits without explaining why; never bypass existing upload limits.

## Security

Audit the new job APIs for: invalid IDs, nonexistent videos, unauthorized operations (if/when auth exists), malformed payloads, repeated cancellation, invalid state transitions, path traversal through any job-related file handling, unsafe error messages, excessive pagination, resource exhaustion. Do not add fake authentication — if auth/RBAC isn't currently implemented, document that as an existing limitation rather than claiming Phase 17 solved it.

## Provenance

Every analysis job must preserve the existing provenance boundary. A job processing real verified data must remain real verified data; synthetic pipeline data remains synthetic pipeline data; synthetic fixture data remains synthetic fixture data. Unverified real-world claims must not become verified merely by passing through the job system. The job layer must not modify provenance semantics.

## Observability

Add structured logging around job creation, start, completion, failure, cancellation, stale-job recovery, and concurrency rejection/queueing, including `job_id`, `video_id`, and `status`. No sensitive data logged; avoid excessive per-frame logs; follow existing logging conventions.

## Performance

Measure: job creation latency, job status latency, queue behavior, cancellation response time, progress-update overhead. Do not claim the CV pipeline itself became faster unless measured — the actual goal is that API responsiveness improves because long-running processing is decoupled from the HTTP request. Demonstrate this with real measurements.

## Testing Requirements

At minimum:

**A. Job creation** — valid video; missing video; invalid payload; duplicate active job.
**B. State machine** — valid transitions; invalid transitions rejected.
**C. Background execution** — job starts; job completes; job fails.
**D. Progress** — known frame count; unknown frame count (no fabricated progress).
**E. Cancellation** — queued cancellation; running cancellation; completed-job cancellation rejected; repeated cancellation rejected.
**F. Concurrency** — configured limit respected; additional jobs queue safely; race-condition coverage.
**G. Recovery** — stale `RUNNING` job handling at startup.
**H. Database** — migration upgrade; migration downgrade; persistence correctness.
**I. API contracts** — safe errors; bounded pagination; correct status codes.
**J. Provenance** — provenance unchanged through job execution.
**K. Regression** — all previous backend tests pass.

## Testing Realism

Do not make fake "production" claims. Fixtures/mocks are acceptable where appropriate, but clearly distinguish unit tests, integration tests, real-pipeline verification, and real-world-data verification. Do not claim a background job processed real-world traffic unless actual real-world input was used.

## Verification Script

Create `scripts/verify_phase17_*.py` following existing verification-script conventions, verifying real behavior for: database schema, migration, job creation, job persistence, job state transitions, background execution, progress, cancellation, failure handling, stale-job recovery, concurrency limit, API contracts, provenance preservation, frontend/API contract compatibility, and regression. Report PASS/FAIL honestly — no placeholder checks, no hardcoded fake results.

## Frontend Verification

Run TypeScript typecheck, production build, relevant frontend tests, job-monitoring behavior, polling cleanup, and loading/error states. No TypeScript errors; no unnecessary new build warnings.

## Documentation

Update `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md` as appropriate, documenting: the Analysis Job architecture, lifecycle, API endpoints, concurrency behavior, cancellation, failure handling, startup recovery, deployment limitations, the single-node/in-process worker limitation (if applicable), and the future path to distributed workers. Do not claim horizontal scalability unless implemented.

## Strict Scope Exclusions

Phase 17 must NOT: reopen Phase 11 forecasting or fabricate forecasting data; add new ML models; replace YOLO or ByteTrack; redesign lane detection; add physical signal control; convert simulations into real-world control; introduce Kubernetes; introduce microservices; introduce distributed queues unnecessarily; add authentication/RBAC merely for appearance; redesign the frontend; rewrite existing CV algorithms; start Phase 18; implement unrelated features.

## Definition of Done

Phase 17 is VERIFIED only when: `AnalysisJob` model exists and persists correctly; migration works upgrade/downgrade; job creation returns quickly; long-running processing executes outside the request lifecycle; the state machine is enforced; progress is real (never fabricated); cancellation works safely; failures are handled safely; duplicate jobs are controlled; concurrency is bounded; stale jobs are handled deterministically; provenance remains intact; API contracts work; the frontend can monitor jobs and cancel where supported; the dashboard remains read-only; resource limits remain enforced; structured logging works; the dedicated verification script passes; backend tests pass; frontend typecheck passes; frontend production build passes; previous phase verification scripts still pass; documentation is updated; the Git working tree is clean; and no unrelated scope was introduced.

If any required gate fails, the status MUST be BLOCKED — do not label the phase VERIFIED simply because most work succeeded.

## Required Completion Report

1. STATUS: VERIFIED / BLOCKED
2. Summary
3. Files changed
4. Architecture changes
5. Database/migration changes
6. API changes
7. Frontend changes
8. Job lifecycle behavior
9. Concurrency behavior
10. Cancellation behavior
11. Recovery behavior
12. Security review
13. Provenance verification
14. Test results
15. Verification-script results
16. Frontend typecheck/build results
17. Full regression results
18. Performance observations
19. Known limitations
20. Git commit hash
21. Git push result
22. Working-tree status
