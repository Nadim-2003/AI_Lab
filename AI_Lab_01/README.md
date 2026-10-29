# Dhaka Route Lab

FastAPI and React/Leaflet vehicle routing application with five manually implemented search algorithms, exact directed-edge geometry, simulated road conditions, persisted overrides, and built-in/custom scenarios.

See the [Functionality Report](FUNCTIONALITY_REPORT.md) for user workflows, algorithms, scenario behavior, API endpoints, verified results, and remaining limitations.

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

## Windows quick start and 503 troubleshooting

A `503` from `/api/roads` or `/api/places` means the backend has no usable road graph. Check `http://localhost:8000/api/metadata` for the actual loading error. The map tiles alone do not supply routing data.

After installing Python 3.12 and Node.js, use Windows Command Prompt:

```bat
cd C:\Users\HP\Downloads\AI_Lab\AI_Lab_01
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
setup_data.bat
```

Allow the OSM download to finish. It needs access to `overpass-api.de` and can take several minutes. No dataset is bundled in GitHub. If acquisition fails, read the command's error output; repeatedly refreshing the map will not create the missing data. The helper accepts acquisition options, for example `setup_data.bat --replace` to explicitly back up and replace an existing dataset. Avoid replacing a dataset unnecessarily, since saved scenarios refer to its edge IDs.

Then start or restart the backend:

```bat
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

In another Command Prompt:

```bat
cd C:\Users\HP\Downloads\AI_Lab\AI_Lab_01\frontend
npm ci
npm run dev -- --port 5173
```

Open `http://localhost:5173`. If it was already open, click **Check dataset status** after restarting the backend. `http://localhost:8000/api/ready` should return 200 with `ready: true`. If the graph still fails to load, inspect `/api/metadata` before downloading again. If `DATA_DIR` is configured, acquisition must use the same directory via `--output`.

While metadata reports that the dataset is unavailable, the frontend disables place search and map endpoint selection and does not request road/place layers. The setup panel displays recovery steps. A bundled SVG favicon replaces the missing icon. React's “Download the React DevTools” console message is an informational development message, not a failure.

## Validation

```bash
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
```

With a backend using an empty dataset directory running on port 8000, browser recovery checks can be run as follows. The runner uses system Chromium when available; otherwise install its browser with `npx playwright install chromium` from `frontend`. You can set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to a custom browser executable:

```bash
npm --prefix frontend run test:e2e
```

Current automated validation passes 35 backend tests and 14 frontend component tests, including dataset-readiness gating, recovery after restart, and acquisition/file-backup behavior with synthetic source fixtures. The frontend production build and three Chromium browser checks also pass. Browser checks cover the missing-data workflow with a real local backend and mocked map tiles, including mobile layout, favicon loading, and suppression of unavailable road/place requests. Live OSM access was denied during initial setup, so actual Dhaka dataset counts, 1,000-place coverage, and routing on the real dataset remain unverified. Synthetic graphs are confined to automated tests.

## Routing behavior

BFS minimizes hops. DFS and IDS have explicit depth limits. UCS optimizes nonnegative generalized cost. A* uses a geographic distance bound scaled by the minimum traversable edge cost per endpoint kilometer; a zero-heuristic comparison is also measured.

Generalized cost = distance_km × (1 + sum(weight × severity)). It is not physical distance or travel time. Blocked directed edges are excluded. Precedence is baseline, scenario class conditions, scenario-specific edge conditions, then saved user override. All algorithms in a comparison use the same cost snapshot. Limits and bounded traces are reported; stale results are hidden from the map.
