#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
mkdir -p .runtime
.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8002 > .runtime/backend.log 2>&1 &
backend_pid=$!
node frontend/node_modules/vite/bin/vite.js frontend --host 0.0.0.0 --port 5174 --strictPort > .runtime/frontend.log 2>&1 &
frontend_pid=$!
trap 'kill "$backend_pid" "$frontend_pid" 2>/dev/null || true' EXIT INT TERM
printf 'Lab 2: backend port 8002, frontend port 5174; logs in .runtime/\n'
wait -n "$backend_pid" "$frontend_pid"
