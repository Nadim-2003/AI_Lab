# Functionality Report: Dhaka Route Lab

**Project title:** Intelligent Vehicle Routing System for Dhaka City Under Dynamic Multi-Parameter Real-World Constraints

**Report date:** 29 October 2026

**Project directory:** `AI_Lab_01`

## 1. Purpose and current status

Dhaka Route Lab is an AI laboratory application for studying how five search algorithms find routes through a directed road network under simulated traffic, road-condition, weather, safety, and blockage constraints.

The application contains a Python/FastAPI backend, a React map interface, an OpenStreetMap acquisition script, and automated tests. Users can select endpoints, run searches, inspect results, edit directed road conditions, and manage scenarios once a valid local road dataset is available.

**The implementation is not yet verified as a complete real-Dhaka deployment.** At the last confirmed validation, live OpenStreetMap access was denied by the cloud network policy. Consequently, no real road dataset or place dataset had been loaded. Final browser checks were interrupted by an environment disconnection. These limits are separate from the passing automated tests described below.

## 2. Main user workflow

1. Acquire and save the actual Dhaka road and place datasets using the provided script, then start the backend and frontend.
2. Choose a start and destination using place autocomplete or map clicks.
3. Review the matched road nodes and snapping distances.
4. Select a simulated scenario and a search algorithm, or compare all five algorithms.
5. Inspect the returned road-following routes, measured search statistics, and bounded exploration trace.
6. Click a road to inspect its original attributes and edit simulated conditions or close that direction.
7. Save the override and recalculate. Old results are marked stale and hidden from the map when relevant inputs change.
8. Create or duplicate custom scenarios and compare their routing outcomes.

## 3. Map and endpoint selection

### Interactive map

The frontend uses React Leaflet and Leaflet, centered on Dhaka, with OpenStreetMap tiles and attribution. Implemented controls include zooming, panning, fitting the selected route, road-class filtering, place-category filtering, and individual route visibility toggles.

Roads are requested for the visible geographic bounds rather than sending the entire graph to the browser. The default road response is limited to 2,500 directed edges. When additional edges match, the interface tells the user to zoom in. Place markers are requested at zoom level 13 or above and limited to 100 per viewport query; autocomplete remains a separate way to find places.

### Location search

Start and destination autocomplete supports partial, case-insensitive matching of available names, English names, Bangla names, alternative names, and locality fields. Suggestions show names and categories, with locality when available. Input is debounced by 250 milliseconds. Arrow keys, Enter, and Escape support keyboard interaction. Selected endpoints can be cleared or replaced.

A map click can also supply endpoint coordinates. Both methods call the backend to resolve the coordinates to a graph node. A spatial index accelerates nearest-node lookup, and the returned distance is checked against the snapping limit: 500 meters by default, configurable through the API up to 2,000 meters.

A nearby node does not guarantee a reachable destination or an exact building entrance. Directionality, disconnected components, and closures can still prevent a route.

## 4. Five search algorithms

Each algorithm is manually implemented in its own module. NetworkX supplies graph storage and adjacency access; its built-in routing functions are not used as substitutes for these searches.

| Algorithm | Behavior | What the result means |
| --- | --- | --- |
| Breadth-First Search (BFS) | Explores the graph in increasing hop count | Finds a minimum-hop route when the search completes; does not optimize generalized cost |
| Depth-First Search (DFS) | Explores a branch before alternatives, with a depth limit | Finds a route within the available search budget; no minimum-cost guarantee |
| Iterative Deepening Search (IDS) | Repeats depth-limited search with increasing bounds | Searches increasing route depths; no minimum-cost guarantee |
| Uniform-Cost Search (UCS) | Expands the lowest accumulated-cost frontier entry | Finds a minimum generalized-cost route when the search completes with nonnegative costs |
| A* Search | Uses accumulated cost plus a scaled geographic lower bound | Finds a minimum generalized-cost route under the implemented heuristic conditions when the search completes |

The shared result includes the algorithm name, route-found flag, status, ordered node IDs, exact selected directed edges, cost, physical distance, expanded and generated counts, measured execution time, and a bounded trace.

The API defaults are 100,000 expansions, a three-second search timeout, a maximum DFS/IDS depth of 100, and a trace limit of 300 nodes. Validation imposes upper bounds on configurable limits. A limited search can report `expansion_limit`, `depth_limit`, or `timeout`; these outcomes must not be presented as proof that no route exists. An exhausted unsuccessful search reports `unreachable`.

### A* heuristic and fair comparisons

The geographic heuristic is scaled by the minimum traversable edge cost per geographic endpoint kilometer. This prevents the heuristic from assuming that a kilometer of geographic distance always costs one unit. A zero scale produces a zero heuristic. A separate zero-heuristic A* run supplies a measured comparison when enabled.

All five algorithms in one comparison use the same graph, endpoints, scenario conditions, and saved-override snapshot. Their routes may overlap or differ. The application does not claim that every algorithm returns the same optimal route or that A* always expands fewer nodes than UCS.

## 5. Route geometry and visualization

Algorithms retain the exact selected edge tuple `(u, v, key)`, including the key distinguishing parallel roads. Geometry is constructed from those selected edges, not by choosing an arbitrary edge after node-path reconstruction.

The geometry builder:

- Preserves intermediate points from each road LineString.
- Reverses geometry when necessary to match traversal direction.
- Uses endpoint coordinates when an individual edge has no saved geometry.
- Avoids duplicate adjacent segment-boundary coordinates.
- Validates finite geographic coordinates.
- Returns GeoJSON coordinates in longitude/latitude order.

The frontend converts them to Leaflet latitude/longitude order and draws road-following polylines. It does not substitute a direct start-to-destination line. An unsuccessful search has no route geometry. A start-equals-destination result can contain zero edges and no line.

Routes use consistent colors, visibility checkboxes, dashed patterns for unselected layers, and a thicker selected route. Selecting a result brings it forward. Identical edge sequences are identified in the results panel rather than manufacturing different routes.

## 6. Road inspection and simulated condition editing

Clicking a visible road opens an inspector showing its available name, road class, original OSM identifier, directed endpoints, edge key, length, one-way attribute, and active generalized cost. Missing source attributes are shown as unavailable or unnamed.

Editable simulation fields are:

| Field | Interface values |
| --- | --- |
| Traffic | Low, Moderate, High, Severe |
| Road condition | Good, Fair, Poor |
| Rain/waterlogging | None, Low, Moderate, Severe |
| Safety penalty | Numeric slider from 0 to 1 |
| Road availability | Open or blocked for the selected direction |

Users can save an override, cancel unsaved changes, reset one road, or reset all saved overrides. A closure excludes the selected directed edge from routing. The reverse edge remains unchanged unless separately edited.

Overrides are stored in SQLite separately from the source graph. They do not overwrite original OpenStreetMap road attributes. All traffic, weather, road-condition, and safety values are simulations; no live measurement service is connected.

## 7. Scenarios and precedence

### Built-in scenarios

| Scenario | Implemented default effect |
| --- | --- |
| Normal Day | Zero baseline simulated penalties |
| Heavy Traffic | Traffic severity 1 on primary, secondary, and trunk roads |
| Heavy Rain and Waterlogging | Rain severity 1 and road-condition severity 0.5 on residential, tertiary, and unclassified roads |
| Night Travel | Safety severity 1 on residential, service, and unclassified roads |
| Road Blockage | No automatic closures; requires explicit road overrides or edge closures in a duplicated custom scenario |
| Combined Emergency | Traffic 1, rain 1, road condition 0.5, and safety 1 across all road classes; closures require explicit edge settings |

The built-in scenarios are deterministic and read-only. Selecting a scenario supplies the scenario ID for subsequent road queries and route calculations; it does not rewrite the road graph.

### Custom scenarios

The scenario studio supports creation, naming, descriptions, duplication, editing, and deletion. Users can set road-class conditions, severity values, cost weights, and edge-specific conditions. The selected directed road can be added to the draft with the draft's current conditions. Multiple edges can be added individually. Custom scenarios persist in SQLite.

Scenario comparison accepts up to eight scenario IDs and runs the selected query against their snapshots. Historical comparison results are labeled for rerunning after changing inputs.

### Precedence and result freshness

Conditions apply in this order, with later entries replacing earlier conditions for the edge:

1. Zero baseline conditions.
2. Scenario conditions for matching road classes.
3. Scenario-specific directed-edge conditions.
4. Saved user override for that directed edge.

A saved user override can therefore reopen an edge closed by a scenario. Returning to Normal Day does not remove saved overrides; reset the overrides as well to restore the zero-penalty baseline.

Each routing response has a snapshot identifier and persistence revision. Conditions captured for a comparison remain stable during that comparison. The frontend marks route results stale after endpoint, active-scenario, or observed revision changes, and hides their historical routes from the map. Metadata polling observes external revision changes every 15 seconds; cross-client changes are not pushed instantly.

## 8. Cost model and reported results

The cost model is:

```text
edge_cost = distance_km × (
    1
    + traffic_weight × traffic_severity
    + condition_weight × condition_severity
    + rain_weight × rain_severity
    + safety_weight × safety_severity
)
```

Default weights are traffic 2, road condition 1, rain 2, and safety 1. Severity values are constrained to 0–1, and weights to 0–10. Blocked edges are excluded, not assigned a finite penalty.

The results table displays status, distance in kilometers, generalized cost, route-node count, expanded-node count, generated-node count, and measured search time in milliseconds. A bar chart compares expanded nodes. Search traces show a bounded sequence of expanded node IDs and optional map points; they are separate from the final route.

**Generalized cost is neither kilometers nor actual travel time.** No travel-time or arrival-time estimator is implemented. Search execution time measures the search/result construction, excluding frontend rendering and API network transit.

## 9. OpenStreetMap acquisition and persistence

`scripts/acquire_data.py` uses OSMnx to request a directed driving graph and named OSM features within an explicit study rectangle. The default bounds are west 90.30, south 23.65, east 90.50, and north 23.90. This is a configurable study area, not a verified administrative boundary.

The pipeline preserves disconnected components, parallel edges, OSM identifiers, directionality, road attributes, and available geometries. Named features are deduplicated by OSM element type and ID. Records include available names, category, coordinates, address/locality, source identity, matched node, and snapping distance. Unresolved road matches are reported rather than inventing connections.

| Local resource | Purpose |
| --- | --- |
| `data/dhaka.graphml` | Persistent directed road graph |
| `data/roads.geojson` | Road geometries and associated properties |
| `data/places.json` | Searchable named source features |
| `data/metadata.json` | Boundary, retrieval time, source/license, counts, categories, graph checksum, and quality report |
| `data/state.sqlite3` | Custom scenarios, saved road overrides, and revision counter |
| `data/osm-cache/` | OSMnx request cache |

Existing dataset files require explicit `--replace`; the script copies them to a timestamped backup before replacement. Acquisition is separate from startup, so normal routing does not download the graph repeatedly. Saved local graph/place data supports operation without live Overpass access, although base-map tiles still require their tile service unless another tile source is configured.

The pipeline aims to collect at least 1,000 valid places where source coverage permits. It reports actual counts and warns if fewer are available. **The 1,000-place target has not been verified, and no real-data counts or category breakdown are available yet.** Data files, databases, caches, dependencies, and build outputs are excluded from Git.

## 10. Backend API

FastAPI exposes interactive API documentation at `/docs` and an OpenAPI schema at `/openapi.json` while the backend is running.

| Method | Endpoint | Function |
| --- | --- | --- |
| GET | `/api/health` | Process liveness and dataset-ready flag |
| GET | `/api/ready` | Dataset readiness; returns 503 when unavailable |
| GET | `/api/metadata` | Current dataset statistics, metadata, and revision |
| GET | `/api/places` | Bounded name/category/bounds search |
| GET | `/api/places/{identifier}` | Details for one source place; IDs can include a slash |
| POST | `/api/resolve` | Coordinate-to-road-node resolution with distance limit |
| POST | `/api/routes` | Run one algorithm or all five; includes geometry, metrics, and bounded traces |
| POST | `/api/compare-scenarios` | Compare a routing query across scenarios |
| GET | `/api/scenarios` | List built-in and custom scenarios |
| POST | `/api/scenarios` | Create a custom scenario |
| PUT | `/api/scenarios/{identifier}` | Update a custom scenario |
| DELETE | `/api/scenarios/{identifier}` | Delete a custom scenario |
| GET | `/api/roads` | Bounded viewport road GeoJSON with optional road-class filter |
| GET | `/api/road?id=...` | Inspect one exact directed edge under a scenario |
| PUT | `/api/overrides?id=...` | Save simulated conditions, including closure/open status |
| DELETE | `/api/overrides?id=...` | Reset one road override |
| DELETE | `/api/overrides` | Reset all road overrides |

Pydantic validates request fields and limits. Missing resources return 404, invalid inputs return 422, attempts to edit/delete built-in scenarios return 409, and unavailable datasets return 503. Geometry and traces are returned with routing results; separate geometry/trace retrieval endpoints are not implemented.

## 11. Code organization and startup

| Location | Responsibility |
| --- | --- |
| `backend/app/algorithms/` | Shared search interface plus BFS, DFS, IDS, UCS, and A* |
| `backend/app/geo.py` | Geographic distances, coordinate validation, edge/route geometry |
| `backend/app/service.py` | Dataset loading, spatial indexes, conditions, snapshots, routing orchestration |
| `backend/app/store.py` | SQLite persistence and revisions |
| `backend/app/models.py` | Request and scenario validation models |
| `backend/app/main.py` | FastAPI endpoints and error handling |
| `frontend/src/App.jsx` | Main workflow, result state, comparison dashboard, and road inspector |
| `frontend/src/MapView.jsx` | Leaflet map, roads, places, route layers, and trace points |
| `frontend/src/Autocomplete.jsx` | Debounced endpoint selection and keyboard controls |
| `frontend/src/Conditions.jsx` | Condition editing controls |
| `frontend/src/ScenarioManager.jsx` | Custom scenario management |
| `scripts/acquire_data.py` | Actual OSM graph and place acquisition |
| `backend/tests/`, `frontend/src/*.test.jsx`, `frontend/e2e/` | Backend, component, and browser test definitions |

Use the installation instructions in [README.md](README.md). From `AI_Lab_01`, run the backend and frontend in separate terminals:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm run dev -- --port 5173 --strictPort
```

Vite proxies `/api` requests to backend port 8000. The backend supports a `DATA_DIR` environment variable for an alternative local dataset directory.

## 12. Confirmed verification and remaining limitations

The last completed verification before this documentation update produced:

| Check | Confirmed result |
| --- | --- |
| Backend automated tests | 33 passed |
| Frontend component tests | 10 passed across two files |
| Production frontend build | Passed, with a large-bundle advisory |
| Backend startup | Passed during initial runtime validation |
| Final Chromium/browser tests | Test definitions added; final execution not completed |
| Live OSM service access | Denied by cloud network policy during initial setup |
| Actual Dhaka routing and place coverage | Not verified; no real dataset loaded at the last confirmed check |

Backend tests exercise algorithm traversal, weighted/parallel edge selection, missing/reversed/curved geometry, directionality, unreachable destinations, identical endpoints, search limits, negative costs, closure/reset behavior, snapshot isolation, scenario API/persistence, condition precedence, coordinate snapping, request validation, and English/Bangla place matching. Frontend tests exercise coordinate conversion, API errors, autocomplete, endpoint clearing, condition controls, scenario duplication, missing-data handling, no-route results, stale results, route-visibility state, and opening the road editor. These tests use deterministic synthetic graphs or mocked responses; they do not establish real-Dhaka integration or visual map correctness.

Outstanding work includes enabling required network access, running and validating actual data acquisition, confirming the real node/edge/place counts and category distribution, exercising routes on the saved Dhaka graph, and completing browser verification. Full-city performance is unmeasured. Place clustering, automatic two-way/group road editing, turn-by-turn navigation, route-direction arrows, search-tree edge visualization, live traffic/weather/safety feeds, travel-time estimates, user accounts, and authentication are not implemented. The current application is a local development and AI-lab prototype, not a verified production navigation service.
