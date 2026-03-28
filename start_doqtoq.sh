#!/bin/bash

# ============================================================
#  DoqToq — Startup Script
#  Starts all three services: Qdrant, FastAPI backend, React frontend
#
#  Usage:
#    chmod +x start_doqtoq.sh
#    ./start_doqtoq.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colors ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log()  { echo -e "${CYAN}[doqtoq]${NC} $*"; }
ok()   { echo -e "${GREEN}[doqtoq]${NC} $*"; }
warn() { echo -e "${YELLOW}[doqtoq]${NC} $*"; }
err()  { echo -e "${RED}[doqtoq]${NC} $*"; exit 1; }

echo ""
echo -e "${BOLD}  DoqToq — Discussion Room AI${NC}"
echo "  ─────────────────────────────"
echo ""

# ── 1. Check .env ──────────────────────────────────────────
if [[ ! -f ".env" ]]; then
    warn ".env not found — copying from .env.example"
    cp .env.example .env
    warn "Edit .env with your API keys before proceeding."
    echo ""
fi

# ── 2. Resolve Python ──────────────────────────────────────
PYTHON_BIN=""
for candidate in "venv/bin/python" "venv/Scripts/python" "python" "python3"; do
    if command -v "$candidate" &>/dev/null || [[ -x "$SCRIPT_DIR/$candidate" ]]; then
        PYTHON_BIN="$(command -v "$candidate" 2>/dev/null || echo "$SCRIPT_DIR/$candidate")"
        break
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    err "Python not found. Create a venv first:
  python -m venv venv && venv/bin/pip install -r requirements.txt"
fi
ok "Python: $PYTHON_BIN"

# ── 3. Check Node / npm ────────────────────────────────────
if ! command -v npm &>/dev/null; then
    err "npm not found. Install Node.js (https://nodejs.org/) then re-run."
fi
ok "Node: $(node --version)  npm: $(npm --version)"

# ── 4. Install frontend deps if needed ────────────────────
if [[ ! -d "frontend/node_modules" ]]; then
    log "Installing frontend dependencies..."
    npm --prefix frontend install --silent
fi

# ── 5. Start Qdrant via Docker ─────────────────────────────
if command -v docker &>/dev/null; then
    log "Starting Qdrant (Docker)..."
    docker compose up -d qdrant 2>/dev/null || docker-compose up -d qdrant 2>/dev/null || \
        warn "Could not start Qdrant via Docker. Make sure Docker Desktop is running."
else
    warn "Docker not found — skipping Qdrant container. Make sure Qdrant is running on port 6333."
fi

echo ""
log "Starting services..."
echo ""

# ── 6. Start FastAPI backend ───────────────────────────────
export PYTHONIOENCODING="utf-8"
export TOKENIZERS_PARALLELISM=false

"$PYTHON_BIN" -m uvicorn api.main:app \
    --reload \
    --port 8000 \
    --log-level info &
BACKEND_PID=$!
ok "Backend started  (PID $BACKEND_PID)  → http://localhost:8000"
ok "API Docs         (Swagger)           → http://localhost:8000/docs"

# ── 7. Start React frontend ────────────────────────────────
npm --prefix frontend run dev &
FRONTEND_PID=$!
ok "Frontend started (PID $FRONTEND_PID)  → http://localhost:5173"

echo ""
echo -e "${BOLD}  All services running. Press Ctrl+C to stop all.${NC}"
echo ""

# ── Cleanup on exit ────────────────────────────────────────
cleanup() {
    echo ""
    log "Shutting down..."
    kill "$BACKEND_PID"  2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    ok "Done."
}
trap cleanup INT TERM

wait
