#!/bin/bash

set -e
cd "$(dirname "$0")"
cd backend
rye run uvicorn src.theke.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

sleep 3

cd frontend
pnpm dev &
FRONTEND_PID=$!
cd ..

echo "up :http://localhost:5173"

cleanup() {
    echo ""
    echo "try to stop..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "done."
    exit 0
}

trap cleanup INT TERM

wait
