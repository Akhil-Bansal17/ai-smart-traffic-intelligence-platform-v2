# Operations — Final Project Audit Prompt (paste into CLAUDE near the end of the project)

> This prompt is for Claude. I'll paste in all available evidence (PROJECT_STATUS.md contents, Antigravity completion reports, test output, screenshots). Claude's job is to classify and produce the final Antigravity task list — not to declare the project done itself.

Here's the current evidence: [paste PROJECT_STATUS.md / Antigravity reports / test results / screenshots here]

Using this evidence (and inspecting the repo directly if you have access), classify every feature listed in `ARCHITECTURE.md` and the original master prompt across these dimensions: CV pipeline, ML/data science, backend, frontend, database, security, testing, deployment, documentation, GitHub quality, and any resume/LinkedIn claims already drafted.

For each feature, classify as exactly one of:
```
VERIFIED WORKING
PARTIALLY WORKING
NOT IMPLEMENTED
SIMULATION
BROKEN
```

Then produce:
1. A classified feature-by-feature table.
2. A prioritized Antigravity task list of exactly what needs to happen before this is genuinely portfolio-ready (fix `BROKEN` items, finish `PARTIALLY WORKING` items that are load-bearing for the README's claims, confirm every `SIMULATION` is labeled as such everywhere it's shown).
3. A go/no-go recommendation — and if no-go, exactly what's blocking it.

Never upgrade a classification without direct evidence. When evidence is missing or ambiguous, classify conservatively (e.g., `PARTIALLY WORKING` rather than `VERIFIED WORKING`) and say what evidence would resolve it.
