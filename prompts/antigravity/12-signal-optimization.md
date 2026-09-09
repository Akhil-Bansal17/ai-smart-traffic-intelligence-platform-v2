# 12 — Traffic Signal Optimization Simulation

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior software/traffic-systems engineer building a technically credible, explainable **traffic signal optimization simulation** on top of the already-verified traffic intelligence pipeline (Phases 4–11). This is decision-support simulation — not control of physical infrastructure.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md`
3. Backend and frontend structure, existing SQLAlchemy models, Alembic migrations, configuration, `.env.example`, security-related configuration
4. CV services: `detector.py`, `tracker.py`, `vehicle_counter.py`, `traffic_metrics_engine.py`, `lane_analyzer.py`, `analysis_persistence_service.py`
5. The prediction implementation and its real/synthetic-pipeline/synthetic-fixture provenance model (Phase 11/11.1/11.2/closure)
6. All relevant schemas, API routers, frontend API clients
7. The existing Dashboard, Traffic Analytics page, Predictions page, History page
8. Existing tests, existing verification scripts, requirements/dependencies, current database schema

**Do not assume a component exists merely because an earlier report says it does — inspect the actual implementation.** Preserve existing architecture unless a concrete Phase 12 requirement genuinely forces a change.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → TEST → DEBUG → VERIFY
  → REGRESSION → SECURITY REVIEW → DOCUMENT → GIT REVIEW → REPORT
```

Do not blindly trust previous completion reports — the actual repository is the source of truth.

## Context — Current State

Phases 1–11 are complete. **Phase 11 is closed with real-world forecasting `PARTIALLY VERIFIED`**: the platform has 10 legitimate real-world observation buckets, below the project's minimum training threshold of 20. This is intentional and correct — the threshold was not weakened, no data was fabricated or duplicated, and no synthetic data was passed off as real. Phase 11's synthetic-pipeline/synthetic-fixture functionality remains available for development and regression testing, clearly labeled as such. Phase 12 builds on this same honesty discipline: **never claim more than the actual data and the actual implementation support.**

## Objective

```
Traffic Video → YOLO → ByteTrack → Vehicle Counting → Traffic Analytics
  → Lane/Density Metrics → Signal Optimization Engine → Baseline Signal Plan
  → Optimized Signal Plan → Comparison → Simulation Results → React Dashboard
```

Use genuine traffic measurements already produced by the verified Phase 4–10 pipeline to calculate and demonstrate how signal timing *could* be optimized. **This is not autonomous control of physical traffic signals and must never be described or implied as such** — every output is explicitly a "Traffic Signal Optimization Simulation" or equivalent unambiguous wording.

## Core Requirements — Modular Signal Optimization Engine

Investigate and design appropriate abstractions — potential candidates: `SignalPhase`, `SignalPlan`, `Intersection`, `Approach`, `TrafficDemand`, `OptimizationConstraints`, `OptimizationResult`, `SignalOptimizer`, `BaselineSignalPlan`, `OptimizedSignalPlan`, `SignalSimulation`. Use whatever naming actually fits the existing architecture after inspection — these are suggestions, not a mandate to copy verbatim if the project already has better conventions.

## Intersection Model

Support a configurable intersection with multiple approaches — at minimum North/South/East/West. Design the architecture to extend later to 3-arm intersections, multiple lanes, and turning movements, without building a full traffic-engineering platform now — a clean, extensible foundation is the actual Phase 12 deliverable.

## Signal Phase Model

Each phase carries: an identifier, the approaches/movements it controls, green duration, yellow duration, all-red duration if applicable, minimum green, maximum green, and optional clearance time — all configurable, never hard-coded without documenting why a default exists.

## Baseline Signal Plan

Define and document a clearly deterministic baseline strategy — e.g., fixed-time cycle with equal green allocation, configurable cycle length, configurable yellow/all-red clearance. Select the specific strategy after inspecting the project, and document its formula mathematically.

## Optimization Strategy

A first-generation, **explainable** optimization algorithm. **Do not introduce reinforcement learning or claim it's necessary.** Prefer a transparent, constrained approach — demand-proportional green allocation, weighted allocation, constrained search over durations, grid search, a heuristic, or a linear/objective-based optimization — chosen to fit the actual project. It must: consume measured traffic demand; respect minimum/maximum green, yellow/clearance times, and cycle length; allocate available green time; calculate an objective score; produce an optimized plan; and compare it against the baseline.

## Objective Function

Define it explicitly and honestly. Reasonable proxies: estimated waiting time, a queue proxy, demand-weighted delay, phase utilization, a throughput proxy. **Never claim "actual vehicle delay" unless the system genuinely measures or simulates it** — name a proxy as a proxy (e.g., "estimated demand-weighted waiting proxy," not "actual average waiting time"), and document its mathematical definition.

## Traffic Demand Input

Use existing project data whenever available: vehicle volume, flow rate, directional flow, lane density, class distribution, observation duration, approach-level counts — pulled from actual persisted analytics, never fabricated. **If the available database data can't provide approach-specific demand (very plausible given Phase 11's data situation), don't pretend it can** — use an explicitly configurable simulation input instead, clearly labeled as such, with its provenance preserved and clearly distinguished from measured data.

## Real Data vs. Simulation Data (carry forward the project's data-honesty discipline)

Maintain a clear four-way distinction: real-world measured traffic data, synthetic traffic-pipeline data, simulation assumptions/configuration, and optimization outputs. Never label a simulation assumption as a real observation, and never write a fabricated optimization result into the real-world analytics dataset. If synthetic data demonstrates the optimizer, label it explicitly (e.g., `data_source = synthetic_simulation` or an equivalent consistent with the project's existing provenance vocabulary from Phase 11).

## Signal Optimization Simulation

A deterministic simulation/evaluation layer comparing baseline vs. optimized, producing only mathematically-supportable outputs: cycle length, green allocation, phase utilization, demand served, an estimated delay proxy, an estimated queue proxy, a throughput proxy, an optimization score, and an improvement percentage — never an invented realistic-looking number.

## Before/After Comparison

Provide a clear baseline-vs-optimized table (phase, baseline green, optimized green, change) plus measurable comparison metrics. **Any improvement percentage must come from actual simulation output — never hard-code "25% improvement" or similar.**

## Constraint Validation

Validate: minimum/maximum green, yellow duration, all-red duration, total cycle length, phase ordering, non-negative durations, finite numeric inputs, valid traffic demand, valid intersection configuration. Invalid configurations fail safely with the project's existing structured error format.

## Resource and Safety Limits

Bound: number of phases, number of candidate signal plans, optimization iterations, simulation horizon, input size, request execution time, memory usage. Prevent: infinite optimization loops, excessive CPU consumption, huge JSON payloads, malicious numeric inputs, NaN/infinite values, path traversal, arbitrary filesystem access — following the project's existing security architecture, not a new one.

## Database

Inspect the current schema before adding anything — only introduce new tables if persistence is genuinely useful. If needed: `intersections`, `signal_plans`, `optimization_runs`, `optimization_results` (adapt naming to existing conventions) — don't create tables that aren't actually justified. Any change: a new Alembic migration, preserving existing migrations, proper foreign keys, indexes, and constraints, tested upgrade/downgrade/re-upgrade and fresh-database initialization. Don't modify historical migrations.

## API Design

Clean REST API under `/api/v1/signal-optimization`. Candidate endpoints: `GET /info`, `POST /optimize`, `POST /simulate`, `GET /runs`, `GET /runs/{run_id}` — finalize the exact set after inspecting existing API conventions and matching them. Support selecting the traffic-data source, intersection configuration, signal configuration, and optimization/simulation parameters. Structured typed responses, the project's existing error format, no filesystem paths, stack traces, secrets, credentials, or arbitrary file access exposed.

## Frontend

Integrate into the existing React app using its established design system and component conventions. The page should clearly communicate "Traffic Signal Optimization" and include: intersection configuration, traffic-demand source, baseline signal plan, optimization controls, optimized signal plan, before/after comparison, simulation metrics, optimization status, data provenance, and honest limitations. The UI must visually distinguish measured traffic data, simulation inputs, and optimized outputs — every chart/value from a real API response, never fabricated.

## Honest UI Requirement

If insufficient measured traffic data exists for a given optimization mode (likely, given Phase 11's 10-of-20 real observation situation), **do not fabricate data** — show "Insufficient measured traffic data for this optimization mode." If the user selects simulation mode, label it "Simulation Input" and explain the results are simulated, not measured real-world performance.

## No Physical Signal Control (hard boundary)

This phase must not connect to physical traffic lights, send commands to traffic controllers, interact with IoT traffic infrastructure, or claim autonomous or deployment-ready traffic control. It is a simulation and decision-support layer only — say so explicitly in the documentation (see below).

## Testing

**Signal model:** valid phase; invalid phase; invalid duration; min/max green; clearance times.

**Baseline plan:** deterministic output; cycle-length validity; phase-duration correctness.

**Optimization:** low demand; high demand; balanced demand; asymmetric demand; zero demand; one dominant approach; multiple approaches; constraint enforcement.

**Mathematical correctness:** cycle length; green allocation; the objective function; improvement-percentage calculation; normalization; edge cases.

**Safety:** NaN; infinity; negative values; oversized configuration; invalid phase counts.

**API:** successful optimization; invalid request; missing data; structured errors; endpoint behavior.

**Database (if persistence implemented):** creation; retrieval; relationships; deletion; migration; rollback; re-upgrade.

## Real Verification

Create `scripts/verify_phase12_signal_optimization.py`. It must exercise the real implementation, not import classes and assert hardcoded expected numbers. It should: connect to the actual project environment; obtain legitimate traffic input from the existing system where possible; configure a valid intersection; generate the baseline plan; run optimization; validate constraints; run simulation/evaluation; compare baseline vs. optimized; verify outputs are genuinely dynamically calculated; verify no fabricated values; verify persistence and REST API if applicable; print measurable evidence; report execution time; fail clearly if any gate fails.

## Dynamic Behavior Proof (required)

Prove the optimizer actually responds to demand — e.g., balanced demand (Input A) vs. heavily East-West-weighted demand (Input B) should produce genuinely different optimized allocations, both generated dynamically. **Never hard-code expected optimization output just to make a test pass.**

## Baseline vs. Optimized Validation

Demonstrate: the baseline plan exists; the optimized plan exists; the optimized plan satisfies constraints; the objective score is calculated; the comparison is calculated. **If optimization doesn't actually improve the objective for a given input, report that honestly — don't force an improvement to always show.**

## Performance

Measure optimization time, simulation time, and total API execution time where applicable. Keep this phase computationally lightweight — the optimizer should be suitable for interactive dashboard use, not a batch job.

## Regression Requirement

Run the complete existing backend test suite. Re-run verification scripts for at least Phases 5–11. Do not claim Phase 12 `VERIFIED` if anything existing regresses. Run frontend typecheck and build — both must be clean.

## Security Audit

Inspect `.gitignore`, `.env`/`.env.example`, secrets, database credentials, model files, uploads, any generated simulation data, logs, temporary files, API input validation, filesystem access, path handling, and resource limits. Never commit `.env`, secrets, database files, uploaded videos, large generated datasets, model binaries, or temporary files unless explicitly intended and safe.

## Documentation

Update `PROJECT_STATUS.md`, `ARCHITECTURE.md`, and `README.md` only where necessary. Document: the Phase 12 architecture, the optimization algorithm, the mathematical objective, constraints, simulation assumptions, the measured-vs-simulated data distinction, API endpoints, frontend functionality, known limitations, and verification evidence. Include, explicitly and verbatim in spirit: **"This system provides traffic signal optimization simulation and decision support; it does not directly control physical traffic signals."**

## Git

Review `git status` before completing. No accidental files, secrets, generated databases, uploaded videos, temporary artifacts, or unrelated modifications. One focused commit — suggested `feat: implement traffic signal optimization simulation`, but follow existing commit conventions if the repository's actual history suggests something different.

## Strict Scope Exclusions

Do not implement: reinforcement learning, deep RL traffic control, physical traffic-light control, IoT integration, hardware control, V2X integration, autonomous vehicle control, real-time controller communication, a new traffic-prediction architecture, camera calibration, speed estimation, autonomous lane detection, road segmentation, emergency-corridor optimization, cloud deployment, an authentication system, or multi-city production deployment. Those belong to future phases.

## Definition of Done

`VERIFIED` only if all of: actual repository inspected; existing architecture preserved; the optimization engine, baseline plan, and optimization strategy are implemented; the mathematical objective is documented; constraints are enforced; dynamic traffic-demand response is demonstrated; baseline-vs-optimized comparison works; the simulation layer works where applicable; no fabricated optimization metrics exist; real/synthetic/simulation provenance stays distinct; API and frontend work; persistence and migrations work if implemented; automated tests and the Phase 12 verification script pass; existing-phase regression passes; backend tests, frontend typecheck, and frontend build all pass; security review and Git hygiene pass; documentation is updated with known limitations stated. If any critical requirement fails, do not force `VERIFIED` — use `PARTIALLY VERIFIED`, `BLOCKED`, or `FAILED` as appropriate.

## Completion Report

Require:

1. Phase 12 status
2. Architecture implemented
3. Signal model
4. Baseline strategy
5. Optimization algorithm
6. Mathematical objective
7. Constraints
8. Traffic data source
9. Real vs. synthetic vs. simulation distinction
10. API endpoints
11. Frontend implementation
12. Database changes
13. Migration results
14. Automated test results
15. Phase 12 verification results
16. Dynamic-behavior evidence
17. Baseline-vs-optimized evidence
18. Performance timings
19. Full Phase 5–11 regression results
20. Frontend typecheck/build results
21. Security audit results
22. Git status
23. Commit hash
24. Files created/modified
25. Known limitations
26. Exact final classification: `VERIFIED` / `PARTIALLY VERIFIED` / `BLOCKED` / `FAILED`

No vague statements like "everything works" — actual evidence for every item.

## Final Rule

Do not begin Phase 13. Do not implement future features. Do not redesign the existing system. Phase 12 establishes a clean, explainable, testable traffic signal optimization simulation layer on top of the already-verified traffic intelligence pipeline — nothing more.
