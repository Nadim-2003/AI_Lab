# Verification record

Executed in this cloud workspace with Python 3.12.14, Node 24.19.0 and system Chromium.

| Check | Outcome |
| --- | --- |
| Backend pytest suite | **42 passed**, including parameterized cases and exhaustive three-variable comparisons |
| Frontend Vitest | **2 passed** |
| Chromium integration | **4 passed** against actual FastAPI/Vite processes |
| Production Vite build | Passed |
| Repeat installation script | Passed |
| Fresh isolated Python install | Lockfile installed, `pip check` passed, all 42 backend tests passed |
| Experiment matrix | 280 measured runs; every returned allocation subset independently validated with zero hard violations |
| Lab 1 preservation | `git diff -- AI_Lab_01` empty; all repository changes are under the new `AI_Lab_02` folder |

The browser checks cover medical allocation, fire multi-resource allocation, physical inventory/availability editing, clearing stale allocations, measured comparison, responsive/mobile layout, full JSON editor availability, and a genuine nonchronological backjump. They also verify that the number of map dispatch-route layers equals the number of returned assignments. Optional OSM tiles remain off, so no external map service is required.

Backend coverage includes compatibility, capacity/capabilities, availability/release time, physical exclusivity, passenger counts, multi-resource quantities, deadlines, budget, blocked and alternate roads, unreachable hospital transport, hospital capabilities and cumulative beds, simultaneous shortages, severity ordering, limits, independently detecting tampered assignments, FC restoration/early detection, AC-3/MAC correctness, global constraints outside binary AC, CBJ conflict propagation, seeded generation/scaling, API input/reference validation, comparison fairness and raw local-search conflict reporting. Exact solvers are checked against exhaustive references for binary and small global-constraint instances.

Warnings: Starlette emits an AnyIO deprecated alias warning under the pinned dependency set. Vite reports a large JS bundle (Leaflet/Recharts); the production build succeeds. These are not failed checks. Browser screenshots are generated in ignored `frontend/test-results/`. The app is an academic simulation; tests do not verify real-world Dhaka roads, live traffic or operational dispatch safety.
