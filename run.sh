#!/bin/bash
# run.sh — Production start script for VPS
# Usage: ./run.sh [port] [workers]
#   API_BASE_URL=http://vps-ip:8000 ./run.sh

PORT=${1:-8000}
WORKERS=${2:-2}

cd "$(dirname "$0")"

export API_BASE_URL="${API_BASE_URL:-}"

echo "[*] Starting MTL Validator on 0.0.0.0:$PORT (workers=$WORKERS)" >&2
if [ -n "$API_BASE_URL" ]; then
    echo "    Dify import URL: ${API_BASE_URL}/dify/openapi.json" >&2
else
    echo "    Set API_BASE_URL env for Dify import (auto-detect from request otherwise)" >&2
fi

uvicorn main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level info
