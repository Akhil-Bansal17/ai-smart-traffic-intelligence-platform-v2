# ARCHITECTURE.md
## AI Smart Traffic Intelligence Platform

Status: **Phases 1–13 Complete & Verified**. This document is the source of truth for how the pieces fit together; update it whenever a real architectural decision changes.

> **Decision Support Disclaimer:** *This system provides traffic signal optimization and emergency corridor simulation for decision support; it does not directly control physical traffic signals, emergency vehicles, or dispatch infrastructure.*

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
- **3-Tier Data Provenance Model (Phase 11.2 & Phase 11 Final Closure):**
  - `real_observations`: Derived exclusively from genuine recorded real-world traffic camera footage with verified provenance (`source_type = 'real_world'`, `provenance_verified = True`, `source_reference != None`). Minimum 20 required to train real forecasting models.
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

Schema managed via Alembic migrations (`0001` through `0005_harden_video_provenance_fields.py`):

**videos**
- `id` (String(36) UUID, PK)
- `uploaded_by` (String(36), nullable, indexed)
- `original_filename` (String(255), not null)
- `storage_path` (String(512), not null)
- `duration_seconds` (Float, not null, default 0.0)
- `fps` (Float, not null, default 0.0)
- `resolution` (String(32), not null, default '0x0')
- `frame_count` (Integer, not null, default 0)
- `source_type` (String(32), not null, default 'unknown', indexed) — `real_world`, `synthetic_test`, or `unknown`
- `source_reference` (String(255), nullable) — direct URL or repository commit identifier
- `license_reference` (String(255), nullable) — open source license (e.g. MIT, CC-BY-4.0)
- `provenance_note` (String(512), nullable) — detailed description of recording context
- `provenance_verified` (Boolean, not null, default False, indexed) — cryptographic/audited provenance verification flag
- `captured_at` (DateTime(timezone=True), nullable) — timestamp when footage was recorded
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

**signal_simulation_runs** (Phase 12)
- `id` (String(36) UUID, PK)
- `analysis_session_id` (String(36), FK `analysis_sessions.id` ON DELETE SET NULL, nullable, indexed)
- `intersection_id` (String(64), not null)
- `intersection_name` (String(128), not null)
- `algorithm_used` (String(64), not null, indexed) — `demand_proportional`, `webster_optimal`, or `constrained_delay_min`
- `data_source` (String(64), not null) — strictly labeled: `real_database_metrics`, `synthetic_pipeline_metrics`, `simulation_configured`, or `synthetic_fixture`
- `baseline_cycle_length` (Float, not null, default 0.0)
- `optimized_cycle_length` (Float, not null, default 0.0)
- `baseline_avg_delay_seconds` (Float, not null, default 0.0)
- `optimized_avg_delay_seconds` (Float, not null, default 0.0)
- `delay_reduction_pct` (Float, not null, default 0.0)
- `baseline_max_queue_vehicles` (Float, not null, default 0.0)
- `optimized_max_queue_vehicles` (Float, not null, default 0.0)
- `queue_reduction_pct` (Float, not null, default 0.0)
- `baseline_throughput_vph` (Float, not null, default 0.0)
- `optimized_throughput_vph` (Float, not null, default 0.0)
- `throughput_increase_pct` (Float, not null, default 0.0)
- `baseline_los` (String(8), not null, default 'LOS_D')
- `optimized_los` (String(8), not null, default 'LOS_C')
- `simulation_duration_minutes` (Float, not null, default 60.0)
- `is_simulation` (Boolean, not null, default True)
- `simulation_notes` (Text, nullable)
- `intersection_config_snapshot` (JSON, nullable)
- `baseline_plan_snapshot` (JSON, nullable)
- `optimized_plan_snapshot` (JSON, nullable)
- `approach_performance_snapshot` (JSON, nullable)
- `created_at` (DateTime(timezone=True), not null, indexed)

**emergency_corridor_simulations** (Phase 13)
- `id` (String(36) UUID, PK)
- `session_id` (String(36), FK `analysis_sessions.id` ON DELETE SET NULL, nullable, indexed)
- `corridor_id` (String(64), not null)
- `corridor_name` (String(128), not null)
- `total_distance_meters` (Float, not null, default 0.0)
- `node_count` (Integer, not null, default 0)
- `vehicle_type` (String(32), not null) — `ambulance`, `fire_engine`, `police_interceptor`
- `desired_speed_kmh` (Float, not null, default 60.0)
- `priority_strategy` (String(64), not null, default 'dynamic_progression')
- `data_source` (String(64), not null) — strictly labeled: `real_database_metrics`, `synthetic_pipeline_metrics`, `simulation_configured`, or `synthetic_fixture`
- `baseline_travel_time_seconds` (Float, not null, default 0.0)
- `priority_travel_time_seconds` (Float, not null, default 0.0)
- `travel_time_savings_seconds` (Float, not null, default 0.0)
- `travel_time_savings_pct` (Float, not null, default 0.0)
- `baseline_corridor_speed_kmh` (Float, not null, default 0.0)
- `priority_corridor_speed_kmh` (Float, not null, default 0.0)
- `total_signals_encountered` (Integer, not null, default 0)
- `green_lights_passed` (Integer, not null, default 0)
- `total_stops_baseline` (Integer, not null, default 0)
- `total_stops_priority` (Integer, not null, default 0)
- `stops_reduced` (Integer, not null, default 0)
- `cross_street_extra_delay_sec` (Float, not null, default 0.0)
- `recovery_time_seconds` (Float, not null, default 0.0)
- `corridor_config_snapshot` (JSON, nullable)
- `vehicle_config_snapshot` (JSON, nullable)
- `node_timelines_snapshot` (JSON, nullable)
- `performance_metrics_snapshot` (JSON, nullable)
- `safety_validation_flags` (JSON, nullable)
- `simulation_notes` (Text, nullable)
- `is_simulation` (Boolean, not null, default True)
- `created_at` (DateTime(timezone=True), not null, indexed)

Planned Future Entities (Phases 14–16):
- `users` (auth, roles)
- `historical_aggregations` (rollups, trends)

Indexes on all foreign keys and temporal attributes ensure fast historical filtering and dashboard aggregations. All child tables employ `ON DELETE CASCADE` (or `ON DELETE SET NULL` for decoupled simulation runs) to guarantee clean relational lifecycle management.

## 8.1. Signal Optimization Simulation Architecture (Phase 12)

The Signal Optimization Simulation module is a decision-support and traffic-engineering analytical engine that models signal timings, computes baseline versus optimized phase allocations, and calculates standard transportation engineering performance metrics.

> **Operational Scope Disclaimer:** *This system provides traffic signal optimization simulation and decision support; it does not directly control physical traffic signals.*

### Components (`backend/app/services/simulation/`):
- `models.py`: Strongly typed dataclasses for `IntersectionConfig`, `ApproachConfig`, `ApproachDemand`, `SignalPhaseConfig`, `PhaseTiming`, `SignalPlan`, `SimulationMetrics`, and HCM Level of Service (`LOS A–F`).
- `baseline.py`: Deterministic un-actuated fixed-time baseline distributing green time equally across all configured phases with exact cycle length and clearance preservation.
- `optimizer.py`: 3 explainable algorithms:
  1. **Demand-Proportional Green Split**: Allocates green time in proportion to critical approach flow ratios $y_i = q_i / S_i$.
  2. **Webster's Minimum-Delay Optimal Cycle & Split**: Computes minimum-delay cycle length $C_0 = \frac{1.5L + 5}{1 - Y}$ and splits green times $g_i = \frac{y_i}{Y}(C_0 - L)$.
  3. **Constrained Delay Minimization Search**: Bounded parameter search minimizing aggregate intersection delay under strict safety bounds.
- `objective.py`: Webster delay proxy formula ($d = d_1 + d_2 - d_3$), Akçelik / HCM oversaturation transition, queue length proxy, capacity throughput, and percentage deltas.
- `presets.py`: 3 standard intersection topologies (4-Way Standard, 4-Way Dual Lane, 3-Way T-Junction) and 5 demand scenarios (Balanced, NS Rush, EW Surge, Asymmetric Bottleneck, Night Low-Volume).
- `data_bridge.py`: Bridges persisted `AnalysisSession` metrics to intersection approaches with 4-way provenance tagging (`real_database_metrics`, `synthetic_pipeline_metrics`, `simulation_configured`, `synthetic_fixture`) and transparent synthetic expansion for unobserved approaches.
- `engine.py`: `SignalSimulationEngine` orchestrating baseline computation, optimization, delta comparison, explainability notes generation, and DB run persistence.

## 8.2. Emergency Corridor Simulation & Signal Priority Architecture (Phase 13)

The Emergency Corridor Simulation module models coordinated arterial signal progression, green wave preemption, and queue clearance for emergency response vehicles across multi-intersection corridors.

> **Operational Scope Disclaimer:** *This system provides emergency corridor simulation and decision support; it does not control physical traffic signals, emergency vehicles, or emergency infrastructure.*

### Components (`backend/app/services/corridor/`):
- `models.py`: Strongly typed dataclasses for `CorridorNodeConfig`, `EmergencyVehicleConfig`, `CorridorConfig`, `PriorityWindow`, `NodeSimulationTimeline`, `CorridorPerformanceMetrics`, and `CorridorSimulationResult`.
- `strategy.py`: `SignalPriorityStrategyEngine` modeling:
  - **Queue Clearance Lead-Time**: $t_{\text{lead}} = Q \times h_d + 2.0\text{s}$, clearing standing queues prior to EV arrival.
  - **Progression Wave**: Computes dynamic ETA at each node $i$: $t_{\text{arrival}, i} = t_{\text{arrival}, i-1} + \frac{d_{i-1, i}}{v_{\text{cruise}}} + \Delta t_{\text{delay}}$.
  - **Priority Window Calculation**: Strategy determines whether green extension, early green / red truncation, or full preemption is required.
  - **Strict Safety Constraint Enforcement**:
    - Minimum green constraint: $g_{\text{min}} \ge 7.0\text{s}$ for all phases.
    - Yellow clearance interval: $y \ge 3.0\text{s}$.
    - All-red clearance interval: $r_{\text{all}} \ge 1.0\text{s}$.
    - Maximum priority hold cap: $\le 80.0\text{s}$ to prevent endless arterial starvation.
    - Conflict-free phase transition: cross-street phases must clear safely before emergency green is served.
  - **Phase-Safe Recovery Compensation**: Post-priority cycle compensates cross-street phases truncated during priority window.
- `engine.py`: `EmergencyCorridorSimulationEngine` running multi-node baseline and priority timeline progression, calculating EV transit delays, cross-street penalty delays, and storing simulation results.
- `presets.py`: 3 corridor presets (3-node Medical Emergency Arterial, 4-node Downtown Fire Response Corridor, 2-node Express Police Bypass) and 3 vehicle presets (Ambulance, Fire Engine, Police Interceptor).
- `data_bridge.py`: `CorridorDataBridge` bridging live/recorded database sessions to corridor nodes with strict provenance segregation.
- `corridor_simulation.py`: SQLAlchemy ORM entity `EmergencyCorridorSimulationRun` and Alembic migration `0007_create_emergency_corridor_tables.py`.

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
