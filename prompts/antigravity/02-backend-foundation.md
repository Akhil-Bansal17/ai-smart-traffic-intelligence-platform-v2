# 02 — Backend Foundation (VERIFICATION + GAP-FILL PROMPT — already implemented once)

> Attach `00-master-project-context.md` alongside this prompt.

## Role
Senior backend developer verifying and, only where genuinely needed, extending an existing FastAPI foundation. This was already implemented and tested directly (not through Antigravity) — treat it as real, working code until you find evidence otherwise.

## Objective
Independently confirm the backend foundation actually works in your environment, then close any real gaps against the Phase 2 objectives below — do not rewrite what already works.

## Current State (claimed — verify by running it yourself)
- `backend/app/main.py`, `app/api/v1/{router,health}.py`, `app/config/settings.py`, `app/core/{logging,exceptions}.py`, `app/db/{session,base}.py` exist.
- `GET /health` and `GET /api/v1/health` were both verified returning HTTP 200 via real `curl` requests in the environment they were built in.
- `backend/tests/` has 6 tests; `pytest` reported `6 passed`.
- Alembic (`backend/migrations/`) was verified against a real local PostgreSQL 16 instance (`alembic current` succeeded).
- `backend/requirements.txt` is pinned.

## Original Phase 2 Objectives (cross-check all of these against the code, not the description above)
FastAPI entry point; app configuration; environment variable loading; Pydantic settings; API router structure with versioning; health-check endpoint; centralized exception handling; structured logging; CORS configuration; basic service-layer architecture (`app/services/` exists but is intentionally empty — that's correct for this phase); database configuration foundation; SQLAlchemy setup; PostgreSQL connection configuration; Alembic migration foundation; backend dependency management; backend tests.

## Tasks
1. Set up your own Python environment, install `backend/requirements.txt`.
2. Point `DATABASE_URL` at a real PostgreSQL instance you control (local or Dockerized) — do not skip this by mocking it.
3. Run `uvicorn app.main:app` and independently hit both health endpoints yourself.
4. Run `pytest` yourself and record the actual output.
5. Run `alembic current` against your live database and record the actual output.
6. Cross-check the objectives list above against the code — flag anything claimed as done that you can't actually verify, and anything genuinely missing.
7. Fix only real gaps you find. If everything checks out, make no code changes.

## Implementation Rules
Keep the existing module boundaries (`api/`, `core/`, `config/`, `db/`, `schemas/`, `services/`) — do not consolidate or restructure them. No hard-coded secrets. No new dependencies without a stated reason.

## Testing
Full `pytest` run, pasted in full (not summarized). Add a new test only if you find and fix a real gap.

## Verification
Paste actual terminal output for: `pytest` run, both `curl`/HTTP checks, `alembic current`. "It works" without pasted output is not acceptable.

## Documentation
Update `PROJECT_STATUS.md` only if you changed something or found a discrepancy — otherwise state explicitly that you independently re-verified Phase 2 and it's accurate as documented.

## Git
No commit if nothing changed. If you fixed something, commit it alone: `fix: <specific gap>` — do not bundle with Phase 3 work.

## Completion Report
Use the format in `00-master-project-context.md`, including all pasted verification output.
