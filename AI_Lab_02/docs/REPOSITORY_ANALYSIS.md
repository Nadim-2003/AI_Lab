# Phase 1 — Previous lab inspection

Inspected `AI_Lab_01` README, functionality report, package manifests/lockfiles, startup/install scripts, Python models/service, directed graph algorithms and geometric helpers, React API client, MapView, styling, tests and browser configuration.

Lab 1 is an OSM driving-route laboratory. FastAPI loads a directed NetworkX MultiDiGraph, scenarios/overrides live in SQLite, and BFS/DFS/IDS/UCS/A* operate through a shared search abstraction. Geographic helpers use longitude/latitude GeoJSON coordinates, convert for Leaflet, and preserve directed/parallel edge identity. React/Leaflet renders roads, scenarios, routes and explored nodes; Vite proxies `/api` to port 8000. Its UI uses dark teal headers, green actions and card layouts. Python 3.12 dependencies and frontend package versions are pinned.

Reusable concepts and dependencies: directed graph representation, haversine distance, route geometry conversion, supporting shortest-path search, React Leaflet Polyline/CircleMarker/Tooltip layers, FastAPI/Pydantic validation, Vite proxy, React testing and Chromium workflow. Lab 2 adapts these patterns in its own modules rather than importing Lab 1's application-level SQLite/OSM dependencies into a CSP solver. Its selected unit-to-incident paths and hospital paths are computed, never copied demonstration paths.

Strategy: build `AI_Lab_02` beside Lab 1, retain its stack and design language, choose independent ports, and use an explicit simulated Dhaka road network because the current Lab 1 checkout has no real dataset and acquisition is network-blocked. Keep routing as supporting infrastructure; make allocation the CSP decision. No Lab 1 source, dependency, test or configuration file is modified.

Backward compatibility is established by isolation and checking that Git reports no modifications under `AI_Lab_01`. Its previous onboarding check found one existing metadata test mismatch (study_area nesting), which is unrelated to Lab 2 and deliberately left untouched. No claim is made that Lab 1's missing real dataset now works.
