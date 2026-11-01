# AI Lab 2 — Dhaka Emergency Response CSP

A working **FastAPI + React + Leaflet** mini-project for Emergency Response Coordination and Resource Allocation using constraint satisfaction. The sibling `AI_Lab_01` is preserved. This project uses the same Python/React stack, directed node/edge representation, shortest-path support, teal control-center design, Leaflet layers and geographic coordinate conventions, without requiring Lab 1's unavailable OSM download.

**All default geography, roads, traffic, dispatch centers, hospitals, costs and operational quantities are simulated.** They are suitable for an academic demonstration, not real emergency dispatch. The default map works offline; optional OSM tiles require Internet access. A feasible CSP allocation is never labeled globally optimal.

## Run

Requires Python 3.12, Node.js 22+ (tested with Node 24), npm and Bash on Linux/macOS. From the repository root:

```bash
cd AI_Lab_02
bash scripts/install.sh
bash scripts/start.sh
```

The frontend listens on port **5174**, backend on **8002**, and FastAPI's interactive API documentation is at `/docs` on the backend. Logs are `.runtime/backend.log` and `.runtime/frontend.log`. Stop the startup script with Ctrl+C; it stops both child processes. Lab 1 uses separate ports 5173/8000.

Alternatively, run these in separate terminals from `AI_Lab_02`:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8002
npm --prefix frontend run dev -- --port 5174 --strictPort
```

Windows: create the environment using `py -3.12 -m venv .venv`, install with `.venv\Scripts\python.exe -m pip install -r requirements.lock`, run `npm --prefix frontend ci`, and use `.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8002` plus the frontend command above. Bash scripts themselves require Bash.

## What works

- Medical, fire, road accident and flooding incidents, with severity-dependent demand defaults, configurable requirements and quantities, patient counts, capabilities, deadlines and service durations. Custom categories can provide their own demand rules.
- Multiple physical ambulances, fire units and rescue teams across five configurable dispatch centers. Pools scale with the number of required slots, with shortage and occupied-unit controls.
- Directed shortest-time Dijkstra routes around blocked roads, simulated traffic, response deadlines, reachable hospitals and separate patient-transport routes/ETAs.
- Chronological backtracking, actual conflict-directed backjumping, forward checking with domain restoration, AC-3 preprocessing and optional maintaining arc consistency (MAC), and bounded min-conflicts with restarts.
- MRV, degree tie-breaks, LCV, and documented severity/deadline ordering. Plain and combined heuristic presets separate their effects from the search method.
- Shared hard constraints and a final validator that recomputes route accessibility, times, capacity, availability, exclusivity, costs and cumulative hospital occupancy independently of domain filtering.
- Map overlays from actual solver results, incident inspection, resource inventory, hospital bed editing, incident addition on the map, directed road blocking and complete scenario JSON editing/export.
- Fully served, partially served and unserved outcomes, explicit infeasibility/limits, search traces, constraint reasons, measured comparisons, charts, repeated runs and JSON/CSV exports.
- All requested scales (10, 20, 30, 50, 100, 150, 250, 300), 30/60/120-minute sensitivity and budget/resource/hospital/road pressure experiments.

## Tests and experiments

```bash
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
# Start backend/frontend first. Browser checks use real local API calls.
npm --prefix frontend run test:e2e
```

Browser tests use `/usr/bin/chromium` by default. On another machine, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to a locally installed Chromium executable, or edit the configuration to use a Playwright-managed installation. No browser download is needed on this cloud machine.

Run measured experiments, including two controlled solver seeds per configuration:

```bash
.venv/bin/python scripts/benchmark.py --timeout .25 --steps 3000 --repeats 2
.venv/bin/python scripts/make_demos.py
```

`results/scale.json`, `deadline.json`, `pressure.json` and corresponding CSV files contain **actual executed measurements**, not demonstration constants. Limits are deliberately short for a reproducible lab run; increase them within the documented batch limits for further analysis. The UI can run trials with up to 2 seconds / 10,000 steps per method and up to three repeats. See [experiment observations](docs/EXPERIMENTS.md) for practical interpretation.

## Project structure

```text
backend/app/models.py          Validated incident/resource/hospital/scenario schema
backend/app/generation.py      Seeded scenarios and configurable demand rules
backend/app/routing.py         Cached directed shortest-time Dijkstra
backend/app/problem.py         Resource slots, unary domains, shared constraints
backend/app/validation.py      Independent final solution validator
backend/app/solvers/           Backtracking, CBJ, FC, AC-3, local search + heuristics
backend/app/service.py         Validated allocation results, ETAs and unmet reasons
backend/app/evaluation.py      Same-instance comparisons and experiment matrix
backend/app/main.py            FastAPI endpoints
backend/tests/                Constraint, algorithm, exhaustive-reference and API tests
frontend/src/                 React control center, Leaflet map and measured charts
frontend/e2e/                 Real-service Chromium tests
scripts/                      Installation, startup, demo generation and benchmarks
demos/                        Full JSON scenarios and generation configurations
results/                      Measured benchmark data
```

## API examples

`POST /api/scenarios` takes generation settings such as `{"count":50,"seed":42,"deadline":60,"supply":1.05}`. Custom rules can override or extend default demands. When rules are supplied, generation samples from the supplied categories:

```json
{"count":10,"rules":{"earthquake":[{"role":"rescue","quantity":2,"capacity":4,"capabilities":["rescue"]}]}}
```

`POST /api/solve` takes `{"scenario": <complete scenario>, "options": {"algorithm":"backjumping","mrv":true,"lcv":false,"timeout":2,"max_steps":10000}}`.

`POST /api/compare` takes one complete scenario and a list of option objects. `POST /api/experiments` takes `kind` (`scale`, `deadline`, `pressure`), `generation`, an `options` list and `repeats`. `/api/validate-scenario` checks edited scenario schemas and references. `/api/health` checks that the backend runs; successful allocations additionally require `validation.valid` and all resource slots assigned.

Scenario JSON controls every requirement quantity, resource/current/home location, availability/release time, capabilities, costs, capacity, incident timestamp, service duration, hospital beds and road travel-time input. Stations do not imply a one-vehicle limit.

## Academic documentation

- [CSP formulation, constraints and assumptions](docs/CSP.md)
- [Algorithms, heuristics, metrics and architecture](docs/ALGORITHMS.md)
- [Measured experiments and limitations](docs/EXPERIMENTS.md)
- [Eight demonstrations for the instructor](docs/DEMO_GUIDE.md)
- [Requirement-to-implementation mapping](docs/REQUIREMENTS.md)
- [Repository analysis and preservation](docs/REPOSITORY_ANALYSIS.md)

## Limits

This is a simultaneous snapshot allocation model: no resource reuse, return trips, hospital discharge, live GIS/traffic, authenticated multi-user dispatch or operational persistence are modeled. Patient transport is modeled after service; response deadlines apply to arrival, not transport completion. Beds are reserved conservatively for the entire scenario. Partial allocations are valid subsets, not proven maximum coverage. Local search does not prove infeasibility except when a unary domain is empty. Exact search may time out, especially with scarce resources and large instances; the UI and exported results preserve those outcomes. AC-3 handles binary constraints only; budget and cumulative beds remain global checks. Map incident clicks snap to the nearest network node; off-network travel is not modeled. The default generated grid is a schematic over Dhaka coordinates, not the actual city's road topology. Existing Lab 1 OSM data is not automatically imported.

See [the verification record](docs/TEST_REPORT.md) for executed checks and their scope.
