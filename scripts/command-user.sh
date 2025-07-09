#!/bin/sh
set -e

echo "Starting FastAPI service..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install --no-cache-dir .

echo "Starting Uvicorn..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload