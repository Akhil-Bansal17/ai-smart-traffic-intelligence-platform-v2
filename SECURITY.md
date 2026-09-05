# SECURITY.md

**Status: Security hardening is Phase 16 and has not started.** This document tracks the practices this project commits to and will be updated as each is actually implemented — see `PROJECT_STATUS.md` for current status per item.

## Commitments

- **Secrets:** never hard-coded, never committed. `.env` is git-ignored; `.env.example` documents required variables with placeholder values only. Secrets are never sent to the frontend or written to logs.
- **File uploads:** size limits, extension + MIME validation, filename sanitization, path-traversal protection, isolated upload directory, no execution of uploaded files, temporary-file cleanup. Client-supplied filenames, extensions, and MIME types are never trusted as-is.
- **Injection:** parameterized queries only (SQLAlchemy) — no raw string-built SQL.
- **XSS/CSRF:** React's default escaping is not treated as sufficient on its own; API responses are validated/sanitized, and CSRF protection is added wherever cookie-based auth is used.
- **CORS:** locked to known origins — never `*` in anything resembling production configuration.
- **Auth:** hashed passwords, token-based sessions, per-endpoint authorization checks (not just UI-level gating).
- **Dependencies:** kept current; no known-vulnerable pins left unaddressed without a documented reason.
- **Logging:** structured, and never includes passwords, tokens, or raw credential-bearing request bodies.

## Privacy

Traffic footage can contain faces, license plates, and pedestrians incidental to vehicle detection.

- No more personal data is collected than the traffic-analytics purpose requires.
- Raw per-frame detection rows (which can include bounding boxes tied to identifiable frames) are not retained indefinitely by default — retention/cleanup is configurable, and the default will be documented once Phase 16 sets it.
- Uploaded source video is cleaned up on a configurable retention schedule rather than kept forever.

## Reporting

This is currently a personal/portfolio project without a public deployment. A disclosure process will be added here if/when that changes.

## Audit History

None yet. Use `prompts/07-security-audit-prompt.md` to run the first formal audit once Phase 16 begins — findings and remediation will be logged here.
