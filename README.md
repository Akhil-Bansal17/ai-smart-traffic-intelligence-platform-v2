# 🚦 AI Smart Traffic Intelligence Platform

> **Status: Active Development (Phases 1–12 Complete & Verified; Phase 13 in progress).** See `PROJECT_STATUS.md` for live test evidence, verification scripts, and provenance audits.

An AI-powered traffic intelligence and decision-support platform: computer vision (vehicle detection + multi-object tracking) feeding a traffic-analytics engine, a short-horizon prediction model, and two explicitly-labeled decision-support simulations (signal timing, emergency corridor routing). Built end-to-end — CV pipeline, ML pipeline, decision-support simulation, REST API, database, and an interactive React frontend — not a single-notebook YOLO demo.

> **Safety & Operational Scope Disclaimer:** *This system provides traffic signal optimization simulation and decision support; it does not directly control physical traffic signals.*

## Implemented & Verified Capabilities (Phases 1–12)

- **Video Ingestion & Validation (Phase 4):** Secure container magic-byte verification, path-traversal prevention, metadata extraction.
- **Vehicle Detection (Phase 5):** Ultralytics YOLOv8n multi-class classification (`car`, `motorcycle`, `bus`, `truck`, `bicycle`).
- **Object Tracking (Phase 6):** ByteTrack Kalman filter motion prediction + IoU association with track lifecycle states.
- **Vehicle Counting (Phase 7):** Virtual line-crossing detector with 2D cross-product transition testing and zero double-counting.
- **Traffic Flow Analytics (Phase 8):** Minute/hourly flow rates, class distributions, directional splits, discrete time-series bucketing.
- **Lane Analysis & Density (Phase 9):** Configurable 2D polygonal lane assignment, Shoelace area calculation, image-space density estimation.
- **Database Integration & Persistence (Phase 10):** Relational persistence of sessions, metrics, lane occupancy, and crossing events.
- **Short-Horizon Traffic Forecasting (Phase 11):** Non-leaking lag feature engineering, classical ML models (Random Forest, HistGradientBoosting, Ridge), empirical residual prediction intervals, and strict 3-tier data provenance tracking.
- **Traffic Signal Optimization Simulation (Phase 12):** Deterministic baseline signal plans, 3 explainable optimization algorithms (Demand-Proportional, Webster's Method, Constrained Delay Minimization), Webster delay proxy modeling ($d_1 + d_2 - d_3$), HCM Level of Service (LOS A–F), and interactive React simulation dashboard.

## Planned Capabilities (Phases 13–18)

- Emergency corridor routing simulation — **simulation, not live control**
- Aggregated historical analytics dashboard
- Role-based authentication & system configuration
- Docker Compose containerization & deployment

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
