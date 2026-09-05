# 03 — Frontend Foundation

> Attach `00-master-project-context.md` alongside this prompt.

## Role
You are a senior frontend engineer building the foundation for a professional AI traffic-analytics product. This phase builds structure and plumbing only — not feature pages, not the CV/ML pipeline, not real traffic data.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md` — project-wide rules, current verified state, required report format.
2. `PROJECT_STATUS.md` — current phase and any changes since this prompt was written.
3. `ARCHITECTURE.md` — read §9 (Frontend Architecture) in full, and skim §7 (API surface) for what's coming in later phases.
4. `README.md` — current public-facing project description.
5. `SECURITY.md` — specifically the CORS and secrets-handling commitments; your frontend work must not violate either (no hard-coded URLs/secrets, respect the existing CORS origin rather than working around it).

If anything below conflicts with what you find in these documents or in the repository itself, the repository and its current docs win — note the discrepancy in your final report rather than silently resolving it.

## Workflow

Follow this sequence exactly, in order, and don't skip a step:

```
READ → INSPECT → PLAN → IMPLEMENT → RUN → TEST → DEBUG → VERIFY → DOCUMENT → UPDATE PROJECT_STATUS.md → REPORT
```

- **READ:** the five documents above.
- **INSPECT:** the actual repository — don't take this prompt's description of current state on faith (see next section).
- **PLAN:** briefly state your implementation plan before writing code, so a scope drift is visible if it happens.
- **IMPLEMENT → RUN → TEST → DEBUG → VERIFY:** build, run it for real, test it for real, fix what's broken, confirm it's actually fixed.
- **DOCUMENT / UPDATE PROJECT_STATUS.md / REPORT:** see the Documentation, Git, and Completion Report sections below.

## Context

This is Phase 3 of the AI Smart Traffic Intelligence Platform. Phases 1 (architecture/scaffolding) and 2 (backend foundation) are complete and independently verified — do not rebuild or restructure them. `frontend/` is *claimed* to currently contain only a placeholder `README.md` and empty `src/{pages,components,api}` directories — **verify this yourself** (`ls -la frontend/` and a full listing of `frontend/src/`) before writing anything. If it's not what's claimed, stop and reconcile the discrepancy in your report before proceeding — don't build on top of an assumption you haven't checked.

## Current State You're Building Against (verified — inspect it yourself before writing any code)

The backend is real and running code, not a spec. Specifically:

- **Root health check:** `GET http://localhost:8000/health` → `{"status": "ok", "service": "traffic-platform-api"}` (200)
- **Versioned health check:** `GET http://localhost:8000/api/v1/health` → `{"status": "ok", "environment": "development", "version": "0.1.0"}` (200) — schema defined in `backend/app/schemas/health.py`
- **Error shape on any failure/404:** `{"error": {"code": "...", "message": "..."}}` — see `backend/app/core/exceptions.py`. Design your frontend API client's error handling around this shape, not a generic try/catch.
- **CORS is already configured** for `http://localhost:5173` (`ALLOWED_ORIGINS` in `.env`) — that's the Vite default dev port, so a standard `vite dev` setup should work against the backend without additional CORS changes. If you use a different port, update `ALLOWED_ORIGINS` in `.env` (not `.env.example`, and never commit `.env`).
- **`.env.example` already has `VITE_API_BASE_URL=http://localhost:8000`** — use this convention (Vite requires the `VITE_` prefix to expose an env var to client code). Do not hard-code the backend URL anywhere in `src/`.
- Full endpoint surface planned for later phases is documented in `ARCHITECTURE.md` §7 — you're only building the client foundation now, not calling most of it yet.

Read `ARCHITECTURE.md` §9 (Frontend Architecture) and `PROJECT_STATUS.md` before starting — if anything in this prompt conflicts with what you find in the actual repo, the repo wins; note the discrepancy in your report.

## Objective

Stand up a working React + TypeScript + Vite + Tailwind application with: a real layout (sidebar/header/content), scalable routing with placeholder pages for every planned section, a typed API client, a global UI component set, and a genuine (not faked) backend-health status indicator. It should run, build, and actually talk to the Phase 2 backend.

## Tasks

1. **Scaffold.** Initialize the Vite + React + TypeScript project inside `frontend/` (don't nest another folder level). Configure `tsconfig` with strict mode where practical. Install and configure Tailwind CSS.
2. **Layout.** Build a `Layout` component: sidebar (nav links to every page below), header (app name, backend-status indicator), main content area. Responsive down to tablet width at minimum.
3. **Routing.** Set up a router (React Router is the standard choice; use it unless you have a concrete reason not to) with one route per planned page: Dashboard, Video Analysis, Traffic Analytics, Predictions, Signal Optimization, Emergency Simulation, History, Settings, System Information. Every page beyond Dashboard and System Information should render a clearly-labeled "Not yet implemented — Phase N" placeholder using a shared `EmptyState`/`PlaceholderPage` component — not a blank screen, not fake content.
4. **API client (`src/api/`).** One module responsible for all HTTP calls, typed request/response shapes matching the actual backend schemas above. No `fetch`/`axios` calls inside components — components call functions exported from `src/api/`. Centralize error handling here so it can parse the `{"error": {...}}` shape consistently.
5. **Types (`src/types/`).** TypeScript interfaces for the health response and the shared error shape now; leave room for the rest (videos, analysis, metrics, etc.) to be added in later phases without restructuring.
6. **Environment config (`src/config/`).** Read `VITE_API_BASE_URL` via Vite's `import.meta.env`; fail loudly (a visible dev-time warning, not a silent fallback) if it's missing, rather than silently defaulting to a guessed URL.
7. **Global UI components (`src/components/`).** Button, Card, Badge, LoadingState, ErrorState, EmptyState. Keep this set minimal — build what the layout and placeholder pages actually need, not a speculative full component library.
8. **Backend status indicator.** On an interval (or on mount, your call — state your reasoning), call `GET /api/v1/health` through the API client and render Online/Offline/Checking based on the *actual* response — never hard-code "Online." Handle the network-failure case explicitly (backend unreachable ≠ backend returned an error).
9. **Visual direction.** Dark, modern, clean, data-focused, professional. Good spacing and typography. Subtle animation only where it aids usability (e.g., a loading transition), not decorative. Avoid neon/glassmorphism/generic-admin-template look and gratuitous gradients.
10. **Dashboard page (this phase only, minimal).** A real page shell with a few KPI-card placeholders and the backend status indicator wired in — clearly labeled as placeholder data (e.g., a visible "Demo data" tag on any static numbers), since no real traffic metrics exist yet. Do not invent traffic numbers and present them as if they came from the backend.

## Acceptance Criteria (this phase is not done until every line here is true and verified)

- [ ] `npm install` (or equivalent) completes with no errors.
- [ ] `npm run build` (or equivalent) succeeds.
- [ ] Lint/typecheck (if configured) passes, or documented failures are genuinely pre-existing and out of scope.
- [ ] Dev server starts and the app renders in a browser with zero console errors.
- [ ] Every planned route (Dashboard, Video Analysis, Traffic Analytics, Predictions, Signal Optimization, Emergency Simulation, History, Settings, System Information) navigates correctly; every page except Dashboard shows a clearly labeled "not yet implemented" placeholder.
- [ ] The backend-status indicator shows a genuine Online state while the Phase 2 backend is running, confirmed by actually calling `GET /api/v1/health`.
- [ ] The same indicator shows a genuine Offline/error state when the backend is stopped — tested by actually stopping it, not assumed.
- [ ] No component makes a raw `fetch`/`axios` call directly — all HTTP goes through `src/api/`.
- [ ] No backend URL is hard-coded anywhere in `src/` — it comes from `VITE_API_BASE_URL`.
- [ ] No fabricated traffic/analytics numbers are presented as if real; any placeholder numbers are visibly labeled as such.
- [ ] `backend/` is untouched, unless a genuine defect was found and separately committed with justification.
- [ ] `PROJECT_STATUS.md` reflects the true, verified end state — not the intended one.

**On test scope:** this phase does not require a full component test suite — that's Phase 17 (Testing). "Tests" here means the build, lint/typecheck, and the manual online/offline verification above, all run for real with output captured. If you judge that a couple of targeted tests (e.g., the status indicator's online/offline logic) are cheap and valuable enough to add now, that's a reasonable judgment call — state it as such in your report rather than treating it as a phase requirement you're behind on.

## Explicit Restrictions

Do not: rewrite or restructure the backend; implement YOLO, tracking, vehicle counting, traffic analytics, ML prediction, signal optimization, or emergency simulation; build out full functionality for any page beyond Dashboard's shell; fetch or display fabricated traffic data as if it were real; scatter API calls across components; hard-code the backend URL; skip the offline-state test.

## Files/Directories to Create or Modify

Work within `frontend/` (structure below is a reasonable default — you may adjust it with a stated reason, but keep API logic out of components regardless of exact folder names):

```
frontend/
├── package.json, vite.config.ts, tsconfig.json, tailwind.config.*, .eslintrc* (or equivalent)
├── index.html
└── src/
    ├── main.tsx, App.tsx
    ├── layouts/        (Layout, Sidebar, Header)
    ├── pages/           (one file per planned page)
    ├── components/      (Button, Card, Badge, LoadingState, ErrorState, EmptyState, StatusIndicator)
    ├── api/             (client + health.ts)
    ├── types/
    ├── hooks/           (e.g., useBackendHealth, only if genuinely needed)
    ├── config/          (env access)
    └── styles/
```

Do not touch anything under `backend/` in this phase. If you find a genuine backend defect blocking frontend integration, stop and report it rather than fixing backend code in this prompt's scope.

## Testing (do all of this for real — see the Completion Report format for how to report it)

1. `npm install` (or your package manager of choice) — record any install errors.
2. Start the Phase 2 backend (`uvicorn app.main:app` from `backend/`, against a reachable PostgreSQL — Alembic/DB connectivity isn't required just to serve `/health`, but note if you needed it).
3. Start the frontend dev server.
4. Load the app in a browser (or headless equivalent) — confirm it renders without console errors.
5. Navigate to every route — confirm placeholders render correctly labeled, Dashboard renders its shell.
6. Confirm the status indicator shows Online while the backend is running.
7. Stop the backend, confirm the indicator correctly shows an offline/error state (not a stale "Online," not a crash).
8. Run the production build (`npm run build` or equivalent) and confirm it succeeds.
9. Run lint/typecheck if configured, and fix any errors found.

## Verification

Paste actual command output for install, dev server start, build, and lint/typecheck. Describe what you actually observed in the browser for the online/offline indicator test — a screenshot or explicit description of the rendered state, not an assumption.

## Documentation

Update `PROJECT_STATUS.md`: Phase 3 status, what's implemented, environment info (Node/npm versions actually used), latest successful test. Replace `frontend/README.md`'s placeholder content with an accurate description of what's actually there. If you touched the root `README.md`'s status banner, make sure it stays accurate (currently says "Phases 1–2 of 20 complete; Phase 3 in progress" — update once Phase 3 is genuinely done).

## Git

One commit once everything above is verified working: `feat: initialize frontend foundation`. Do not bundle backend changes into it. If you made a genuine, justified backend fix, commit it separately with its own message.

## Completion Report

Follow the format in `00-master-project-context.md` (what was implemented, files created/modified, dependencies added, exact commands run with real output, test/build results, backend-integration result, known issues, remaining work, exact next phase), and additionally classify the overall phase outcome as one of:

```
VERIFIED
PARTIALLY VERIFIED
NOT IMPLEMENTED
BLOCKED
```

If `BLOCKED`, state exactly what's blocking and what you need to proceed. Never report `VERIFIED` for something you didn't actually run and observe.
