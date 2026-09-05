# 17 — Documentation Prompt

**Use when:** syncing docs to actual code state (Phase 19, or anytime docs drift).

## Role
Technical writer who verifies claims against code before writing them.

## Context to Read
Current `README.md`, `ARCHITECTURE.md`, `PROJECT_STATUS.md`, and the actual current codebase.

## Objective
Make documentation match reality exactly — no aspirational claims presented as current state.

## Workflow
1. Diff documented behavior against actual behavior, file by file.
2. Correct any doc that overstates completeness.
3. Fill gaps where real functionality exists but isn't documented.
4. Keep "Planned"/"Simulation"/"Not yet measured" labels wherever they still apply.

## Expected Output
Updated docs, with a short note on what was corrected and why.

## Restrictions
Never document a feature as complete without having verified it runs.
