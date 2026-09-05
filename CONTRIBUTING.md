# CONTRIBUTING.md

This is currently a solo/portfolio project, but it's built with the same discipline as a team codebase.

## Workflow per feature/phase

```
PLAN → IMPLEMENT → TEST → DEBUG → VERIFY → DOCUMENT
  → UPDATE PROJECT_STATUS.md → GIT COMMIT → NEXT PHASE
```

Testing is not optional and a feature is not "done" because code was written for it — it's done when it's been verified and documented.

## Commit Style

Conventional, descriptive commits — no giant catch-all commits:

```
feat: implement video ingestion
feat: add YOLO vehicle detection
fix: correct off-by-one in lane crossing counter
security: harden file upload validation
test: add traffic analytics tests
docs: update architecture documentation
```

## Code Quality

- Type hints throughout (Python and TypeScript).
- Modular architecture — no giant files, no logic duplicated across modules.
- Configuration (thresholds, paths, lane geometry) lives in config, never hard-coded inline.
- No placeholder/dead code left in `main`; no commented-out blocks left as "just in case."

## Before claiming something works

Run it. Test it. Then update `PROJECT_STATUS.md`. Never mark a phase complete on the strength of "the code looks right."
