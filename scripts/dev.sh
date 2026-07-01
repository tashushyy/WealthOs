#!/usr/bin/env bash
#
# WealthOS local dev launcher.
#
# Starts the FastAPI backend and the Next.js frontend, waits until both are up,
# then opens the app, the API docs, and the GitHub repo in your browser.
# Press Ctrl+C to stop everything.
#
# Prereqs (one-time):
#   pip3 install --break-system-packages -e packages/financial-engine
#   pip3 install --break-system-packages -e "apps/backend[dev]"
#   (cd apps/frontend && npm install && cp -n .env.local.example .env.local)
#
# Usage:  bash scripts/dev.sh

set -u

# --- config ------------------------------------------------------------------
BACKEND_PORT=8000
FRONTEND_PORT=3000
REPO_FALLBACK="https://github.com/tashushyy/WealthOs"

# Repo root = parent of this script's directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Prefer Python 3.12 explicitly — scripts don't load ~/.zshrc, so a bare
# `python3` can resolve to the system 3.9.
PYTHON="python3.12"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python3"

# Kill the whole process group (backend, frontend, and their children) on exit.
trap 'echo; echo "Shutting down…"; kill 0 2>/dev/null' INT TERM EXIT

echo "Starting backend  (http://localhost:${BACKEND_PORT}) with ${PYTHON}…"
"$PYTHON" -m uvicorn app.main:app --reload --port "$BACKEND_PORT" --app-dir apps/backend &

echo "Starting frontend (http://localhost:${FRONTEND_PORT})…"
( cd apps/frontend && npm run dev ) &

# --- wait for services, then open browser ------------------------------------
wait_for() {
  local url="$1" name="$2" i
  for i in $(seq 1 40); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "  (warning: ${name} did not respond in time — opening anyway)"
}

wait_for "http://localhost:${BACKEND_PORT}/health" "backend"
wait_for "http://localhost:${FRONTEND_PORT}" "frontend"

REPO_URL="$(git remote get-url origin 2>/dev/null \
  | sed -E 's#git@github.com:#https://github.com/#; s#\.git$##')"
[ -z "$REPO_URL" ] && REPO_URL="$REPO_FALLBACK"

echo "Opening app, API docs, and repo…"
open "http://localhost:${FRONTEND_PORT}"
open "http://localhost:${BACKEND_PORT}/docs"
open "$REPO_URL"

echo
echo "WealthOS is running. Press Ctrl+C to stop."
wait
