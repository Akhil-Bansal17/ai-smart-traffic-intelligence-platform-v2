# 01 — Project Initialization (VERIFICATION PROMPT — foundation already exists)

> Attach `00-master-project-context.md` alongside this prompt.

## Role
You are verifying an existing project foundation, not creating one. Phase 1 was already completed directly (not through Antigravity) — your job is to confirm it's real, correct, and reproducible in your own environment, and to fix only genuine gaps.

## Objective
Independently verify the repository foundation and environment; report any discrepancy between documentation and reality.

## Current State (claimed — verify, don't assume)
Repo has: `README.md`, `ARCHITECTURE.md`, `PROJECT_STATUS.md`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`, `.gitignore`, `.env.example`, a full `backend/`/`frontend/`/`data_science/`/`docs/`/`prompts/`/`scripts/`/`tests/` folder structure, and one git commit.

## Tasks
1. Clone/open the repo in your environment.
2. Confirm the directory structure matches what `ARCHITECTURE.md` §2 and the root `README.md` describe.
3. Confirm `git log` shows the expected initial commit and the working tree is clean.
4. Confirm `.gitignore` actually excludes `.env`, `__pycache__/`, `node_modules/`, and uploaded media — test this by creating a throwaway file matching each pattern and running `git status` to confirm it's ignored, then delete the throwaway files.
5. Confirm `.env.example` has no real secret values (only placeholders).
6. Confirm `PROJECT_STATUS.md`'s "Completed Work" and "Unfinished Work" table match what's actually in the repo (no code should exist for phases marked not-started).
7. Note your local Python and Node versions and confirm they're reasonable for the pinned dependencies once you reach Phase 2/3 (this repo does not yet pin exact versions in `PROJECT_STATUS.md`'s Environment Information — fill that in from what you actually have).

## Files to Inspect
Everything at repo root, plus the full output of `find . -type f` (excluding `.git`).

## Implementation Rules
Do not regenerate any of the root docs or restructure folders — only fix a genuine discrepancy (e.g., a `.gitignore` gap) if you find one, and explain exactly why.

## Testing
No automated tests apply to this phase — verification is manual inspection plus the `.gitignore` throwaway-file check above.

## Verification
Your report must state, for each of Tasks 1–7, what you actually found — not "looks correct."

## Documentation
Update `PROJECT_STATUS.md`'s Environment Information section with your actual local versions. Do not change anything else in it unless you found and fixed a real gap.

## Git
If you made no changes, no commit is needed — say so explicitly. If you fixed a genuine gap, commit it alone with a message like `fix: <specific gap>`.

## Completion Report
Use the format in `00-master-project-context.md`. Explicitly state: "Phase 1 verified, no gaps found" OR "Phase 1 verified, fixed: <list>".
