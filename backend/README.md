# 🚦 Traffic Intelligence Backend

> **Status: Phases 2–18 Complete & Verified.** See `../PROJECT_STATUS.md` for full implementation history and test verification logs.

FastAPI-powered asynchronous traffic intelligence, analytics, forecasting, simulation, and decision intelligence service.

## Backend Architecture Layout

```
backend/
├── app/
│   ├── api/v1/                  # Versioned API route endpoints (videos, cv, ml, simulation, insights)
│   ├── config/                  # Pydantic v2 application settings & environment validation
│   ├── core/                    # Centralized exceptions, security helpers, structured logging
│   ├── db/                      # SQLAlchemy database session & engine configuration
│   ├── models/                  # SQLAlchemy ORM models (Video, AnalysisSession, Predictions, etc.)
│   ├── schemas/                 # Pydantic v2 request / response validation schemas
│   ├── services/
│   │   ├── cv/                  # Video ingestion, YOLOv8 detector, ByteTrack tracker, counting, lanes, jobs
│   │   ├── ml/                  # Non-leaking feature engineering, dataset extractor, forecasting models
│   │   ├── simulation/          # Webster & delay-minimized traffic signal optimization simulation
│   │   ├── corridor/            # Coordinated multi-intersection emergency corridor priority simulation
│   │   ├── dashboard/           # Single-roundtrip system intelligence aggregator
│   │   ├── anomaly/             # Multi-rule statistical traffic anomaly & incident detector
│   │   └── insights/            # Deterministic multi-category explainable decision intelligence
│   └── main.py                  # FastAPI application entry point with lifespan lifecycle hooks
├── migrations/                  # Alembic database migration scripts (0001 through 0010)
├── tests/                       # Complete pytest suite (200 unit & integration tests)
├── alembic.ini                  # Alembic environment and configuration
├── pytest.ini                   # Pytest testpath and pythonpath configuration
└── requirements.txt             # Pinned backend dependencies
```

## Running the Backend

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Database Migrations
```bash
alembic upgrade head
```

### 3. Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Run Pytest Test Suite
```bash
python -m pytest tests
```

