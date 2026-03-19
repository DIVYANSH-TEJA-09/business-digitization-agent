#!/bin/bash

echo "Starting Caddy..."
./caddy run --config Caddyfile &

echo "Starting FastAPI Backend..."
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --workers 1 &

echo "Starting Next.js Frontend with 1GB memory limit..."
cd frontend
NODE_OPTIONS="--max-old-space-size=1024" npm start
