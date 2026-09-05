# Prompt Library

> **Workflow update:** as of this project's current phase, implementation is delegated to Google Antigravity. Claude's role is architect/prompt-engineer, not primary coder. The prompts below (written during Phase 1–2) are still valid for a Claude coding session, but going forward, use **`prompts/antigravity/`** for the active workflow — it contains the Antigravity-facing implementation prompts plus a set of Claude-facing operational prompts (resume, debugging, security audit, final audit) that produce Antigravity prompts as output. Start there.

A complete, reusable set of prompts for building and maintaining the AI Smart Traffic Intelligence Platform across sessions. Each one is meant to be pasted directly into a new Claude session (Claude Code is a natural fit for this project given its multi-phase, multi-session nature — a persistent local repo and git history) along with whatever's needed from the "Context to Read" list in that prompt.

## How to use these

1. Start (or resume) a session.
2. Pick the prompt that matches what you're doing right now — see the map below.
3. Paste it in, optionally with any extra specifics ("...focused on Phase 6" or "...on the `lane_analyzer.py` module").
4. Let Claude read the context files it asks for before it starts changing anything.

## Map

| When you want to... | Use |
|---|---|
| Start a brand-new session and pick up where you left off | `02-resume-project-prompt.md` |
| Record what happened this session | `03-project-status-prompt.md` |
| Build a specific feature/phase | `04-feature-development-prompt.md` |
| Fix something broken | `05-debugging-prompt.md` |
| Review a finished feature before calling it done | `06-code-review-prompt.md` |
| Run a real security audit | `07-security-audit-prompt.md` |
| Investigate slowness | `08-performance-audit-prompt.md` |
| Improve detection/tracking/counting accuracy | `09-computer-vision-improvement-prompt.md` |
| Improve the prediction model | `10-ml-improvement-prompt.md` |
| Explore traffic data before modeling | `11-data-science-analysis-prompt.md` |
| Improve a dashboard page or component | `12-frontend-improvement-prompt.md` |
| Audit backend robustness (non-security) | `13-backend-audit-prompt.md` |
| Audit schema/queries/indexes | `14-database-audit-prompt.md` |
| Add test coverage | `15-testing-prompt.md` |
| Work on Docker/Compose/deployment | `16-deployment-prompt.md` |
| Sync docs to actual code state | `17-documentation-prompt.md` |
| Write the final portfolio README | `18-github-readme-prompt.md` |
| Write a LinkedIn post about it | `19-linkedin-project-prompt.md` |
| Write resume bullets | `20-resume-bullet-prompt.md` |
| Prep for an interview about this project | `21-interview-preparation-prompt.md` |
| Do the final pre-portfolio audit | `22-final-project-audit-prompt.md` |

`01-master-project-prompt.md` is the original project brief — the source of truth for scope, stack, and rules (especially the no-fake-results rule in its §46). Every other prompt here assumes it.

## The one rule that spans all of them

Nothing gets marked done, working, or measured unless it was actually verified in that session. "Not yet measured," "Simulation," and "Planned" are correct answers, not failures.
