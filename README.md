# 🚦 AI Smart Traffic Intelligence Platform

> **Status: Active Development (Phases 1–15 Complete & Verified).** See `PROJECT_STATUS.md` for live test evidence, verification scripts, and provenance audits.

An AI-powered traffic intelligence and decision-support platform: computer vision (vehicle detection + multi-object tracking) feeding a traffic-analytics engine, a short-horizon prediction model, and two explicitly-labeled decision-support simulations (signal timing, emergency corridor routing). Built end-to-end — CV pipeline, ML pipeline, decision-support simulation, REST API, database, and an interactive React frontend — not a single-notebook YOLO demo.

> **Safety & Operational Scope Disclaimer:** *This system provides traffic signal optimization, emergency corridor simulation, and anomaly detection for decision support; it does not directly control physical traffic signals, emergency vehicles, or dispatch infrastructure.*

## Implemented & Verified Capabilities (Phases 1–15)

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

## Planned Capabilities (Phases 16–18)

- Operational Reporting, Alerts & Exporting (Phase 16)
- Docker Compose containerization & deployment (Phase 17)
- Final portfolio documentation & presentation (Phase 18)

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

## Getting Started

Local setup instructions (`.env`, Docker Compose, running the backend/frontend) will be filled in as Phases 2, 3, and 18 land. See `PROJECT_STATUS.md` for the current next task.

## A Note on Honesty

This project follows a strict no-fake-results rule: unmeasured numbers are reported as "Not yet measured," simulated features are labeled "Simulation," and planned-but-unbuilt features are labeled "Planned." That rule applies to this README too.
