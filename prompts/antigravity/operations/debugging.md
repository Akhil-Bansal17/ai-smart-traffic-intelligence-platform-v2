# Operations — Debugging Prompt (paste into CLAUDE, with evidence attached)

> This prompt is for Claude. I'll attach one or more of: an error message, terminal output, a screenshot, an Antigravity completion report, or specific files. Claude's job is to diagnose and produce an Antigravity debugging prompt — not to fix the code directly.

Here's the problem: [paste error / terminal output / screenshot / Antigravity report / files here]

Please:
1. Understand what's actually failing from the evidence given — don't guess beyond it.
2. Classify the likely cause: architecture problem, implementation bug, environment issue, dependency issue, or configuration issue.
3. If the evidence is insufficient to localize the problem, ask for the *specific* missing piece (e.g., "the full stack trace" or "the contents of X file") rather than guessing.
4. Generate a targeted Antigravity debugging prompt requiring it to:
   1. Reproduce the issue.
   2. Identify the root cause (and explain it in the report).
   3. Implement the smallest correct fix — not a rewrite.
   4. Test the fix.
   5. Check for regressions in related functionality.
   6. Update `PROJECT_STATUS.md` / relevant docs if needed.
   7. Report exactly what was wrong, what changed, and the test evidence.

Do not rewrite the surrounding architecture to fix a small bug. Do not have Antigravity guess at multiple speculative fixes — one targeted, explained fix per prompt.
