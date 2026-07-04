#!/usr/bin/env bash
#
# start.sh — boot Degree Copilot end-to-end.
#
# Starts the FastAPI backend (port 8000) and the Vite frontend (port 5173)
# in parallel. Handles venv creation, dependency install, port conflicts,
# orphan uvicorn processes, and Ctrl+C cleanup.
#
# Usage:
#   ./start.sh             boot everything
#   ./start.sh --clean     also wipe the SQLite DB so it reseeds fresh
#   ./start.sh --no-reload boot uvicorn without --reload (slightly faster)
#   ./start.sh --help      show this message
#
# Tested on macOS + Linux. Requires: python3, node, npm.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$SCRIPT_DIR/apps/api"
WEB_DIR="$SCRIPT_DIR/apps/web"
DB_PATH="$API_DIR/degreepilot.db"

# ---- colors ----
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

log()  { echo -e "${BLUE}[degree-copilot]${RESET} $*"; }
ok()   { echo -e "${GREEN}[ok]${RESET} $*"; }
warn() { echo -e "${YELLOW}[warn]${RESET} $*"; }
err()  { echo -e "${RED}[error]${RESET} $*" >&2; }

# ---- args ----
CLEAN=0
RELOAD_FLAG="--reload"
for arg in "$@"; do
  case "$arg" in
    --clean) CLEAN=1 ;;
    --no-reload) RELOAD_FLAG="" ;;
    -h|--help)
      cat <<'EOF'
start.sh — boot Degree Copilot end-to-end.

  ./start.sh             boot API (:8000) and Web (:5173)
  ./start.sh --clean     wipe SQLite DB so the API reseeds on boot
  ./start.sh --no-reload boot uvicorn without --reload
  ./start.sh --help      show this message

Press Ctrl+C to stop both services cleanly.
EOF
      exit 0
      ;;
    *) err "Unknown arg: $arg"; err "Try: ./start.sh --help"; exit 1 ;;
  esac
done

# ---- child PIDs ----
API_PID=""
WEB_PID=""

cleanup() {
  echo
  log "Shutting down…"
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$WEB_PID" ]] && kill "$WEB_PID" 2>/dev/null || true
  # Kill any descendants (e.g., uvicorn's reload child, vite worker)
  pkill -P $$ 2>/dev/null || true
  ok "Stopped."
  exit 0
}
trap cleanup INT TERM

# ---- preflight ----
log "Checking prerequisites…"
for cmd in python3 node npm; do
  command -v "$cmd" >/dev/null || { err "$cmd is required but not installed"; exit 1; }
done
ok "python3 $(python3 --version 2>&1 | awk '{print $2}') · node $(node --version) · npm $(npm --version)"

# ---- clean DB if requested ----
if [[ $CLEAN -eq 1 ]]; then
  log "Cleaning database + lock files…"
  rm -f "$DB_PATH" "$DB_PATH-journal" "$DB_PATH-wal" "$DB_PATH-shm"
  ok "Database cleared. Will reseed on API boot."
fi

# ---- free ports if held ----
free_port() {
  local port=$1
  if lsof -ti :"$port" >/dev/null 2>&1; then
    warn "Port $port is in use. Killing the process holding it…"
    lsof -ti :"$port" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}
free_port 8000
free_port 5173

# Also nuke any stale uvicorn processes from this project
if pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
  warn "Stale uvicorn process(es) found. Killing…"
  pkill -f "uvicorn app.main:app" 2>/dev/null || true
  sleep 1
fi

# ---- backend setup ----
log "Setting up backend (apps/api)…"
cd "$API_DIR"
if [[ ! -d .venv ]]; then
  log "Creating Python venv…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if ! python -c "import fastapi, bs4, httpx, sqlmodel" 2>/dev/null; then
  log "Installing Python dependencies…"
  pip install --quiet --upgrade pip
  pip install --quiet -r requirements.txt
fi
ok "Backend ready."

# ---- frontend setup ----
log "Setting up frontend (apps/web)…"
cd "$WEB_DIR"
if [[ ! -d node_modules ]]; then
  log "Installing npm dependencies…"
  npm install --no-audit --no-fund
fi
ok "Frontend ready."

# ---- boot both ----
log "Booting services…"
cd "$API_DIR"
# shellcheck disable=SC2086
uvicorn app.main:app $RELOAD_FLAG --host 127.0.0.1 --port 8000 &
API_PID=$!

cd "$WEB_DIR"
npm run dev &
WEB_PID=$!

sleep 2
echo
echo -e "${BOLD}Degree Copilot is up:${RESET}"
echo -e "  ${GREEN}API${RESET}    http://localhost:8000        ${DIM}(Swagger at /docs · PID $API_PID)${RESET}"
echo -e "  ${GREEN}Web${RESET}    http://localhost:5173        ${DIM}(PID $WEB_PID)${RESET}"
echo
echo -e "${DIM}Press Ctrl+C to stop both.${RESET}"
echo

# Wait for either to die; if one drops, take the other down too.
while true; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    err "API process exited unexpectedly."
    cleanup
  fi
  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    err "Web process exited unexpectedly."
    cleanup
  fi
  sleep 2
done
