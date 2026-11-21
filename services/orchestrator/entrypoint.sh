#!/bin/sh
set -e

echo "Starting orchestrator..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8002}"