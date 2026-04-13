#!/usr/bin/env bash
# start_backend.sh — Start the FastAPI backend
set -e

cd "$(dirname "$0")"

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🚀 Starting FastAPI backend on http://localhost:8080..."
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
