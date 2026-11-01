# Requirement coverage and implementation locations

| Major requirement | Implementation / evidence |
| --- | --- |
| Inspect and preserve Lab 1 | `REPOSITORY_ANALYSIS.md`; independent folder and ports; no changes to Lab 1 |
| FastAPI + React | `backend/app/main.py`, `frontend/src/App.jsx`, Vite proxy |
| Formal CSP=(X,D,C) | `CSP.md`, `problem.py`: one physical resource assignment per demand slot |
| Four emergency categories and extensibility | `generation.py:demands`, `models.py:Requirement/Incident/Generate.rules`; custom earthquake rule test |
| Configurable quantities, severity and circumstances | Requirement list, quantity, patients, capacity/capabilities; severity defaults and full JSON editor |
| Physical resources at several locations | Resource IDs, station/home/current nodes, availability/release times, capacities, capabilities and costs; five centers with multiple units |
| C1 compatibility | Role filtering and independent type validation |
| C2 availability | Available flag + release time compared to request timestamp |
| C3 exclusivity | Shared binary conflict, AC support and final physical-ID counting |
| C4 deadline | Shortest response minutes <= incident deadline, independently recomputed |
| C5 roads | Blocked directed edges excluded by router and rejected by validator |
| C6 capacity | Per-slot capacity and capability requirements, patients <= physical unit capacity |
| C7 budget | Global total dispatch and distance operating cost, checked in all methods and independently recomputed |
| C8 distance/time | Cached Dijkstra; actual selected edges, geometry, travel time and distance |
| C9 multiple resources | Expand every quantity into separate slots; full/partial/unserved depends on all incident slots |
| C10 hospitals | Compatible reachable transport routes + cumulative patient beds; separate response/transport times |
| C11 priority | Configurable severity/deadline ordering and optional severity-based deadline generation; no hard rule relaxed |
| C12 conflicts | BT/CBJ/FC/AC/local search share constraints; explanations for empty domains and conflicts with returned subset |
| Actual chronological BT | `solvers/backtracking.py`, exhaustive-reference tests |
| Actual conflict-directed backjumping | `solvers/backjumping.py`, conflict sets, propagated causes, nonchronological jump count, production witness |
| Look-ahead / FC | `solvers/forward_checking.py`, trailed pruning, wipeout and restoration tests |
| Arc consistency | `solvers/arc_consistency.py`; AC-3 preprocessing and optional MAC; global constraints remain outside binary AC |
| Local search | `solvers/local_search.py`; seeded min-conflicts, bounded restarts, raw conflicts + valid repaired subset |
| Applied MRV, degree, LCV | `solvers/common.py`; configurable in UI and compared as distinct presets |
| All workload scales | Scale generator/configurations and committed measurements through 300 incidents |
| 30/60/120 sensitivity | `evaluation.py`; clones one base scenario, changes deadlines only |
| Budget/supply/capacity experiments | Pressure matrix: budget up/down, ambulance/rescue shortages, busy fire, zero beds, blocked corridor, all-severe competition |
| Geographic visualization | `MapView.jsx`: nodes/roads/centers/hospitals/incidents, role-colored computed routes, blocked edges, response vs transport |
| Control center | Incident/resource/hospital tables, map addition, inventory availability, selected incident edits, JSON validation/export, solver controls |
| Results and charts | Served counts, selected units, ETAs, hard violations, failures, bounded trace, runtime chart and runtime/steps/coverage/checks experiments |
| Fair comparison | Same immutable scenario/domain preparation, option labels, scenario fingerprints, controlled repeat seeds, measured timing excluding generation/rendering |
| Independent validation | `validation.py` recomputes hard rules and selected paths; shared by all solver result handling |
| Automated tests | Backend constraint/algorithm/API/exhaustive tests; frontend controls/error tests; real-service Chromium map/allocation/mobile tests |
| Reproducible demonstrations | `demos/`, `DEMO_GUIDE.md`, `scripts/make_demos.py` and actual measured CBJ witness |
| Documentation | README setup/commands/structure, CSP/algorithm explanations, experiment observations, demos, preservation and this mapping |

## Explicit scope boundaries

No live OSM road import is implemented in Lab 2. The previous lab remains available for actual OSM route analysis when its data can be downloaded. Its directed graph/map patterns are reused in an independently runnable simulated allocation application. The application is in-memory and single-scenario, without operational persistence/authentication. Resources cannot be reused within a solve, even after displayed release times; hospital discharges are not modeled. Partial allocations and local-search repaired subsets are not maximum-coverage solutions. Exhaustion can prove complete infeasibility; time/step limits cannot. Large workloads are supported for bounded experimentation, not guaranteed rapid complete allocation. These are documented design assumptions and limitations rather than hidden relaxations of hard constraints.
