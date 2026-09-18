# 🚦 AI Smart Traffic Intelligence Platform

> **Status: Production Packaged & Verified (Phases 1–20 Complete).** See [`PROJECT_STATUS.md`](file:///c:/Users/Akhil/Downloads/ai-smart-traffic-intelligence-platform%203/ai-smart-traffic-intelligence-platform/PROJECT_STATUS.md) for live test evidence, 212 passed backend unit/integration tests, 16/16 Phase 20 verification checks, and complete subsystem test results.

An end-to-end AI-powered traffic intelligence and decision-support platform: computer vision (YOLOv8 vehicle detection + ByteTrack multi-object tracking) feeding a traffic-analytics engine, an explainable ML prediction service, two explicitly-labeled decision-support simulations (signal timing optimization, emergency corridor routing), an explainable decision intelligence layer, and business-grade traffic reporting in vector PDF and CSV formats. Built end-to-end as a modular monolith with FastAPI, PostgreSQL/SQLite, and a dark-mode React/TypeScript frontend — not a single-notebook demo.

> **Safety & Operational Scope Disclaimer:** *This system provides traffic analytics, signal timing optimization simulations, emergency corridor simulations, anomaly detection, operational recommendations, and reporting purely for decision support; it does not directly control physical traffic signals, emergency vehicles, or municipal dispatch infrastructure.*

---

## 🏗️ System Architecture & End-to-End Data Flow

```
+---------------------------------------------------------------------------------------------------+
|                                       END-TO-END DATA FLOW                                        |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
                                     [ 1. VIDEO INGESTION ]
                                (Container Magic-Byte Check,
                                  Path Sanitization, 500MB)
                                                  │
                                                  ▼
                                      [ 2. YOLOv8n DETECTION ]
                                  (CPU Inference, 5 Vehicle
                                    Classes, Clamped BBoxes)
                                                  │
                                                  ▼
                                      [ 3. ByteTrack TRACKING ]
                                 (8-State Kalman Filter, IoU
                                   Association, Track States)
                                                  │
                                                  ▼
                                      [ 4. VEHICLE COUNTING ]
                                  (2D Signed Cross-Product
                                   Virtual Tripwire Crossing)
                                                  │
                                                  ▼
                                    [ 5. TRAFFIC FLOW & LANES ]
                                 (Flow Rates, Direction Splits,
                                  Shoelace Lane Density, Area)
                                                  │
                                                  ▼
                                   [ 6. ATOMIC DB PERSISTENCE ]
                                 (AnalysisSession, LaneResults,
                                  CrossingEvents, VideoRecord)
                                                  │
               ┌──────────────────────────────────┴──────────────────────────────────┐
               ▼                                                                     ▼
   [ 7. ANOMALY & INCIDENT ]                                             [ 8. DECISION INTELLIGENCE ]
 (Congestion Buildup, Flow Drop,                                         (7 Rule Synthesis, Evidence,
  Lane Imbalance, Density Spike)                                          Severity, Epistemic Labels)
               │                                                                     │
               ├──────────────────────────────────┬──────────────────────────────────┤
               ▼                                  ▼                                  ▼
    [ 9. ML FORECASTING ]              [ 10. SIMULATION ENGINES ]           [ 11. REPORTING ENGINE ]
 (Lag Features, Random Forest,       (Webster/HCM Delay Optimization,    (Pure-Python ReportLab PDF,
  Honest N < 20 Threshold Label)      Emergency Green-Wave Priority)      RFC 4180 CSV, Zero Recalc)
               │                                  │                                  │
               └──────────────────────────────────┼──────────────────────────────────┘
                                                  │
                                                  ▼
                                    [ 12. OPERATIONAL INTERFACES ]
                                 (FastAPI REST Endpoints, OpenAPI Docs,
                                  Dark-Mode React Command Dashboard)
```

---

## 🌟 Implemented & Verified Capabilities (Phases 1–20)

- **Video Ingestion & Validation (Phase 4):** Secure container magic-byte verification (ISO BMFF `ftyp`, `RIFF...AVI`, QuickTime), path-traversal prevention, streaming upload validation, and automatic temporary file cleanup.
- **Vehicle Detection (Phase 5):** Ultralytics YOLOv8n multi-class classification (`car`, `motorcycle`, `bus`, `truck`, `bicycle`) running offline on CPU with bounded coordinates.
- **Object Tracking (Phase 6):** ByteTrack 8-state Kalman filter motion prediction + two-stage IoU association with track lifecycle states (`NEW` -> `ACTIVE` -> `LOST` -> `TERMINATED`).
- **Vehicle Counting (Phase 7):** Virtual line-crossing detector with 2D cross-product transition testing and persistent track-ID deduplication (zero double-counting).
- **Traffic Flow Analytics (Phase 8):** Minute/hourly flow rates, class distributions, directional splits, and discrete time-series bucketing.
- **Lane Analysis & Density (Phase 9):** Configurable 2D polygonal lane assignment, Shoelace area calculation, and image-space density estimation with calibration disclaimers.
- **Database Integration & Persistence (Phase 10):** Relational persistence of sessions, metrics, lane occupancy, and crossing events with cascading cleanup.
- **Short-Horizon Traffic Forecasting (Phase 11):** Non-leaking lag feature engineering, classical ML models (Random Forest, HistGradientBoosting, Ridge), empirical residual prediction intervals, and transparent handling of training observation thresholds ($N < 20$).
- **Traffic Signal Optimization Simulation (Phase 12):** Deterministic baseline signal plans, 3 explainable optimization algorithms (Demand-Proportional, Webster's Method, Constrained Delay Minimization), Webster delay proxy modeling ($d_1 + d_2 - d_3$), and HCM Level of Service (LOS A–F).
- **Emergency Corridor Simulation & Signal Priority (Phase 13):** Coordinated multi-intersection arterial progression, green wave preemption, queue clearance lead-time ($t_{\text{lead}} = Q \times h_d + 2$s), strict safety constraints ($g_{\text{min}} \ge 7$s, yellow $\ge 3$s, all-red $\ge 1$s, max priority cap $\le 80$s), and cross-street delay trade-off analysis.
- **System-Wide Command Dashboard (Phase 14):** Unified aggregation endpoint (`GET /api/v1/dashboard/summary`) with strict read-only anti-trigger protection (zero inference/simulation on page load/refresh), 10 modular React widgets, 5-state explicit provenance qualification (`REAL DATA`, `SIMULATION`, `PREDICTION`, `SYNTHETIC`, `UNAVAILABLE`), and full data lineage trust boundary panel.
- **Traffic Anomaly & Congestion Incident Detection (Phase 15):** Explainable statistical rule engine evaluating persisted traffic metrics across 4 transparent rules (Congestion Buildup, Abnormal Flow Drop $\ge 50\%$, Multi-Lane Imbalance $\ge 3.0$x, Image-Space Density Spike), 4-tier severity scaling (`low`, `medium`, `high`, `critical`), and automated CV persistence hook.
- **Production Readiness & Observability Hardening (Phase 16):** Strict Pydantic v2 settings validation, deep health and readiness diagnostics (`/readiness`), bounded pagination on all list endpoints, standardized sanitized error envelopes, and cross-platform logging.
- **Analysis Job Orchestration (Phase 17):** Non-blocking asynchronous CV execution via bounded in-process `ThreadPoolExecutor`, explicit state machine (`QUEUED` -> `RUNNING` -> `COMPLETED`/`FAILED`/`CANCELLED`), token-based cooperative cancellation in tracker loops, honest frame-level progress tracking with indeterminate handling, startup stale-job recovery (`process_restarted_stale_job`), and idempotency conflict protection (HTTP 409 `duplicate_active_job`).
- **Intelligent Traffic Insights & Explainable Decision Intelligence (Phase 18):** Deterministic synthesis layer evaluating persisted traffic data across 7 categories (`CONGESTION`, `FLOW_DEGRADATION`, `LANE_IMBALANCE`, `DENSITY_SPIKE`, `TRAFFIC_SURGE`, `UNDERUTILIZED_LANE`, `OPERATIONAL_RECOMMENDATION`), strict epistemic separation (`Observed:` empirical measurements vs `Inferred:` deductive reasoning with confidence ratings), honest evidence packages (simulation flags, $N < 20$ sample ML threshold declarations, uncalibrated 2D pixel-space caveats), non-actuating advisory recommendations, deterministic deduplication hashing (`dedup_signature`), and state lifecycle tracking.
- **Business-Grade Traffic Reporting & Export (Phase 19):** Structured, reproducible, downloadable reports in printable vector PDF (pure-Python ReportLab with `NumberedCanvas` "Page X of Y", dark theme headers, color-coded badges, limitation disclaimers) and clean RFC 4180 CSV for single analysis sessions and bounded historical time ranges ($\le 30$ days), zero metric recalculation invariant, mandatory 6-state truth labeling taxonomy (`OBSERVED`, `INFERRED`, `PREDICTED`, `SIMULATED`, `RECOMMENDED/ADVISORY`, `UNAVAILABLE`), and path-traversal security.
- **Production Packaging & Deployment Readiness (Phase 20):** Multi-stage containerization (`backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`), CI workflow (`.github/workflows/ci.yml`), environment configuration auditing, and comprehensive 16-point automated verification suite.

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Computer Vision** | Python 3.11+, OpenCV Headless, Ultralytics YOLOv8n, ByteTrack |
| **Machine Learning** | scikit-learn, NumPy, Pandas |
| **Backend Framework** | FastAPI, Pydantic v2, Pydantic-Settings, Uvicorn, SQLAlchemy 2.0, Alembic |
| **Database** | PostgreSQL 16 (production/Docker) / SQLite (zero-config development & testing) |
| **Reporting & Export** | ReportLab 5 (Vector PDF with NumberedCanvas), Python CSV (RFC 4180) |
| **Frontend Framework** | React 18, TypeScript, Vite 5, Tailwind CSS, Lucide React, React Router 6 |
| **Web Server / Proxy** | Nginx (Alpine) with SPA routing fallback & backend API reverse proxy |
| **Containerization** | Docker, Docker Compose (Multi-stage builds, non-root users, health checks) |
| **CI / Automation** | GitHub Actions (backend pytest on Python 3.11 + frontend typecheck and build on Node 20) |

---

## 🚀 Quick Start & Deployment Options

### Option A: Docker Compose (Recommended for Containerized Run)

1. **Clone the repository and prepare the environment:**

   ```bash
   git clone https://github.com/Akhil-Bansal17/ai-smart-traffic-intelligence-platform-v2.git
   cd ai-smart-traffic-intelligence-platform-v2
   cp .env.example .env
   ```

2. **Start the single-node stack with Docker Compose:**

   ```bash
   docker compose up --build -d
   ```

3. **Access the application:**
   - **Web Dashboard:** [http://localhost](http://localhost) (or [http://localhost:80](http://localhost:80))
   - **Backend API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Probe:** [http://localhost:8000/health](http://localhost:8000/health)
   - **Readiness Diagnostics:** [http://localhost:8000/readiness](http://localhost:8000/readiness)

4. **Stop the stack:**

   ```bash
   docker compose down
   ```

---

### Option B: Local Development Setup

#### Prerequisites
- **Python**: 3.10+ (tested on Python 3.11–3.14)
- **Node.js**: 18+ (tested on Node 20 / 22)
- **Database**: SQLite (built-in zero configuration) or PostgreSQL 16+

#### 1. Configure Environment
```bash
cp .env.example .env
```

#### 2. Backend Setup & Database Migration
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run migrations
cd backend
alembic upgrade head
cd ..

# Start backend dev server
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

#### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 📖 Interactive Platform Walkthrough / Demo Guide

To demonstrate the full end-to-end traffic intelligence pipeline:

1. **Check System Health:**
   - Visit `http://localhost:8000/health` (liveness: 200 OK) and `http://localhost:8000/readiness` (diagnostics: database, storage, YOLO model weights, configuration).
2. **Ingest a Traffic Video:**
   - Navigate to **Video Ingestion** in the dashboard, upload a traffic video (`.mp4`, `.avi`, `.mov`).
3. **Trigger Asynchronous Analysis Job:**
   - Go to **Analysis Jobs**, create a new job selecting the uploaded video. Monitor the real-time frame progress bar and state transitions (`QUEUED` -> `RUNNING` -> `COMPLETED`).
4. **Inspect Traffic Analytics & Lane Metrics:**
   - Review volume counts, flow rates (veh/hr), directional distribution, and 2D polygonal lane utilization on the **Analytics** and **Lane Analysis** pages.
5. **Review Detected Anomalies & Incident Alerts:**
   - Open **Anomaly Detection** or view the `AlertsWidget` on the Command Dashboard to inspect congestion buildups, acute flow drops, or lane imbalances.
6. **Examine Explainable Decision Intelligence Insights:**
   - Open **Decision Intelligence** to view synthesized insights with explicit `Observed:` vs `Inferred:` evidence, confidence ratings, and advisory recommendations.
7. **Run Decision-Support Simulations:**
   - Open **Signal Optimization** to run Webster/HCM signal timing simulations.
   - Open **Emergency Corridor** to simulate emergency vehicle arterial priority progression and trade-off analysis.
8. **Generate & Download Business-Grade Reports:**
   - Navigate to **Reports**, generate a report for the analysis session or date range, preview in the UI, and download vector **PDF** or tabular **CSV**.

---

## 🧪 Comprehensive Testing & Verification

The platform maintains automated test and verification coverage with zero regressions:

```bash
# 1. Run full backend pytest suite (212 tests)
python -m pytest backend/tests -v

# 2. Run Phase 20 Production Readiness & Packaging Verification (16 checks)
python scripts/verify_phase20_production_readiness.py

# 3. Run individual phase verification scripts
python scripts/verify_phase10_database.py
python scripts/verify_phase15_anomaly_detection.py
python scripts/verify_phase16_production_readiness.py
python scripts/verify_phase17_job_orchestration.py
python scripts/verify_phase18_decision_intelligence.py
python scripts/verify_phase19_reporting.py

# 4. Run frontend TypeScript typecheck and production build
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

---

## 🔒 Security, Trust Boundaries & Honest Limitations

1. **Epistemic Truth Separation:** The platform strictly differentiates empirical video data (`OBSERVED`), deductive rules (`INFERRED`), predictive ML models (`PREDICTED`), mathematical simulations (`SIMULATED`), operational guidance (`RECOMMENDED/ADVISORY`), and missing data (`UNAVAILABLE`).
2. **Forecasting Observation Threshold:** The short-horizon forecasting engine requires $\ge 20$ chronological traffic observations ($N \ge 20$). If real-world observations are below this threshold ($N < 20$), predictions are honestly presented as `UNAVAILABLE` without synthetic data substitution.
3. **Simulation-Only Decision Support:** All signal timing and emergency green-wave simulations are mathematical approximations (Webster formula, HCM LOS, progression queues) and do not actuate real-world traffic controllers.
4. **Read-Only Dashboard Guarantee:** Dashboard queries (`GET /api/v1/dashboard/summary`) are strictly read-only and never trigger background inference, model retraining, or database mutations.
5. **Single-Node Architecture:** Designed for single-node deployment with bounded concurrency (`MAX_CONCURRENT_ANALYSIS_JOBS=2`) and CPU inference; not designed as a distributed cluster.
6. **No Production RBAC / Auth:** User authentication and role-based access control are out of scope for this release; the platform is designed for trusted operator environments.

---

## 📄 License & Provenance

- **License:** MIT License. See [`LICENSE`](file:///c:/Users/Akhil/Downloads/ai-smart-traffic-intelligence-platform%203/ai-smart-traffic-intelligence-platform/LICENSE) for details.
- **Model Weights:** Ultralytics YOLOv8n (AGPL-3.0 / Ultralytics license).
