# 12 — Frontend Improvement Prompt

**Use when:** improving the UI/UX of the dashboard or any page.

## Role
Frontend engineer aiming for a UI that reads as a real product, not a bootstrapped admin panel.

## Context to Read
`frontend/src/pages/`, `frontend/src/components/`, `ARCHITECTURE.md` §9.

## Objective
Improve clarity, visual hierarchy, and professionalism of the specified page/component without breaking data accuracy (e.g., a chart must still reflect real values).

## Workflow
1. Identify the specific page/component and what's currently weak about it (cluttered layout, unclear KPI meaning, poor mobile behavior, etc.).
2. Propose the specific change with a rationale.
3. Implement it.
4. Verify real data still renders correctly after the change (not just that it looks good with placeholder data).

## Expected Output
Updated component(s) plus a short rationale for the design choices made.

## Restrictions
Never hide a "Simulation" or "Not yet measured" label to make a view look more finished.
