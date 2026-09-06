# 11 — Traffic Prediction / Forecasting

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior ML/backend engineer adding the platform's first genuine machine-learning layer: real persisted traffic data → dataset extraction → feature engineering → a trained, evaluated model → honest predictions. No fabricated numbers anywhere in this phase.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`, `ARCHITECTURE.md` (§8, the schema — see Current State below), `README.md`
3. `prompts/antigravity/01` through `10` — accumulated architecture decisions, known discrepancies, and Phase 9.1/10's actual verified outcomes
4. **The actual current Phase 10 implementation** — this is critical for this phase: the real `AnalysisSession`/`analysis_sessions` model, `TrafficMetricsRecord`/`traffic_metrics`, lane-result records, crossing-event records if persisted, `Video`, their actual relationships, indexes, constraints, and timestamps. **Do not design Phase 11 against the schema `ARCHITECTURE.md` §8 describes without confirming Phase 10 actually implemented it that way** — Phase 10 may have adapted the design; the live database schema wins.
5. Existing API endpoints and the History page's actual data consumption pattern
6. `backend/app/`, `backend/tests/`, `backend/scripts/`, requirements files, `.env.example`
7. `frontend/src/` — pages, components, API client, types, routing, configuration; `frontend/package.json`, Vite/TypeScript configuration

**Do not blindly trust prior completion reports, including Phase 10's claimed "92 tests passed / 8-8 database verification / clean regression."** Confirm it yourself by inspecting the actual repository and re-running what you can. If the repository differs from Current State below, build against what's actually there and report the discrepancy. If a genuine gap makes Phase 11 impossible to build correctly, stop and report `BLOCKED`.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY → DOCUMENT → UPDATE PROJECT_STATUS.md → GIT REVIEW → REPORT
```

## Context — Verify Before Building On It

Phases 1–2 were independently verified directly in a prior session. **Phases 3–10 were completed by prior Antigravity runs.** Phase 10's reported scope: real PostgreSQL persistence for analysis runs, traffic analytics, and lane results, wired to the existing CV pipeline's output without modifying that pipeline, verified via a real `scripts/verify_phase10_database.py` run. **Confirm this is actually true before starting** — Phase 11 depends entirely on Phase 10's persisted data existing and being queryable; if it doesn't, this phase can't proceed and must be reported `BLOCKED`, not worked around with a parallel data source.

## Current State You're Building Against (per architecture docs + prior reports — confirm against actual code)

- `ARCHITECTURE.md` §8 already documents a `predictions` table from Phase 1: `id, analysis_session_id (fk), generated_at, horizon_minutes, target (volume/congestion/queue), predicted_value, model_version`. **This means new-table need should be minimal** — confirm this table (or Phase 10's actual equivalent) exists and is adequate before designing something new. If it needs extending (e.g., for evaluation metrics or a model-version registry), extend it deliberately and explain why, rather than replacing it.
- Historical traffic data, if it exists at all, lives in whatever Phase 10 actually persisted (`analysis_sessions` + `traffic_metrics`, per §8's design) — the amount of *real* historical data available is almost certainly small (however many videos have actually been processed through the pipeline so far), which directly shapes the Model Design and Data Reality sections below.
- No prediction code, no training pipeline, no prediction endpoint, and no prediction persistence exist yet as of the state this prompt was written against — confirm this is still true.

## Objective

```
PostgreSQL Historical Traffic Data → Dataset Extraction → Feature Engineering
  → Training/Validation → ML Prediction Model → Future Traffic Forecast
  → Prediction API → React Prediction Dashboard
```

Introduce genuine, honestly-evaluated traffic forecasting built on real persisted data from Phases 1–10 — never fabricated predictions, random numbers presented as ML output, hardcoded values, fake confidence scores, or a UI-only simulation pretending to be machine learning.

## Explicit Exclusions — Do NOT Implement

YOLO/tracking/counting improvements, autonomous lane detection, camera calibration, speed estimation, signal optimization, adaptive traffic signals, emergency corridor simulation, reinforcement learning, advanced deep learning forecasting (unless the actual data genuinely justifies it — unlikely at this stage, see Model Design), cloud deployment, distributed processing, authentication, user accounts, microservices, real-time streaming infrastructure, or any Phase 12+ functionality. Do not modify previously-verified CV functionality unless a concrete compatibility defect is found.

## The Data Reality Requirement (the most important section in this prompt)

Distinguish, everywhere and always: **(A) real persisted traffic observations**, **(B) synthetic/fixture training data**, **(C) model predictions**. Never blur these. If the actual database contains too few real historical observations for meaningful supervised learning (likely, this early in the project), **do not pretend the resulting model is production-ready**. Instead:

- Define a minimum-dataset-size threshold for "enough data to train meaningfully" (state your chosen number and reasoning).
- Implement a dataset-readiness check that the API and UI both honestly reflect.
- If real data is insufficient, you may generate clearly-labeled synthetic fixture data **for development/testing only** — it must never be presented to a user as real-world traffic data, and any evaluation metric computed against it must be labeled as a synthetic-data result, not a real-world performance claim.
- The frontend must communicate the actual data basis plainly. `"Prediction unavailable: insufficient historical observations"` is a correct and acceptable outcome. `"Traffic predicted: 47 vehicles"` backed by no real training data is not acceptable under any framing.

## Model Design

Inspect what's actually available (row counts, feature richness, time span) before choosing anything. Prefer a simple, explainable baseline first — Linear/Ridge Regression, Random Forest Regressor, Gradient Boosting/HistGradientBoostingRegressor, or another lightweight classical method are all reasonable candidates; do not reach for deep learning without a data-driven reason you can actually state. Justify your choice against: available data volume, feature types, the target variable, computational cost, interpretability, and maintainability. If temporal structure exists in the data (it should — traffic is a time series), preserve chronological order; do not randomly shuffle observations if that would leak future information into training.

## Prediction Target

Define explicitly — a reasonable first target is **future vehicle volume for a specified future interval**, directly derived from persisted traffic-analytics data, matching `predictions.target` in the existing schema design. Document: the exact target variable and its unit, the prediction horizon, every feature's definition, the time-bucket definition used, the training window, the validation strategy, and the evaluation metrics. "Traffic prediction" without these specifics is not an acceptable scope definition.

## Feature Engineering

Derive features only from what's actually in the persisted database — don't invent a feature the schema can't support. Candidates, only if genuinely available: historical vehicle volume, flow rate, class counts/percentages, inbound/outbound counts, observation duration, time-of-day, day-of-week, lag values, rolling statistics. For every feature used, document its source, definition, unit, and leakage risk. Never construct a training feature using information that wouldn't have been available at that point in time (no using future data to predict the past). Handle missing initial values from lag/rolling features explicitly and honestly (e.g., drop the affected rows, or document the imputation choice — don't silently zero-fill without saying so).

## Temporal Validation

Respect chronological order: earlier observations train, later observations validate/test — not an ordinary random split, which would leak future information into training for a forecasting task. If the actual dataset is too small for a meaningful chronological split, **report that limitation explicitly rather than inventing statistical confidence** you don't have.

## Model Evaluation

Use appropriate regression metrics (MAE, RMSE, R² — whichever are actually meaningful given the dataset size; don't report R² on a handful of points and imply it's meaningful). Document the metric definitions, the exact validation dataset used, a baseline comparison (e.g., "predict the previous observed value" or another honest, simple baseline the data supports), and the model's actual measured result. Never claim the ML model outperforms the baseline unless the measured numbers actually show it.

## Prediction Uncertainty

Do not fabricate a confidence percentage. If the chosen model doesn't naturally produce calibrated uncertainty, don't display a fake "95% confidence" anywhere. Acceptable UI content: prediction value, model name, evaluation metrics, training-data size, data source (real vs. synthetic), prediction horizon, and model status. If genuine uncertainty quantification is implemented via a defensible method, document exactly how.

## Model Storage / Lifecycle

Choose train-on-demand, a locally persisted model artifact, versioned model metadata in the database, or explicit retraining — based on what fits the existing architecture, and state your reasoning. Never commit generated model binaries to Git if the existing `.gitignore` policy already excludes such artifacts (it does — confirm and respect it). Never expose an arbitrary filesystem path through the API. If storing artifacts locally, use a controlled, configured directory (add to `.env.example` if new). Model loading must validate the artifact and fail safely, not crash the server or silently serve stale/corrupt results.

## Database Integration

Confirm the actual Phase 10 schema first (per Current State). If persistence is needed beyond the existing `predictions` table design, evaluate genuinely necessary additions — e.g., `model_versions` if you need to track multiple trained model iterations — but **do not create tables the existing schema can already reasonably serve**. Any new model needs proper primary/foreign keys, indexes, timestamps, and constraints, consistent with existing conventions. Use Alembic exclusively: verify the migration applies to a fresh database, upgrades the existing Phase 10 database cleanly, is reversible where practical, and survives an upgrade → downgrade → re-upgrade cycle. No manual schema edits outside Alembic.

## API Design

Versioned endpoints under `/api/v1/predictions`, following existing conventions exactly (schema style, error format, dependency injection, response models). Design only what's genuinely needed — likely candidates: prediction-engine info, dataset-readiness check, trigger training, trigger/retrieve evaluation, generate a prediction, retrieve prediction history, retrieve a specific prediction run. Typed Pydantic schemas throughout. No filesystem paths, database credentials, unsafe model internals, stack traces, or secrets in any response. Bound request parameters (e.g., a maximum prediction horizon) and prevent an endpoint from triggering an unbounded, expensive training job on every call.

## Frontend

Integrate into the existing React app — likely a `PredictionsPage.tsx` (confirm the actual current placeholder/route name first; it may already exist from Phase 3's routing scaffold). Real API data only. Reasonable UI: dataset-readiness indicator, historical-observation count, training status, model name, training-dataset size, evaluation metrics, prediction horizon, prediction value, a historical-vs-predicted visualization, a clear real-data-vs-synthetic-data badge, an honest insufficient-data state, and loading/error states consistent with the rest of the app. Never fabricate chart data to fill an empty view — if there isn't enough real data, the UI says so. Reuse existing components and styling; don't redesign the app.

## Security & Resource Limits

Guard against: arbitrary filesystem/model-path input from clients, uncontrolled/unbounded training job triggering, unbounded dataset extraction, memory/CPU exhaustion during training or inference, an oversized prediction horizon, SQL injection (ORM/parameterized queries only), unsafe deserialization of model artifacts, unsafe model loading (validate before use), secret leakage, model-artifact exposure via the API, and unbounded database queries. Apply reasonable, configured limits on both training and inference.

## Testing

**Dataset:** historical-data extraction; empty dataset handled correctly; insufficient dataset handled correctly (readiness check fires); valid dataset extraction; feature generation correctness; temporal ordering preserved; leakage prevention (a feature never uses future data relative to its target); missing-value handling.

**Model:** initialization; training actually runs and completes; prediction actually runs and completes; deterministic/reproducible behavior where the algorithm allows it; invalid-input handling; evaluation metrics computed correctly; baseline comparison, if implemented.

**Prediction:** a valid prediction request; horizon bounds enforced; correct insufficient-data behavior (no fabricated fallback); correct response schema; no fabricated values anywhere; persistence, if implemented.

**API:** info endpoint; readiness endpoint; training endpoint; prediction endpoint; history endpoint if implemented; invalid IDs and parameters rejected cleanly; structured error responses; path isolation.

**Database:** migrations apply correctly; foreign keys and constraints enforced; persistence and retrieval work; cascade behavior where applicable.

**Regression:** the complete existing Phase 1–10 test suite still passes — paste actual output.

## Real Verification Requirement

Create `scripts/verify_phase11_prediction.py` (or the repository's equivalent naming convention). It must, with genuine observed values throughout:

1. Connect to the actual configured PostgreSQL database.
2. Inspect actually-available historical traffic data.
3. Determine, using your stated threshold, whether enough real data exists.
4. If real data is insufficient, generate clearly-labeled synthetic fixture data **for this verification run only** — never presented as real.
5. Build the training dataset and show actual feature counts/shapes.
6. Train the actual selected model.
7. Evaluate it and report real metrics.
8. Generate at least one genuine prediction and show its actual output.
9. Prove the prediction is not hardcoded (e.g., show it changes with different input data, or trace the computation).
10. Verify temporal train/test separation was actually respected.
11. Persist prediction/model metadata, if persistence is in scope for this phase.
12. Query the persisted result back through a fresh database session (proving genuine persistence, not in-process caching).
13. Verify the REST API against a running server.
14. Verify frontend integration via typecheck/build.
15. Report timing/resource usage for training and inference.

The script's output must clearly state, at the top: `DATA SOURCE: REAL DATABASE` or `DATA SOURCE: SYNTHETIC FIXTURE — NOT REAL TRAFFIC DATA` — and if synthetic, every subsequent metric in that run must be understood as a synthetic-data result, not a real-world performance claim.

## Definition of Done

Phase 11 may be reported `VERIFIED` only if **all** of the following are true and evidenced: the actual repository was inspected (not assumed); the prediction target is explicitly defined; dataset extraction works; feature engineering works; temporal leakage is prevented; the model genuinely trains; the model genuinely predicts; evaluation genuinely runs; no fabricated predictions or metrics exist anywhere; insufficient-data behavior is honest; database persistence works if it's part of this phase's design; the REST API works; the frontend uses real API data; Phase 11's own tests pass; the full Phase 1–10 regression suite passes; frontend typecheck passes; frontend production build passes; security/resource checks pass; the verification script produces real evidence; documentation is updated; `PROJECT_STATUS.md` is updated with actual evidence; Git changes are focused and clean. **If any of these can't be confirmed, the status must be `PARTIALLY VERIFIED`, not `VERIFIED`.**

## Documentation

Update only what's actually affected — likely `PROJECT_STATUS.md`, `ARCHITECTURE.md` (confirm the `predictions` table's real implementation against §8), `README.md` if warranted. Document: the prediction target, feature definitions, model choice and rationale, evaluation methodology, the real-vs-synthetic data-source policy, limitations, the API contract, model lifecycle, and known issues. Never claim production-grade forecasting capability if the available dataset doesn't actually justify it.

## Git

Focused changes only — no unrelated refactoring, no secrets, no `.env` files, no database files, no generated uploads, no model binaries if repository policy excludes them, no scratch/debug artifacts left behind. Suggested commit: `feat: add traffic prediction pipeline`. Only commit after tests and verification genuinely pass.

## Completion Report

Require:

1. Phase 11 summary
2. Files created
3. Files modified
4. Database changes
5. Migration details
6. Dataset source (real, synthetic, or a mix — and why)
7. Dataset size (actual numbers)
8. Feature definitions
9. Prediction target
10. Model selected
11. Why that model was selected
12. Training results
13. Evaluation metrics (real)
14. Baseline comparison, if implemented
15. A genuine prediction example with actual output
16. Persistence results
17. API results
18. Frontend typecheck results
19. Frontend build results
20. Phase 11 test results (pasted)
21. Full Phase 1–10 regression results (pasted)
22. Security/resource checks
23. Git status
24. Commit hash
25. Known limitations
26. Data-source limitations
27. Whether synthetic data was used, and where
28. Final status: `VERIFIED` / `PARTIALLY VERIFIED` / `BLOCKED` / `FAILED`

`VERIFIED` is only appropriate when the evidence actually supports every item in the Definition of Done above.

## Critical Architecture Principle

```
Video → CV Pipeline → Traffic Metrics → PostgreSQL → Prediction Dataset
  → ML Model → Prediction → API → React
```

Do not bypass the database — predictions are built from persisted data, not a shortcut around it. Do not build a disconnected ML demo; this becomes a real, integrated part of the existing platform, or it doesn't count as done.
