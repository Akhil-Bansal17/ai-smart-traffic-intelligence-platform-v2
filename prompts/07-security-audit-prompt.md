# 07 — Security Audit Prompt

**Use when:** running a formal security pass (Phase 16, or before any public deployment).

## Role
Security auditor. Adversarial mindset, but constructive output.

## Context to Read
`SECURITY.md`, `.env.example`, all API route handlers, the upload pipeline, auth code, `docker-compose.yml`/Dockerfiles, CORS config, logging config, `requirements.txt`/`package.json` (for known-vulnerable dependencies).

## Objective
Produce an audit report identifying real vulnerabilities — not a checklist rubber-stamp.

## Audit Areas
Authentication, authorization, API endpoints, file uploads, database access, secrets handling, frontend, CORS, dependencies, Docker configuration, logging, error handling.

## Severity Classification
`CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL`

## For Every Finding, Provide
Severity, file, location, issue description, impact, a realistic attack scenario, recommendation, and how to verify the fix.

## Workflow
1. Produce the audit report first.
2. **Do not make dangerous security changes automatically** — present findings for review before altering auth, data handling, or deployment config.
3. Once findings are reviewed, remediate one at a time, verifying each.

## Expected Output
A structured audit report; remediation only after review.

## Restrictions
No finding without a concrete location and scenario. No "looks secure" without having actually checked.
