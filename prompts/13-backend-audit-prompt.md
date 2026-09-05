# 13 — Backend Audit Prompt

**Use when:** reviewing backend robustness outside of a full security audit.

## Role
Backend engineer auditing for correctness and robustness, not just "does it run."

## Context to Read
`backend/app/api/`, `backend/app/core/`, `backend/app/schemas/`, error-handling middleware.

## Inspect
Input validation (Pydantic coverage), status code correctness, error handling (no leaked internals), logging quality, endpoint consistency, N+1 query patterns, transaction boundaries.

## Workflow
1. Walk each endpoint against its intended contract in `ARCHITECTURE.md` §7.
2. Check validation and error paths, not just the happy path.
3. Flag anything inconsistent across endpoints (e.g., one returns a raw 500, another a clean error shape).

## Expected Output
A findings list by endpoint, ranked by severity, with concrete fixes.

## Restrictions
Don't conflate this with the full security audit (`07-security-audit-prompt.md`) — this is about robustness/correctness, run that one for adversarial risk.
