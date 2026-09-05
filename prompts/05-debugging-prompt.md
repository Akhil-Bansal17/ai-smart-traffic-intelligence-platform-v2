# 05 — Debugging Prompt

**Use when:** something is broken and you need it fixed correctly, not patched.

## Role
Debugger, not a patcher. Root cause over quick fix.

## Context to Read
The failing code path, its tests (if any), recent related commits, and `PROJECT_STATUS.md`'s Known Bugs section.

## Objective
Fix the actual root cause with the smallest correct change.

## Rules
Never apply a fix you can't explain. Never suppress an error without understanding why it occurs. Never fix a symptom while leaving the cause in place.

## Workflow
1. Reproduce the issue (state exactly how).
2. Inspect the relevant code.
3. Identify the root cause.
4. Explain the root cause in plain language.
5. Implement the smallest correct fix.
6. Test the fix.
7. Check for regressions in related functionality.
8. Update `PROJECT_STATUS.md` (Known Bugs) if the bug was tracked there.

## Expected Output
A root-cause explanation, the fix, and confirmation it was tested.

## Verification
Re-run whatever reproduced the bug — confirm it no longer does, and that nearby tests still pass.

## Restrictions
No speculative multi-file rewrites "just in case" — fix what's actually broken.
