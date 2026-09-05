# 02 — Resume / Continuation Prompt

**Use when:** starting a new Claude session to keep working on this project.

## Role
You are resuming work on the AI Smart Traffic Intelligence Platform as the ongoing lead engineer. This is not a new project — treat everything already built as real and load-bearing until you've verified otherwise.

## Context to Read (in this order)
1. `PROJECT_STATUS.md` — current phase, completed/unfinished work, known bugs, blockers, next task.
2. `ARCHITECTURE.md` — system design and decisions already made.
3. `README.md` — current public-facing description of the project.
4. Any docs under `docs/` relevant to the area you're about to touch.
5. The actual repository — directory structure, and the specific files for the current phase.
6. Git history (`git log --oneline -20`) — what actually landed, not just what was planned.
7. Run the existing test suite (if any) to see current state directly, not just what the docs claim.

## Objective
Identify exactly where the project stands, then continue from that exact state — no more, no less.

## Rules
- Never restart the project or regenerate large parts of it "for consistency."
- Never rewrite working functionality unless there's a concrete reason (bug, security issue, a phase's explicit scope).
- Never assume a feature works because a doc says so — verify by reading the code and, where possible, running it/tests.
- Never delete existing work without stating why in your response and in `PROJECT_STATUS.md`.

## Workflow
1. Read the context above.
2. State in plain language: current phase, what's actually done, what's next.
3. Confirm the next task matches `PROJECT_STATUS.md`'s "Next Task" — flag it if it doesn't.
4. Proceed with that task using the relevant phase-specific prompt (e.g., `04-feature-development-prompt.md`).

## Expected Output
A short status summary, then implementation work for the identified next task.

## Verification
Before writing new code, confirm your understanding of "what's done" against the actual files, not just the doc text.

## Restrictions
Do not jump ahead to a later phase's features "while you're in there."
