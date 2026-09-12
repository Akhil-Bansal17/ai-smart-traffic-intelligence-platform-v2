# Phase 15 — Traffic Anomaly & Congestion Incident Detection

## Role

You are Antigravity, the implementation agent for the AI Smart Traffic Intelligence Platform. You implement, test, debug, root-cause-fix, verify, and report. You do not implement code beyond this phase's scope. The repository is the source of truth — where it differs from prior documentation (including this prompt's assumptions), investigate and resolve based on actual implementation, and report the discrepancy.

Workflow, in order, no steps skipped:
READ → INSPECT → UNDERSTAND → PLAN → IMPLEMENT → TEST → DEBUG → ROOT-CAUSE FIX → RE-TEST → VERIFY → FULL REGRESSION → SECURITY REVIEW → PERFORMANCE REVIEW → DOCUMENT → GIT REVIEW → REPORT.

## Required Reading

Before any implementation:

1. `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md` — confirm actual current state; do not trust documentation blindly.
2. Backend routers/services/models for: Traffic Analytics (Phase 8), Lane/Density (Phase 9), Database persistence (Phase 10 — `AnalysisSession`, `TrafficMetricsRecord`, `LaneResultRecord`, `CrossingEventRecord`), Prediction (Phase 11), Signal Optimization (Phase 12), Emergency Corridor (Phase 13), System Dashboard (Phase 14).
3. Alembic migration history — confirm actual schema, not assumed schema.
4. Existing provenance implementation (`source_type`, `provenance_verified`, synthetic/simulation flags) and the four provenance categories: `real_database_metrics`, `synthetic_pipeline_metrics`, `simulation_configured`, `synthetic_fixture`.
5. Existing test suites and verification scripts for Phases 8–14, to understand established conventions before adding new ones.
6. Existing frontend Dashboard (Phase 14) component structure, API client, and design system.
7. Configuration/environment files — understand how thresholds/config are currently managed (e.g. `.env`, settings module) so new configuration follows the same pattern.

Do not proceed to PLAN until you can state, from the actual repository, exactly which of the below already exist versus need to be built.

## Current Project State (confirm against repo)

- Phases 1–10, 12, 13, 14: VERIFIED.
- Phase 11: CLOSED / PARTIALLY VERIFIED — 10 of 20 required real-world observation buckets exist. Remains closed; not reopened by this phase.
- Phase 14 delivered a strictly read-only System-Wide Decision Dashboard (System Health, Traffic Overview, Vehicle Composition, Traffic Flow, Lane/Density, Prediction Availability, Signal Optimization, Emergency Corridor, Historical Sessions, Data Provenance) that triggers no CV/ML/simulation work on load or refresh. Verified: 11/11 dashboard checks, 146 backend tests passed, 0 frontend typecheck errors, clean production build.

## Objective

Add a **Traffic Anomaly & Congestion Incident Detection** capability that analyzes already-persisted traffic metrics (flow, density, lane occupancy, class distribution) and flags statistically or rule-based abnormal conditions — e.g. sudden congestion buildup, abnormal density spikes, unexpected flow drops, lane imbalance — as discrete, persisted **incident/anomaly events**, surfaced through a new API and a new "Alerts" section on the existing Phase 14 dashboard.

This is a detection and decision-support layer over existing data — it is not a new CV model, not a new ML forecasting model, and does not require additional real-world observation volume (it operates on whatever `TrafficMetricsRecord`/`LaneResultRecord` data already exists, real or synthetic, with provenance always carried through and displayed).

## Existing Components to Reuse (do not rebuild)

- Traffic Analytics computation and persisted `TrafficMetricsRecord` (Phase 8/10)
- Lane/Density computation and persisted `LaneResultRecord` (Phase 9/10)
- `AnalysisSession` and `CrossingEventRecord` models (Phase 10)
- Existing provenance fields and categories (Phase 10/11)
- Existing Phase 14 dashboard shell, layout, design tokens, and API client
- Existing configuration/settings pattern for thresholds

Do not reimplement detection, tracking, counting, analytics computation, lane analysis, prediction, signal optimization, or emergency simulation. Do not introduce a new ML training pipeline — detection logic must be transparent, rule/statistics-based (e.g. configurable thresholds, rolling z-score/EWMA deviation, sustained-duration conditions), and explainable, not a black-box model.

## Architecture

```
Persisted TrafficMetricsRecord / LaneResultRecord (existing, Phase 10)
            ↓
   Anomaly Detection Service (new — rule/statistical, reads only)
            ↓
   AnomalyEvent persistence (new table, via Alembic migration)
            ↓
   REST API: list/filter/detail anomaly events (new)
            ↓
   Dashboard "Alerts" section (extends Phase 14 dashboard)
```

The detection service runs against already-persisted data — either as a lightweight step invoked after existing analytics/lane persistence completes for a session, or as an on-demand/query-time computation. Choose whichever fits the existing pipeline's actual invocation pattern (inspect Phase 8–10 code to decide) and justify the choice in the completion report. It must NOT trigger new video ingestion, detection, tracking, or counting.

## Functional Requirements

1. **Detection logic** (transparent, configurable, not a black box):
   - Congestion buildup: sustained density/occupancy above a configurable threshold for a configurable minimum duration.
   - Abnormal flow drop: flow/minute falling sharply below a rolling baseline (e.g. relative to recent session average or a configured statistical deviation).
   - Lane imbalance: significant occupancy skew across lanes in the same session.
   - Density spike: image-space density (Phase 9) exceeding a configured threshold — must retain the existing caveat that this is image-space density, not physical vehicles/km².
   - Each detection rule's thresholds/parameters must be configurable (not hardcoded magic numbers) via the existing configuration pattern.

2. **Anomaly/incident event record**, at minimum:
   - type (congestion / flow-drop / lane-imbalance / density-spike)
   - severity (e.g. low/medium/high, derived from how far the metric deviates from threshold — must be deterministic and explainable, not arbitrary)
   - source session/time-window reference
   - the actual metric values that triggered detection (for auditability)
   - provenance category inherited from the underlying data (real/synthetic/simulation) — an anomaly detected on synthetic data must be labeled as such, never presented as a real incident
   - timestamp of detection

3. **No fabrication**: if no data qualifies for a given detection rule, no anomaly is created — do not force-generate anomalies to populate the UI.

## Data / Provenance Requirements

- Every `AnomalyEvent` must carry through the provenance category of the underlying `TrafficMetricsRecord`/`LaneResultRecord` it was derived from.
- Anomalies derived from `synthetic_pipeline_metrics` or `synthetic_fixture` data must be visibly labeled as synthetic in both API responses and UI — never displayed as a real incident.
- Anomalies must never be derived from Phase 12/13 simulation output and presented as real-world incidents; if simulation-derived anomaly detection is out of scope for this phase, exclude it explicitly (see Strict Scope Exclusions).
- If underlying data is insufficient to evaluate a rule (e.g. not enough history for a rolling baseline), the API/UI must report that rule as "insufficient data," not silently skip it without explanation.

## API Requirements

- New read/query endpoints only where genuinely needed:
  - List anomaly events (filterable by session, type, severity, time range, provenance)
  - Get single anomaly event detail (including triggering metric values)
- If detection needs to be triggerable (rather than purely automatic/query-time), provide an explicit, clearly-named endpoint for it — do not silently run detection as a side effect of unrelated endpoints.
- All new endpoints use typed Pydantic request/response schemas, consistent with existing API conventions.
- Document each new endpoint (path, method, schema, example request/response).

## Database Requirements

- New `AnomalyEvent` table via a proper, minimal Alembic migration — do not modify or backfill historical migrations.
- Foreign-key relationship to the source `AnalysisSession`/`TrafficMetricsRecord`/`LaneResultRecord` as appropriate.
- Index fields used for filtering (session, type, severity, timestamp) to keep queries efficient.

## Frontend Requirements

- Extend the existing Phase 14 dashboard with an "Alerts" / "Anomalies" section, reusing existing design tokens, layout, and component patterns — no new UI framework, no divergent visual style.
- Each anomaly card/row must show: type, severity, triggering metrics, timestamp, and a clear provenance/state label (real / synthetic / simulation / insufficient-data), consistent with Phase 14's REAL / SIMULATION / PREDICTION / SYNTHETIC / UNAVAILABLE labeling convention.
- Support filtering by type/severity/session in the UI.
- Handle empty state honestly ("No anomalies detected in current data" is different from "Detection unavailable" — do not conflate them).
- Do not trigger new detection/analysis merely by opening this dashboard section unless the user explicitly initiates it (if an on-demand trigger is implemented).

## Security

- Reuse existing authentication/authorization conventions if any exist; do not introduce a new auth model.
- Validate/sanitize all filter query parameters on new endpoints.
- Do not leak raw database errors or stack traces in API responses.
- Confirm no secrets, credentials, or `.env` values are introduced, logged, or committed.

## Performance

- Detection computation must not run expensive full-table scans on every dashboard load; use indexed, bounded queries or precomputed/persisted results.
- Avoid N+1 query patterns in list/filter endpoints.
- Report actual measured query/response times for the new endpoints — do not estimate.

## Critical Root-Cause Fix Rule (mandatory)

Do not fix code merely to make a test or verification check pass. For any failing test, verification script, integration test, or runtime check:
1. Investigate the actual underlying cause.
2. Reproduce the problem.
3. Trace it to the responsible implementation/design/data/configuration issue.
4. Fix the root cause correctly.
5. Add or improve regression coverage where appropriate.
6. Re-run the failing check, then re-run related tests.
7. Verify actual behavior, not merely that an assertion passes.
8. Continue debugging if the implementation is still incorrect.

A manipulated test, weakened assertion, hardcoded expected value, special-cased workaround, mocked behavior that hides a real defect, or superficial patch whose only purpose is to make verification green is NOT an acceptable fix. A PASS result is meaningful only when underlying behavior is genuinely correct. If a proper fix requires an architectural adjustment, make the proper adjustment rather than a superficial workaround.

## Testing

- Unit tests for each detection rule: true-positive case, true-negative case, boundary/threshold case, insufficient-data case.
- Unit tests confirming provenance is correctly inherited and never upgraded (e.g. synthetic input must never yield a "real" labeled anomaly).
- Integration tests for new API endpoints: filtering, pagination if applicable, detail retrieval, empty-result handling.
- Frontend component tests for the Alerts section: populated state, empty state, insufficient-data state, mixed-provenance state.
- Regression tests confirming the dashboard's read-only guarantee still holds (opening/refreshing the Alerts section triggers no ingestion/detection/tracking/counting side effects unless explicitly on-demand and user-initiated).

## Verification Script

Extend or add a verification script that:
- Seeds/uses test data covering at least one real-provenance and one synthetic-provenance scenario
- Confirms each detection rule fires correctly under a known constructed condition and does not fire under a known negative condition
- Confirms provenance labeling is correct on generated anomaly events
- Confirms API filter/query behavior
- Prints explicit pass/fail per check with the underlying values checked — not just "success"

## Regression

Run and report full existing test suites for Phases 1–14 (backend and frontend). Confirm no existing endpoint, page, dashboard section, or migration was broken. Report any pre-existing failures unrelated to this phase as pre-existing — do not silently fix or hide them as a side effect of this phase's work.

## Documentation

- Update `PROJECT_STATUS.md` with Phase 15's honest status (VERIFIED / PARTIALLY VERIFIED / BLOCKED), what was built, what was reused, and detection-rule configuration reference.
- Update `ARCHITECTURE.md`/README with the new Anomaly Detection Service and its data flow.
- Document new API endpoints and the `AnomalyEvent` schema.
- Document each detection rule's parameters/thresholds and how to configure them.

## Git

- Focused commit(s) scoped to Phase 15 only.
- No secrets, `.env`, database files, generated runtime artifacts, or media uploads committed.
- Clean working tree at completion.
- Commit message references Phase 15 explicitly.

## Definition of Done

- Anomaly detection service implemented against existing persisted data only, with transparent/configurable rule logic (no black-box ML).
- `AnomalyEvent` persisted via proper migration, correctly carrying inherited provenance.
- New API endpoints implemented, typed, and documented.
- Dashboard "Alerts" section implemented, reusing existing design system, with correct state/provenance labeling and honest empty/insufficient-data handling.
- No CV/ML/simulation engine rebuilt; no physical control introduced.
- All new code has passing unit/integration/component tests; verification script passes with printed evidence.
- Full regression suite for Phases 1–14 passes, or failures are reported as pre-existing with justification.
- Root-cause fix rule followed for any failures encountered (documented in the report).
- Security and performance reviews completed with findings reported.
- Documentation and `PROJECT_STATUS.md` updated.
- Git history clean and focused.

## Completion Report

Must include, with actual evidence (command output, logs, screenshots where useful — not claims):
- What was built vs. reused, and why the chosen architecture (invocation point of detection) fits the existing pipeline
- Verification script output
- Regression test results (pass/fail counts; pre-existing failures explicitly noted)
- Root-cause investigation notes for any failures encountered during implementation, and the actual fix applied
- Security review findings
- Performance measurements (query/response times)
- Any provenance/data-honesty edge cases encountered and how they were resolved
- Any deviation from this prompt and why
- Explicit Phase 15 status: VERIFIED / PARTIALLY VERIFIED / BLOCKED, with justification

## Strict Scope Exclusions

- Do NOT build a new CV model, tracker, counter, or lane analyzer.
- Do NOT build a new ML forecasting/prediction model, and do NOT reopen or attempt to work around Phase 11's real-data shortfall.
- Do NOT derive anomaly detection from Phase 12/13 simulation output in this phase — detection scope is limited to real/synthetic traffic metrics and lane/density data (Phases 8–10). If simulation-based anomaly detection is desired later, that is a future phase.
- Do NOT implement any physical control: no traffic light hardware control, IoT signal commands, emergency/police/fire dispatch, or V2X control commands.
- Do NOT introduce a new frontend framework, competing design system, or new authentication model.
- Do NOT begin Phase 16 or any work beyond anomaly/incident detection and its dashboard integration.
- Do NOT fabricate anomalies to populate an otherwise-empty UI.

## Final Rules

Never fabricate traffic values, vehicle counts, historical records, predictions, confidence values, performance measurements, KPIs, charts, simulation outcomes, or verification results. Never present synthetic data as real traffic, simulation output as measured real-world traffic, prediction output as ground truth, or unavailable functionality as operational. Maintain all existing provenance categories and qualification rules without weakening them. If something cannot be verified, report PARTIALLY VERIFIED, BLOCKED, or FAILED — not "implemented successfully" without evidence. The repository is the source of truth; when this prompt and actual repository state disagree, investigate and resolve based on real implementation, and report the discrepancy.
