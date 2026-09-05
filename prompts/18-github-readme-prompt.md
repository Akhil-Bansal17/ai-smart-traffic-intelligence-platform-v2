# 18 — GitHub README (Final Portfolio Version) Prompt

**Use when:** Phase 20 — producing the polished, public-facing README.

## Role
You're writing for a technical reviewer (recruiter, hiring manager, interviewer) who will skim in under two minutes.

## Context to Read
`PROJECT_STATUS.md` (for what's genuinely true), `ARCHITECTURE.md`, actual test results, actual screenshots if available.

## Required Sections
Project overview, problem statement, solution, features (marked verified/simulated/planned as accurate), architecture (diagram + summary), AI pipeline, ML pipeline, tech stack, setup instructions (tested), screenshots, API documentation, testing summary, security summary, limitations, future improvements.

## Rules
- Every feature claim must be checked against `PROJECT_STATUS.md` before being stated as done.
- Limitations section is not optional — a project that's honest about what it doesn't do reads as more credible, not less.
- No invented metrics anywhere.

## Expected Output
The full replacement `README.md`.

## Verification
Cross-check every "✅ implemented" claim in the new README against `PROJECT_STATUS.md`'s phase table.
