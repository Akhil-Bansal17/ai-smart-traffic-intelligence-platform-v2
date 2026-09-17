# 🚦 AI Smart Traffic Intelligence Platform

> **Status: Active Development (Phases 1–19 Complete & Verified).** See `PROJECT_STATUS.md` for live test evidence, verification scripts, and provenance audits.

An AI-powered traffic intelligence and decision-support platform: computer vision (vehicle detection + multi-object tracking) feeding a traffic-analytics engine, a short-horizon prediction model, two explicitly-labeled decision-support simulations (signal timing, emergency corridor routing), an explainable decision intelligence layer, and business-grade traffic reporting and export. Built end-to-end — CV pipeline, ML pipeline, decision-support simulation, decision intelligence, reporting subsystem, REST API, database, and an interactive React frontend — not a single-notebook YOLO demo.

> **Safety & Operational Scope Disclaimer:** *This system provides traffic signal optimization, emergency corridor simulation, anomaly detection, operational recommendations, and reporting for decision support; it does not directly control physical traffic signals, emergency vehicles, or dispatch infrastructure.*

## Implemented & Verified Capabilities (Phases 1–19)

- **Video Ingestion & Validation (Phase 4):** Secure container magic-byte verification, path-traversal prevention, metadata extraction.
- **Vehicle Detection (Phase 5):** Ultralytics YOLOv8n multi-class classification (`car`, `motorcycle`, `bus`, `truck`, `bicycle`).
- **Object Tracking (Phase 6):** ByteTrack Kalman filter motion prediction + IoU association with track lifecycle states.
- **Vehicle Counting (Phase 7):** Virtual line-crossing detector with 2D cross-product transition testing and zero double-counting.
- **Traffic Flow Analytics (Phase 8):** Minute/hourly flow rates, class distributions, directional splits, discrete time-series bucketing.
- **Lane Analysis & Density (Phase 9):** Configurable 2D polygonal lane assignment, Shoelace area calculation, image-space density estimation.
- **Database Integration & Persistence (Phase 10):** Relational persistence of sessions, metrics, lane occupancy, and crossing events.
- **Short-Horizon Traffic Forecasting (Phase 11):** Non-leaking lag feature engineering, classical ML models (Random Forest, HistGradientBoosting, Ridge), empirical residual prediction intervals, and strict 3-tier data provenance tracking.
- **Traffic Signal Optimization Simulation (Phase 12):** Deterministic baseline signal plans, 3 explainable optimization algorithms (Demand-Proportional, Webster's Method, Constrained Delay Minimization), Webster delay proxy modeling ($d_1 + d_2 - d_3$), HCM Level of Service (LOS A–F), and interactive React simulation dashboard.
- **Emergency Corridor Simulation & Signal Priority (Phase 13):** Coordinated multi-intersection arterial progression, green wave preemption, queue clearance lead-time ($t_{\text{lead}} = Q \times h_d + 2$s), strict safety constraints ($g_{\text{min}} \ge 7$s, yellow clearance $\ge 3$s, all-red clearance $\ge 1$s, max priority cap $\le 80$s), cross-street delay trade-off analysis, and interactive React emergency corridor dashboard.
- **System-Wide Traffic Intelligence & Decision-Support Dashboard (Phase 14):** Unified single-roundtrip aggregation endpoint (`GET /api/v1/dashboard/summary`) with strict read-only anti-trigger protection (zero inference/simulation on page load/refresh), 10 modular React widgets, 5-state explicit provenance qualification (`REAL DATA`, `SIMULATION`, `PREDICTION`, `SYNTHETIC`, `UNAVAILABLE`), dynamic 20-sample observation bucket threshold reporting, Shoelace image-space density labeling, and full data lineage trust boundary panel.
- **Traffic Anomaly & Congestion Incident Detection (Phase 15):** Explainable statistical rule engine evaluating persisted traffic metrics across 4 transparent rules (Congestion Buildup, Abnormal Flow Drop $\ge 50\%$, Multi-Lane Imbalance $\ge 3.0$x, Image-Space Density Spike), 4-tier severity scaling (`low`, `medium`, `high`, `critical`), lifecycle management (`open`, `acknowledged`, `resolved`), parent video lineage traceability, automated CV persistence hook, and interactive `AlertsWidget` on the Command Dashboard.
- **Production Readiness & Observability Hardening (Phase 16):** Strict Pydantic v2 settings validation, deep health and readiness diagnostics (`/readiness`), bounded pagination on all list endpoints, standardized sanitized error envelopes, and cross-platform logging.
- **Analysis Job Orchestration & Real-Time Processing Foundation (Phase 17):** Non-blocking asynchronous CV execution via bounded in-process `ThreadPoolExecutor`, explicit state machine (`QUEUED` -> `RUNNING` -> `COMPLETED`/`FAILED`/`CANCELLED`), token-based cooperative cancellation in tracker loops, honest frame-level progress tracking with indeterminate handling, startup stale-job recovery (`process_restarted_stale_job`), idempotency conflict protection (HTTP 409 `duplicate_active_job`), and full frontend live job monitoring and cancellation.
- **Intelligent Traffic Insights & Explainable Decision Intelligence (Phase 18):** Deterministic synthesis layer evaluating persisted traffic data across 7 categories (`CONGESTION`, `FLOW_DEGRADATION`, `LANE_IMBALANCE`, `DENSITY_SPIKE`, `TRAFFIC_SURGE`, `UNDERUTILIZED_LANE`, `OPERATIONAL_RECOMMENDATION`), strict epistemic separation (`Observed:` empirical measurements vs `Inferred:` deductive reasoning with confidence ratings), honest evidence packages (simulation flags, $N < 20$ sample ML threshold declarations, uncalibrated 2D pixel-space caveats), non-actuating advisory recommendations, deterministic deduplication hashing (`dedup_signature`), state lifecycle tracking (`NEW` -> `ACTIVE` -> `RECOVERED` -> `DISMISSED`), and interactive dashboard widget with full evidence drawer.
- **Business-Grade Traffic Reporting & Export (Phase 19):** Structured, reproducible, downloadable reports in printable vector PDF (pure-Python ReportLab 5.0.1 with `NumberedCanvas` "Page X of Y", dark theme headers, color-coded badges, limitation disclaimers) and clean RFC 4180 CSV for single analysis sessions and bounded historical time ranges ($\le 30$ days), zero metric recalculation invariant, mandatory 6-state truth labeling taxonomy (`OBSERVED`, `INFERRED`, `PREDICTED`, `SIMULATED`, `RECOMMENDED/ADVISORY`, `UNAVAILABLE`), path-traversal security, and dedicated Reports page with live modal preview.

## Planned Capabilities (Phase 20)

- Docker Compose containerization, portfolio documentation & presentation (Phase 20)

## Tech Stack

| Layer | Tools |
|---|---|
| Computer Vision | Python, OpenCV, Ultralytics YOLO, ByteTrack/BoT-SORT |
| Data Science | Pandas, NumPy, scikit-learn, XGBoost, Matplotlib/Plotly |
| Backend | FastAPI, Pydantic, SQLAlchemy, PostgreSQL |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Recharts/Plotly |
| Infra | Docker, Docker Compose, Git |

## Repository Layout

```
backend/         FastAPI app: api, core, models, schemas, services (cv/ml/simulation), db, config
frontend/        React + TypeScript app: pages, components, api client
data_science/    Notebooks, training scripts, serialized models (research code, kept separate from production inference)
docs/            Additional documentation as it's produced
prompts/         Full reusable prompt library for continuing this project across sessions — start here
scripts/         One-off / operational scripts
tests/           Integration tests (unit tests live alongside backend/frontend code)
```

## Key Documents

- **`ARCHITECTURE.md`** — full system design: pipeline, database schema, API surface, security model.
- **`PROJECT_STATUS.md`** — exactly where the project stands right now; read this before doing anything else.
- **`prompts/README.md`** — how to use the prompt library to resume, extend, audit, or document this project in a future session.
- **`SECURITY.md`** — security practices and current hardening status.

## Getting Started & Local Development

### Prerequisites

- **Python**: 3.10+ (tested on Python 3.14)
- **Node.js**: 18+ (tested on Node 22 / 24, npm 10 / 11)
- **Database**: SQLite (default zero-config for local development) or PostgreSQL 16+
- **Git**

---

### Step 1: Environment Configuration

Copy the example environment configuration file to `.env`:

```bash
cp .env.example .env
```

For zero-config local development, SQLite is preconfigured out-of-the-box. To use PostgreSQL, update `DATABASE_URL` in `.env`:

```ini
DATABASE_URL=postgresql://traffic_user:changeme@localhost:5432/traffic_platform
```

---

### Step 2: Backend Setup & Database Migrations

1. **Install backend dependencies:**

   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Apply database schema migrations (Alembic):**

   ```bash
   cd backend
   alembic upgrade head
   cd ..
   ```

3. **Start the FastAPI development server:**

   ```bash
   uvicorn app.main:app --reload --app-dir backend --port 8000
   ```

   The backend will be available at:
   - **API Root / Health:** `http://localhost:8000/health`
   - **Readiness Diagnostic:** `http://localhost:8000/readiness`
   - **Interactive OpenAPI / Swagger Docs:** `http://localhost:8000/docs`
   - **ReDoc Documentation:** `http://localhost:8000/redoc`

---

### Step 3: Frontend Setup & Development

1. **Install frontend dependencies:**

   ```bash
   cd frontend
   npm install
   ```

2. **Start the Vite development server:**

   ```bash
   npm run dev
   ```

   The frontend dashboard will be available at `http://localhost:5173`.

3. **Build & Typecheck verification:**

   ```bash
   npm run typecheck    # Strict TypeScript verification (tsc --noEmit)
   npm run build        # Production bundle build (vite build)
   ```

---

### Step 4: Running Tests & Verification Suites

- **Run all backend pytest suites (200 tests):**

  ```bash
  cd backend
  python -m pytest tests
  cd ..
  ```

- **Run standalone phase verification scripts:**

  ```bash
  # Standalone end-to-end Decision Intelligence verification (Phase 18)
  python scripts/verify_phase18_decision_intelligence.py

  # Standalone Async Analysis Job Orchestration verification (Phase 17)
  python scripts/verify_phase17_job_orchestration.py

  # Standalone Production Readiness & Diagnostic verification (Phase 16)
  python scripts/verify_phase16_production_readiness.py

  # Standalone Anomaly & Congestion Detection verification (Phase 15)
  python scripts/verify_phase15_anomaly_detection.py

  # Standalone Command Dashboard verification (Phase 14)
  python scripts/verify_phase14_dashboard.py
  ```

---

## API Surface Overview

All REST API endpoints are versioned under `/api/v1` (with root-level unversioned infrastructure health endpoints):

| Category | Endpoint | Method | Description |
|---|---|---|---|
| **System** | `/health` | `GET` | Unversioned liveness check for load balancers and containers |
| | `/readiness` | `GET` | Deep diagnostic probe verifying database, storage, and model weights |
| | `/api/v1/health` | `GET` | Versioned API subsystem health report |
| **Video Ingestion** | `/api/v1/videos/upload` | `POST` | Validated video upload with magic-byte check and path sanitation |
| | `/api/v1/videos` | `GET` | Paginated listing of ingested video records |
| | `/api/v1/videos/{id}` | `GET` | Detailed metadata for a specific video |
| **Computer Vision** | `/api/v1/detection/videos/{id}` | `POST` | YOLOv8n multi-class vehicle detection |
| | `/api/v1/tracking/videos/{id}` | `POST` | ByteTrack Kalman-filter multi-object tracking |
| | `/api/v1/counting/videos/{id}` | `POST` | Directional virtual line-crossing vehicle count |
| | `/api/v1/analytics/videos/{id}` | `POST` | Flow rate, class distribution, and time-series bucketing |
| | `/api/v1/lane-analysis/videos/{id}` | `POST` | 2D polygon lane occupancy and image-space density |
| **Analysis Sessions** | `/api/v1/analysis/videos/{id}/run` | `POST` | Execute full CV pipeline synchronously and persist session |
| | `/api/v1/analysis/sessions` | `GET` | Paginated query of historical analysis sessions |
| | `/api/v1/analysis/sessions/{id}` | `GET` | Full session detail with metrics, lane polygons, and crossing logs |
| **Job Orchestration** | `/api/v1/analysis/jobs` | `POST` | Enqueue non-blocking background CV analysis job |
| | `/api/v1/analysis/jobs` | `GET` | List active and historical analysis jobs with live progress |
| | `/api/v1/analysis/jobs/{id}` | `GET` | Real-time job status, stage, and frame-level progress |
| | `/api/v1/analysis/jobs/{id}/cancel` | `POST` | Cooperatively cancel an in-progress analysis job |
| **ML Forecasting** | `/api/v1/predictions/readiness` | `GET` | 3-tier data provenance readiness check ($N \ge 20$ sample threshold) |
| | `/api/v1/predictions/train` | `POST` | Train forecasting model (Random Forest, HistGradientBoosting, Ridge) |
| | `/api/v1/predictions/runs` | `GET` | List historical forecasting runs |
| | `/api/v1/predictions/runs/{id}` | `GET` | Multi-step forecast trajectory with empirical residual intervals |
| **Signal Simulation** | `/api/v1/signal-optimization/presets` | `GET` | Preconfigured intersection topologies and demand scenarios |
| | `/api/v1/signal-optimization/simulate` | `POST` | Fixed-time baseline vs Webster/Delay-optimized signal timing simulation |
| | `/api/v1/signal-optimization/runs` | `GET` | Historical signal simulation runs and Level of Service (LOS) records |
| **Emergency Priority** | `/api/v1/emergency-corridor/presets` | `GET` | Preconfigured arterial corridors and emergency vehicle scenarios |
| | `/api/v1/emergency-corridor/simulate` | `POST` | Coordinated green wave arterial priority simulation with safety caps |
| | `/api/v1/emergency-corridor/runs` | `GET` | Historical corridor simulation runs and delay trade-off records |
| **Command Dashboard** | `/api/v1/dashboard/summary` | `GET` | Unified read-only single-roundtrip system intelligence aggregation |
| **Anomaly Detection** | `/api/v1/anomalies` | `GET` | Query traffic anomaly and congestion incident events |
| | `/api/v1/anomalies/{id}/status` | `PATCH` | Update incident lifecycle state (`open`, `acknowledged`, `resolved`) |
| **Decision Intelligence** | `/api/v1/insights/generate` | `POST` | Evaluate 7 deterministic rule categories and synthesize insights |
| | `/api/v1/insights` | `GET` | List insights with epistemic separation (`Observed:` vs `Inferred:`) |
| | `/api/v1/insights/{id}` | `GET` | Detailed insight package with full evidence and advisory recommendations |
| | `/api/v1/insights/{id}/status` | `PATCH` | Transition lifecycle state (`NEW` -> `ACTIVE` -> `RECOVERED` -> `DISMISSED`) |

---

## Developer Troubleshooting & Environment Notes

- **PyTorch / YOLO CPU Execution:**
  By default, `YOLO_DEVICE=cpu` is set in `.env.example` for universal compatibility without requiring a dedicated CUDA GPU.
- **Data Provenance & ML Boundary:**
  In compliance with Phase 11 trust boundaries, forecasting models require at least 20 genuine real-world observations before training on real data. When fewer samples exist, the readiness API transparently declares `is_ready=False` and offers explicit developer fixture fallback options.
- **Simulation Transparency:**
  All signal optimization and emergency corridor metrics are generated within validated decision-support simulation engines and explicitly tagged `is_simulation=True`. They do not actuate physical hardware.
- **Windows UTF-8 Encoding:**
  When executing verification scripts directly on Windows PowerShell, ensure console UTF-8 support (handled automatically in Python scripts via `sys.stdout.reconfigure(encoding="utf-8")`).

## A Note on Honesty

This project follows a strict no-fake-results rule: unmeasured numbers are reported as "Not yet measured," simulated features are labeled "Simulation," and planned-but-unbuilt features are labeled "Planned." That rule applies to this README too.
