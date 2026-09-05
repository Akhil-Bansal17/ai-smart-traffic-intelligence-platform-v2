# 03 — Update PROJECT_STATUS.md Prompt

**Use when:** wrapping up a work session or completing a phase.

## Role
You are updating the project's single source of truth for state.

## Context to Read
- The current `PROJECT_STATUS.md`.
- What was actually implemented/changed in this session (diff or summary of your own recent work).
- Any test results from this session.

## Objective
Produce an accurate, current `PROJECT_STATUS.md` — not an optimistic one.

## Rules
- Every "Completed" item must have been verified this session (run, tested, or directly inspected) — not just written.
- Every unresolved issue goes under Known Bugs or Current Blockers, however small.
- "Latest Successful Test" must name the actual test/command run and when.
- Never mark a phase complete if any part of it is untested or unverified — mark it partial instead.

## Workflow
1. List what changed since the last update.
2. Update: Current Phase, Completed Work, Unfinished Work (phase table), Known Bugs, Current Blockers, Technical Decisions Log (append, don't erase history), Environment Information, Latest Successful Test, Next Task.
3. Keep the phase table (Phase 1–20) in sync with reality.

## Expected Output
The full replacement content of `PROJECT_STATUS.md`.

## Verification
Read back the new "Next Task" — it should be immediately actionable by someone who has read nothing else.

## Restrictions
Don't delete the Technical Decisions Log history — append to it.
