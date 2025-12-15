#!/bin/bash

# Start script for UNOOSA Registry application
# Starts both the Python API backend and React frontend

set -e

echo "🚀 Starting UNOOSA Registry..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill any existing processes on ports 8000 and 3000
echo "Cleaning up old processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start the API server
echo "📡 Starting API server on http://127.0.0.1:8000..."
cd "$SCRIPT_DIR"
/usr/local/Cellar/python@3.11/3.11.13/Frameworks/Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python -m uvicorn api:app --host 127.0.0.1 --port 8000 &
API_PID=$!
sleep 2

# Verify API is running
if ! kill -0 $API_PID 2>/dev/null; then
  echo "❌ Failed to start API server"
  exit 1
fi
echo "✅ API server running (PID: $API_PID)"

# Start the React development server
echo "⚛️  Starting React dev server on http://localhost:3000..."
cd "$SCRIPT_DIR/react-app"
npm run dev &
REACT_PID=$!
sleep 3

# Verify React is running
if ! kill -0 $REACT_PID 2>/dev/null; then
  echo "❌ Failed to start React dev server"
  kill $API_PID 2>/dev/null || true
  exit 1
fi
echo "✅ React dev server running (PID: $REACT_PID)"

echo ""
echo "=========================================="
echo "🎉 All services started successfully!"
echo "=========================================="
echo ""
echo "Access the app at: http://localhost:3000"
echo ""
echo "API server: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Handle Ctrl+C to stop both services
trap 'echo ""; echo "Stopping services..."; kill $API_PID $REACT_PID 2>/dev/null; exit 0' SIGINT

# Wait for both processes
wait
