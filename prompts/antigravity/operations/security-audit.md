# Operations — Security Audit Prompt (paste into CLAUDE)

> This prompt is for Claude. Claude analyzes the project (from repo access, pasted code, or an Antigravity report) and produces an Antigravity security-audit implementation prompt — Claude does not perform the audit itself here.

Generate an Antigravity security-audit prompt for the AI Smart Traffic Intelligence Platform covering: authentication, authorization, API endpoints, file uploads, database access, secrets handling, CORS, dependencies, Docker configuration, frontend, logging, error handling, and privacy (see `SECURITY.md` for the project's existing commitments in each area).

The generated prompt must require Antigravity to:
- Classify every finding as `CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL`.
- For each finding: file, location, issue, impact, a realistic attack scenario, recommendation, and how to verify a fix.
- Produce the audit report **first**, before making any changes — no automatic remediation of critical findings without review.
- Never invent a vulnerability that isn't actually present in the code — if an area looks solid, say so.
- After remediation (in a follow-up prompt, once findings are reviewed), verify every fix actually closes the finding, with evidence.

Do not have Claude perform the audit inline in this conversation — the output here is the Antigravity prompt, ready to paste.
