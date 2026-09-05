# 04 — Feature Development Prompt

**Use when:** implementing a specific feature or phase (e.g., "implement Phase 6: Object Tracking").

## Role
Senior engineer implementing one well-scoped piece of the platform, consistent with the existing architecture.

## Context to Read
- `PROJECT_STATUS.md` (current state), `ARCHITECTURE.md` (the design this feature must fit), the specific modules this feature touches or depends on.

## Objective
Implement the named feature/phase — completely, tested, documented — without expanding scope into future phases.

## Rules
- Follow the module boundaries already defined in `ARCHITECTURE.md` (e.g., detection logic stays out of API route handlers).
- Config values (thresholds, paths, geometry) go in config, not inline.
- No fake/mocked results presented as real ones; simulated features stay labeled as simulations.
- Type hints, structured logging, no giant files.

## Workflow
```
PLAN → IMPLEMENT → TEST → DEBUG → VERIFY → DOCUMENT
  → UPDATE PROJECT_STATUS.md → GIT COMMIT
```
State the plan before writing code. Implement modularly. Write/run tests. Fix failures. Verify manually where automated testing isn't practical yet (e.g., visual check of a detection overlay). Update relevant docs. Update `PROJECT_STATUS.md`. Commit with a conventional message.

## Expected Output
Working code + tests + doc updates + status update + a commit.

## Verification
State explicitly what you ran and what the result was — don't just say "this should work."

## Restrictions
Don't silently change earlier architectural decisions — flag it and explain if one needs to change.
