# 13 — Emergency Corridor Simulation

> Attach `00-master-project-context.md` alongside this prompt.

## Role

You are a senior software/traffic-systems engineer building an **Emergency Corridor Simulation / Signal Priority decision-support layer** on top of the already-verified Phase 12 traffic signal optimization system. This is simulation only — not control of physical infrastructure, emergency dispatch, or emergency vehicles.

## Required Reading (in order, before touching any code)

1. `prompts/antigravity/00-master-project-context.md`
2. `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md`
3. The actual Phase 12 implementation in full: its signal-optimization service, domain models (`SignalPhase`, `SignalPlan`, `Intersection`, `Approach`, etc.), baseline implementation, optimizer, objective/LOS implementation, simulation engine, database models, schemas, API router, and frontend page
4. Existing traffic analytics/lane-analysis services, the existing PostgreSQL/Alembic architecture, existing tests and verification scripts, configuration and security settings

**Do not assume a prior report is correct — inspect the actual implementation.** Reuse existing Phase 12 components; do not duplicate signal models or optimization logic that already exists.

## Workflow

```
READ → INSPECT → PLAN → IMPLEMENT → TEST → DEBUG → VERIFY
  → REGRESSION → SECURITY REVIEW → DOCUMENT → GIT REVIEW → REPORT
```

No speculative architecture, no unnecessary refactoring, no unrelated features.

## Context — Current State

Phases 1–12 are complete. **Phase 12 is reported VERIFIED and CLOSED**, with: configurable intersection topology, traffic approaches, signal phases, deterministic baseline plans, demand-proportional optimization, Webster optimal cycle/split calculation, constrained delay-minimization optimization, delay/queue/throughput proxies, HCM-style LOS classification, baseline-vs-optimized comparison, simulation results, persistence, REST APIs, a React dashboard, and provenance-aware simulation inputs — explicitly not controlling physical traffic lights. **Phase 11 remains closed at `PARTIALLY VERIFIED`** (10 of 20 required real-world observation buckets). **Do not reopen Phase 11, do not weaken its data requirements, and do not fabricate real-world forecasting data** — future improvements there are deferred. Phase 13 builds directly on Phase 12's implementation rather than creating an independent traffic-control architecture.

## Objective

```
Traffic Intelligence → Intersection Traffic Demand → Baseline Signal Plans
  → Emergency Corridor Definition → Emergency Vehicle/Corridor Scenario
  → Signal Priority Strategy → Coordinated Intersection Simulation
  → Baseline vs. Emergency-Priority Comparison → Impact Metrics → React Dashboard
```

Simulate how an emergency-vehicle corridor could receive temporary signal priority through coordinated signal timing. This is a "traffic signal priority / emergency corridor simulation" — explicitly **not** physical signal control, autonomous infrastructure, real emergency dispatch, real vehicle routing, IoT control, or hardware integration.

## Emergency Corridor Model

Design a clean abstraction — candidates: `EmergencyCorridor`, `CorridorNode`, `CorridorSegment`, `EmergencyScenario`, `EmergencyVehicle`, `PriorityRequest`, `SignalPriorityPlan`, `CorridorSimulation`, `CorridorSimulationResult`. These are suggestions — use naming consistent with what Phase 12 actually established.

## Corridor Topology

Support a configurable sequence of intersections (emergency origin → Intersection A → B → C → ... → destination), each connected to the next segment. Support at least 2 intersections, preferably 3+ for a meaningful demonstration, configurable order, travel direction, and corridor/segment length. Do not build a city-wide routing engine.

## Emergency Vehicle Model

A simple, configurable simulation entity: vehicle ID, vehicle type, start/destination intersection, corridor path, start time, a simulated speed or travel-time assumption, and a priority level. **Never claim the system detects a real emergency vehicle unless actual detection functionality genuinely exists** (it doesn't, as of Phase 12).

## Emergency Vehicle Data Honesty (critical — carries forward the project's core discipline)

Distinguish, everywhere: real measured traffic observations, synthetic traffic-pipeline observations, configured simulation inputs, emergency-scenario assumptions, and simulation outputs. An emergency-vehicle scenario is a **simulation input** by default — never label a simulated emergency vehicle as a real detected one.

## Signal Priority Strategy

An explainable strategy — candidates: green extension, early green, phase truncation, safe phase reordering, coordinated green wave, progression-based priority. Select one manageable, well-understood strategy after inspecting Phase 12, rather than several shallow ones. It must: identify corridor intersections, determine expected emergency arrival time at each, calculate compatible signal-timing adjustments, respect safety constraints, produce a priority plan, simulate its effect, and compare it against baseline operation.

## Safety Constraints (non-negotiable)

Emergency priority must never simply force every signal green. Validate: minimum/maximum green, yellow duration, all-red duration, clearance intervals, cycle length, phase ordering, conflicting-movement protection, transition feasibility, maximum priority duration, and recovery after priority. The simulation must explicitly model that conflicting traffic cannot receive simultaneously incompatible green phases — this is the same constraint discipline Phase 12 already established for its optimizer, applied here too.

## Priority Window

Define explicitly and configurably: priority begins at `T_arrival - lead_time`, ends at `T_arrival + clearance_window`. No arbitrary unlimited priority duration.

## Recovery Strategy

After the emergency vehicle passes an intersection, the system must explicitly model a return toward normal operation — e.g., resume baseline plan, phase-safe recovery, bounded cycle correction. The simulation must demonstrate that priority doesn't permanently destroy normal signal timing.

## Multi-Intersection Coordination (one of the most important requirements)

Demonstrate genuine coordination across the corridor — the emergency vehicle's estimated arrival time at each successive intersection should influence that intersection's priority timing, producing a coordinated corridor strategy rather than each intersection independently optimizing without regard to the corridor as a whole.

## Baseline vs. Emergency Priority

Run two scenarios — (A) normal baseline operation, (B) emergency corridor priority enabled — and compare them. Possible measured outputs: emergency corridor travel-time proxy, emergency delay proxy, intersection arrival delay, number of priority interventions, priority duration, general traffic delay proxy, queue proxy, throughput proxy, recovery duration, corridor progression quality. **Only include metrics the simulation actually computes.** Never claim an actual real-world emergency response-time improvement unless the simulation genuinely models it — use honest terminology like "simulated emergency corridor travel-time proxy."

## Trade-Off Analysis (required, not optional)

Emergency priority should not magically improve every metric — a credible simulation shows the trade-off: the emergency corridor potentially improves while other traffic potentially worsens (delay/queue). Report both sides. **Do not force an improvement to appear** — if priority makes the objective worse in a given scenario, report that honestly, the same way Phase 12 was required to report when optimization didn't beat baseline.

## Corridor Performance Metrics

Candidates: baseline corridor travel time, priority corridor travel time, emergency travel-time-proxy improvement, baseline general-traffic delay, priority general-traffic delay, queue impact, number of affected intersections, priority duration, recovery time, total simulation duration. Every metric needs an explicit mathematical definition — no vague metrics.

## Traffic Data Input

Use existing Phase 12 traffic-demand and signal-simulation data wherever possible. If the database lacks corridor-level traffic information (plausible, given Phase 11's 10-of-20 real-observation situation), allow explicitly configured simulation demand, labeled `data_source = simulation_configured` (or the project's actual equivalent vocabulary). Never fabricate measured traffic demand.

## Provenance Model

Maintain the project's existing discipline with clear categories: `real_database_metrics`, `synthetic_pipeline_metrics`, `simulation_configured`, `synthetic_fixture`. Emergency-scenario configuration must never become part of the real-world traffic dataset — never write simulation output into `traffic_metrics` or other real-observation tables.

## Deterministic Simulation

Given the same traffic demand, topology, signal plans, emergency scenario, and simulation parameters, the simulation should be deterministic. If randomness is introduced anywhere, it must be explicit, seedable, documented, and reproducible. Prefer deterministic behavior throughout this phase.

## Database

Inspect whether Phase 12's persistence can already store what's needed — don't create a new model unless necessary. If useful: `EmergencyCorridorSimulationRun`, `CorridorConfiguration`, `PriorityIntervention`, `CorridorSimulationResult` (adapt naming to existing conventions). Any change: a new Alembic migration, never modifying historical ones, tested upgrade/downgrade/re-upgrade and fresh-database init, proper foreign keys/indexes/constraints. Store configuration snapshots so historical simulations stay reproducible.

## API

A clean namespace, e.g. `/api/v1/emergency-corridor`. Candidate endpoints: `GET /info`, `GET /presets`, `POST /simulate`, `POST /optimize`, `GET /runs`, `GET /runs/{run_id}` — finalize after inspecting Phase 12's actual conventions and matching them. Support corridor configuration, intersection sequence, traffic demand, baseline signal plans, emergency-vehicle scenario, priority parameters, and simulation horizon. Typed structured responses, existing error handling, no filesystem paths/secrets/stack traces/credentials/arbitrary file access exposed.

## Frontend

Create or integrate an Emergency Corridor Simulation page using the existing design system — likely route `/emergency-simulation`, but confirm against actual current routing first. Include: corridor topology, intersection sequence, emergency-vehicle scenario, traffic-demand source, baseline signal timing, priority strategy, priority window, simulation controls, a corridor timeline, intersection-by-intersection priority state, baseline-vs-priority metrics, general traffic impact, emergency corridor impact, recovery visualization, provenance, and a simulation disclaimer.

## Corridor Visualization

Provide an understandable, non-decorative visual representation driven entirely by real simulation output — e.g., the emergency vehicle progressing through `[INT A] → [INT B] → [INT C]` with each intersection's actual signal/priority state shown. Never a static illustration disconnected from the API response.

## Timeline

For each intersection, show baseline signal state, priority signal state, emergency arrival time, priority start, priority end, and recovery — all sourced from actual simulation results, none invented for presentation.

## Honest UI

Clearly distinguish measured data, simulation input, simulation output, and assumption. Never present simulation results as real-world measured performance. Display, verbatim in spirit: **"This system provides emergency corridor simulation and decision support; it does not control physical traffic signals or emergency infrastructure."**

## Testing

**Domain models:** valid/invalid corridor; valid intersections; invalid topology; invalid emergency scenario; invalid timing parameters.

**Priority logic:** emergency vehicle reaching an intersection; early green; green extension; the priority window; priority expiration; recovery; multiple intersections; corridor ordering.

**Safety:** minimum/maximum green; yellow; all-red; conflicting phases; maximum priority duration; invalid transitions.

**Dynamic behavior:** at least — a short/simple corridor; a longer corridor; different emergency arrival timing; different traffic demand — output must change dynamically across these.

**Trade-off behavior:** the emergency-corridor metric is calculated; general-traffic impact is calculated; no metric is fabricated; improvement percentages are mathematically derived, not asserted.

**Persistence (if implemented):** create/retrieve a simulation run; configuration snapshot; result persistence; relationship integrity; deletion; migration.

**API:** valid request; invalid request; missing data; malformed corridor; invalid timing; structured errors.

## Dynamic Behavior Proof (required)

Prove genuine dynamism: emergency vehicle traveling A→B→C vs. A→C directly should produce a different priority plan; normal vs. high asymmetric traffic demand should change the priority impact where mathematically appropriate. **Never hard-code expected output values to pass a test.**

## Anti-Fabrication Check

Verify explicitly: no hardcoded improvement percentages, no hardcoded travel-time improvement, no fake emergency-vehicle observations, no fake measured traffic, no fake signal states, no synthetic output inserted into real traffic tables, no misleading "real-world" labels anywhere.

## Real Verification

Create `scripts/verify_phase13_emergency_corridor.py`, exercising the real implementation. It must: connect to the actual environment; load or configure a valid intersection topology; load legitimate traffic demand or explicitly-labeled simulation demand; create a baseline plan; create an emergency corridor; calculate arrival times; generate a priority plan; validate all safety constraints; simulate baseline; simulate emergency priority; compare results; verify recovery; verify multi-intersection coordination; verify dynamic behavior; verify provenance; verify persistence/API if applicable; print measurable evidence; measure execution time; fail clearly on any failed gate.

## Required Verification Evidence

The output must show actual generated values — corridor path, emergency vehicle start/destination, per-intersection baseline state, per-intersection priority state, baseline vs. priority corridor metric with the actual difference, general traffic impact, recovery duration. **No placeholder values.**

## Performance

Measure simulation time, priority-calculation time, API latency, total execution time — the system should stay lightweight enough for interactive use. Bound: number of intersections, simulation horizon, time-step resolution, number of candidate plans, optimization iterations, JSON payload size. Prevent infinite loops and excessive computation.

## Security

Audit: API validation, numeric bounds, NaN/infinity, negative timing, invalid topology, oversized corridor, excessive simulation horizon, excessive candidate plans, filesystem access, secrets, database credentials, `.env`/`.env.example`, generated files, uploaded videos, logs, temporary artifacts. Never commit `.env`, secrets, database files, generated datasets, uploaded media, or temporary artifacts.

## Full Regression

Run `python -m pytest backend/tests -v`. Re-run verification scripts for Phases 5 through 13. Do not claim Phase 13 `VERIFIED` if any existing phase regresses. Run `npm run typecheck` and `npm run build` — both must pass.

## Documentation

Update `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `README.md` where necessary. Document: the Phase 13 architecture, the corridor model, emergency-vehicle simulation, the priority strategy, safety constraints, the recovery strategy, mathematical metrics, the baseline comparison, simulation assumptions, provenance, API, frontend, verification results, and limitations. Include, verbatim in spirit: **"This system provides emergency corridor simulation and decision support; it does not control physical traffic signals, emergency vehicles, or emergency infrastructure."**

## Safety Boundary (hard exclusions)

Do not implement: physical traffic-light control, emergency-vehicle control, ambulance/police/fire dispatch, IoT traffic-controller communication, hardware integration, emergency-services APIs, GPS tracking of real emergency vehicles, autonomous emergency routing, V2X infrastructure, or real-world signal-override commands. Phase 13 is simulation only.

## Strict Scope Exclusions

Do not implement: reinforcement learning, deep RL, autonomous traffic control, real emergency dispatch, physical infrastructure, hardware, IoT, V2X, a new prediction architecture, autonomous lane detection, camera calibration, speed estimation, city-scale routing, cloud deployment, an authentication system, or multi-city production infrastructure. Do not redesign the platform.

## Definition of Done

`VERIFIED` only if all of: actual repository inspected; Phase 12 architecture correctly reused; the emergency corridor model, multi-intersection support, emergency-vehicle simulation, an explainable priority strategy, the priority window, safety constraints, and recovery strategy are all implemented; multi-intersection coordination is demonstrated; baseline and emergency-priority simulation both work; their comparison works; emergency impact and general-traffic impact are both calculated; trade-offs are reported honestly; dynamic behavior is demonstrated; no data is fabricated; provenance is preserved; API and frontend work; persistence and migration work if implemented; unit, integration, and Phase 13 verification-script tests pass; Phase 5–12 regression passes; backend tests, frontend typecheck, and frontend build all pass; security audit and performance limits are verified; Git hygiene passes; documentation and limitations are recorded. If any critical requirement fails, do not force `VERIFIED` — use `PARTIALLY VERIFIED`, `BLOCKED`, or `FAILED`.

## Completion Report

Require:

1. Phase 13 status
2. Architecture implemented
3. Emergency corridor model
4. Intersection topology
5. Emergency vehicle model
6. Priority strategy
7. Priority window
8. Safety constraints
9. Recovery strategy
10. Mathematical formulas
11. Baseline scenario
12. Emergency-priority scenario
13. Traffic data source
14. Provenance classification
15. Baseline vs. priority metrics
16. Emergency corridor impact
17. General traffic impact
18. Trade-off analysis
19. Dynamic-behavior evidence
20. API endpoints
21. Frontend implementation
22. Database changes
23. Migration verification
24. Automated test results
25. Phase 13 verification results
26. Performance timings
27. Phase 5–12 regression results
28. Frontend typecheck/build results
29. Security audit
30. Git status
31. Commit hash
32. Files created/modified
33. Known limitations
34. Exact final classification: `VERIFIED` / `PARTIALLY VERIFIED` / `BLOCKED` / `FAILED`

No vague statements like "everything works" — actual evidence for every item.

## Critical Final Rule

Do not begin Phase 14. Do not implement future features. Do not reopen Phase 11. Do not redesign the existing platform. Do not connect to physical traffic infrastructure. Phase 13 exists only to establish a technically credible, explainable, reproducible Emergency Corridor Simulation and decision-support layer on top of the existing traffic signal optimization system.
