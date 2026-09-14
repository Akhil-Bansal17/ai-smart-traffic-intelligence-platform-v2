# PHASE 18 — Intelligent Traffic Insights & Explainable Decision Intelligence

## ROLE

You are the implementation agent for the AI Smart Traffic Intelligence Platform. You inspect the real repository, make no assumptions, implement Phase 18 completely, test it, verify it, document it, commit it, and report results. You do not skip inspection. You do not fabricate results.

## REQUIRED READING (do this before writing any code)

Inspect and understand, in this order:
1. `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md`
2. `backend/app/` — models, schemas, services, routers, core config, logging
3. `backend/alembic/` — migration history and conventions
4. `backend/tests/` — existing test structure and fixtures
5. `frontend/src/` — dashboard, analytics, alerts pages and their data-fetch patterns
6. Specifically: `TrafficMetricsEngine`, `TrafficMetricsRecord`, `LaneResultRecord`, `CrossingEventRecord`, `AnalysisSession`, `AnalysisJob` (Phase 17), anomaly detection models/services (Phase 15), signal optimization simulation (Phase 12), emergency corridor simulation (Phase 13), prediction module (Phase 11, closed), provenance utilities, existing verification scripts under `scripts/`.

Trace the real data flow end-to-end before designing anything. The repository is the source of truth, not this prompt.

## CURRENT PROJECT STATE

Phases 1–10, 12, 13, 14, 15, 16, 17 are implemented and verified. Phase 11 (real-world traffic prediction) is CLOSED/PARTIALLY VERIFIED — only ~10 of 20 required verified real-world observation buckets exist. Do not reopen Phase 11 or fabricate forecasting data under any circumstance. The project enforces a strict provenance taxonomy (`real_database_metrics`, `real_world`, `synthetic_pipeline`, `synthetic_fixture`, `unknown`) that must never be silently upgraded or mixed. Phase 17 introduced the `AnalysisJob` state machine for long-running work; Phase 18 must not create a second job system.

## OBJECTIVE

Build a deterministic **Traffic Decision Intelligence layer** that sits above existing persisted analytical outputs and answers: what happened, how significant it is, why the system believes it, what response is recommended, what evidence supports that, and how reliable the evidence is. This is an interpretation layer over existing data — not a new ML model, not a new forecasting system, not an LLM-based explanation generator.

## EXISTING COMPONENTS TO REUSE (do not rebuild)

- YOLO detection, ByteTrack tracking, vehicle counting — untouched
- `TrafficMetricsEngine` and persisted metrics/lane/crossing records — read-only inputs
- Phase 15 anomaly detection — remains the detector; Phase 18 interprets its output, does not duplicate it
- Phase 12 signal optimization simulation and Phase 13 emergency corridor simulation — usable as evidence, must remain explicitly labeled as simulation, never presented as real-world outcomes
- Phase 17 `AnalysisJob` infrastructure — reuse if insight generation ever needs to be long-running; otherwise keep generation lightweight and synchronous
- Existing provenance utilities, safe error envelopes, logging conventions

## ARCHITECTURE

```
Persisted observations (metrics/lanes/crossings/anomalies/simulations)
        ↓ evidence aggregation
        ↓ insight detection (deterministic rules, centralized thresholds)
        ↓ severity assessment (INFO/LOW/MEDIUM/HIGH/CRITICAL, evidence-based)
        ↓ root-cause reasoning (explicit OBSERVED vs INFERRED separation)
        ↓ recommendation generation (deterministic mapping, advisory only)
        ↓ evidence package (structured, honest about unavailable data)
        ↓ structured explanation (WHAT / WHY / IMPACT / RECOMMENDATION / EVIDENCE / LIMITATIONS)
```

The engine must never modify source metrics, never fabricate a value, and must represent unavailable evidence as unavailable rather than omitting or guessing it. No LLM is used or needed for this phase.

## FUNCTIONAL REQUIREMENTS

- Insight categories: implement only those the repository's actual persisted data can support (candidates: CONGESTION, FLOW_DEGRADATION, LANE_IMBALANCE, DENSITY_SPIKE, QUEUE_BUILDUP, TRAFFIC_SURGE, UNDERUTILIZED_LANE, OPERATIONAL_RECOMMENDATION). Drop any category the data can't back.
- Root-cause reasoning must label every statement `Observed:` or `Inferred:` — never state an inference as fact.
- Recommendations map deterministically to measurable conditions and are advisory only. The system never claims to control signals or that a real-world improvement occurred unless it was actually observed. Simulation-derived evidence is phrased as "simulation indicates," never as an observed real-world result.
- Anomaly integration: Phase 18 interprets Phase 15 anomaly events into higher-level insights; it does not own or duplicate anomaly lifecycle state.
- Prediction integration: reference Phase 11 output only if valid verified data exists; otherwise explicitly state forecast evidence is unavailable due to insufficient verified observations. Never synthesize forecast evidence.
- Deduplication: repeated generation over the same analysis/session + insight type + observation window + affected lane/approach must not create uncontrolled duplicates, while genuine new recurrences remain distinguishable.
- Generation is deterministic: same evidence + same config → same result (excluding intentional timestamp-based identity).
- Generation must not trigger CV/tracking/detection/re-analysis — it consumes persisted data only.

## DATA REQUIREMENTS

Design the minimal persisted `TrafficInsight` schema the repository actually needs — do not implement every field listed here reflexively. Consider: insight id, session/job reference, type, category, severity, status, title, summary, observation window, evidence references, supporting metrics, contributing factors (observed/inferred separated), recommendation + rationale, provenance tier, created/updated timestamps. Avoid duplicating existing metric records — reference them, don't copy them. Lifecycle: NEW/ACTIVE/RECOVERED/DISMISSED only if justified by the architecture; keep it distinct from the Phase 15 anomaly lifecycle.

## API REQUIREMENTS

Implement only endpoints the architecture justifies, e.g.:
- `POST /api/v1/insights/generate` — lightweight, consumes persisted data only, never triggers heavy processing
- `GET /api/v1/insights` — bounded pagination; filters limited to what's actually useful (severity, category, status, provenance, session/job reference)
- `GET /api/v1/insights/{insight_id}`
- `GET /api/v1/insights/info`

## FRONTEND REQUIREMENTS

Add an "Intelligent Insights" experience integrated into the existing dashboard/analytics/alerts pages — do not redesign the frontend. Display title, category, severity, status, summary, evidence, contributing factors, recommendation, provenance, observation window, limitations, with expandable detail. Visually distinguish Observed / Inferred / Simulated / Unavailable. Add a concise read-only Insights widget to the dashboard (active high-severity insights, recent insights, category distribution, recommendation count) — dashboard load must never generate new insights.

## DATABASE REQUIREMENTS

Create the Alembic migration for the new insight table(s) following existing conventions. Verify upgrade → downgrade → upgrade again. Do not alter or break any existing migration or historical data.

## SECURITY

Validate all insight endpoint inputs (ids, filters, pagination, malformed requests, unsupported category/status/reference values). Never expose stack traces, filesystem paths, DB internals, or config. Use the existing safe error envelope.

## PERFORMANCE

Insight generation must not rerun YOLO, ByteTrack, video decoding, or ML training. Measure and report actual generation/list/detail/dashboard-widget latency — do not claim "real-time" without measurement.

## TESTING

Cover at minimum: generation (valid/no/incomplete evidence), severity threshold boundaries, evidence completeness and honest unavailability, observed-vs-inferred separation, recommendation mapping (including conditions that should produce no recommendation), provenance across all tiers including mixed evidence, deduplication vs legitimate recurrence, full API behavior (create/list/detail/filter/paginate/error), and full regression for Phases 10, 15, 16, 17. All existing tests must keep passing.

## VERIFICATION SCRIPT

Create `scripts/verify_phase18_*.py` following existing repo conventions, with real checks (no placeholders, no hardcoded PASS) covering: migration, insight model, deterministic generation, severity calculation, evidence package integrity, observed/inferred distinction, recommendation generation, provenance preservation, anomaly integration, simulation labeling, prediction-limitation handling, deduplication, API contracts, pagination, dashboard read-only behavior, measured performance, and full regression.

## REGRESSION

Re-run and pass Phase 10, 15, 16, and 17 test/verification suites unchanged.

## DOCUMENTATION

Update `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md` to cover: the Decision Intelligence architecture, insight lifecycle, evidence model, severity model, recommendation engine, provenance behavior, anomaly/simulation/prediction relationships, deterministic behavior, and known limitations.

## GIT

Follow existing repo conventions. One meaningful Phase 18 commit. Push to the established origin/main only if that is the existing workflow. Verify a clean working tree. Do not touch unrelated history.

## DEFINITION OF DONE

Phase 18 is VERIFIED only if all of the following hold — otherwise STATUS = BLOCKED (never fabricate success):
- Deterministic Insight Engine implemented and persisted; migration verified both directions
- Severity is evidence-based; evidence packages are complete and honest about unavailable data
- Observed and inferred information are explicitly separated everywhere
- Recommendations are deterministic, advisory-only, and never imply real-world control or unverified improvement
- Anomaly, simulation, and prediction integrations respect their existing boundaries (no ownership takeover, no upgraded provenance, no fabricated forecasts)
- Deduplication works without suppressing legitimate recurrence
- APIs work with bounded pagination and safe error handling
- Dashboard remains read-only; frontend insight experience works without a redesign
- Backend tests pass; frontend typecheck and production build pass
- Phase 10, 15, 16, 17 regressions pass
- Phase 18 verification script passes with real checks
- Documentation updated; git tree clean; no unrelated scope introduced

## COMPLETION REPORT (required at the end)

Report: STATUS (VERIFIED/BLOCKED), summary, repository inspection findings, files changed, architecture/DB/migration changes, insight model and lifecycle, severity logic, evidence architecture, root-cause/inference logic, recommendation logic, provenance verification, anomaly/simulation/prediction integration behavior, API and frontend/dashboard changes, deduplication behavior, security review, measured performance, test and verification results, Phase 10/15/16/17 regression results, frontend typecheck/build results, known limitations, git commit hash, push result, working-tree status.

## STRICT SCOPE EXCLUSIONS

Do not: reopen Phase 11 or fabricate forecasting data; add new forecasting/ML models; replace or modify YOLO, ByteTrack, or lane detection; implement any physical or real signal-control capability; convert simulation output into real-world claims; create a second job system; introduce an LLM for narrative generation; introduce microservices, Kubernetes, or distributed infra; add auth/RBAC for appearance only; redesign the frontend; start Phase 19; implement anything outside this scope.

## FINAL RULES

If a failure occurs: reproduce it, find the actual root cause, trace the real architecture, fix the root cause (not the symptom), add regression coverage, rerun affected and full regression. If any requirement cannot be safely implemented, STATUS = BLOCKED — do not fabricate a passing result. Never invent repository details you have not actually inspected.
