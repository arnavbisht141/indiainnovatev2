#!/bin/bash
# ============================================================
# Nagar Mirror — One-command startup
# Starts the FastAPI backend and Vite frontend in parallel
# ============================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# ── Colors ──────────────────────────────────────────────────
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${CYAN}"
echo "  ███╗   ██╗ █████╗  ██████╗  █████╗ ██████╗     ███╗   ███╗██╗██████╗ ██████╗  ██████╗ ██████╗ "
echo "  ████╗  ██║██╔══██╗██╔════╝ ██╔══██╗██╔══██╗    ████╗ ████║██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗"
echo "  ██╔██╗ ██║███████║██║  ███╗███████║██████╔╝    ██╔████╔██║██║██████╔╝██████╔╝██║   ██║██████╔╝"
echo "  ██║╚██╗██║██╔══██║██║   ██║██╔══██║██╔══██╗    ██║╚██╔╝██║██║██╔══██╗██╔══██╗██║   ██║██╔══██╗"
echo "  ██║ ╚████║██║  ██║╚██████╔╝██║  ██║██║  ██║    ██║ ╚═╝ ██║██║██║  ██║██║  ██║╚██████╔╝██║  ██║"
echo -e "  ╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝    ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝${NC}"
echo ""
echo -e "${YELLOW}  Citizen Intelligence Platform — Karol Bagh Ward${NC}"
echo ""

# ── Check .env ───────────────────────────────────────────────
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo -e "${RED}✗  Root .env not found. Copy backend/.env.example → .env and fill in Neo4j credentials.${NC}"
    exit 1
fi

source "$ROOT_DIR/.env"

if [ -z "$NEO4J_URI" ] || [ -z "$NEO4J_PASSWORD" ] || [ "$NEO4J_URI" = "neo4j+s://xxxxxxxx.databases.neo4j.io" ]; then
    echo -e "${YELLOW}⚠  Neo4j credentials not set in .env — backend will start but DB calls will fail.${NC}"
    echo -e "   Edit .env and set NEO4J_URI and NEO4J_PASSWORD (get free AuraDB at https://console.neo4j.io)"
    echo ""
fi

# ── Start Backend ────────────────────────────────────────────
echo -e "${CYAN}▶  Starting FastAPI backend on http://localhost:8000${NC}"
(
    cd "$BACKEND_DIR"
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    # Copy root .env to backend if not present
    [ ! -f ".env" ] && cp "$ROOT_DIR/.env" .env
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 2>&1 | sed "s/^/  [backend] /"
) &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# ── Start Frontend ───────────────────────────────────────────
echo -e "${CYAN}▶  Starting Vite frontend on http://localhost:5174${NC}"
(
    cd "$FRONTEND_DIR"
    npm run dev 2>&1 | sed "s/^/  [frontend] /"
) &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}✅  Nagar Mirror is running!${NC}"
echo -e "      Frontend: ${CYAN}http://localhost:5174${NC}"
echo -e "      Backend:  ${CYAN}http://localhost:8000${NC}"
echo -e "      API Docs: ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "  Press ${RED}Ctrl+C${NC} to stop both servers."
echo ""

# Wait for either process to exit
trap "echo -e '\n${YELLOW}Shutting down...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait $BACKEND_PID $FRONTEND_PID
