# ARCHITECTURE.md
## AI Smart Traffic Intelligence Platform

Status: **Design phase (Phase 1)**. Nothing described here is implemented yet unless PROJECT_STATUS.md says otherwise. This document is the source of truth for how the pieces fit together; update it whenever a real architectural decision changes.

---

## 1. System Overview

The platform turns uploaded traffic-camera video into structured traffic intelligence: counts, lane-level density, congestion assessment, short-horizon prediction, and two clearly-labeled decision-support simulations (signal timing, emergency corridor). It is explicitly **not** a "YOLO demo" — the value is the pipeline that turns detections into explainable metrics and the product layer around it.

```
                    ┌───────────────────────┐
                    │      React Frontend    │
                    │  Dashboard / Analytics │
                    └───────────┬───────────┘
                                │ REST (JSON)
                    ┌───────────▼───────────┐
                    │     FastAPI Backend    │
                    └───────────┬───────────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
       Video Service      Analytics Engine     ML Engine
             │                  │                  │
             ▼                  ▼                  ▼
       OpenCV + YOLO       Traffic Metrics      Prediction
             │
             ▼
        Object Tracker (ByteTrack/BoT-SORT)
             │
             ▼
       Lane / Flow Engine
             │
             └──────────────┬────────────────────┘
                            ▼
                     PostgreSQL Database
```

Supporting modules (not in the hot path): signal optimization, emergency corridor simulation, reporting, authentication, system configuration.

## 2. Design Principles

- **Modular over monolithic.** Each pipeline stage (`VideoSource`, `Detector`, `Tracker`, `VehicleCounter`, `LaneAnalyzer`, `TrafficMetricsEngine`) is its own class behind a small interface, so the tracker or detector can be swapped without touching business logic.
- **Config over hard-coding.** Lane polygons, counting lines, confidence thresholds, and density thresholds live in config (DB or YAML), never inline in code.
- **Honesty over completeness-theater.** Anything simulated is labeled "Simulation" in both the API response and the UI. Anything not yet measured is reported as "Not yet measured," never invented.
- **Source video stays swappable.** `VideoSource` abstracts "where frames come from" so upload → webcam → RTSP is a new adapter, not a rewrite.

## 3. Computer Vision Pipeline

```
Traffic Video → Frame Extraction → YOLO Detection → Object Tracking
   → Vehicle Classification → Lane Assignment → Line/Zone Crossing
   → Traffic Metrics → Database → Analytics Dashboard
```

Module responsibilities (`backend/app/services/cv/`):

| Module | Responsibility |
|---|---|
| `video_source.py` | Yields frames from an uploaded file today; webcam/RTSP adapters later, same interface. |
| `detector.py` | Wraps Ultralytics YOLO. Input: frame. Output: list of `(bbox, class, confidence)`. Confidence/class thresholds come from config. |
| `tracker.py` | Wraps ByteTrack Kalman/IoU behind a `Tracker` interface (`update(detections) -> tracked_objects`). Assigns/persists a track ID per vehicle across frames. |
| `vehicle_counter.py` | Counts a track only when its trajectory crosses a configured line/zone — not per-frame — so one vehicle is counted once. |
| `lane_analyzer.py` | Assigns tracked vehicle centroids (`TrackedObject.center`) to configured polygon lane regions via ray-casting with temporal persistence; computes Shoelace polygon area, deduplicated counts, class breakdowns, image-space density ($\text{veh/px}^2$), normalized density scores ($0.0-1.0$), and frame occupancies. |
| `traffic_metrics_engine.py` | Aggregates crossing output into flow rate ($N/T_{\text{obs}}$), directional distribution, discrete non-interpolated time-series volume bucketing, and transparent extrapolation flagging. |

Per-detection fields persisted: track ID, class, confidence, bounding box, frame number, timestamp, lane, direction.

## 4. Density & Congestion Scoring

Density score (0–100) is a configurable weighted combination of vehicle count, lane occupancy, queue length, average estimated speed, and flow rate. Bands are project-defined assumptions, not a traffic-engineering standard, and will be documented as such wherever they appear:

```
0–25    LOW
26–50   MODERATE
51–75   HIGH
76–100  SEVERE
```

Congestion output is explainable, not just a number — it returns the score, severity, affected lane/direction, timestamp, and a short list of contributing reasons (e.g., "queue length increasing," "reduced estimated speed").

## 5. Data Science / ML Pipeline

Research code (`data_science/notebooks/`) and production inference code (`backend/app/services/ml/`) are kept separate on purpose — notebooks are for exploration, the service module only loads a serialized, evaluated model.

```
Raw Traffic Data → Cleaning → EDA → Feature Engineering
  → Train/Val/Test Split → Baseline Models → Model Comparison
  → Evaluation → Model Selection → Serialization → Production Inference
```

- **Targets:** short-horizon (5–15 min) vehicle volume, congestion, and/or queue length — final target chosen once real data exists to support it.
- **Candidate models:** linear regression and a tree ensemble (Random Forest / XGBoost) as baselines; a time-series-appropriate model if the baseline underperforms. No model is chosen before there's a reason to prefer it.
- **3-Tier Data Provenance Model (Phase 11.2):**
  - `real_observations`: Derived exclusively from genuine recorded real-world traffic camera footage. Minimum 20 required to train real forecasting models.
  - `synthetic_pipeline`: Genuine CV pipeline (YOLO/ByteTrack/Counter/Analytics) execution on synthetic/test video clips. Validates CV-to-ML integration; explicitly rejected for real forecasting.
  - `synthetic_fixture`: Mathematically generated development fixtures with diurnal patterns for unit testing and offline development.
- **Evaluation is never invented.** Metrics reported in docs/README always come from an actual eval run logged in PROJECT_STATUS.md.

## 6. Decision-Support Simulations (explicitly not real control systems)

- **Signal optimization** (`services/simulation/`): given per-direction vehicle counts, computes a recommended green-time allocation and compares it to current timing (expected queue/wait-time change). Framed everywhere as a simulation/recommendation, never as live signal control.
- **Emergency corridor simulation**: given an emergency vehicle's origin/destination and current traffic state, proposes a route, affected intersections, and simulated signal-priority changes with an estimated travel time. Same labeling rule applies.
- **Emergency vehicle detection**: architecture exists from the start (a pluggable detector module), but if the base YOLO model can't reliably distinguish ambulance/fire truck/police from generic vehicle classes, that limitation is documented rather than faked, and the module is built to accept a future fine-tuned model.

## 7. Backend API (FastAPI)

Representative surface (full contract lives in `docs/` once implemented):

```
POST /api/v1/videos/upload
GET  /api/v1/videos
GET  /api/v1/videos/{id}
POST /api/v1/analysis/start
GET  /api/v1/analysis/{id}
GET  /api/v1/analysis/{id}/metrics
GET  /api/v1/analysis/{id}/detections
GET  /api/v1/analysis/{id}/predictions
GET  /api/v1/analysis/{id}/signal-recommendation
GET  /api/v1/analytics/summary
GET  /api/v1/analytics/history
POST /api/v1/simulation/signal
POST /api/v1/emergency/simulation
```

All request/response shapes are Pydantic models. Errors are centrally handled and return a consistent shape — no internal stack traces ever reach the client. Structured logging (not print statements) throughout.

## 8. Database Schema (PostgreSQL / SQLite via SQLAlchemy 2.0 & Alembic)

Initial schema implemented and migrated via Alembic (`0001_create_videos_table.py`, `0002_create_analysis_tables.py`):

**videos**
- `id` (String(36) UUID, PK)
- `uploaded_by` (String(36), nullable, indexed)
- `original_filename` (String(255), not null)
- `storage_path` (String(512), not null)
- `duration_seconds` (Float, not null, default 0.0)
- `fps` (Float, not null, default 0.0)
- `resolution` (String(32), not null, default '0x0')
- `frame_count` (Integer, not null, default 0)
- `source_type` (String(32), not null, default 'real_world', indexed) — `real_world` vs `synthetic_test` (Phase 11.2 provenance audit)
- `status` (String(32), not null, default 'uploaded', indexed)
- `uploaded_at` (DateTime(timezone=True), not null, indexed)

**analysis_sessions**
- `id` (String(36) UUID, PK)
- `video_id` (String(36), FK `videos.id` ON DELETE CASCADE, not null, indexed)
- `analysis_type` (String(32), not null, default 'full_pipeline', indexed)
- `status` (String(32), not null, default 'pending', indexed)
- `started_at` (DateTime(timezone=True), not null, indexed)
- `completed_at` (DateTime(timezone=True), nullable)
- `processing_time_ms` (Float, nullable)
- `total_frames_processed` (Integer, not null, default 0)
- `total_vehicles_detected` (Integer, not null, default 0)
- `total_vehicles_counted` (Integer, not null, default 0)
- `config_snapshot` (JSON, nullable — records confidence, IoU, tripwire geometry, and lane definitions)
- `error_message` (Text, nullable)
- `created_at` (DateTime(timezone=True), not null)

**traffic_metrics**
- `id` (String(36) UUID, PK)
- `analysis_session_id` (String(36), FK `analysis_sessions.id` ON DELETE CASCADE, not null, indexed)
- `observation_duration_seconds` (Float, not null, default 0.0)
- `total_volume` (Integer, not null, default 0)
- `flow_rate_per_minute` (Float, not null, default 0.0)
- `flow_rate_per_hour` (Float, not null, default 0.0)
- `is_extrapolated` (Boolean, not null, default true)
- `class_distribution` (JSON, nullable — list of `{class_name, count, percentage}`)
- `direction_distribution` (JSON, nullable — list of `{direction, count, percentage}`)
- `time_series_buckets` (JSON, nullable — list of discrete non-interpolated time bins with counts and breakdowns)
- `created_at` (DateTime(timezone=True), not null)

**lane_results**
- `id` (String(36) UUID, PK)
- `analysis_session_id` (String(36), FK `analysis_sessions.id` ON DELETE CASCADE, not null, indexed)
- `lane_id` (String(64), not null, indexed)
- `lane_name` (String(128), not null)
- `direction_hint` (String(64), nullable)
- `polygon_json` (JSON, not null — list of `[x, y]` coordinates)
- `polygon_area_px2` (Float, not null, default 0.0 — computed via Shoelace formula)
- `unique_vehicles_count` (Integer, not null, default 0)
- `peak_occupancy` (Integer, not null, default 0)
- `average_occupancy` (Float, not null, default 0.0)
- `image_space_density` (Float, not null, default 0.0 — vehicles/px²)
- `normalized_density_score` (Float, not null, default 0.0 — 0.0 to 1.0)
- `vehicle_class_counts` (JSON, nullable)
- `density_unit` (String(32), not null, default 'vehicles/px²')
- `density_calibration_warning` (String(255), nullable)
- `created_at` (DateTime(timezone=True), not null)

**crossing_events**
- `id` (String(36) UUID, PK)
- `analysis_session_id` (String(36), FK `analysis_sessions.id` ON DELETE CASCADE, not null, indexed)
- `track_id` (Integer, not null, indexed)
- `class_name` (String(32), not null)
- `direction` (String(32), not null)
- `frame_index` (Integer, not null)
- `timestamp_seconds` (Float, not null)
- `centroid_x` (Float, not null)
- `centroid_y` (Float, not null)
- `line_label` (String(64), not null, default 'main_line')
- `created_at` (DateTime(timezone=True), not null)
- **Unique Constraint:** `uq_crossing_event_session_track_line` on `(analysis_session_id, track_id, line_label)` enforcing zero duplicate crossing events at the database level.

**prediction_runs** (Phase 11)
- `id` (String(36) UUID, PK)
- `session_id` (String(36), FK `analysis_sessions.id` ON DELETE SET NULL, nullable, indexed)
- `model_type` (String(64), not null) — e.g. `random_forest`, `hist_gradient_boosting`, `ridge`, `naive_persistence`
- `data_source` (String(32), not null) — strictly labeled: `real_observations` (genuine camera video), `synthetic_pipeline` (CV pipeline output on synthetic/test video), or `synthetic_fixture` (direct fixture generator per Phase 11.2 provenance policy)
- `sample_count` (Integer, not null, default 0)
- `train_samples` (Integer, not null, default 0)
- `test_samples` (Integer, not null, default 0)
- `horizon_steps` (Integer, not null, default 3)
- `time_step_seconds` (Integer, not null, default 300)
- `mae` (Float, not null, default 0.0) — evaluated on held-out test split
- `rmse` (Float, not null, default 0.0)
- `r2_score` (Float, not null, default 0.0)
- `baseline_mae` (Float, not null, default 0.0) — naive persistence benchmark ($t = t-1$)
- `baseline_rmse` (Float, not null, default 0.0)
- `baseline_improvement_pct` (Float, not null, default 0.0)
- `feature_importance` (JSON, nullable)
- `created_at` (DateTime(timezone=True), not null)

**prediction_items** (Phase 11)
- `id` (String(36) UUID, PK)
- `prediction_run_id` (String(36), FK `prediction_runs.id` ON DELETE CASCADE, not null, indexed)
- `step` (Integer, not null) — 1, 2, 3...
- `predicted_volume` (Float, not null, default 0.0)
- `predicted_inbound` (Float, not null, default 0.0)
- `predicted_outbound` (Float, not null, default 0.0)
- `predicted_density_state` (String(32), not null, default 'medium')
- `lower_bound` (Float, not null, default 0.0) — empirical residual prediction interval lower bound
- `upper_bound` (Float, not null, default 0.0) — empirical residual prediction interval upper bound
- `forecast_horizon_seconds` (Integer, not null, default 0)
- `target_timestamp` (DateTime(timezone=True), not null)
- `created_at` (DateTime(timezone=True), not null)

Planned Future Entities (Phases 12–16):
- `users` (auth, roles)
- `signal_recommendations` (simulation recommendations)
- `emergency_events` (emergency vehicle priority logs)

Indexes on all foreign keys and temporal attributes ensure fast historical filtering and dashboard aggregations. All child tables employ `ON DELETE CASCADE` to guarantee clean relational lifecycle management.

## 9. Frontend Architecture (React + TypeScript + Vite + Tailwind)

Pages: Dashboard, Video Analysis, Traffic Analytics, Predictions, Signal Optimization, Emergency Simulation, History, Settings, System Information.

- `src/api/` — typed API client (one function per backend endpoint, no ad-hoc fetches scattered through components).
- `src/pages/` — one file per page above, composed from `src/components/`.
- `src/components/` — reusable chart wrappers (Recharts/Plotly), KPI cards, the video-annotation overlay, lane-editor widget.
- Real data by default; any demo/mocked view is explicitly labeled "Demo data" in the UI, per the no-fake-results rule.

## 10. Security Model (see SECURITY.md for the living checklist)

- Upload pipeline: extension + MIME validation, size limits, filename sanitization, path-traversal protection, isolated upload directory, uploaded files never executed, temp-file cleanup.
- Standard web risks in scope from day one: SQL injection (parameterized queries via SQLAlchemy), XSS (React escapes by default, but API responses are still sanitized/validated), CSRF where cookies are used, CORS locked to known origins (not `*`).
- Secrets: `.env` only, never committed, never sent to the frontend; `.env.example` documents the shape with placeholder values only.
- Auth: standard hashed-password + token-based auth; authorization checked per-endpoint, not just per-page in the frontend.
- Logging never includes passwords, tokens, or full request bodies with credentials.

## 11. Configuration Strategy

Runtime-tunable values (confidence thresholds, frame-skip rate, processing FPS, density weights, lane polygons, counting lines) live in the database or a config table/YAML — not scattered as magic numbers through business logic — so tuning doesn't require a code change.

## 12. Deployment

Docker Compose brings up: backend (FastAPI), frontend (static build or dev server), PostgreSQL. Dockerfiles and compose file are Phase 18 work — not created yet; see PROJECT_STATUS.md.
