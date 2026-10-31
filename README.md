# AI Lab — Dhaka University Route Lab

Explore real OpenStreetMap roads with BFS, DFS, IDS, UCS, and A*. The app includes simulated road conditions, route comparisons, and clickable search traces.

See [the application guide](AI_Lab_01/README.md) for installation, dataset downloads, running the app, and validation.

## Get the latest code

First download:

```bash
git clone https://github.com/Nadim-2003/AI_Lab.git
cd AI_Lab
```

Update an existing clone (commit or stash your local edits first):

```bash
cd AI_Lab
git switch main
git pull --ff-only origin main
```

Updates become available through `git pull` after the changes are committed and pushed to GitHub. Keep your existing `AI_Lab_01/data` directory; it contains downloaded roads and saved scenarios.

## Run on Windows PowerShell

Install Python 3.12 and Node.js with npm. From the repository directory:

```powershell
cd AI_Lab_01
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
npm --prefix frontend ci
.\setup_data.bat
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Leave the backend running. Open a second terminal in `AI_Lab/AI_Lab_01`:

```powershell
npm --prefix frontend run dev -- --port 5173
```

Open `http://localhost:5173` on your computer. Download the dataset only once; subsequent runs need only the backend and frontend commands. Restart the backend after downloading data.

## Run on Linux / macOS

Install Python 3.12 and Node.js with npm. From the repository directory:

```bash
cd AI_Lab_01
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
npm --prefix frontend ci
.venv/bin/python scripts/acquire_data.py
.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000
```

In a second terminal, from `AI_Lab/AI_Lab_01`:

```bash
npm --prefix frontend run dev -- --port 5173
```

## Click an explored node

1. Select start and destination, then run an algorithm or compare all five.
2. Select the algorithm in the results table and expand **Bounded search trace**.
3. Click any node ID. The map centers on that node, shows a yellow marker, and displays its ID, latitude, and longitude. Clicking the same ID again recenters it.
4. Enable **Show explored nodes for selected algorithm** to see the whole trace; these markers are clickable too.

Searches capture up to **5,000 explored nodes per algorithm**. This is a trace limit, not a request to generate 5,000 new road nodes: smaller searches naturally capture fewer nodes. Search expansion, depth, and time limits still apply. Changing endpoints or conditions makes old results stale; run the search again before selecting trace nodes.

## Checks and troubleshooting

From `AI_Lab_01` on Linux/macOS:

```bash
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
```

On Windows use `.\.venv\Scripts\python.exe` instead of `.venv/bin/python`.

`/api/health` checks the server; `/api/ready` must return HTTP 200 before routing works. If data acquisition fails, run `python scripts/acquire_data.py --diagnose` using your virtual environment's Python. Network access to `overpass-api.de` is required for downloads, and `tile.openstreetmap.org` supplies background tiles. Do not delete an existing dataset to troubleshoot a connection failure.
