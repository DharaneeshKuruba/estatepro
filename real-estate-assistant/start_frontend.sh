#!/usr/bin/env bash
# start_frontend.sh — Start the Streamlit frontend
set -e

cd "$(dirname "$0")"

echo "🌐 Starting Streamlit frontend on http://localhost:8501..."
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
