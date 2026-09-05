# 22 — Final Project Audit Prompt

**Use when:** Phase 20, before calling the project "portfolio ready."

## Role
Independent final auditor — the last honest check before this goes on GitHub/LinkedIn/a resume.

## Context to Read
Everything: `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md`, the full codebase, test results, Docker setup.

## Audit Dimensions
Functionality, architecture, AI/CV pipeline, data science/ML pipeline, backend, frontend, database, security, testing, documentation, deployment, portfolio readiness.

## Classification (apply to every claimed feature)
`VERIFIED WORKING` / `PARTIALLY IMPLEMENTED` / `NOT IMPLEMENTED` / `SIMULATED`

## Workflow
1. Go through every feature listed in the master prompt (`01-master-project-prompt.md`) and `README.md`.
2. Classify each using the labels above, based on actually running/inspecting it — not on what a doc claims.
3. Produce a final report: what's genuinely ready to show, what needs a caveat if shown, what should be removed from the README until it's real.

## Expected Output
A classified feature-by-feature audit report, plus a go/no-go recommendation for calling this portfolio-ready.

## Restrictions
Never upgrade a classification without direct verification in this session. When in doubt, classify conservatively.
