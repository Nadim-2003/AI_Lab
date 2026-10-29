# Dhaka University Route Lab

A local AI search application for **Dhaka University and nearby areas**, using real OpenStreetMap driving roads, five manually implemented search algorithms, and simulated road conditions. The default dataset is deliberately small to reduce download time and public-server workload.

See the [Functionality Report](FUNCTIONALITY_REPORT.md) for algorithms, road editing, scenarios, API endpoints, and known limitations.

## Quick start on Windows PowerShell

From `AI_Lab_01`, install dependencies if you have not already done so:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
```

Download the small DU-area dataset:

```powershell
.\setup_data.bat
```

The default bounds are west **90.385**, south **23.718**, east **90.412**, north **23.746**: an explicit rectangle around the campus and nearby areas, approximately 3 km by 3 km. It is not an official campus or administrative boundary. The downloader requests a driving graph and one area of named places. It reports actual counts; the smaller scope does not require 1,000 places.

Start the backend after acquisition finishes:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

In a second terminal, from `AI_Lab_01`:

```powershell
cd frontend
npm ci
npm run dev -- --port 5173
```

Open `http://localhost:5173`. Backend API documentation is at `http://localhost:8000/docs`. If the page was already open, click **Check dataset status** after restarting the backend.

The `200 OK` response from `/api/metadata` reports status; it does not prove routing is ready. `/api/ready` returns 200 only when a usable graph is loaded.

## Existing downloads and alternate areas

Keep your existing `data` directory when updating project files. If a completed dataset is already installed, explicitly replace it with the DU dataset:

```powershell
.\setup_data.bat --replace
```

Existing dataset files are backed up before replacement. Road overrides and scenarios refer to graph edge IDs; review them when changing study areas.

Full Dhaka remains optional:

```powershell
.\setup_data.bat --area dhaka
```

The `dhaka` preset retains the old bounds `[90.30, 23.65, 90.50, 23.90]` and a 3-by-3 place grid. Use `--replace` as well if an installed dataset exists. Old full-Dhaka checkpoints are preserved and reused only for their matching area/server settings.

Advanced options include `--bbox WEST SOUTH EAST NORTH`, `--place-grid N`, and `--overpass-url https://YOUR-HOST/api` for an authorized Overpass service. A custom boundary overrides the area preset. The default place grid is 1 for DU and 3 for full Dhaka.

## Interrupted downloads

Requests are sequential, with bounded retries, backoff, and Retry-After handling. Completed roads and place tiles are saved in `data/download-checkpoints/`; OSMnx also retains `data/osm-cache/`. Rerun the same command to resume. Do not run multiple acquisition processes at once.

If the graph downloaded successfully but the place query failed, install available data offline:

```powershell
.\setup_data.bat --publish-partial
```

This requires a verified graph checkpoint and makes no network requests. It installs the saved graph and available places, marks incomplete place coverage, and enables map-click routing after backend restart. It cannot recover a graph that was never saved.

For older full-city checkpoints, select their original area explicitly:

```powershell
.\setup_data.bat --area dhaka --publish-partial
```

Use the same endpoint and grid options as the original download. Later resume missing places with `--replace` and the same area options. Here, `publish-partial` means installing local dataset files, not uploading data or publishing a cloud environment.

## Connection problems

A smaller area reduces query workload but cannot fix an HTTP rejection or a connection that receives no response. Check access without attempting a dataset download:

```powershell
.\setup_data.bat --diagnose
```

The check sends one GET to `/status` and one tiny POST query to `/interpreter`, reporting HTTP status, elapsed time, content type, response validity, and error category. A 406 from `/status` does not establish whether `/interpreter` works. The check leaves files unchanged and keeps TLS verification enabled. Add `--overpass-url` to diagnose another authorized service.

If the tiny query also fails, wait for the service or compare the same check on another network. Repeated backend restarts cannot create a missing graph. React DevTools advice and pip update notices are informational.

## Local data and behavior

- `data/dhaka.graphml`: directed road graph; the filename is retained for compatibility even for the DU area.
- `data/roads.geojson`: actual road geometries.
- `data/places.json`: valid named OSM source features and road matches.
- `data/metadata.json`: area name/bounds, source, timestamps, actual counts, and place completeness.
- `data/state.sqlite3`: custom scenarios, road overrides, and revision counter.

Data, caches, dependencies, and generated build outputs are excluded from Git. No synthetic production dataset is supplied. Original OSM attributes remain separate from simulated overrides. Normal startup uses saved files and never redownloads the graph. Base-map tiles still require network access.

BFS minimizes hops; DFS/IDS use depth limits; UCS and A* optimize nonnegative generalized cost. Exact selected edges retain direction and parallel-edge identity. Generalized cost is `distance_km × (1 + sum(weight × severity))`, not travel time. Blocked edges are excluded. Scenario conditions apply before saved user overrides. The five algorithms share a snapshot for comparison, and stale routes are hidden.

## macOS / Linux

From `AI_Lab_01`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python scripts/acquire_data.py
.venv/bin/python -m uvicorn backend.app.main:app --port 8000
```

Use the same frontend commands as above. `DATA_DIR` can select a different backend dataset directory; use acquisition's `--output` for that same directory.

## Validation

```bash
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
```

Current checks: **53 backend tests**, **16 frontend tests**, and the production build pass. Tests cover the DU default, explicit boundary overrides, full-Dhaka compatibility, retry/diagnostic handling, offline recovery, routing, geometry, scenarios, and UI state. Public OSM acquisition for the new DU area and routing on the user's laptop remain unverified; tests use synthetic source fixtures where needed.

Browser recovery checks require a backend on port 8000 with an empty dataset directory:

```bash
npm --prefix frontend run test:e2e
```

The runner uses system Chromium when available. Otherwise run `npx playwright install chromium` in `frontend`, or set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`. The three recovery checks use real local FastAPI/Vite processes and mocked map tiles; they do not establish live OSM access.
