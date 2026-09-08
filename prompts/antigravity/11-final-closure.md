# 11 — Final Closure: Real-World Data, Provenance, ML Readiness & Production Hardening

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are acting as a senior software architect, computer-vision engineer, ML engineer, data engineer, security reviewer, and verification engineer simultaneously. This is the final closure and hardening pass on Phase 11 before the project can honestly move to Phase 12.

## Current Status Going Into This Phase

Phases 1–10 and 9.1 have passed their regression/verification gates (see `PROJECT_STATUS.md` for exact evidence and caveats). Phase 11's prediction functionality was implemented and technically works. Phase 11.1 generated 34 observations from 10 video-analysis sessions and labeled them `real_observations`. **Phase 11.2's provenance audit found those videos were not genuine real-world traffic recordings — they were generated/test videos created with OpenCV and a demo bus image.** The CV pipeline, tracking/counting/analytics outputs, database persistence, and ML training pipeline are all genuine — only the underlying footage is synthetic. Phase 11.2 correctly classified this as **Outcome C: only synthetic/test traffic data available** → CV-to-ML pipeline validation = VERIFIED, real-world traffic forecasting = NOT YET VERIFIED, Phase 11 overall = PARTIALLY VERIFIED. This phase exists to resolve that, honestly, one way or another.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md`
3. `backend/app/models/{video,analysis,prediction}.py`
4. `backend/app/schemas/{video,analytics,lane_analysis,prediction}.py`
5. `backend/app/services/cv/{video_source,detector,tracker,vehicle_counter,traffic_metrics_engine,lane_analyzer,analysis_persistence_service}.py`
6. `backend/app/services/ml/{dataset_extractor,traffic_feature_engineer,traffic_predictor}.py`
7. All prediction and video API modules; all relevant frontend prediction/video/history components
8. All Alembic migrations, all verification scripts, all relevant backend tests
9. Frontend package configuration, `backend/requirements.txt` (or equivalent), `.env.example`, `.gitignore`, Git status and recent history

**Do not blindly trust previous completion reports — including this prompt's own summary of Phase 11.2 above.** The repository is the source of truth; confirm everything before building on it.

## Workflow

```
READ → INSPECT → TRACE → PLAN → VERIFY → REPRODUCE → FIX → TEST
  → ACQUIRE/VERIFY REAL DATA → RUN REAL CV PIPELINE → TRAIN/EVALUATE REAL ML MODEL
  → RE-VERIFY → FULL REGRESSION → SECURITY CHECK → DOCUMENT → GIT REVIEW → REPORT
```

Do not skip to implementation. Do not make speculative changes — every fix needs a demonstrated reason.

## Primary Objective

Close Phase 11 honestly and completely by demonstrating (or honestly failing to demonstrate) this full chain:

```
Genuine recorded real-world traffic footage → verified provenance → Phase 4 ingestion
  → YOLO → ByteTrack → counting → traffic analytics → lane/density analysis
  → PostgreSQL persistence → real-world observations → feature engineering
  → chronological train/test split → prediction model → real-data evaluation
  → future forecast → prediction persistence → REST API → React frontend
```

No synthetic/test video may be represented as real-world data. No fabricated metrics, hardcoded forecasts, fabricated timestamps, fake accuracy numbers, or fake real-world dataset.

## Critical Problem #1 — Real-World Data Must Actually Exist

The repository's current synthetic/test videos (including the OpenCV-generated one from Phase 11.1) must stay available for regression testing but must never count as real-world observations. This phase must obtain or use a legitimate source of genuine recorded real-world traffic footage. Preferred source order: (1) existing repository footage, if its real-world origin can actually be verified; (2) existing uploaded footage, if verifiable; (3) a legitimate publicly-available traffic-video dataset/footage with clearly documented usage/license terms; (4) if a public dataset is used, record its exact source, dataset name, URL/reference, license/usage terms, and acquisition date in the documentation. **Never use:** OpenCV-generated traffic videos, moving image patches, mathematically generated scenes, synthetic datasets, copied verification fixtures, procedurally generated frames, manually fabricated database rows, hardcoded CSV rows pretending to be observations, fake timestamps, or arbitrary numbers chosen to make ML "work."

## Real Data Acquisition Requirements

If no genuine footage exists in the repository, obtain a small, legitimate real-world traffic dataset/footage that can legally and technically be used for development — ideally actual road traffic, multiple vehicles, multiple frames, real temporal continuity, and (preferably) enough footage for multiple independent observation intervals. For every real-world video used, record: source name, source URL/dataset reference, license/usage basis, acquisition date, original and local filename, duration, fps, resolution, source type, and a provenance note. Never claim a license you can't verify. **If no legitimate real-world source can be obtained in your environment, do not fabricate one — report `BLOCKED` with the exact reason, but only after genuinely exhausting the reasonable legitimate options available to you.**

## CRITICAL REAL-DATA INTEGRITY RULE

Do not create, generate, transform, remix, animate, crop-and-move, or otherwise manufacture footage in order to make it qualify as real-world traffic.

If a legitimate real-world traffic video is not already available locally and the environment does not provide an authorized way to obtain one, STOP and report BLOCKED rather than attempting to manufacture or simulate real-world footage.

If external access is available, use only a clearly identifiable legitimate source with verifiable provenance and usage/license information.

If user-provided real-world footage is required, clearly report exactly what footage is missing and do not substitute synthetic footage.

The number of observations must never be increased artificially by duplicating, copying, resampling, or fabricating traffic observations.

20 observations means 20 legitimate observations produced from genuine recorded traffic data — not 20 duplicated rows, repeated frames, or synthetic expansions of a smaller dataset.

## Provenance Model Hardening

Review the current `videos.source_type` implementation. **Known concern:** the migration reportedly defaulted new rows to `source_type = 'real_world'`, which is unsafe — an unknown/unverified upload must never automatically become "real-world" data. Harden this to explicit semantics: `real_world`, `synthetic_test`, `unknown` (introduce another state only with a genuinely justified reason). **Critical rule: `unknown` and `synthetic_test` must never be eligible for real-world ML training.** Only `video.source_type == "real_world"` **and** verified provenance metadata may contribute to the real-world prediction dataset. Never infer `real_world` just because a file happens to be an MP4.

## Video Provenance Metadata

If the current `Video` model is insufficient, add the minimum necessary fields: `source_type`, `source_reference`, `license_reference`, `provenance_note`, `provenance_verified`, `captured_at` (only if genuinely known — represent unknown capture time as unknown, never invented). Any migration: proper Alembic migration, works against existing databases, correctly preserves existing synthetic/test records (they stay `synthetic_test`, not silently upgraded), any unverified video becomes `unknown` (never defaults to `real_world`), and upgrade/downgrade/re-upgrade/fresh-database-creation are all tested.

## PROVENANCE TRUST BOUNDARY

The fields `source_type` and `provenance_verified` are metadata claims, not proof by themselves.

Real-world ML eligibility requires both:

1. database provenance metadata indicating `real_world` + verified provenance
2. an auditable source record/reference that independently supports the claim that the footage originated from genuine recorded real-world traffic

Do not consider a manually edited database flag sufficient evidence.

Client-uploaded `source_type=real_world` must not automatically establish trusted provenance.

If provenance cannot be independently supported, classify the video as `unknown` and exclude it from real-world ML.

## Real vs. Synthetic Data Segregation (three categories, explicit)

- **A. `real_observations`** — genuine real-world traffic footage only. Eligible for real-world forecasting.
- **B. `synthetic_pipeline`** — synthetic/test traffic video processed through the genuine CV pipeline (this describes the existing 34 Phase 11.1 observations). Useful for CV-to-ML integration testing. **Not eligible for real-world forecasting.**
- **C. `synthetic_fixture`** — mathematically generated/offline ML development data. Useful for unit/integration tests. **Not eligible for real-world forecasting.**

Audit `DatasetExtractor` to make this distinction explicit in every query — no query may accidentally combine all three, and no join may accidentally treat `synthetic_pipeline` as `real_observations`.

## Database Provenance Chain

Verify the full chain: `PredictionRun → traffic_metrics → analysis_session → video → source_type → source_reference/provenance metadata → actual original source`. A `PredictionRun` marked `data_source = real_observations` must be provably built from observations whose underlying videos are genuinely `source_type = real_world` and `provenance_verified = true`. A run marked `synthetic_pipeline` must trace back to `source_type = synthetic_test` and never count as real-world.

## Real Dataset Quality Check

Once genuine footage is obtained, process it through the **existing** Phase 4–10 pipeline — never bypass it by inserting `traffic_metrics` rows directly. Correct route: real video → upload → `VideoSource` → YOLO → ByteTrack → counting → analytics → lane analysis → `AnalysisPersistenceService` → PostgreSQL, then `DatasetExtractor` reads what was persisted. Report: genuine real-world video count, session count, observation count, temporal coverage, observation durations, total vehicle counts, class distribution, direction distribution where available, and source provenance.

## Minimum Dataset Requirement

The existing threshold is `MIN_TRAINING_SAMPLES = 20`. Do not simply lower it to force a pass — determine whether 20 is actually defensible for the current model/feature design. Distinguish three states: enough real data (train/evaluate real forecasting), real data exists but is insufficient (forecasting stays unavailable), and no real data (forecasting stays unavailable). Never convert insufficient data into fake readiness. If the genuine dataset has fewer than the required observations, document that honestly; if ≥20 legitimate observations exist, proceed to real-data evaluation.

## REAL DATASET INDEPENDENCE AND COVERAGE

Do not treat the numerical threshold of 20 observations as sufficient by itself.

Also inspect whether the observations contain meaningful temporal variation and sufficient independent information.

Report:

- number of source videos
- number of analysis sessions
- number of observation buckets
- observation interval
- temporal span
- unique recording periods
- whether observations come from one continuous clip or multiple recordings
- whether observations are highly repetitive/correlated
- distribution of traffic volumes
- distribution of vehicle classes
- distribution of directions
- missing/zero-volume intervals

If 20+ observations are obtained from an extremely short or highly repetitive recording, do NOT describe the dataset as a strong real-world forecasting dataset.

The system may technically train if the existing readiness policy permits it, but the final report must explicitly classify the dataset as limited and must not make production-quality or generalization claims.

Never manufacture independence by splitting one frame sequence into artificial copies.

## Temporal Coverage

Report earliest/latest observation timestamp (if genuinely available), total temporal span, observation count, interval/bucket size, and whether observations are contiguous or sparse. Never invent a timestamp. If actual capture timestamps are unavailable, clearly distinguish video-relative timestamps from acquisition timestamps from real-world capture timestamps — and never claim day-of-week or time-of-day features are meaningful unless backed by legitimate timestamps.

## Feature Engineering Audit

Audit every existing feature (lag 1/2/3, rolling mean, rolling std, flow/minute, inbound ratio, hour sin/cos, day-of-week, peak flag): confirm each is genuinely available at prediction time and that no future target information enters the feature vector. Pay particular attention to rolling windows, target shifts, timestamp-derived features, recursive forecasting, the train/test boundary, and any normalization/scaling.

## Formal Future-Leakage Test (on the real dataset)

Choose a real observation `t_k`, record its feature vector, modify only future target observations after `t_k`, recompute the feature vector for `t_k`. Expected: unchanged. Print: observation index, original target, perturbed future target, original feature vector, perturbed feature vector, and the maximum absolute feature difference — expected `0`, or a mathematically explained legitimate non-zero difference. No hardcoded result.

## Real-Data Model Evaluation

Only using legitimate real-world observations. Chronological validation — never a random shuffle of time-series data; earlier observations train, later observations are held-out test. Compare the selected model against the naive-persistence baseline using appropriate metrics (MAE, RMSE, R² where statistically meaningful — a positive R² alone isn't success). Report: real observation count, train/test sample counts, model, baseline, metrics, training time, inference time. If the model underperforms the baseline, report that honestly — the goal is trustworthy forecasting, not forced model superiority.

## Model Selection

Reconsider the existing candidates (Random Forest, HistGradientBoosting, Ridge, naive baseline) against the real-world dataset rather than defaulting to whatever Phase 11 originally picked on synthetic data — but keep it lightweight and explainable; don't reach for deep learning or added complexity without compelling evidence from the real data.

## Multi-Step Forecast Validation

Verify the existing forecast horizon (+5/+10/+15 min or whatever's actually implemented) genuinely depends on model input — a low-current-traffic input should produce a different result than a high-current-traffic input, generated by the actual model, never hardcoded to differ.

## Uncertainty / Prediction Interval Audit

Confirm the UI/API never calls the empirical residual-based interval a "confidence interval" unless it genuinely is one statistically — use accurate terminology ("empirical prediction interval") and document the method. Verify intervals aren't nonsensical or negative for vehicle counts.

## Training API Safety

Audit `POST /api/v1/predictions/train`: if genuine real-world data is insufficient, the endpoint must reject the request or explicitly return an unavailable/`readiness=false` response — **never silently substitute synthetic data.** Explicit synthetic/development training may remain available only via a clearly named development/testing option, and its resulting `PredictionRun` must say `data_source = synthetic_pipeline` or `synthetic_fixture` as appropriate — never `real_observations`.

## Readiness API

Audit `GET /api/v1/predictions/readiness`. It must report: real observation count, synthetic-pipeline observation count, synthetic-fixture availability, the minimum required real observations, readiness, the reason, and the data source. An honest current state, given Phase 11.1/11.2's findings, is plausibly: `real observations = 0, synthetic pipeline observations = 34, minimum required = 20, is_ready = false, status = synthetic_pipeline_only` — confirm this is what the API actually reports, and update it if it isn't.

## Frontend Transparency

Audit `PredictionsPage`. It must make the difference unmistakable: real-world (positive state), synthetic-pipeline (clearly labeled synthetic/test), synthetic-fixture (clearly labeled development fixture), and unavailable (clear explanation of why real forecasting can't currently run) — never a synthetic prediction displayed in a way that could be mistaken for a real-world one. For a real-world run, show data source, observation count, evaluation metrics, forecast horizon, model, and train/test split. For synthetic runs, show a strong disclaimer.

## Persistence Audit

For every persisted `PredictionRun`, verify: source provenance, model name, feature information, train/test sample counts, metrics, baseline metrics, prediction horizon, data source, timestamp — confirmed via a fresh database session, not an in-memory-only claim.

## Synthetic Test Data Must Remain

Do not delete the existing synthetic/test videos — they're useful for regression, CI, CV testing, integration testing, and ML pipeline testing. Keep them clearly classified as `synthetic_test`/`synthetic_fixture` and excluded from real-world forecasting. The final architecture should support both real-world validation and repeatable synthetic regression testing.

## Testing

Add/update coverage for: **provenance** (real-world eligibility, synthetic_test exclusion, unknown exclusion, provenance_verified requirement, invalid provenance handling); **dataset extraction** (only legitimate real observations enter the real dataset; synthetic pipeline and fixtures excluded); **training** (insufficient real data rejected; explicit synthetic training allowed; source labels persisted correctly); **feature engineering** (temporal ordering, no future leakage, lag/rolling correctness); **prediction** (baseline comparison, multi-step forecasting, dynamic inputs, prediction intervals); **API** (readiness, training, run retrieval, provenance in responses); **database** (migrations, constraints, indexes, cascade behavior, provenance consistency); **frontend** (real/synthetic labeling, unavailable state, API integration).

## Real-World End-to-End Verification Script

Create or update `scripts/verify_phase11_final_closure.py` — the authoritative Phase 11 final verification. It must verify the genuine real-world path, not just synthetic fixtures. Roughly: database connectivity → provenance schema → a genuine real-world source exists → provenance is verified → the video exists in the DB with `source_type = real_world` → it was processed through the real Phase 4–10 pipeline → the resulting analysis session and traffic metrics are persisted → the real observation count is calculated → `DatasetExtractor` extracts real observations while excluding synthetic ones → minimum-dataset readiness is evaluated → the feature matrix is built → temporal ordering is verified → the future-leakage experiment runs → chronological train/test split → real ML training → baseline evaluation → real-data metrics → dynamic forecast verification → prediction-interval verification → `PredictionRun` persistence → a fresh-database read confirms it → REST API verification → frontend typecheck/build → full backend regression → Phase 5–10 regression → Git/security audit. The exact check count may differ, but every requirement above must be covered, and **every result must come from actual execution.**

## Source Video Provenance Table (required in the report)

```
Video ID | Filename | Source Type | Provenance Verified | Source | License | Sessions | Observations | Eligible for ML
REAL-001 | traffic_x.mp4 | real_world | YES | verified dataset | documented | 3 | 24 | YES
SYN-001  | generated_bus.mp4 | synthetic_test | YES | OpenCV fixture | internal | 1 | 5 | NO
```

(Illustrative only — populate with real values from actual inspection, including the existing OpenCV/demo-bus-image video from Phase 11.1, which should appear as `synthetic_test`, not eligible.)

## Security Audit

Verify: no `.env`, credentials, database files, uploaded media, or secrets committed; no model weights committed unless intentionally permitted by existing policy; no unsafe path handling or path traversal; provenance fields cannot be abused to bypass ML eligibility. **Especially inspect `POST /api/v1/videos/upload`: a client must not be able to simply send `source_type=real_world` and thereby bypass provenance safeguards** — design the safest practical behavior within the current architecture (e.g., client-supplied `source_type` claims require separate verification before being trusted for ML eligibility).

## Resource / Performance Check

Measure real video processing time, ML training time, prediction inference time, and database persistence time where practical. Confirm: no per-frame database transaction, no unbounded memory growth, no unbounded prediction horizon, no unrestricted video size, no unbounded observation count, no excessive training resource usage — all consistent with existing Phase 4–10 limits.

## Regression Requirement

Run the full backend suite (`python -m pytest backend/tests -v`) — expect 0 failures. Run every existing live verification script (Phases 5 through 10, Phase 11's synthetic verification, Phase 11's real-data verification, and this phase's closure script) — don't skip earlier phases just because the changes look unrelated. Run `npm run typecheck` and `npm run build` on the frontend — both must pass.

## Git / Repository Hygiene

Review `git status`, `git diff`, `git log`. Only intentional files should be modified. Never commit `.env`, database files, uploads, temporary videos, scratch files, generated caches, secrets, or credentials. **Real-world dataset files should not be committed unless their license explicitly permits redistribution and doing so is appropriate** — prefer documenting the source and acquisition process over committing a large copyrighted dataset.

## Documentation

Update `PROJECT_STATUS.md`; `ARCHITECTURE.md` only if the architecture actually changed; `README.md` if Phase 11's status or setup instructions are stale. Document: the real-world data source, the provenance policy, the synthetic/test data policy, how to acquire legitimate real traffic footage, how to run this phase's final verification, the minimum data requirement, ML limitations, current evaluation results, the prediction-interval methodology, and the real-vs-synthetic run distinction. No exaggerated claims — if the real dataset is small, explicitly state the model is a prototype/research validation, not production-grade forecasting.

## Critical Success Condition — Do Not Force `VERIFIED`

Exactly four acceptable outcomes:

- **Outcome A — Fully Verified:** genuine real-world footage proven, provenance verified, sufficient legitimate observations, they pass quality checks, no leakage, the model genuinely trains and evaluates on held-out real data, prediction works on real data, results persist, API and frontend work, all tests pass, full Phase 1–10 regression passes, security passes, docs updated → **Phase 11 = VERIFIED.**
- **Outcome B — Real data exists but insufficient:** → **Phase 11 implementation = VERIFIED; real-world forecasting = PARTIALLY VERIFIED.** Do not fake readiness.
- **Outcome C — No legitimate real-world data can be acquired:** → **CV-to-ML pipeline = VERIFIED; synthetic prediction = VERIFIED; real-world forecasting = NOT VERIFIED; Phase 11 = PARTIALLY VERIFIED.** Explain exactly what's missing. Do not fabricate data.
- **Outcome D — A defect is discovered** (provenance, schema, API, ML, leakage, or persistence): → **Phase 11 final closure = FAILED/PARTIALLY VERIFIED.** List the defect and its evidence.

## Do Not Start Phase 12

This task ends with Phase 11. No new prediction capabilities beyond what closure requires, no signal optimization, emergency corridor simulation, advanced CV, speed estimation, autonomous lane detection, cloud deployment, authentication, or unrelated new frontend features.

## Definition of Done

Closure is complete only when the implementation and verification give an honest, evidence-backed answer to: **"Can this system currently train and evaluate a traffic prediction model using genuine real-world traffic observations?"** The system must never confuse real-world traffic with synthetic/test traffic or synthetic ML fixtures, and it must remain trustworthy even when the honest answer is "not yet."

## Completion Report

Require:

**A. Final classification** — exactly one of A/B/C/D as defined above.

**B. Provenance evidence** — per video: ID, filename, source type, source, license, provenance status, observations, ML eligibility.

**C. Real-data summary** — real videos, real sessions, real observations, temporal span, observation duration, vehicle volume.

**D. Synthetic-data summary** — synthetic-pipeline observation count, synthetic-fixture observation count, confirmation both are excluded from real ML.

**E. ML results** (only for real data, if available) — model, features, train/test counts, MAE, RMSE, R², baseline metrics, training/inference time, forecast outputs, prediction-interval method.

**F. Leakage experiment** — actual before/after feature vectors and the maximum difference.

**G. API verification** — readiness/training/run-retrieval results.

**H. Database verification** — migration and persistence results.

**I. Frontend verification** — typecheck, build, provenance display, real/synthetic separation.

**J. Regression** — backend tests, Phase 5–10 scripts, Phase 11 synthetic script, Phase 11 real-data/final script.

**K. Security** — confirmation that secrets, database files, uploads, model files, and provenance-bypass risks were checked.

**L. Files changed** — every modified/created file and why.

**M. Git** — branch, commit, `git status`, whether the working tree is clean.

**N. Known limitations** — stated explicitly, not glossed over.

**O. Phase 12 readiness** — state `READY FOR PHASE 12` only if Outcome A was achieved, or if the remaining limitation is explicitly accepted as a non-blocking research limitation. If genuine real-world forecasting remains unverified, state plainly: **NOT READY TO CLAIM REAL-WORLD FORECASTING.** Do not hide limitations.
