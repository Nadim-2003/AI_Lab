# Dhaka Route Lab

FastAPI and React/Leaflet vehicle routing application with five manually implemented search algorithms, exact directed-edge geometry, simulated road conditions, persisted overrides, and built-in/custom scenarios.

## Setup

Requires Python 3.12 and Node.js 24. From this directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
cd frontend
npm ci
npm run build
```

## Real OpenStreetMap data

From this directory:

```bash
.venv/bin/python scripts/acquire_data.py
```

The default explicit study rectangle is west 90.30, south 23.65, east 90.50, north 23.90. It is not an administrative boundary. Override it with `--bbox WEST SOUTH EAST NORTH`. Downloads require HTTPS access to overpass-api.de; map tiles use tile.openstreetmap.org. Existing datasets require explicit `--replace`, which creates a backup.

The acquisition script stores the directed driving graph, actual road geometries, named places, source metadata, counts, category breakdown, and quality report in data/. No synthetic production dataset is supplied. Restart the backend after acquisition. Retain data/ locally; it is excluded from Git. Traffic, weather, road conditions, and safety are simulations, not live measurements. Overrides are separate from the original graph, in data/state.sqlite3.

## Run

In separate terminals, from this directory:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm run dev -- --port 5173 --strictPort
```

Vite proxies /api to port 8000. Backend API documentation is at /docs. /api/health reports process liveness; /api/ready returns 503 until valid road data is loaded. A missing dataset is shown explicitly in the interface.

## Validation

```bash
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
```

With the backend running and Chromium installed at /usr/bin/chromium:

```bash
npm --prefix frontend run test:e2e
```

Initial validation passed 33 backend tests, 10 frontend component tests, a frontend production build, and backend startup. The cloud environment disconnected during final browser checks. Live OSM access was denied by network policy, so actual Dhaka dataset counts, 1,000-place coverage, and routing on the real dataset remain unverified. Synthetic graphs are confined to automated tests.

## Routing behavior

BFS minimizes hops. DFS and IDS have explicit depth limits. UCS optimizes nonnegative generalized cost. A* uses a geographic distance bound scaled by the minimum traversable edge cost per endpoint kilometer; a zero-heuristic comparison is also measured.

Generalized cost = distance_km × (1 + sum(weight × severity)). It is not physical distance or travel time. Blocked directed edges are excluded. Precedence is baseline, scenario class conditions, scenario-specific edge conditions, then saved user override. All algorithms in a comparison use the same cost snapshot. Limits and bounded traces are reported; stale results are hidden from the map.
