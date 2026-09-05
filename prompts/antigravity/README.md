# Antigravity Prompt Library

**Workflow: Claude plans it. Antigravity codes it. Claude reviews it. Antigravity fixes it.**

This subfolder is distinct from the top-level `prompts/` library:

- **`prompts/` (top level)** — prompts for a Claude *coding* session (Claude Code, or this chat). Written during Phase 1–2 before the Claude/Antigravity split was adopted.
- **`prompts/antigravity/` (here)** — the current model. Two kinds of file:
  - **Direct-to-Antigravity prompts** (`00-...`, `01-...`, `02-...`, etc.) — copy these straight into Antigravity.
  - **`operations/`** — prompts for *Claude*, not Antigravity. You paste one of these into a Claude session along with evidence (an error, a screenshot, Antigravity's own report). Claude's job is to analyze and produce the right Antigravity prompt in response — Claude does not fix anything directly here.

## Recommended Development Sequence

| # | Phase | Status |
|---|---|---|
| 1 | Project foundation & architecture | ✅ Done (built directly by Claude, verified) |
| 2 | Backend foundation | ✅ Done (built directly by Claude, verified — see PROJECT_STATUS.md) |
| 3 | Frontend foundation | ⬜ Next — first phase to go through Antigravity |
| 4 | Video ingestion | ⬜ |
| 5 | YOLO detection | ⬜ |
| 6 | Object tracking | ⬜ |
| 7 | Vehicle counting | ⬜ |
| 8 | Lane analysis | ⬜ |
| 9 | Traffic analytics engine | ⬜ |
| 10 | Database integration | ⬜ |
| 11 | Professional dashboard | ⬜ |
| 12 | Historical analytics | ⬜ |
| 13 | Traffic prediction (ML) | ⬜ |
| 14 | Signal optimization simulation | ⬜ |
| 15 | Emergency corridor simulation | ⬜ |
| 16 | Security hardening | ⬜ |
| 17 | Testing | ⬜ |
| 18 | Performance optimization | ⬜ |
| 19 | Docker / deployment | ⬜ |
| 20 | Documentation | ⬜ |
| 21 | GitHub README | ⬜ |
| 22 | LinkedIn project description | ⬜ |
| 23 | Resume bullets | ⬜ |
| 24 | Interview preparation | ⬜ |
| 25 | Final project audit | ⬜ |

## Full planned file tree

```
prompts/antigravity/
├── README.md                          (this file)
├── 00-master-project-context.md       ← give this to Antigravity once, first
├── 01-project-initialization.md       ← verification prompt (already built)
├── 02-backend-foundation.md           ← verification prompt (already built)
├── 03-frontend-foundation.md          ← not yet written — next up
├── 04-video-ingestion.md              ┐
├── 05-yolo-detection.md               │
├── 06-object-tracking.md              │
├── 07-vehicle-counting.md             │  generated as we reach
├── 08-lane-analysis.md                │  each phase, not
├── 09-traffic-analytics.md            │  all at once
├── 10-database-integration.md         │
├── 11-dashboard.md                    │
├── 12-historical-analytics.md         │
├── 13-traffic-prediction.md           │
├── 14-signal-optimization.md          │
├── 15-emergency-corridor.md           │
├── 16-security-hardening.md           │
├── 17-testing.md                      │
├── 18-performance-optimization.md     │
├── 19-docker-deployment.md            │
├── 20-documentation.md                │
├── 21-github-readme.md                │
├── 22-linkedin-project-description.md │
├── 23-resume-bullets.md               │
├── 24-interview-preparation.md        ┘
├── 25-final-project-audit.md          ← operations/final-audit.md generates this one
└── operations/
    ├── resume-continuation.md         ← paste into a new Claude session to resume
    ├── debugging.md                   ← paste into Claude with an error/report/screenshot
    ├── security-audit.md              ← paste into Claude to generate a security-audit prompt
    └── final-audit.md                 ← paste into Claude near the end, with all evidence
```

Only the files that exist right now are written — the rest get generated as each phase is actually reached, per the master prompt's own rule against front-loading everything.

## The one rule every prompt here follows

Nothing is reported as working, measured, or complete unless it was actually verified. `NOT MEASURED`, `SIMULATION`, `PLANNED`, and `BROKEN` are all correct, expected answers.
