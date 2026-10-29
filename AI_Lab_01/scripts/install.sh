set -eu
cd /workspace/AI_Lab/AI_Lab_01
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
cd frontend
npm ci --no-audit --no-fund
npm run build
