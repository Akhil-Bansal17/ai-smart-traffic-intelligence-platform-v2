# 16 — Deployment Prompt

**Use when:** working on Docker/Compose setup or deployment readiness (Phase 18).

## Role
DevOps-minded engineer making local/first deployment reliable and reproducible.

## Context to Read
`ARCHITECTURE.md` §12, `.env.example`, current backend/frontend entry points.

## Objective
A `docker-compose.yml` (+ Dockerfiles) that brings up backend, frontend, and PostgreSQL with one command, using only `.env`-driven config — no hard-coded secrets or paths.

## Workflow
1. Write minimal, correct Dockerfiles per service.
2. Wire them together in Compose with proper service dependencies (backend waits for DB readiness).
3. Verify a clean `docker compose up` actually works end to end.
4. Document the exact run steps in `README.md`.

## Expected Output
Working Docker setup, verified by an actual run, plus updated setup docs.

## Restrictions
Never document run instructions that haven't actually been executed successfully.
