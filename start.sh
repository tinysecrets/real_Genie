#!/usr/bin/env bash
# Ember — one-shot local setup + startup.
# Does the absolute minimum needed. Skips steps that are already done.
# Usage: ./start.sh
set -e

cd "$(dirname "$0")"
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; NC='\033[0m'
# ok prints a green checkmark followed by the provided message in green to stdout.
ok()   { echo -e "${GREEN}✓${NC} $1"; }
# info prints an informational message to stdout prefixed with a blue arrow.
info() { echo -e "${BLUE}→${NC} $1"; }
# warn prints a yellow warning message prefixed with '!'.
warn() { echo -e "${YELLOW}!${NC} $1"; }
# fail prints a red error message prefixed with "✗" and then exits the script with status 1.
# It takes a single argument: the error message to display.
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo -e "${BLUE}━━━ Ember — local setup ━━━${NC}"
echo ""

# ---------- prereqs ----------
command -v python3 >/dev/null || fail "Python 3 not found. Install from https://python.org"
command -v node    >/dev/null || fail "Node not found. Install from https://nodejs.org (18+)"
command -v mongosh >/dev/null 2>&1 || command -v mongo >/dev/null 2>&1 || warn "MongoDB CLI not found — make sure 'mongod' is running on :27017"
command -v ffmpeg  >/dev/null 2>&1 || warn "ffmpeg not found — voice transcription (Vosk) will be disabled. Install: brew install ffmpeg / apt-get install ffmpeg"
command -v ollama  >/dev/null 2>&1 || warn "ollama not found — chat will not respond. Install from https://ollama.com/download"
ok "Prereqs checked"

# ---------- backend deps ----------
cd backend
if [ ! -d ".venv" ]; then
    info "Creating Python venv..."
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
info "Installing Python deps (this can take a couple minutes the first time)..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
ok "Python deps installed"

# Playwright browser
if [ ! -d "$HOME/Library/Caches/ms-playwright" ] && [ ! -d "$HOME/.cache/ms-playwright" ]; then
    info "Installing Playwright Chromium..."
    python -m playwright install chromium >/dev/null
    ok "Chromium installed"
else
    ok "Playwright Chromium already installed"
fi

# Vosk model
if [ ! -d "models/vosk-en-small" ]; then
    info "Downloading Vosk speech model (~68 MB, one time only)..."
    mkdir -p models && cd models
    if command -v curl >/dev/null 2>&1; then
        curl -L -o vosk.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    else
        wget -q https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip -O vosk.zip
    fi
    unzip -q vosk.zip
    rm vosk.zip
    mv vosk-model-small-en-us-0.15 vosk-en-small
    cd ..
    ok "Vosk model installed"
else
    ok "Vosk model already installed"
fi

# .env (only create if missing)
if [ ! -f ".env" ]; then
    cat > .env <<EOF
MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"
CORS_ORIGINS="*"
OLLAMA_URL="http://localhost:11434"
OLLAMA_MODEL="dolphin3"
OLLAMA_VISION_MODEL="llama3.2-vision"
VOSK_MODEL_PATH="./models/vosk-en-small"
COOKIE_SECURE="false"
COOKIE_SAMESITE="lax"
EOF
    ok "backend/.env created (localhost-friendly)"
else
    ok "backend/.env already present"
fi
cd ..

# ---------- frontend deps ----------
cd frontend
if [ ! -d "node_modules" ]; then
    info "Installing frontend deps (this takes 1-2 min the first time)..."
    if command -v yarn >/dev/null 2>&1; then
        yarn install --silent
    else
        npm install --silent
    fi
    ok "Frontend deps installed"
else
    ok "Frontend deps already installed"
fi

if [ ! -f ".env" ]; then
    cat > .env <<EOF
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
ENABLE_HEALTH_CHECK=false
EOF
    ok "frontend/.env created"
else
    ok "frontend/.env already present"
fi
cd ..

# ---------- launch ----------
echo ""
info "Starting backend on http://localhost:8001 ..."
cd backend
source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
cd ..

sleep 3
if curl -sf http://localhost:8001/api/ >/dev/null; then
    ok "Backend is up:  http://localhost:8001/api/"
else
    warn "Backend didn't respond yet. Tailing logs..."
fi

echo ""
info "Starting frontend on http://localhost:3000 ..."
cd frontend
if command -v yarn >/dev/null 2>&1; then
    yarn start &
else
    npm start &
fi
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}━━━ Ember is starting ━━━${NC}"
echo "  Backend  → http://localhost:8001/api/"
echo "  Frontend → http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop everything."

trap "echo ''; info 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
