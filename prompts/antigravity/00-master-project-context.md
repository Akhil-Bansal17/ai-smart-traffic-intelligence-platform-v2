# 00 — MASTER PROJECT CONTEXT (give this to Antigravity first, and re-attach it at the start of every new Antigravity session)

## Project

**AI Smart Traffic Intelligence Platform** — an AI-powered traffic intelligence and decision-support platform: computer vision (vehicle detection + multi-object tracking) feeding a traffic-analytics engine, a short-horizon prediction model, and two explicitly-labeled decision-support simulations (signal timing, emergency corridor routing). This is a portfolio-grade, end-to-end system — not a single-notebook YOLO demo. Target uses: GitHub, LinkedIn, resume, internship applications.

## Pipeline (conceptual)

```
Traffic Video → Object Detection (YOLO) → Object Tracking (ByteTrack/BoT-SORT)
  → Vehicle Counting → Lane Analysis → Traffic Metrics → Data Storage (PostgreSQL)
  → Machine Learning (Traffic Prediction) → Decision Support (Signal / Emergency simulations)
  → Visualization (React dashboard)
```

## Stack (do not deviate without a strong, stated technical reason)

- **CV:** Python, OpenCV, Ultralytics YOLO, ByteTrack or BoT-SORT, NumPy
- **Data Science:** Pandas, NumPy, scikit-learn, XGBoost where appropriate, Matplotlib/Plotly
- **Backend:** FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Recharts/Plotly
- **Testing:** pytest (backend), a suitable frontend testing framework
- **Infra:** Docker, Docker Compose, Git

## Current Repository State (verified — read `PROJECT_STATUS.md` for the live version of this)

- **Phase 1 (foundation/scaffolding): DONE.** Full repo structure, `ARCHITECTURE.md`, `PROJECT_STATUS.md`, `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `.gitignore`, `.env.example`, git initialized.
- **Phase 2 (backend foundation): DONE and verified live**, not just written:
  - `backend/app/main.py` — FastAPI app with lifespan startup/shutdown logging, CORS, centralized exception handlers, versioned router mounted.
  - `GET /health` (unversioned, infra liveness) and `GET /api/v1/health` (versioned) — both hit over real HTTP and returned 200.
  - `backend/app/config/settings.py` — Pydantic Settings, reads from `.env`, no hard-coded secrets.
  - `backend/app/core/logging.py`, `backend/app/core/exceptions.py` — structured logging, centralized error handling (no leaked stack traces — verified: a 404 on an unknown route returned `{"error": {"code": "http_error", "message": "Not Found"}}`, not a raw traceback).
  - `backend/app/db/session.py`, `backend/app/db/base.py` — SQLAlchemy engine/session (lazy — no live connection required to import).
  - `backend/migrations/` — Alembic scaffold, wired to `settings.database_url`. `alembic current` was run against a real local PostgreSQL 16 instance and succeeded.
  - `backend/requirements.txt` — pinned versions.
  - `backend/tests/` — 6 tests, all passing (`pytest` run: `6 passed`).
- **No frontend code exists yet.** No CV/YOLO code exists yet. No ML code exists yet. No Docker setup exists yet.

Do not assume anything beyond what's listed above without inspecting the repo yourself first.

## Rules (apply to every phase, every prompt)

- Read the relevant files before changing anything. Never blindly overwrite existing code.
- Never delete working functionality without a stated reason.
- Never create fake functionality, fabricate test results, or fabricate ML metrics (accuracy, FPS, MAE, RMSE, R², detection counts, or any "improvement" percentage) — if it wasn't measured this session, say `NOT MEASURED`.
- Simulated features (signal optimization, emergency corridor) are labeled `SIMULATION` everywhere — code comments, API responses, UI, docs — never presented as real control of infrastructure.
- No hard-coded secrets, ever. All config through `.env` / `.env.example`.
- No unnecessary dependencies. No giant files — keep the modular boundaries already established in `ARCHITECTURE.md`.
- Don't skip testing, and don't claim success without having actually run something and observed the result.

## Standard Workflow (every phase prompt expects this sequence)

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY
  → DOCUMENT → UPDATE PROJECT_STATUS.md → REPORT
```

## Required Completion Report Format

At the end of any phase, report exactly:
1. What was implemented
2. Files created/modified
3. Tests performed and their exact results (paste real output, don't summarize into "tests pass")
4. Anything not implemented or partially implemented, and why
5. Known issues/bugs
6. The exact next recommended phase

## Reference documents in this repo

`ARCHITECTURE.md` (system design, DB schema, API surface, security model), `PROJECT_STATUS.md` (live state — treat as more current than this file if they ever disagree), `README.md`, `SECURITY.md`.
