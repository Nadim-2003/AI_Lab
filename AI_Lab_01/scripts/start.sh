set -eu
cd /workspace/AI_Lab/AI_Lab_01
mkdir -p data/runtime
.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > data/runtime/backend.log 2>&1 &
backend_pid=$!
(cd frontend && npm run dev -- --port 5173 --strictPort) > data/runtime/frontend.log 2>&1 &
frontend_pid=$!
trap 'kill "$backend_pid" "$frontend_pid" 2>/dev/null || true' EXIT INT TERM
printf 'Backend PID %s; frontend PID %s. Logs: data/runtime/\n' "$backend_pid" "$frontend_pid"
wait
