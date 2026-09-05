# 15 — Testing Prompt

**Use when:** adding test coverage for a module or before marking a phase complete.

## Role
QA-minded engineer — tests should catch real regressions, not just exist for coverage numbers.

## Context to Read
The module(s) needing coverage, `ARCHITECTURE.md` for expected behavior, existing tests for style consistency.

## Coverage Targets
- CV: detection handling, tracking, counting correctness (no double-counts), lane assignment, density calculation.
- Data Science: preprocessing, feature engineering, prediction interface.
- Backend: API contracts, validation, DB operations, uploads (including malicious-input cases).
- Frontend: key user flows/components.
- Integration: upload → process → metrics → store → retrieve → display.

## Workflow
1. Identify untested behavior (not just untested lines).
2. Write tests that would actually fail if the behavior broke.
3. Run the full relevant suite, not just the new tests, to check for regressions.

## Expected Output
New/updated tests, and confirmation of a full test run (pass/fail counts).

## Restrictions
Don't write tests that only assert the code does whatever it currently does (tautological tests) — assert against the intended behavior.
