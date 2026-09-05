# 🚦 AI Smart Traffic Intelligence Platform

> **Status: early development (Phases 1–4 of 20 complete; Phase 5 in progress).** This README will be replaced with the full portfolio version in Phase 20. Right now it exists so the repo is self-explanatory from day one.

An AI-powered traffic intelligence and decision-support platform: computer vision (vehicle detection + multi-object tracking) feeding a traffic-analytics engine, a short-horizon prediction model, and two explicitly-labeled decision-support simulations (signal timing, emergency corridor routing). Built end-to-end — CV pipeline, ML pipeline, API, database, and a real frontend — not a single-notebook YOLO demo.

## What this is not (yet)

No feature below is claimed as finished unless `PROJECT_STATUS.md` says so. As of this commit, working FastAPI backend (with secure video ingestion), React frontend, and database foundations exist and are tested (see `PROJECT_STATUS.md` for exact verification evidence) — but the CV detection/tracking pipeline, ML pipeline, and decision simulations do not exist yet.

## Planned Capabilities

- Vehicle detection & multi-class classification (car, motorcycle, bus, truck, bicycle)
- Multi-object tracking with persistent IDs (no double-counting)
- Configurable lane/zone-based counting, density, and queue-length estimation
- Explainable congestion scoring (0–100, with stated reasons)
- Short-horizon (5–15 min) traffic prediction, evaluated against real held-out data
- Signal-timing recommendation — **simulation, not live control**
- Emergency corridor routing — **simulation, not live control**
- Historical analytics dashboard

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
