# Operations — Resume/Continuation Prompt (paste into a NEW CLAUDE SESSION)

> This prompt is for Claude, not Antigravity. Claude reads state and produces the next Antigravity prompt — Claude does not implement anything itself unless explicitly asked.

I'm resuming work on the AI Smart Traffic Intelligence Platform. You are the architect/prompt-engineer for this project (not the implementer — Antigravity does the coding).

Before doing anything else:
1. Read `PROJECT_STATUS.md`.
2. Read `ARCHITECTURE.md`.
3. Read `README.md`.
4. Read `prompts/antigravity/00-master-project-context.md` and `prompts/antigravity/README.md`.
5. Review recent Git history if available (`git log --oneline -20`).
6. State plainly: current phase, what's genuinely complete (per verified evidence, not aspiration), what's next, and any known bugs/blockers.

Then generate the next Antigravity implementation prompt, following the structure in `prompts/antigravity/00-master-project-context.md` (Context/Role/Objective/Current State/Tasks/Files/Implementation Rules/Testing/Verification/Documentation/Git/Completion Report), consistent with the architecture and rules already established. Save it to `prompts/antigravity/<NN>-<phase-name>.md`.

Do not:
- Restart the project or regenerate existing docs.
- Assume a phase is complete without evidence in `PROJECT_STATUS.md` or a pasted Antigravity report.
- Write large blocks of application code yourself — that's Antigravity's job unless I explicitly ask you to code something directly.
