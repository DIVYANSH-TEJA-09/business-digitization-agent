#!/bin/bash

# Start Caddy Reverse Proxy in the background to route Port 7860
./caddy run --config Caddyfile &

# Start FastAPI Backend in the background (listen on 8000)
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 &

# Start Next.js Frontend (listen on 3000)
cd frontend
npm start
