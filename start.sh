#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=========================================================="
echo " Starting TitanOps AI Enterprise SRE Runbook Assistant "
echo "=========================================================="

# Ensure data directory exists and runbook is generated
mkdir -p "$DIR/backend/data/documents"
if [ ! -f "$DIR/backend/data/documents/titancloud_sre_incident_runbook_50p.pdf" ]; then
    echo "[*] Generating 50-page enterprise SRE runbook PDF..."
    PYTHONPATH="$DIR/backend" "$DIR/backend/venv/bin/python" "$DIR/backend/app/runbook_generator.py"
fi

# Start Backend Server
echo "[*] Starting FastAPI Backend on port 8000..."
cd "$DIR/backend"
PYTHONPATH="$DIR/backend" "$DIR/backend/venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Frontend Dev Server
echo "[*] Starting Vite Frontend on port 3000..."
cd "$DIR/frontend"
npm run dev -- --port 3000 --host 0.0.0.0 &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "[!] Stopping TitanOps AI services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "[✓] TitanOps AI running at:"
echo "    Frontend: http://localhost:3000"
echo "    Backend API: http://localhost:8000"
echo "    Swagger Docs: http://localhost:8000/docs"
echo "Press Ctrl+C to stop."

wait
